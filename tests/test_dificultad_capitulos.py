"""Capítulos del más fácil al más difícil y vida de los mobs según la
toxicidad (vida_por_toxicidad / reforzar_con_toxicidad)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    REPORTES_POR_ZONA, STATS_TIPO_ENEMIGO, VIDA_JEFE, ZONA_COLEGIO, ZONA_EMPRESA_MEDIOS, ZONA_HOSPITAL,
)
from src.dungeon.clasificador_toxicidad import vida_por_toxicidad  # noqa: E402
from src.story.contenido import cargar  # noqa: E402


@pytest.fixture(autouse=True)
def _ventana():
    pygame.init()
    pygame.display.set_mode((1280, 720))


def test_la_toxicidad_sube_con_el_numero_de_capitulo():
    from src.dungeon.partida import Partida

    partida = Partida()
    capitulos = cargar()["capitulos"]
    orden = sorted(capitulos, key=lambda zona: capitulos[zona]["numero"])
    assert orden == ["Colegio", "Hospital", "Empresa de Medios", "Alcaldía"]  # la historia no cambió
    niveles = [partida.toxicidad(zona) for zona in orden]
    assert niveles == sorted(niveles) and len(set(niveles)) == len(niveles)
    assert niveles == [pytest.approx(15.0), pytest.approx(50.0), pytest.approx(85.0), 100.0]


def test_solo_se_intercambiaron_los_reportes():
    # Los mismos reportes de siempre: el Hospital igual y Colegio/Medios cambiados de lugar.
    assert [r["gravedad"] for r in REPORTES_POR_ZONA[ZONA_HOSPITAL]] == [2, 4, 3, 3]
    assert [r["gravedad"] for r in REPORTES_POR_ZONA[ZONA_COLEGIO]] == [1, 2, 1, 2, 2]
    assert [r["gravedad"] for r in REPORTES_POR_ZONA[ZONA_EMPRESA_MEDIOS]] == [4, 5, 5, 3, 5]


@pytest.mark.parametrize("base, esperado", [(2, [3, 4, 5, 5]), (3, [5, 6, 7, 8]), (5, [8, 10, 12, 13])])
def test_tabla_de_vida(base, esperado):
    assert [vida_por_toxicidad(base, t) for t in (15, 50, 85, 100)] == esperado


def test_la_vida_crece_con_la_toxicidad_y_nunca_baja():
    for base in (2, 3, 4, 5, 6):
        anterior = base
        for toxicidad in range(0, 101, 5):
            vida = vida_por_toxicidad(base, toxicidad)
            assert anterior <= vida
            anterior = vida
        assert vida_por_toxicidad(base, -50) == vida_por_toxicidad(base, 0) >= base
        assert vida_por_toxicidad(base, 500) == vida_por_toxicidad(base, 100)


def _enemigos_de(zona, semilla=4):
    from src.dungeon.mazmorra import Mazmorra
    from src.dungeon.mazmorra_jugable import MazmorraJugable
    from src.entities.player import Ciudadano

    mazmorra = MazmorraJugable(Mazmorra(REPORTES_POR_ZONA[zona], zona, semilla=semilla))
    mazmorra.colocar_en_entrada([Ciudadano(0, 0)])
    m = mazmorra.mazmorra
    resultado = []
    for id_cuarto in [c for c in m.toxicidad if c in mazmorra._distancia_entrada]:
        m.entrar(id_cuarto)
        mazmorra._crear_cuarto_si_falta(id_cuarto)
        cuarto = mazmorra.cuartos[id_cuarto]
        for enemigo in cuarto.enemigos:
            resultado.append((enemigo, cuarto.nivel_toxicidad))
    random.seed()
    return resultado


def test_los_mobs_de_cada_cuarto_traen_la_vida_de_su_toxicidad():
    promedios = []
    for zona in (ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS):
        enemigos = _enemigos_de(zona)
        assert enemigos
        for enemigo, toxicidad in enemigos:
            base = enemigo.variante.stats.vida if enemigo.variante else STATS_TIPO_ENEMIGO[enemigo.tipo.value].vida
            assert enemigo.vida == enemigo.vida_maxima == vida_por_toxicidad(base, toxicidad)
            assert enemigo.vida > base
        promedios.append(sum(e.vida for e, _ in enemigos) / len(enemigos))
    assert promedios == sorted(promedios)  # capítulo 1 < 2 < 3


def test_la_velocidad_y_la_cantidad_salen_igual_que_antes():
    from src.dungeon.clasificador_toxicidad import nivel_a_dificultad
    from src.dungeon.cuarto import Cuarto

    cuarto = Cuarto(nombre_zona="Hospital", direcciones_puertas=("N", "S"), nivel_toxicidad=50.0,
                    es_final=False, rng=random.Random(2), semilla_visual=2)
    assert cuarto.dificultad == nivel_a_dificultad(50.0)


def test_el_enemigo_suelto_y_el_jefe_no_cambian():
    from src.core.colapso import ColapsoElectoral
    from src.dungeon.arena_jefe import ArenaJefe
    from src.entities.enemigos import crear_enemigo
    from src.entities.player import Ciudadano
    from src.entities.tipos_enemigo import TipoEnemigo

    suelto = crear_enemigo(TipoEnemigo.PERSEGUIDOR, 10, 10)
    assert suelto.vida == STATS_TIPO_ENEMIGO["perseguidor"].vida  # fuera de un cuarto: la vida de su tipo

    arena = ArenaJefe(ColapsoElectoral(), [Ciudadano(640, 600)])
    assert arena.jefe.vida_maxima == VIDA_JEFE
    arena._invocar(2)
    assert arena.subditos
    for subdito in arena.subditos:
        base = subdito.variante.stats.vida if subdito.variante else STATS_TIPO_ENEMIGO[subdito.tipo.value].vida
        assert subdito.vida == subdito.vida_maxima == vida_por_toxicidad(base, 100)
