"""Tests de ArbolDecision usando el árbol real de la terminal de decisión.

Estructura construida (ids entre paréntesis):

    Publicación Viral (1)
    ├── Verificar (2)
    │   ├── Contrastar con Fuente (6)
    │   │   └── Purificación Exitosa (8)
    │   └── Creer Rumor (7)
    │       └── Detonación (9)
    ├── Compartir (3)
    ├── Reportar (4)
    └── Ignorar (5)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402
from src.structures.tree import ArbolDecision  # noqa: E402


def crear_arbol_del_juego():
    arbol = ArbolDecision(1, "Publicación Viral")
    arbol.insertar(1, 2, "Verificar")
    arbol.insertar(1, 3, "Compartir")
    arbol.insertar(1, 4, "Reportar")
    arbol.insertar(1, 5, "Ignorar")
    arbol.insertar(2, 6, "Contrastar con Fuente")
    arbol.insertar(2, 7, "Creer Rumor")
    arbol.insertar(6, 8, "Purificación Exitosa")
    arbol.insertar(7, 9, "Detonación")
    return arbol


def test_insertar_construye_la_estructura_esperada():
    arbol = crear_arbol_del_juego()

    assert [h.id for h in arbol.raiz.hijos] == [2, 3, 4, 5]
    verificar = arbol.buscar(2)
    assert [h.id for h in verificar.hijos] == [6, 7]
    assert arbol.buscar(8).etiqueta == "Purificación Exitosa"
    assert arbol.buscar(9).etiqueta == "Detonación"


def test_insertar_padre_inexistente_lanza_error():
    arbol = crear_arbol_del_juego()
    with pytest.raises(ValueError):
        arbol.insertar(999, 10, "Nodo Fantasma")


def test_insertar_id_duplicado_lanza_error():
    arbol = crear_arbol_del_juego()
    with pytest.raises(ValueError):
        arbol.insertar(1, 2, "Duplicado")


def test_buscar_nodo_existente_y_no_existente():
    arbol = crear_arbol_del_juego()

    nodo = arbol.buscar(6)
    assert nodo is not None
    assert nodo.etiqueta == "Contrastar con Fuente"

    assert arbol.buscar(123) is None


def test_eliminar_nodo_hoja():
    arbol = crear_arbol_del_juego()

    eliminado = arbol.eliminar(9)

    assert eliminado is True
    assert arbol.buscar(9) is None
    creer_rumor = arbol.buscar(7)
    assert creer_rumor.hijos == []


def test_eliminar_nodo_con_hijos_borra_todo_el_subarbol():
    arbol = crear_arbol_del_juego()

    eliminado = arbol.eliminar(6)

    assert eliminado is True
    assert arbol.buscar(6) is None
    assert arbol.buscar(8) is None  # hijo de 6, debe desaparecer también
    verificar = arbol.buscar(2)
    assert [h.id for h in verificar.hijos] == [7]


def test_eliminar_id_inexistente_retorna_false():
    arbol = crear_arbol_del_juego()

    assert arbol.eliminar(999) is False


def test_preorden():
    arbol = crear_arbol_del_juego()

    assert arbol.preorden() == [
        "Publicación Viral",
        "Verificar",
        "Contrastar con Fuente",
        "Purificación Exitosa",
        "Creer Rumor",
        "Detonación",
        "Compartir",
        "Reportar",
        "Ignorar",
    ]


def test_inorden():
    arbol = crear_arbol_del_juego()

    # Convención N-aria: primer hijo, nodo, resto de hijos (recursivo).
    assert arbol.inorden() == [
        "Purificación Exitosa",
        "Contrastar con Fuente",
        "Verificar",
        "Detonación",
        "Creer Rumor",
        "Publicación Viral",
        "Compartir",
        "Reportar",
        "Ignorar",
    ]


def test_postorden():
    arbol = crear_arbol_del_juego()

    assert arbol.postorden() == [
        "Purificación Exitosa",
        "Contrastar con Fuente",
        "Detonación",
        "Creer Rumor",
        "Verificar",
        "Compartir",
        "Reportar",
        "Ignorar",
        "Publicación Viral",
    ]


def test_por_niveles():
    arbol = crear_arbol_del_juego()

    assert arbol.por_niveles() == [
        "Publicación Viral",
        "Verificar",
        "Compartir",
        "Reportar",
        "Ignorar",
        "Contrastar con Fuente",
        "Creer Rumor",
        "Purificación Exitosa",
        "Detonación",
    ]

