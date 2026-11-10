"""Tests del mapa de casillas de Ciudad Nova (sin pygame): datos del
mapa, calles sobre casillas transitables, barricadas, movimiento con
colisión y cámara."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import ENTRADA_ALCANCE, TAM_CASILLA, ZONA_ALCALDIA  # noqa: E402
from src.dungeon import ciudad_mapa as cm  # noqa: E402
from src.dungeon.grafo_ciudad import EDIFICIOS, NODOS, GrafoCiudad  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.structures.graph import Grafo  # noqa: E402

TODAS_LAS_BARRICADAS = frozenset(c for t in cm.TRAMOS for c in t.seccion) | cm.BARRICADAS_ALCALDIA


# ----------------------------------------------------------------------
# Datos del mapa
# ----------------------------------------------------------------------

def test_mapa_rectangular_de_64x47_y_casillas_de_48px():
    assert TAM_CASILLA == 48
    assert cm.FILAS == 47
    assert all(len(fila) == cm.COLUMNAS == 64 for fila in cm.MAPA)
    letras_validas = set(".:ck#HJEXF~")
    assert all(set(fila) <= letras_validas for fila in cm.MAPA)


def test_el_mundo_es_mas_grande_que_la_ventana():
    assert cm.TAM_MUNDO[0] > 1280 and cm.TAM_MUNDO[1] > 720


def test_spawn_y_entradas_son_transitables():
    assert not cm.es_solida(*cm.SPAWN)
    for zona, puerta in cm.ENTRADAS.items():
        assert cm.casilla(*puerta) == cm.ENTRADA, zona
        assert not cm.es_solida(*puerta), zona


def test_los_4_edificios_tienen_su_entrada_en_la_fachada():
    assert set(cm.EDIFICIOS) == set(EDIFICIOS) == set(cm.ENTRADAS)
    for zona, (col, fila, ancho, alto) in cm.EDIFICIOS.items():
        puerta_col, puerta_fila = cm.ENTRADAS[zona]
        assert col <= puerta_col < col + ancho
        assert puerta_fila == fila + alto - 1  # en la fila de abajo: la fachada
        # El resto del edificio es sólido.
        for f in range(fila, fila + alto):
            for c in range(col, col + ancho):
                if (c, f) != (puerta_col, puerta_fila):
                    assert cm.es_solida(c, f), (zona, c, f)


def test_el_borde_del_mundo_es_solido():
    for col in range(cm.COLUMNAS):
        assert cm.es_solida(col, 0) and cm.es_solida(col, cm.FILAS - 1)
    for fila in range(cm.FILAS):
        assert cm.es_solida(0, fila) and cm.es_solida(cm.COLUMNAS - 1, fila)
    assert cm.es_solida(-1, 5) and cm.es_solida(5, cm.FILAS)


# ----------------------------------------------------------------------
# Grafo de calles sobre el mapa (validado con BFS)
# ----------------------------------------------------------------------

def test_cada_nodo_esta_sobre_una_casilla_de_calle_transitable():
    assert set(cm.NODOS_CALLE) == set(NODOS)
    for nodo, casilla in cm.NODOS_CALLE.items():
        assert not cm.es_solida(*casilla), nodo


def test_cada_tramo_une_sus_extremos_por_casillas_transitables():
    """Grafo con solo las casillas del eje del tramo + BFS: el otro
    extremo debe alcanzarse sin pisar nada sólido."""
    for t in cm.TRAMOS:
        assert t.puntos[0] == cm.NODOS_CALLE[t.a] and t.puntos[-1] == cm.NODOS_CALLE[t.b]
        casillas = cm.casillas_de_tramo(t.puntos)
        eje = Grafo()
        for casilla in casillas:
            assert not cm.es_solida(*casilla), (t.a, t.b, casilla)
            eje.agregar_nodo(casilla)
        for (c, f) in casillas:
            for vecino in ((c + 1, f), (c, f + 1)):
                if vecino in eje:
                    eje.agregar_arista((c, f), vecino)
        _, distancias, _ = eje.bfs(cm.NODOS_CALLE[t.a])
        assert cm.NODOS_CALLE[t.b] in distancias, (t.a, t.b)


def test_cada_seccion_cruza_su_propio_tramo():
    for t in cm.TRAMOS:
        assert set(t.seccion) & set(cm.casillas_de_tramo(t.puntos)), (t.a, t.b)
        assert all(not cm.es_solida(*casilla) for casilla in t.seccion)


def test_sin_barricadas_todo_se_alcanza_a_pie_desde_el_spawn():
    grafo = cm.grafo_casillas(cm.es_solida)
    _, distancias, _ = grafo.bfs(cm.SPAWN)
    for nodo, casilla in cm.NODOS_CALLE.items():
        assert casilla in distancias, nodo
    for zona, puerta in cm.ENTRADAS.items():
        assert puerta in distancias, zona


def test_cada_barricada_corta_su_calle_de_verdad():
    """Con todas las barricadas puestas ningún nodo alcanza a otro: cada
    sección va de sólido a sólido y no se puede rodear por la acera."""
    grafo = cm.grafo_casillas(lambda c, f: cm.es_solida(c, f, TODAS_LAS_BARRICADAS))
    casillas_nodo = set(cm.NODOS_CALLE.values())
    for nodo, casilla in cm.NODOS_CALLE.items():
        _, distancias, _ = grafo.bfs(casilla)
        assert casillas_nodo & set(distancias) == {casilla}, nodo


def test_con_las_calles_bloqueadas_el_mapa_sigue_igual_de_conexo_que_el_grafo():
    """Tras bloquear todo lo que se pueda, cada edificio sigue
    alcanzable a pie desde la Plaza (la física coincide con el grafo)."""
    ciudad = GrafoCiudad()
    for a, b, _ in ciudad.calles():
        ciudad.bloquear((a, b))
    assert ciudad.bloqueadas
    grafo = cm.grafo_casillas(ciudad.es_solida)
    _, distancias, _ = grafo.bfs(cm.SPAWN)
    for nodo, casilla in cm.NODOS_CALLE.items():
        assert casilla in distancias, nodo


# ----------------------------------------------------------------------
# Barricadas dinámicas
# ----------------------------------------------------------------------

def test_barricadas_de_una_calle_solidas_solo_mientras_esta_bloqueada():
    ciudad = GrafoCiudad()
    t = cm.tramo("Cruce Sur", "Empresa de Medios")
    assert not any(ciudad.es_solida(*c) for c in t.seccion)
    assert ciudad.bloquear(("Cruce Sur", "Empresa de Medios"))
    assert all(ciudad.es_solida(*c) for c in t.seccion)
    # Las de las demás calles siguen libres.
    otra = cm.tramo("Cruce Norte", "Colegio")
    assert not any(ciudad.es_solida(*c) for c in otra.seccion)
    ciudad.desbloquear(("Empresa de Medios", "Cruce Sur"))
    assert not any(ciudad.es_solida(*c) for c in t.seccion)


def test_barricadas_de_la_alcaldia_desaparecen_al_desbloquearse():
    partida = Partida()
    assert not partida.alcaldia_desbloqueada()
    assert cm.BARRICADAS_ALCALDIA
    assert all(partida.es_solida(*c) for c in cm.BARRICADAS_ALCALDIA)
    # Sellada, la puerta no se alcanza a pie desde la calle de enfrente.
    grafo = cm.grafo_casillas(partida.es_solida)
    _, distancias, _ = grafo.bfs(cm.NODOS_CALLE[ZONA_ALCALDIA])
    assert cm.ENTRADAS[ZONA_ALCALDIA] not in distancias

    partida.progreso.mazmorras_completadas = 1
    assert partida.alcaldia_desbloqueada()
    assert not any(partida.es_solida(*c) for c in cm.BARRICADAS_ALCALDIA)
    grafo = cm.grafo_casillas(partida.es_solida)
    _, distancias, _ = grafo.bfs(cm.NODOS_CALLE[ZONA_ALCALDIA])
    assert cm.ENTRADAS[ZONA_ALCALDIA] in distancias


# ----------------------------------------------------------------------
# Entradas, aparición, movimiento y cámara
# ----------------------------------------------------------------------

def test_entrada_cercana_respeta_el_alcance():
    puerta = cm.centro_casilla(*cm.ENTRADAS["Colegio"])
    assert cm.entrada_cercana(puerta) == "Colegio"
    assert cm.entrada_cercana((puerta[0], puerta[1] + ENTRADA_ALCANCE - 1)) == "Colegio"
    assert cm.entrada_cercana((puerta[0], puerta[1] + ENTRADA_ALCANCE + 1)) is None
    assert cm.entrada_cercana(cm.centro_casilla(*cm.SPAWN)) is None


def test_aparicion_frente_a_la_puerta_y_fuera_del_alcance():
    for zona in cm.ENTRADAS:
        x, y = cm.posicion_aparicion(zona)
        assert not cm.es_solida(*cm.casilla_de(x, y))
        assert cm.entrada_cercana((x, y)) is None
        assert cm.casilla_de(x, y)[0] == cm.ENTRADAS[zona][0]
    assert cm.posicion_aparicion("Plaza") == cm.centro_casilla(*cm.SPAWN)


def muro_en_columna(col_muro):
    return lambda c, f: c == col_muro


def test_mover_con_colision_no_atraviesa_casillas_solidas():
    es_solida = muro_en_columna(3)
    tamano = (36, 36)
    x, y = cm.centro_casilla(1, 1)
    for _ in range(50):
        x, y = cm.mover_con_colision((x, y), (10, 0), tamano, es_solida)
    # El borde derecho queda pegado al borde izquierdo de la columna 3.
    assert x + tamano[0] / 2 == pytest.approx(3 * TAM_CASILLA)
    # Un salto enorme de una vez tampoco lo atraviesa.
    x2, _ = cm.mover_con_colision(cm.centro_casilla(1, 1), (500, 0), tamano, es_solida)
    assert x2 + tamano[0] / 2 <= 3 * TAM_CASILLA


def test_mover_con_colision_resbala_por_el_eje_libre():
    es_solida = muro_en_columna(3)
    tamano = (36, 36)
    inicio = (3 * TAM_CASILLA - 18, cm.centro_casilla(1, 5)[1])  # pegado al muro
    x, y = cm.mover_con_colision(inicio, (8, 8), tamano, es_solida)
    assert x == pytest.approx(inicio[0])  # x bloqueado
    assert y == pytest.approx(inicio[1] + 8)  # y avanza: resbala


def test_mover_con_colision_hacia_la_izquierda_y_arriba():
    es_solida = lambda c, f: c == 0 or f == 0  # noqa: E731
    tamano = (36, 36)
    x, y = cm.mover_con_colision(cm.centro_casilla(2, 2), (-500, -500), tamano, es_solida)
    assert x - 18 == pytest.approx(TAM_CASILLA)
    assert y - 18 == pytest.approx(TAM_CASILLA)


def test_un_jugador_cabe_por_una_puerta_de_una_casilla():
    tamano = (36, 36)
    x, y = cm.posicion_aparicion("Colegio")
    for _ in range(40):
        x, y = cm.mover_con_colision((x, y), (0, -6), tamano, cm.es_solida)
    assert cm.entrada_cercana((x, y)) == "Colegio"


@pytest.mark.parametrize("jugador, esperada", [
    ((0, 0), (0, 0)),  # arriba a la izquierda
    ((99999, 0), (64 * 48 - 1280, 0)),  # arriba a la derecha
    ((0, 99999), (0, 47 * 48 - 568)),  # abajo a la izquierda
    ((99999, 99999), (64 * 48 - 1280, 47 * 48 - 568)),  # abajo a la derecha
])
def test_camara_se_limita_a_los_bordes_en_las_cuatro_esquinas(jugador, esperada):
    assert cm.calcular_camara(jugador, cm.TAM_MUNDO, (1280, 568)) == esperada


def test_camara_centra_al_jugador_lejos_de_los_bordes():
    assert cm.calcular_camara((1500, 1000), cm.TAM_MUNDO, (1280, 568)) == (860, 716)


def test_camara_centra_un_mundo_mas_chico_que_la_vista():
    assert cm.calcular_camara((50, 50), (400, 300), (1280, 568)) == (-440, -134)


def test_polilinea_de_ruta_sigue_los_codos_y_termina_en_la_puerta():
    puntos = cm.polilinea_ruta((100.0, 100.0), ["Colegio", "Cruce Oeste"])
    assert puntos[0] == (100.0, 100.0)
    assert puntos[1] == cm.centro_casilla(15, 10)
    assert cm.centro_casilla(6, 10) in puntos  # el codo
    assert puntos[-1] == cm.centro_casilla(6, 25)
    hacia_puerta = cm.polilinea_ruta((0, 0), ["Plaza", "Cruce Norte", "Colegio"])
    assert hacia_puerta[-1] == cm.centro_casilla(*cm.ENTRADAS["Colegio"])


def test_modulos_de_la_ciudad_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = (
        "import sys, src.dungeon.ciudad_mapa, src.dungeon.grafo_ciudad, src.dungeon.noticias,"
        " src.dungeon.partida, src.core.escenas, src.core.balance;"
        "print('pygame' in sys.modules)"
    )
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"
