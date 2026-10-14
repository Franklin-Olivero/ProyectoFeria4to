"""Tests del clasificador de toxicidad (árbol de reportes -> dificultad).

Árbol construido por `crear_reportes_colegio()` (ids entre paréntesis):

    Colegio (zona)
    ├── comentario, gravedad 2 (1)
    ├── publicacion_viral, gravedad 4 (2)
    ├── denuncia, gravedad 5 (3)
    ├── comentario, gravedad 3 (4)
    └── publicacion_viral, gravedad 4 (5)

Promedio de gravedad = 18 / 5 = 3.6 -> nivel (3.6 - 1) / 4 * 100 = 65.0
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402
from src.dungeon.clasificador_toxicidad import (  # noqa: E402
    DIFICULTAD_ALTA,
    DIFICULTAD_BAJA,
    DIFICULTAD_MEDIA,
    ID_RAIZ_ZONA,
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)


def crear_reportes_colegio():
    return [
        {"id": 1, "tipo": "comentario", "gravedad": 2},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 4},
        {"id": 3, "tipo": "denuncia", "gravedad": 5},
        {"id": 4, "tipo": "comentario", "gravedad": 3},
        {"id": 5, "tipo": "publicacion_viral", "gravedad": 4},
    ]


def reportes_con_gravedad(gravedades):
    return [
        {"id": i, "tipo": "comentario", "gravedad": gravedad}
        for i, gravedad in enumerate(gravedades, start=1)
    ]


# ----------------------------------------------------------------------
# construir_arbol_reportes
# ----------------------------------------------------------------------


def test_construir_arbol_raiz_es_la_zona_y_cada_reporte_es_hijo():
    arbol = construir_arbol_reportes(crear_reportes_colegio(), "Colegio")

    assert arbol.raiz.id == ID_RAIZ_ZONA
    assert arbol.raiz.etiqueta == "Colegio"
    assert [h.id for h in arbol.raiz.hijos] == [1, 2, 3, 4, 5]
    assert all(h.hijos == [] for h in arbol.raiz.hijos)


def test_construir_arbol_guarda_el_reporte_en_la_etiqueta():
    arbol = construir_arbol_reportes(crear_reportes_colegio())

    denuncia = arbol.buscar(3)
    assert denuncia.etiqueta == {"id": 3, "tipo": "denuncia", "gravedad": 5}


def test_construir_arbol_sin_reportes_solo_tiene_raiz():
    arbol = construir_arbol_reportes([])

    assert arbol.raiz.hijos == []


def test_construir_arbol_gravedad_fuera_de_rango_lanza_error():
    with pytest.raises(ValueError):
        construir_arbol_reportes(reportes_con_gravedad([3, 6]))
    with pytest.raises(ValueError):
        construir_arbol_reportes(reportes_con_gravedad([0]))


def test_construir_arbol_id_duplicado_lanza_error():
    reportes = [
        {"id": 1, "tipo": "comentario", "gravedad": 2},
        {"id": 1, "tipo": "denuncia", "gravedad": 5},
    ]
    with pytest.raises(ValueError):
        construir_arbol_reportes(reportes)


# ----------------------------------------------------------------------
# calcular_nivel_toxicidad
# ----------------------------------------------------------------------


def test_nivel_del_colegio_es_65():
    arbol = construir_arbol_reportes(crear_reportes_colegio())

    assert calcular_nivel_toxicidad(arbol) == pytest.approx(65.0)


def test_nivel_todo_gravedad_minima_es_0():
    arbol = construir_arbol_reportes(reportes_con_gravedad([1, 1, 1]))

    assert calcular_nivel_toxicidad(arbol) == pytest.approx(0.0)


def test_nivel_todo_gravedad_maxima_es_100():
    arbol = construir_arbol_reportes(reportes_con_gravedad([5, 5]))

    assert calcular_nivel_toxicidad(arbol) == pytest.approx(100.0)


def test_nivel_gravedad_media_es_50():
    arbol = construir_arbol_reportes(reportes_con_gravedad([1, 5]))

    assert calcular_nivel_toxicidad(arbol) == pytest.approx(50.0)


def test_nivel_sin_reportes_es_0():
    arbol = construir_arbol_reportes([])

    assert calcular_nivel_toxicidad(arbol) == 0.0


def test_nivel_ignora_reportes_eliminados_del_arbol():
    arbol = construir_arbol_reportes(reportes_con_gravedad([1, 5]))

    arbol.eliminar(2)  # quita el reporte de gravedad 5

    assert calcular_nivel_toxicidad(arbol) == pytest.approx(0.0)


# ----------------------------------------------------------------------
# nivel_a_dificultad
# ----------------------------------------------------------------------


def test_tramo_bajo():
    assert nivel_a_dificultad(0.0) == DIFICULTAD_BAJA
    assert nivel_a_dificultad(33.9) == DIFICULTAD_BAJA
    assert nivel_a_dificultad(0.0) == {"cantidad_enemigos": 2, "multiplicador_velocidad": 0.8}


def test_tramo_medio():
    assert nivel_a_dificultad(34.0) == DIFICULTAD_MEDIA
    assert nivel_a_dificultad(66.9) == DIFICULTAD_MEDIA
    assert nivel_a_dificultad(50.0) == {"cantidad_enemigos": 3, "multiplicador_velocidad": 1.0}


def test_tramo_alto():
    assert nivel_a_dificultad(67.0) == DIFICULTAD_ALTA
    assert nivel_a_dificultad(100.0) == DIFICULTAD_ALTA
    assert nivel_a_dificultad(100.0) == {"cantidad_enemigos": 5, "multiplicador_velocidad": 1.3}


def test_mas_toxicidad_nunca_da_menos_enemigos():
    bajo = nivel_a_dificultad(10.0)
    medio = nivel_a_dificultad(50.0)
    alto = nivel_a_dificultad(90.0)

    assert bajo["cantidad_enemigos"] < medio["cantidad_enemigos"] < alto["cantidad_enemigos"]
    assert (
        bajo["multiplicador_velocidad"]
        < medio["multiplicador_velocidad"]
        < alto["multiplicador_velocidad"]
    )


def test_nivel_a_dificultad_devuelve_copia_independiente():
    dificultad = nivel_a_dificultad(0.0)
    dificultad["cantidad_enemigos"] = 99

    assert DIFICULTAD_BAJA["cantidad_enemigos"] == 2
