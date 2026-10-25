"""Dibujo del cuerpo de los proyectiles (solo presentación).

Cada proyectil llama a `dibujar_cuerpo` desde su `dibujar()`: si hay una
plantilla de pixel art para su tamaño (sprites.sprite_proyectil) la
dibuja teñida con su color y, si tiene dirección y la plantilla es
direccional (la onda del Influencer), girada hacia donde viaja; si no,
cae al rect / círculo de siempre. Las estelas siguen en cada clase.
"""

import math

import pygame

from src.core import assets
from src.ui import sprites

PASO_ANGULO = 15  # grados: los sprites girados se cachean por este paso
_cache_girados = {}


def _girado(imagen, direccion):
    """`imagen` girada hacia `direccion` (apunta a la derecha en reposo)."""
    angulo = -math.degrees(math.atan2(direccion.y, direccion.x))
    angulo = round(angulo / PASO_ANGULO) * PASO_ANGULO % 360
    clave = (id(imagen), angulo)
    if clave not in _cache_girados:
        _cache_girados[clave] = pygame.transform.rotate(imagen, angulo)
    return _cache_girados[clave]


def dibujar_cuerpo(pantalla, proyectil, plantilla=None, redondo=False):
    """Cuerpo del proyectil centrado en su rect. `plantilla` fuerza unas
    filas concretas (p. ej. sprites.RAYO_5); `redondo` elige el fallback
    circular en vez del rect."""
    imagen = sprites.sprite_proyectil(proyectil.color, proyectil.rect.width, plantilla)
    if imagen is None:
        if redondo:
            pygame.draw.circle(pantalla, proyectil.color, proyectil.rect.center, proyectil.rect.width // 2)
        else:
            pygame.draw.rect(pantalla, proyectil.color, proyectil.rect)
        return
    if proyectil.rect.width == assets.TAMANIO_PROYECTIL_INFLUENCER and proyectil.direccion.length_squared() > 0:
        imagen = _girado(imagen, proyectil.direccion)
    pantalla.blit(imagen, imagen.get_rect(center=proyectil.rect.center))
