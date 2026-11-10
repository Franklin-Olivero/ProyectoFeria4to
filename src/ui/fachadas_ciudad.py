"""Casas y edificios de Ciudad Nova armados con los packs (solo dibujo).

Vista estilo Pokémon: el techo arriba y la fachada abajo, del tamaño exacto
de la huella y a escala 1 (sin reescalar el arte):

    techo(nombre, ancho, alto)            -> marco de CORNERS 5 estirado en 9 partes
                                             (esquinas fijas, lados y centro repetidos)
    fachada(nombre, ancho, alto)          -> panel de WALLS 1 repetido a lo ancho,
                                             recortado al alto pedido por el medio
    edificio(ancho, alto, filas_fachada, techo, fachada, neon, puerta_x=None,
             puerta=None, pilar=None)     -> Surface completa (o None sin atlas)

La franja de neón entre techo y fachada lleva el color del estilo; la
puerta (si la casa da a una acera) se recorta del centro de su pieza.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.ui import cargador_assets


def _pieza(nombre):
    return cargador_assets.pieza_ciudad(nombre) if nombre else None


def _repetir(superficie, pieza, rect):
    """Rellena `rect` de `superficie` repitiendo `pieza` (sin escalar)."""
    x0, y0, ancho, alto = rect
    if ancho <= 0 or alto <= 0:
        return
    superficie.set_clip(pygame.Rect(rect))
    for y in range(y0, y0 + alto, pieza.get_height()):
        for x in range(x0, x0 + ancho, pieza.get_width()):
            superficie.blit(pieza, (x, y))
    superficie.set_clip(None)


def techo(nombre, ancho, alto):
    """Marco del techo en 9 partes: las esquinas de LADO_MARCO_TECHO px no
    se deforman; los lados y el centro se repiten."""
    pieza = _pieza(nombre)
    if pieza is None:
        return None
    w, h = pieza.get_size()
    b = min(assets.LADO_MARCO_TECHO, ancho // 2, alto // 2)
    salida = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    centro = pieza.subsurface((b, b, w - 2 * b, h - 2 * b))
    _repetir(salida, centro, (b, b, ancho - 2 * b, alto - 2 * b))
    _repetir(salida, pieza.subsurface((b, 0, w - 2 * b, b)), (b, 0, ancho - 2 * b, b))
    _repetir(salida, pieza.subsurface((b, h - b, w - 2 * b, b)), (b, alto - b, ancho - 2 * b, b))
    _repetir(salida, pieza.subsurface((0, b, b, h - 2 * b)), (0, b, b, alto - 2 * b))
    _repetir(salida, pieza.subsurface((w - b, b, b, h - 2 * b)), (ancho - b, b, b, alto - 2 * b))
    salida.blit(pieza.subsurface((0, 0, b, b)), (0, 0))
    salida.blit(pieza.subsurface((w - b, 0, b, b)), (ancho - b, 0))
    salida.blit(pieza.subsurface((0, h - b, b, b)), (0, alto - b))
    salida.blit(pieza.subsurface((w - b, h - b, b, b)), (ancho - b, alto - b))
    return salida


def fachada(nombre, ancho, alto):
    """Panel de fachada repetido a lo ancho; si el panel es más alto que
    `alto` se toma su franja central, si es más bajo se repite hacia abajo."""
    pieza = _pieza(nombre)
    if pieza is None:
        return None
    w, h = pieza.get_size()
    if h > alto:
        pieza = pieza.subsurface((0, (h - alto) // 2, w, alto))
    salida = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    # Cada repetición empieza corrida para que dos casas iguales no calcen igual.
    _repetir(salida, pieza, (0, 0, ancho, alto))
    return salida


def _puerta(nombre, alto):
    pieza = _pieza(nombre)
    if pieza is None:
        return None
    w, h = pieza.get_size()
    ancho = min(w, TAM_CASILLA - 8)
    alto = min(h, alto)
    return pieza.subsurface(((w - ancho) // 2, h - alto, ancho, alto))


def edificio(ancho, alto, filas_fachada, nombre_techo, nombre_fachada, neon, puerta_x=None, puerta=None,
             pilar=None):
    """Surface de `ancho` x `alto` px: techo arriba, fachada de
    `filas_fachada` casillas abajo, neón entre ambos, puerta centrada en
    `puerta_x` (px, centro) y pilares en las esquinas. None sin atlas."""
    alto_fachada = filas_fachada * TAM_CASILLA
    arriba = techo(nombre_techo, ancho, alto - alto_fachada + assets.GROSOR_NEON_CASA)
    abajo = fachada(nombre_fachada, ancho, alto_fachada)
    if arriba is None or abajo is None:
        return None
    salida = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    salida.blit(abajo, (0, alto - alto_fachada))
    salida.blit(arriba, (0, 0))
    salida.fill(neon, (0, alto - alto_fachada - assets.GROSOR_NEON_CASA, ancho, assets.GROSOR_NEON_CASA))
    columna = _pieza(pilar)
    if columna is not None:
        grosor = assets.ANCHO_PILAR_EDIFICIO
        tramo = columna.subsurface(((columna.get_width() - grosor) // 2, 0, grosor, columna.get_height()))
        for x in (0, ancho - grosor):
            _repetir(salida, tramo, (x, alto - alto_fachada, grosor, alto_fachada))
    if puerta_x is not None and puerta is not None:
        hoja = _puerta(puerta, alto_fachada - 4)
        if hoja is not None:
            salida.blit(hoja, hoja.get_rect(midbottom=(puerta_x, alto)))
    return salida
