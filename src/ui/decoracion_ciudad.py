"""Decoración de Ciudad Nova: arte de cada prop y dibujo ordenado por Y.

Los props salen de ciudad_mapa.DECORACION (reglas en
src/dungeon/layout_decoracion.py). Aquí solo se resuelve su imagen, por
el cargador central (src/ui/cargador_assets.py) con caché, y se dibujan
junto con el jugador ordenados por la base de cada uno: el jugador pasa
por delante de un árbol si está más abajo y queda detrás si está más
arriba. Si falta un PNG, el árbol y la farola vuelven a su casilla en
pixel art y el resto a un bolardo: nunca se cae el juego.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import ciudad_mapa
from src.ui import cargador_assets, casillas_ciudad, sprites

ELEVACION_BASE = 4  # px: la base del prop queda apenas sobre el borde inferior de su casilla


def imagen(prop):
    """Imagen del prop (cacheada por el cargador), o su placeholder."""
    if prop.tipo == "arbol":
        imagen_prop = cargador_assets.arbol(prop.variante)
        return imagen_prop if imagen_prop is not None else casillas_ciudad.casilla_arbol()
    imagen_prop = cargador_assets.prop_urbano(prop.tipo)
    if imagen_prop is not None:
        return imagen_prop
    if prop.tipo == "farola":
        return casillas_ciudad.casilla_farola()
    return _bolardo()


_bolardo_cache = []


def _bolardo():
    if not _bolardo_cache:
        superficie = pygame.Surface((TAM_CASILLA // 3, TAM_CASILLA // 2), pygame.SRCALPHA)
        pygame.draw.rect(superficie, assets.COLOR_COLUMNA, superficie.get_rect(), border_radius=4)
        _bolardo_cache.append(superficie)
    return _bolardo_cache[0]


def base(prop):
    """Punto (px del mundo) donde se apoya el prop: centro inferior de su casilla."""
    col, fila = prop.casilla
    return (round((col + 0.5) * TAM_CASILLA), (fila + 1) * TAM_CASILLA - ELEVACION_BASE)


def visibles(rect_mundo):
    """Props cuya imagen toca `rect_mundo` (la vista de la cámara)."""
    salida = []
    for prop in ciudad_mapa.DECORACION:
        figura = imagen(prop).get_rect(midbottom=base(prop))
        if figura.colliderect(rect_mundo):
            salida.append(prop)
    return salida


def dibujar_con_jugador(pantalla, rect_mundo, dx, dy, dibujar_jugador, base_jugador):
    """Props visibles y el jugador en orden de base (Y): lo de abajo tapa a
    lo de arriba. `dibujar_jugador()` lo dibuja; `base_jugador` es la y
    (px del mundo) de sus pies."""
    capas = [(base(p)[1], 1 if p.capa == "arbol" else 0, p) for p in visibles(rect_mundo)]
    capas.append((base_jugador, 2, None))
    for _, _, prop in sorted(capas, key=lambda c: (c[0], c[1])):
        if prop is None:
            dibujar_jugador()
            continue
        figura = imagen(prop)
        x, y = base(prop)
        if prop.capa == "arbol":
            sprites.dibujar_sombra(pantalla, (x + dx, y + dy), figura.get_width() * 2 // 3)
        pantalla.blit(figura, figura.get_rect(midbottom=(x + dx, y + dy)))


def farolas():
    """Centros (px del mundo) de las farolas, para sus halos de luz."""
    return [ciudad_mapa.centro_casilla(*p.casilla) for p in ciudad_mapa.DECORACION if p.tipo == "farola"]
