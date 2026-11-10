"""Edificios de Ciudad Nova: arte, escala y anclaje (solo presentación).

Cada edificio se dibuja con la configuración de assets.ARTE_EDIFICIOS:
su fuente de arte (pixel art en código con la paleta propia de la zona, o
el pack del Colegio) a una escala ENTERA (vecino más cercano, sin suavizado) para que mida
exactamente su huella de ciudad_mapa.EDIFICIOS en casillas, anclado por
su base-centro a la base de la huella. Así ningún edificio se sale de su
huella, ni tapa la acera, la puerta ni a sus vecinos.

    imagen(zona)     -> Surface del edificio (cacheada)
    rect(zona)       -> dónde va en el mundo (px)
    rect_placa(zona) -> la placa del rótulo, en px del mundo
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import ciudad_mapa
from src.ui import arte_colegio, casillas_ciudad

_cache = {}


def huella(zona):
    """Rect de la huella en px del mundo."""
    col, fila, ancho, alto = ciudad_mapa.EDIFICIOS[zona]
    return pygame.Rect(col * TAM_CASILLA, fila * TAM_CASILLA, ancho * TAM_CASILLA, alto * TAM_CASILLA)


def rect_placa(zona):
    """Placa del rótulo de `zona` en px del mundo (sobre la puerta)."""
    col, fila, ancho, alto = ciudad_mapa.EDIFICIOS[zona]
    puerta = ciudad_mapa.ENTRADAS[zona][0] - col
    x, y, w, h = casillas_ciudad.placa_rotulo(ancho, alto, puerta)
    escala = assets.ESCALA_PIXEL  # la placa se mide en píxeles de casilla (16 por casilla)
    base = huella(zona)
    return pygame.Rect(base.x + x * escala, base.y + y * escala, w * escala, h * escala)


def imagen(zona):
    """Surface del edificio, del tamaño exacto de su huella."""
    if zona not in _cache:
        col, fila, ancho, alto = ciudad_mapa.EDIFICIOS[zona]
        puerta = ciudad_mapa.ENTRADAS[zona][0] - col
        config = assets.ARTE_EDIFICIOS[zona]
        superficie = None
        if config["fuente"] == "pack_colegio" and arte_colegio.disponible():
            placa = rect_placa(zona).move(-col * TAM_CASILLA, -fila * TAM_CASILLA)
            superficie = arte_colegio.fachada(ancho, alto, puerta, placa, config["escala"], TAM_CASILLA)
        if superficie is None:
            # Pixel art en código (16 px por casilla) a ESCALA_PIXEL: también el respaldo del Colegio.
            superficie = casillas_ciudad.fachada(zona, ancho, alto, puerta, assets.ESCALA_PIXEL)
        _cache[zona] = superficie
    return _cache[zona]


def rect(zona):
    """Dónde se dibuja: anclado por la base-centro a la base de su huella."""
    destino = imagen(zona).get_rect()
    setattr(destino, assets.ANCLA_EDIFICIOS, getattr(huella(zona), assets.ANCLA_EDIFICIOS))
    return destino


def dibujar_todos(superficie, desplazamiento=(0, 0)):
    for zona in ciudad_mapa.EDIFICIOS:
        superficie.blit(imagen(zona), rect(zona).move(desplazamiento))
