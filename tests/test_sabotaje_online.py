"""Sabotaje del impostor en la terminal de decisión (modo Online): el
bloqueo puro (10 a 15 s al abrirse la terminal, después elige normal), el
host que lo hace cumplir, el invitado que lo refleja y el aviso de quién
sigue leyendo una escena de la historia."""

import os
import random
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import COOLDOWN_SABOTAJE_MAX, COOLDOWN_SABOTAJE_MIN  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui import dibujo  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA, TerminalDecision, construir_arbol_publicacion  # noqa: E402
from Online import sabotaje_render  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import DECISION_NAV, DESCONEXION, HISTORIA  # noqa: E402
from Online.sabotaje import Sabotaje  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import LECTURA, AdaptadorOnlineHost, AdaptadorOnlineJoin  # noqa: E402

ESPERA = 12.0  # bloqueo fijo (mínimo = máximo) para contar los segundos en los tests


def test_el_bloqueo_pedido_va_de_10_a_15_segundos():
    assert (COOLDOWN_SABOTAJE_MIN, COOLDOWN_SABOTAJE_MAX) == (10.0, 15.0)


# ----------------------------------------------------------------------
# El bloqueo, solo
# ----------------------------------------------------------------------

def test_sin_terminal_no_hay_sabotaje():
    sabotaje = Sabotaje()
    sabotaje.actualizar(100)
    assert not sabotaje.activo and not sabotaje.listo


def test_cada_terminal_sortea_su_bloqueo_entre_10_y_15_segundos():
    sabotaje = Sabotaje(azar=random.Random(4))
    esperas = []
    for _ in range(200):
        sabotaje.seguir_terminal(object())  # una mazmorra nueva cada vez
        assert sabotaje.restante == sabotaje.espera and not sabotaje.listo
        esperas.append(sabotaje.espera)
    assert all(COOLDOWN_SABOTAJE_MIN <= espera <= COOLDOWN_SABOTAJE_MAX for espera in esperas)
    assert max(esperas) - min(esperas) > 3  # de verdad cambia de una terminal a otra


def test_con_la_misma_semilla_sale_el_mismo_bloqueo():
    a, b = Sabotaje(azar=random.Random(7)), Sabotaje(azar=random.Random(7))
    for _ in range(5):
        a.seguir_terminal(object())
        b.seguir_terminal(object())
        assert a.espera == b.espera


def test_con_minimo_y_maximo_iguales_el_bloqueo_es_fijo():
    sabotaje = Sabotaje(minimo=ESPERA, maximo=ESPERA)
    sabotaje.seguir_terminal(object())
    assert sabotaje.espera == sabotaje.restante == ESPERA


def test_bloqueado_al_abrir_y_despues_habilitado_hasta_cerrar():
    sabotaje, terminal = Sabotaje(ESPERA, ESPERA), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(ESPERA - 0.01)
    assert not sabotaje.listo  # los primeros segundos son del equipo
    sabotaje.actualizar(0.01)
    assert sabotaje.listo
    for _ in range(20):  # ya no se vuelve a bloquear: elegir no gasta nada
        sabotaje.seguir_terminal(terminal)
        sabotaje.actualizar(0.5)
        assert sabotaje.listo and sabotaje.restante == 0.0


def test_la_misma_terminal_sigue_su_cuenta_y_otra_vuelve_a_bloquear():
    sabotaje, terminal = Sabotaje(ESPERA, ESPERA), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(10)
    sabotaje.seguir_terminal(terminal)  # cada frame se vuelve a decir cuál es
    assert sabotaje.restante == pytest.approx(ESPERA - 10)
    sabotaje.actualizar(ESPERA)
    assert sabotaje.listo
    sabotaje.seguir_terminal(object())  # la terminal de otra mazmorra
    assert sabotaje.restante == ESPERA and not sabotaje.listo


def test_sin_terminal_el_bloqueo_no_corre_y_la_misma_terminal_lo_retoma():
    sabotaje, terminal = Sabotaje(ESPERA, ESPERA), object()
    sabotaje.seguir_terminal(terminal)
    sabotaje.actualizar(5)
    sabotaje.seguir_terminal(None)  # un frame sin terminal
    sabotaje.actualizar(100)
    assert not sabotaje.activo and not sabotaje.listo
    sabotaje.seguir_terminal(terminal)
    assert sabotaje.restante == pytest.approx(ESPERA - 5)  # ni se sorteó de nuevo ni se saltó el bloqueo


# ----------------------------------------------------------------------
# El host hace cumplir el bloqueo
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


def _host(impostor=1, sabotaje=None):
    """Host con 2 jugadores (ids 0 y 1) y una terminal abierta; `impostor` = su índice."""
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1])
    host.sabotaje = sabotaje or Sabotaje(ESPERA, ESPERA)
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


def test_el_host_de_verdad_sortea_entre_10_y_15_segundos():
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1])
    assert (host.sabotaje.minimo, host.sabotaje.maximo) == (COOLDOWN_SABOTAJE_MIN, COOLDOWN_SABOTAJE_MAX)
    assert host.espera_sabotaje() is None  # sin terminal
    host._seguir_sabotaje(Escena.DECISION, _mazmorra_en_decision(), 0.0)
    assert COOLDOWN_SABOTAJE_MIN <= host.espera_sabotaje() <= COOLDOWN_SABOTAJE_MAX
    assert host.restante_sabotaje() == host.espera_sabotaje()


def test_el_impostor_no_navega_durante_el_bloqueo():
    host, mazmorra = _host(impostor=1)
    assert _nav(host, DERECHA) == []
    _pasar(host, mazmorra, ESPERA - 0.5)
    assert _nav(host, CONFIRMAR) == []
    assert host.restante_sabotaje() == pytest.approx(0.5)


def test_tras_el_bloqueo_el_impostor_elige_normal_sin_limite():
    """El bug: antes solo podía hacer un movimiento y se volvía a bloquear."""
    host, mazmorra = _host(impostor=1)
    _pasar(host, mazmorra, ESPERA)
    for direccion in (DERECHA, DERECHA, IZQUIERDA, DERECHA):
        assert _nav(host, direccion) == [direccion]
        _pasar(host, mazmorra, 0.1)
    assert _nav(host, CONFIRMAR) == [CONFIRMAR]
    assert host.restante_sabotaje() == 0.0


def test_el_resto_del_equipo_navega_libre():
    host, mazmorra = _host(impostor=0)  # el impostor es el host: el invitado 1 es tripulante
    assert _nav(host, DERECHA) == [DERECHA]
    assert _nav(host, IZQUIERDA) == [IZQUIERDA]
    assert _nav(host, CONFIRMAR) == [CONFIRMAR]


def test_el_host_impostor_tambien_espera_su_bloqueo():
    host, mazmorra = _host(impostor=0)
    assert host.puede_navegar(0) is False
    _pasar(host, mazmorra, ESPERA)
    assert host.puede_navegar(0) is True
    assert host.puede_navegar(0) is True  # elegir no gasta nada
    assert host.puede_navegar(1) is True


def test_con_la_terminal_de_main_el_bloqueo_corre_desde_el_primer_frame():
    """El frame en que Main pasa a la terminal, el adaptador todavía vio la
    mazmorra: sin la terminal de Main, una tecla del host impostor se colaba."""
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1])
    host.sabotaje = Sabotaje(ESPERA, ESPERA)
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[0].es_impostor = True
    host._preparar_frame(SimpleNamespace(), None, jugadores)
    host._seguir_sabotaje(Escena.MAZMORRA, None, 0.016)
    mazmorra = _mazmorra_en_decision()
    assert host.puede_navegar(0, mazmorra.cuarto.terminal) is False
    assert host.restante_sabotaje() == ESPERA
    _pasar(host, mazmorra, 0.5)  # el mismo frame, ya en DECISION: no se vuelve a sortear
    assert host.restante_sabotaje() == pytest.approx(ESPERA - 0.5)
    assert host.puede_navegar(1, mazmorra.cuarto.terminal) is True  # el tripulante, libre


def test_la_terminal_de_la_siguiente_mazmorra_vuelve_a_bloquear():
    host, mazmorra = _host(impostor=1)
    _pasar(host, mazmorra, ESPERA)
    assert _nav(host, DERECHA) == [DERECHA]
    host._seguir_sabotaje(Escena.RESULTADO, None, 1.0)  # resultado y vuelta a la ciudad
    otra = _mazmorra_en_decision()
    host._seguir_sabotaje(Escena.DECISION, otra, 0.0)
    assert _nav(host, DERECHA) == []
    assert host.restante_sabotaje() == ESPERA


def test_sin_impostor_nadie_tiene_limite():
    host, _ = _host(impostor=None)
    assert _nav(host, DERECHA) == [DERECHA]
    assert host.puede_navegar(0) and host.puede_navegar(1)


def test_fuera_de_la_terminal_el_impostor_navega_libre():
    """La investigación del capítulo 3 también usa DECISION_NAV: ahí no hay sabotaje."""
    host, mazmorra = _host(impostor=1)
    host._seguir_sabotaje(Escena.RESULTADO, None, 0.1)
    assert host.restante_sabotaje() is None and host.espera_sabotaje() is None
    assert _nav(host, DERECHA) == [DERECHA]


def test_una_confirmacion_rechazada_no_carga_al_impostor_con_la_decision():
    host, _ = _host(impostor=1)
    campania = SimpleNamespace(puede_decidir=lambda i: True, actores=[])
    campania.registrar_actor = campania.actores.append
    host._partida = SimpleNamespace(campania=campania)
    assert _nav(host, CONFIRMAR) == []
    assert campania.actores == [] and host.ultimo_actor == 0


def test_el_estado_lleva_el_bloqueo_con_la_terminal():
    host, mazmorra = _host(impostor=1)
    _pasar(host, mazmorra, 4.0)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0), _reinicios_red=0, _historial_red=[],
                              campania=SimpleNamespace(resumen_red=lambda: {}))
    mazmorra.cuarto.fase = None
    estado = host.estado_completo(Escena.DECISION, None, _mazmorra_completa(mazmorra), partida, host._jugadores)
    assert estado["term"]["sab"] == pytest.approx(ESPERA - 4.0)
    assert estado["term"]["sabt"] == ESPERA
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


def test_el_invitado_refleja_bloqueo_y_lectores_del_host():
    invitado = AdaptadorOnlineJoin(_ClienteFalso(), id_local=1, ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[1].es_impostor = True
    invitado._preparar_frame(SimpleNamespace(), None, jugadores)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0),
                              campania=SimpleNamespace(aplicar_resumen_red=lambda datos: None))
    invitado._aplicar({"term": {"sab": 6.5, "sabt": 13.25}, "leen": [0, 1, "x"]},
                      Escena.DECISION, None, None, partida, jugadores)
    assert invitado.restante_sabotaje() == 6.5 and invitado.espera_sabotaje() == 13.25
    assert invitado.puede_navegar(1) is False  # él es el impostor y sigue bloqueado
    assert invitado.puede_navegar(0) is True
    assert invitado.esperando_lectura() == [0]  # él mismo no cuenta
    for _ in range(3):  # habilitado: el host sigue mandando 0 y él sigue eligiendo
        invitado._aplicar({"term": {"sab": 0, "sabt": 13.25}}, Escena.DECISION, None, None, partida, jugadores)
        assert invitado.puede_navegar(1) is True and invitado.esperando_lectura() == []
    invitado._aplicar({}, Escena.MAZMORRA, None, None, partida, jugadores)
    assert invitado.restante_sabotaje() is None and invitado.espera_sabotaje() is None
    assert invitado.puede_navegar(1) is True


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


def test_por_red_el_host_frena_al_invitado_impostor_y_despues_lo_deja_elegir():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.id_jugador == 1)
        host = AdaptadorOnlineHost(servidor, ids_red=[0, 1])
        host.sabotaje = Sabotaje(ESPERA, ESPERA)
        jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
        jugadores[1].es_impostor = True
        host._preparar_frame(SimpleNamespace(), None, jugadores)
        mazmorra = _mazmorra_en_decision()
        host._seguir_sabotaje(Escena.DECISION, mazmorra, 0.0)

        cliente.enviar_decision_nav(DERECHA)  # bloqueado: no vale
        cliente.enviar_historia(LECTURA, ocupado=True)
        recibidos = []

        def procesado():
            host._procesar_mensajes()
            recibidos.extend(host._solicitudes_decision)
            host._solicitudes_decision.clear()
            return host.esperando_lectura() == [1]

        assert _esperar(procesado)
        assert recibidos == []
        host._seguir_sabotaje(Escena.DECISION, mazmorra, ESPERA)
        for direccion in (DERECHA, IZQUIERDA, DERECHA, CONFIRMAR):  # habilitado: todas valen
            cliente.enviar_decision_nav(direccion)
        assert _esperar(lambda: procesado() and recibidos == [DERECHA, IZQUIERDA, DERECHA, CONFIRMAR])
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# Lo que ve el impostor
# ----------------------------------------------------------------------

def test_textos_del_indicador():
    assert sabotaje_render.texto_sabotaje(0) == assets.TEXTO_SABOTAJE_LISTO
    assert sabotaje_render.texto_sabotaje(11.2) == "Se habilita en 12 s"
    assert sabotaje_render.texto_sabotaje(11.2, aviso=0.3) == "Aún no: faltan 12 s"


def test_los_textos_caben_en_el_indicador():
    pygame.font.init()
    ancho = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE).width - 32
    fuente = dibujo.fuente(assets.TAMANIO_FUENTE_NORMAL, True)
    for restante, aviso in ((0, 0), (COOLDOWN_SABOTAJE_MAX, 0), (COOLDOWN_SABOTAJE_MAX, 0.3)):
        assert fuente.size(sabotaje_render.texto_sabotaje(restante, aviso))[0] <= ancho


@pytest.mark.parametrize("restante, espera, lleno", [
    (ESPERA, ESPERA, 0.0),
    (ESPERA / 2, ESPERA, 0.5),
    (0.0, ESPERA, 1.0),
    (COOLDOWN_SABOTAJE_MAX / 2, None, 0.5),  # sin el total del host: sobre el máximo
    (0.0, 0.0, 1.0),  # sin bloqueo
])
def test_el_indicador_se_dibuja_con_su_barra(restante, espera, lleno):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    sabotaje_render.dibujar_sabotaje(pantalla, restante, espera=espera)
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    barra_y = rect.bottom - 10
    rojos = [x for x in range(rect.left + 16, rect.right - 16)
             if pantalla.get_at((x, barra_y))[:3] == assets.COLOR_IMPOSTOR]
    assert len(rojos) / (rect.width - 32) == pytest.approx(lleno, abs=0.03)
