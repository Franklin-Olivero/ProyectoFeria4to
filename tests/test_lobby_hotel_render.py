"""Cargador Backrooms y lobby del hotel con pygame (ventana dummy):
caché, damero si falta un asset (aviso una sola vez) y caída al lobby
clásico cuando falta el arte."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.ui import cargador_backrooms, escena_lobby_render, seleccion_rol  # noqa: E402
from src.ui.seleccion import SeleccionRoles  # noqa: E402


@pytest.fixture(autouse=True)
def ventana():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    cargador_backrooms.limpiar_cache()
    yield
    cargador_backrooms.limpiar_cache()


def test_tile_y_prop_del_grade_del_lobby_con_cache():
    grade = assets.GRADE_LOBBY
    assert cargador_backrooms.disponible(grade)
    tile = cargador_backrooms.tile(grade, 3148)
    assert tile.get_size() == (48, 48)
    assert cargador_backrooms.tile(grade, 3148) is tile
    sofa = cargador_backrooms.prop(grade, "hotel", "lobby_sofa")
    assert sofa.get_size() == (42 * 3, 24 * 3)
    assert cargador_backrooms.avisos() == set()


def test_asset_faltante_da_damero_y_avisa_una_sola_vez(capsys):
    pieza = cargador_backrooms.prop(assets.GRADE_LOBBY, "hotel", "no_existe", tamanio=(10, 8))
    assert pieza.get_size() == (30, 24)
    assert pieza.get_at((0, 0))[:3] == assets.COLOR_FALTANTE_BACKROOMS
    cargador_backrooms.prop(assets.GRADE_LOBBY, "hotel", "no_existe", tamanio=(10, 8))
    assert capsys.readouterr().err.count("no_existe") == 1
    assert ("hum", "prop", "hotel_no_existe") in cargador_backrooms.avisos()


def test_animacion_que_el_grade_no_trae_es_none_para_usar_la_quieta():
    assert cargador_backrooms.animacion(assets.GRADE_LOBBY, "no_es_una_animacion") is None


def test_grade_sin_empaquetar_no_esta_disponible_y_el_lobby_vuelve_al_clasico(monkeypatch):
    monkeypatch.setattr(assets, "RUTA_BACKROOMS", os.path.join("assets", "no_existe"))
    cargador_backrooms.limpiar_cache()
    assert escena_lobby_render.crear() is None
    vista = seleccion_rol.VistaSeleccion(4, None, ())
    assert not vista.hotel
    pantalla = pygame.display.get_surface()
    vista.dibujar(pantalla, _clases(), SeleccionRoles(1, 4), 80, False)


def _clases():
    import Main
    return Main.CLASES_ROL


def test_escena_del_hotel_se_dibuja_con_dos_jugadores_y_reducir_movimiento():
    escena = escena_lobby_render.crear()
    assert escena is not None
    vista = seleccion_rol.VistaSeleccion(4, escena, [])
    seleccion = SeleccionRoles(2, 4)
    seleccion.cursores[1].indice = 2
    seleccion.cursores[1].confirmar()
    pantalla = pygame.display.get_surface()
    for reducir in (False, True):
        vista.actualizar(0.5, seleccion)
        vista.dibujar(pantalla, _clases(), seleccion, 50, True, reducir)
    assert cargador_backrooms.avisos() == set()


def test_raton_usa_las_tarjetas_del_diseno_activo():
    clasica = seleccion_rol.rect_tarjeta(0)
    hotel = seleccion_rol.rect_tarjeta(0, hotel=True)
    assert hotel.top > clasica.top and hotel.height < clasica.height
    punto = (hotel.centerx, hotel.bottom - 4)
    assert seleccion_rol.tarjeta_en(punto, 4, hotel=True) == 0
    vista = seleccion_rol.VistaSeleccion(4, escena_lobby_render.crear(), [])
    assert vista.tarjeta_en((clasica.centerx, clasica.top + 4), 4) is None  # sobre la escena, no sobre la tarjeta
    assert vista.tarjeta_en(punto, 4) == 0
