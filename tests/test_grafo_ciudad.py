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
    METROS_POR_CASILLA,
    METROS_POR_PUNTO_DE_PESO,
    PESO_MINIMO_CIUDAD,
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
from src.dungeon.grafo_ciudad import (  # noqa: E402
    EDIFICIOS,
    NODOS,
    PESOS_INICIALES_CIUDAD,
    ZONAS,
    GrafoCiudad,
    metros_tramo,
    peso_base,
    tiempo_recorrido,
)


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


# ----------------------------------------------------------------------
# Distancias reales: el peso base sale del largo de la calle
# ----------------------------------------------------------------------

def test_peso_base_es_funcion_del_largo_real_en_todas_las_calles():
    for t in ciudad_mapa.TRAMOS:
        casillas = ciudad_mapa.largo_tramo(t)
        metros = casillas * METROS_POR_CASILLA
        assert metros_tramo(t.a, t.b) == metros
        esperado = max(PESO_MINIMO_CIUDAD, int(metros / METROS_POR_PUNTO_DE_PESO + 0.5))
        assert peso_base(t.a, t.b) == esperado == GrafoCiudad().grafo.peso(t.a, t.b), (t.a, t.b)


def test_largo_de_tramo_cuenta_los_codos():
    # Colegio -> Cruce Oeste: 9 casillas al oeste y 15 al sur.
    assert ciudad_mapa.largo_tramo(ciudad_mapa.tramo(ZONA_COLEGIO, CRUCE_OESTE)) == 24
    # Plaza -> Cruce Sur: 3 al sur y 5 al oeste por la Plaza, y 10 al sur por el radio.
    assert ciudad_mapa.largo_tramo(ciudad_mapa.tramo(ZONA_PLAZA, CRUCE_SUR)) == 18
    # Cruce Sur -> Medios: la Z (6 al este, 4 al sur y 15 al este).
    assert ciudad_mapa.largo_tramo(ciudad_mapa.tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS)) == 25


def test_calle_mas_larga_pesa_mas():
    """Nunca pesa menos una calle más larga; y si es al menos un punto
    de peso más larga (4 casillas = 20 m), pesa estrictamente más."""
    paso = METROS_POR_PUNTO_DE_PESO / METROS_POR_CASILLA
    for t1, t2 in itertools.permutations(ciudad_mapa.TRAMOS, 2):
        largo1, largo2 = ciudad_mapa.largo_tramo(t1), ciudad_mapa.largo_tramo(t2)
        if largo1 > largo2:
            assert peso_base(t1.a, t1.b) >= peso_base(t2.a, t2.b)
        if largo1 - largo2 >= paso:
            assert peso_base(t1.a, t1.b) > peso_base(t2.a, t2.b), (t1.a, t1.b, t2.a, t2.b)


def test_tiempo_de_recorrido_proporcional_al_largo():
    for t in ciudad_mapa.TRAMOS:
        segundos = tiempo_recorrido(t.a, t.b, velocidad=100)
        assert segundos == pytest.approx(ciudad_mapa.largo_tramo(t) * ciudad_mapa.TAM_CASILLA / 100)
    largo = ciudad_mapa.tramo(ZONA_COLEGIO, CRUCE_OESTE)
    corto = ciudad_mapa.tramo(ZONA_PLAZA, CRUCE_SUR)
    assert tiempo_recorrido(largo.a, largo.b) > tiempo_recorrido(corto.a, corto.b)


def test_etiqueta_de_peso_a_mitad_de_la_calle_y_lejos_de_los_nodos():
    """El peso se dibuja a mitad del recorrido: sobre la calle y a más de
    3 casillas de cualquier nodo (así nunca tapa un círculo del mapa)."""
    for t in ciudad_mapa.TRAMOS:
        col, fila = ciudad_mapa.punto_medio_tramo(t)
        assert (round(col), round(fila)) in set(ciudad_mapa.casillas_de_tramo(t.puntos))
        for nodo in ciudad_mapa.NODOS_CALLE.values():
            assert abs(col - nodo[0]) + abs(fila - nodo[1]) > 3, (t.a, t.b, nodo)


def test_los_ejes_de_dos_calles_no_comparten_casillas():
    """Fuera de sus nodos, dos tramos nunca pasan por la misma casilla:
    en el mapa del mundo ninguna calle se dibuja encima de otra."""
    nodos = set(ciudad_mapa.NODOS_CALLE.values())
    vistas = {}
    for t in ciudad_mapa.TRAMOS:
        for casilla in set(ciudad_mapa.casillas_de_tramo(t.puntos)) - nodos:
            assert casilla not in vistas, (t.a, t.b, vistas.get(casilla))
            vistas[casilla] = (t.a, t.b)


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
        # Plaza -> Medios: por el Sur 5 + 6 = 11; por el Este 6 + 6 = 12.
        (ZONA_PLAZA, ZONA_EMPRESA_MEDIOS, [ZONA_PLAZA, CRUCE_SUR, ZONA_EMPRESA_MEDIOS], 11),
        # Plaza -> Colegio: por el Norte 5 + 5 = 10; por el Oeste 6 + 6 = 12.
        (ZONA_PLAZA, ZONA_COLEGIO, [ZONA_PLAZA, CRUCE_NORTE, ZONA_COLEGIO], 10),
        # Plaza -> Alcaldía: por el Norte 5 + 5 = 10; por el Este 6 + 5 = 11.
        (ZONA_PLAZA, ZONA_ALCALDIA, [ZONA_PLAZA, CRUCE_NORTE, ZONA_ALCALDIA], 10),
        # Hospital -> Alcaldía: Sur, Plaza, Norte = 3 + 5 + 5 + 5 = 18 (Sur, Plaza, Este: 19;
        # por el Oeste: 5 + 6 + 5 + 5 = 21).
        (ZONA_HOSPITAL, ZONA_ALCALDIA, [ZONA_HOSPITAL, CRUCE_SUR, ZONA_PLAZA, CRUCE_NORTE, ZONA_ALCALDIA], 18),
        (ZONA_HOSPITAL, ZONA_HOSPITAL, [ZONA_HOSPITAL], 0),
    ],
)
def test_rutas_calculadas_a_mano(origen, destino, camino, costo):
    assert GrafoCiudad().ruta_mas_segura(origen, destino) == (camino, costo)


def test_ruta_sugerida_elige_por_pesos_y_no_por_cantidad_de_calles():
    # Desde el Cruce Sur la Empresa de Medios está a 1 calle (peso 6),
    # y ninguna alternativa es más barata: 6 < 5 + 6 + 6.
    assert GrafoCiudad().ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS) == (
        [CRUCE_SUR, ZONA_EMPRESA_MEDIOS], 6)
    # Desde la Plaza gana la más corta aunque ambas tengan 2 calles.
    nodos, costo = GrafoCiudad().ruta_sugerida(en(ZONA_PLAZA), ZONA_EMPRESA_MEDIOS)
    assert nodos == [ZONA_PLAZA, CRUCE_SUR, ZONA_EMPRESA_MEDIOS] and costo == 11


def test_al_bloquear_una_arista_la_ruta_rodea_con_mayor_costo():
    ciudad = GrafoCiudad()
    nodos, costo = ciudad.ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS)
    assert ciudad.bloquear((CRUCE_SUR, ZONA_EMPRESA_MEDIOS))
    nodos_rodeo, costo_rodeo = ciudad.ruta_sugerida(en(CRUCE_SUR), ZONA_EMPRESA_MEDIOS)
    assert nodos_rodeo == [CRUCE_SUR, ZONA_PLAZA, CRUCE_ESTE, ZONA_EMPRESA_MEDIOS]
    assert costo_rodeo == 5 + 6 + 6 > costo
    tramos = set(map(frozenset, zip(nodos_rodeo, nodos_rodeo[1:])))
    assert frozenset((CRUCE_SUR, ZONA_EMPRESA_MEDIOS)) not in tramos


def test_nodo_mas_cercano_no_cruza_una_barricada():
    """Justo al oeste de la barricada Cruce Sur - Medios, el nodo más
    cercano a pie es el Cruce Sur aunque Medios esté cerca en línea recta."""
    ciudad = GrafoCiudad()
    col = ciudad_mapa.tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS).seccion[0][0]
    fila = ciudad_mapa.NODOS_CALLE[ZONA_EMPRESA_MEDIOS][1]  # la calle de ese tramo (el último tramo de la Z)
    posicion_oeste = ciudad_mapa.centro_casilla(col - 1, fila)
    posicion_este = ciudad_mapa.centro_casilla(col + 1, fila)
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
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)
    # La calle larga (105 m, peso 5) llega a 8 y se bloquea; la corta (55 m, peso 3) no.
    assert ciudad.grafo.peso(ZONA_HOSPITAL, CRUCE_OESTE) == 8 == BLOQUEO_PESO
    assert ciudad.esta_bloqueada(ZONA_HOSPITAL, CRUCE_OESTE)
    assert ciudad.grafo.peso(CRUCE_SUR, ZONA_HOSPITAL) == 6
    assert not ciudad.esta_bloqueada(CRUCE_SUR, ZONA_HOSPITAL)
    # Las demás calles no cambian.
    assert ciudad.grafo.peso(ZONA_PLAZA, CRUCE_OESTE) == 6


def test_una_calle_que_desconectaria_queda_abierta_al_maximo():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)
    # Hospital - Cruce Sur llegó a 9, pero es su única salida abierta: queda al máximo.
    assert not ciudad.esta_bloqueada(CRUCE_SUR, ZONA_HOSPITAL)
    assert ciudad.grafo.peso(CRUCE_SUR, ZONA_HOSPITAL) == PESO_MAXIMO_CIUDAD
    assert ciudad.esta_bloqueada(ZONA_HOSPITAL, CRUCE_OESTE)


def test_desbloqueo_solo_al_bajar_de_6():
    ciudad = GrafoCiudad()
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)  # 8: bloqueada
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)  # 6: sigue bloqueada
    assert ciudad.grafo.peso(ZONA_HOSPITAL, CRUCE_OESTE) == DESBLOQUEO_PESO
    assert ciudad.esta_bloqueada(ZONA_HOSPITAL, CRUCE_OESTE)
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)  # 4: se abre
    assert ciudad.grafo.peso(ZONA_HOSPITAL, CRUCE_OESTE) == 4
    assert not ciudad.esta_bloqueada(ZONA_HOSPITAL, CRUCE_OESTE)


def test_al_desbloquear_una_calle_otra_saturada_puede_bloquearse():
    ciudad = GrafoCiudad()
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=False)
    # Oeste-Hospital bloqueada (10) y Hospital-Sur al máximo pero abierta.
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)
        # Mientras Oeste-Hospital siga bloqueada, Hospital-Sur (8) no puede
        # bloquearse y vuelve al máximo.
        assert ciudad.grafo.peso(CRUCE_SUR, ZONA_HOSPITAL) == PESO_MAXIMO_CIUDAD
    assert ciudad.calles_bloqueadas() == [(CRUCE_OESTE, ZONA_HOSPITAL)]
    # Oeste-Hospital: 10 -> 8 -> 6 -> 4, se abre; entonces Hospital-Sur (8) sí se bloquea.
    ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)
    assert ciudad.calles_bloqueadas() == [(ZONA_HOSPITAL, CRUCE_SUR)]
    for _ in range(2):
        ciudad.actualizar_tras_mazmorra(ZONA_HOSPITAL, exito=True)
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

    # Los capítulos van del más fácil al más difícil: 1 Colegio, 2 Hospital, 3 Medios.
    assert dificultad(ZONA_COLEGIO) == DIFICULTAD_BAJA
    assert dificultad(ZONA_HOSPITAL) == DIFICULTAD_MEDIA
    assert dificultad(ZONA_EMPRESA_MEDIOS) == DIFICULTAD_ALTA
    assert not GrafoCiudad.tiene_mazmorra_normal(ZONA_ALCALDIA)
    assert not GrafoCiudad.tiene_mazmorra_normal(ZONA_PLAZA)
