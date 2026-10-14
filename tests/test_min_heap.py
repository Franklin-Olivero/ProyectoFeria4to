"""Tests del MinHeap manual (sin pygame)."""

import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.structures.min_heap import MinHeap  # noqa: E402


def vaciar(heap):
    salida = []
    while not heap.esta_vacio():
        salida.append(heap.extraer_minimo())
    return salida


def test_heap_nuevo_esta_vacio():
    heap = MinHeap()
    assert heap.esta_vacio()
    assert len(heap) == 0


def test_extrae_en_orden_aunque_se_inserte_desordenado():
    heap = MinHeap()
    for prioridad in [7, 3, 9, 1, 5, 8, 2]:
        heap.insertar(prioridad, f"v{prioridad}")
    assert vaciar(heap) == [(p, f"v{p}") for p in [1, 2, 3, 5, 7, 8, 9]]


def test_prioridades_repetidas_salen_en_orden_de_llegada():
    heap = MinHeap()
    heap.insertar(2, "a")
    heap.insertar(1, "b")
    heap.insertar(2, "c")
    heap.insertar(1, "d")
    heap.insertar(2, "e")
    assert vaciar(heap) == [(1, "b"), (1, "d"), (2, "a"), (2, "c"), (2, "e")]


def test_valores_no_comparables_no_rompen_el_desempate():
    heap = MinHeap()
    heap.insertar(1, {"x": 1})
    heap.insertar(1, {"x": 2})
    assert heap.extraer_minimo() == (1, {"x": 1})


def test_muchas_prioridades_aleatorias_salen_ordenadas():
    rng = random.Random(42)
    prioridades = [rng.randint(0, 20) for _ in range(300)]
    heap = MinHeap()
    for i, prioridad in enumerate(prioridades):
        heap.insertar(prioridad, i)
    extraidas = [prioridad for prioridad, _ in vaciar(heap)]
    assert extraidas == sorted(prioridades)


def test_insertar_y_extraer_intercalados():
    heap = MinHeap()
    heap.insertar(5, "a")
    heap.insertar(3, "b")
    assert heap.extraer_minimo() == (3, "b")
    heap.insertar(1, "c")
    heap.insertar(4, "d")
    assert vaciar(heap) == [(1, "c"), (4, "d"), (5, "a")]


def test_extraer_de_heap_vacio_lanza_error():
    with pytest.raises(IndexError):
        MinHeap().extraer_minimo()
