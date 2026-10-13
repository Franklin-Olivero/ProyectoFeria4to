"""Tests del jefe final, los charcos y la mazmorra final (sin pygame)."""

import os
import random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

import src.dungeon.mazmorra_final as mazmorra_final  # noqa: E402
import src.ui.terminal_decision as terminal_decision  # noqa: E402
from src.core.balance import (  # noqa: E402
    CHARCO_AVISO,
    CHARCO_DANIO_POR_SEGUNDO,
    CHARCO_DURACION,
    ESCUDO_VIDA,
    PAUSA_CAMBIO_FASE,
    RAFAGA_CANTIDAD,
    RAFAGA_INTERVALO,
    TIEMPO_LIMITE_JEFE,
)
from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.dungeon.charco import Charco  # noqa: E402
from src.dungeon.mazmorra_final import (  # noqa: E402
    EN_COMBATE,
    VICTORIA,
    MazmorraFinal,
    esta_desbloqueada,
)
from src.entities.jefe import (  # noqa: E402
    EVENTO_CAMBIO_FASE,
    EVENTO_ESCUDO_ROTO,
    Jefe,
    SalidaJefe,
    fase_por_vida,
)

LIMITES = (20, 120, 780, 590)  # izquierda, arriba, derecha, abajo


class JugadorFalso:
    """Lo mínimo que MazmorraFinal lee de un jugador."""

    def __init__(self, x=400, y=550, vida=5):
        self.posicion = SimpleNamespace(x=x, y=y)
        self.vida = vida

    @property
    def vivo(self):
        return self.vida > 0

    def recibir_dano(self, danio, inicia_invulnerabilidad=True):
        self.vida -= danio


def crear_jefe():
    return Jefe(400, 240, LIMITES, random.Random(0))


def llevar_a_fase_2(jefe):
    jefe.recibir_dano(jefe.vida_maxima * 0.4)  # justo 60%
    assert jefe.fase == 2 and jefe.escudo_anonimato


def test_modulos_del_jefe_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = (
        "import sys, src.entities.jefe, src.dungeon.charco, src.dungeon.mazmorra_final;"
        "print('pygame' in sys.modules)"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


# ----------------------------------------------------------------------
# Fases
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "fraccion, fase",
    [(1.0, 1), (0.61, 1), (0.6001, 1), (0.60, 2), (0.45, 2), (0.3001, 2), (0.30, 3), (0.1, 3), (0.0, 3)],
)
def test_fase_por_vida_con_limites_exactos(fraccion, fase):
    assert fase_por_vida(fraccion) == fase


def test_cambio_de_fase_pausa_ataques_y_emite_evento():
    jefe = crear_jefe()
    llevar_a_fase_2(jefe)
    assert jefe.tiempo_pausa == PAUSA_CAMBIO_FASE
    assert EVENTO_CAMBIO_FASE in jefe.eventos
    salida = SalidaJefe()
    jefe.actualizar(PAUSA_CAMBIO_FASE / 2, (400, 550), salida)
    assert salida.disparos == []  # durante la pausa no ataca
    jefe.actualizar(PAUSA_CAMBIO_FASE, (400, 550), salida)
    assert salida.disparos  # pasada la pausa, la espiral dispara


def test_fase_1_rafaga_radial_e_invocacion():
    jefe = crear_jefe()
    salida = SalidaJefe()
    jefe.actualizar(RAFAGA_INTERVALO, (400, 550), salida)
    assert len(salida.disparos) == RAFAGA_CANTIDAD
    for _ in range(8 * 60):
        jefe.actualizar(1 / 60, (400, 550), salida)
    assert salida.invocaciones >= 2


def test_fase_3_se_acerca_al_jugador_y_suelta_charcos():
    jefe = crear_jefe()
    jefe.vida = jefe.vida_maxima * 0.3
    salida = SalidaJefe()
    jefe.actualizar(1 / 60, (400, 550), salida)
    assert jefe.fase == 3
    y_inicial = jefe.y
    for _ in range(5 * 60):
        jefe.actualizar(1 / 60, (400, 550), salida)
    assert jefe.y > y_inicial
    assert salida.charcos


# ----------------------------------------------------------------------
# Escudo de anonimato
# ----------------------------------------------------------------------


def test_con_escudo_no_pierde_vida_y_al_romperse_si():
    jefe = crear_jefe()
    llevar_a_fase_2(jefe)
    vida = jefe.vida
    for _ in range(ESCUDO_VIDA - 1):
        jefe.recibir_dano(5)
    assert jefe.vida == vida
    assert jefe.vida_escudo == 1
    jefe.recibir_dano(5)  # impacto 15: rompe el escudo
    assert not jefe.escudo_anonimato
    assert jefe.vida == vida
    jefe.recibir_dano(5)
    assert jefe.vida == vida - 5


def test_fact_checking_rompe_el_escudo_de_golpe():
    # RayoPerforante(quita_escudo=True).al_impactar hace exactamente
    # esto antes de dañar (ver test_roles para la prueba con el rayo real).
    jefe = crear_jefe()
    llevar_a_fase_2(jefe)
    jefe.eventos.clear()
    jefe.escudo_anonimato = False
    assert jefe.vida_escudo == 0
    assert EVENTO_ESCUDO_ROTO in jefe.eventos
    vida = jefe.vida
    jefe.recibir_dano(2)
    assert jefe.vida == vida - 2


# ----------------------------------------------------------------------
# Charcos
# ----------------------------------------------------------------------


def test_charco_no_dania_durante_el_aviso():
    charco = Charco(100, 100)
    charco.actualizar(CHARCO_AVISO * 0.9)
    assert charco.en_aviso
    assert charco.danio_para(100, 100, 1.0) == 0.0


def test_charco_dania_en_fase_activa_solo_dentro():
    charco = Charco(100, 100)
    charco.actualizar(CHARCO_AVISO)
    assert charco.activo
    assert charco.danio_para(100, 100, 0.5) == pytest.approx(CHARCO_DANIO_POR_SEGUNDO * 0.5)
    assert charco.danio_para(100 + charco.radio + 1, 100, 0.5) == 0.0


def test_charco_desaparece_al_terminar():
    charco = Charco(100, 100)
    charco.actualizar(CHARCO_AVISO + CHARCO_DURACION)
    assert not charco.vivo
    assert charco.danio_para(100, 100, 1.0) == 0.0


# ----------------------------------------------------------------------
# Mazmorra final
# ----------------------------------------------------------------------


def test_toxicidad_fija_al_maximo():
    mazmorra = MazmorraFinal(ColapsoElectoral(), LIMITES, random.Random(0))
    assert mazmorra.nivel_toxicidad == 100.0
    assert mazmorra.dificultad == mazmorra_final.nivel_a_dificultad(100.0)


def test_derrota_por_tiempo_agotado_suma_fallo_y_reinicia():
    colapso = ColapsoElectoral(50.0)
    mazmorra = MazmorraFinal(colapso, LIMITES, random.Random(0))
    jefe_original = mazmorra.jefe
    # Jugador lejos del jefe y fuera de alcance de charcos: solo cuenta el tiempo.
    mazmorra.actualizar(TIEMPO_LIMITE_JEFE + 1, JugadorFalso(vida=1000))
    assert colapso.valor == pytest.approx(50.2)
    assert mazmorra.derrotas == 1
    assert mazmorra.reinicio_pendiente
    assert mazmorra.estado == EN_COMBATE
    assert mazmorra.tiempo_restante == TIEMPO_LIMITE_JEFE
    assert mazmorra.jefe is not jefe_original
    assert mazmorra.jefe.vida == mazmorra.jefe.vida_maxima


def test_derrota_si_el_jugador_muere():
    colapso = ColapsoElectoral(50.0)
    mazmorra = MazmorraFinal(colapso, LIMITES, random.Random(0))
    mazmorra.actualizar(1 / 60, JugadorFalso(vida=0))
    assert mazmorra.derrotas == 1
    assert colapso.valor == pytest.approx(50.2)


def test_victoria_resta_colapso_una_sola_vez():
    colapso = ColapsoElectoral(50.0)
    mazmorra = MazmorraFinal(colapso, LIMITES, random.Random(0))
    mazmorra.jefe.vida = 0
    jugador = JugadorFalso()
    mazmorra.actualizar(1 / 60, jugador)
    mazmorra.actualizar(1 / 60, jugador)
    assert mazmorra.estado == VICTORIA
    assert mazmorra.texto_mensaje() == "Servidor Central purificado"
    assert colapso.valor == pytest.approx(49.9)


def test_mazmorra_final_nunca_instancia_terminal_decision(monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("La mazmorra final no debe tener minijuego de decisión")

    monkeypatch.setattr(terminal_decision.TerminalDecision, "__init__", prohibido)
    assert not hasattr(mazmorra_final, "TerminalDecision")

    # Pelea completa con derrota, reinicio y victoria.
    colapso = ColapsoElectoral()
    mazmorra = MazmorraFinal(colapso, LIMITES, random.Random(0))
    jugador = JugadorFalso(vida=1000)
    for _ in range(600):
        mazmorra.actualizar(1 / 60, jugador)
    mazmorra.actualizar(TIEMPO_LIMITE_JEFE, jugador)
    mazmorra.jefe.vida = 0
    mazmorra.actualizar(1 / 60, jugador)
    assert mazmorra.estado == VICTORIA
    assert not any(isinstance(v, terminal_decision.TerminalDecision) for v in vars(mazmorra).values())


# ----------------------------------------------------------------------
# Desbloqueo
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "colapso, completadas, esperado",
    [
        (80.0, 0, False),  # justo 80: no basta, debe SUPERAR 80
        (80.1, 0, True),
        (0.0, 0, False),
        (0.0, 1, True),
        (90.0, 3, True),
    ],
)
def test_esta_desbloqueada_casos_borde(colapso, completadas, esperado):
    assert esta_desbloqueada(ColapsoElectoral(colapso), completadas) is esperado
