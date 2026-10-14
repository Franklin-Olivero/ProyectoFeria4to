"""Tests de la invulnerabilidad tras un golpe (i-frames), sin pygame."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import INVULNERABILIDAD_DURACION  # noqa: E402
from src.entities.invulnerabilidad import Invulnerabilidad  # noqa: E402


def test_modulo_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.entities.invulnerabilidad; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


def test_duracion_es_0_6_segundos():
    assert INVULNERABILIDAD_DURACION == 0.6


def test_un_golpe_resta_vida_y_abre_la_ventana():
    inv = Invulnerabilidad()
    assert inv.aplicar_golpe(5, 1) == 4
    assert inv.activa


def test_segundo_golpe_dentro_de_la_ventana_no_resta():
    inv = Invulnerabilidad()
    vida = inv.aplicar_golpe(5, 1)
    inv.actualizar(INVULNERABILIDAD_DURACION - 0.01)
    assert inv.aplicar_golpe(vida, 1) == vida


def test_golpe_despues_de_la_ventana_si_resta():
    inv = Invulnerabilidad()
    vida = inv.aplicar_golpe(5, 1)
    inv.actualizar(INVULNERABILIDAD_DURACION)
    assert not inv.activa
    assert inv.aplicar_golpe(vida, 1) == vida - 1


def test_golpes_dentro_de_la_ventana_no_la_reinician():
    inv = Invulnerabilidad()
    vida = inv.aplicar_golpe(5, 1)  # abre la ventana en t = 0
    for _ in range(5):  # golpes en t = 0.1 .. 0.5
        inv.actualizar(0.1)
        vida = inv.aplicar_golpe(vida, 1)
    assert vida == 4
    inv.actualizar(0.11)  # t = 0.61: la ventana original ya cerró (no se reinició)
    assert not inv.activa
    assert inv.aplicar_golpe(vida, 1) == 3


def test_danio_continuo_respeta_la_ventana_pero_no_la_abre():
    inv = Invulnerabilidad()
    assert inv.aplicar_golpe(5, 0.1, inicia=False) == pytest.approx(4.9)
    assert not inv.activa  # el charco no abre la ventana
    inv.aplicar_golpe(5, 1)  # un proyectil sí la abre
    assert inv.aplicar_golpe(4, 0.1, inicia=False) == 4  # y el charco la respeta


def test_parpadeo_alterna_visible_e_invisible():
    inv = Invulnerabilidad()
    assert inv.visible
    inv.aplicar_golpe(5, 1)
    inv.actualizar(0.04)  # se muestrea a mitad de cada período, lejos de los bordes
    estados = []
    for _ in range(6):
        estados.append(inv.visible)
        inv.actualizar(0.08)
    assert estados == [True, False, True, False, True, False]
    inv.actualizar(1.0)
    assert inv.visible
