"""Cargador central de imágenes en hojas (solo presentación).

Lee cada hoja PNG una vez (caché por ruta) y recorta piezas por rect, con
caché por (ruta, rect, escala, factor). Si la hoja falta o no se puede
leer, devuelve None y quien pide la pieza dibuja su placeholder de
siempre: el juego nunca depende de un archivo de arte.

    hoja(ruta)                 -> Surface completa o None
    recorte(ruta, rect, ...)   -> pieza (escalada, opcionalmente oscurecida) o None
    prop_urbano(nombre)        -> prop de la ciudad (assets.PROPS_URBANOS), recortado a su contenido
    pieza_colegio(nombre)      -> pieza del pack del Colegio (assets.PIEZAS_COLEGIO)
    arbol(numero, escala)      -> árbol del pack Trees_Vol2 (assets.RUTA_ARBOLES)
    pieza_ciudad(nombre)       -> pieza del atlas de Ciudad Nova (assets/ciudad/, packs cyberpunk)
    ajustar_paleta(sup, s, b)  -> copia con la saturación y el brillo escalados (la única
                                  función que corrige el color del arte de un pack)

Las rutas y rects viven en src/core/assets.py.
"""

import json
import os

import pygame

from src.core import assets

_hojas = {}  # ruta -> Surface o None
_recortes = {}  # (ruta, rect, escala, factor, ajustar) -> Surface o None
_atlas = {}  # ruta del json -> {nombre: rect}


def hoja(ruta):
    """La hoja PNG completa (convert_alpha si hay ventana), o None."""
    if ruta not in _hojas:
        imagen = None
        if ruta and os.path.exists(ruta):
            try:
                imagen = pygame.image.load(ruta)
                if pygame.display.get_surface() is not None:
                    imagen = imagen.convert_alpha()
            except (pygame.error, FileNotFoundError):
                imagen = None
        _hojas[ruta] = imagen
    return _hojas[ruta]


def recorte(ruta, rect, escala=assets.ESCALA_ARTE_PACKS, factor=1.0, ajustar=False):
    """Pieza `rect` de la hoja `ruta`, escalada (vecino más cercano: el
    pixel art no se difumina) y multiplicada por `factor` (< 1 oscurece).
    Con `ajustar`, se recorta a la caja de sus píxeles visibles. None si
    no hay hoja o el rect se sale de ella."""
    clave = (ruta, tuple(rect), escala, factor, ajustar)
    if clave not in _recortes:
        _recortes[clave] = _armar_recorte(ruta, pygame.Rect(rect), escala, factor, ajustar)
    return _recortes[clave]


def _armar_recorte(ruta, rect, escala, factor, ajustar):
    imagen = hoja(ruta)
    if imagen is None or not imagen.get_rect().contains(rect):
        return None
    pieza = imagen.subsurface(rect).copy()
    if ajustar:
        caja = pieza.get_bounding_rect()
        if caja.width and caja.height:
            pieza = pieza.subsurface(caja).copy()
    if escala != 1:
        pieza = pygame.transform.scale(pieza, (pieza.get_width() * escala, pieza.get_height() * escala))
    if factor != 1.0:
        tinte = round(255 * factor)
        pieza.fill((tinte, tinte, tinte, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return pieza


def prop_urbano(nombre, factor=1.0):
    """Prop de la hoja urbana por nombre (assets.PROPS_URBANOS), o None."""
    if nombre not in assets.PROPS_URBANOS:
        return None
    col, fila = assets.PROPS_URBANOS[nombre]
    lado = assets.CELDA_PROPS_URBANOS
    return recorte(assets.RUTA_PROPS_URBANOS, (col * lado, fila * lado, lado, lado), factor=factor, ajustar=True)


def arbol(numero, escala=assets.ESCALA_ARBOLES):
    """Árbol `numero` del pack (assets.RUTA_ARBOLES), escalado entero; None si falta."""
    ruta = os.path.join(assets.RUTA_ARBOLES, f"arbol_{numero:02d}.png")
    imagen = hoja(ruta)
    if imagen is None:
        return None
    return recorte(ruta, imagen.get_rect(), escala=escala)


def pieza_colegio(nombre, factor=1.0):
    """Pieza del pack del Colegio por nombre (assets.PIEZAS_COLEGIO), o None."""
    if nombre not in assets.PIEZAS_COLEGIO:
        return None
    archivo, rect = assets.PIEZAS_COLEGIO[nombre]
    return recorte(os.path.join(assets.RUTA_COLEGIO, archivo), rect, factor=factor)


def rects_atlas(ruta_json):
    """{nombre: (x, y, w, h)} de un atlas empaquetado, o {} si falta o está roto."""
    if ruta_json not in _atlas:
        try:
            with open(ruta_json, encoding="utf-8") as archivo:
                _atlas[ruta_json] = {n: tuple(r) for n, r in json.load(archivo)["piezas"].items()}
        except (OSError, ValueError, KeyError, TypeError):
            _atlas[ruta_json] = {}
    return _atlas[ruta_json]


def pieza_ciudad(nombre, factor=1.0):
    """Pieza `nombre` del atlas de Ciudad Nova (assets.RUTA_ATLAS_CIUDAD), o None."""
    rect = rects_atlas(assets.RUTA_ATLAS_CIUDAD_JSON).get(nombre)
    if rect is None:
        return None
    return recorte(assets.RUTA_ATLAS_CIUDAD, rect, escala=1, factor=factor)


def ajustar_paleta(superficie, saturacion=1.0, brillo=1.0):
    """Copia de `superficie` con la saturación escalada por `saturacion`
    (0 = gris, 1 = igual) y el brillo por `brillo` (< 1 oscurece): sobre su
    versión en grises se pega la original con opacidad `saturacion`, o sea
    gris + (color - gris) * saturacion. Con pixel art (alfa 0 o 255) el
    alfa queda igual. Es el único ajuste de color del arte de packs."""
    if saturacion == 1.0 and brillo == 1.0:
        return superficie
    salida = pygame.transform.grayscale(superficie)
    if saturacion > 0:
        color = superficie.copy()
        color.set_alpha(round(255 * min(1.0, saturacion)))
        salida.blit(color, (0, 0))
    if brillo != 1.0:
        tinte = max(0, min(255, round(255 * brillo)))
        salida.fill((tinte, tinte, tinte), special_flags=pygame.BLEND_RGB_MULT)
    return salida
