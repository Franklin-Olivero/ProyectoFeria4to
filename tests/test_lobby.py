"""Lobby (sin pygame): sinergias, descripciones, valores de stats y barras."""

import itertools
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import ESTADISTICAS_VISIBLES, STATS_POR_ROL, stats_normalizadas  # noqa: E402
from src.ui import lobby  # noqa: E402

ROLES = list(STATS_POR_ROL)


def test_cada_rol_tiene_descripcion_papel_y_companeros():
    for rol in ROLES:
        assert lobby.DESCRIPCION_HABILIDAD[rol]
        assert lobby.PAPEL[rol]
        assert all(companero in ROLES and companero != rol for companero in lobby.COMPANEROS[rol])


def test_todo_par_de_roles_distintos_tiene_sinergia():
    for a, b in itertools.combinations(ROLES, 2):
        assert frozenset((a, b)) in lobby.SINERGIAS


def test_un_jugador_ve_con_quien_combina():
    estrellas, texto = lobby.sinergia(["periodista"])
    assert estrellas == 0 and "Candidato" in texto


def test_dos_roles_distintos_suman_estrellas():
    estrellas, texto = lobby.sinergia(["influencer", "candidato"])
    assert estrellas == 2 and texto == lobby.SINERGIAS[frozenset(("influencer", "candidato"))]


def test_mismo_rol_una_estrella_y_maximo_tres():
    assert lobby.sinergia(["ciudadano", "ciudadano"])[0] == 1
    assert lobby.sinergia(ROLES)[0] == lobby.MAXIMO_ESTRELLAS
    assert lobby.sinergia([]) == (0, "")


@pytest.mark.parametrize("rol, atributo, texto", [
    ("ciudadano", "cadencia", "10/10"),  # la cadencia más alta
    ("candidato", "carga_maxima", "10/10"),  # menos kills: Carga 10
    ("ciudadano", "carga_maxima", "1/10"),
    ("influencer", "velocidad_mult", "10/10"),
])
def test_puntaje_1_a_10_junto_a_la_barra(rol, atributo, texto):
    assert lobby.valor_estadistica(rol, atributo) == texto


def test_barras_del_lobby_incluyen_carga_y_menos_kills_es_barra_mas_larga():
    assert ("Carga", "carga_maxima") in ESTADISTICAS_VISIBLES
    normalizadas = stats_normalizadas()
    cargas = {rol: normalizadas[rol]["carga_maxima"] for rol in ROLES}
    assert cargas["candidato"] == 1.0  # 4 kills: la más barata
    assert cargas["ciudadano"] == pytest.approx(4 / 6)
    for _, atributo in ESTADISTICAS_VISIBLES:
        fracciones = [normalizadas[rol][atributo] for rol in ROLES]
        assert max(fracciones) == 1.0 and all(0 < f <= 1 for f in fracciones)
