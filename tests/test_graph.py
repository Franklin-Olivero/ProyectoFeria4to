"""Tests del Grafo manual (sin pygame). Los resultados esperados están
calculados a mano sobre grafos pequeños."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.structures.graph import INFINITO, Grafo  # noqa: E402


def grafo_arbol():
    """      A
            / \
           B   C
           |   |
           D   E      (todas las aristas con peso 1)"""
    g = Grafo()
    g.agregar_arista("A", "B")
    g.agregar_arista("A", "C")
    g.agregar_arista("B", "D")
    g.agregar_arista("C", "E")
    return g


def grafo_ponderado():
    """A-D directo pesa 5; A-B-C-D son 3 saltos de peso 1 (total 3)."""
    g = Grafo()
    g.agregar_arista("A", "B", 1)
    g.agregar_arista("B", "C", 1)
    g.agregar_arista("C", "D", 1)
    g.agregar_arista("A", "D", 5)
    return g


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------


def test_agregar_arista_no_dirigida_crea_ambos_sentidos():
    g = Grafo()
    g.agregar_arista(1, 2, 7)
    assert g.existe_arista(1, 2) and g.existe_arista(2, 1)
    assert g.peso(2, 1) == 7
    assert g.nodos() == [1, 2]


def test_arista_dirigida_solo_va_en_un_sentido():
    g = Grafo()
    g.agregar_arista("x", "y", 3, dirigida=True)
    assert g.existe_arista("x", "y")
    assert not g.existe_arista("y", "x")


def test_cambiar_peso_actualiza_los_dos_sentidos():
    g = Grafo()
    g.agregar_arista("a", "b", 2)
    g.cambiar_peso("a", "b", 9)
    assert g.peso("a", "b") == 9 and g.peso("b", "a") == 9


def test_eliminar_arista_y_nodo():
    g = grafo_arbol()
    g.eliminar_arista("A", "B")
    assert not g.existe_arista("A", "B") and not g.existe_arista("B", "A")
    g.eliminar_nodo("C")
    assert "C" not in g
    assert g.vecinos("A") == []
    assert g.vecinos("E") == []


def test_eliminar_nodo_quita_aristas_dirigidas_que_llegaban():
    g = Grafo()
    g.agregar_arista("a", "b", dirigida=True)
    g.eliminar_nodo("b")
    assert g.vecinos("a") == []


def test_errores_de_nodo_arista_y_peso():
    g = grafo_arbol()
    with pytest.raises(KeyError):
        g.peso("A", "E")
    with pytest.raises(KeyError):
        g.vecinos("Z")
    with pytest.raises(KeyError):
        g.eliminar_arista("D", "E")
    with pytest.raises(ValueError):
        g.agregar_arista("A", "Z", -1)


# ----------------------------------------------------------------------
# Recorridos
# ----------------------------------------------------------------------


def test_bfs_orden_distancias_y_predecesores():
    orden, distancias, predecesores = grafo_arbol().bfs("A")
    assert orden == ["A", "B", "C", "D", "E"]
    assert distancias == {"A": 0, "B": 1, "C": 1, "D": 2, "E": 2}
    assert predecesores == {"A": None, "B": "A", "C": "A", "D": "B", "E": "C"}


def test_dfs_baja_primero_por_una_rama():
    assert grafo_arbol().dfs("A") == ["A", "B", "D", "C", "E"]


def test_dfs_con_ciclo_visita_cada_nodo_una_vez():
    assert grafo_ponderado().dfs("A") == ["A", "B", "C", "D"]


def test_camino_reconstruye_desde_predecesores():
    g = grafo_arbol()
    _, _, predecesores = g.bfs("A")
    assert Grafo.camino(predecesores, "A", "E") == ["A", "C", "E"]
    assert Grafo.camino(predecesores, "A", "A") == ["A"]
    assert Grafo.camino(predecesores, "A", "Z") is None


def test_es_conexo():
    g = grafo_arbol()
    assert g.es_conexo()
    g.agregar_nodo("F")
    assert not g.es_conexo()
    assert Grafo().es_conexo()


def test_dijkstra_elige_ruta_mas_larga_en_saltos_pero_de_menor_peso():
    g = grafo_ponderado()
    distancias, predecesores = g.dijkstra("A")
    assert distancias == {"A": 0, "B": 1, "C": 2, "D": 3}
    assert Grafo.camino(predecesores, "A", "D") == ["A", "B", "C", "D"]
    # BFS, que cuenta saltos, se quedaría con la arista directa.
    _, _, predecesores_bfs = g.bfs("A")
    assert Grafo.camino(predecesores_bfs, "A", "D") == ["A", "D"]


def test_dijkstra_nodo_inalcanzable_queda_en_infinito():
    g = grafo_ponderado()
    g.agregar_nodo("X")
    distancias, predecesores = g.dijkstra("A")
    assert distancias["X"] == INFINITO
    assert Grafo.camino(predecesores, "A", "X") is None


def test_estructuras_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = (
        "import sys, src.structures.graph, src.structures.min_heap, src.dungeon.mazmorra,"
        " src.dungeon.grafo_ciudad, src.dungeon.partida, src.core.escenas, src.ui.mapa_ciudad;"
        "print('pygame' in sys.modules)"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"
