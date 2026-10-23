"""Menú de inicio: modo de juego y cursores de rol (src/ui/seleccion.py, sin pygame)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.seleccion import (  # noqa: E402
    DOS_JUGADORES,
    UN_JUGADOR,
    CursorRol,
    SeleccionRoles,
    SelectorModo,
)
from src.ui.terminal_decision import DERECHA, IZQUIERDA  # noqa: E402


def test_modulo_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.ui.seleccion; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


def test_modo_empieza_en_un_jugador_y_alterna():
    selector = SelectorModo()
    assert selector.seleccionado == UN_JUGADOR
    selector.mover(DERECHA)
    assert selector.seleccionado == DOS_JUGADORES
    selector.mover(DERECHA)
    assert selector.seleccionado == UN_JUGADOR
    selector.mover(IZQUIERDA)
    assert selector.seleccionado == DOS_JUGADORES


def test_cursor_da_la_vuelta_y_se_bloquea_al_confirmar():
    cursor = CursorRol(4)
    cursor.mover(IZQUIERDA)
    assert cursor.indice == 3
    cursor.confirmar()
    cursor.mover(DERECHA)
    assert cursor.indice == 3  # confirmado: no se mueve
    cursor.cancelar()
    cursor.mover(DERECHA)
    assert cursor.indice == 0


def test_atajo_elige_y_confirma():
    cursor = CursorRol(4)
    cursor.elegir(2)
    assert cursor.indice == 2 and cursor.confirmado


def test_con_dos_jugadores_empieza_solo_cuando_ambos_confirman():
    seleccion = SeleccionRoles(2, 4)
    j1, j2 = seleccion.cursores
    assert (j1.indice, j2.indice) == (0, 3)  # arrancan en extremos opuestos
    j1.confirmar()
    assert not seleccion.lista
    j2.confirmar()
    assert seleccion.lista
    j2.cancelar()
    assert not seleccion.lista


def test_pueden_elegir_el_mismo_rol():
    seleccion = SeleccionRoles(2, 4)
    seleccion.cursores[0].elegir(1)
    seleccion.cursores[1].elegir(1)
    assert seleccion.lista
    assert seleccion.indices() == [1, 1]


def test_un_jugador_tiene_un_solo_cursor():
    seleccion = SeleccionRoles(1, 4)
    assert len(seleccion.cursores) == 1
    seleccion.cursores[0].confirmar()
    assert seleccion.lista
