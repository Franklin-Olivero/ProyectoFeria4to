"""Coberturas dentro del juego real: cuartos de cada zona, balas de los
roles y de los enemigos, la arena del jefe y el frame de combate de Main.

Con SDL dummy (necesitan las imágenes para conocer el tamaño de cada mueble).
"""

import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import PASO_MINIMO_COBERTURA  # noqa: E402
from src.core.colapso import ColapsoElectoral  # noqa: E402
from src.dungeon.arena_jefe import ArenaJefe  # noqa: E402
from src.dungeon.cuarto import Cuarto, punto_llegada  # noqa: E402
from src.entities.candidato import OndaExpansiva, ProyectilRebotante  # noqa: E402
from src.entities.periodista import RayoPerforante  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.entities.projectile import Proyectil  # noqa: E402
from src.ui.particulas import SistemaParticulas  # noqa: E402

ZONAS = ("Colegio", "Hospital", "Empresa de Medios")
PUERTAS = (("N", "E", "S", "W"), ("E", "W"), ("N", "S"), ("S",), ("N", "W"))


@pytest.fixture(scope="module", autouse=True)
def _ventana():
    pygame.init()
    pygame.display.set_mode((1280, 720))


def _cuarto(zona="Hospital", semilla=1, puertas=("N", "E", "S", "W"), final=False, toxicidad=70):
    return Cuarto(nombre_zona=zona, direcciones_puertas=puertas, nivel_toxicidad=toxicidad, es_final=final,
                  rng=random.Random(semilla), semilla_visual=semilla)


def _todos_los_cuartos():
    for zona in ZONAS:
        for semilla in range(9):  # la mazmorra usa el id del cuarto (0..8) como semilla visual
            for puertas in PUERTAS:
                for final in (False, True):
                    yield _cuarto(zona, semilla, puertas, final)


def test_todo_cuarto_tiene_coberturas_dentro_del_piso():
    for cuarto in _todos_los_cuartos():
        assert len(cuarto.coberturas.lista) >= 6, (cuarto.nombre_zona, cuarto.semilla_visual)
        for cobertura in cuarto.coberturas.lista:
            assert cuarto.rect.contains(pygame.Rect(cobertura.hitbox)), cobertura.nombre


def test_desde_cada_puerta_se_llega_a_todas_las_demas_al_centro_y_a_la_terminal():
    for cuarto in _todos_los_cuartos():
        nav = cuarto.coberturas.navegacion
        puntos = [punto_llegada(cuarto.rect, d) for d in cuarto.puertas] + [cuarto.rect.center]
        puntos.append((cuarto.rect.centerx, cuarto.rect.centery - 40))  # donde cae la evidencia
        if cuarto.es_final:
            puntos.append((cuarto.rect.right - assets.ZONA_LIBRE_TERMINAL[0] // 2, cuarto.rect.centery))
        lado = (assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
        for punto in puntos:
            assert cuarto.coberturas.punto_libre(punto, lado), (cuarto.nombre_zona, cuarto.semilla_visual, punto)
            assert nav.alcanzable(punto, puntos[0]), (cuarto.nombre_zona, cuarto.semilla_visual, punto)


def test_no_hay_rincones_donde_quepa_el_jugador_y_no_los_enemigos():
    """Todo hueco entre dos muebles enfrentados, o entre un mueble y un
    muro, es cerrado (< HUECO_CERRADO_COBERTURA: no entra el jugador) o
    ancho (>= PASO_MINIMO_COBERTURA: entra el enemigo más grande)."""
    from src.core.balance import HUECO_CERRADO_COBERTURA as cerrado
    from src.ui import plan_decor, temas_mazmorra

    assert assets.TAMANIO_JUGADOR > cerrado and assets.TAMANIO_ENEMIGO_MAXIMO <= PASO_MINIMO_COBERTURA
    for cuarto in _todos_los_cuartos():
        clave = (cuarto.nombre_zona, cuarto.semilla_visual, tuple(cuarto.puertas), cuarto.es_final)
        r = cuarto.rect
        piso = (r.left, r.top + temas_mazmorra.ALTO_CARA_MURO * temas_mazmorra.P, r.width,
                r.height - temas_mazmorra.ALTO_CARA_MURO * temas_mazmorra.P)
        bases = [c.hitbox for c in cuarto.coberturas.lista]
        for i, base in enumerate(bases):
            assert not plan_decor.hueco_al_muro(base, piso, cerrado, PASO_MINIMO_COBERTURA - 2), (clave, base)
            for otra in bases[i + 1:]:
                assert not plan_decor.hueco_a_medias(base, otra, cerrado, PASO_MINIMO_COBERTURA - 2), (clave, base, otra)


def test_ningun_enemigo_aparece_dentro_de_un_mueble_ni_encerrado():
    for cuarto in _todos_los_cuartos():
        for enemigo in cuarto.enemigos:
            assert cuarto.coberturas.punto_libre(enemigo.rect.center, enemigo.rect.size), enemigo.nombre
            assert cuarto.coberturas.navegacion.alcanzable(enemigo.rect.center, cuarto.rect.center)


def test_el_mismo_cuarto_da_las_mismas_coberturas():
    """El plan es determinista (zona + semilla + puertas): en red, el
    invitado arma la misma lista que el host y sus vidas calzan una a una."""
    a, b = _cuarto("Colegio", 4), _cuarto("Colegio", 4)
    assert [(c.nombre, c.rect) for c in a.coberturas.lista] == [(c.nombre, c.rect) for c in b.coberturas.lista]
    assert [c.rect for c in _cuarto("Colegio", 5).coberturas.lista] != [c.rect for c in a.coberturas.lista]


def test_sin_tema_no_hay_coberturas_y_el_cuarto_funciona_igual():
    cuarto = Cuarto(rng=random.Random(1))  # la zona de ejemplo no tiene escenario propio
    assert not cuarto.coberturas and cuarto.coberturas.solidas() == []
    cuarto.actualizar(0.016, [Ciudadano(*cuarto.rect.center)], [])
    cuarto.dibujar(pygame.display.get_surface())


# ----------------------------------------------------------------------
# Balas
# ----------------------------------------------------------------------

def _cobertura_de(cuarto):
    """Una cobertura del medio del cuarto (lejos de los muros): tiene paso por todos sus lados."""
    r = cuarto.rect.inflate(-2 * PASO_MINIMO_COBERTURA, -2 * PASO_MINIMO_COBERTURA)
    del_medio = [c for c in cuarto.coberturas.lista if r.contains(pygame.Rect(c.hitbox).inflate(80, 80))]
    return max(del_medio, key=lambda c: c.hitbox[2] * c.hitbox[3])


def test_las_balas_de_cualquiera_se_frenan_en_el_mueble():
    cuarto = _cuarto()
    cobertura = _cobertura_de(cuarto)
    centro = pygame.Rect(cobertura.hitbox).center
    for bala in (Proyectil(centro, (1, 0), 300, 1, (255, 255, 255)),  # enemigo o Ciudadano
                 RayoPerforante(centro, (1, 0), 1.6)):  # perfora enemigos, no muebles
        vida = cobertura.vida
        assert cuarto.coberturas.impactar(bala) is cobertura
        assert not bala.vivo and cobertura.vida == vida - bala.danio


def test_la_onda_del_candidato_dania_una_vez_cada_mueble_y_sigue():
    cuarto = _cuarto()
    cobertura = _cobertura_de(cuarto)
    onda = OndaExpansiva(pygame.Rect(cobertura.hitbox).center, 3.0)
    onda.radio = 10
    vida = cobertura.vida
    assert cuarto.coberturas.impactar(onda) is cobertura and onda.vivo
    assert cobertura.vida == vida - 3.0
    cuarto.coberturas.impactar(onda)  # el mismo frente no vuelve a dañarla
    assert cobertura.vida == vida - 3.0


def test_el_debate_rebotante_rebota_en_el_mueble():
    cuarto = _cuarto()
    cobertura = _cobertura_de(cuarto)
    x, y, ancho, alto = cobertura.hitbox
    bala = ProyectilRebotante((x - 2, y + alto // 2), (1, 0), 1)
    assert cuarto.coberturas.impactar(bala) is cobertura
    assert bala.vivo and bala.direccion.x < 0 and bala.rebotes == 1
    assert not bala.rect.colliderect(pygame.Rect(cobertura.hitbox))  # quedó fuera: no rebota dos veces


def test_frame_de_combate_el_jugador_no_atraviesa_y_el_mueble_lo_cubre():
    import Main
    from src.core.entrada import InputJugador

    cuarto = _cuarto()
    from src.dungeon.gracia_entrada import GraciaEntrada
    cuarto.gracia = GraciaEntrada()
    cuarto.enemigos.clear()
    cobertura = _cobertura_de(cuarto)
    x, y, ancho, alto = cobertura.hitbox
    jugador = Ciudadano(x - 60, y + alto // 2)
    derecha = InputJugador(movimiento=(1, 0), punto_apuntado=None, direccion_apuntado=None,
                           disparando=False, habilidad=False, dash=False)
    hostiles = [Proyectil((x + ancho + 40, y + alto // 2), (-1, 0), 400, 1, (255, 0, 0))]
    original = Main._leer_entrada
    Main._leer_entrada = lambda entrada, teclas, sacudida: derecha
    try:
        for _ in range(90):
            Main._frame_de_combate(1 / 60, [jugador], [None], cuarto, [[]], hostiles, _SinTextos(),
                                   SistemaParticulas())
    finally:
        Main._leer_entrada = original
    assert jugador.rect.right <= x  # se quedó pegado a la cara del mueble
    assert jugador.vida == jugador.vida_maxima and hostiles == []  # la bala murió en la cobertura
    assert cobertura.vida == cobertura.vida_maxima - 1


class _SinTextos:
    def agregar(self, *args, **kwargs):
        pass


def test_un_perseguidor_rodea_el_mueble_y_alcanza_al_jugador():
    cuarto = _cuarto("Empresa de Medios", 2)
    from src.entities.enemigos import Perseguidor
    cobertura = _cobertura_de(cuarto)
    x, y, ancho, alto = cobertura.hitbox
    jugador = Ciudadano(x + ancho + 40, y + alto // 2)  # escondido justo detrás del mueble
    enemigo = Perseguidor(x - 60, y + alto // 2)
    assert cuarto.coberturas.punto_libre(jugador.rect.center, jugador.rect.size)
    cuarto.enemigos[:] = [enemigo]
    for _ in range(60 * 12):
        cuarto.actualizar(1 / 60, [jugador], [])
        jugador.vida = jugador.vida_maxima
        assert cuarto.coberturas.punto_libre((enemigo.posicion.x, enemigo.posicion.y), enemigo.rect.size)
        if enemigo.rect.inflate(8, 8).colliderect(jugador.rect):
            break
    assert enemigo.rect.inflate(8, 8).colliderect(jugador.rect)


# ----------------------------------------------------------------------
# Arena del jefe
# ----------------------------------------------------------------------

def test_la_arena_tiene_coberturas_el_jefe_las_aplasta_y_vuelven_al_reiniciar():
    jugador = Ciudadano(0, 0)
    arena = ArenaJefe(ColapsoElectoral(), [jugador])
    assert len(arena.coberturas.lista) >= 8
    assert arena.coberturas.punto_libre(jugador.rect.center, jugador.rect.size)
    cobertura = arena.coberturas.lista[0]
    arena.jefe.rect.center = pygame.Rect(cobertura.hitbox).center
    arena.coberturas.aplastar(tuple(arena.jefe.rect))
    assert cobertura.rota
    arena.mazmorra.reinicio_pendiente = True
    arena.gracia.restante = 0
    arena.actualizar(0.016, [jugador], [])
    assert not any(c.rota for c in arena.coberturas.lista)
    arena.dibujar(pygame.display.get_surface())
    arena.dibujar_delante(pygame.display.get_surface(), [jugador.rect])


def test_los_muebles_se_dibujan_en_todas_sus_etapas():
    from src.dungeon.coberturas import ETAPA_ROTA
    from src.ui import cobertura_render

    cuarto = _cuarto("Colegio", 3)  # el aula: pupitres del pack escolar
    pantalla = pygame.display.get_surface()
    for cobertura in cuarto.coberturas.lista:
        tamanios = set()
        for etapa in range(ETAPA_ROTA + 1):
            imagen = cobertura_render.imagen(cuarto.tema, cobertura.nombre, etapa)
            assert imagen is not None, cobertura.nombre
            tamanios.add(imagen.get_size())
        assert tamanios == {(cobertura.rect[2], cobertura.rect[3])}  # romperse no cambia su lugar
    cuarto.coberturas.lista[0].recibir_impacto(1)
    cuarto.coberturas.lista[1].romper()
    cuarto.dibujar(pantalla)
    cuarto.dibujar_delante(pantalla, [pygame.Rect(cuarto.coberturas.lista[0].rect)])
