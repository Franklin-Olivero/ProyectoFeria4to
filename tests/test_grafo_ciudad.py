"""Tests de la red de calles de Ciudad Nova: Dijkstra, pesos dinámicos y
barricadas (sin pygame)."""

import itertools
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    BLOQUEO_PESO,
    CRUCE_ESTE,
    CRUCE_NORTE,
    CRUCE_OESTE,
    CRUCE_SUR,
    DESBLOQUEO_PESO,
    PESO_MAXIMO_CIUDAD,
    PESO_MINIMO_CIUDAD,
    PESOS_INICIALES_CIUDAD,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
    ZONA_PLAZA,
)
from src.dungeon import ciudad_mapa  # noqa: E402
from src.dungeon.clasificador_toxicidad import (  # noqa: E402
    DIFICULTAD_ALTA,
    DIFICULTAD_BAJA,
    DIFICULTAD_MEDIA,
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)
from src.dungeon.grafo_ciudad import EDIFICIOS, NODOS, ZONAS, GrafoCiudad  # noqa: E402


def pesos_de(ciudad, zona):
    return [ciudad.grafo.peso(zona, vecino) for vecino in ciudad.grafo.vecinos(zona)]


def en(nodo):
    """Posición (px del mundo) del nodo, como si el jugador estuviera ahí."""
    return ciudad_mapa.centro_casilla(*ciudad_mapa.NODOS_CALLE[nodo])


# ----------------------------------------------------------------------
# Trazado
# ----------------------------------------------------------------------

def test_nodos_plaza_cruces_y_edificios_con_pesos_iniciales_entre_1_y_6():
    ciudad = GrafoCiudad()
    assert ciudad.grafo.nodos() == NODOS
    assert len(NODOS) == 9 and ZONAS == [ZONA_PLAZA, *EDIFICIOS]
    assert ciudad.grafo.es_conexo()
    assert all(1 <= peso <= 6 for _, _, peso in PESOS_INICIALES_CIUDAD)
    assert len(ciudad.calles()) == len(PESOS_INICIALES_CIUDAD) == len(ciudad_mapa.TRAMOS)


def test_ninguna_arista_es_puente():
    for a, b, _ in GrafoCiudad().calles():
        grafo = GrafoCiudad().grafo
        grafo.eliminar_arista(a, b)
        assert grafo.es_conexo(), (a, b)


def test_cada_edificio_tiene_dos_rutas_distintas():
    """Grado >= 2 y, quitando cualquier calle del edificio, sigue
    llegándose a él desde la Plaza por la otra."""
    for edificio in EDIFICIOS:
        vecinos = GrafoCiudad().grafo.vecinos(edificio)
        assert len(vecinos) >= 2, edificio
        for vecino in vecinos:
            ciudad = GrafoCiudad()
            ciudad.bloqueadas.add(frozenset((edificio, vecino)))
            camino, _ = ciudad.ruta_mas_segura(ZONA_PLAZA, edificio)
            assert camino is not None and camino[-2] != vecino, (edificio, vecino)


# ----------------------------------------------------------------------
# Dijkstra
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "origen, destino, camino, costo",
    [
        (ZONA_PLAZA, ZONA_EMPRESA_MEDIOS, [ZONA_PLAZA, CRUCE_ESTE, ZONA_EMPRESA_MEDIOS], 6),
        (ZONA_PLAZA, ZONA_COLEGIO, [ZONA_PLAZA, CRUCE_OESTE, ZONA_COLEGIO], 4),
        (ZONA_PLAZA, ZONA_ALCALDIA, [ZONA_PLAZA, CRUCE_NORTE, ZONA_ALCALDIA], 6),
        (ZONA_HOSPITAL, ZONA_HOSPITAL, [ZONA_HOSPITAL], 0),
    ],
)
def test_rutas_calculadas_a_mano(origen, destino, camino, costo):
    assert GrafoCiudad().ruta_mas_segura(origen, destino) == (camino, costo)


def test_ruta_sugerida_elige_por_pesos_y_no_por_cantidad_de_calles():
    # Desde el Cruce Sur la Empresa de Medios está a 1 calle (peso 5),
    # pero no hay alternativa más barata: 5 < 3 + 4 + 2.
    assert GrafoCiudad().ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS) == (
        [CRUCE_SUR, ZONA_EMPRESA_MEDIOS], 5)
    # Desde la Plaza gana la de pesos menores aunque ambas tengan 2 calles.
    nodos, costo = GrafoCiudad().ruta_sugerida(en(ZONA_PLAZA), ZONA_EMPRESA_MEDIOS)
    assert nodos == [ZONA_PLAZA, CRUCE_ESTE, ZONA_EMPRESA_MEDIOS] and costo == 6


def test_al_bloquear_una_arista_la_ruta_rodea_con_mayor_costo():
    ciudad = GrafoCiudad()
    nodos, costo = ciudad.ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS)
    assert ciudad.bloquear((CRUCE_SUR, ZONA_EMPRESA_MEDIOS))
    nodos_rodeo, costo_rodeo = ciudad.ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS)
    assert nodos_rodeo == [CRUCE_SUR, ZONA_PLAZA, CRUCE_ESTE, ZONA_EMPRESA_MEDIOS]
    assert costo_rodeo == 3 + 4 + 2 > costo
    tramos = set(map(frozenset, zip(nodos_rodeo, nodos_rodeo[1:])))
    assert frozenset((CRUCE_SUR, ZONA_EMPRESA_MEDIOS)) not in tramos


def test_nodo_mas_cercano_no_cruza_una_barricada():
    """Justo al oeste de la barricada Cruce Sur - Medios, el nodo más
    cercano a pie es el Cruce Sur aunque Medios esté cerca en línea recta."""
    ciudad = GrafoCiudad()
    col = ciudad_mapa.tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS).seccion[0][0]
    posicion_oeste = ciudad_mapa.centro_casilla(col - 1, 34)
    posicion_este = ciudad_mapa.centro_casilla(col + 1, 34)
    ciudad.bloquear((CRUCE_SUR, ZONA_EMPRESA_MEDIOS))
    assert ciudad.nodo_mas_cercano(posicion_oeste) == CRUCE_SUR
    assert ciudad.nodo_mas_cercano(posicion_este) == ZONA_EMPRESA_MEDIOS
    assert ciudad.nodo_mas_cercano(en(ZONA_COLEGIO)) == ZONA_COLEGIO


def test_ruta_sugerida_hasta_donde_ya_se_esta():
    assert GrafoCiudad().ruta_sugerida(en(ZONA_HOSPITAL), ZONA_HOSPITAL) == ([ZONA_HOSPITAL], 0)


# ----------------------------------------------------------------------
# Barricadas
# ----------------------------------------------------------------------

def test_puede_bloquearse_nunca_desconecta_aunque_se_intenten_todas():
    ciudad = GrafoCiudad()
    for a, b, _ in ciudad.calles():
        ciudad.bloquear((a, b))
        assert ciudad.grafo_abierto().es_conexo()
    # 9 nodos conexos necesitan al menos 8 calles abiertas.
    assert len(ciudad.calles()) - len(ciudad.bloqueadas) >= len(NODOS) - 1
    for a, b, _ in ciudad.calles():
        if not ciudad.esta_bloqueada(a, b):
            assert not ciudad.puede_bloquearse((a, b))


@pytest.mark.parametrize("orden", list(itertools.islice(itertools.permutations(range(12)), 0, 400, 37)))
def test_puede_bloquearse_en_cualquier_orden(orden):
    ciudad = GrafoCiudad()
    calles = ciudad.calles()
    for i in orden:
        a, b, _ = calles[i]
        ciudad.bloquear((a, b))
        assert ciudad.grafo_abierto().es_conexo()


def test_detonacion_sube_3_y_bloquea_al_llegar_a_8():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=False)
    assert ciudad.grafo.peso(CRUCE_SUR, ZONA_EMPRESA_MEDIOS) == 8 == BLOQUEO_PESO
    assert ciudad.esta_bloqueada(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)
    assert ciudad.grafo.peso(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE) == 5
    assert not ciudad.esta_bloqueada(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE)
    # Las demás calles no cambian.
    assert ciudad.grafo.peso(ZONA_PLAZA, CRUCE_ESTE) == 4


def test_una_calle_que_desconectaria_queda_abierta_al_maximo():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=False)
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=False)
    # Medios - Cruce Este llegó a 8, pero es su única salida abierta.
    assert not ciudad.esta_bloqueada(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE)
    assert ciudad.grafo.peso(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE) == PESO_MAXIMO_CIUDAD
    assert ciudad.esta_bloqueada(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)


def test_desbloqueo_solo_al_bajar_de_6():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=False)  # 8: bloqueada
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)  # 6: sigue bloqueada
    assert ciudad.grafo.peso(CRUCE_SUR, ZONA_EMPRESA_MEDIOS) == DESBLOQUEO_PESO
    assert ciudad.esta_bloqueada(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)  # 4: se abre
    assert ciudad.grafo.peso(CRUCE_SUR, ZONA_EMPRESA_MEDIOS) == 4
    assert not ciudad.esta_bloqueada(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)


def test_al_desbloquear_una_calle_otra_saturada_puede_bloquearse():
    ciudad = GrafoCiudad()
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=False)
    # Sur-Medios bloqueada (10) y Medios-Este al máximo pero abierta.
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)
        # Mientras Sur-Medios siga bloqueada, Medios-Este (8) no puede
        # bloquearse y vuelve al máximo.
        assert ciudad.grafo.peso(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE) == PESO_MAXIMO_CIUDAD
    assert ciudad.calles_bloqueadas() == [(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)]
    # Sur-Medios: 10 -> 8 -> 6 -> 4, se abre; entonces Medios-Este (8) sí se bloquea.
    ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)
    assert ciudad.calles_bloqueadas() == [(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE)]
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_EMPRESA_MEDIOS, exito=True)
    assert ciudad.bloqueadas == set()


def test_pesos_dinamicos_respetan_minimo_y_maximo():
    for zona in EDIFICIOS:
        ciudad = GrafoCiudad()
        for _ in range(10):
            ciudad.actualizar_tras_mazmorra(zona, exito=True)
        assert all(peso == PESO_MINIMO_CIUDAD for peso in pesos_de(ciudad, zona))
        assert not ciudad.bloqueadas
        for _ in range(10):
            ciudad.actualizar_tras_mazmorra(zona, exito=False)
            assert all(PESO_MINIMO_CIUDAD <= peso <= PESO_MAXIMO_CIUDAD for _, _, peso in ciudad.calles())
            assert ciudad.grafo_abierto().es_conexo()
        assert all(peso == PESO_MAXIMO_CIUDAD for peso in pesos_de(ciudad, zona))


def test_detonaciones_en_todos_lados_nunca_aislan_un_edificio():
    ciudad = GrafoCiudad()
    for _ in range(4):
        for zona in EDIFICIOS:
            ciudad.actualizar_tras_mazmorra(zona, exito=False)
    for edificio in EDIFICIOS:
        assert ciudad.ruta_sugerida(en(ZONA_PLAZA), edificio) is not None


def test_restablecer_vuelve_a_los_pesos_iniciales_sin_barricadas():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_COLEGIO, exito=False)
    ciudad.actualizar_tras_mazmorra(ZONA_COLEGIO, exito=False)
    assert ciudad.bloqueadas
    ciudad.restablecer()
    assert not ciudad.bloqueadas
    assert not ciudad.barricadas_activas()
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
