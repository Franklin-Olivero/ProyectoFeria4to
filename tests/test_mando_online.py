"""Modo Online con el control de PS4 (Online/mando_online.py): las pantallas
del Online (crear o unirse, código, error y sala de espera), caminar por la
ciudad con el stick, el control conectado a mitad de partida y las pantallas
de resultado. Con eventos simulados: aquí no hay un control de verdad."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from Online import lobby, mando_online, sesion_red  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from tests.test_presentacion_online import _Fin, _Reloj, correr  # noqa: E402,F401


def _boton(boton):
    pygame.event.post(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=boton, instance_id=0))


def _stick(eje, valor):
    return pygame.event.Event(pygame.CONTROLLERAXISMOTION, axis=eje, value=valor, instance_id=0)


@pytest.fixture
def pantalla():
    pygame.init()
    superficie = pygame.display.set_mode((1280, 720))
    pygame.event.clear()
    return superficie


def _correr(funcion, guion, *args, maximo=60):
    """Corre una pantalla del lobby; `guion(n)` postea eventos en el cuadro n."""
    cuadros = {"n": 0}

    def presentar():
        cuadros["n"] += 1
        guion(cuadros["n"])
        if cuadros["n"] >= maximo:
            raise _Fin

    try:
        return funcion(args[0], _Reloj(), presentar, *args[1:])
    except _Fin:
        return "siguió"


# ----------------------------------------------------------------------
# Traducción de botones a teclas
# ----------------------------------------------------------------------

def test_cada_boton_es_su_tecla():
    evento = pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_A, instance_id=0)
    assert mando_online.como_tecla(evento).key == pygame.K_RETURN
    assert mando_online.como_tecla(evento, mando_online.SALA).key == pygame.K_e  # en la sala, ✕ interactúa
    otro = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
    assert mando_online.como_tecla(otro) is otro


def test_el_stick_es_una_flecha_por_inclinacion():
    mando_online._stick.clear()
    eje = pygame.CONTROLLER_AXIS_LEFTX
    assert mando_online.como_tecla(_stick(eje, 30000)).key == pygame.K_RIGHT
    assert mando_online.como_tecla(_stick(eje, 31000)).type == pygame.CONTROLLERAXISMOTION  # sigue inclinado: nada
    assert mando_online.como_tecla(_stick(eje, 0)).type == pygame.CONTROLLERAXISMOTION
    assert mando_online.como_tecla(_stick(eje, -30000)).key == pygame.K_LEFT


def test_sin_control_la_direccion_es_cero(monkeypatch):
    monkeypatch.setattr(mando_online, "mando", lambda: None)
    assert mando_online.direccion() == (0.0, 0.0)


class _MandoFalso:
    def __init__(self, ejes=None, botones=()):
        self.ejes, self.botones = ejes or {}, set(botones)

    def attached(self):
        return True

    def get_axis(self, eje):
        return self.ejes.get(eje, 0)

    def get_button(self, boton):
        return boton in self.botones


def test_la_direccion_suma_stick_y_cruceta(monkeypatch):
    falso = _MandoFalso({pygame.CONTROLLER_AXIS_LEFTX: 32767, pygame.CONTROLLER_AXIS_LEFTY: 3000},
                        {pygame.CONTROLLER_BUTTON_DPAD_UP})
    monkeypatch.setattr(mando_online, "mando", lambda: falso)
    assert mando_online.direccion() == (1.0, -1.0)  # el 3000 del eje Y es zona muerta; manda la cruceta


# ----------------------------------------------------------------------
# Pantallas del Online
# ----------------------------------------------------------------------

def test_elegir_unirse_con_la_cruceta_y_la_x(pantalla):
    def guion(n):
        if n == 2:
            _boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
            _boton(pygame.CONTROLLER_BUTTON_A)

    assert _correr(lobby.pantalla_elegir_modo_online, guion, pantalla) == "join"


def test_o_vuelve_de_elegir_modo(pantalla):
    assert _correr(lobby.pantalla_elegir_modo_online,
                   lambda n: n == 2 and _boton(pygame.CONTROLLER_BUTTON_B), pantalla) == "volver"


def test_el_codigo_se_escribe_con_el_control(pantalla):
    def guion(n):
        if n == 2:
            for boton in (pygame.CONTROLLER_BUTTON_DPAD_DOWN, pygame.CONTROLLER_BUTTON_DPAD_DOWN,
                          pygame.CONTROLLER_BUTTON_A,  # C
                          pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_A,  # B
                          pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_Y,  # B y se borra
                          pygame.CONTROLLER_BUTTON_DPAD_RIGHT,  # → también agrega: B
                          pygame.CONTROLLER_BUTTON_START):
                _boton(boton)

    assert _correr(lobby._pantalla_ingresar_ip, guion, pantalla) == "CBB"


def test_el_error_se_cierra_con_la_x(pantalla):
    assert _correr(lobby._pantalla_error, lambda n: n == 2 and _boton(pygame.CONTROLLER_BUTTON_A),
                   pantalla, "falló") == "volver"


def test_en_la_sala_la_x_abre_la_recepcion_y_la_cruceta_elige_rol(pantalla):
    servidor = Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    vistos = {}
    try:
        def guion(n):
            if n == 3:
                _boton(pygame.CONTROLLER_BUTTON_A)  # lejos de los vestidores: la recepción (roles)
            if n == 5:
                _boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
            if n == 7:
                vistos["rol"] = servidor.sala.rol_de(0)
                _boton(pygame.CONTROLLER_BUTTON_B)  # cierra la recepción
                _boton(pygame.CONTROLLER_BUTTON_B)  # y no sale de la sala

        resultado = _correr(lobby.pantalla_sala_espera, guion, pantalla, [None] * 4, True, servidor, "127.0.0.1",
                            maximo=12)
        assert resultado == "siguió"
        assert vistos["rol"] == lobby.ROLES[1]  # Influencer: el siguiente al Ciudadano
    finally:
        servidor.detener()


# ----------------------------------------------------------------------
# La partida
# ----------------------------------------------------------------------

def test_en_la_ciudad_se_camina_con_el_stick_del_control_local():
    entrada = sesion_red.EntradaTecladoRed()
    entrada.mando, entrada._mando_lector = _MandoFalso(), object()
    sesion = type("S", (), {"adaptador_red": object(), "entradas": [entrada]})()
    assert sesion_red.mando_local_online(sesion) is entrada.mando
    local = type("S", (), {"adaptador_red": None, "entradas": [entrada]})()
    assert sesion_red.mando_local_online(local) is None  # en local el control es del J2


def test_el_control_se_puede_conectar_a_mitad_de_partida(monkeypatch):
    entrada = sesion_red.EntradaTecladoRed()
    entrada.mando, entrada._mando_lector = sesion_red._MandoFicticio(), None
    falso = _MandoFalso()
    monkeypatch.setattr(sesion_red, "_detectar_mando", lambda: falso)
    for _ in range(sesion_red.CUADROS_ENTRE_BUSQUEDAS_DE_MANDO):
        sesion_red._revisar_mando(entrada)
    assert entrada.mando is falso and entrada._mando_lector is not None
    falso.attached = lambda: False  # se desconectó: leer() sigue con el teclado y se busca otro
    otro = _MandoFalso()
    monkeypatch.setattr(sesion_red, "_detectar_mando", lambda: otro)
    for _ in range(sesion_red.CUADROS_ENTRE_BUSQUEDAS_DE_MANDO):
        sesion_red._revisar_mando(entrada)
    assert entrada.mando is otro


def test_las_pantallas_de_resultado_se_pasan_con_la_x():
    assert Escena.RESULTADO in mando_online.ESCENAS_TECLA_DE_BOTON_ONLINE
    assert mando_online.tecla_de_boton_online(pygame.CONTROLLER_BUTTON_A).key == pygame.K_RETURN
    assert mando_online.tecla_de_boton_online(pygame.CONTROLLER_BUTTON_DPAD_RIGHT).key == pygame.K_RIGHT
    assert mando_online.tecla_de_boton_online(pygame.CONTROLLER_BUTTON_B) is None  # Esc cerraría el juego



# ----------------------------------------------------------------------
# Ningún botón del control cierra la partida (el bug de la ✕ en la ciudad)
# ----------------------------------------------------------------------

BOTONES = (
    pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_X, pygame.CONTROLLER_BUTTON_Y,
    pygame.CONTROLLER_BUTTON_BACK, pygame.CONTROLLER_BUTTON_GUIDE, pygame.CONTROLLER_BUTTON_LEFTSTICK,
    pygame.CONTROLLER_BUTTON_RIGHTSTICK, pygame.CONTROLLER_BUTTON_LEFTSHOULDER, pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_DPAD_DOWN, pygame.CONTROLLER_BUTTON_DPAD_LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
)
EJES = (pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY, pygame.CONTROLLER_AXIS_RIGHTX,
        pygame.CONTROLLER_AXIS_RIGHTY, pygame.CONTROLLER_AXIS_TRIGGERLEFT, pygame.CONTROLLER_AXIS_TRIGGERRIGHT)


@pytest.fixture
def errores(monkeypatch):
    """Todo lo que el Online atrapa y anota (si algo falla, la partida se cerraba)."""
    from Online import registro_errores
    anotados = []
    monkeypatch.setattr(registro_errores, "registrar", lambda contexto, error=None: anotados.append(contexto))
    return anotados


def _apretar_todo(boton_inicial):
    """Cada botón (salvo START: la pausa tiene su propia prueba) y cada eje, desde `boton_inicial`."""
    for boton in BOTONES[boton_inicial:]:
        pygame.event.post(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=boton, instance_id=0))
        pygame.event.post(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=boton, instance_id=0))
    for eje in EJES:
        for valor in (32767, -32768, 0):
            pygame.event.post(_stick(eje, valor))


@pytest.mark.parametrize("espejo", [False, True], ids=["host", "invitado"])
@pytest.mark.parametrize("lugar", ["ciudad", "mazmorra", "terminal"])
def test_ningun_boton_del_control_cierra_la_partida(correr, errores, lugar, espejo):
    from Online.servidor import Servidor as _Servidor
    from tests.test_reunion_online import _RedReunion, _impostor_j2
    servidor = _Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    try:
        red = _RedReunion(cuando=10_000 if lugar == "ciudad" else 3, espejo=espejo, en_decision=lugar == "terminal")
        red.servidor = servidor  # con celular
        vistos = {}

        def guion(n, loc):
            if n in (8, 14, 20, 26):  # varias veces: con el celular abierto, en sus pestañas, cerrado...
                _apretar_todo(0)
            if n == 32:
                vistos["llego"] = True
                return True
            return False

        _, cuadros = correr(red, guion, id_local=1 if espejo else 0, preparar=_impostor_j2)
        assert vistos.get("llego"), f"la partida terminó en el cuadro {cuadros}"
        assert not [e for e in errores if e.startswith("Main._jugar")], errores
        assert not [e for e in errores if "Celular" in e or "celular" in e], errores
    finally:
        servidor.detener()


def test_x_en_la_ciudad_entra_como_la_e(correr, errores):
    """El bug: ✕ frente a una puerta cerraba la partida. Ahora entra, como la E."""
    from src.dungeon import ciudad_mapa
    from tests.test_reunion_online import _RedReunion, _impostor_j2
    red = _RedReunion(cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            loc["jugador"].colocar_en(ciudad_mapa.centro_casilla(*ciudad_mapa.ENTRADAS["Colegio"]))
            _boton(pygame.CONTROLLER_BUTTON_A)
        if n == 8:
            vistos["escena"] = loc["escena"]
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert not [e for e in errores if e.startswith("Main._jugar")], errores
    assert vistos["escena"] == Escena.MAZMORRA


def test_ningun_boton_cierra_la_sala_de_espera(pantalla, errores):
    servidor = Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    try:
        def guion(n):
            if n in (3, 9, 15):
                _apretar_todo(0)

        resultado = _correr(lobby.pantalla_sala_espera, guion, pantalla, [None] * 4, True, servidor, "127.0.0.1",
                            maximo=22)
        assert resultado == "siguió"  # ningún botón saca de la sala ni la cierra
        assert not errores, errores
    finally:
        servidor.detener()


def test_la_pausa_con_el_control_no_rompe_nada(correr, errores):
    """START abre la pausa; con todos los botones adentro puede elegirse "Salir al
    menú" (eso sí vale), pero nada debe fallar."""
    from tests.test_reunion_online import _RedReunion, _impostor_j2

    def guion(n, loc):
        if n == 4:
            _boton(pygame.CONTROLLER_BUTTON_START)
        if n in (6, 10):
            _apretar_todo(0)
        return n >= 16

    correr(_RedReunion(cuando=10_000, espejo=False), guion, id_local=0, preparar=_impostor_j2)
    assert not [e for e in errores if e.startswith("Main._jugar")], errores
