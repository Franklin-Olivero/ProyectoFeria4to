"""Input de un jugador, igual venga del teclado+mouse o de un control.

`InputJugador` (dataclass pura) es lo que un jugador quiere hacer en un
frame. JugadorBase.manejar_input() lo aplica sin saber de dónde salió,
así J1 (teclado+mouse) y J2 (control de PS4) usan el mismo código:

    teclado + mouse --EntradaTeclado.leer()--> InputJugador --> jugador1.manejar_input()
    control PS4     --EntradaMando.leer()----> InputJugador --> jugador2.manejar_input()

El control se lee con la API "GameController" de SDL
(pygame._sdl2.controller), que normaliza los botones entre marcas: en
un DualShock 4, BUTTON_A es la Cruz, B el Círculo, X el Cuadrado, Y el
Triángulo, LEFTSHOULDER es L1 y AXIS_TRIGGERRIGHT es R2. Con los índices
crudos de pygame.joystick el mapeo cambia según el driver y el sistema.

Los "pulsos" (habilidad, dash) son True solo el frame en que se aprieta
el botón: cada lector recuerda el estado del frame anterior.
"""

import math
from dataclasses import dataclass

import pygame

from src.core.balance import CLICK_DISPARA, UMBRAL_GATILLO, ZONA_MUERTA_STICK

TECLA_DISPARAR = pygame.K_SPACE
TECLA_HABILIDAD = pygame.K_f
TECLAS_DASH = (pygame.K_LSHIFT, pygame.K_RSHIFT)
# Teclas de interfaz en combate (eventos en Main.py; aquí para que la
# guía de controles de los ajustes lea las mismas que el juego).
TECLA_MINIMAPA = pygame.K_m
TECLA_ARBOL = pygame.K_TAB
# Audio (en todas las pantallas): N silencia / vuelve a sonar; - y +
# bajan y suben el volumen general en el lobby.
TECLA_SILENCIO = pygame.K_n
TECLAS_VOLUMEN = {pygame.K_MINUS: -1, pygame.K_KP_MINUS: -1, pygame.K_PLUS: 1, pygame.K_EQUALS: 1, pygame.K_KP_PLUS: 1}

# Botones del control (nombres de SDL, ver docstring del módulo).
BOTON_DASH = pygame.CONTROLLER_BUTTON_A  # Cruz
BOTON_HABILIDAD = pygame.CONTROLLER_BUTTON_LEFTSHOULDER  # L1
EJE_DISPARO = pygame.CONTROLLER_AXIS_TRIGGERRIGHT  # R2
EJE_MAXIMO = 32767  # los ejes de SDL van de -32768 a 32767 (gatillos de 0 a 32767)

# Distancia a la que se proyecta la dirección del stick derecho para
# apuntar como si fuera un punto del mouse (ver JugadorBase.manejar_input).
DISTANCIA_PUNTO_STICK = 1000


@dataclass
class InputJugador:
    """Lo que un jugador pide en un frame."""

    movimiento: tuple = (0.0, 0.0)  # largo 0 o 1
    punto_apuntado: tuple | None = None  # punto del mundo (mouse); None = no apuntar
    direccion_apuntado: tuple | None = None  # dirección unitaria (stick); None = no apuntar
    disparando: bool = False
    habilidad: bool = False  # pulso: solo el frame en que se aprieta
    dash: bool = False  # pulso


def direccion_teclado(teclas):
    """(x, y) unitaria según WASD/flechas, o (0, 0) sin teclas."""
    x = (teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - (teclas[pygame.K_a] or teclas[pygame.K_LEFT])
    y = (teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - (teclas[pygame.K_w] or teclas[pygame.K_UP])
    return _unitario(x, y)


def leer_stick(x, y, zona_muerta=ZONA_MUERTA_STICK):
    """Dirección unitaria de un stick con ejes en -1..1, o None si su
    inclinación es menor que la zona muerta (stick suelto)."""
    if math.hypot(x, y) < zona_muerta:
        return None
    return _unitario(x, y)


def _unitario(x, y):
    largo = math.hypot(x, y)
    return (x / largo, y / largo) if largo else (0.0, 0.0)


class _Pulsos:
    """Convierte botones mantenidos en pulsos de un frame."""

    def __init__(self):
        self._antes = {}

    def pulso(self, nombre, apretado):
        nuevo = apretado and not self._antes.get(nombre, False)
        self._antes[nombre] = apretado
        return nuevo


class EntradaTeclado:
    """J1: WASD mueve, el mouse apunta, SPACE/click dispara, F habilidad, Shift dash."""

    def __init__(self):
        self._pulsos = _Pulsos()

    def leer(self, teclas, botones_mouse, punto_mouse):
        """`punto_mouse` ya en coordenadas del mundo, o None sin foco."""
        dash = any(teclas[tecla] for tecla in TECLAS_DASH)
        return InputJugador(
            movimiento=direccion_teclado(teclas),
            punto_apuntado=punto_mouse,
            disparando=bool(teclas[TECLA_DISPARAR] or (CLICK_DISPARA and botones_mouse[0])),
            habilidad=self._pulsos.pulso("habilidad", bool(teclas[TECLA_HABILIDAD])),
            dash=self._pulsos.pulso("dash", dash),
        )


class EntradaMando:
    """J2: stick izquierdo mueve, stick derecho apunta, R2 dispara, L1
    habilidad, Cruz dash. `mando` es un pygame._sdl2.controller.Controller
    (o cualquier objeto con get_axis/get_button/attached, para tests)."""

    def __init__(self, mando):
        self.mando = mando
        if self.mando is None:
            from Online.sesion_red import _MandoFicticio
            self.mando = _MandoFicticio()
        self._pulsos = _Pulsos()

    def leer(self):
        if not self.mando.attached():
            return InputJugador()  # control desconectado: el J2 se queda quieto
        eje = lambda nombre: self.mando.get_axis(nombre) / EJE_MAXIMO  # noqa: E731
        movimiento = leer_stick(eje(pygame.CONTROLLER_AXIS_LEFTX), eje(pygame.CONTROLLER_AXIS_LEFTY))
        return InputJugador(
            movimiento=movimiento or (0.0, 0.0),
            direccion_apuntado=leer_stick(eje(pygame.CONTROLLER_AXIS_RIGHTX), eje(pygame.CONTROLLER_AXIS_RIGHTY)),
            disparando=eje(EJE_DISPARO) > UMBRAL_GATILLO,
            habilidad=self._pulsos.pulso("habilidad", bool(self.mando.get_button(BOTON_HABILIDAD))),
            dash=self._pulsos.pulso("dash", bool(self.mando.get_button(BOTON_DASH))),
        )
