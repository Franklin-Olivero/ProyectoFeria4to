"""Arte nuevo: props de la ciudad (no cortan ninguna ruta), rects de las
hojas dentro de sus imágenes y fallback del cargador si falta una hoja."""

import os
import struct
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon import ciudad_mapa, zonas_ciudad  # noqa: E402
from src.ui import rutas_backrooms  # noqa: E402

_ATLAS_CIUDAD = rutas_backrooms.leer_atlas(assets.GRADE_CIUDAD)


def _tamanio_png(ruta):
    """(ancho, alto) leyendo la cabecera IHDR, sin pygame."""
    with open(ruta, "rb") as archivo:
        cabecera = archivo.read(24)
    return struct.unpack(">II", cabecera[16:24])


# ----------------------------------------------------------------------
# Props de Ciudad Nova
# ----------------------------------------------------------------------

def test_cada_prop_tiene_arte():
    for prop in ciudad_mapa.DECORACION:
        if prop.tipo == "arbol":
            assert os.path.exists(os.path.join(assets.RUTA_ARBOLES, f"arbol_{prop.variante:02d}.png")), prop
        elif prop.tipo in zonas_ciudad.PROPS_BACKROOMS:
            assert rutas_backrooms.rect_prop(_ATLAS_CIUDAD, zonas_ciudad.PROPS_BACKROOMS[prop.tipo]), prop
        else:
            assert prop.tipo in assets.PROPS_URBANOS, prop
        assert ciudad_mapa.es_solida(*prop.casilla) == prop.solido or not prop.solido


def test_con_props_se_llega_a_pie_a_todos_los_nodos_y_puertas():
    casillas = ciudad_mapa.grafo_casillas(ciudad_mapa.es_solida)
    alcanzables, _, _ = casillas.bfs(ciudad_mapa.SPAWN)
    alcanzables = set(alcanzables)
    for nodo in ciudad_mapa.NODOS_CALLE.values():
        assert nodo in alcanzables, nodo
    for col, fila in ciudad_mapa.ENTRADAS.values():
        assert (col, fila + 1) in alcanzables


# ----------------------------------------------------------------------
# Hojas y rects
# ----------------------------------------------------------------------

def test_props_urbanos_dentro_de_la_hoja():
    ancho, alto = _tamanio_png(assets.RUTA_PROPS_URBANOS)
    lado = assets.CELDA_PROPS_URBANOS
    for nombre, (col, fila) in assets.PROPS_URBANOS.items():
        assert (col + 1) * lado <= ancho and (fila + 1) * lado <= alto, nombre


def test_piezas_del_colegio_dentro_de_su_hoja():
    for nombre, (archivo, (x, y, w, h)) in assets.PIEZAS_COLEGIO.items():
        ancho, alto = _tamanio_png(os.path.join(assets.RUTA_COLEGIO, archivo))
        assert x >= 0 and y >= 0 and x + w <= ancho and y + h <= alto, nombre


# ----------------------------------------------------------------------
# Cargador: caché y fallback
# ----------------------------------------------------------------------

def test_cargador_recorta_y_cachea():
    from src.ui import cargador_assets

    banca = cargador_assets.prop_urbano("banca")
    assert banca is not None and banca.get_width() <= assets.CELDA_PROPS_URBANOS
    assert cargador_assets.prop_urbano("banca") is banca
    pupitre = cargador_assets.pieza_colegio("pupitre")
    assert pupitre.get_size() == tuple(assets.PIEZAS_COLEGIO["pupitre"][1][2:])


def test_cargador_sin_archivo_devuelve_none():
    from src.ui import cargador_assets

    assert cargador_assets.hoja(os.path.join("assets", "no_existe.png")) is None
    assert cargador_assets.recorte(os.path.join("assets", "no_existe.png"), (0, 0, 8, 8)) is None
    assert cargador_assets.prop_urbano("no_existe") is None
    assert cargador_assets.pieza_colegio("no_existe") is None
    # Un rect que se sale de la hoja tampoco rompe nada.
    assert cargador_assets.recorte(assets.RUTA_PROPS_URBANOS, (2000, 2000, 64, 64)) is None


def test_aula_y_fachada_del_colegio_se_dibujan():
    from src.ui import arte_colegio, temas_mazmorra

    pygame.display.init()
    assert arte_colegio.disponible()
    rect = pygame.Rect(120, 150, 1040, 480)
    fondo = temas_mazmorra.fondo(rect, "colegio", 3, ("N", "S"), 40)
    assert fondo.get_width() == 1280 // temas_mazmorra.P * temas_mazmorra.P
    fachada = arte_colegio.fachada(11, 6, 5, (120, 198, 288, 36), 2, 48)
    assert fachada.get_size() == (11 * 48, 6 * 48)
