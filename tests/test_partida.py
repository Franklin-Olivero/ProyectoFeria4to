"""Tests de la partida: viaje por la ciudad, decisión y derrota global (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    COSTO_VIAJE_COLAPSO,
    PESOS_INICIALES_CIUDAD,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_PLAZA,
)
from src.core.escenas import Escena, escena_tras_colapso  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.ui.mapa_ciudad import SelectorZona  # noqa: E402
from src.ui.terminal_decision import (  # noqa: E402
    DERECHA,
    DETONACION,
    IZQUIERDA,
    PURIFICACION_EXITOSA,
)


def test_partida_nueva_empieza_en_la_plaza_sin_colapso():
    partida = Partida()
    assert partida.ubicacion == ZONA_PLAZA
    assert partida.colapso.valor == 0.0
    assert partida.progreso.mazmorras_completadas == 0
    assert not partida.alcaldia_desbloqueada()


def test_viajar_cobra_el_costo_de_la_ruta_y_mueve_al_jugador():
    partida = Partida()
    _, costo = partida.viajar(ZONA_EMPRESA_MEDIOS)
    assert costo == 5
    assert partida.colapso.valor == pytest.approx(5 * COSTO_VIAJE_COLAPSO)
    assert partida.ubicacion == ZONA_EMPRESA_MEDIOS
    # Viajar a donde ya se está no cuesta nada.
    partida.viajar(ZONA_EMPRESA_MEDIOS)
    assert partida.colapso.valor == pytest.approx(5 * COSTO_VIAJE_COLAPSO)


def test_decision_aplica_colapso_progreso_y_pesos_de_la_zona():
    partida = Partida()
    partida.registrar_decision(ZONA_COLEGIO, PURIFICACION_EXITOSA)
    assert partida.progreso.mazmorras_completadas == 1
    assert partida.ciudad.grafo.peso(ZONA_PLAZA, ZONA_COLEGIO) == 1
    assert partida.alcaldia_desbloqueada()

    partida.registrar_decision(ZONA_EMPRESA_MEDIOS, DETONACION)
    assert partida.progreso.mazmorras_completadas == 1
    assert partida.ciudad.grafo.peso(ZONA_PLAZA, ZONA_EMPRESA_MEDIOS) == 7


def test_colapso_en_100_activa_la_escena_de_derrota():
    partida = Partida()
    assert escena_tras_colapso(Escena.MAZMORRA, partida.colapso) == Escena.MAZMORRA
    partida.colapso.valor = 100.0
    assert partida.hay_derrota_global()
    for escena in (Escena.MAPA_CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE):
        assert escena_tras_colapso(escena, partida.colapso) == Escena.DERROTA


def test_colapso_justo_bajo_100_no_es_derrota():
    partida = Partida()
    partida.colapso.valor = 99.9
    assert escena_tras_colapso(Escena.MAPA_CIUDAD, partida.colapso) == Escena.MAPA_CIUDAD


def test_un_viaje_puede_llevar_el_colapso_al_100():
    partida = Partida()
    partida.colapso.valor = 99.9
    partida.viajar(ZONA_ALCALDIA)  # costo 7 -> +0.14
    assert partida.colapso.valor == 100.0
    assert escena_tras_colapso(Escena.MAPA_CIUDAD, partida.colapso) == Escena.DERROTA


def test_sumar_fallos_hasta_el_100_tolera_el_error_de_float():
    partida = Partida()
    partida.colapso.valor = 99.0
    for _ in range(5):
        partida.colapso.sumar_fallo()  # 99.0 + 5 * 0.2 puede quedar en 99.999...
    assert partida.hay_derrota_global()


def test_reinicio_deja_todo_en_estado_inicial():
    partida = Partida()
    partida.viajar(ZONA_COLEGIO)
    partida.registrar_decision(ZONA_COLEGIO, DETONACION)
    partida.registrar_decision(ZONA_COLEGIO, PURIFICACION_EXITOSA)
    partida.colapso.valor = 100.0

    partida.reiniciar()

    assert partida.colapso.valor == 0.0
    assert not partida.hay_derrota_global()
    assert partida.progreso.mazmorras_completadas == 0
    assert partida.ubicacion == ZONA_PLAZA
    for a, b, peso in PESOS_INICIALES_CIUDAD:
        assert partida.ciudad.grafo.peso(a, b) == peso
    assert escena_tras_colapso(Escena.MAPA_CIUDAD, partida.colapso) == Escena.MAPA_CIUDAD


def test_selector_de_zona_da_la_vuelta():
    selector = SelectorZona(["a", "b", "c"], "a")
    selector.mover(IZQUIERDA)
    assert selector.seleccionada == "c"
    selector.mover(DERECHA)
    selector.mover(DERECHA)
    assert selector.seleccionada == "b"
