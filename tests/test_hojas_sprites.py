"""Hojas de sprites: lectura del atlas de Pixelbolt, elección del cuadro
por tiempo (lógica pura) y carga con fallback en sprites.py."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.ui import sprites  # noqa: E402
from src.ui.ruta_sprites import cuadros_de_atlas, indice_por_tiempo, ruta_atlas, ruta_sprite  # noqa: E402

ATLAS = {
    "frames": {
        "quieto": {"frame": {"x": 0, "y": 0, "w": 16, "h": 20}, "duration": 150},
        "paso": {"frame": {"x": 16, "y": 0, "w": 16, "h": 20}, "duration": 50},
        "dash": {"frame": {"x": 32, "y": 0, "w": 16, "h": 20}, "duration": 120},
    },
    "animations": {
        "caminar": {"frames": ["quieto", "paso", "quieto"], "loop": True},
        "dash": {"frames": ["dash"], "loop": False},
    },
}


@pytest.fixture(autouse=True)
def cache_limpio():
    sprites.limpiar_cache_hojas()
    yield
    sprites.limpiar_cache_hojas()


def test_ruta_sprite_y_atlas():
    assert ruta_sprite("x", "carpeta", existe=lambda r: True) == os.path.join("carpeta", "x.png")
    assert ruta_sprite("x", "carpeta", existe=lambda r: False) is None
    assert ruta_atlas(os.path.join("c", "x.png")) == os.path.join("c", "x.atlas.json")


def test_cuadros_de_atlas_respeta_el_orden_de_la_animacion():
    cuadros = cuadros_de_atlas(ATLAS)
    assert cuadros["caminar"] == [((0, 0, 16, 20), 150), ((16, 0, 16, 20), 50), ((0, 0, 16, 20), 150)]
    assert cuadros["dash"] == [((32, 0, 16, 20), 120)]


def test_cuadros_de_atlas_sin_animaciones_usa_default():
    atlas = {"frames": ATLAS["frames"]}
    assert list(cuadros_de_atlas(atlas)) == ["default"]
    assert len(cuadros_de_atlas(atlas)["default"]) == 3


def test_indice_por_tiempo_recorre_en_bucle():
    duraciones = [150, 50, 150]  # total 350 ms
    assert indice_por_tiempo(duraciones, 0.0) == 0
    assert indice_por_tiempo(duraciones, 0.149) == 0
    assert indice_por_tiempo(duraciones, 0.150) == 1
    assert indice_por_tiempo(duraciones, 0.2) == 2
    assert indice_por_tiempo(duraciones, 0.35) == 0  # vuelve a empezar
    assert indice_por_tiempo(duraciones, 0.36) == 0
    assert indice_por_tiempo([120], 99.0) == 0
    assert indice_por_tiempo([], 1.0) == 0
    assert indice_por_tiempo(duraciones, -5.0) == 0


def _guardar_hoja(carpeta, nombre):
    hoja = pygame.Surface((48, 20), pygame.SRCALPHA)
    for i, color in enumerate(((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))):
        hoja.fill(color, (i * 16, 0, 16, 20))
    pygame.image.save(hoja, str(carpeta / f"{nombre}.png"))
    (carpeta / f"{nombre}.atlas.json").write_text(json.dumps(ATLAS), encoding="utf-8")


def test_sprite_jugador_usa_la_hoja_del_rol_y_escala(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_SPRITES_JUGADORES", str(tmp_path))
    _guardar_hoja(tmp_path, "influencer")
    quieto = sprites.sprite_jugador((1, 2, 3), rol="influencer")
    assert quieto.get_size() == (16 * assets.ESCALA_PIXEL, 20 * assets.ESCALA_PIXEL)
    assert quieto.get_at((0, 0))[:3] == (255, 0, 0)
    # Caminando, en el segundo cuadro; quieto siempre el primero.
    paso = sprites.sprite_jugador((1, 2, 3), rol="influencer", tiempo=0.16, caminando=True)
    assert paso.get_at((0, 0))[:3] == (0, 255, 0)
    assert sprites.sprite_jugador((1, 2, 3), rol="influencer", tiempo=0.16).get_at((0, 0))[:3] == (255, 0, 0)
    assert sprites.sprite_jugador((1, 2, 3), rol="influencer", dash=True).get_at((0, 0))[:3] == (0, 0, 255)
    # Un rol sin hoja cae al muñeco en código (12x16 por ESCALA_PIXEL).
    assert sprites.sprite_jugador((1, 2, 3), rol="candidato").get_size() == (36, 48)


def test_sprite_jefe_v2_es_el_flame_golem_y_su_hitbox_lo_contiene_casi():
    sprites.limpiar_cache_hojas()
    idle = sprites.sprite_jefe(0.0)
    furia = sprites.sprite_jefe(0.0, furia=True)
    assert idle.get_width() > 2 * assets.TAMANIO_ENEMIGO_TIPO["perseguidor"]
    assert idle.get_width() >= assets.TAMANIO_JEFE and furia.get_height() >= assets.TAMANIO_JEFE
    assert sprites.sprite_jefe(0.0) is idle  # cacheado


def test_sprite_jefe_con_y_sin_hoja(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "JEFE_V2", None)
    monkeypatch.setattr(assets, "RUTA_SPRITES_JEFE", str(tmp_path))
    placeholder = sprites.sprite_jefe(0.0)
    assert placeholder.get_size() == (22 * assets.ESCALA_SPRITE_JEFE, 22 * assets.ESCALA_SPRITE_JEFE)
    _guardar_hoja(tmp_path, assets.ID_SPRITE_JEFE)
    sprites.limpiar_cache_hojas()
    assert sprites.sprite_jefe(0.0).get_size() == (16 * assets.ESCALA_SPRITE_JEFE, 20 * assets.ESCALA_SPRITE_JEFE)


def test_retrato_rol_escala_a_la_altura_pedida(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_SPRITES_RETRATOS", str(tmp_path))
    assert sprites.retrato_rol("periodista", 100) is None
    pygame.image.save(pygame.Surface((200, 400), pygame.SRCALPHA), str(tmp_path / "periodista.png"))
    sprites.limpiar_cache_hojas()
    assert sprites.retrato_rol("periodista", 100).get_size() == (50, 100)


def test_cuadro_por_nombre_y_cuadros_del_cuarto(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_SPRITES_CUARTO", str(tmp_path))
    assert sprites.cuadro_cuarto("piso_a") is None
    assert sprites.cuadro_puerta("abierta") is None
    assert sprites.sprite_charco(True, 0.0, 45) is None
    _guardar_hoja(tmp_path, assets.ID_SPRITE_CUARTO)
    sprites.limpiar_cache_hojas()
    cuadro = sprites.cuadro_cuarto("paso")
    assert cuadro.get_size() == (16 * assets.ESCALA_PIXEL, 20 * assets.ESCALA_PIXEL)
    assert cuadro.get_at((0, 0))[:3] == (0, 255, 0)
    assert sprites.cuadro_cuarto("no_existe") is None


def test_sprite_proyectil_por_tamanio():
    assert sprites.sprite_proyectil((255, 0, 0), 8).get_size() == (8, 8)
    assert sprites.sprite_proyectil((255, 0, 0), 12).get_size() == (12, 12)
    assert sprites.sprite_proyectil((255, 0, 0), 26).get_size() == (26, 26)
    assert sprites.sprite_proyectil((255, 0, 0), 7) is None  # sin plantilla: rect
    assert sprites.sprite_proyectil((255, 0, 0), 10, sprites.RAYO_5).get_size() == (10, 10)


def test_el_repo_trae_hojas_para_los_4_roles_los_3_enemigos_y_el_jefe():
    for id_sprite in (assets.ID_SPRITE_CUARTO, assets.ID_SPRITE_PUERTA, assets.ID_SPRITE_CHARCO):
        assert ruta_sprite(id_sprite, assets.RUTA_SPRITES_CUARTO) is not None
    for rol in ("ciudadano", "influencer", "periodista", "candidato"):
        assert ruta_sprite(rol, assets.RUTA_SPRITES_JUGADORES) is not None
        assert ruta_sprite(rol, assets.RUTA_SPRITES_RETRATOS) is not None
    for tipo in assets.ID_SPRITE_ENEMIGO.values():
        assert ruta_sprite(tipo, assets.RUTA_SPRITES_ENEMIGOS) is not None
    assert ruta_sprite(assets.ID_SPRITE_JEFE, assets.RUTA_SPRITES_JEFE) is not None
