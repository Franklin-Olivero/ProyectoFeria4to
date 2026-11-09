"""Dash: la lógica pura (src/entities/dash.py) y su efecto en los roles.

Los tests de Dash no usan pygame; los de JugadorBase usan
pygame.Rect/Vector2 sin abrir ventana, como test_roles.py.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    DASH_COOLDOWN,
    DASH_DURACION,
    DASH_VELOCIDAD_MULT,
    VELOCIDAD_BASE,
)
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.dash import Dash  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402

ROLES = [Ciudadano, Influencer, Periodista, Candidato]
LIMITES = pygame.Rect(0, 0, 2000, 2000)
DT = 1 / 60


def test_modulo_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.entities.dash; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


# ----------------------------------------------------------------------
# Dash (lógica pura)
# ----------------------------------------------------------------------


def test_iniciar_activa_y_normaliza_la_direccion():
    dash = Dash()
    assert dash.iniciar((3, 4))
    assert dash.activo
    assert dash.direccion == pytest.approx((0.6, 0.8))
    assert dash.velocidad_multiplicador == DASH_VELOCIDAD_MULT
    assert not dash.puede_disparar
    assert dash.invulnerable


def test_direccion_nula_no_inicia():
    dash = Dash()
    assert not dash.iniciar((0, 0))
    assert not dash.activo


def test_termina_al_pasar_la_duracion():
    dash = Dash()
    dash.iniciar((1, 0))
    dash.actualizar(DASH_DURACION * 0.9)
    assert dash.activo
    dash.actualizar(DASH_DURACION * 0.2)
    assert not dash.activo
    assert dash.velocidad_multiplicador == 1.0
    assert dash.puede_disparar
    assert not dash.invulnerable


def test_cooldown_impide_encadenar_dashes():
    dash = Dash()
    dash.iniciar((1, 0))
    dash.actualizar(DASH_DURACION + 0.01)
    assert not dash.iniciar((1, 0))  # terminó, pero el cooldown sigue
    dash.actualizar(DASH_COOLDOWN)
    assert dash.iniciar((0, 1))


def test_cooldown_es_de_5_segundos():
    assert DASH_COOLDOWN == 5.0


def test_fraccion_cooldown_va_de_1_a_0():
    dash = Dash()
    assert dash.fraccion_cooldown == 0.0  # listo desde el inicio
    dash.iniciar((1, 0))
    assert dash.fraccion_cooldown == 1.0
    dash.actualizar(DASH_COOLDOWN / 2)
    assert dash.fraccion_cooldown == pytest.approx(0.5)
    dash.actualizar(DASH_COOLDOWN)
    assert dash.fraccion_cooldown == 0.0


def test_tiempo_listo_marca_cuando_vuelve_a_estar_disponible():
    dash = Dash()
    assert dash.tiempo_listo == float("inf")  # sin destello al arrancar
    dash.iniciar((1, 0))
    dash.actualizar(DASH_COOLDOWN - 0.01)
    dash.actualizar(0.02)  # en este frame termina el cooldown
    assert dash.tiempo_listo == 0.0
    dash.actualizar(0.1)
    assert dash.tiempo_listo == pytest.approx(0.1)


def test_no_se_reinicia_mientras_esta_activo():
    dash = Dash()
    dash.iniciar((1, 0))
    assert not dash.iniciar((0, 1))
    assert dash.direccion == (1.0, 0.0)


# ----------------------------------------------------------------------
# Dash en los roles (JugadorBase)
# ----------------------------------------------------------------------


def jugador_en_centro(clase):
    jugador = clase(1000, 1000)
    return jugador


@pytest.mark.parametrize("clase", ROLES)
def test_dash_recorre_velocidad_por_multiplicador(clase):
    jugador = jugador_en_centro(clase)
    jugador.mover((1, 0), DT, LIMITES)  # camina un frame: fija la dirección de movimiento
    inicio = jugador.posicion.x
    assert jugador.iniciar_dash()
    jugador.mover((1, 0), DT, LIMITES)
    esperado = VELOCIDAD_BASE * jugador.stats.velocidad_mult * DASH_VELOCIDAD_MULT * DT
    assert jugador.posicion.x - inicio == pytest.approx(esperado, abs=1)


def test_dash_mantiene_la_direccion_aunque_cambie_el_input():
    jugador = jugador_en_centro(Ciudadano)
    jugador.mover((1, 0), DT, LIMITES)
    jugador.iniciar_dash()
    y_antes = jugador.posicion.y
    jugador.mover((0, 1), DT, LIMITES)  # el input pide bajar
    assert jugador.posicion.y == y_antes  # pero el dash sigue a la derecha


def test_quieto_el_dash_sale_hacia_donde_mira():
    jugador = jugador_en_centro(Periodista)
    jugador.direccion_mirada = pygame.Vector2(0, -1)
    jugador.mover((0, 0), DT, LIMITES)
    assert jugador.iniciar_dash()
    assert jugador.dash.direccion == (0.0, -1.0)


def test_dash_no_atraviesa_muros():
    limites = pygame.Rect(0, 0, 400, 400)
    jugador = Influencer(380, 200)  # pegado al muro derecho
    jugador.mover((1, 0), DT, limites)
    jugador.iniciar_dash()
    for _ in range(10):
        jugador.mover((1, 0), DT, limites)
    assert jugador.rect.right <= limites.right


def test_durante_el_dash_no_se_dispara_y_el_cooldown_queda_en_pausa():
    jugador = jugador_en_centro(Ciudadano)
    jugador.tiempo_para_disparo = 0.3
    jugador.mover((1, 0), DT, LIMITES)
    jugador.iniciar_dash()
    assert jugador.actualizar_disparo(DT, disparando=True) == []
    assert jugador.tiempo_para_disparo == 0.3
    jugador.actualizar_dash(DASH_DURACION + 0.01)
    assert jugador.actualizar_disparo(0.31, disparando=True)


def test_durante_el_dash_no_se_usa_la_habilidad():
    jugador = jugador_en_centro(Ciudadano)
    jugador.carga_habilidad = jugador.carga_maxima
    jugador.mover((1, 0), DT, LIMITES)
    jugador.iniciar_dash()
    assert not jugador.intentar_habilidad()
    assert jugador.carga_habilidad == jugador.carga_maxima  # no se gastó
    jugador.actualizar_dash(DASH_DURACION + 0.01)
    assert jugador.intentar_habilidad()


def test_durante_el_dash_no_recibe_dano_ni_abre_la_ventana():
    jugador = jugador_en_centro(Candidato)
    jugador.mover((1, 0), DT, LIMITES)
    jugador.iniciar_dash()
    jugador.recibir_dano(1)
    assert jugador.vida == jugador.vida_maxima
    assert not jugador.invulnerabilidad.activa
    jugador.actualizar_dash(DASH_DURACION + 0.01)
    jugador.recibir_dano(1)
    assert jugador.vida == jugador.vida_maxima - 1


def test_el_rastro_guarda_posiciones_solo_durante_el_dash():
    jugador = jugador_en_centro(Ciudadano)
    jugador.mover((1, 0), DT, LIMITES)
    assert len(jugador.rastro_dash) == 0
    jugador.iniciar_dash()
    for _ in range(5):
        jugador.mover((1, 0), DT, LIMITES)
    assert 0 < len(jugador.rastro_dash) <= jugador.rastro_dash.maxlen
    jugador.actualizar_dash(DASH_DURACION + 0.01)
    assert len(jugador.rastro_dash) == 0
