"""Movimiento con inercia de los jugadores (JugadorBase.mover).

Usan pygame.Rect/Vector2 sin abrir ventana, como test_roles.py.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.balance import DASH_DURACION  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402

ROLES = [Ciudadano, Influencer, Periodista, Candidato]
LIMITES = pygame.Rect(0, 0, 4000, 4000)
DT = 1 / 60


def caminar(jugador, direccion, segundos, dt=DT):
    for _ in range(round(segundos / dt)):
        jugador.mover(direccion, dt, LIMITES)


@pytest.mark.parametrize("clase", ROLES)
def test_arranca_suave_y_llega_a_la_velocidad_del_rol(clase):
    jugador = clase(2000, 2000)
    jugador.mover((1, 0), DT, LIMITES)
    assert 0 < jugador.velocidad_actual.x < jugador.velocidad * 0.5  # el primer frame no salta al máximo
    caminar(jugador, (1, 0), 0.5)
    assert jugador.velocidad_actual.x == pytest.approx(jugador.velocidad, rel=0.01)


@pytest.mark.parametrize("clase", ROLES)
def test_en_diagonal_no_pierde_velocidad(clase):
    """Antes la posición se redondeaba a enteros cada frame y en diagonal
    el jugador iba más lento y a saltos."""
    jugador = clase(2000, 2000)
    caminar(jugador, (1, 1), 0.5)
    inicio = pygame.Vector2(jugador.posicion)
    caminar(jugador, (1, 1), 1.0)
    assert jugador.posicion.distance_to(inicio) == pytest.approx(jugador.velocidad, rel=0.02)


def test_al_soltar_frena_y_se_detiene():
    jugador = Ciudadano(2000, 2000)
    caminar(jugador, (1, 0), 0.5)
    caminar(jugador, (0, 0), 0.05)
    assert 0 < jugador.velocidad_actual.x < jugador.velocidad
    caminar(jugador, (0, 0), 0.5)
    assert jugador.velocidad_actual.length() == 0


def test_la_inercia_no_depende_del_framerate():
    a, b = Influencer(2000, 2000), Influencer(2000, 2000)
    caminar(a, (1, 0), 0.3, dt=1 / 30)
    caminar(b, (1, 0), 0.3, dt=1 / 144)
    assert a.posicion.x == pytest.approx(b.posicion.x, abs=3)


def test_contra_un_muro_pierde_la_velocidad_en_ese_eje():
    limites = pygame.Rect(0, 0, 400, 400)
    jugador = Ciudadano(370, 200)
    for _ in range(30):
        jugador.mover((1, 1), DT, limites)
    assert jugador.rect.right == limites.right
    assert jugador.velocidad_actual.x == 0
    assert jugador.velocidad_actual.y > 0  # sigue deslizándose a lo largo del muro


def test_tras_el_dash_la_velocidad_se_frena_en_vez_de_cortarse():
    jugador = Periodista(2000, 2000)
    jugador.mover((1, 0), DT, LIMITES)
    jugador.iniciar_dash()
    jugador.mover((1, 0), DT, LIMITES)
    jugador.actualizar_dash(DASH_DURACION + 0.01)
    jugador.mover((0, 0), DT, LIMITES)
    assert jugador.velocidad < jugador.velocidad_actual.x  # todavía va más rápido que caminando


def test_detener_quita_la_inercia():
    jugador = Candidato(2000, 2000)
    caminar(jugador, (0, 1), 0.3)
    jugador.detener()
    x, y = jugador.posicion
    jugador.mover((0, 0), DT, LIMITES)
    assert tuple(jugador.posicion) == (x, y)
