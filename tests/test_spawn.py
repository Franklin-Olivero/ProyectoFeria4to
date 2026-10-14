"""Tests de dónde aparecen los enemigos: nunca cerca de la entrada.

posiciones_spawn es pura; los tests de Cuarto/MazmorraJugable usan
pygame.Rect sin abrir ventana, como test_roles.py.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    DISTANCIA_MIN_SPAWN_ENEMIGO,
    REPORTES_POR_ZONA,
    SEPARACION_MIN_SPAWN_ENEMIGOS,
    ZONA_COLEGIO,
)
from src.dungeon.clasificador_toxicidad import DIFICULTAD_ALTA  # noqa: E402
from src.dungeon.cuarto import DIRECCIONES, Cuarto, punto_llegada  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.mazmorra_jugable import MazmorraJugable  # noqa: E402
from src.dungeon.spawn import posiciones_spawn  # noqa: E402
from src.structures.graph import Grafo  # noqa: E402

LIMITES = (140, 80, 1140, 640)  # el cuarto de 1000x560 centrado en (640, 360)
SEMILLAS = range(60)


def entradas():
    import pygame

    rect = pygame.Rect(0, 0, assets.ANCHO_CUARTO, assets.ALTO_CUARTO)
    rect.center = assets.CENTRO_CUARTO
    return [punto_llegada(rect, d) for d in DIRECCIONES] + [rect.center]


def test_limites_coinciden_con_el_cuarto():
    cuarto = Cuarto(dificultad={"cantidad_enemigos": 0, "multiplicador_velocidad": 1.0})
    assert (cuarto.rect.left, cuarto.rect.top, cuarto.rect.right, cuarto.rect.bottom) == LIMITES


@pytest.mark.parametrize("cantidad", [1, 2, 3, 5])
def test_posiciones_lejos_de_la_entrada_y_separadas(cantidad):
    for entrada in entradas():
        for semilla in SEMILLAS:
            puntos = posiciones_spawn(LIMITES, entrada, cantidad, random.Random(semilla))
            assert len(puntos) == cantidad
            for p in puntos:
                assert math.dist(p, entrada) >= DISTANCIA_MIN_SPAWN_ENEMIGO
                assert LIMITES[0] < p[0] < LIMITES[2] and LIMITES[1] < p[1] < LIMITES[3]
            for a in range(cantidad):
                for b in range(a + 1, cantidad):
                    assert math.dist(puntos[a], puntos[b]) >= SEPARACION_MIN_SPAWN_ENEMIGOS
            # De la más cercana a la más lejana (los curanderos van al final).
            distancias = [math.dist(p, entrada) for p in puntos]
            assert distancias == sorted(distancias)


def test_misma_semilla_mismas_posiciones():
    entrada = entradas()[0]
    assert posiciones_spawn(LIMITES, entrada, 5, random.Random(3)) == posiciones_spawn(
        LIMITES, entrada, 5, random.Random(3))


def test_cuarto_genera_sus_enemigos_lejos_del_punto_de_entrada():
    for entrada in entradas():
        for semilla in SEMILLAS:
            cuarto = Cuarto(dificultad=dict(DIFICULTAD_ALTA), es_final=True,
                            punto_entrada=entrada, rng=random.Random(semilla))
            assert len(cuarto.enemigos) == 5
            for enemigo in cuarto.enemigos:
                assert math.dist(enemigo.rect.center, entrada) >= DISTANCIA_MIN_SPAWN_ENEMIGO


def test_al_cruzar_puertas_ningun_enemigo_aparece_cerca_del_jugador():
    """Recorre cuarto por cuarto varias mazmorras de toxicidad alta."""
    for semilla in range(15):
        mj = MazmorraJugable(Mazmorra(REPORTES_POR_ZONA[ZONA_COLEGIO], ZONA_COLEGIO, semilla=semilla))
        m = mj.mazmorra
        jugador = _jugador()
        mj.colocar_en_entrada(jugador)
        revisados = 0
        for _ in range(40):
            if not m.cuartos_pendientes() and m.actual == m.cuarto_final:
                break
            while mj.cuarto.enemigos:
                mj.cuarto.eliminar_un_enemigo()
            mj.actualizar(0.0, jugador, [])
            destino = _siguiente(m)
            direccion = next(d for d, v in m.puertas(m.actual).items() if v == destino)
            jugador.rect.center = mj.cuarto.puertas[direccion].rect.center
            jugador.posicion.update(jugador.rect.center)
            nuevo = destino not in mj.cuartos
            mj.actualizar(0.0, jugador, [])
            assert m.actual == destino
            if nuevo:
                revisados += 1
                for enemigo in mj.cuarto.enemigos:
                    assert math.dist(enemigo.rect.center, jugador.rect.center) >= DISTANCIA_MIN_SPAWN_ENEMIGO
        assert revisados >= 4


def _siguiente(m):
    """Próximo cuarto hacia el pendiente más cercano (sin pisar el final
    sellado) o hacia el final si ya no hay pendientes."""
    pendientes = m.cuartos_pendientes()
    grafo = m.grafo
    if pendientes:
        grafo = m.grafo.copia()
        grafo.eliminar_nodo(m.cuarto_final)
    _, distancias, predecesores = grafo.bfs(m.actual)
    objetivo = min(pendientes, key=lambda c: distancias[c]) if pendientes else m.cuarto_final
    return Grafo.camino(predecesores, m.actual, objetivo)[1]


def _jugador():
    import pygame
    from types import SimpleNamespace

    rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
    return SimpleNamespace(rect=rect, posicion=pygame.Vector2(rect.center), recibir_dano=lambda *a, **k: None)
