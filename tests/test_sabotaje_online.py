"""Sabotaje del impostor en la terminal de decisión (modo Online): la carga
pura, el host que la hace cumplir, el invitado que la refleja y el aviso de
quién sigue leyendo una escena de la historia."""

import os
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import COOLDOWN_SABOTAJE_IMPOSTOR  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA, TerminalDecision, construir_arbol_publicacion  # noqa: E402
from Online import sabotaje_render  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import DECISION_NAV, DESCONEXION, HISTORIA  # noqa: E402
from Online.sabotaje import Sabotaje  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import LECTURA, AdaptadorOnlineHost, AdaptadorOnlineJoin  # noqa: E402

RECARGA = COOLDOWN_SABOTAJE_IMPOSTOR


def test_la_recarga_pedida_es_de_15_segundos():
    assert RECARGA == 15.0


# ----------------------------------------------------------------------
# La carga, sola
# ----------------------------------------------------------------------

def test_sin_terminal_no_hay_sabotaje():
    sabotaje = Sabotaje()
    sabotaje.actualizar(100)
    assert not sabotaje.activo and not sabotaje.listo and not sabotaje.intentar()


def test_una_terminal_nueva_empieza_vacia_y_se_llena_en_15_segundos():
    sabotaje, terminal = Sabotaje(), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(RECARGA - 0.01)
    assert not sabotaje.listo and not sabotaje.intentar()  # los primeros 15 s son del equipo
    sabotaje.actualizar(0.01)
    assert sabotaje.listo


def test_sabotear_gasta_la_carga_y_vuelve_a_recargar():
    sabotaje, terminal = Sabotaje(), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(RECARGA)
    assert sabotaje.intentar() is True
    assert sabotaje.restante == RECARGA and not sabotaje.intentar()
    sabotaje.actualizar(RECARGA)
    assert sabotaje.intentar() is True


def test_la_misma_terminal_no_reinicia_la_carga_y_otra_si():
    sabotaje, terminal = Sabotaje(), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(10)
    sabotaje.seguir_terminal(terminal)  # cada frame se vuelve a decir cuál es
    assert sabotaje.restante == pytest.approx(RECARGA - 10)
    sabotaje.seguir_terminal(object())  # otra mazmorra
    assert sabotaje.restante == RECARGA
    sabotaje.actualizar(RECARGA)
    sabotaje.seguir_terminal(None)  # se cerró la terminal
    assert not sabotaje.activo and sabotaje.restante == RECARGA


# ----------------------------------------------------------------------
# El host hace cumplir la carga
# ----------------------------------------------------------------------

class _ServidorFalso:
    def __init__(self):
        self.cola = []

    def leer_mensajes(self):
        mensajes, self.cola = self.cola, []
        return mensajes


def _mazmorra_en_decision():
    terminal = TerminalDecision(construir_arbol_publicacion(), duracion=45.0)
    terminal.iniciar()
    return SimpleNamespace(cuarto=SimpleNamespace(terminal=terminal), mazmorra=SimpleNamespace(nombre_zona="Colegio"))


def _host(impostor=1):
    """Host con 2 jugadores (ids 0 y 1) y una terminal abierta; `impostor` = su índice."""
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    if impostor is not None:
        jugadores[impostor].es_impostor = True
    host._preparar_frame(SimpleNamespace(), None, jugadores)
    mazmorra = _mazmorra_en_decision()
    host._seguir_sabotaje(Escena.DECISION, mazmorra, 0.0)
    return host, mazmorra


def _pasar(host, mazmorra, segundos):
    host._seguir_sabotaje(Escena.DECISION, mazmorra, segundos)


def _nav(host, direccion, id_red=1):
    host.servidor.cola.append({"tipo": DECISION_NAV, "dir": direccion, "id": id_red})
    host._procesar_mensajes()
    pedidos = list(host._solicitudes_decision)
    host._solicitudes_decision.clear()
    return pedidos


def test_el_impostor_no_navega_en_los_primeros_15_segundos():
    host, mazmorra = _host(impostor=1)
    assert _nav(host, DERECHA) == []
    _pasar(host, mazmorra, RECARGA - 0.5)
    assert _nav(host, CONFIRMAR) == []
    assert host.restante_sabotaje() == pytest.approx(0.5)


def test_con_la_carga_lista_el_impostor_sabotea_una_vez_y_espera_otra_vez():
    host, mazmorra = _host(impostor=1)
    _pasar(host, mazmorra, RECARGA)
    assert _nav(host, DERECHA) == [DERECHA]
    assert _nav(host, CONFIRMAR) == []  # ya gastó la carga
    assert host.restante_sabotaje() == RECARGA
    _pasar(host, mazmorra, RECARGA)
    assert _nav(host, CONFIRMAR) == [CONFIRMAR]


def test_el_resto_del_equipo_navega_libre():
    host, mazmorra = _host(impostor=0)  # el impostor es el host: el invitado 1 es tripulante
    assert _nav(host, DERECHA) == [DERECHA]
    assert _nav(host, IZQUIERDA) == [IZQUIERDA]
    assert _nav(host, CONFIRMAR) == [CONFIRMAR]


def test_el_host_impostor_tambien_espera_su_carga():
    host, mazmorra = _host(impostor=0)
    assert host.puede_navegar(0) is False
    _pasar(host, mazmorra, RECARGA)
    assert host.puede_navegar(0) is True
    assert host.puede_navegar(0) is False  # la gastó
    assert host.puede_navegar(1) is True


def test_sin_impostor_nadie_tiene_limite():
    host, _ = _host(impostor=None)
    assert _nav(host, DERECHA) == [DERECHA]
    assert host.puede_navegar(0) and host.puede_navegar(1)


def test_fuera_de_la_terminal_el_impostor_navega_libre():
    """La investigación del capítulo 3 también usa DECISION_NAV: ahí no hay sabotaje."""
    host, mazmorra = _host(impostor=1)
    host._seguir_sabotaje(Escena.RESULTADO, None, 0.1)
    assert host.restante_sabotaje() is None
    assert _nav(host, DERECHA) == [DERECHA]


def test_una_confirmacion_rechazada_no_carga_al_impostor_con_la_decision():
    host, _ = _host(impostor=1)
    campania = SimpleNamespace(puede_decidir=lambda i: True, actores=[])
    campania.registrar_actor = campania.actores.append
    host._partida = SimpleNamespace(campania=campania)
    assert _nav(host, CONFIRMAR) == []
    assert campania.actores == [] and host.ultimo_actor == 0


def test_el_estado_lleva_la_carga_con_la_terminal():
    host, mazmorra = _host(impostor=1)
    _pasar(host, mazmorra, 4.0)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0), _reinicios_red=0, _historial_red=[],
                              campania=SimpleNamespace(resumen_red=lambda: {}))
    mazmorra.cuarto.fase = None
    estado = host.estado_completo(Escena.DECISION, None, _mazmorra_completa(mazmorra), partida, host._jugadores)
    assert estado["term"]["sab"] == pytest.approx(RECARGA - 4.0)
    assert estado["leen"] == []


def _mazmorra_completa(mazmorra):
    """Lo que estado_completo lee de una mazmorra real, con la terminal de `mazmorra`."""
    from src.dungeon.mazmorra import Mazmorra
    from src.dungeon.mazmorra_jugable import MazmorraJugable
    from src.dungeon.partida import Partida
    real = MazmorraJugable(Mazmorra(Partida().ciudad.reportes("Colegio"), "Colegio", semilla=3))
    real.cuarto.terminal = mazmorra.cuarto.terminal
    return real


# ----------------------------------------------------------------------
# Quién sigue leyendo una escena de la historia
# ----------------------------------------------------------------------

def test_el_host_anota_a_quien_lee_y_lo_olvida_al_cerrar_o_irse():
    host, _ = _host()
    host.servidor.cola.append({"tipo": HISTORIA, "evento": LECTURA, "ocupado": True, "id": 1})
    host._procesar_mensajes()
    assert host.esperando_lectura() == [1]
    host.servidor.cola.append({"tipo": HISTORIA, "evento": LECTURA, "ocupado": False, "id": 1})
    host._procesar_mensajes()
    assert host.esperando_lectura() == []
    host.servidor.cola.append({"tipo": HISTORIA, "evento": LECTURA, "ocupado": True, "id": 1})
    host.servidor.cola.append({"tipo": DESCONEXION, "id": 1})
    host._procesar_mensajes()
    assert host.esperando_lectura() == []  # se fue: el mundo no lo espera para siempre


def test_el_estado_dice_quien_lee_incluido_el_host():
    host, _ = _host()
    host._leyendo.add(1)
    host._sesion = SimpleNamespace(historia_ocupada=True)
    assert host._lectores() == [0, 1]


class _ClienteFalso:
    conectado = True

    def __init__(self):
        self.historias = []

    def enviar_historia(self, evento, **datos):
        self.historias.append((evento, datos))


def test_el_invitado_avisa_solo_cuando_abre_o_cierra_una_escena():
    cliente = _ClienteFalso()
    invitado = AdaptadorOnlineJoin(cliente, id_local=1, ids_red=[0, 1])
    for ocupado in (False, True, True, True, False, False):
        invitado._sesion = SimpleNamespace(historia_ocupada=ocupado)
        invitado._avisar_lectura()
    assert cliente.historias == [(LECTURA, {"ocupado": True}), (LECTURA, {"ocupado": False})]


def test_el_invitado_refleja_carga_y_lectores_del_host():
    invitado = AdaptadorOnlineJoin(_ClienteFalso(), id_local=1, ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[1].es_impostor = True
    invitado._preparar_frame(SimpleNamespace(), None, jugadores)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0),
                              campania=SimpleNamespace(aplicar_resumen_red=lambda datos: None))
    invitado._aplicar({"term": {"sab": 6.5}, "leen": [0, 1, "x"]}, Escena.DECISION, None, None, partida, jugadores)
    assert invitado.restante_sabotaje() == 6.5
    assert invitado.puede_navegar(1) is False  # él es el impostor y recarga
    assert invitado.puede_navegar(0) is True
    assert invitado.esperando_lectura() == [0]  # él mismo no cuenta
    invitado._aplicar({"term": {"sab": 0}}, Escena.DECISION, None, None, partida, jugadores)
    assert invitado.puede_navegar(1) is True and invitado.esperando_lectura() == []
    invitado._aplicar({}, Escena.MAZMORRA, None, None, partida, jugadores)
    assert invitado.restante_sabotaje() is None and invitado.puede_navegar(1) is True


# ----------------------------------------------------------------------
# Por la red de verdad
# ----------------------------------------------------------------------

def _esperar(condicion, limite_s=5.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def test_por_red_el_host_frena_al_invitado_impostor_y_cuenta_su_lectura():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.id_jugador == 1)
        host = AdaptadorOnlineHost(servidor, ids_red=[0, 1])
        jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
        jugadores[1].es_impostor = True
        host._preparar_frame(SimpleNamespace(), None, jugadores)
        mazmorra = _mazmorra_en_decision()
        host._seguir_sabotaje(Escena.DECISION, mazmorra, 0.0)

        cliente.enviar_decision_nav(DERECHA)  # en recarga: no vale
        cliente.enviar_historia(LECTURA, ocupado=True)
        recibidos = []

        def procesado():
            host._procesar_mensajes()
            recibidos.extend(host._solicitudes_decision)
            host._solicitudes_decision.clear()
            return host.esperando_lectura() == [1]

        assert _esperar(procesado)
        assert recibidos == []
        host._seguir_sabotaje(Escena.DECISION, mazmorra, RECARGA)
        cliente.enviar_decision_nav(DERECHA)  # con la carga lista: sí
        assert _esperar(lambda: procesado() and recibidos == [DERECHA])
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# Lo que ve el impostor
# ----------------------------------------------------------------------

def test_textos_del_indicador():
    assert sabotaje_render.texto_sabotaje(0) == assets.TEXTO_SABOTAJE_LISTO
    assert sabotaje_render.texto_sabotaje(11.2) == "Recargando: 12 s"
    assert sabotaje_render.texto_sabotaje(11.2, aviso=0.3) == "Aún no: faltan 12 s"


@pytest.mark.parametrize("restante, lleno", [(RECARGA, 0.0), (RECARGA / 2, 0.5), (0.0, 1.0)])
def test_el_indicador_se_dibuja_con_su_barra(restante, lleno):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    sabotaje_render.dibujar_sabotaje(pantalla, restante)
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    barra_y = rect.bottom - 10
    rojos = [x for x in range(rect.left + 16, rect.right - 16)
             if pantalla.get_at((x, barra_y))[:3] == assets.COLOR_IMPOSTOR]
    assert len(rojos) / (rect.width - 32) == pytest.approx(lleno, abs=0.03)
