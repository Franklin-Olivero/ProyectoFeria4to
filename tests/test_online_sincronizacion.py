"""Tests para la sincronización multijugador online, tolerancia a desconexión y mazmorras."""

import socket
import time
import pytest

from Online.protocolo import (
    ENTRAR_MAZMORRA, CAMBIO_ESCENA, CAMBIO_CUARTO,
    msg_entrar_mazmorra, msg_cambio_escena, msg_cambio_cuarto,
    deserializar_buffer,
)
from Online.servidor import Servidor
from Online.cliente import Cliente
from Online.sesion_red import (
    _MandoFicticio, EntradaRed, EntradaLocalCliente, EntradaRemotaHost,
    AdaptadorOnlineHost, AdaptadorOnlineJoin, preparar_sesion_online,
    ConfigSesionHost, ConfigSesionJoin,
)
from src.core.entrada import EntradaMando, EntradaTeclado, InputJugador
from src.entities.player import Ciudadano
from src.entities.candidato import Candidato
from src.dungeon.partida import Partida


def test_mando_ficticio_evita_attribute_error():
    """Verifica que el mando ficticio responde a attached() y no causa crash en Main.py."""
    mf = _MandoFicticio()
    assert mf.attached() is True
    assert mf.get_axis(0) == 0.0
    assert mf.get_button(0) is False

    # EntradaMando instanciado con None ahora usa el mando ficticio automáticamente
    em = EntradaMando(None)
    assert em.mando is not None
    assert em.mando.attached() is True
    inp = em.leer()
    assert isinstance(inp, InputJugador)


def test_todas_las_entradas_online_tienen_mando_ficticio():
    """Garantiza que ninguna ranura de entrada en modo online lance AttributeError en Main.py."""
    er = EntradaRed(None, id_jugador=1)
    assert er.mando.attached() is True

    el = EntradaLocalCliente(None, id_jugador=1)
    assert el.mando.attached() is True

    eh = EntradaRemotaHost(None, id_jugador=0)
    assert eh.mando.attached() is True


def test_preparar_sesion_online_host():
    """Verifica la configuración de sesión para el Host."""
    servidor = Servidor()
    clases = [Ciudadano, Candidato]
    clases_res, mando_res, config = preparar_sesion_online(clases, None, servidor, es_host=True)

    assert isinstance(config, ConfigSesionHost)
    assert config.mando.attached() is True

    # Simular objeto sesión
    class DummySesion:
        pass
    sesion = DummySesion()
    config.configurar_sesion(sesion)

    assert sesion.id_local == 0
    assert isinstance(sesion.adaptador_red, AdaptadorOnlineHost)
    assert len(sesion.entradas) == 2
    assert isinstance(sesion.entradas[0], EntradaTeclado)
    assert isinstance(sesion.entradas[1], EntradaRed)
    assert sesion.entradas[1].mando.attached() is True


def test_preparar_sesion_online_join():
    """Verifica la configuración de sesión para el Invitado (Guest)."""
    cliente = Cliente()
    cliente.id_jugador = 1
    clases = [Ciudadano, Candidato]
    clases_res, mando_res, config = preparar_sesion_online(clases, None, cliente, es_host=False)

    assert isinstance(config, ConfigSesionJoin)
    assert config.mando.attached() is True

    class DummySesion:
        pass
    sesion = DummySesion()
    config.configurar_sesion(sesion)

    assert sesion.id_local == 1
    assert isinstance(sesion.adaptador_red, AdaptadorOnlineJoin)
    assert len(sesion.entradas) == 2
    # Ranura 0 es el Host remoto
    assert isinstance(sesion.entradas[0], EntradaRemotaHost)
    assert sesion.entradas[0].mando.attached() is True
    # Ranura 1 es el jugador local
    assert isinstance(sesion.entradas[1], EntradaLocalCliente)
    assert sesion.entradas[1].mando.attached() is True


def _esperar(condicion, limite_s=3.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def test_reconexion_en_partida_iniciada_recibe_iniciar_de_inmediato():
    """Si el host ya inició la partida, un invitado que se una o reconecte

    recibe INICIAR automáticamente y no queda atrapado en el lobby.
    """
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    # El host marca que la partida ya arrancó en la mazmorra Colegio
    servidor.marcar_iniciado({"escena": "MAZMORRA", "zona": "Colegio", "cuarto_idx": 1})

    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        # Esperar a que el cliente procese la bienvenida y el inicio
        assert _esperar(lambda: cliente.iniciado is True)
        assert cliente.estado_partida["escena"] == "MAZMORRA"
        assert cliente.estado_partida["zona"] == "Colegio"

        # El host recibe aviso de reconexión
        msgs_host = servidor.leer_mensajes()
        tipos_host = [m.get("tipo") for m in msgs_host]
        assert "RECONEXION" in tipos_host
    finally:
        cliente.detener()
        servidor.detener()


def test_protocolo_mensajes_mazmorra():
    """Valida la serialización y deserialización de mensajes de mazmorra."""
    datos = msg_entrar_mazmorra("Colegio", id_jugador=1)
    msgs, _ = deserializar_buffer(datos)
    assert len(msgs) == 1
    assert msgs[0]["tipo"] == ENTRAR_MAZMORRA
    assert msgs[0]["zona"] == "Colegio"
    assert msgs[0]["id"] == 1

    datos_escena = msg_cambio_escena("MAZMORRA", zona="Hospital", cuarto_idx=2)
    msgs, _ = deserializar_buffer(datos_escena)
    assert len(msgs) == 1
    assert msgs[0]["tipo"] == CAMBIO_ESCENA
    assert msgs[0]["escena"] == "MAZMORRA"
    assert msgs[0]["zona"] == "Hospital"
    assert msgs[0]["cuarto"] == 2

    datos_cuarto = msg_cambio_cuarto(3)
    msgs, _ = deserializar_buffer(datos_cuarto)
    assert len(msgs) == 1
    assert msgs[0]["tipo"] == CAMBIO_CUARTO
    assert msgs[0]["cuarto"] == 3


def test_normalizar_escena_evita_crash_sin_lugar():
    """Valida que normalizar_escena rescate el juego si una escena de combate
    no tiene su mazmorra o arena cargada."""
    from src.core.escenas import Escena
    from Online.sesion_red import normalizar_escena

    # MAZMORRA sin mazmorra -> vuelve a CIUDAD
    corregida = normalizar_escena(Escena.MAZMORRA, arena=None, mazmorra=None,
                                  resultado=None, jugador=None, partida=None)
    assert corregida == Escena.CIUDAD

    # JEFE sin arena -> vuelve a CIUDAD
    corregida_jefe = normalizar_escena(Escena.JEFE, arena=None, mazmorra=None,
                                       resultado=None, jugador=None, partida=None)
    assert corregida_jefe == Escena.CIUDAD

    # CIUDAD normal permanece igual
    assert normalizar_escena(Escena.CIUDAD, None, None, None, None, None) == Escena.CIUDAD


def test_proteger_partida_online_captura_excepciones():
    """Valida que en una partida online una excepción no cierre el juego a escritorio
    sino que retorne MENU de forma segura."""
    from Online.sesion_red import proteger_partida_online, MENU

    def funcion_que_falla(*args):
        raise ValueError("Error simulado en sincronización")

    protegida = proteger_partida_online(funcion_que_falla)

    class SesionLocal:
        adaptador_red = None

    class SesionOnline:
        adaptador_red = object()

    # Si es local, debe lanzar la excepción
    with pytest.raises(ValueError):
        protegida(None, None, SesionLocal(), None, None)

    # Si es online, debe atraparla y retornar MENU sin tumbar el juego
    resultado = protegida(None, None, SesionOnline(), None, None)
    assert resultado == MENU


def test_compartir_combate_con_sesion():
    """Valida que compartir_combate_con_sesion adjunte las referencias en la sesión."""
    from Online.sesion_red import compartir_combate_con_sesion

    class DummySesion:
        pass

    sesion = DummySesion()
    limpiar = lambda: None
    proyectiles = []
    textos = object()

    compartir_combate_con_sesion(sesion, limpiar, proyectiles, textos)
    assert sesion.limpiar_combate is limpiar
    assert sesion.proyectiles_enemigos is proyectiles
    assert sesion.textos is textos


def test_frame_de_combate_con_escenario_none():
    """Valida que _frame_de_combate retorne sin error si escenario es None."""
    from Main import _frame_de_combate

    # No debe levantar ninguna excepción
    _frame_de_combate(0.016, [], [], None, [], [], None, None)

