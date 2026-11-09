"""Agua de Ciudad Nova con tiles del pack Backrooms (puro, sin Pygame).

    capas(mapa, terrenos) -> [(nombre, filas de ids o -1)] de abajo hacia arriba
    tiles_usados(capas_agua, terrenos) -> ids que hay que empaquetar (con sus cuadros animados)

La fuente ('F' en ciudad_mapa.MAPA) es un borde de azulejos (pool_tile)
con agua de piscina (pool_water) en las casillas interiores; el estanque
('~') es agua estancada (flood_water) sobre el pasto. Ambos salen del
auto-tiling blob (src/dungeon/autotile.py): basta con marcar sus casillas
en el mapa para que bordes y esquinas encajen.
"""

import json
import os

from src.core import assets
from src.dungeon import autotile

FUENTE = "F"
ESTANQUE = "~"


def cargar_terrenos(raiz="."):
    try:
        with open(os.path.join(raiz, assets.RUTA_TERRENOS_BACKROOMS), encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return None


def _grilla(mapa, letra):
    return [[ch == letra for ch in fila] for fila in mapa]


def _interior(grilla):
    alto, ancho = len(grilla), len(grilla[0])

    def lleno(c, f):
        return 0 <= c < ancho and 0 <= f < alto and grilla[f][c]

    return [[grilla[f][c] and all(lleno(c + dc, f + df) for dc, df in ((1, 0), (-1, 0), (0, 1), (0, -1)))
             for c in range(ancho)] for f in range(alto)]


def capas(mapa, terrenos):
    fuente = _grilla(mapa, FUENTE)
    wang = terrenos["wang"]
    return [
        ("borde_fuente", autotile.resolver(fuente, wang[assets.TERRENO_BORDE_FUENTE])),
        ("agua_fuente", autotile.resolver(_interior(fuente), wang[assets.TERRENO_AGUA_FUENTE])),
        ("estanque", autotile.resolver(_grilla(mapa, ESTANQUE), wang[assets.TERRENO_ESTANQUE])),
    ]


def animacion(terrenos, id_tile):
    """[(id cuadro, ms)] del tile animado, o None si es quieto."""
    cuadros = terrenos.get("animaciones", {}).get(str(id_tile))
    return [tuple(c) for c in cuadros] if cuadros else None


def tiles_usados(capas_agua, terrenos):
    usados = {t for _, filas in capas_agua for fila in filas for t in fila if t >= 0}
    for id_tile in list(usados):
        for cuadro, _ in animacion(terrenos, id_tile) or ():
            usados.add(cuadro)
    return usados
