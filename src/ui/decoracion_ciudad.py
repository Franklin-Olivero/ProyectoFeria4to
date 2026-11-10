"""Decoración de Ciudad Nova: arte de cada prop y dibujo ordenado por Y.

Los props salen de ciudad_mapa.DECORACION (reglas en
src/dungeon/layout_decoracion.py, identidad por zona en
src/dungeon/zonas_ciudad.py). Su imagen se pide SOLO por
src/ui/arte_ciudad.py con el id de id_arte(prop): "arbol:<n>" (Trees_Vol2),
"backrooms:<tipo>" (antena, conos, letrero) o "urbano:<tipo>" (farolas,
bancas, papeleras...); un id fuera de assets.ASSETS_CIUDAD_PERMITIDOS no se
dibuja. Todo se dibuja con una sombra suave y junto con el jugador,
ordenado por la base de cada uno (el borde inferior de su huella). Si
falta un PNG, el árbol y las farolas vuelven a su casilla en pixel art y
el resto a un bolardo: nunca se cae el juego.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import ciudad_mapa, zonas_ciudad
from src.dungeon.layout_decoracion import CAPA_ARBOL, FAROLAS
from src.ui import arte_ciudad, casillas_ciudad, sprites

ELEVACION_BASE = 4  # px: la base del prop queda apenas sobre el borde inferior de su huella
_cache = {}


def id_arte(prop):
    """Id de arte del prop para arte_ciudad (y la lista blanca)."""
    if prop.tipo == "arbol":
        return f"arbol:{prop.variante}"
    if prop.tipo in zonas_ciudad.PROPS_BACKROOMS:
        return f"backrooms:{prop.tipo}"
    return f"urbano:{prop.tipo}"


def imagen(prop):
    """Imagen del prop (cacheada por arte_ciudad), o su placeholder."""
    figura = arte_ciudad.imagen(id_arte(prop))
    if figura is None:
        if prop.tipo == "arbol":
            return casillas_ciudad.casilla_arbol()
        if prop.tipo in FAROLAS:
            return casillas_ciudad.casilla_farola()
        return _bolardo()
    return _orientada(prop, figura)


def origen(prop):
    """De dónde sale el arte del prop: todos los props de la ciudad son del
    arte que ya se veía bien (pack urbano, Trees_Vol2, Backrooms)."""
    return "antiguo"


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


def rect_imagen(prop):
    """Rect (px del mundo) que ocupa la imagen del prop, apoyada en su base."""
    clave = ("rect", prop)
    if clave not in _cache:
        _cache[clave] = imagen(prop).get_rect(midbottom=base(prop))
    return _cache[clave]


def todos():
    return ciudad_mapa.DECORACION


def visibles(rect_mundo):
    """Props cuya imagen toca `rect_mundo` (la vista de la cámara)."""
    return [prop for prop in todos() if rect_imagen(prop).colliderect(rect_mundo)]


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
        sprites.dibujar_sombra(pantalla, (x + dx, y + dy), max(TAM_CASILLA // 2, figura.get_width() * 2 // 3))
        pantalla.blit(figura, figura.get_rect(midbottom=(x + dx, y + dy)))


def farolas():
    """Centros (px del mundo) de las farolas de todos los modelos, para sus halos."""
    return [ciudad_mapa.centro_casilla(*p.casilla) for p in ciudad_mapa.DECORACION if p.tipo in FAROLAS]
