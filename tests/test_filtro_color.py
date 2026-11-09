"""Filtro de daltonismo: la descomposición en pasadas reproduce la matriz y
el filtro aplicado sobre una superficie da M·color."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.audio.gestor_audio import a_volumen_mixer  # noqa: E402
from src.ui.combate_render import alfa_cono  # noqa: E402
from src.ui.filtro_color import (  # noqa: E402
    UMBRAL_COEFICIENTE,
    FiltroColor,
    coeficientes_por_vista,
    descomponer,
    matriz_correccion,
)

FILTROS = ("Protanopia", "Deuteranopia", "Tritanopia")


def test_ninguno_no_tiene_matriz():
    assert matriz_correccion("Ninguno") is None


@pytest.mark.parametrize("filtro", FILTROS)
def test_las_cuatro_vistas_cubren_las_nueve_entradas(filtro):
    m = matriz_correccion(filtro)
    coeficientes = coeficientes_por_vista(m)
    suma = sum(sum(abs(c) for c in valores) for valores in coeficientes.values())
    assert suma == pytest.approx(sum(abs(c) for fila in m for c in fila))


@pytest.mark.parametrize("filtro", FILTROS)
def test_las_pasadas_suman_la_matriz(filtro):
    m = matriz_correccion(filtro)
    pasadas, k = descomponer(m)
    reconstruida = {vista: [0.0, 0.0, 0.0] for vista in coeficientes_por_vista(m)}
    for vista, color, signo in pasadas:
        for canal in range(3):
            reconstruida[vista][canal] += signo * color[canal] / 255 * k
            assert 0 <= color[canal] <= 255
    for vista, esperados in coeficientes_por_vista(m).items():
        for obtenido, esperado in zip(reconstruida[vista], esperados):
            if abs(esperado) < UMBRAL_COEFICIENTE:
                esperado = 0.0
            assert obtenido == pytest.approx(esperado, abs=2 * k / 255)


@pytest.mark.parametrize("filtro", FILTROS)
def test_las_sumas_van_antes_que_las_restas(filtro):
    signos = [signo for _, _, signo in descomponer(matriz_correccion(filtro))[0]]
    assert signos == sorted(signos, reverse=True)


@pytest.fixture(scope="module")
def pantalla():
    pygame.display.init()
    return pygame.display.set_mode((64, 32))


@pytest.mark.parametrize("filtro", FILTROS)
def test_aplicar_da_la_matriz_por_el_color(pantalla, filtro):
    m = matriz_correccion(filtro)
    filtro_color = FiltroColor()
    for color in ((255, 255, 255), (255, 56, 120), (62, 230, 196), (10, 20, 30), (0, 0, 0)):
        pantalla.fill(color)
        filtro_color.aplicar(pantalla, filtro)
        obtenido = tuple(pantalla.get_at((5, 5)))[:3]
        esperado = tuple(max(0, min(255, round(sum(m[i][j] * color[j] for j in range(3))))) for i in range(3))
        for a, b in zip(obtenido, esperado):
            assert abs(a - b) <= 5, (color, obtenido, esperado)


def test_ninguno_no_toca_la_pantalla(pantalla):
    pantalla.fill((12, 34, 56))
    FiltroColor().aplicar(pantalla, "Ninguno")
    assert tuple(pantalla.get_at((1, 1)))[:3] == (12, 34, 56)


def test_volumen_de_interfaz_a_mixer():
    assert a_volumen_mixer(0) == 0.0
    assert a_volumen_mixer(100) == 1.0
    assert a_volumen_mixer(150) == 1.0  # nunca amplifica por encima del máximo
    assert a_volumen_mixer(35) == pytest.approx(0.35)


def test_opacidad_del_cono_solo_cambia_el_alfa():
    assert alfa_cono(0) == 0
    assert alfa_cono(40) == 46  # el cono de siempre
    assert alfa_cono(100) == alfa_cono(250)
