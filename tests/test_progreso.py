"""Tests del progreso entre mazmorras (sin pygame): solo una
"Purificación Exitosa" cuenta como mazmorra completada."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.dungeon.mazmorra_final import esta_desbloqueada  # noqa: E402
from src.dungeon.progreso import ProgresoPartida  # noqa: E402
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA  # noqa: E402


def test_detonacion_no_cuenta_pero_suma_colapso():
    progreso, colapso = ProgresoPartida(), ColapsoElectoral(50.0)
    progreso.registrar_decision(DETONACION, colapso)
    assert progreso.mazmorras_completadas == 0
    assert colapso.valor == pytest.approx(50.2)


def test_purificacion_exitosa_cuenta_y_resta_colapso():
    progreso, colapso = ProgresoPartida(), ColapsoElectoral(50.0)
    progreso.registrar_decision(PURIFICACION_EXITOSA, colapso)
    assert progreso.mazmorras_completadas == 1
    assert colapso.valor == pytest.approx(49.9)


def test_solo_purificacion_desbloquea_la_mazmorra_final():
    progreso, colapso = ProgresoPartida(), ColapsoElectoral()
    for _ in range(3):
        progreso.registrar_decision(DETONACION, colapso)
    assert not esta_desbloqueada(colapso, progreso.mazmorras_completadas)
    progreso.registrar_decision(PURIFICACION_EXITOSA, colapso)
    assert esta_desbloqueada(colapso, progreso.mazmorras_completadas)
