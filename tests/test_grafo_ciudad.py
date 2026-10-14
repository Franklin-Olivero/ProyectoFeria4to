"""Tests del mapa de la ciudad: Dijkstra y pesos dinámicos (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    PESO_MAXIMO_CIUDAD,
    PESO_MINIMO_CIUDAD,
    PESOS_INICIALES_CIUDAD,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
    ZONA_PLAZA,
)
from src.dungeon.clasificador_toxicidad import (  # noqa: E402
    DIFICULTAD_ALTA,
    DIFICULTAD_BAJA,
    DIFICULTAD_MEDIA,
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)
from src.dungeon.grafo_ciudad import ZONAS, GrafoCiudad  # noqa: E402


def pesos_de(ciudad, zona):
    return [ciudad.grafo.peso(zona, vecino) for vecino in ciudad.grafo.vecinos(zona)]


def test_nodos_y_pesos_iniciales_entre_1_y_6():
    ciudad = GrafoCiudad()
    assert ciudad.grafo.nodos() == ZONAS
    assert ciudad.grafo.es_conexo()
    assert all(1 <= peso <= 6 for _, _, peso in PESOS_INICIALES_CIUDAD)


def test_ruta_larga_y_segura_gana_a_la_corta_y_peligrosa():
    ciudad = GrafoCiudad()
    assert ciudad.grafo.peso(ZONA_PLAZA, ZONA_EMPRESA_MEDIOS) == 6  # 1 calle, saturada
    camino, costo = ciudad.ruta_mas_segura(ZONA_PLAZA, ZONA_EMPRESA_MEDIOS)
    assert camino == [ZONA_PLAZA, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS]
    assert costo == 5


@pytest.mark.parametrize(
    "origen, destino, camino, costo",
    [
        (ZONA_PLAZA, ZONA_ALCALDIA, [ZONA_PLAZA, ZONA_COLEGIO, ZONA_ALCALDIA], 7),
        (ZONA_PLAZA, ZONA_COLEGIO, [ZONA_PLAZA, ZONA_COLEGIO], 2),
        (ZONA_COLEGIO, ZONA_EMPRESA_MEDIOS, [ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS], 6),
        (ZONA_HOSPITAL, ZONA_HOSPITAL, [ZONA_HOSPITAL], 0),
    ],
)
def test_rutas_calculadas_a_mano(origen, destino, camino, costo):
    assert GrafoCiudad().ruta_mas_segura(origen, destino) == (camino, costo)


def test_purificacion_baja_en_1_las_calles_de_la_zona():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)
    assert ciudad.grafo.peso(ZONA_PLAZA, ZONA_EMPRESA_MEDIOS) == 5
    assert ciudad.grafo.peso(ZONA_EMPRESA_MEDIOS, ZONA_HOSPITAL) == 1
    assert ciudad.grafo.peso(ZONA_ALCALDIA, ZONA_EMPRESA_MEDIOS) == 2
    # Las demás calles no cambian.
    assert ciudad.grafo.peso(ZONA_PLAZA, ZONA_COLEGIO) == 2


def test_detonacion_sube_en_1_y_puede_cambiar_la_ruta():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_COLEGIO, exito=False)
    ciudad.actualizar_tras_mazmorra(ZONA_COLEGIO, exito=False)
    assert ciudad.grafo.peso(ZONA_COLEGIO, ZONA_ALCALDIA) == 7
    # Plaza -> Colegio -> Alcaldía ahora cuesta 4 + 7 = 11; gana la de la
    # Empresa de Medios: 3 + 2 + 3 = 8.
    camino, costo = ciudad.ruta_mas_segura(ZONA_PLAZA, ZONA_ALCALDIA)
    assert camino == [ZONA_PLAZA, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS, ZONA_ALCALDIA]
    assert costo == 8


def test_pesos_dinamicos_respetan_minimo_y_maximo():
    ciudad = GrafoCiudad()
    for _ in range(20):
        ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)
    assert all(peso == PESO_MINIMO_CIUDAD for peso in pesos_de(ciudad, ZONA_HOSPITAL))
    for _ in range(20):
        ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)
    assert all(peso == PESO_MAXIMO_CIUDAD for peso in pesos_de(ciudad, ZONA_HOSPITAL))
    # La calle sigue siendo simétrica.
    assert ciudad.grafo.peso(ZONA_PLAZA, ZONA_HOSPITAL) == PESO_MAXIMO_CIUDAD


def test_restablecer_vuelve_a_los_pesos_iniciales():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_COLEGIO, exito=False)
    ciudad.restablecer()
    for a, b, peso in PESOS_INICIALES_CIUDAD:
        assert ciudad.grafo.peso(a, b) == peso


def test_cada_zona_tiene_su_gravedad_promedio():
    def dificultad(zona):
        reportes = GrafoCiudad.reportes(zona)
        return nivel_a_dificultad(calcular_nivel_toxicidad(construir_arbol_reportes(reportes, zona)))

    assert dificultad(ZONA_COLEGIO) == DIFICULTAD_ALTA
    assert dificultad(ZONA_HOSPITAL) == DIFICULTAD_MEDIA
    assert dificultad(ZONA_EMPRESA_MEDIOS) == DIFICULTAD_BAJA
    assert not GrafoCiudad.tiene_mazmorra_normal(ZONA_ALCALDIA)
    assert not GrafoCiudad.tiene_mazmorra_normal(ZONA_PLAZA)
