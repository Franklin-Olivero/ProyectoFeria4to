"""Tests del balance de roles y de la carga compartida (sin pygame).

Verifican las reglas de diseño de src/core/balance.py: cada rol tiene
una fortaleza y una debilidad, ninguno domina a otro, y el DPS de todos
queda en un rango parejo.
"""

import os
import subprocess
import sys
from itertools import permutations

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    BUFF_KILL_MULTIPLICADOR,
    CADENCIA_MAXIMA,
    CADENCIA_MINIMA_INTERVALO,
    CARGA_COMPARTIDA,
    STATS_POR_ROL,
    dps_nominal,
    intervalo_disparo,
    stats_normalizadas,
)
from src.core.equipo import registrar_kill_equipo  # noqa: E402

ROLES = list(STATS_POR_ROL)
STATS_COMPARADAS = ("velocidad_mult", "cadencia", "vida_mult", "danio_mult")


class JugadorFalso:
    """Doble mínimo de JugadorBase (que importa pygame): misma regla de
    carga, acotada a la carga_maxima del rol."""

    def __init__(self, rol):
        self.carga_maxima = STATS_POR_ROL[rol].carga_maxima
        self.carga_habilidad = 0.0

    def sumar_carga(self, cantidad):
        self.carga_habilidad = min(self.carga_habilidad + cantidad, self.carga_maxima)

    def registrar_kill(self):
        self.sumar_carga(1)


def test_balance_y_equipo_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.core.balance, src.core.equipo; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


# ----------------------------------------------------------------------
# Ningún rol domina, DPS parejo
# ----------------------------------------------------------------------


@pytest.mark.parametrize("rol_a, rol_b", list(permutations(ROLES, 2)))
def test_ningun_rol_domina_a_otro(rol_a, rol_b):
    a, b = STATS_POR_ROL[rol_a], STATS_POR_ROL[rol_b]
    domina = all(getattr(a, s) >= getattr(b, s) for s in STATS_COMPARADAS)
    assert not domina, f"{rol_a} es >= que {rol_b} en velocidad, cadencia, vida y daño"


@pytest.mark.parametrize("rol", ROLES)
def test_dps_nominal_dentro_de_30_por_ciento_del_promedio(rol):
    promedio = sum(dps_nominal(s) for s in STATS_POR_ROL.values()) / len(STATS_POR_ROL)
    dps = dps_nominal(STATS_POR_ROL[rol])
    assert promedio * 0.7 <= dps <= promedio * 1.3


def test_velocidad_y_vida_distintas_entre_los_4_roles():
    for atributo in ("velocidad_mult", "vida_mult"):
        valores = [getattr(s, atributo) for s in STATS_POR_ROL.values()]
        assert len(set(valores)) == len(valores), atributo


def test_perfil_velocidad_vida_carga_distinto_entre_los_4_roles():
    # La tabla de diseño repite carga 5 en Influencer y Periodista, así
    # que la carga sola no distingue a todos; el perfil combinado sí.
    perfiles = [(s.velocidad_mult, s.vida_mult, s.carga_maxima) for s in STATS_POR_ROL.values()]
    assert len(set(perfiles)) == len(perfiles)


# ----------------------------------------------------------------------
# Cadencia y buff por kill
# ----------------------------------------------------------------------


@pytest.mark.parametrize("rol", ROLES)
def test_cooldown_es_uno_sobre_cadencia(rol):
    cadencia = STATS_POR_ROL[rol].cadencia
    assert intervalo_disparo(cadencia) == pytest.approx(1 / cadencia)


@pytest.mark.parametrize("rol", ROLES)
def test_buff_por_kill_acorta_el_cooldown(rol):
    cadencia = STATS_POR_ROL[rol].cadencia
    con_buff = intervalo_disparo(cadencia, buff_activo=True)
    assert con_buff < intervalo_disparo(cadencia)
    assert con_buff == pytest.approx(1 / (cadencia * BUFF_KILL_MULTIPLICADOR))


def test_buff_respeta_tope_de_cadencia_y_piso_de_intervalo():
    # Una cadencia exagerada: con buff superaría el tope de 12/s.
    intervalo = intervalo_disparo(CADENCIA_MAXIMA, buff_activo=True)
    assert intervalo >= 1 / CADENCIA_MAXIMA
    assert intervalo >= CADENCIA_MINIMA_INTERVALO
    assert intervalo_disparo(1000, buff_activo=True) >= CADENCIA_MINIMA_INTERVALO


def test_stats_normalizadas_el_maximo_vale_1():
    normalizadas = stats_normalizadas()
    for atributo in STATS_COMPARADAS:
        fracciones = [normalizadas[rol][atributo] for rol in ROLES]
        assert max(fracciones) == 1.0
        assert all(0 < f <= 1 for f in fracciones)


# ----------------------------------------------------------------------
# Carga compartida de equipo
# ----------------------------------------------------------------------


def test_carga_compartida_da_un_cuarto_al_aliado():
    asesino, aliado = JugadorFalso("candidato"), JugadorFalso("ciudadano")
    registrar_kill_equipo(asesino, [asesino, aliado])
    assert asesino.carga_habilidad == 1
    assert aliado.carga_habilidad == CARGA_COMPARTIDA == 0.25


def test_carga_compartida_acumula_fracciones_sin_pasar_del_maximo():
    asesino, aliado = JugadorFalso("candidato"), JugadorFalso("candidato")
    for _ in range(4):
        registrar_kill_equipo(asesino, [aliado])
    assert aliado.carga_habilidad == 1.0
    for _ in range(100):
        registrar_kill_equipo(asesino, [aliado])
    assert aliado.carga_habilidad == STATS_POR_ROL["candidato"].carga_maxima


def test_jugador_solo_no_recibe_carga_extra():
    solo = JugadorFalso("periodista")
    registrar_kill_equipo(solo, [solo])
    assert solo.carga_habilidad == 1
