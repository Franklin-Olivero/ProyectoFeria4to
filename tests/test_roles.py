"""Tests de los 4 roles jugables y de los efectos de sus ataques.

Usan pygame.Rect/Vector2, que no necesitan ventana ni pygame.init().
Los enemigos son Enemigo reales (su behavior tree no corre aquí salvo
en los tests de aggro forzado).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    BUFF_KILL_DURACION,
    DANIO_BASE,
    STATS_POR_ROL,
    VELOCIDAD_BASE,
    VIDA_BASE,
)
from src.core.equipo import registrar_kill_equipo  # noqa: E402
from src.entities.candidato import Candidato, OndaExpansiva, ProyectilRebotante  # noqa: E402
from src.entities.enemy import Enemigo  # noqa: E402
from src.entities.influencer import Influencer, ProyectilEmpuje  # noqa: E402
from src.entities.periodista import Periodista, RayoPerforante  # noqa: E402
from src.entities.player import Ciudadano, JugadorBase  # noqa: E402
from src.entities.projectile import Proyectil  # noqa: E402

ROLES = [Ciudadano, Influencer, Periodista, Candidato]
LIMITES = pygame.Rect(0, 0, 500, 400)
DANIO = 1  # daño fijo para probar los efectos sin depender del balance


def cargar_completo(jugador):
    for _ in range(jugador.carga_maxima):
        jugador.registrar_kill()


# ----------------------------------------------------------------------
# Comunes a los 4 roles (patrón de tests de Ciudadano)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("clase", ROLES)
def test_todos_heredan_de_jugador_base(clase):
    assert issubclass(clase, JugadorBase)


@pytest.mark.parametrize("clase", ROLES)
def test_usar_habilidad_sin_carga_no_actua(clase):
    jugador = clase(250, 200)
    enemigo = Enemigo(250, 100)
    salida = []
    for _ in range(STATS_POR_ROL[clase.rol].carga_maxima - 1):
        jugador.registrar_kill()
    assert jugador.usar_habilidad([enemigo], salida) is False
    assert jugador.carga_habilidad == STATS_POR_ROL[clase.rol].carga_maxima - 1
    assert salida == []
    assert enemigo.objetivo_forzado is None


@pytest.mark.parametrize("clase", ROLES)
def test_usar_habilidad_con_carga_resetea(clase):
    jugador = clase(250, 200)
    cargar_completo(jugador)
    assert jugador.usar_habilidad([], []) is True
    assert jugador.carga_habilidad == 0


@pytest.mark.parametrize("clase", ROLES)
def test_ataque_basico_devuelve_lista_no_vacia(clase):
    assert len(clase(250, 200).ataque_basico()) >= 1


# ----------------------------------------------------------------------
# Influencer
# ----------------------------------------------------------------------


def test_influencer_ataque_es_proyectil_ancho_de_empuje():
    (proyectil,) = Influencer(250, 200).ataque_basico()
    assert isinstance(proyectil, ProyectilEmpuje)
    assert proyectil.rect.width > assets.TAMANIO_PROYECTIL


def test_proyectil_empuje_daña_y_empuja_en_su_direccion():
    enemigo = Enemigo(100, 100)
    proyectil = ProyectilEmpuje((100, 130), (0, -1), DANIO)
    proyectil.al_impactar(enemigo)
    assert enemigo.vida == assets.VIDA_ENEMIGO - DANIO
    assert enemigo.rect.centery == 100 - assets.IMPULSO_EMPUJE_INFLUENCER
    assert not proyectil.vivo


def test_live_stream_fuerza_aggro_de_enemigos_vivos():
    influencer = Influencer(250, 200)
    vivo, muerto = Enemigo(50, 50), Enemigo(60, 60)
    muerto.vida = 0
    cargar_completo(influencer)
    influencer.usar_habilidad([vivo, muerto])
    assert vivo.objetivo_forzado is influencer
    assert vivo.tiempo_objetivo_forzado == assets.DURACION_LIVE_STREAM
    assert muerto.objetivo_forzado is None


def test_aggro_forzado_persigue_fuera_de_rango_y_expira():
    influencer = Influencer(0, 0)
    # Sin agresividad absoluta, para probar el rango de detección.
    enemigo = Enemigo(2000, 0, agro_permanente=False)  # muy fuera de RANGO_DISPARO_ENEMIGO
    enemigo.forzar_objetivo(influencer, 1.0)
    enemigo.actualizar(0.5, influencer, [])
    assert enemigo.posicion.x < 2000  # se acercó pese a estar lejos
    enemigo.actualizar(0.6, influencer, [])
    assert enemigo.objetivo_forzado is None
    x_antes = enemigo.posicion.x
    enemigo.actualizar(0.5, influencer, [])
    assert enemigo.posicion.x == x_antes  # sin aggro y fuera de rango: quieto


# ----------------------------------------------------------------------
# Periodista
# ----------------------------------------------------------------------


def test_periodista_ataque_es_rayo_perforante():
    (rayo,) = Periodista(250, 200).ataque_basico()
    assert isinstance(rayo, RayoPerforante)
    assert not rayo.quita_escudo


def test_rayo_perfora_y_daña_una_vez_a_cada_enemigo():
    rayo = RayoPerforante((0, 0), (1, 0), DANIO)
    a, b = Enemigo(100, 0), Enemigo(200, 0)
    rayo.al_impactar(a)
    rayo.al_impactar(a)  # mismo enemigo en el frame siguiente
    rayo.al_impactar(b)
    assert rayo.vivo
    assert a.vida == assets.VIDA_ENEMIGO - DANIO
    assert b.vida == assets.VIDA_ENEMIGO - DANIO


def test_escudo_anonimato_bloquea_daño_normal():
    enemigo = Enemigo(0, 0)
    enemigo.escudo_anonimato = True
    Proyectil((0, 0), (1, 0), 0, 1, (0, 0, 0)).al_impactar(enemigo)
    assert enemigo.vida == assets.VIDA_ENEMIGO


def test_fact_checking_dispara_rayo_que_quita_escudo():
    periodista = Periodista(250, 200)
    cargar_completo(periodista)
    salida = []
    periodista.usar_habilidad([], salida)
    (rayo,) = salida
    assert isinstance(rayo, RayoPerforante) and rayo.quita_escudo

    enemigo = Enemigo(0, 0)
    enemigo.escudo_anonimato = True
    rayo.al_impactar(enemigo)
    assert not enemigo.escudo_anonimato
    assert enemigo.vida == pytest.approx(assets.VIDA_ENEMIGO - periodista.danio)


# ----------------------------------------------------------------------
# Candidato
# ----------------------------------------------------------------------


def test_candidato_ataque_es_onda_centrada_en_el_jugador():
    (onda,) = Candidato(250, 200).ataque_basico()
    assert isinstance(onda, OndaExpansiva)
    assert onda.centro == pygame.Vector2(250, 200)


def test_onda_crece_daña_en_area_una_vez_y_desaparece():
    onda = OndaExpansiva((250, 200), DANIO)
    cerca = Enemigo(250 + assets.RADIO_MAXIMO_ONDA - 10, 200)
    lejos = Enemigo(250 + assets.RADIO_MAXIMO_ONDA + 100, 200)
    assert not onda.colisiona_con(cerca.rect)  # radio 0 al nacer
    onda.actualizar(assets.DURACION_ONDA * 0.99, LIMITES)
    assert onda.colisiona_con(cerca.rect)
    assert not onda.colisiona_con(lejos.rect)
    onda.al_impactar(cerca)
    onda.al_impactar(cerca)
    assert cerca.vida == assets.VIDA_ENEMIGO - DANIO
    onda.actualizar(assets.DURACION_ONDA, LIMITES)
    assert not onda.vivo


def test_debate_rebotante_dispara_proyectiles_rebotantes():
    candidato = Candidato(250, 200)
    cargar_completo(candidato)
    salida = []
    candidato.usar_habilidad([], salida)
    assert len(salida) == len(assets.ANGULOS_DEBATE_REBOTANTE)
    assert all(isinstance(p, ProyectilRebotante) for p in salida)


def test_rebotante_invierte_x_al_tocar_borde_y_sigue_vivo():
    proyectil = ProyectilRebotante((LIMITES.right - 5, 200), (1, 0), DANIO)
    proyectil.actualizar(0.05, LIMITES)
    assert proyectil.direccion.x < 0
    assert proyectil.rebotes == 1
    assert proyectil.vivo
    assert LIMITES.contains(proyectil.rect)


def test_rebotante_muere_al_superar_maximo_de_rebotes():
    proyectil = ProyectilRebotante((LIMITES.centerx, LIMITES.top + 5), (0, -1), DANIO)
    proyectil.rebotes = assets.MAXIMO_REBOTES
    proyectil.actualizar(0.05, LIMITES)
    assert not proyectil.vivo


def test_rebotante_muere_al_agotar_tiempo_de_vida():
    proyectil = ProyectilRebotante(LIMITES.center, (1, 0), DANIO)
    proyectil.tiempo_vida = 0.01
    proyectil.actualizar(0.02, LIMITES)
    assert not proyectil.vivo


# ----------------------------------------------------------------------
# Stats del balance aplicadas a cada rol + disparo sostenido
# ----------------------------------------------------------------------


@pytest.mark.parametrize("clase", ROLES)
def test_rol_toma_sus_stats_de_balance(clase):
    stats = STATS_POR_ROL[clase.rol]
    jugador = clase(250, 200)
    assert jugador.velocidad == pytest.approx(VELOCIDAD_BASE * stats.velocidad_mult)
    assert jugador.vida == pytest.approx(VIDA_BASE * stats.vida_mult)
    assert jugador.danio == pytest.approx(DANIO_BASE * stats.danio_mult)
    assert jugador.carga_maxima == stats.carga_maxima
    for proyectil in jugador.ataque_basico():
        assert proyectil.danio == pytest.approx(jugador.danio)


@pytest.mark.parametrize("clase", ROLES)
def test_disparo_sostenido_respeta_la_cadencia(clase):
    """Mantener disparo 3 s a 60 FPS da ~cadencia*3 volleys (+1 del primero)."""
    jugador = clase(250, 200)
    volleys_por_ataque = len(jugador.ataque_basico())
    total = sum(len(jugador.actualizar_disparo(1 / 60, True)) for _ in range(180))
    esperados = int(3 * jugador.stats.cadencia) + 1
    assert total // volleys_por_ataque in (esperados - 1, esperados)


def test_disparo_independiente_del_framerate():
    a, b = Influencer(0, 0), Influencer(0, 0)
    disparos_30 = sum(len(a.actualizar_disparo(1 / 30, True)) for _ in range(60))
    disparos_144 = sum(len(b.actualizar_disparo(1 / 144, True)) for _ in range(288))
    assert abs(disparos_30 - disparos_144) <= 1


def test_sin_disparar_no_se_acumulan_volleys():
    jugador = Influencer(0, 0)
    for _ in range(300):
        assert jugador.actualizar_disparo(1 / 60, False) == []
    assert len(jugador.actualizar_disparo(1 / 60, True)) == 1


def test_kill_propia_activa_buff_y_expira():
    jugador = Candidato(0, 0)
    base = jugador.intervalo_disparo()
    jugador.registrar_kill()
    assert jugador.intervalo_disparo() < base
    jugador.actualizar_disparo(BUFF_KILL_DURACION + 0.01, False)
    assert jugador.intervalo_disparo() == base


def test_carga_compartida_real_no_pasa_del_maximo_del_rol():
    asesino, aliado = Periodista(0, 0), Ciudadano(0, 0)
    for _ in range(200):
        registrar_kill_equipo(asesino, [asesino, aliado])
    assert aliado.carga_habilidad == aliado.carga_maxima
    assert not aliado.buff_kill_activo  # el buff es solo para la kill propia


# ----------------------------------------------------------------------
# Roles contra el escudo del jefe final (rayos reales, con pygame)
# ----------------------------------------------------------------------


def _jefe_con_escudo():
    import random

    from src.entities.jefe import Jefe

    jefe = Jefe(400, 240, (20, 120, 780, 590), random.Random(0))
    jefe.recibir_dano(jefe.vida_maxima * 0.4)  # entra a fase 2 -> escudo
    assert jefe.escudo_anonimato
    return jefe


def test_fact_checking_real_rompe_escudo_del_jefe_de_golpe():
    jefe = _jefe_con_escudo()
    vida = jefe.vida
    RayoPerforante((0, 0), (1, 0), DANIO, quita_escudo=True).al_impactar(jefe)
    assert not jefe.escudo_anonimato
    assert jefe.vida == vida - DANIO  # el mismo impacto ya daña la vida


def test_otros_roles_solo_restan_un_impacto_al_escudo():
    from src.core.balance import ESCUDO_VIDA

    jefe = _jefe_con_escudo()
    vida = jefe.vida
    RayoPerforante((0, 0), (1, 0), 99).al_impactar(jefe)
    OndaExpansiva((0, 0), 99).al_impactar(jefe)
    ProyectilEmpuje((0, 0), (1, 0), 99).al_impactar(jefe)
    assert jefe.vida_escudo == ESCUDO_VIDA - 3
    assert jefe.vida == vida


# ----------------------------------------------------------------------
# Invulnerabilidad en los jugadores reales (los 4 roles)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("clase", ROLES)
def test_rol_tiene_invulnerabilidad_tras_un_golpe(clase):
    from src.core.balance import INVULNERABILIDAD_DURACION

    jugador = clase(0, 0)
    vida = jugador.vida
    jugador.recibir_dano(1)
    jugador.recibir_dano(1)  # dentro de la ventana: no resta
    assert jugador.vida == pytest.approx(vida - 1)
    jugador.actualizar_invulnerabilidad(INVULNERABILIDAD_DURACION)
    jugador.recibir_dano(1)
    assert jugador.vida == pytest.approx(vida - 2)
