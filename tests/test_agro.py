"""Agresividad absoluta de los enemigos (agro_permanente).

Usan pygame.Rect/Vector2 sin abrir ventana, como test_roles.py.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.dungeon.arena_jefe import ArenaJefe  # noqa: E402
from src.entities.enemy import Enemigo  # noqa: E402
from src.entities.tipos_enemigo import TipoEnemigo  # noqa: E402


def jugador_en(x, y):
    rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
    rect.center = (x, y)
    return SimpleNamespace(rect=rect, posicion=pygame.Vector2(x, y), vivo=True,
                           vida=5, vida_maxima=5,
                           invulnerabilidad=SimpleNamespace(reiniciar=lambda: None),
                           recibir_dano=lambda *a, **k: None)


def test_por_defecto_tiene_agro_permanente():
    assert Enemigo(0, 0).agro_permanente


def test_con_agro_permanente_persigue_y_dispara_a_cualquier_distancia():
    enemigo = Enemigo(40, 140)
    jugador = jugador_en(760, 570)  # esquina opuesta de la arena, muy fuera de rango
    assert pygame.Vector2(enemigo.rect.center).distance_to(jugador.rect.center) > assets.RANGO_DISPARO_ENEMIGO
    proyectiles = []
    distancia_antes = enemigo.posicion.distance_to(jugador.rect.center)
    enemigo.actualizar(0.5, jugador, proyectiles)
    assert enemigo.posicion.distance_to(jugador.rect.center) < distancia_antes
    assert len(proyectiles) == 1


def test_sin_agro_permanente_usa_el_rango_y_se_queda_quieto():
    enemigo = Enemigo(40, 140, agro_permanente=False)
    jugador = jugador_en(760, 570)
    proyectiles = []
    posicion = pygame.Vector2(enemigo.posicion)
    enemigo.actualizar(0.5, jugador, proyectiles)
    assert enemigo.posicion == posicion
    assert proyectiles == []


def test_subditos_del_jefe_actuan_desde_lejos():
    """Los súbditos alternan Perseguidor y Tirador (agro_permanente):
    ambos se acercan desde lejos y el tirador dispara tras su telegrafía."""
    jugador = jugador_en(0, 0)
    arena = ArenaJefe(ColapsoElectoral(), [jugador])
    # Jugador en la esquina inferior izquierda, lejos del jefe (arriba al centro).
    jugador.rect.center = (arena.rect.left + 30, arena.rect.bottom - 30)
    jugador.posicion.update(jugador.rect.center)
    arena._invocar(2)
    assert [s.tipo for s in arena.subditos] == [TipoEnemigo.PERSEGUIDOR, TipoEnemigo.TIRADOR]
    for subdito in arena.subditos:
        assert subdito.agro_permanente
        assert pygame.Vector2(subdito.rect.center).distance_to(jugador.rect.center) > assets.RANGO_DISPARO_ENEMIGO
    distancias = [s.posicion.distance_to(jugador.rect.center) for s in arena.subditos]
    proyectiles = []
    for _ in range(30):  # medio segundo a 60 FPS
        for subdito in arena.subditos:
            subdito.actualizar(1 / 60, jugador, proyectiles)
    for subdito, antes in zip(arena.subditos, distancias):
        assert subdito.posicion.distance_to(jugador.rect.center) < antes
    assert len(proyectiles) >= 1  # solo el tirador dispara (su variante puede lanzar un abanico)
