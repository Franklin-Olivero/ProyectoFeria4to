"""Online, en el loop real de Main._jugar: lo que pasa cuando la red cambia
de escena. La presentación del capítulo sale en TODAS las PCs (antes solo en
la que apretó E), el mundo espera a quien sigue leyendo en otra PC y el
impostor no mueve la terminal durante su bloqueo y después elige normal.

Una "red" falsa hace de adaptador: lleva a esta PC a una mazmorra igual que
cuando entra el host o lo pide un invitado. Se corta el loop desde
presentar() con una excepción que proteger_partida_online no atrapa."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.entrada import EntradaTeclado  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.core.preferencias import Preferencias  # noqa: E402
from src.dungeon import ciudad_mapa  # noqa: E402
from src.dungeon.cuarto import FASE_DECISION  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.mazmorra_jugable import MazmorraJugable  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.story.cinematica import Cinematica  # noqa: E402
from src.ui.terminal_decision import TerminalDecision, construir_arbol_publicacion  # noqa: E402

ZONA = "Colegio"


class _Fin(BaseException):
    """Corta Main._jugar: proteger_partida_online atrapa Exception, no esto."""


class _Reloj:
    def tick_busy_loop(self, _fps=0):
        return 16

    tick = tick_busy_loop


def _locales():
    """Variables locales del loop de Main._jugar (como tools/recorrido_campania.py)."""
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_code.co_name == "_jugar" and "partida" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return None


class _Red:
    """Adaptador de red falso. En el frame `cuando` lleva a esta PC a la
    mazmorra `zona` (o a su terminal si `en_decision`). Con `espejo` hace de
    invitado: Main lo reconoce porque tiene enviar_decision_nav."""

    def __init__(self, cuando=5, espejo=True, en_decision=False):
        self.cuando = cuando
        self.en_decision = en_decision
        self.frames = 0
        self.lectores = []
        self.permitir = True
        self.restante = None
        self.espera = None
        self.navegaciones = []
        self.mazmorra = None
        if espejo:
            self.enviar_decision_nav = self.navegaciones.append

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        self.frames += 1
        if self.frames == self.cuando:
            partida.entrar(ZONA)
            self.mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes(ZONA), ZONA, semilla=7),
                                            fabrica_arbol=partida.fabrica_arbol(ZONA))
            self.mazmorra.colocar_en_entrada(jugadores)
            if self.en_decision:
                terminal = TerminalDecision(construir_arbol_publicacion(), duracion=45.0)
                terminal.iniciar()
                self.mazmorra.cuarto.terminal = terminal
                self.mazmorra.cuarto.fase = FASE_DECISION
                return Escena.DECISION, None, self.mazmorra, 0.0
            return Escena.MAZMORRA, None, self.mazmorra, assets.DURACION_FUNDIDO
        return escena, arena, mazmorra, fundido

    def actualizar_ciudad(self, dt, partida, jugadores, jugador):
        pass

    def esperando_lectura(self):
        return list(self.lectores)

    def puede_navegar(self, indice, terminal=None):
        return self.permitir

    def restante_sabotaje(self):
        return self.restante

    def espera_sabotaje(self):
        return self.espera


@pytest.fixture
def correr(monkeypatch):
    """correr(red, guion, id_local=1): corre Main._jugar con 2 jugadores
    hasta que `guion(n, locales)` retorne True (n = cuadro presentado)."""
    import Main

    pygame.font.init()
    pantalla = pygame.display.set_mode((1280, 720))

    def ejecutar(red, guion, id_local=1, maximo=400, preparar=None):
        partida = Partida()
        partida.campania.prologo_visto = True  # sin la intro de 40 s
        sesion = Main._Sesion(partida, [Ciudadano(0, 0), Candidato(0, 0)], [EntradaTeclado(), EntradaTeclado()])
        sesion.adaptador_red = red
        sesion.id_local = id_local
        if preparar is not None:
            preparar(sesion)
        pygame.event.clear()
        cuadros = {"n": 0}

        def presentar():
            cuadros["n"] += 1
            if guion(cuadros["n"], _locales()) or cuadros["n"] >= maximo:
                raise _Fin

        try:
            Main._jugar(pantalla, _Reloj(), sesion, Preferencias(), presentar)
        except _Fin:
            pass
        return sesion, cuadros["n"]

    return ejecutar


def _tecla(tecla):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=0, unicode=""))


def _boton(boton):
    pygame.event.post(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=boton, instance_id=0))


# ----------------------------------------------------------------------
# El bug: la presentación del capítulo solo salía en el host
# ----------------------------------------------------------------------

@pytest.mark.parametrize("espejo", [True, False], ids=["invitado al que trae el host", "host al que lo pide un invitado"])
def test_la_presentacion_del_capitulo_sale_aunque_entre_otro(correr, espejo):
    vistos = {}

    def guion(n, loc):
        if n == 3:
            vistos["antes"] = (loc["escena"], loc["dialogo"])
        if n == 8:
            vistos["despues"] = (loc["escena"], loc["dialogo"], list(loc["cola_historia"]))
            return True
        return False

    sesion, _ = correr(_Red(cuando=5, espejo=espejo), guion, id_local=1 if espejo else 0)
    assert vistos["antes"] == (Escena.CIUDAD, None)
    escena, dialogo, cola = vistos["despues"]
    assert escena == Escena.MAZMORRA
    assert isinstance(dialogo, Cinematica)  # la tarjeta del capítulo...
    assert len(cola) == 1 and not isinstance(cola[0], Cinematica)  # ...y luego su diálogo
    assert ZONA in sesion.partida.campania.intros_vistas


def test_con_la_e_propia_sale_una_sola_vez(correr):
    """La E encola la presentación y la red no la vuelve a encolar."""
    vistos = {}
    col, fila = ciudad_mapa.ENTRADAS[ZONA]
    x, y = ciudad_mapa.centro_casilla(col, fila)

    def guion(n, loc):
        if n == 2:
            loc["jugador"].colocar_en((x, y + 8))
        if n == 3:
            _tecla(pygame.K_e)
        if n == 10:
            vistos["fin"] = (loc["escena"], loc["dialogo"], list(loc["cola_historia"]))
            return True
        return False

    correr(_Red(cuando=10 ** 6, espejo=False), guion, id_local=0)
    escena, dialogo, cola = vistos["fin"]
    assert escena == Escena.MAZMORRA and isinstance(dialogo, Cinematica) and len(cola) == 1


def test_una_zona_ya_presentada_no_se_repite(correr):
    vistos = {}

    def guion(n, loc):
        if n == 8:
            vistos["dialogo"] = loc["dialogo"]
            return True
        return False

    correr(_Red(cuando=5), guion, preparar=lambda s: s.partida.campania.intros_vistas.add(ZONA))
    assert vistos["dialogo"] is None


# ----------------------------------------------------------------------
# El mundo espera a quien sigue leyendo en otra PC
# ----------------------------------------------------------------------

def test_en_combate_el_mundo_espera_a_quien_lee(correr, monkeypatch):
    import Main

    combate = []
    original = Main._frame_de_combate
    monkeypatch.setattr(Main, "_frame_de_combate", lambda *a, **k: combate.append(1) or original(*a, **k))
    red = _Red(cuando=3)
    red.lectores = [0]  # el host sigue leyendo
    vistos = {}

    def guion(n, loc):
        if n == 15:
            vistos["leyendo"] = (len(combate), loc["espera_equipo"])
            red.lectores = []  # terminó de leer
        if n == 25:
            return True
        return False

    correr(red, guion, preparar=lambda s: s.partida.campania.intros_vistas.add(ZONA))
    assert vistos["leyendo"] == (0, True)  # mientras leía, ni un frame de combate
    assert len(combate) > 0  # después, el combate sigue


def test_en_la_ciudad_nadie_espera(correr, monkeypatch):
    red = _Red(cuando=10 ** 6)
    red.lectores = [0]
    vistos = {}

    def guion(n, loc):
        if n == 6:
            vistos["espera"] = loc["espera_equipo"]
            return True
        return False

    correr(red, guion)
    assert vistos["espera"] is False


def test_el_aviso_dice_a_quien_se_espera():
    import Main

    assert Main._texto_espera_lectura([0]) == "Esperando a que J1 termine de leer"
    assert Main._texto_espera_lectura([0, 2]) == "Esperando a que J1 y J3 terminen de leer"


# ----------------------------------------------------------------------
# El impostor en la terminal
# ----------------------------------------------------------------------

@pytest.mark.parametrize("espejo", [True, False], ids=["invitado impostor", "host impostor"])
def test_el_impostor_no_mueve_la_terminal_hasta_que_termine_su_bloqueo(correr, espejo):
    red = _Red(cuando=3, espejo=espejo, en_decision=True)
    red.permitir, red.restante, red.espera = False, 9.0, 18.0
    vistos = {}

    def guion(n, loc):
        if n == 5:
            _tecla(pygame.K_RIGHT)
        if n == 7:
            vistos["bloqueado"] = (red.mazmorra.cuarto.terminal.indice_seleccionado, list(red.navegaciones),
                                   loc["aviso_sabotaje"] > 0)
            vistos["indicador"] = pygame.display.get_surface().copy()
            red.permitir, red.restante = True, 0.0
            _tecla(pygame.K_RIGHT)
        if n == 9:
            vistos["habilitado"] = (red.mazmorra.cuarto.terminal.indice_seleccionado, list(red.navegaciones))
            _tecla(pygame.K_LEFT)  # habilitado: sigue eligiendo normal
        if n == 11:
            vistos["otra_vez"] = (red.mazmorra.cuarto.terminal.indice_seleccionado, list(red.navegaciones))
            return True
        return False

    def impostor_local(sesion):
        sesion.jugadores[sesion.id_local].es_impostor = True

    correr(red, guion, id_local=1 if espejo else 0, preparar=impostor_local)
    assert vistos["bloqueado"] == (0, [], True)
    assert vistos["habilitado"][0] == 1
    assert vistos["otra_vez"][0] == 0
    if espejo:
        assert vistos["habilitado"][1] == ["derecha"]  # al host le llega el sabotaje
        assert vistos["otra_vez"][1] == ["derecha", "izquierda"]
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    rojos = sum(vistos["indicador"].get_at((x, y))[:3] == assets.COLOR_IMPOSTOR
                for x in range(rect.left, rect.right, 2) for y in range(rect.top, rect.bottom, 2))
    assert rojos > 20  # el indicador se ve
    # La barra se llena sobre el bloqueo que sorteó el host: 9 de 18 s = la mitad.
    barra = [vistos["indicador"].get_at((x, rect.bottom - 10))[:3] == assets.COLOR_IMPOSTOR
             for x in range(rect.left + 16, rect.right - 16)]
    assert sum(barra) / len(barra) == pytest.approx(0.5, abs=0.05)


@pytest.mark.parametrize("espejo", [True, False], ids=["invitado impostor", "host impostor"])
def test_el_control_pasa_por_el_mismo_bloqueo_que_el_teclado(correr, espejo):
    """Antes el control movía la terminal sin preguntar por el bloqueo (y en
    el invitado no le llegaba nada al host)."""
    red = _Red(cuando=3, espejo=espejo, en_decision=True)
    red.permitir, red.restante = False, 9.0
    vistos = {}

    def guion(n, loc):
        if n == 5:
            _boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
            _boton(pygame.CONTROLLER_BUTTON_A)
        if n == 7:
            terminal = red.mazmorra.cuarto.terminal
            vistos["bloqueado"] = (terminal.indice_seleccionado, terminal.nodo_actual is terminal.arbol.raiz,
                                   list(red.navegaciones), loc["aviso_sabotaje"] > 0)
            red.permitir, red.restante = True, 0.0
            _boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
        if n == 9:
            vistos["habilitado"] = (red.mazmorra.cuarto.terminal.indice_seleccionado, list(red.navegaciones))
            return True
        return False

    def impostor_local(sesion):
        sesion.jugadores[sesion.id_local].es_impostor = True

    correr(red, guion, id_local=1 if espejo else 0, preparar=impostor_local)
    assert vistos["bloqueado"] == (0, True, [], True)
    assert vistos["habilitado"][0] == 1
    if espejo:
        assert vistos["habilitado"][1] == ["derecha"]  # ahora el control del invitado llega al host


def test_un_tripulante_no_ve_el_indicador_del_bloqueo(correr):
    red = _Red(cuando=3, en_decision=True)
    red.restante = 9.0
    vistos = {}

    def guion(n, loc):
        if n == 6:
            vistos["pantalla"] = pygame.display.get_surface().copy()
            return True
        return False

    correr(red, guion)
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    rojos = sum(vistos["pantalla"].get_at((x, y))[:3] == assets.COLOR_IMPOSTOR
                for x in range(rect.left, rect.right, 2) for y in range(rect.top, rect.bottom, 2))
    assert rojos == 0
