"""Tipos de enemigo y gracia de entrada con las clases reales.

Usan pygame.Rect/Vector2 sin abrir ventana, como test_roles.py y
test_agro.py (la lógica pura de cada pieza tiene sus propios tests:
test_nodos_combate.py, test_tipos_enemigo.py, test_spawn.py).
"""

import os
import random
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

import Main  # noqa: E402
from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    CADENCIA_TIRADOR_S,
    COOLDOWN_CONTACTO_PERSEGUIDOR,
    MAX_CURAS_POR_ALIADO,
    PANICO_CURANDERO_S,
    REPORTES_POR_ZONA,
    TELEGRAFIA_TIRADOR_S,
    ZONA_COLEGIO,
)
from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.dungeon.arena_jefe import ArenaJefe  # noqa: E402
from src.dungeon.cuarto import FASE_COMBATE, FASE_LIMPIO, Cuarto  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.mazmorra_jugable import MazmorraJugable  # noqa: E402
from src.entities.enemigos import Curandero, Perseguidor, Tirador, crear_enemigo  # noqa: E402
from src.entities.enemy import Enemigo  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.entities.projectile import Proyectil  # noqa: E402
from src.entities.tipos_enemigo import TipoEnemigo  # noqa: E402

DT = 1 / 60


def jugador_en(x, y):
    """Jugador falso que cuenta los golpes recibidos."""
    rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
    rect.center = (x, y)
    golpes = []
    return SimpleNamespace(
        rect=rect, posicion=pygame.Vector2(x, y), vivo=True, vida=5, vida_maxima=5, golpes=golpes,
        invulnerabilidad=SimpleNamespace(reiniciar=lambda: None),
        recibir_dano=lambda danio, **k: golpes.append(danio),
    )


def correr(enemigo, jugador, segundos, proyectiles=None, aliados=None):
    proyectiles = [] if proyectiles is None else proyectiles
    if aliados is not None:
        enemigo.aliados = aliados
    for _ in range(round(segundos / DT)):
        enemigo.actualizar(DT, jugador, proyectiles)
    return proyectiles


def distancia(a, b):
    return pygame.Vector2(a.rect.center).distance_to(b.rect.center)


# ----------------------------------------------------------------------
# Gracia de entrada
# ----------------------------------------------------------------------

@pytest.mark.parametrize("clase", [Enemigo, Perseguidor, Tirador, Curandero])
def test_congelado_queda_quieto_aunque_tenga_agro_permanente(clase):
    enemigo = clase(300, 300)
    assert enemigo.agro_permanente
    herido = Perseguidor(320, 300)
    herido.vida = 1
    enemigo.congelado = True
    jugador = jugador_en(310, 300)  # pegado: le podría pegar
    posicion = pygame.Vector2(enemigo.posicion)
    proyectiles = correr(enemigo, jugador, 2.0, aliados=[enemigo, herido])
    assert enemigo.posicion == posicion
    assert proyectiles == [] and jugador.golpes == []
    assert herido.vida == 1
    assert enemigo.nodo_activo == ("Selector", "Congelado (gracia)")


def test_jugador_sin_disparo_ni_habilidad_durante_la_gracia():
    jugador = Ciudadano(0, 0)
    jugador.sumar_carga(jugador.carga_maxima)
    jugador.armas_bloqueadas = True
    assert jugador.actualizar_disparo(0.5, True) == []
    assert not jugador.puede_usar_habilidad()
    assert jugador.habilidad_cargada()
    assert jugador.usar_habilidad() is False
    assert jugador.carga_habilidad == jugador.carga_maxima
    jugador.armas_bloqueadas = False
    assert len(jugador.actualizar_disparo(0.5, True)) > 0
    assert jugador.usar_habilidad() is True


def mazmorra_alta(semilla=1):
    return MazmorraJugable(Mazmorra(REPORTES_POR_ZONA[ZONA_COLEGIO], ZONA_COLEGIO, semilla=semilla))


def cruzar_a_un_vecino(mj, jugador):
    m = mj.mazmorra
    direccion, _ = next((d, v) for d, v in m.puertas(m.actual).items() if m.puede_entrar(v))
    jugador.rect.center = mj.cuarto.puertas[direccion].rect.center
    jugador.posicion.update(jugador.rect.center)
    proyectiles = [Proyectil((0, 0), (1, 0), 10, 1, (0, 0, 0))]
    mj.actualizar(DT, jugador, proyectiles)
    assert mj.cambio_de_cuarto
    assert proyectiles == []  # los proyectiles hostiles en vuelo se limpian
    return proyectiles


def test_gracia_al_empezar_y_en_cada_cambio_de_cuarto():
    mj = mazmorra_alta()
    jugador = jugador_en(0, 0)
    mj.colocar_en_entrada(jugador)
    assert mj.gracia.activa and mj.gracia.restante == 1.0
    for _ in range(70):
        mj.actualizar(DT, jugador, [])
    assert not mj.gracia.activa
    cruzar_a_un_vecino(mj, jugador)
    assert mj.gracia.restante == pytest.approx(1.0)
    mj.actualizar(DT, jugador, [])
    assert mj.cuarto.congelado
    assert mj.cuarto.enemigos and all(e.congelado for e in mj.cuarto.enemigos)


def test_sin_dano_durante_la_gracia_y_con_dano_despues():
    mj = mazmorra_alta()
    jugador = jugador_en(0, 0)
    mj.colocar_en_entrada(jugador)
    cruzar_a_un_vecino(mj, jugador)
    # El peor caso: el jugador pegado a un perseguidor recién aparecido.
    perseguidor = next(e for e in mj.cuarto.enemigos if e.tipo == TipoEnemigo.PERSEGUIDOR)
    jugador.rect.center = perseguidor.rect.center
    jugador.posicion.update(jugador.rect.center)
    proyectiles = []
    for _ in range(55):  # < 1 s
        mj.actualizar(DT, jugador, proyectiles)
        jugador.rect.center = perseguidor.rect.center
    assert mj.gracia.activa
    assert jugador.golpes == [] and proyectiles == []
    for _ in range(20):
        mj.actualizar(DT, jugador, proyectiles)
        jugador.rect.center = perseguidor.rect.center
    assert not mj.gracia.activa and jugador.golpes


def test_gracia_en_la_arena_del_jefe():
    jugador = jugador_en(0, 0)
    arena = ArenaJefe(ColapsoElectoral(), jugador)
    arena._invocar(2)
    tiempo = arena.mazmorra.tiempo_restante
    proyectiles = []
    for _ in range(55):
        arena.actualizar(DT, jugador, proyectiles)
    assert arena.gracia.activa
    assert proyectiles == [] and arena.mazmorra.tiempo_restante == tiempo
    assert all(s.congelado for s in arena.subditos)
    for _ in range(200):
        arena.actualizar(DT, jugador, proyectiles)
    assert proyectiles and arena.mazmorra.tiempo_restante < tiempo


# ----------------------------------------------------------------------
# Comportamiento de cada tipo
# ----------------------------------------------------------------------

def test_perseguidor_se_acerca_y_golpea_por_contacto_con_cooldown():
    perseguidor = Perseguidor(100, 300)
    jugador = jugador_en(500, 300)
    antes = distancia(perseguidor, jugador)
    proyectiles = correr(perseguidor, jugador, 0.5)
    assert distancia(perseguidor, jugador) < antes
    assert proyectiles == [] and jugador.golpes == []  # no dispara
    jugador.rect.center = perseguidor.rect.center
    correr(perseguidor, jugador, COOLDOWN_CONTACTO_PERSEGUIDOR * 2 + DT * 2)
    assert len(jugador.golpes) == 3  # t = 0, 0.8 y 1.6


def test_tirador_retrocede_si_el_jugador_esta_cerca_y_se_acerca_si_esta_lejos():
    tirador = Tirador(400, 300)
    cerca = jugador_en(500, 300)
    antes = distancia(tirador, cerca)
    correr(tirador, cerca, 0.3)
    assert distancia(tirador, cerca) > antes
    tirador = Tirador(100, 300)
    lejos = jugador_en(900, 300)
    antes = distancia(tirador, lejos)
    correr(tirador, lejos, 0.3)
    assert distancia(tirador, lejos) < antes


def test_tirador_dispara_con_telegrafia_y_cadencia():
    tirador = Tirador(100, 300)
    jugador = jugador_en(420, 300)
    proyectiles = []
    momentos, telegrafiaba = [], []
    for paso in range(round(5 / DT)):
        antes = tirador.telegrafia
        cantidad = len(proyectiles)
        tirador.actualizar(DT, jugador, proyectiles)
        if len(proyectiles) > cantidad:
            momentos.append(paso * DT)
            telegrafiaba.append(antes > 0)
    assert len(momentos) == 3 and all(telegrafiaba)
    assert momentos[0] == pytest.approx(TELEGRAFIA_TIRADOR_S, abs=2 * DT)
    for a, b in zip(momentos, momentos[1:]):
        # Tolerancia de 3 frames: el cooldown se mide en pasos de 1/60 s.
        assert b - a == pytest.approx(CADENCIA_TIRADOR_S + TELEGRAFIA_TIRADOR_S, abs=3 * DT)
    bala = proyectiles[0]
    assert bala.velocidad < assets.VELOCIDAD_PROYECTIL  # esquivable


def test_curandero_cura_a_un_herido_con_limite_por_aliado():
    curandero = Curandero(300, 300)
    herido = Perseguidor(350, 300)
    herido.vida = 0.5
    jugador = jugador_en(1000, 300)
    correr(curandero, jugador, 30, aliados=[curandero, herido])
    assert herido.curaciones_recibidas == MAX_CURAS_POR_ALIADO
    assert herido.vida == pytest.approx(0.5 + 2 * 0.34 * herido.vida_maxima)


def test_curandero_no_se_cura_a_si_mismo_ni_al_jefe():
    jugador = jugador_en(0, 0)
    arena = ArenaJefe(ColapsoElectoral(), jugador)
    jefe = arena.jefe
    jefe.vida = 10
    curandero = Curandero(jefe.x + 50, jefe.y)
    curandero.vida = 1
    aliado_sano = Perseguidor(jefe.x - 50, jefe.y)  # que no lo deje solo (sin pánico)
    jugador.rect.center = (jefe.x, jefe.y + 900)
    correr(curandero, jugador, 10, aliados=[curandero, jefe, aliado_sano])
    assert jefe.vida == 10 and curandero.vida == 1


def test_curandero_huye_si_el_jugador_se_acerca():
    curandero = Curandero(400, 300)
    aliado = Perseguidor(600, 300)
    jugador = jugador_en(480, 300)
    antes = distancia(curandero, jugador)
    correr(curandero, jugador, 0.3, aliados=[curandero, aliado])
    assert distancia(curandero, jugador) > antes


def test_curandero_entra_en_panico_tras_6_s_solo():
    curandero = Curandero(300, 300)
    jugador = jugador_en(900, 300)
    correr(curandero, jugador, PANICO_CURANDERO_S - 0.2, aliados=[curandero])
    assert not curandero.en_panico
    correr(curandero, jugador, 0.4, aliados=[curandero])
    assert curandero.en_panico
    assert curandero.velocidad == curandero.velocidad_base
    antes = distancia(curandero, jugador)
    correr(curandero, jugador, 0.5, aliados=[curandero])
    assert distancia(curandero, jugador) < antes  # ahora persigue


def test_compania_reinicia_el_conteo_de_panico():
    curandero = Curandero(300, 300)
    aliado = Perseguidor(100, 100)
    jugador = jugador_en(900, 300)
    correr(curandero, jugador, 4, aliados=[curandero])
    correr(curandero, jugador, 0.1, aliados=[curandero, aliado])
    correr(curandero, jugador, 4, aliados=[curandero])
    assert not curandero.en_panico


# ----------------------------------------------------------------------
# Cuarto y carga de habilidad
# ----------------------------------------------------------------------

def test_cuarto_no_se_libera_con_un_curandero_vivo():
    cuarto = Cuarto(dificultad={"cantidad_enemigos": 1, "multiplicador_velocidad": 1.0}, es_final=False)
    assert cuarto.fase == FASE_COMBATE
    cuarto.enemigos = [Curandero(600, 300)]  # el único que queda es un curandero
    cuarto._actualizar_estado_puertas()
    jugador = jugador_en(200, 300)
    for _ in range(60):
        cuarto.actualizar(DT, jugador, [])
    assert cuarto.fase == FASE_COMBATE
    assert all(p.bloqueada for p in cuarto.puertas.values())
    cuarto.enemigos[0].vida = 0
    cuarto.actualizar(DT, jugador, [])
    assert cuarto.fase == FASE_LIMPIO
    assert not any(p.bloqueada for p in cuarto.puertas.values())


def test_cuarto_usa_composicion_cuarto():
    from src.dungeon.clasificador_toxicidad import DIFICULTAD_ALTA

    cuarto = Cuarto(dificultad=dict(DIFICULTAD_ALTA), es_final=True, rng=random.Random(4))
    tipos = [e.tipo for e in cuarto.enemigos]
    assert tipos.count(TipoEnemigo.CURANDERO) >= 1 and tipos.count(TipoEnemigo.TIRADOR) >= 2
    assert len(tipos) == 5


@pytest.mark.parametrize("tipo", list(TipoEnemigo))
def test_matar_cualquier_tipo_carga_la_habilidad(tipo):
    jugador = Ciudadano(0, 0)
    enemigo = crear_enemigo(tipo, 200, 200)
    bala = Proyectil(enemigo.rect.center, (1, 0), 0, 99, assets.COLOR_PROYECTIL_JUGADOR)
    textos = SimpleNamespace(agregar=lambda *a, **k: None)
    Main._resolver_colisiones_contra_enemigos([bala], [enemigo], jugador, [jugador], textos)
    assert not enemigo.vivo
    assert jugador.carga_habilidad == 1
