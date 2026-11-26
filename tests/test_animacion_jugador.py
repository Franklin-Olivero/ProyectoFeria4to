"""Animación de los personajes (src/ui/animacion_jugador.py): caminar con
rebote, respirar, parpadear y mirar hacia donde se camina o apunta."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.ui import animacion_jugador as anim  # noqa: E402
from src.ui import sprites  # noqa: E402

COLOR = (1, 2, 3)


@pytest.fixture(autouse=True)
def _pantalla():
    pygame.init()
    pygame.display.set_mode((10, 10))


def _pixeles(superficie):
    return tuple(tuple(superficie.get_at((x, y))[:4] for x in range(superficie.get_width()))
                 for y in range(superficie.get_height()))


@pytest.mark.parametrize("rol", assets.ROLES_APARIENCIA)
def test_bajar_mueve_el_cuerpo_y_deja_las_piernas(rol):
    datos = sprites._datos_hoja(rol)
    cuadro, partes = datos["cuadros"]["quieto"], datos["partes"]["quieto"]
    cuello, cadera = anim.zonas(partes)
    assert cuello is not None and cadera is not None and cuello < cadera
    bajado, _ = anim.bajar(cuadro, partes, cadera, 1)
    assert bajado[cadera + 3:] == cuadro[cadera + 3:]  # las piernas, iguales
    assert bajado[1:cadera] == cuadro[0:cadera - 1]  # lo de arriba, un renglón más abajo
    assert all(c is None for c in bajado[0])


@pytest.mark.parametrize("rol", assets.ROLES_APARIENCIA)
def test_los_ciclos_tienen_mas_cuadros_que_la_hoja(rol):
    datos = sprites._datos_hoja(rol)
    ciclos = anim.ciclos(datos["cuadros"], datos["partes"])
    caminar = [c for c, _, _ in ciclos["caminar"]]
    assert len(caminar) == 8 and len(set(caminar)) >= 6  # antes eran 3 cuadros distintos
    assert len({c for c, _, _ in ciclos[anim.ANIMACION_RESPIRAR]}) >= 3  # respira y parpadea
    assert sum(ms for _, _, ms in ciclos["caminar"]) == 600  # el mismo ritmo de paso de antes


@pytest.mark.parametrize("rol", ["ciudadano", "influencer", "candidato"])
def test_parpadea_cerrando_los_ojos(rol):
    datos = sprites._datos_hoja(rol)
    cuadro, partes = datos["cuadros"]["quieto"], datos["partes"]["quieto"]
    ojos = anim.ojos(cuadro, partes)
    assert len(ojos) == 2
    cerrado = anim.parpadear(cuadro, partes, ojos)
    for grupo in ojos:
        arriba = min(y for _, y in grupo)
        cambiados = [(x, y) for x, y in grupo if y == arriba and cerrado[y][x] != cuadro[y][x]]
        assert cambiados  # el ojo se tapó con piel
    # fuera de los ojos no cambia nada
    for y, fila in enumerate(cuadro):
        for x, color in enumerate(fila):
            if not any((x, y) in g for g in ojos):
                assert cerrado[y][x] == color


def test_con_lentes_no_hay_parpadeo_raro():
    datos = sprites._datos_hoja("periodista")
    assert anim.ojos(datos["cuadros"]["quieto"], datos["partes"]["quieto"]) == []


def test_quieto_respira_y_caminando_rebota():
    quieto = [sprites.sprite_jugador(COLOR, 3, rol="candidato", tiempo=t) for t in (0.1, 1.2, 2.0, 2.75)]
    assert len({id(c) for c in quieto}) >= 2  # quieto ya no es una foto
    paso = [sprites.sprite_jugador(COLOR, 3, rol="candidato", tiempo=0.075 * k + 0.001, caminando=True)
            for k in range(8)]
    assert len({id(c) for c in paso}) >= 6
    # Sin tiempo (retratos, tarjetas), el primer cuadro: el dibujo original.
    assert _pixeles(sprites.sprite_jugador(COLOR, 2, rol="ciudadano")) == \
        _pixeles(sprites._superficie_pixeles(sprites._datos_hoja("ciudadano")["cuadros"]["quieto"], 1))


def test_mira_hacia_la_izquierda():
    derecha = sprites.sprite_jugador(COLOR, 3, rol="influencer", tiempo=0.1)
    izquierda = sprites.sprite_jugador(COLOR, 3, rol="influencer", tiempo=0.1, mirando_izquierda=True)
    assert _pixeles(izquierda) == _pixeles(pygame.transform.flip(derecha, True, False))
    assert sprites.sprite_jugador(COLOR, 3, rol="influencer", tiempo=0.1, mirando_izquierda=True) is izquierda


def test_se_da_vuelta_segun_el_ultimo_paso():
    memoria = {}
    assert sprites.mira_izquierda(memoria, 100) is False
    assert sprites.mira_izquierda(memoria, 90) is True  # fue a la izquierda
    assert sprites.mira_izquierda(memoria, 90) is True  # quieto: sigue mirando hacia allá
    assert sprites.mira_izquierda(memoria, 90.2) is True  # un temblor no lo da vuelta
    assert sprites.mira_izquierda(memoria, 95) is False
