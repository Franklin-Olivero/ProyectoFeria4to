"""Decoración de Ciudad Nova: arte de cada prop y dibujo ordenado por Y.

Los props salen de ciudad_mapa.DECORACION (reglas en
src/dungeon/layout_decoracion.py, identidad por zona en
src/dungeon/zonas_ciudad.py). Aquí solo se resuelve su imagen por los
cargadores centrales con caché: el pack urbano (cargador_assets,
assets.PROPS_URBANOS), los árboles de Trees_Vol2 y los props del pack
Backrooms (cargador_backrooms: autos, antenas, conos). Se dibujan junto
con el jugador ordenados por la base de cada uno (el borde inferior de su
huella). Si falta un PNG, el árbol y las farolas vuelven a su casilla en
pixel art y el resto a un bolardo: nunca se cae el juego.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import ciudad_mapa, zonas_ciudad
from src.dungeon.layout_decoracion import CAPA_ARBOL, FAROLAS
from src.ui import cargador_assets, cargador_backrooms, casillas_ciudad, sprites

ELEVACION_BASE = 4  # px: la base del prop queda apenas sobre el borde inferior de su huella
_cache = {}


def imagen(prop):
    """Imagen del prop (cacheada por el cargador), o su placeholder."""
    if prop.tipo == "arbol":
        imagen_prop = cargador_assets.arbol(prop.variante)
        return imagen_prop if imagen_prop is not None else casillas_ciudad.casilla_arbol()
    if prop.tipo in zonas_ciudad.PROPS_BACKROOMS:
        nombre = zonas_ciudad.PROPS_BACKROOMS[prop.tipo]
        if cargador_backrooms.disponible(assets.GRADE_CIUDAD) and cargador_backrooms.tiene_prop(assets.GRADE_CIUDAD, nombre):
            return cargador_backrooms.prop(assets.GRADE_CIUDAD, "", nombre, assets.ESCALA_BACKROOMS)
        return _bolardo()
    imagen_prop = cargador_assets.prop_urbano(prop.tipo)
    if imagen_prop is not None:
        return _orientada(prop, imagen_prop)
    if prop.tipo in FAROLAS:
        return casillas_ciudad.casilla_farola()
    return _bolardo()


def _orientada(prop, figura):
    """Las bancas que miran al este u oeste se dibujan espejadas según el lado."""
    if prop.orientacion != "O":
        return figura
    clave = ("espejo", prop.tipo)
    if clave not in _cache:
        _cache[clave] = pygame.transform.flip(figura, True, False)
    return _cache[clave]


def _bolardo():
    if "bolardo" not in _cache:
        superficie = pygame.Surface((TAM_CASILLA // 3, TAM_CASILLA // 2), pygame.SRCALPHA)
        pygame.draw.rect(superficie, assets.COLOR_COLUMNA, superficie.get_rect(), border_radius=4)
        _cache["bolardo"] = superficie
    return _cache["bolardo"]


def base(prop):
    """Punto (px del mundo) donde se apoya el prop: centro del borde inferior de su huella."""
    col, fila = prop.casilla
    return (round((col + prop.ancho / 2) * TAM_CASILLA), (fila + prop.alto) * TAM_CASILLA - ELEVACION_BASE)


def _figura(prop):
    clave = ("rect", prop)
    if clave not in _cache:
        _cache[clave] = imagen(prop).get_rect(midbottom=base(prop))
    return _cache[clave]


def visibles(rect_mundo):
    """Props cuya imagen toca `rect_mundo` (la vista de la cámara)."""
    return [prop for prop in ciudad_mapa.DECORACION if _figura(prop).colliderect(rect_mundo)]


def dibujar_con_jugador(pantalla, rect_mundo, dx, dy, dibujar_jugador, base_jugador):
    """Props visibles y el jugador en orden de base (Y): lo de abajo tapa a
    lo de arriba. `dibujar_jugador()` lo dibuja; `base_jugador` es la y
    (px del mundo) de sus pies."""
    capas = [(base(p)[1], 1 if p.capa == CAPA_ARBOL else 0, p) for p in visibles(rect_mundo)]
    capas.append((base_jugador, 2, None))
    for _, _, prop in sorted(capas, key=lambda c: (c[0], c[1])):
        if prop is None:
            dibujar_jugador()
            continue
        figura = imagen(prop)
        x, y = base(prop)
        if prop.capa == CAPA_ARBOL or prop.ancho > 1:
            sprites.dibujar_sombra(pantalla, (x + dx, y + dy), figura.get_width() * 2 // 3)
        pantalla.blit(figura, figura.get_rect(midbottom=(x + dx, y + dy)))


def farolas():
    """Centros (px del mundo) de las farolas de todos los modelos, para sus halos."""
    return [ciudad_mapa.centro_casilla(*p.casilla) for p in ciudad_mapa.DECORACION if p.tipo in FAROLAS]
