"""Carga y caché de fuentes (solo presentación).

`fuente(tamanio, negrita)` devuelve siempre el mismo objeto Font para
el mismo pedido, así los módulos de dibujo no crean fuentes cada frame.
Usa JetBrains Mono desde assets/fonts (ver src/core/assets.py); si el
archivo no existe, cae a la fuente por defecto de pygame para que el
juego siga abriendo.
"""

import os

import pygame

from src.core import assets

_cache = {}


def fuente(tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False):
    clave = (tamanio, negrita)
    if clave not in _cache:
        ruta = assets.RUTA_FUENTE_NEGRITA if negrita else assets.RUTA_FUENTE_REGULAR
        if os.path.exists(ruta):
            _cache[clave] = pygame.font.Font(ruta, tamanio)
        else:
            fallback = pygame.font.Font(None, tamanio + 4)
            fallback.set_bold(negrita)
            _cache[clave] = fallback
    return _cache[clave]
