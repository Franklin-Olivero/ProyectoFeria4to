"""La ciudad se dibuja aunque falte el arte (ventana dummy): sin el atlas de
los packs cyberpunk, sin Backrooms ni pack urbano, todo cae al pixel art."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon import ciudad_mapa  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.ui import cargador_assets, cargador_backrooms, casas_render, ciudad_render, decoracion_ciudad  # noqa: E402
from src.ui import edificios_ciudad, tiles_ciudad  # noqa: E402


def _limpiar():
    cargador_backrooms.limpiar_cache()
    cargador_assets._hojas.clear()
    cargador_assets._recortes.clear()
    cargador_assets._atlas.clear()
    ciudad_render._cache.clear()
    casas_render._cache.clear()
    decoracion_ciudad._cache.clear()
    edificios_ciudad._cache.clear()
    tiles_ciudad._cache.clear()


def test_sin_ningun_arte_la_ciudad_igual_se_dibuja(monkeypatch):
    pygame.init()
    pantalla = pygame.display.set_mode((1280, 720))
    monkeypatch.setattr(assets, "RUTA_BACKROOMS", os.path.join("assets", "no_existe"))
    monkeypatch.setattr(assets, "RUTA_PROPS_URBANOS", os.path.join("assets", "no_existe.png"))
    monkeypatch.setattr(assets, "RUTA_ATLAS_CIUDAD", os.path.join("assets", "no_existe.png"))
    monkeypatch.setattr(assets, "RUTA_ATLAS_CIUDAD_JSON", os.path.join("assets", "no_existe.json"))
    _limpiar()
    try:
        assert not tiles_ciudad.disponible()
        mundo = ciudad_render.render_panoramico(Partida())
        assert mundo.get_size() == (64 * 48, 47 * 48)
        assert tiles_ciudad.origen(10, 10) == "antiguo"
        assert all(decoracion_ciudad.origen(p) == "antiguo" for p in ciudad_mapa.DECORACION)
    finally:
        monkeypatch.undo()
        _limpiar()
    assert pantalla is not None


def test_con_el_atlas_el_suelo_y_las_casas_salen_de_los_packs():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    _limpiar()
    assert tiles_ciudad.disponible()
    assert tiles_ciudad.origen(10, 10) == "nuevo"  # calle
    assert tiles_ciudad.origen(*ciudad_mapa.PARQUE[:2]) == "antiguo"  # pasto: los packs no traen vegetación
    assert tiles_ciudad.casilla(10, 10).get_size() == (48, 48)
    assert all(casas_render.compuesta(i) for i in range(len(ciudad_mapa.CASAS)))
    assert edificios_ciudad.compuesto("Hospital") and not edificios_ciudad.compuesto("Colegio")
