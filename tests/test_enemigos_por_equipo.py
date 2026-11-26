"""Más jugadores, más enemigos (enemigos_para_equipo): con 2 a 4 jugadores
cada cuarto trae más enemigos según su toxicidad, sin pasar del tope."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import math  # noqa: E402
import random  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.balance import MAX_ENEMIGOS_CUARTO, SEPARACION_MIN_SPAWN_ENEMIGOS  # noqa: E402
from src.dungeon.clasificador_toxicidad import enemigos_para_equipo, nivel_a_dificultad  # noqa: E402


@pytest.mark.parametrize("toxicidad, esperado", [(20, [2, 3, 3, 4]), (50, [3, 4, 4, 5]), (90, [5, 6, 7, 8])])
def test_la_tabla_por_toxicidad_y_jugadores(toxicidad, esperado):
    base = nivel_a_dificultad(toxicidad)
    assert [enemigos_para_equipo(base, toxicidad, n)["cantidad_enemigos"] for n in (1, 2, 3, 4)] == esperado


def test_solo_cambia_la_cantidad():
    base = nivel_a_dificultad(80)
    con_equipo = enemigos_para_equipo(base, 80, 4)
    assert con_equipo["multiplicador_velocidad"] == base["multiplicador_velocidad"]
    assert base == nivel_a_dificultad(80)  # no toca el dict original


def test_crece_con_la_toxicidad_y_con_los_jugadores_sin_pasar_el_tope():
    for jugadores in (1, 2, 3, 4):
        anterior = 0
        for toxicidad in range(0, 101, 5):
            cantidad = enemigos_para_equipo(nivel_a_dificultad(toxicidad), toxicidad, jugadores)["cantidad_enemigos"]
            assert anterior <= cantidad <= MAX_ENEMIGOS_CUARTO
            anterior = cantidad
    for toxicidad in (0, 40, 100):
        cantidades = [enemigos_para_equipo(nivel_a_dificultad(toxicidad), toxicidad, n)["cantidad_enemigos"]
                      for n in (1, 2, 3, 4)]
        assert cantidades == sorted(cantidades) and cantidades[-1] > cantidades[0]


def test_la_entrada_y_el_solitario_no_cambian():
    vacio = {"cantidad_enemigos": 0, "multiplicador_velocidad": 1.0}
    assert enemigos_para_equipo(vacio, 100, 4)["cantidad_enemigos"] == 0
    for toxicidad in (10, 50, 95):
        base = nivel_a_dificultad(toxicidad)
        assert enemigos_para_equipo(base, toxicidad, 1) == base


def test_la_mazmorra_usa_la_cantidad_de_jugadores():
    pygame.init()
    pygame.display.set_mode((10, 10))
    from src.dungeon.mazmorra import Mazmorra
    from src.dungeon.mazmorra_jugable import MazmorraJugable
    from src.dungeon.partida import Partida
    from src.entities.player import Ciudadano

    def total_enemigos(cantidad):
        partida = Partida()
        mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes("Colegio"), "Colegio", semilla=5))
        mazmorra.colocar_en_entrada([Ciudadano(0, 0) for _ in range(cantidad)])
        m = mazmorra.mazmorra
        total = 0
        for id_cuarto in [c for c in m.toxicidad if c in mazmorra._distancia_entrada]:
            m.entrar(id_cuarto)  # al entrar se calcula su dificultad (generación perezosa)
            mazmorra._crear_cuarto_si_falta(id_cuarto)
            cuarto = mazmorra.cuartos[id_cuarto]
            pos = [e.rect.center for e in cuarto.enemigos]
            assert len(pos) <= MAX_ENEMIGOS_CUARTO
            # No se saturan: aparecen separados.
            assert all(math.dist(a, b) >= SEPARACION_MIN_SPAWN_ENEMIGOS - 1 for i, a in enumerate(pos) for b in pos[i + 1:])
            total += len(pos)
        return total

    uno, cuatro = total_enemigos(1), total_enemigos(4)
    assert cuatro > uno
    random.seed()
