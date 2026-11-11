"""Vestidor del lobby online: lógica pura de las pestañas COLOR / HAT /
SKIN, clics del modal y cómo el lobby lo abre, lo usa y lo sincroniza."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from Online import lobby, personalizacion_render  # noqa: E402
from Online.personalizacion import (  # noqa: E402
    COLOR, COLUMNAS, HAT, PESTANAS, SKIN, Vestidor, etiqueta_opcion, opciones, texto_opcion,
)
from Online.personalizacion_render import (  # noqa: E402
    CENTRO_CERRAR, CERRAR, DENTRO, FUERA, OPCION, PESTANA, RECT_MODAL, RECT_OPCIONES,
    dibujar_vestidor, objetivo_en, rect_casilla, rect_pestana,
)
from Online.protocolo import LOBBY, GrafoSala, deserializar_buffer  # noqa: E402


# --- Lógica pura ----------------------------------------------------------

def test_cada_pestana_empieza_con_auto():
    assert opciones(COLOR) == (None, *range(len(assets.TONOS_PIEL)))
    assert opciones(HAT) == (None, *assets.ROLES_APARIENCIA)
    assert opciones(SKIN) == (None, *assets.ROLES_APARIENCIA)


def test_vestidor_nuevo_tiene_todo_en_auto():
    vestidor = Vestidor()
    assert vestidor.pestana == COLOR
    assert vestidor.apariencia == PREDETERMINADA
    assert [vestidor.indice_elegido(p) for p in PESTANAS] == [0] * len(PESTANAS) and len(PESTANAS) == 6
    assert Vestidor(pestana="PET").pestana == COLOR  # no hay pestaña de mascotas


def test_elegir_equipa_el_campo_de_la_pestana_visible():
    vestidor = Vestidor()
    assert vestidor.elegir(3) is True
    assert vestidor.apariencia == Apariencia(piel=2)
    vestidor.ir_a_pestana(1)
    assert vestidor.elegir(3) is True
    assert vestidor.apariencia == Apariencia(piel=2, cabeza=assets.ROLES_APARIENCIA[2])
    vestidor.ir_a_pestana(2)
    assert vestidor.elegir(4) is True
    assert vestidor.apariencia.traje == assets.ROLES_APARIENCIA[3]
    assert vestidor.elegir(0) is True  # AUTO vuelve al traje del rol
    assert vestidor.apariencia.traje is None


def test_elegir_lo_mismo_o_fuera_de_rango_no_cambia():
    vestidor = Vestidor(Apariencia(piel=4))
    assert vestidor.elegir(5) is False  # el tono 4 ya está en la casilla 5
    assert vestidor.elegir(-1) is False
    assert vestidor.elegir(len(opciones(COLOR))) is False
    assert vestidor.apariencia == Apariencia(piel=4)


def test_izquierda_y_derecha_recorren_en_ciclo():
    vestidor = Vestidor(pestana=HAT)
    assert vestidor.mover(-1, 0) is True
    assert vestidor.indice_elegido() == len(opciones(HAT)) - 1
    assert vestidor.mover(1, 0) is True
    assert vestidor.indice_elegido() == 0
    assert vestidor.apariencia.cabeza is None


def test_arriba_y_abajo_cambian_de_fila():
    vestidor = Vestidor()  # COLOR: 9 casillas en filas de 5
    vestidor.elegir(2)
    assert vestidor.mover(0, 1) and vestidor.indice_elegido() == 2 + COLUMNAS
    assert vestidor.mover(0, -1) and vestidor.indice_elegido() == 2
    assert vestidor.mover(0, -1) is False  # ya está en la primera fila
    vestidor.elegir(COLUMNAS - 1)  # fin de la fila de arriba: abajo no hay casilla
    assert vestidor.mover(0, 1) and vestidor.indice_elegido() == len(opciones(COLOR)) - 1
    assert vestidor.mover(0, 1) is False  # ya está en la última fila


def test_abajo_no_hace_nada_con_una_sola_fila():
    vestidor = Vestidor(Apariencia(traje="influencer"), pestana=SKIN)
    assert vestidor.mover(0, 1) is False
    assert vestidor.apariencia.traje == "influencer"


def test_pestanas_en_ciclo_sin_tocar_la_apariencia():
    vestidor = Vestidor(Apariencia(piel=1))
    assert vestidor.pestana_siguiente(-1) is True and vestidor.pestana == PESTANAS[-1]  # la última: PANTS
    assert vestidor.pestana_siguiente() is True and vestidor.pestana == COLOR
    assert vestidor.ir_a_pestana(0) is False  # ya estaba
    assert vestidor.ir_a_pestana(len(PESTANAS)) is False
    assert vestidor.apariencia == Apariencia(piel=1)


def test_valor_desconocido_se_muestra_como_auto():
    # Una Apariencia armada a mano con un tono que no existe no rompe el modal.
    assert Vestidor(Apariencia(piel=99)).indice_elegido() == 0


def test_textos_de_las_opciones():
    assert texto_opcion(COLOR, None, "periodista") == "Auto: piel original"
    assert texto_opcion(COLOR, 0, "periodista") == "Tono 1"
    assert texto_opcion(HAT, None, "periodista") == "Auto: cabeza de tu rol (Periodista)"
    assert texto_opcion(SKIN, "candidato", "periodista") == "Traje de Candidato"
    assert etiqueta_opcion(HAT, None) == "AUTO"
    assert etiqueta_opcion(COLOR, 7) == "Tono 8"
    assert etiqueta_opcion(SKIN, "ciudadano") == "Ciudadano"


# --- Modal: geometría y clics ---------------------------------------------

def test_las_casillas_caben_en_su_panel_sin_pisarse():
    rects = [rect_casilla(i) for i in range(len(opciones(COLOR)))]
    for i, rect in enumerate(rects):
        assert RECT_OPCIONES.contains(rect)
        assert all(not rect.colliderect(otro) for otro in rects[i + 1:])
    assert all(RECT_MODAL.contains(rect_pestana(i)) for i in range(len(PESTANAS)))


def test_objetivo_bajo_el_raton():
    vestidor = Vestidor(pestana=HAT)
    assert objetivo_en(vestidor, CENTRO_CERRAR) == (CERRAR, None)
    assert objetivo_en(vestidor, rect_pestana(2).center) == (PESTANA, 2)
    assert objetivo_en(vestidor, rect_casilla(4).center) == (OPCION, 4)
    # HAT tiene 5 casillas: donde COLOR tendría la sexta no hay nada.
    assert objetivo_en(vestidor, rect_casilla(5).center) == (DENTRO, None)
    vestidor.ir_a_pestana(0)
    assert objetivo_en(vestidor, rect_casilla(5).center) == (OPCION, 5)
    assert objetivo_en(vestidor, (RECT_MODAL.left - 5, RECT_MODAL.centery)) == (FUERA, None)


@pytest.mark.parametrize("pestana", PESTANAS)
def test_el_modal_se_dibuja_en_cada_pestana(pestana):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    vestidor = Vestidor(Apariencia(piel=6, cabeza="candidato", traje="influencer"), pestana)
    dibujar_vestidor(pantalla, vestidor, "periodista", assets.COLOR_PERIODISTA, rect_casilla(1).center)
    # La casilla equipada lleva el borde de acento.
    elegida = rect_casilla(vestidor.indice_elegido())
    assert pantalla.get_at((elegida.centerx, elegida.top + 1))[:3] == personalizacion_render.COLOR_ACENTO


# --- Lobby: abrir, usar y sincronizar -------------------------------------

def _tecla(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)


def _clic(posicion):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=posicion)


def test_cada_caja_es_un_vestidor_al_alcance():
    assert len(lobby.CAJAS_VESTIDOR) == 4
    for indice, caja in enumerate(lobby.CAJAS_VESTIDOR):
        # Parado justo debajo de la caja (sin chocar con ella).
        assert lobby._caja_cercana(caja.centerx, caja.bottom + 20) == indice
    laptop = lobby.OBSTACULOS[0]
    assert lobby._caja_cercana(laptop.centerx, laptop.bottom + 30) is None


def test_teclado_en_el_vestidor():
    vestidor = Vestidor()
    assert lobby._evento_vestidor(_tecla(pygame.K_RIGHT), vestidor) == lobby.CAMBIO_VESTIDOR
    assert vestidor.apariencia == Apariencia(piel=0)
    assert lobby._evento_vestidor(_tecla(pygame.K_2), vestidor) is None
    assert vestidor.pestana == HAT
    assert lobby._evento_vestidor(_tecla(pygame.K_TAB), vestidor) is None
    assert vestidor.pestana == SKIN
    assert lobby._evento_vestidor(_tecla(pygame.K_TAB, pygame.KMOD_LSHIFT), vestidor) is None
    assert vestidor.pestana == HAT
    assert lobby._evento_vestidor(_tecla(pygame.K_d), vestidor) == lobby.CAMBIO_VESTIDOR
    assert vestidor.apariencia == Apariencia(piel=0, cabeza=assets.ROLES_APARIENCIA[0])
    assert lobby._evento_vestidor(_tecla(pygame.K_w), vestidor) is None  # una sola fila
    for tecla in (pygame.K_e, pygame.K_ESCAPE, pygame.K_RETURN):
        assert lobby._evento_vestidor(_tecla(tecla), vestidor) == lobby.CERRAR_VESTIDOR


def test_raton_en_el_vestidor():
    vestidor = Vestidor()
    assert lobby._evento_vestidor(_clic(rect_pestana(2).center), vestidor) is None
    assert vestidor.pestana == SKIN
    assert lobby._evento_vestidor(_clic(rect_casilla(3).center), vestidor) == lobby.CAMBIO_VESTIDOR
    assert vestidor.apariencia.traje == assets.ROLES_APARIENCIA[2]
    assert lobby._evento_vestidor(_clic(rect_casilla(3).center), vestidor) is None  # ya la tenía
    assert lobby._evento_vestidor(_clic(CENTRO_CERRAR), vestidor) == lobby.CERRAR_VESTIDOR
    assert lobby._evento_vestidor(_clic((5, 5)), vestidor) == lobby.CERRAR_VESTIDOR


class _HostFalso:
    def __init__(self):
        self.sala = GrafoSala()
        self.sala.conectar(0)
        self.sala.conectar(1)
        self.enviados = []

    def enviar_a_todos(self, datos):
        self.enviados.append(datos)


class _InvitadoFalso:
    def __init__(self):
        self.apariencias = []

    def enviar_apariencia(self, apariencia):
        self.apariencias.append(apariencia)


def test_el_host_guarda_su_apariencia_y_avisa_a_la_sala():
    host = _HostFalso()
    apariencia = Apariencia(piel=5, traje="candidato")
    lobby._actualizar_apariencia(True, host, apariencia)
    assert host.sala.apariencia_de(0) == apariencia
    mensajes, _ = deserializar_buffer(b"".join(host.enviados))
    assert mensajes[-1]["tipo"] == LOBBY
    sala = GrafoSala.de_dict(mensajes[-1]["sala"])
    assert sala.apariencia_de(0) == apariencia
    assert sala.apariencia_de(1) == PREDETERMINADA


def test_el_invitado_la_manda_al_host():
    invitado = _InvitadoFalso()
    apariencia = Apariencia(cabeza="periodista")
    lobby._actualizar_apariencia(False, invitado, apariencia)
    assert invitado.apariencias == [apariencia]
