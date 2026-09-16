"""Tests de Node/Selector/Sequence/Action en aislado, sin pygame."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.behavior_tree import (  # noqa: E402
    EN_PROGRESO,
    EXITO,
    FALLO,
    Action,
    Selector,
    Sequence,
)


def accion_fija(estado, contador=None):
    """Crea una Action que retorna `estado` y cuenta cuántas veces se llamó."""

    def callback():
        if contador is not None:
            contador.append(1)
        return estado

    return Action(callback)


def test_action_retorna_el_estado_del_callback():
    assert Action(lambda: EXITO).tick() == EXITO
    assert Action(lambda: FALLO).tick() == FALLO
    assert Action(lambda: EN_PROGRESO).tick() == EN_PROGRESO


def test_selector_retorna_exito_en_el_primero_que_tiene_exito():
    llamadas_segundo = []
    selector = Selector(
        [
            accion_fija(FALLO),
            accion_fija(EXITO, llamadas_segundo),
            accion_fija(FALLO, llamadas_segundo),  # no debería llegar a evaluarse
        ]
    )

    assert selector.tick() == EXITO
    assert llamadas_segundo == [1]  # solo se llamó la segunda acción


def test_selector_retorna_fallo_si_todos_los_hijos_fallan():
    selector = Selector([accion_fija(FALLO), accion_fija(FALLO), accion_fija(FALLO)])

    assert selector.tick() == FALLO


def test_selector_corta_y_retorna_en_progreso():
    llamadas_tercero = []
    selector = Selector(
        [
            accion_fija(FALLO),
            accion_fija(EN_PROGRESO),
            accion_fija(EXITO, llamadas_tercero),  # no debería llegar a evaluarse
        ]
    )

    assert selector.tick() == EN_PROGRESO
    assert llamadas_tercero == []


def test_sequence_retorna_exito_si_todos_los_hijos_tienen_exito():
    secuencia = Sequence([accion_fija(EXITO), accion_fija(EXITO), accion_fija(EXITO)])

    assert secuencia.tick() == EXITO


def test_sequence_retorna_fallo_en_el_primero_que_falla():
    llamadas_tercero = []
    secuencia = Sequence(
        [
            accion_fija(EXITO),
            accion_fija(FALLO),
            accion_fija(EXITO, llamadas_tercero),  # no debería llegar a evaluarse
        ]
    )

    assert secuencia.tick() == FALLO
    assert llamadas_tercero == []


def test_sequence_corta_y_retorna_en_progreso():
    llamadas_tercero = []
    secuencia = Sequence(
        [
            accion_fija(EXITO),
            accion_fija(EN_PROGRESO),
            accion_fija(EXITO, llamadas_tercero),  # no debería llegar a evaluarse
        ]
    )

    assert secuencia.tick() == EN_PROGRESO
    assert llamadas_tercero == []


def test_arbol_de_enemigo_persigue_y_dispara_en_rango():
    """Reproduce la estructura real del enemigo: Selector con una Sequence
    de persecución/disparo y una Action de "quedarse quieto" como
    respaldo, para confirmar que el árbol combinado se comporta como
    se espera en ambos casos (en rango / fuera de rango)."""

    en_rango = True
    disparos = []

    def en_rango_de_disparo():
        return EXITO if en_rango else FALLO

    def disparar():
        disparos.append(1)
        return EXITO

    def quedarse_quieto():
        return EXITO

    arbol = Selector(
        [
            Sequence([Action(en_rango_de_disparo), Action(disparar)]),
            Action(quedarse_quieto),
        ]
    )

    assert arbol.tick() == EXITO
    assert disparos == [1]

    en_rango = False
    disparos.clear()

    assert arbol.tick() == EXITO  # cae al fallback de "quedarse quieto"
    assert disparos == []
