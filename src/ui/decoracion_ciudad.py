"""Decoración de Ciudad Nova: arte de cada prop y dibujo ordenado por Y.

Los props salen de ciudad_mapa.DECORACION (reglas en
src/dungeon/layout_decoracion.py, identidad por zona en
src/dungeon/zonas_ciudad.py). Aquí solo se resuelve su imagen por los
cargadores centrales con caché: el atlas de la ciudad (packs cyberpunk:
máquinas, tótems, servidores... assets.PROPS_CIUDAD), el pack urbano
(cargador_assets, assets.PROPS_URBANOS: farolas, bancas, terrazas), los
árboles de Trees_Vol2 y los props del pack Backrooms (cargador_backrooms:
antena, conos, letrero). La Torre de Datos (ciudad_mapa.MONUMENTO) se
ordena junto con ellos. Todo se dibuja con una sombra suave y junto con
el jugador, ordenado por la base de cada uno (el borde inferior de su
huella). Si falta un PNG, el árbol y las farolas vuelven a su casilla en
pixel art y el resto a un bolardo: nunca se cae el juego.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import ciudad_mapa, zonas_ciudad
from src.dungeon.layout_decoracion import CAPA_ARBOL, FAROLAS, Prop
from src.ui import cargador_assets, cargador_backrooms, casillas_ciudad, sprites

ELEVACION_BASE = 4  # px: la base del prop queda apenas sobre el borde inferior de su huella
_cache = {}
TORRE = Prop("torre_datos", ciudad_mapa.MONUMENTO[:2], ancho=ciudad_mapa.MONUMENTO[2], alto=ciudad_mapa.MONUMENTO[3])


def imagen(prop):
    """Imagen del prop (cacheada por el cargador), o su placeholder."""
    if prop.tipo == "torre_datos":
        return _torre()
    if prop.tipo == "arbol":
        imagen_prop = cargador_assets.arbol(prop.variante)
        return imagen_prop if imagen_prop is not None else casillas_ciudad.casilla_arbol()
    if prop.tipo in assets.PROPS_CIUDAD:
        imagen_prop = cargador_assets.pieza_ciudad(assets.PROPS_CIUDAD[prop.tipo])
        return imagen_prop if imagen_prop is not None else _bolardo()
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


def origen(prop):
    """'nuevo' si el arte del prop sale de los packs cyberpunk, si no 'antiguo'."""
    if prop.tipo == "torre_datos" or prop.tipo in assets.PROPS_CIUDAD:
        return "nuevo" if cargador_assets.pieza_ciudad(assets.PROPS_CIUDAD.get(prop.tipo, assets.PIEZA_TORRE_DATOS)) \
            is not None else "antiguo"
    return "antiguo"


def _torre():
    """La Torre de Datos de la Plaza: el pilar neón del pack, recortado desde arriba."""
    if "torre" not in _cache:
        pieza = cargador_assets.pieza_ciudad(assets.PIEZA_TORRE_DATOS)
        if pieza is None:
            _cache["torre"] = casillas_ciudad.casilla_farola()
        else:
            alto = min(pieza.get_height(), assets.ALTO_TORRE_DATOS)
            _cache["torre"] = pieza.subsurface((0, 0, pieza.get_width(), alto))
    return _cache["torre"]


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


def todos():
    """Los props de la ciudad más la Torre de Datos de la Plaza."""
    return ciudad_mapa.DECORACION + (TORRE,)


def visibles(rect_mundo):
    """Props cuya imagen toca `rect_mundo` (la vista de la cámara)."""
    return [prop for prop in todos() if _figura(prop).colliderect(rect_mundo)]


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
