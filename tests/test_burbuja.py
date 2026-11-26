"""Burbuja Comunitaria del Ciudadano (src/entities/burbuja.py): frena las
balas enemigas que entran al domo y cura a los aliados de adentro."""

import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import CURACION_BURBUJA_POR_S  # noqa: E402
from src.entities.burbuja import aplicar_burbujas, burbujas_activas  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.entities.projectile import Proyectil  # noqa: E402

ROJO = (255, 0, 0)


@pytest.fixture(autouse=True)
def _ventana():
    pygame.init()
    pygame.display.set_mode((1280, 720))


def _ciudadano_con_burbuja(x=400, y=300):
    ciudadano = Ciudadano(x, y)
    ciudadano.carga_habilidad = ciudadano.carga_maxima
    assert ciudadano.usar_habilidad()
    assert ciudadano.burbuja_activa and ciudadano.tiempo_burbuja == assets.DURACION_BURBUJA
    return ciudadano


def _bala(centro):
    return Proyectil(centro, (-1, 0), 300, 1, ROJO)


def test_frena_las_balas_de_adentro_y_deja_las_de_afuera():
    ciudadano = _ciudadano_con_burbuja()
    cx, cy = ciudadano.rect.center
    adentro = _bala((cx + assets.RADIO_BURBUJA - 10, cy))
    afuera = _bala((cx + assets.RADIO_BURBUJA + 40, cy))
    balas = [adentro, afuera]
    frenados = aplicar_burbujas([ciudadano], balas, 1 / 60)
    assert balas == [afuera] and not adentro.vivo and afuera.vivo
    assert frenados == [adentro.rect.center]


def test_cura_a_los_de_adentro_sin_pasar_la_vida_maxima():
    ciudadano = _ciudadano_con_burbuja()
    aliado = Candidato(*ciudadano.rect.topleft)
    lejos = Candidato(ciudadano.rect.x + 600, ciudadano.rect.y)
    for jugador in (ciudadano, aliado, lejos):
        jugador.vida = jugador.vida_maxima - 1
    aplicar_burbujas([ciudadano, aliado, lejos], [], 1.0)
    assert ciudadano.vida == pytest.approx(ciudadano.vida_maxima - 1 + CURACION_BURBUJA_POR_S)
    assert aliado.vida == pytest.approx(aliado.vida_maxima - 1 + CURACION_BURBUJA_POR_S)
    assert lejos.vida == lejos.vida_maxima - 1
    for _ in range(10):
        aplicar_burbujas([ciudadano, aliado], [], 1.0)
    assert aliado.vida == aliado.vida_maxima and ciudadano.vida == ciudadano.vida_maxima


def test_no_levanta_caidos_ni_toca_fantasmas():
    ciudadano = _ciudadano_con_burbuja()
    caido = Candidato(*ciudadano.rect.topleft)
    caido.vida = 0
    fantasma = Candidato(*ciudadano.rect.topleft)
    fantasma.vida = 1
    fantasma.expulsado = True
    aplicar_burbujas([ciudadano, caido, fantasma], [], 1.0)
    assert caido.vida == 0 and fantasma.vida == 1


def test_sin_burbuja_no_hace_nada_y_se_apaga_con_el_tiempo():
    ciudadano = Ciudadano(400, 300)
    bala = _bala(ciudadano.rect.center)
    assert aplicar_burbujas([ciudadano], [bala], 1.0) == [] and bala.vivo
    ciudadano = _ciudadano_con_burbuja()
    ciudadano.actualizar_habilidad(assets.DURACION_BURBUJA + 0.1)
    assert not ciudadano.burbuja_activa and burbujas_activas([ciudadano]) == []
    # Un Ciudadano caído no sostiene el domo.
    ciudadano = _ciudadano_con_burbuja()
    ciudadano.vida = 0
    assert burbujas_activas([ciudadano]) == []


def test_en_el_frame_de_combate_la_bala_no_llega_al_ciudadano():
    import Main
    from src.core.entrada import InputJugador
    from src.dungeon.cuarto import Cuarto
    from src.dungeon.gracia_entrada import GraciaEntrada
    from src.ui.particulas import SistemaParticulas

    cuarto = Cuarto(nombre_zona="Hospital", direcciones_puertas=("N", "E", "S", "W"), nivel_toxicidad=70,
                    es_final=False, rng=random.Random(1), semilla_visual=1)
    cuarto.gracia = GraciaEntrada()
    cuarto.enemigos.clear()
    cuarto.coberturas.lista.clear()
    ciudadano = _ciudadano_con_burbuja(*cuarto.rect.center)
    ciudadano.vida = ciudadano.vida_maxima - 1
    cx, cy = ciudadano.rect.center
    balas = [Proyectil((cx + assets.RADIO_BURBUJA + 60, cy), (-1, 0), 400, 1, ROJO)]
    quieto = InputJugador(movimiento=(0, 0), punto_apuntado=None, direccion_apuntado=None,
                          disparando=False, habilidad=False, dash=False)

    class _SinTextos:
        def agregar(self, *args, **kwargs):
            pass

    original = Main._leer_entrada
    Main._leer_entrada = lambda entrada, teclas, sacudida: quieto
    try:
        for _ in range(60):
            Main._frame_de_combate(1 / 60, [ciudadano], [None], cuarto, [[]], balas, _SinTextos(),
                                   SistemaParticulas())
    finally:
        Main._leer_entrada = original
    assert balas == []  # la bala se deshizo en el domo
    assert ciudadano.vida > ciudadano.vida_maxima - 1  # no le pegó y además se curó


def test_el_domo_viaja_por_la_red():
    from Online.sesion_red import _datos_extra

    ciudadano = _ciudadano_con_burbuja()
    assert _datos_extra(ciudadano)["bur"] == pytest.approx(assets.DURACION_BURBUJA)
    ciudadano.actualizar_habilidad(assets.DURACION_BURBUJA + 1)
    assert _datos_extra(ciudadano)["bur"] == 0
    assert "bur" not in _datos_extra(Candidato(0, 0))  # solo el Ciudadano lo manda
