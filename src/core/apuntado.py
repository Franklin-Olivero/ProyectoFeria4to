"""Apuntado con el mouse (lógica pura, sin Pygame: solo math).

Ciudadano, Influencer y Periodista apuntan hacia el mouse: cada frame
de combate Main.py lee la posición del cursor y JugadorBase.apuntar_a()
usa esta función para fijar `direccion_mirada`. El Candidato no la usa
(su ataque es radial y su habilidad sale hacia donde camina).
"""

import math

from src.core.balance import ZONA_MUERTA_APUNTADO


def calcular_direccion_apuntado(centro, punto_mouse, direccion_previa):
    """Vector unitario (x, y) desde `centro` hacia `punto_mouse`.

    Si el mouse está a menos de ZONA_MUERTA_APUNTADO píxeles del centro
    (incluido justo encima), la dirección sería inestable o indefinida,
    así que se devuelve `direccion_previa` sin cambios. O(1).
    """
    dx = punto_mouse[0] - centro[0]
    dy = punto_mouse[1] - centro[1]
    distancia = math.hypot(dx, dy)
    if distancia < ZONA_MUERTA_APUNTADO:
        return direccion_previa
    return (dx / distancia, dy / distancia)
