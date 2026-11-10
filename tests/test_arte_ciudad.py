"""Arte de Ciudad Nova: lista blanca, ajuste de paleta, paleta sobria y cero
solapes de imagen (ventana dummy)."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools"))
os.chdir(RAIZ)

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import MAX_FAMILIAS_DOMINANTES_CIUDAD, MAX_FRACCION_SATURADA_CIUDAD  # noqa: E402
from src.core.medicion_paleta import es_saturado, familia, medir  # noqa: E402
from src.dungeon import ciudad_mapa as cm, huellas_ciudad as hc  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.ui import arte_ciudad, cargador_assets, casas_render, ciudad_render, decoracion_ciudad  # noqa: E402
from src.ui import edificios_ciudad  # noqa: E402


@pytest.fixture(scope="module")
def panoramica():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    arte_ciudad.pedidos.clear()
    return ciudad_render.render_panoramico(Partida())


# ----------------------------------------------------------------------
# Lista blanca
# ----------------------------------------------------------------------

def test_todo_lo_que_la_ciudad_declara_esta_en_la_lista_blanca():
    for nombre in assets.TEXTURA_TERRENO_CIUDAD.values():
        assert arte_ciudad.permitido(f"ciudad:{nombre}"), nombre
    for nombre in (assets.PIEZA_BORDILLO, assets.PIEZA_LINEA_CARRIL, assets.PIEZA_CEBRA):
        assert arte_ciudad.permitido(f"ciudad:{nombre}"), nombre
    for prop in cm.DECORACION:
        assert arte_ciudad.permitido(decoracion_ciudad.id_arte(prop)), prop
    for id_arte in assets.AJUSTE_PALETA_CIUDAD:
        assert arte_ciudad.permitido(id_arte), id_arte


def test_el_render_solo_pide_ids_de_la_lista_blanca(panoramica):
    assert arte_ciudad.pedidos  # el render pasó por la puerta única
    assert arte_ciudad.pedidos <= assets.ASSETS_CIUDAD_PERMITIDOS, arte_ciudad.pedidos - assets.ASSETS_CIUDAD_PERMITIDOS


def test_un_id_fuera_de_la_lista_no_se_dibuja():
    for prohibido in ("ciudad:fachada_neon", "urbano:no_existe", "arbol:90", "arbol:75", "ciudad:techo_3"):
        with pytest.raises(arte_ciudad.ArteNoPermitido):
            arte_ciudad.imagen(prohibido)


def test_el_atlas_trae_solo_lo_permitido():
    piezas = set(cargador_assets.rects_atlas(assets.RUTA_ATLAS_CIUDAD_JSON))
    assert piezas and {f"ciudad:{p}" for p in piezas} <= assets.ASSETS_CIUDAD_PERMITIDOS


def test_los_arboles_de_fantasia_no_estan_permitidos():
    for numero in (75, 78, 81, 84, 87, 90):
        assert not arte_ciudad.permitido(f"arbol:{numero}")


# ----------------------------------------------------------------------
# Paleta
# ----------------------------------------------------------------------

def test_ajustar_paleta_baja_la_saturacion_y_conserva_el_alfa():
    pygame.init()
    figura = pygame.Surface((2, 1), pygame.SRCALPHA)
    figura.fill((255, 0, 0, 255))
    figura.set_at((0, 0), (0, 0, 0, 0))
    gris = cargador_assets.ajustar_paleta(figura, 0.0)
    assert gris.get_at((1, 0))[0] == gris.get_at((1, 0))[1] == gris.get_at((1, 0))[2]
    assert gris.get_at((0, 0))[3] == 0 and gris.get_at((1, 0))[3] == 255
    medio = cargador_assets.ajustar_paleta(figura, 0.5, 0.5)
    r, g, _, _ = medio.get_at((1, 0))
    assert g < r < 255 // 2 + 10
    assert cargador_assets.ajustar_paleta(figura) is figura  # sin ajuste no copia


def test_medicion_de_paleta_pura():
    assert es_saturado((255, 0, 200)) and not es_saturado((90, 92, 100)) and not es_saturado((60, 0, 0))
    assert familia((128, 128, 128)) == "neutro" and familia((40, 200, 60)) == "verde"
    resultado = medir([(128, 128, 128)] * 90 + [(255, 0, 200)] * 10)
    assert resultado["fraccion_saturada"] == pytest.approx(0.10)
    assert resultado["dominantes"][0] == "neutro"


def test_la_panoramica_es_sobria(panoramica):
    import medir_paleta_ciudad
    resultado = medir(medir_paleta_ciudad.pixeles(panoramica))
    assert resultado["fraccion_saturada"] < MAX_FRACCION_SATURADA_CIUDAD, resultado["fraccion_saturada"]
    assert len(resultado["dominantes"]) <= MAX_FAMILIAS_DOMINANTES_CIUDAD, resultado["dominantes"]


# ----------------------------------------------------------------------
# Cero solapes de imagen
# ----------------------------------------------------------------------

def _edificios():
    return [(f"edificio {z}", tuple(edificios_ciudad.rect(z))) for z in cm.EDIFICIOS] + \
        [(f"casa {i}", tuple(casas_render.rect(i))) for i in range(len(cm.CASAS))]


def test_ninguna_imagen_de_prop_ni_edificio_se_monta_sobre_otra(panoramica):
    """Las copas de los árboles pueden caer sobre la banqueta (se dibujan por
    Y); todo lo demás (bancas, farolas, carteles...) no toca a nada."""
    rects = _edificios() + [(f"{p.tipo} {p.casilla}", tuple(decoracion_ciudad.rect_imagen(p)))
                            for p in cm.DECORACION if p.tipo != "arbol"]
    assert hc.solapes_rects(rects) == []


def test_ninguna_copa_tapa_un_edificio(panoramica):
    edificios = _edificios()
    for prop in cm.DECORACION:
        if prop.tipo == "arbol":
            copa = ("copa", tuple(decoracion_ciudad.rect_imagen(prop)))
            assert not any(hc.solapes_rects([copa, edificio]) for edificio in edificios), prop
