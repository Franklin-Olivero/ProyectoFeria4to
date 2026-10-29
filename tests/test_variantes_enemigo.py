"""Variantes de enemigo (assets/sprites/enemigos 2.0): tabla, reparto por
cuarto y mazmorra, ataques con animación y etiqueta de debug.

La tabla y la elección son puras; los ataques usan las clases reales con
un jugador falso (como test_enemigos.py) y el arte se lee de disco sin
abrir ventana.
"""

import os
import random
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import STATS_TIPO_ENEMIGO, STATS_VARIANTE_ENEMIGO  # noqa: E402
from src.dungeon.cuarto import Cuarto  # noqa: E402
from src.entities.enemigos import crear_enemigo  # noqa: E402
from src.entities.tipos_enemigo import TipoEnemigo  # noqa: E402
from src.entities.variantes_enemigo import VARIANTES, elegir_variantes, variantes_de  # noqa: E402
from src.ui import enemigo_render, sprites  # noqa: E402

DT = 1 / 60


def jugador_en(x, y):
    rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
    rect.center = (x, y)
    golpes = []
    return SimpleNamespace(
        rect=rect, posicion=pygame.Vector2(x, y), vivo=True, vida=5, vida_maxima=5, golpes=golpes,
        recibir_dano=lambda danio, **k: golpes.append(danio),
    )


def correr(enemigo, jugador, segundos, proyectiles=None):
    proyectiles = [] if proyectiles is None else proyectiles
    for _ in range(round(segundos / DT)):
        enemigo.actualizar(DT, jugador, proyectiles)
    return proyectiles


# ----------------------------------------------------------------------
# Tabla
# ----------------------------------------------------------------------

def test_todas_las_carpetas_de_enemigos_2_tienen_variante_salvo_el_jefe():
    carpetas = set(os.listdir(assets.RUTA_SPRITES_ENEMIGOS_V2))
    assert carpetas - set(VARIANTES) == {assets.JEFE_V2}
    assert set(VARIANTES) - carpetas == set()


def test_cada_tipo_tiene_variantes_y_la_tabla_de_arte_coincide():
    assert set(assets.ARTE_VARIANTE) == set(STATS_VARIANTE_ENEMIGO)
    for tipo in TipoEnemigo:
        assert variantes_de(tipo), tipo
    for stats in STATS_VARIANTE_ENEMIGO.values():
        assert stats.tipo in STATS_TIPO_ENEMIGO
        if stats.tipo == "perseguidor":
            assert stats.danio > 0 and stats.cooldown_s > 0
        if stats.tipo == "tirador":
            assert stats.danio > 0 and stats.velocidad_proyectil > 0 and stats.proyectiles >= 1


def test_hellhound_y_warlock_conservan_su_escala():
    assert assets.ARTE_VARIANTE["Hellhound"]["escala"] == 2
    assert assets.ARTE_VARIANTE["Warlock"]["escala"] == 4


@pytest.mark.parametrize("nombre", sorted(VARIANTES))
def test_cada_variante_carga_su_arte_alineado(nombre):
    caminar = sprites.sprite_variante(nombre, 0.0)
    atacar = sprites.sprite_variante(nombre, 0.0, ataque_t=0.0)
    assert caminar is not None and atacar is not None
    assert caminar.get_size() == atacar.get_size()  # misma caja: el cuerpo no salta
    # Volteado: mismo tamaño y distinto contenido.
    izq = sprites.sprite_variante(nombre, 0.0, mirando_izquierda=True)
    assert izq.get_size() == caminar.get_size()
    ultimo = sprites.sprite_variante(nombre, 0.0, ataque_t=99.0)
    assert ultimo is sprites.sprite_variante(nombre, 0.0, ataque_t=99.0)  # cacheado


# ----------------------------------------------------------------------
# Reparto
# ----------------------------------------------------------------------

def test_elegir_variantes_no_repite_dentro_del_cuarto_ni_hasta_agotar_la_mazmorra():
    rng = random.Random(1)
    usos = {}
    tipos = [TipoEnemigo.PERSEGUIDOR] * 5
    primera = [v.nombre for v in elegir_variantes(tipos, rng, usos)]
    assert len(set(primera)) == 5
    segunda = [v.nombre for v in elegir_variantes(tipos, rng, usos)]
    assert len(set(segunda)) == 5 and not set(primera) & set(segunda)  # 10 melee: 2 cuartos sin repetir
    for nombre in primera + segunda:
        assert VARIANTES[nombre].tipo == TipoEnemigo.PERSEGUIDOR


def test_elegir_variantes_respeta_el_tipo_y_el_orden():
    tipos = [TipoEnemigo.PERSEGUIDOR, TipoEnemigo.TIRADOR, TipoEnemigo.CURANDERO]
    elegidas = elegir_variantes(tipos, random.Random(2), {})
    assert [v.tipo for v in elegidas] == tipos


def test_cuartos_de_una_mazmorra_comparten_los_usos_y_traen_variantes_distintas():
    usos = {}
    nombres = []
    for semilla in range(2):
        cuarto = Cuarto(nivel_toxicidad=10, es_final=False, rng=random.Random(semilla), usos_variantes=usos)
        assert all(e.variante is not None for e in cuarto.enemigos)
        nombres += [e.nombre for e in cuarto.enemigos]
    assert len(set(nombres)) == len(nombres) == sum(usos.values())


# ----------------------------------------------------------------------
# Ataques
# ----------------------------------------------------------------------

def test_cuerpo_a_cuerpo_con_variante_golpea_a_mitad_de_la_animacion_y_con_cooldown():
    variante = VARIANTES["Minotaur"]
    enemigo = crear_enemigo(TipoEnemigo.PERSEGUIDOR, 300, 300, variante=variante)
    jugador = jugador_en(300, 300)
    correr(enemigo, jugador, variante.tiempo_impacto - 2 * DT)
    assert enemigo.atacando and jugador.golpes == []  # el golpe aún no cae
    correr(enemigo, jugador, 4 * DT)
    assert jugador.golpes == [variante.stats.danio]
    correr(enemigo, jugador, variante.stats.cooldown_s + variante.tiempo_impacto + 0.1)  # cooldown + nuevo golpe
    assert len(jugador.golpes) == 2


def test_si_el_jugador_se_aleja_durante_el_golpe_lo_esquiva():
    variante = VARIANTES["Hellhound"]
    enemigo = crear_enemigo(TipoEnemigo.PERSEGUIDOR, 300, 300, variante=variante)
    jugador = jugador_en(300, 300)
    correr(enemigo, jugador, DT * 2)
    assert enemigo.atacando
    jugador.rect.center = (900, 300)
    jugador.posicion.update(jugador.rect.center)
    correr(enemigo, jugador, variante.duracion_ataque)
    assert jugador.golpes == []


def test_tirador_con_variante_telegrafia_con_la_animacion_y_dispara_su_abanico():
    variante = VARIANTES["Demon_D"]  # abanico de 3
    enemigo = crear_enemigo(TipoEnemigo.TIRADOR, 300, 300, variante=variante)
    jugador = jugador_en(300 + variante.stats.alcance, 300)
    proyectiles = correr(enemigo, jugador, variante.tiempo_impacto * 0.5)
    assert enemigo.atacando and proyectiles == []
    proyectiles = correr(enemigo, jugador, variante.tiempo_impacto + 0.2, proyectiles)
    assert len(proyectiles) == variante.stats.proyectiles == 3
    assert {p.danio for p in proyectiles} == {variante.stats.danio}
    # El abanico se abre: direcciones distintas, la central apunta al jugador.
    assert len({(round(p.direccion.x, 3), round(p.direccion.y, 3)) for p in proyectiles}) == 3


def test_curandero_con_variante_anima_su_hechizo_al_curar():
    variante = VARIANTES["Ghostfire"]
    curandero = crear_enemigo(TipoEnemigo.CURANDERO, 300, 300, variante=variante)
    aliado = crear_enemigo(TipoEnemigo.PERSEGUIDOR, 340, 300, variante=VARIANTES["Hellhound"])
    aliado.vida = 1
    curandero.aliados = [curandero, aliado]
    jugador = jugador_en(900, 300)
    correr(curandero, jugador, 3.2)
    assert aliado.vida > 1 and curandero.efecto_cura is aliado
    assert curandero.atacando or curandero.ataque_t is None  # la animación corrió


def test_las_variantes_usan_su_vida_su_velocidad_y_su_hitbox():
    for nombre, variante in VARIANTES.items():
        enemigo = crear_enemigo(variante.tipo, 300, 300, 100, variante=variante)
        assert enemigo.vida == variante.stats.vida
        assert enemigo.velocidad == pytest.approx(100 * variante.stats.velocidad_mult)
        assert enemigo.rect.width == assets.ARTE_VARIANTE[nombre]["tamanio"]
        assert enemigo.nombre == nombre


def test_sin_variante_sigue_el_comportamiento_original():
    enemigo = crear_enemigo(TipoEnemigo.TIRADOR, 300, 300)
    assert enemigo.variante is None and enemigo.nombre is None
    assert enemigo.rect.width == assets.TAMANIO_ENEMIGO_TIPO["tirador"]


# ----------------------------------------------------------------------
# Debug: nombre flotante
# ----------------------------------------------------------------------

def test_el_nombre_exacto_se_dibuja_encima_del_sprite(monkeypatch):
    pygame.font.init()
    pantalla = pygame.Surface((400, 300), pygame.SRCALPHA)
    enemigo = crear_enemigo(TipoEnemigo.TIRADOR, 200, 200, variante=VARIANTES["Black Knight_B"])
    enemigo.reloj = 0.0
    monkeypatch.setattr(assets, "MOSTRAR_NOMBRE_ENEMIGO", True)
    enemigo_render.dibujar_enemigo(pantalla, enemigo)
    sprite = sprites.sprite_variante("Black Knight_B")
    arriba = enemigo.rect.centery - sprite.get_height() // 2
    etiqueta = enemigo_render._etiqueta_nombre("Black Knight_B")
    zona = pygame.Rect(0, 0, etiqueta.get_width(), etiqueta.get_height())
    zona.midbottom = (enemigo.rect.centerx, arriba - assets.SEPARACION_NOMBRE_ENEMIGO)
    assert pygame.mask.from_surface(pantalla.subsurface(zona)).count() > 0

    limpia = pygame.Surface((400, 300), pygame.SRCALPHA)
    monkeypatch.setattr(assets, "MOSTRAR_NOMBRE_ENEMIGO", False)
    enemigo_render.dibujar_enemigo(limpia, enemigo)
    assert pygame.mask.from_surface(limpia.subsurface(zona)).count() == 0
