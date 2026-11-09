"""Reputación y redención en red, con sockets reales en localhost.

El host es la autoridad: cada jugador tiene su reputación, los invitados la
reciben en el snapshot y una decisión de crisis de un invitado la aplica el host.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import HISTORIA, msg_historia  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import AdaptadorOnlineHost, AdaptadorOnlineJoin  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.story.investigacion import Investigacion  # noqa: E402
from src.story.reputacion import EN_REDENCION, RECHAZADA, REDIMIDO  # noqa: E402


class _SesionFalsa:
    historia_ocupada = False


def _esperar(condicion, limite_s=3.0):
    fin = time.time() + limite_s
    while time.time() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def red():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") if _acepta_cero(servidor) else servidor.iniciar(7791, interfaz="127.0.0.1")
    puerto = getattr(servidor, "puerto", 7791)
    cliente = Cliente()
    assert cliente.conectar("127.0.0.1", puerto)
    assert _esperar(lambda: cliente.id_jugador is not None)
    yield servidor, cliente
    cliente.detener()
    servidor.detener()


def _acepta_cero(_servidor):
    return False


def _host(servidor):
    partida = Partida()
    partida.campania.rep(0)
    partida.campania.rep(1)
    adaptador = AdaptadorOnlineHost(servidor, ids_red=[0, 1])
    adaptador._partida = partida
    adaptador._sesion = _SesionFalsa()
    return partida, adaptador


def _procesar_hasta(adaptador, condicion):
    return _esperar(lambda: (adaptador._procesar_mensajes(), condicion())[1])


def test_el_protocolo_lleva_las_decisiones_de_historia():
    mensaje = msg_historia("completar", 2, origenes=["ana"])
    assert b'"HISTORIA"' in mensaje and b'"ana"' in mensaje
    assert HISTORIA == "HISTORIA"


def test_el_invitado_acepta_y_completa_y_el_host_fija_la_reputacion(red):
    servidor, cliente = red
    partida, host = _host(servidor)
    campania = partida.campania
    id_invitado = cliente.id_jugador
    indice = host._indice_de_id(id_invitado)
    campania.rep(indice).aplicar(-80, "Daño", "Colegio")
    campania.red.expuestos = {"ana", "gina"}

    cliente.enviar_historia("aceptar")
    assert _procesar_hasta(host, lambda: campania.rep(indice).estado_crisis == EN_REDENCION)
    assert campania.rep(0).valor == 0  # el host no se ve afectado

    cliente.enviar_historia("completar", origenes=["ana", "no_existe", 7])
    assert _procesar_hasta(host, lambda: campania.rep(indice).estado_crisis == REDIMIDO)
    assert campania.rep(indice).valor == -35  # -80 + 45
    assert "ana" in campania.red.corregidos  # BFS recalculado en el host
    # Repetir el mensaje no paga otra vez.
    cliente.enviar_historia("completar", origenes=["ana"])
    time.sleep(0.1)
    host._procesar_mensajes()
    assert campania.rep(indice).valor == -35


def test_un_invitado_que_rechaza_no_termina_la_partida_de_los_demas(red):
    servidor, cliente = red
    partida, host = _host(servidor)
    campania = partida.campania
    indice = host._indice_de_id(cliente.id_jugador)
    campania.rep(indice).aplicar(-80, "Daño", "Colegio")
    cliente.enviar_historia("rechazar")
    assert _procesar_hasta(host, lambda: campania.rep(indice).estado_crisis == RECHAZADA)
    assert not campania.todos_sin_voz() and campania.puede_decidir(0) and not campania.puede_decidir(indice)
    # Su navegación en la terminal ya no cuenta.
    cliente.enviar_decision_nav("confirmar")
    time.sleep(0.1)
    host._procesar_mensajes()
    assert host._solicitudes_decision == []
    # Y puede volver al punto de control.
    cliente.enviar_historia("reintentar")
    assert _procesar_hasta(host, lambda: campania.puede_decidir(indice))


def test_quien_confirma_en_la_terminal_carga_con_la_decision(red):
    servidor, cliente = red
    partida, host = _host(servidor)
    indice = host._indice_de_id(cliente.id_jugador)
    cliente.enviar_decision_nav("derecha")
    time.sleep(0.05)
    host._procesar_mensajes()
    assert partida.campania.actor_decision == 0
    cliente.enviar_decision_nav("confirmar")
    assert _procesar_hasta(host, lambda: partida.campania.actor_decision == indice)
    assert host.ultimo_actor == indice


def test_snapshot_del_host_llega_a_la_copia_del_invitado():
    host = Partida()
    host.campania.rep(0).aplicar(30, "Bien", "Colegio")
    host.campania.rep(1).aplicar(-70, "Mal", "Hospital")
    invitado = Partida()
    invitado.campania.espejo = True
    invitado.campania.aplicar_resumen_red(host.campania.resumen_red())
    assert invitado.campania.rep(0).valor == 30 and invitado.campania.rep(1).crisis_pendiente


def test_decision_del_invitado_no_se_revierte_con_un_snapshot_viejo():
    host = Partida().campania
    host.rep(1).aplicar(-70, "Mal", "Hospital")
    invitado = Partida().campania
    invitado.espejo = True
    invitado.aplicar_resumen_red(host.resumen_red())
    invitado.esperar_host(1)
    invitado.aceptar_redencion(1)
    # Este snapshot salió antes de que el host procesara el mensaje.
    invitado.aplicar_resumen_red(host.resumen_red())
    assert invitado.jugador_en_crisis([1]) is None and invitado.mision_de(1) is not None
    # El host lo procesa: ahora los dos coinciden.
    host.aceptar_redencion(1)
    invitado.aplicar_resumen_red(host.resumen_red())
    assert invitado.rep(1).estado_crisis == EN_REDENCION and 1 not in invitado.esperando_host


def test_investigacion_se_refleja_en_el_invitado():
    datos = Partida().campania.contenido["red_cuentas"]
    host = Investigacion(datos)
    host.navegar("derecha")
    host.navegar("confirmar")
    invitado = Investigacion(datos)
    invitado.copiar_de(host.a_dict())
    assert invitado.pila == host.pila and invitado.visitadas == host.visitadas
    host.senalar(host.actual)
    host.resultado = host.senalar("nova_root")
    invitado.copiar_de(host.a_dict())
    assert invitado.terminada and invitado.resultado.correcto
    invitado.copiar_de({"pila": ["no_existe"], "vis": 3, "i": "x", "fin": "nadie"})  # basura: no se rompe
    assert invitado.pila == host.pila


def test_las_entradas_de_invitados_esperan_si_el_host_lee_una_escena(red):
    servidor, _ = red
    partida, host = _host(servidor)
    sesion = _SesionFalsa()
    sesion.historia_ocupada = True
    host._sesion = sesion
    host._solicitudes = ["Colegio"]
    jugadores = [Ciudadano(0, 0)]
    resultado = host._atender_solicitudes(Escena.CIUDAD, None, None, 0.0, partida, jugadores)
    assert resultado[0] == Escena.CIUDAD and host._solicitudes == ["Colegio"]


def test_adaptador_del_invitado_expone_el_envio_de_historia():
    assert hasattr(AdaptadorOnlineJoin, "enviar_historia")
