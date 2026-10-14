"""Tests del apuntado con mouse.

La función pura (src/core/apuntado.py) no usa pygame. Los tests de los
roles usan pygame.Rect/Vector2 sin abrir ventana, como test_roles.py.
"""

import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.apuntado import calcular_direccion_apuntado  # noqa: E402
from src.core.balance import ZONA_MUERTA_APUNTADO  # noqa: E402
from src.entities.candidato import Candidato, OndaExpansiva, ProyectilRebotante  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402

CENTRO = (100, 100)
PREVIA = (0.0, -1.0)
ROLES_CON_MOUSE = [Ciudadano, Influencer, Periodista]
LIMITES = pygame.Rect(0, 0, 500, 400)


class Teclas:
    """Sustituto de pygame.key.get_pressed() con las teclas dadas."""

    def __init__(self, *presionadas):
        self.presionadas = set(presionadas)

    def __getitem__(self, tecla):
        return tecla in self.presionadas


def cerca(vector, esperado):
    return vector[0] == pytest.approx(esperado[0]) and vector[1] == pytest.approx(esperado[1])


# ----------------------------------------------------------------------
# Función pura
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "punto, esperado",
    [
        ((150, 100), (1, 0)),  # derecha
        ((100, 40), (0, -1)),  # arriba (y crece hacia abajo)
        ((100, 180), (0, 1)),  # abajo
        ((20, 100), (-1, 0)),  # izquierda
    ],
)
def test_direcciones_cardinales(punto, esperado):
    assert cerca(calcular_direccion_apuntado(CENTRO, punto, PREVIA), esperado)


def test_diagonal_tiene_longitud_1():
    x, y = calcular_direccion_apuntado(CENTRO, (130, 70), PREVIA)
    assert math.hypot(x, y) == pytest.approx(1.0)
    assert cerca((x, y), (math.sqrt(0.5), -math.sqrt(0.5)))


@pytest.mark.parametrize("punto", [(100, 100), (103, 100), (100, 95), (104, 104)])
def test_dentro_de_la_zona_muerta_devuelve_la_previa(punto):
    assert calcular_direccion_apuntado(CENTRO, punto, PREVIA) == PREVIA


def test_justo_en_el_borde_de_la_zona_muerta_ya_apunta():
    punto = (CENTRO[0] + ZONA_MUERTA_APUNTADO, CENTRO[1])
    assert cerca(calcular_direccion_apuntado(CENTRO, punto, PREVIA), (1, 0))


def test_fuera_de_la_zona_muerta_siempre_longitud_1():
    for dx in range(-60, 61, 7):
        for dy in range(-60, 61, 7):
            if math.hypot(dx, dy) < ZONA_MUERTA_APUNTADO:
                continue
            x, y = calcular_direccion_apuntado(CENTRO, (100 + dx, 100 + dy), PREVIA)
            assert math.hypot(x, y) == pytest.approx(1.0)


def test_apuntado_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    salida = subprocess.run(
        [sys.executable, "-c", "import sys, src.core.apuntado; print('pygame' in sys.modules)"],
        cwd=raiz, capture_output=True, text=True, check=True,
    )
    assert salida.stdout.strip() == "False"


# ----------------------------------------------------------------------
# Roles que apuntan con el mouse
# ----------------------------------------------------------------------


@pytest.mark.parametrize("clase", ROLES_CON_MOUSE)
def test_apuntar_a_orienta_hacia_el_punto(clase):
    jugador = clase(250, 200)
    assert jugador.apunta_con_mouse
    jugador.apuntar_a((250, 300))
    assert isinstance(jugador.direccion_mirada, pygame.Vector2)
    assert cerca(jugador.direccion_mirada, (0, 1))
    jugador.apuntar_a((100, 50))
    assert cerca(jugador.direccion_mirada, (-math.sqrt(0.5), -math.sqrt(0.5)))


@pytest.mark.parametrize("clase", ROLES_CON_MOUSE)
def test_caminar_ya_no_cambia_la_mira(clase):
    jugador = clase(250, 200)
    jugador.apuntar_a((400, 200))  # mira a la derecha
    jugador.manejar_movimiento(Teclas(pygame.K_a, pygame.K_w), 0.1, LIMITES)
    assert jugador.rect.center != (250, 200)  # sí se movió
    assert cerca(jugador.direccion_mirada, (1, 0))


@pytest.mark.parametrize("clase", ROLES_CON_MOUSE)
def test_apuntar_a_en_la_zona_muerta_conserva_la_mira(clase):
    jugador = clase(250, 200)
    jugador.apuntar_a((400, 200))
    jugador.apuntar_a((252, 201))
    assert cerca(jugador.direccion_mirada, (1, 0))


@pytest.mark.parametrize("clase", ROLES_CON_MOUSE)
def test_ataque_basico_sale_hacia_el_mouse(clase):
    jugador = clase(250, 200)
    jugador.apuntar_a((250, 380))
    proyectiles = jugador.ataque_basico()
    central = proyectiles[len(proyectiles) // 2]  # el Ciudadano dispara en abanico
    assert cerca(central.direccion.normalize(), (0, 1))


def test_fact_checking_del_periodista_sale_hacia_el_mouse():
    jugador = Periodista(250, 200)
    for _ in range(jugador.carga_maxima):
        jugador.registrar_kill()
    jugador.apuntar_a((0, 200))
    salida = []
    assert jugador.usar_habilidad([], salida)
    assert cerca(salida[0].direccion.normalize(), (-1, 0))


# ----------------------------------------------------------------------
# Candidato: comportamiento anterior intacto
# ----------------------------------------------------------------------


def test_candidato_ignora_el_mouse():
    jugador = Candidato(250, 200)
    assert not jugador.apunta_con_mouse
    antes = pygame.Vector2(jugador.direccion_mirada)
    jugador.apuntar_a((400, 380))
    assert jugador.direccion_mirada == antes


def test_candidato_apunta_hacia_donde_camina():
    jugador = Candidato(250, 200)
    jugador.manejar_movimiento(Teclas(pygame.K_d), 0.1, LIMITES)
    assert cerca(jugador.direccion_mirada, (1, 0))
    jugador.apuntar_a((0, 0))  # el mouse no lo cambia
    assert cerca(jugador.direccion_mirada, (1, 0))


def test_candidato_onda_radial_y_debate_rebotante_como_antes():
    jugador = Candidato(250, 200)
    assert isinstance(jugador.ataque_basico()[0], OndaExpansiva)
    jugador.manejar_movimiento(Teclas(pygame.K_s), 0.1, LIMITES)
    for _ in range(jugador.carga_maxima):
        jugador.registrar_kill()
    salida = []
    jugador.apuntar_a((600, 0))  # ignorado
    assert jugador.usar_habilidad([], salida)
    assert all(isinstance(p, ProyectilRebotante) for p in salida)
    direcciones = [p.direccion.normalize() for p in salida]
    esperadas = [pygame.Vector2(0, 1).rotate(a) for a in assets.ANGULOS_DEBATE_REBOTANTE]
    for real, esperada in zip(direcciones, esperadas):
        assert cerca(real, esperada)
