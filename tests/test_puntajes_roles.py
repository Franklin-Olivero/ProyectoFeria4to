"""Estadísticas de rol en escala 1-10 (sin pygame)."""

import copy
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core import balance  # noqa: E402
from src.core.balance import ESTADISTICAS_INVERSAS, ESTADISTICAS_VISIBLES, RANGOS_STATS, STATS_POR_ROL  # noqa: E402
from src.core.puntajes_roles import puntaje_de, puntaje_stat, puntajes  # noqa: E402

ATRIBUTOS = [atributo for _, atributo in ESTADISTICAS_VISIBLES]


def test_siempre_entre_1_y_10():
    for valor in (-5, 0, 0.5, 1, 1.7, 3, 99):
        assert 1 <= puntaje_stat(valor, 0.5, 3.0) <= 10
        assert 1 <= puntaje_stat(valor, 0.5, 3.0, inverso=True) <= 10


def test_extremos_y_redondeo():
    assert puntaje_stat(0, 0, 9) == 1 and puntaje_stat(9, 0, 9) == 10
    assert puntaje_stat(4.5, 0, 9) == 6  # 4.5 + 0.5 = 5 -> sube
    assert puntaje_stat(1, 1, 1) == 10  # rango vacío
    assert puntaje_stat(0, 0, 9, inverso=True) == 10


def test_monotonia():
    valores = [0.85 + 0.01 * i for i in range(41)]
    normales = [puntaje_stat(v, 0.85, 1.25) for v in valores]
    inversos = [puntaje_stat(v, 0.85, 1.25, inverso=True) for v in valores]
    assert normales == sorted(normales)
    assert inversos == sorted(inversos, reverse=True)


@pytest.mark.parametrize("atributo", ATRIBUTOS)
def test_el_mejor_rol_saca_10_y_el_peor_1(atributo):
    valores = {rol: getattr(stats, atributo) for rol, stats in STATS_POR_ROL.items()}
    if atributo in ESTADISTICAS_INVERSAS:
        mejor, peor = min(valores, key=valores.get), max(valores, key=valores.get)
    else:
        mejor, peor = max(valores, key=valores.get), min(valores, key=valores.get)
    assert puntaje_de(mejor, atributo) == 10
    assert puntaje_de(peor, atributo) == 1


def test_rangos_salen_de_los_4_roles():
    for atributo, (minimo, maximo) in RANGOS_STATS.items():
        valores = [getattr(s, atributo) for s in STATS_POR_ROL.values()]
        assert (minimo, maximo) == (min(valores), max(valores))


def test_en_la_escala_ningun_rol_domina_a_otro():
    """La regla de balance del proyecto, vista en la tarjeta: ningún rol
    tiene puntaje >= que otro en todas las estadísticas."""
    for a in STATS_POR_ROL:
        for b in STATS_POR_ROL:
            if a != b:
                pa, pb = puntajes(a), puntajes(b)
                assert not all(pa[s] >= pb[s] for s in ATRIBUTOS), (a, b)


def test_mostrar_puntajes_no_toca_los_valores_reales():
    antes = copy.deepcopy(STATS_POR_ROL)
    for rol in STATS_POR_ROL:
        puntajes(rol)
    assert STATS_POR_ROL == antes
    assert balance.STATS_POR_ROL["ciudadano"].cadencia == 2.4  # el balance real sigue igual
    assert balance.STATS_POR_ROL["candidato"].danio_mult == 3.0
