"""Cooperativo local: reglas de equipo, objetivos de los enemigos,
cruce de puertas, pelea final con 2 jugadores y partículas del dash.

Usan pygame.Rect/Vector2 sin abrir ventana, como test_roles.py; las
reglas de src/core/equipo.py se prueban sin pygame.
"""

import os
import random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import CHARCO_AVISO, REPORTES_POR_ZONA, VIDA_AL_REVIVIR, ZONA_HOSPITAL  # noqa: E402
from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.core.equipo import (  # noqa: E402
    jugador_mas_cercano,
    jugadores_en_combate,
    revivir_caidos,
    todos_caidos,
)
from src.dungeon.charco import Charco  # noqa: E402
from src.dungeon.cuarto import Cuarto  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.mazmorra_final import MazmorraFinal  # noqa: E402
from src.dungeon.mazmorra_jugable import MazmorraJugable  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui.particulas import SistemaParticulas  # noqa: E402

LIMITES_ARENA = (0, 0, 800, 600)


def test_reglas_de_equipo_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.core.equipo; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


# ----------------------------------------------------------------------
# Reglas de equipo (src/core/equipo.py)
# ----------------------------------------------------------------------


def falso(x, y, vida=5):
    return SimpleNamespace(
        posicion=SimpleNamespace(x=x, y=y), vida=vida, vivo=vida > 0,
        invulnerabilidad=SimpleNamespace(reiniciar=lambda: None),
    )


def test_en_combate_excluye_caidos_salvo_que_caigan_todos():
    a, b = falso(0, 0), falso(10, 0, vida=0)
    assert jugadores_en_combate([a, b]) == [a]
    b.vivo = False
    a.vida, a.vivo = 0, False
    assert jugadores_en_combate([a, b]) == [a, b]  # como en solitario
    assert todos_caidos([a, b])


def test_mas_cercano_ignora_al_caido():
    cerca, lejos = falso(10, 0), falso(500, 0)
    assert jugador_mas_cercano((0, 0), [lejos, cerca]) is cerca
    cerca.vida, cerca.vivo = 0, False
    assert jugador_mas_cercano((0, 0), [lejos, cerca]) is lejos


def test_revivir_solo_si_queda_alguien_en_pie():
    j1, j2 = Ciudadano(0, 0), Influencer(0, 0)
    j2.vida = 0
    assert revivir_caidos([j1, j2]) == [j2]
    assert j2.vida == VIDA_AL_REVIVIR
    j1.vida = j2.vida = 0
    assert revivir_caidos([j1, j2]) == []
    assert j1.vida == 0


# ----------------------------------------------------------------------
# Escenarios con 2 jugadores
# ----------------------------------------------------------------------


def test_cada_enemigo_persigue_al_jugador_mas_cercano():
    cuarto = Cuarto()
    enemigo = cuarto.enemigos[0]
    cerca = Ciudadano(enemigo.rect.centerx + 120, enemigo.rect.centery)
    lejos = Influencer(cuarto.rect.right - 30, cuarto.rect.bottom - 30)
    cuarto.enemigos = [enemigo]
    distancia_antes = enemigo.posicion.distance_to(cerca.rect.center)
    cuarto.actualizar(0.2, [lejos, cerca], [])
    assert enemigo.posicion.distance_to(cerca.rect.center) < distancia_antes


def test_al_cruzar_una_puerta_pasa_todo_el_equipo_en_fila():
    mazmorra = MazmorraJugable(Mazmorra(REPORTES_POR_ZONA[ZONA_HOSPITAL], ZONA_HOSPITAL, 6, 0))
    j1, j2 = Ciudadano(0, 0), Influencer(0, 0)
    mazmorra.colocar_en_entrada([j1, j2])
    assert j1.rect.centery == j2.rect.centery
    assert abs(j1.rect.centerx - j2.rect.centerx) == assets.SEPARACION_JUGADORES_COOP

    puerta = next(p for p in mazmorra.cuarto.puertas.values() if not p.sellada)
    entrada = mazmorra.mazmorra.actual
    j1.rect.center = puerta.rect.center
    j1.posicion.update(j1.rect.center)
    mazmorra.actualizar(1 / 60, [j1, j2], [])
    assert mazmorra.cambio_de_cuarto
    assert mazmorra.mazmorra.actual != entrada
    assert pygame.Vector2(j1.rect.center).distance_to(j2.rect.center) == pytest.approx(
        assets.SEPARACION_JUGADORES_COOP, abs=1
    )
    for jugador in (j1, j2):
        assert mazmorra.cuarto.rect.inflate(80, 80).collidepoint(jugador.rect.center)


def test_pelea_final_solo_se_pierde_si_caen_todos():
    colapso = ColapsoElectoral(50.0)
    mazmorra = MazmorraFinal(colapso, LIMITES_ARENA, random.Random(0))
    j1, j2 = falso(400, 550), falso(300, 550, vida=0)
    j1.recibir_dano = j2.recibir_dano = lambda *a, **k: None
    mazmorra.actualizar(1 / 60, [j1, j2])
    assert mazmorra.derrotas == 0
    j1.vida, j1.vivo = 0, False
    mazmorra.actualizar(1 / 60, [j1, j2])
    assert mazmorra.derrotas == 1


def test_los_charcos_danan_a_cada_jugador_que_los_pisa():
    mazmorra = MazmorraFinal(ColapsoElectoral(), LIMITES_ARENA, random.Random(0))
    golpes = []

    def jugador_en(x, y):
        j = falso(x, y, vida=100)
        j.recibir_dano = lambda danio, **k: golpes.append((x, danio))
        return j

    charco = Charco(200, 500)
    charco.tiempo = CHARCO_AVISO  # recién terminó el aviso: está activo
    mazmorra.charcos = [charco]
    j1, j2, lejos = jugador_en(200, 500), jugador_en(205, 505), jugador_en(700, 100)
    mazmorra._actualizar_charcos(0.1, [j1, j2, lejos])
    assert {x for x, _ in golpes} == {200, 205}


# ----------------------------------------------------------------------
# Partículas del dash (solo visual)
# ----------------------------------------------------------------------


def test_particulas_se_encogen_y_desaparecen():
    sistema = SistemaParticulas(random.Random(0))
    sistema.emitir((100, 100), assets.COLOR_CIUDADANO, cantidad=3)
    assert len(sistema.particulas) == 3
    sistema.actualizar(assets.DASH_PARTICULA_DURACION / 2)
    assert all(0 < p.fraccion < 1 for p in sistema.particulas)
    sistema.actualizar(assets.DASH_PARTICULA_DURACION)
    assert sistema.particulas == []


def test_particulas_nacen_cerca_del_jugador():
    sistema = SistemaParticulas(random.Random(1))
    sistema.emitir((100, 100), assets.COLOR_CIUDADANO, cantidad=20)
    dispersion = assets.DASH_PARTICULA_DISPERSION
    assert all(abs(p.x - 100) <= dispersion and abs(p.y - 100) <= dispersion for p in sistema.particulas)
