"""Lobby Online con el estilo de ahora: la sala de espera como salón del hotel
Backrooms (Online/sala_hotel.py y sala_hotel_render.py), los vestidores con
HAIR / SHIRT / PANTS (recolorean el arte que ya existe) y los botones
REPORTAR y SABOTEAR a la izquierda (Online/disposicion_hud.py)."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.dungeon import compositor_interior  # noqa: E402
from src.ui import sprites, tinte_jugador  # noqa: E402
from Online import disposicion_hud, lobby, sala_hotel, sala_hotel_render  # noqa: E402
from Online.personalizacion import (  # noqa: E402
    HAIR, PANTS, PESTANAS, SHIRT, SHOES, Vestidor, color_de_opcion, etiqueta_opcion, opciones, texto_opcion,
)


@pytest.fixture(scope="module")
def pantalla():
    pygame.display.init()
    pygame.font.init()
    return pygame.display.set_mode((1280, 720))


# ----------------------------------------------------------------------
# La sala del hotel
# ----------------------------------------------------------------------

COMPOSICION = sala_hotel.cargar_composicion()
DISPOSICION = sala_hotel.disposicion(COMPOSICION)


def _r(rect):
    return pygame.Rect(rect)


def test_la_sala_tiene_recepcion_y_cuatro_vestidores_que_estorban():
    assert DISPOSICION.recepcion is not None and len(DISPOSICION.vestidores) == 4
    for rect in (DISPOSICION.recepcion, *DISPOSICION.vestidores):
        assert rect in DISPOSICION.obstaculos
    sala = _r(DISPOSICION.sala)
    assert sala.right <= 960  # a la derecha van los paneles de la sala
    assert sala.bottom <= 720 - assets.ALTO_BARRA_CONTROLES
    for rect in DISPOSICION.obstaculos:
        assert sala.contains(_r(rect))


def test_los_jugadores_aparecen_en_el_piso_sin_chocar_con_nada():
    piso = _r(DISPOSICION.piso)
    for x, y in DISPOSICION.apariciones:
        cuadro = pygame.Rect(x - 16, y - 16, 32, 32)
        assert piso.contains(cuadro)
        assert not any(cuadro.colliderect(_r(o)) for o in DISPOSICION.obstaculos)


def test_se_puede_llegar_a_la_recepcion_y_a_cada_vestidor():
    """Desde la aparición, caminando por el piso sin atravesar nada, hay un
    punto a menos del alcance de cada estación (BFS sobre una grilla de 8 px)."""
    piso = _r(DISPOSICION.piso)
    obstaculos = [_r(o) for o in DISPOSICION.obstaculos]
    paso = 8

    def libre(x, y):
        cuadro = pygame.Rect(x - 16, y - 16, 32, 32)
        return piso.contains(cuadro) and not any(cuadro.colliderect(o) for o in obstaculos)

    inicio = DISPOSICION.apariciones[0]
    vistos, cola = {inicio}, [inicio]
    while cola:
        x, y = cola.pop()
        for dx, dy in ((paso, 0), (-paso, 0), (0, paso), (0, -paso)):
            nuevo = (x + dx, y + dy)
            if nuevo not in vistos and libre(*nuevo):
                vistos.add(nuevo)
                cola.append(nuevo)
    for estacion, alcance in [(DISPOSICION.recepcion, 95)] + [(v, lobby.ALCANCE_VESTIDOR) for v in DISPOSICION.vestidores]:
        centro = _r(estacion).center
        assert any((x - centro[0]) ** 2 + (y - centro[1]) ** 2 < alcance ** 2 for x, y in vistos), estacion


def test_el_boton_de_inicio_queda_dentro_de_la_sala_y_libre():
    boton = lobby.RECT_BOTON_INICIO
    assert _r(DISPOSICION.sala).contains(boton)
    assert not any(boton.colliderect(_r(o)) for o in DISPOSICION.obstaculos)


def test_el_lobby_usa_la_disposicion_del_hotel():
    assert lobby.ESTACION_ROLES == _r(DISPOSICION.recepcion)
    assert [tuple(r) for r in lobby.CAJAS_VESTIDOR] == list(DISPOSICION.vestidores)
    assert lobby.SPAWNS == list(DISPOSICION.apariciones)


def test_todo_el_arte_que_usa_la_sala_ya_existe():
    """Sin assets nuevos: cada tile y cada prop de la sala está en el atlas del hotel."""
    atlas = json.load(open(os.path.join("assets", "backrooms", assets.GRADE_LOBBY, "atlas.json"), encoding="utf-8"))
    plantilla = sala_hotel.plantilla(COMPOSICION)
    assert plantilla is not None
    assert {str(t) for t in compositor_interior.tiles_usados(plantilla)} <= set(atlas["tiles"])
    for obj in COMPOSICION["objetos"]:
        assert (obj.get("estatico") or obj["nombre"]) in atlas["props"]
        if obj.get("apagado"):
            assert obj["apagado"] in atlas["props"]
    for luz in COMPOSICION["luces"]:
        assert luz["nombre"] in atlas["luces"]


@pytest.mark.parametrize("recepcion, vestidor", [(False, None), (True, None), (False, 0), (False, 3)])
def test_el_salon_se_dibuja_con_sus_carteles(pantalla, recepcion, vestidor):
    pantalla.fill((0, 0, 0))
    assert sala_hotel_render.dibujar_sala(pantalla, 1.0, recepcion, vestidor, COMPOSICION) is True
    sala = _r(DISPOSICION.sala)
    assert pantalla.get_at((sala.centerx, sala.top + 30))[:3] != (0, 0, 0)  # la pared del fondo


def test_sin_composicion_vuelve_la_sala_neon(pantalla):
    assert sala_hotel_render.dibujar_sala(pantalla, 1.0, False, None, None) is False
    lobby._dibujar_escenario_lobby(pantalla, 1.0, False, None)  # dibuja algo sin fallar


# ----------------------------------------------------------------------
# Los botones a la izquierda
# ----------------------------------------------------------------------

FEED = pygame.Rect(assets.RECT_FEED_CIVITAS)
MINIMAPA = pygame.Rect(1010, 70, 122, 140)


@pytest.mark.parametrize("escena, cantidad, detallado", [
    (Escena.CIUDAD, 2, False), (Escena.CIUDAD, 4, True), (Escena.MAZMORRA, 2, False), (Escena.MAZMORRA, 3, False),
    (Escena.MAZMORRA, 4, True), (Escena.JEFE, 2, False), (Escena.JEFE, 4, False), (Escena.DECISION, 2, False),
])
def test_los_botones_van_a_la_izquierda_sin_tapar_nada(escena, cantidad, detallado):
    reportar, sabotear = disposicion_hud.rects_botones(escena, cantidad, detallado)
    rects = [pygame.Rect(reportar)] + ([pygame.Rect(sabotear)] if sabotear else [])
    assert (sabotear is None) == (escena == Escena.DECISION)
    for rect in rects:
        assert rect.right <= 640 and pygame.Rect(0, 0, 1280, 720).contains(rect)  # mitad izquierda
        assert not rect.colliderect(FEED) and not rect.colliderect(MINIMAPA)
        if escena in (Escena.MAZMORRA, Escena.JEFE):
            for numero in range(cantidad):
                assert not rect.colliderect(pygame.Rect(assets.RECTS_PANEL_JUGADOR[numero])), (numero, rect)
            if detallado:
                assert not rect.colliderect(pygame.Rect(assets.RECT_PANEL_MISION_COMBATE))
        if escena == Escena.CIUDAD:
            assert not rect.colliderect(pygame.Rect(assets.RECT_PANEL_MISION_CIUDAD))
    if len(rects) == 2:
        assert not rects[0].colliderect(rects[1])


# ----------------------------------------------------------------------
# HAIR, SHIRT, PANTS y SHOES sobre el arte de Higgsfield
# ----------------------------------------------------------------------

PALETAS = ((HAIR, assets.TONOS_PELO), (SHIRT, assets.COLORES_ROPA), (PANTS, assets.COLORES_PANTALON),
           (SHOES, assets.COLORES_ZAPATOS))


def test_cada_pestana_de_color_tiene_nombre():
    assert PESTANAS[1:] == (HAIR, SHIRT, PANTS, SHOES)
    for pestana, paleta in PALETAS:
        valores = opciones(pestana)
        assert valores[0] is None and len(valores) == len(paleta) + 1 <= 10  # entra en 2 filas de 5
        assert etiqueta_opcion(pestana, None) == "AUTO" and color_de_opcion(pestana, None) is None
        for valor in valores[1:]:
            assert etiqueta_opcion(pestana, valor) and color_de_opcion(pestana, valor) == paleta[valor]
            assert ":" in texto_opcion(pestana, valor, "ciudadano")


def test_elegir_un_color_lo_equipa_y_viaja_por_red():
    vestidor = Vestidor(PREDETERMINADA, SHIRT)
    assert vestidor.elegir(2) is True
    assert vestidor.apariencia.ropa == 1
    vestidor.ir_a_pestana(PESTANAS.index(HAIR))
    vestidor.mover(1, 0)
    assert vestidor.apariencia.pelo == 0
    vestidor.ir_a_pestana(PESTANAS.index(SHOES))
    vestidor.elegir(5)
    assert vestidor.apariencia.zapatos == 4
    assert Apariencia.de_dict(json.loads(json.dumps(vestidor.apariencia.a_dict()))) == vestidor.apariencia


@pytest.mark.parametrize("datos", [{"pelo": 99}, {"ropa": -1}, {"pantalon": True}, {"pelo": "rubio"},
                                   {"zapatos": 9}, {}])
def test_un_color_roto_o_de_una_version_vieja_queda_en_auto(datos):
    apariencia = Apariencia.de_dict({"piel": 1, **datos})
    assert apariencia.piel == 1 and apariencia.pelo is None and apariencia.ropa is None
    assert apariencia.pantalon is None and apariencia.zapatos is None


def test_teñir_conserva_las_sombras():
    objetivo = (200, 40, 60)
    assert tinte_jugador.teñir((100, 100, 100), (100, 100, 100), objetivo) == objetivo
    sombra = tinte_jugador.teñir((50, 50, 50), (100, 100, 100), objetivo)
    assert all(s < o for s, o in zip(sombra, objetivo))


def _pixeles(superficie):
    return {superficie.get_at((x, y))[:3] for x in range(superficie.get_width()) for y in range(superficie.get_height())
            if superficie.get_at((x, y))[3] > 0}


@pytest.mark.parametrize("campo, paleta", [("pelo", assets.TONOS_PELO), ("ropa", assets.COLORES_ROPA),
                                           ("pantalon", assets.COLORES_PANTALON),
                                           ("zapatos", assets.COLORES_ZAPATOS), ("piel", assets.TONOS_PIEL)])
def test_el_jugador_vestido_lleva_el_color_elegido(pantalla, campo, paleta):
    for rol in assets.ROLES_APARIENCIA:
        normal = sprites.sprite_jugador(assets.COLOR_CIUDADANO, escala=1, rol=rol)
        vestido = sprites.sprite_jugador(assets.COLOR_CIUDADANO, escala=1, rol=rol,
                                         apariencia=PREDETERMINADA.con(campo, 1))
        assert paleta[1] in _pixeles(vestido) and paleta[1] not in _pixeles(normal), (rol, campo)


def test_la_vista_previa_de_cada_casilla_muestra_el_color(pantalla):
    cabeza = sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "ciudadano", None, 1, PREDETERMINADA.con("pelo", 3))
    traje = sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "ciudadano", None, 1, PREDETERMINADA.con("ropa", 0))
    zapatos = sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "ciudadano", None, 1, PREDETERMINADA.con("zapatos", 5))
    assert assets.TONOS_PELO[3] in _pixeles(cabeza) and assets.COLORES_ROPA[0] in _pixeles(traje)
    assert assets.COLORES_ZAPATOS[5] in _pixeles(zapatos) and assets.COLORES_ZAPATOS[5] not in _pixeles(cabeza)


@pytest.mark.parametrize("pestana", [HAIR, SHIRT, PANTS, SHOES])
def test_el_vestidor_dibuja_las_pestanas_nuevas(pantalla, pestana):
    from Online.personalizacion_render import dibujar_vestidor, rect_pestana
    vestidor = Vestidor(Apariencia(pelo=2, ropa=4, pantalon=6, zapatos=1), pestana)
    dibujar_vestidor(pantalla, vestidor, "periodista", assets.COLOR_PERIODISTA, (0, 0))
    for indice in range(len(PESTANAS)):  # las cinco pestañas entran en la fila de arriba
        assert rect_pestana(indice).right < 960


def test_las_teclas_1_a_5_abren_cada_pestana():
    for tecla, pestana in zip((pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5), PESTANAS):
        assert lobby.TECLAS_PESTANA_VESTIDOR[tecla] == PESTANAS.index(pestana)
