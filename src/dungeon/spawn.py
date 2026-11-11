"""Dónde aparecen los enemigos de un cuarto (lógica pura, sin Pygame).

posiciones_spawn() arma una grilla de posiciones candidatas dentro del
cuarto (con margen a los muros), descarta las que estén a menos de
DISTANCIA_MIN_SPAWN_ENEMIGO del punto donde entra el jugador y elige al
azar (rng inyectado) entre las que quedan, separadas entre sí. Así el
jugador nunca aparece pegado a un enemigo al cruzar una puerta.
"""

import math

from src.core.balance import (
    DISTANCIA_MIN_SPAWN_ENEMIGO,
    MARGEN_SPAWN_ENEMIGO,
    PASO_GRILLA_SPAWN,
    SEPARACION_MIN_SPAWN_ENEMIGOS,
)


def candidatas(limites):
    """Puntos de la grilla dentro de `limites` = (izq, arriba, der, abajo)."""
    izquierda, arriba, derecha, abajo = limites
    paso_x, paso_y = PASO_GRILLA_SPAWN
    puntos = []
    y = arriba + MARGEN_SPAWN_ENEMIGO
    while y <= abajo - MARGEN_SPAWN_ENEMIGO:
        x = izquierda + MARGEN_SPAWN_ENEMIGO
        while x <= derecha - MARGEN_SPAWN_ENEMIGO:
            puntos.append((x, y))
            x += paso_x
        y += paso_y
    return puntos


def posiciones_spawn(limites, punto_entrada, cantidad, rng, distancia_min=DISTANCIA_MIN_SPAWN_ENEMIGO,
                     libre=None):
    """`cantidad` posiciones (x, y) ordenadas de la más cercana a la más
    lejana al punto de entrada. Todas a >= `distancia_min` de él y a >=
    SEPARACION_MIN_SPAWN_ENEMIGOS entre sí cuando el cuarto lo permite;
    si no alcanzaran, se completa con las candidatas más lejanas.
    `libre` (opcional): función punto -> bool; las candidatas donde da
    False se descartan (hay una cobertura encima o no se llega caminando).
    O(c * n), con c candidatas y n enemigos."""
    if cantidad <= 0:
        return []
    todas = candidatas(limites)
    if libre is not None:
        todas = [p for p in todas if libre(p)] or todas

    def lejania(punto):
        return math.dist(punto, punto_entrada)

    seguras = [p for p in todas if lejania(p) >= distancia_min]
    rng.shuffle(seguras)
    elegidas = []
    for punto in seguras:
        if all(math.dist(punto, otro) >= SEPARACION_MIN_SPAWN_ENEMIGOS for otro in elegidas):
            elegidas.append(punto)
            if len(elegidas) == cantidad:
                break
    if len(elegidas) < cantidad:
        restantes = sorted((p for p in todas if p not in elegidas), key=lejania, reverse=True)
        elegidas.extend(restantes[:cantidad - len(elegidas)])
    return sorted(elegidas, key=lejania)
