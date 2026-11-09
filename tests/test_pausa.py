"""Menú de pausa (sin pygame): abrir y cerrar, opciones por escena y
modo, confirmaciones, multijugador, y que en pausa el mundo no avanza."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import REPORTES_POR_ZONA  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.dungeon.gracia_entrada import GraciaEntrada  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.ui import pausa as p  # noqa: E402
from src.ui.ajustes import PESTANAS_PAUSA, ModalAjustes  # noqa: E402
from src.ui.navegacion import ABAJO, ARRIBA, CONFIRMAR, DERECHA, VOLVER  # noqa: E402
from src.ui.terminal_decision import TerminalDecision, construir_arbol_publicacion  # noqa: E402


def abierta(escena=Escena.MAZMORRA, jugadores=1, en_red=False):
    pausa = p.Pausa()
    assert pausa.abrir(escena, jugadores, en_red)
    return pausa


# ----------------------------------------------------------------------
# Abrir, cerrar y opciones
# ----------------------------------------------------------------------

def test_se_abre_en_ciudad_mazmorra_decision_y_jefe():
    for escena in (Escena.CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE):
        assert p.Pausa().abrir(escena)


def test_no_se_abre_en_resultado_victoria_ni_derrota():
    for escena in (Escena.RESULTADO, Escena.VICTORIA, Escena.DERROTA):
        assert not p.Pausa().abrir(escena)


def test_opciones_por_escena():
    assert p.opciones_para(Escena.CIUDAD) == [p.CONTINUAR, p.AJUSTES, p.SALIR_MENU]
    assert p.opciones_para(Escena.MAZMORRA) == [p.CONTINUAR, p.AJUSTES, p.REINICIAR, p.VOLVER_CIUDAD, p.SALIR_MENU]
    assert p.VOLVER_CIUDAD in p.opciones_para(Escena.DECISION)
    # En el jefe final no se puede volver a la ciudad.
    assert p.opciones_para(Escena.JEFE) == [p.CONTINUAR, p.AJUSTES, p.REINICIAR, p.SALIR_MENU]


def test_continuar_y_esc_cierran_sin_otra_accion():
    pausa = abierta()
    pausa.accion(CONFIRMAR)  # el foco empieza en Continuar
    assert pausa.tomar_accion() == p.CONTINUAR
    assert pausa.tomar_accion() is None  # se lee una sola vez
    pausa = abierta()
    pausa.accion(VOLVER)
    assert pausa.tomar_accion() == p.CONTINUAR


def test_foco_da_la_vuelta():
    pausa = abierta(Escena.CIUDAD)
    pausa.accion(ARRIBA)
    assert pausa.opcion_enfocada == p.SALIR_MENU
    pausa.accion(ABAJO)
    assert pausa.opcion_enfocada == p.CONTINUAR


def test_reiniciar_volver_y_salir_piden_confirmacion():
    for opcion in (p.REINICIAR, p.VOLVER_CIUDAD, p.SALIR_MENU):
        pausa = abierta()
        pausa.elegir(opcion)
        assert pausa.confirmando == opcion and pausa.foco_confirmacion == p.NO
        pausa.accion(CONFIRMAR)  # No
        assert pausa.confirmando is None and pausa.tomar_accion() is None
        pausa.elegir(opcion)
        pausa.accion(DERECHA)  # a Sí
        pausa.accion(CONFIRMAR)
        assert pausa.tomar_accion() == opcion


def test_esc_en_la_confirmacion_la_cancela():
    pausa = abierta()
    pausa.elegir(p.SALIR_MENU)
    pausa.accion(VOLVER)
    assert pausa.confirmando is None and pausa.abierta and pausa.tomar_accion() is None


def test_ajustes_dentro_de_la_pausa_y_volver():
    pausa = abierta()
    pausa.elegir(p.AJUSTES)
    assert pausa.tomar_accion() == p.AJUSTES
    modal = ModalAjustes(Preferencias(), AjustesAudio(), PESTANAS_PAUSA)
    pausa.abrir_ajustes(modal)
    pausa.accion(ABAJO)  # -> volumen general
    pausa.accion(p.IZQUIERDA)
    assert modal.audio.volumen_general == 95
    pausa.accion(VOLVER)  # cierra el modal, la pausa sigue abierta
    assert pausa.ajustes is None and pausa.abierta


def test_raton_enfoca_y_elige():
    pausa = abierta()
    assert pausa.enfocar(p.AJUSTES)
    assert not pausa.enfocar("no_existe")
    pausa.elegir(p.VOLVER_CIUDAD)
    assert pausa.enfocar(p.SI) and pausa.elegir(p.SI)
    assert pausa.tomar_accion() == p.VOLVER_CIUDAD


# ----------------------------------------------------------------------
# Individual vs. multijugador
# ----------------------------------------------------------------------

def test_individual_congela():
    assert abierta(jugadores=1).congelada


def test_multijugador_local_u_online_no_congela():
    assert not abierta(jugadores=2).congelada
    assert not abierta(jugadores=1, en_red=True).congelada
    assert not p.congela(4, False)


def test_el_flag_permite_congelar_en_multijugador():
    pausa = p.Pausa()
    pausa.abrir(Escena.MAZMORRA, 2, False, multijugador_permitido=True)
    assert pausa.congelada


def test_cerrar_descongela():
    pausa = abierta()
    pausa.cerrar()
    assert not pausa.abierta and not pausa.congelada


# ----------------------------------------------------------------------
# En pausa el mundo no avanza
# ----------------------------------------------------------------------

def test_con_pausa_congelada_avanzar_no_cambia_los_temporizadores():
    gracia = GraciaEntrada()
    gracia.iniciar()
    terminal = TerminalDecision(construir_arbol_publicacion())
    terminal.iniciar()
    mazmorra = Mazmorra(REPORTES_POR_ZONA["Colegio"], "Colegio", semilla=1)
    antes = (gracia.restante, terminal.tiempo_restante, dict(mazmorra.toxicidad))

    pausa = abierta()
    for _ in range(1200):  # 20 s simulados: sin pausa ya habría propagado toxicidad (cada 15 s)
        assert not p.avanzar(pausa, 1 / 60, gracia.actualizar, terminal.actualizar,
                             lambda dt: mazmorra.actualizar(dt, True))
    assert (gracia.restante, terminal.tiempo_restante, dict(mazmorra.toxicidad)) == antes

    pausa.cerrar()
    for _ in range(1200):
        assert p.avanzar(pausa, 1 / 60, gracia.actualizar, terminal.actualizar,
                         lambda dt: mazmorra.actualizar(dt, True))
    assert gracia.restante < antes[0] and terminal.tiempo_restante < antes[1]
    assert dict(mazmorra.toxicidad) != antes[2]  # la propagación sí corre sin pausa


def test_en_multijugador_el_mundo_sigue_con_el_menu_abierto():
    gracia = GraciaEntrada()
    gracia.iniciar()
    pausa = abierta(jugadores=2)
    assert p.avanzar(pausa, 0.25, gracia.actualizar)
    assert gracia.restante < gracia.duracion


from src.audio.ajustes_audio import AjustesAudio  # noqa: E402
from src.core.preferencias import Preferencias  # noqa: E402
