"""El control de PS4 en las pantallas del modo Online (crear o unirse, código,
error y sala de espera).

Esas pantallas se escribieron para teclado y ratón. En vez de duplicar su
lógica, cada botón del control se traduce a la tecla que ya hace lo mismo
(`como_tecla`): ✕ confirma (Enter) o interactúa (E en la sala), ○ vuelve
(Esc), la cruceta y el stick izquierdo son las flechas, START inicia. Para
caminar por la sala, `direccion()` suma el stick y la cruceta a WASD.

El teclado y el ratón siguen funcionando igual: se puede jugar con los dos a
la vez. El control se abre solo (también si se conecta después) con la API
GameController de SDL, la misma que usa el resto del juego.
"""

import pygame

from Online import registro_errores

ZONA_MUERTA = 0.35  # fracción del recorrido del stick que no cuenta (el DualShock nunca vuelve justo a 0)
UMBRAL_STICK_MENU = 0.6  # el stick como flecha: una pulsación cada vez que se inclina más que esto
EJE_MAXIMO = 32767

# Traducción botón -> tecla de cada pantalla.
MENU = {  # elegir crear/unirse y la pantalla de error
    pygame.CONTROLLER_BUTTON_A: pygame.K_RETURN,
    pygame.CONTROLLER_BUTTON_START: pygame.K_RETURN,
    pygame.CONTROLLER_BUTTON_B: pygame.K_ESCAPE,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: pygame.K_LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: pygame.K_RIGHT,
    pygame.CONTROLLER_BUTTON_DPAD_UP: pygame.K_UP,
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: pygame.K_DOWN,
}
SALA = {  # sala de espera: ✕ interactúa (vestidor / recepción), START inicia (host)
    pygame.CONTROLLER_BUTTON_A: pygame.K_e,
    pygame.CONTROLLER_BUTTON_START: pygame.K_RETURN,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: pygame.K_LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: pygame.K_RIGHT,
}

# Barras de controles cuando hay un control conectado.
CONTROLES_MENU = [("Cruceta / stick", "elegir"), ("✕", "confirmar"), ("○", "volver")]
CONTROLES_ERROR = [("✕ / ○", "volver")]
CONTROLES_CODIGO = [("↑ ↓", "letra"), ("✕ / →", "agregar"), ("△ / ←", "borrar"), ("START", "conectar"),
                    ("○", "volver")]
CONTROLES_SALA = [("Stick / cruceta", "caminar"), ("✕", "vestidor / rol"), ("START", "iniciar"),
                  ("Share", "celular"), ("○", "cerrar")]

_mando = None  # el control abierto (o None)
_stick = {}  # eje -> -1, 0 o 1: hacia dónde está inclinado (para no repetir la flecha)


def mando():
    """El control conectado, abierto (None si no hay). Si se desconectó, lo
    olvida; si se conecta uno, lo abre. Nunca lanza."""
    global _mando
    try:
        if _mando is not None and not _mando.attached():
            _mando = None
        if _mando is None:
            from pygame._sdl2 import controller
            if not controller.get_init():
                controller.init()
            for indice in range(controller.get_count()):
                if controller.is_controller(indice):
                    _mando = controller.Controller(indice)
                    break
    except Exception:  # noqa: BLE001 - sin control se juega con el teclado
        registro_errores.registrar("mando_online.mando")
        _mando = None
    return _mando


def hay_mando():
    return mando() is not None


def _eje(nombre):
    actual = mando()
    if actual is None:
        return 0.0
    try:
        return actual.get_axis(nombre) / EJE_MAXIMO
    except Exception:  # noqa: BLE001
        return 0.0


def _boton(nombre):
    actual = mando()
    try:
        return bool(actual is not None and actual.get_button(nombre))
    except Exception:  # noqa: BLE001
        return False


def direccion():
    """(dx, dy) de -1 a 1 del stick izquierdo (con zona muerta) o la cruceta, para caminar."""
    dx, dy = _eje(pygame.CONTROLLER_AXIS_LEFTX), _eje(pygame.CONTROLLER_AXIS_LEFTY)
    dx = dx if abs(dx) > ZONA_MUERTA else 0.0
    dy = dy if abs(dy) > ZONA_MUERTA else 0.0
    if _boton(pygame.CONTROLLER_BUTTON_DPAD_LEFT):
        dx = -1.0
    elif _boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT):
        dx = 1.0
    if _boton(pygame.CONTROLLER_BUTTON_DPAD_UP):
        dy = -1.0
    elif _boton(pygame.CONTROLLER_BUTTON_DPAD_DOWN):
        dy = 1.0
    return dx, dy


def _tecla(tecla):
    return pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=0, unicode="", scancode=0)


def como_tecla(evento, tabla=MENU, stick_como_flechas=True):
    """El evento del control como la tecla equivalente de `tabla` (un
    KEYDOWN), o el mismo evento si no es del control o no tiene traducción.
    El stick izquierdo inclinado da una flecha por inclinación (si
    `stick_como_flechas`). Conectar o desconectar el control lo abre u olvida."""
    if evento.type in (pygame.CONTROLLERDEVICEADDED, pygame.CONTROLLERDEVICEREMOVED):
        mando()
        return evento
    if evento.type == pygame.CONTROLLERBUTTONDOWN and evento.button in tabla:
        return _tecla(tabla[evento.button])
    if stick_como_flechas and evento.type == pygame.CONTROLLERAXISMOTION \
            and evento.axis in (pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY):
        valor = evento.value / EJE_MAXIMO
        lado = 1 if valor > UMBRAL_STICK_MENU else -1 if valor < -UMBRAL_STICK_MENU else 0
        if lado == _stick.get(evento.axis, 0):
            return evento
        _stick[evento.axis] = lado
        if lado == 0:
            return evento
        if evento.axis == pygame.CONTROLLER_AXIS_LEFTX:
            return _tecla(pygame.K_RIGHT if lado > 0 else pygame.K_LEFT)
        return _tecla(pygame.K_DOWN if lado > 0 else pygame.K_UP)
    return evento


# --- La partida: pantallas que solo esperan teclas ----------------------
# El resultado de una mazmorra (y la investigación del capítulo 3), la
# victoria y la derrota se pasan con Enter y flechas. En el Online, quien
# juega solo con el control las pasa con ✕ y la cruceta (Main.py postea la
# tecla). ○ NO se traduce a Esc: en la victoria Esc cierra el juego.
def _escenas_tecla_de_boton():
    from src.core.escenas import Escena
    return (Escena.RESULTADO, Escena.VICTORIA, Escena.DERROTA)


ESCENAS_TECLA_DE_BOTON_ONLINE = _escenas_tecla_de_boton()
TECLA_DE_BOTON_PARTIDA = {
    pygame.CONTROLLER_BUTTON_A: pygame.K_RETURN,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: pygame.K_LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: pygame.K_RIGHT,
    pygame.CONTROLLER_BUTTON_DPAD_UP: pygame.K_UP,
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: pygame.K_DOWN,
}


def tecla_de_boton_online(boton):
    """El KEYDOWN equivalente a `boton` en esas pantallas, o None."""
    tecla = TECLA_DE_BOTON_PARTIDA.get(boton)
    return _tecla(tecla) if tecla is not None else None
