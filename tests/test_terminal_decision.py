"""Tests del minijuego de decisión (lógica pura, sin pygame).

Árbol de `construir_arbol_publicacion()`:

    Publicación Viral
    ├── Verificar  -> Purificación Exitosa
    ├── Compartir  -> Detonación
    ├── Reportar   -> Purificación Exitosa
    └── Ignorar    -> Detonación
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.ui.terminal_decision import (  # noqa: E402
    CONFIRMAR,
    DERECHA,
    DETONACION,
    DURACION_TERMINAL,
    IZQUIERDA,
    PURIFICACION_EXITOSA,
    TerminalDecision,
    construir_arbol_publicacion,
)


@pytest.fixture
def terminal():
    terminal = TerminalDecision(construir_arbol_publicacion())
    terminal.iniciar()
    return terminal


def test_el_modulo_no_importa_pygame():
    # Proceso aparte: en este proceso otros tests ya pudieron cargar pygame.
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.ui.terminal_decision; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


def test_arbol_publicacion_tiene_la_forma_esperada():
    arbol = construir_arbol_publicacion()
    assert arbol.raiz.etiqueta == "Publicación Viral"
    assert [h.etiqueta for h in arbol.raiz.hijos] == [
        "Verificar",
        "Compartir",
        "Reportar",
        "Ignorar",
    ]
    hojas = [h.hijos[0].etiqueta for h in arbol.raiz.hijos]
    assert hojas == [PURIFICACION_EXITOSA, DETONACION, PURIFICACION_EXITOSA, DETONACION]


def test_iniciar_pone_cursor_en_raiz_y_reloj_lleno(terminal):
    assert terminal.nodo_actual is terminal.arbol.raiz
    assert terminal.indice_seleccionado == 0
    assert terminal.tiempo_restante == DURACION_TERMINAL
    assert terminal.resultado is None


def test_derecha_e_izquierda_mueven_entre_hijos(terminal):
    terminal.navegar(DERECHA)
    assert terminal.hijo_seleccionado.etiqueta == "Compartir"
    terminal.navegar(DERECHA)
    assert terminal.hijo_seleccionado.etiqueta == "Reportar"
    terminal.navegar(IZQUIERDA)
    assert terminal.hijo_seleccionado.etiqueta == "Compartir"


def test_navegar_da_la_vuelta_en_los_extremos(terminal):
    terminal.navegar(IZQUIERDA)
    assert terminal.hijo_seleccionado.etiqueta == "Ignorar"
    terminal.navegar(DERECHA)
    assert terminal.hijo_seleccionado.etiqueta == "Verificar"


def test_confirmar_desciende_sin_resultado_hasta_la_hoja(terminal):
    terminal.navegar(CONFIRMAR)
    assert terminal.nodo_actual.etiqueta == "Verificar"
    assert terminal.resultado is None


def test_verificar_lleva_a_purificacion_exitosa(terminal):
    terminal.navegar(CONFIRMAR)  # Verificar
    terminal.navegar(CONFIRMAR)  # Purificación Exitosa
    assert terminal.resultado == PURIFICACION_EXITOSA
    assert not terminal.activa


def test_compartir_lleva_a_detonacion(terminal):
    terminal.navegar(DERECHA)
    terminal.navegar(CONFIRMAR)
    terminal.navegar(CONFIRMAR)
    assert terminal.resultado == DETONACION


def test_timeout_sin_llegar_a_hoja_es_detonacion(terminal):
    terminal.actualizar(DURACION_TERMINAL - 0.5)
    assert terminal.resultado is None
    terminal.actualizar(1.0)
    assert terminal.tiempo_restante == 0.0
    assert terminal.resultado == DETONACION


def test_timeout_tras_resultado_no_lo_cambia(terminal):
    terminal.navegar(CONFIRMAR)
    terminal.navegar(CONFIRMAR)
    terminal.actualizar(DURACION_TERMINAL + 1)
    assert terminal.resultado == PURIFICACION_EXITOSA


def test_navegar_sin_iniciar_no_hace_nada():
    terminal = TerminalDecision(construir_arbol_publicacion())
    terminal.navegar(CONFIRMAR)
    assert terminal.nodo_actual is terminal.arbol.raiz
