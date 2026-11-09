"""La ciudad se dibuja aunque falte el arte nuevo (ventana dummy)."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.ui import cargador_assets, cargador_backrooms, casas_render, ciudad_render, decoracion_ciudad  # noqa: E402


def _limpiar():
    cargador_backrooms.limpiar_cache()
    cargador_assets._hojas.clear()
    cargador_assets._recortes.clear()
    ciudad_render._cache.clear()
    casas_render._cache.clear()
    decoracion_ciudad._cache.clear()


def test_sin_backrooms_ni_pack_urbano_la_ciudad_igual_se_dibuja(monkeypatch):
    pygame.init()
    pantalla = pygame.display.set_mode((1280, 720))
    monkeypatch.setattr(assets, "RUTA_BACKROOMS", os.path.join("assets", "no_existe"))
    monkeypatch.setattr(assets, "RUTA_PROPS_URBANOS", os.path.join("assets", "no_existe.png"))
    _limpiar()
    try:
        mundo = ciudad_render.render_panoramico(Partida())
        assert mundo.get_size() == (64 * 48, 47 * 48)
        assert ciudad_render._agua() == (None, None)  # sin tiles: sin agua animada, pero sin caerse
    finally:
        monkeypatch.undo()
        _limpiar()
    assert pantalla is not None
