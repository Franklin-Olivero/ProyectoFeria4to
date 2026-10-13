"""Tests de la carga de habilidad por kills del Jugador (Ciudadano).

Jugador usa pygame.Rect/Vector2, que no necesitan ventana ni
pygame.init(), así que se instancia directamente.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.entities.player import Jugador  # noqa: E402

MAXIMO = Jugador.CARGA_MAXIMA_HABILIDAD


@pytest.fixture
def jugador():
    return Jugador(0, 0)


def cargar(jugador, kills):
    for _ in range(kills):
        jugador.registrar_kill()


def test_carga_empieza_en_cero(jugador):
    assert jugador.carga_habilidad == 0


def test_registrar_kill_incrementa(jugador):
    jugador.registrar_kill()
    assert jugador.carga_habilidad == 1


def test_registrar_kill_no_pasa_del_maximo(jugador):
    cargar(jugador, MAXIMO + 3)
    assert jugador.carga_habilidad == MAXIMO


def test_puede_usar_habilidad_solo_en_el_limite(jugador):
    cargar(jugador, MAXIMO - 1)
    assert not jugador.puede_usar_habilidad()
    jugador.registrar_kill()
    assert jugador.puede_usar_habilidad()


def test_usar_habilidad_sin_carga_no_hace_nada(jugador):
    cargar(jugador, MAXIMO - 1)
    assert jugador.usar_habilidad() is False
    assert jugador.carga_habilidad == MAXIMO - 1
    assert not jugador.burbuja_activa


def test_usar_habilidad_resetea_carga_y_activa_burbuja(jugador):
    cargar(jugador, MAXIMO)
    assert jugador.usar_habilidad() is True
    assert jugador.carga_habilidad == 0
    assert jugador.burbuja_activa
    assert not jugador.puede_usar_habilidad()


def test_burbuja_se_apaga_al_terminar_su_duracion(jugador):
    cargar(jugador, MAXIMO)
    jugador.usar_habilidad()
    jugador.actualizar_habilidad(assets.DURACION_BURBUJA - 0.1)
    assert jugador.burbuja_activa
    jugador.actualizar_habilidad(0.2)
    assert not jugador.burbuja_activa
