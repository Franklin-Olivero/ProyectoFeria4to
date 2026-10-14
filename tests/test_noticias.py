"""Tests de los titulares del cintillo "Breaking News Civitas" (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import COLAPSO_TITULAR_ALTO  # noqa: E402
from src.dungeon.noticias import (  # noqa: E402
    TITULAR_ALCALDIA_ABIERTA,
    TITULAR_ALCALDIA_SELLADA,
    TITULAR_SIN_NOVEDADES,
    EstadoNoticias,
    generar_titulares,
)
from src.dungeon.partida import Partida  # noqa: E402
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA  # noqa: E402

TOXICIDAD = {"Colegio": 85.0, "Hospital": 50.0, "Empresa de Medios": 15.0}


def test_sin_novedades():
    titulares = generar_titulares(EstadoNoticias(toxicidad=TOXICIDAD))
    assert titulares[0] == TITULAR_SIN_NOVEDADES
    assert TITULAR_ALCALDIA_SELLADA in titulares
    assert not any("barricada" in t or "Colapso" in t for t in titulares)
    # La toxicidad de cada zona, de la más tóxica a la menos.
    assert titulares[-3:] == ["Colegio: toxicidad 85", "Hospital: toxicidad 50", "Empresa de Medios: toxicidad 15"]


def test_calle_bloqueada():
    estado = EstadoNoticias(toxicidad=TOXICIDAD, calles_bloqueadas=[("Cruce Sur", "Empresa de Medios")])
    titulares = generar_titulares(estado)
    assert "Cruce Sur" in titulares[0] and "Empresa de Medios" in titulares[0] and "barricada" in titulares[0]
    assert TITULAR_SIN_NOVEDADES not in titulares


def test_colapso_alto():
    bajo = generar_titulares(EstadoNoticias(colapso=COLAPSO_TITULAR_ALTO - 0.1))
    assert not any("Colapso electoral" in t for t in bajo)
    alto = generar_titulares(EstadoNoticias(colapso=72.4))
    assert alto[0] == "Colapso electoral en 72.4%: la ciudad al borde"
    assert TITULAR_SIN_NOVEDADES not in alto


def test_alcaldia_desbloqueada():
    titulares = generar_titulares(EstadoNoticias(alcaldia_abierta=True))
    assert TITULAR_ALCALDIA_ABIERTA in titulares
    assert TITULAR_ALCALDIA_SELLADA not in titulares


def test_titulares_de_la_partida_siguen_el_estado_real():
    partida = Partida()
    assert partida.titulares()[0] == TITULAR_SIN_NOVEDADES
    partida.registrar_decision("Empresa de Medios", DETONACION)
    assert "barricada" in partida.titulares()[0]
    partida.registrar_decision("Colegio", PURIFICACION_EXITOSA)
    assert TITULAR_ALCALDIA_ABIERTA in partida.titulares()
