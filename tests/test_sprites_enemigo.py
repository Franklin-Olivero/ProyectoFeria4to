"""Arte intercambiable de los enemigos.

La regla de qué archivo usar (ruta_sprite_enemigo) es pura; los tests
de sprite_enemigo crean Surfaces en memoria, que no necesitan ventana
(SDL_VIDEODRIVER=dummy por si acaso).
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.entities.tipos_enemigo import TipoEnemigo  # noqa: E402
from src.ui import sprites  # noqa: E402
from src.ui.ruta_sprites import ruta_sprite_enemigo  # noqa: E402


@pytest.fixture(autouse=True)
def cache_limpio():
    sprites.limpiar_cache_enemigos()
    yield
    sprites.limpiar_cache_enemigos()


def test_ruta_con_y_sin_archivo():
    assert ruta_sprite_enemigo("tirador", "x", existe=lambda ruta: True) == os.path.join("x", "tirador.png")
    assert ruta_sprite_enemigo("tirador", "x", existe=lambda ruta: False) is None
    # Por defecto busca en assets/sprites/enemigos/: el perseguidor ya
    # tiene arte real; un id sin PNG cae al placeholder.
    assert ruta_sprite_enemigo("perseguidor") == os.path.join(assets.RUTA_SPRITES_ENEMIGOS, "perseguidor.png")
    assert ruta_sprite_enemigo("no_existe") is None


def test_cada_tipo_tiene_id_colores_y_tamano():
    for tipo in TipoEnemigo:
        clave = tipo.value
        assert assets.ID_SPRITE_ENEMIGO[clave]
        assert clave in assets.COLOR_PRINCIPAL_ENEMIGO and clave in assets.COLOR_SECUNDARIO_ENEMIGO
        assert assets.TAMANIO_ENEMIGO_TIPO[clave] > 0


def test_sprite_distinto_por_tipo_y_cacheado():
    imagenes = {tipo: sprites.sprite_enemigo(tipo) for tipo in TipoEnemigo}
    pixeles = {pygame.image.tobytes(imagen, "RGBA") for imagen in imagenes.values()}
    assert len(pixeles) == len(TipoEnemigo)
    for tipo, imagen in imagenes.items():
        assert sprites.sprite_enemigo(tipo) is imagen
        assert sprites.sprite_enemigo(tipo.value) is imagen  # también acepta el texto


def test_carga_el_png_si_existe_y_si_no_usa_el_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_SPRITES_ENEMIGOS", str(tmp_path))
    placeholder = sprites.sprite_enemigo(TipoEnemigo.TIRADOR)
    assert placeholder.get_size() == (42, 42)

    arte = pygame.Surface((20, 24), pygame.SRCALPHA)
    arte.fill((1, 2, 3, 255))
    pygame.image.save(arte, str(tmp_path / "tirador.png"))
    sprites.limpiar_cache_enemigos()
    cargado = sprites.sprite_enemigo(TipoEnemigo.TIRADOR)
    assert cargado.get_size() == (20, 24)
    assert cargado.get_at((0, 0))[:3] == (1, 2, 3)
    # Los demás tipos siguen con su placeholder.
    assert sprites.sprite_enemigo(TipoEnemigo.CURANDERO).get_size() == (42, 42)


def test_png_corrupto_cae_al_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_SPRITES_ENEMIGOS", str(tmp_path))
    (tmp_path / "curandero.png").write_bytes(b"no es un png")
    assert sprites.sprite_enemigo(TipoEnemigo.CURANDERO).get_size() == (42, 42)
