"""Input por jugador (src/core/entrada.py): teclado+mouse y control de PS4.

El control se sustituye por un objeto falso con la misma interfaz que
pygame._sdl2.controller.Controller (get_axis, get_button, attached), así
los tests no necesitan un control conectado ni abrir ventana.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.entrada import (  # noqa: E402
    BOTON_DASH,
    BOTON_HABILIDAD,
    EJE_DISPARO,
    EJE_MAXIMO,
    EntradaMando,
    EntradaTeclado,
    InputJugador,
    leer_stick,
)
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402

LIMITES = pygame.Rect(0, 0, 2000, 2000)


class Teclas:
    def __init__(self, *presionadas):
        self.presionadas = set(presionadas)

    def __getitem__(self, tecla):
        return tecla in self.presionadas


class MandoFalso:
    """Ejes en -1..1 (se escalan como SDL) y botones apretados."""

    def __init__(self, ejes=None, botones=(), conectado=True):
        self.ejes = ejes or {}
        self.botones = set(botones)
        self.conectado = conectado

    def attached(self):
        return self.conectado

    def get_axis(self, eje):
        return round(self.ejes.get(eje, 0.0) * EJE_MAXIMO)

    def get_button(self, boton):
        return boton in self.botones


def test_stick_dentro_de_la_zona_muerta_cuenta_como_suelto():
    assert leer_stick(0.1, 0.05) is None
    assert leer_stick(0.6, 0.8) == pytest.approx((0.6, 0.8))
    assert leer_stick(0.3, 0.0) == pytest.approx((1.0, 0.0))  # se normaliza


def test_teclado_lee_movimiento_disparo_y_pulsos():
    entrada = EntradaTeclado()
    teclas = Teclas(pygame.K_d, pygame.K_w, pygame.K_f, pygame.K_LSHIFT)
    pedido = entrada.leer(teclas, (False, False, False), (300, 200))
    assert pedido.movimiento == pytest.approx((0.7071, -0.7071), abs=1e-3)
    assert pedido.punto_apuntado == (300, 200)
    assert not pedido.disparando
    assert pedido.habilidad and pedido.dash
    # Mantener F y Shift el frame siguiente no repite el pulso.
    pedido = entrada.leer(teclas, (True, False, False), (300, 200))
    assert pedido.disparando  # click izquierdo
    assert not pedido.habilidad and not pedido.dash


def test_mando_lee_sticks_gatillo_y_botones():
    mando = MandoFalso(
        ejes={
            pygame.CONTROLLER_AXIS_LEFTX: -1.0,
            pygame.CONTROLLER_AXIS_RIGHTY: 0.9,
            EJE_DISPARO: 0.8,
        },
        botones={BOTON_DASH, BOTON_HABILIDAD},
    )
    entrada = EntradaMando(mando)
    pedido = entrada.leer()
    assert pedido.movimiento == pytest.approx((-1.0, 0.0))
    assert pedido.direccion_apuntado == pytest.approx((0.0, 1.0))
    assert pedido.punto_apuntado is None
    assert pedido.disparando
    assert pedido.dash and pedido.habilidad
    pedido = entrada.leer()
    assert not pedido.dash and not pedido.habilidad  # botones mantenidos: sin pulso nuevo


def test_mando_con_sticks_sueltos_y_gatillo_a_medias():
    mando = MandoFalso(ejes={pygame.CONTROLLER_AXIS_LEFTX: 0.1, EJE_DISPARO: 0.3})
    pedido = EntradaMando(mando).leer()
    assert pedido.movimiento == (0.0, 0.0)
    assert pedido.direccion_apuntado is None
    assert not pedido.disparando


def test_mando_desconectado_no_pide_nada():
    pedido = EntradaMando(MandoFalso(botones={BOTON_DASH}, conectado=False)).leer()
    assert pedido == InputJugador()


def test_stick_derecho_apunta_al_jugador():
    jugador = Ciudadano(500, 500)
    jugador.manejar_input(InputJugador(direccion_apuntado=(1.0, 0.0)), 1 / 60, LIMITES)
    assert jugador.direccion_mirada.x == pytest.approx(1.0)
    # Stick suelto: conserva la dirección.
    jugador.manejar_input(InputJugador(), 1 / 60, LIMITES)
    assert jugador.direccion_mirada.x == pytest.approx(1.0)


def test_candidato_ignora_el_stick_derecho_y_mira_hacia_donde_camina():
    jugador = Candidato(500, 500)
    pedido = InputJugador(movimiento=(0.0, 1.0), direccion_apuntado=(1.0, 0.0))
    jugador.manejar_input(pedido, 1 / 60, LIMITES)
    assert tuple(jugador.direccion_mirada) == pytest.approx((0.0, 1.0))


def test_manejar_input_arranca_el_dash():
    jugador = Ciudadano(500, 500)
    jugador.manejar_input(InputJugador(movimiento=(1.0, 0.0), dash=True), 1 / 60, LIMITES)
    assert jugador.dash.activo
    assert jugador.dash.direccion == (1.0, 0.0)
