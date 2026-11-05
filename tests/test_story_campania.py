"""Tests de la campaña y del estado de Ciudad Nova integrados a la Partida (sin pygame).

Cubren: prólogo una sola vez, intro por zona una vez, evidencia por
cuarto limpio y pistas sin duplicar, indicadores acotados a 0-100,
cierre de mazmorra que aplica la consecuencia UNA vez, sin dobles
recompensas, derrota global y reinicio completo.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    INDICADORES_INICIALES,
    REPORTES_POR_ZONA,
    REPUTACION_INICIAL,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_HOSPITAL,
)
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story.dialogo import DialogoSecuencia  # noqa: E402
from src.story.escenarios import DESMENTIDO, PARCIAL, SIN_PRUEBAS  # noqa: E402
from src.story.estado_ciudad import EstadoCiudad  # noqa: E402
from src.ui.terminal_decision import (  # noqa: E402
    CONFIRMAR,
    DERECHA,
    DETONACION,
    PURIFICACION_EXITOSA,
    TerminalDecision,
)


# ----------------------------------------------------------------------
# EstadoCiudad
# ----------------------------------------------------------------------


def test_estado_inicial_y_acotado():
    estado = EstadoCiudad()
    assert estado.como_dict() == INDICADORES_INICIALES
    deltas = estado.aplicar({"confianza": 80, "conflictos": -100})
    assert estado.valor("confianza") == 100 and estado.valor("conflictos") == 0
    assert deltas == {"confianza": 100 - INDICADORES_INICIALES["confianza"],
                      "conflictos": -INDICADORES_INICIALES["conflictos"]}
    with pytest.raises(KeyError):
        estado.aplicar({"karma": 1})


def test_salud_sube_con_buenos_y_baja_con_malos():
    estado = EstadoCiudad()
    base = estado.salud()
    estado.aplicar({"desinformacion": 30})
    assert estado.salud() < base
    estado.aplicar({"informacion_verificada": 40, "confianza": 40})
    assert estado.salud() > base


# ----------------------------------------------------------------------
# Diálogos
# ----------------------------------------------------------------------


def test_prologo_una_sola_vez_y_con_variante_por_rol():
    partida = Partida()
    dialogo = partida.campania.dialogo_prologo("periodista", "Periodista")
    assert isinstance(dialogo, DialogoSecuencia) and not dialogo.terminado
    textos = [linea.texto for linea in dialogo.lineas]
    assert any("campaña coordinada" in t for t in textos)
    assert any(linea.hablante == "Periodista" and linea.retrato == "periodista" for linea in dialogo.lineas)
    assert partida.campania.dialogo_prologo("periodista", "Periodista") is None
    dialogo.saltar()
    assert dialogo.terminado


def test_dialogo_avanza_y_filtra_por_pistas():
    partida = Partida()
    campania = partida.campania
    campania.pistas = ["col_e3", "hos_e3", "med_e3"]
    completo = campania.dialogo_capitulo(ZONA_ALCALDIA, "ciudadano", "Ciudadano")
    assert any("todas las pistas" in l.texto for l in completo.lineas)
    assert not any("No tengo todas" in l.texto for l in completo.lineas)
    assert campania.dialogo_capitulo(ZONA_ALCALDIA, "ciudadano", "Ciudadano") is None
    campania.reiniciar()
    parcial = campania.dialogo_capitulo(ZONA_ALCALDIA, "ciudadano", "Ciudadano")
    assert any("No tengo todas" in l.texto for l in parcial.lineas)
    total = parcial.progreso[1]
    for _ in range(total):
        parcial.avanzar()
    assert parcial.terminado and parcial.actual is None
    assert campania.dialogo_capitulo("Plaza") is None


# ----------------------------------------------------------------------
# Evidencia y pistas
# ----------------------------------------------------------------------


def test_evidencia_por_cuarto_y_pistas_sin_duplicar():
    campania = Partida().campania
    assert campania.estado_evidencia(ZONA_COLEGIO) == SIN_PRUEBAS
    assert campania.revelar_evidencia(ZONA_COLEGIO)["id"] == "col_e1"
    assert campania.estado_evidencia(ZONA_COLEGIO) == PARCIAL
    campania.revelar_evidencia(ZONA_COLEGIO)
    assert campania.pistas == []
    tercera = campania.revelar_evidencia(ZONA_COLEGIO)
    assert tercera.get("pista") and campania.pistas == ["col_e3"]
    assert campania.estado_evidencia(ZONA_COLEGIO) == DESMENTIDO
    assert campania.revelar_evidencia(ZONA_COLEGIO) is None
    assert campania.pistas == ["col_e3"]
    assert len(campania.textos_pistas()) == 1


# ----------------------------------------------------------------------
# Cierre de mazmorra con consecuencia
# ----------------------------------------------------------------------


def _mazmorra_lista(zona, semilla=0):
    m = Mazmorra(REPORTES_POR_ZONA[zona], zona, semilla=semilla)
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.marcar_limpiado(cuarto)
    m.entrar(m.cuarto_final)
    return m


def _terminal_resuelta(partida, zona, *pasos):
    terminal = TerminalDecision(partida.fabrica_arbol(zona)(), 15.0)
    terminal.iniciar()
    for paso in pasos:
        terminal.navegar(paso)
    return terminal


def test_cerrar_mazmorra_aplica_consecuencia_una_sola_vez():
    partida = Partida()
    campania = partida.campania
    for _ in range(3):
        campania.revelar_evidencia(ZONA_COLEGIO)
    m = _mazmorra_lista(ZONA_COLEGIO)
    terminal = _terminal_resuelta(partida, ZONA_COLEGIO, CONFIRMAR, CONFIRMAR, CONFIRMAR)
    assert terminal.resultado == PURIFICACION_EXITOSA

    antes = campania.estado.como_dict()
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert partida.progreso.mazmorras_completadas == 1
    assert campania.ultima_consecuencia.exito
    assert campania.estado.valor("informacion_verificada") > antes["informacion_verificada"]
    assert campania.puntos == 120 and campania.reputacion > REPUTACION_INICIAL + 10
    despues = campania.estado.como_dict()
    reputacion_tras_decidir = campania.reputacion

    # Segunda llamada con la misma mazmorra: nada cambia.
    assert not partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert campania.estado.como_dict() == despues and campania.puntos == 120
    assert campania.reputacion == reputacion_tras_decidir
    assert partida.progreso.mazmorras_completadas == 1


def test_sin_evidencia_la_misma_opcion_detona_y_no_completa():
    partida = Partida()
    m = _mazmorra_lista(ZONA_COLEGIO)
    terminal = _terminal_resuelta(partida, ZONA_COLEGIO, CONFIRMAR, CONFIRMAR, CONFIRMAR)
    assert terminal.resultado == DETONACION
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert partida.progreso.mazmorras_completadas == 0
    assert partida.colapso.valor > 0
    assert partida.campania.reputacion < REPUTACION_INICIAL
    assert partida.campania.ultima_consecuencia.estado_evidencia == SIN_PRUEBAS


def test_repetir_zona_no_duplica_puntos_pero_si_efectos():
    partida = Partida()
    campania = partida.campania
    for _ in range(3):
        campania.revelar_evidencia(ZONA_COLEGIO)
    for semilla in (1, 2):
        m = _mazmorra_lista(ZONA_COLEGIO, semilla)
        terminal = _terminal_resuelta(partida, ZONA_COLEGIO, CONFIRMAR, CONFIRMAR, CONFIRMAR)
        assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert campania.puntos == 120  # una sola recompensa
    assert len(campania.rep(0).historial) == 1  # la reputación tampoco se duplica
    # Los efectos sí se repiten (y la corrección por el grafo suma encima).
    assert campania.estado.valor("informacion_verificada") >= min(100, INDICADORES_INICIALES["informacion_verificada"] + 24)


def test_tiempo_agotado_aplica_consecuencia_coherente():
    partida = Partida()
    m = _mazmorra_lista(ZONA_HOSPITAL)
    terminal = _terminal_resuelta(partida, ZONA_HOSPITAL, DERECHA)
    terminal.actualizar(99)
    assert terminal.resultado == DETONACION and terminal.opcion_elegida is None
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert "tiempo" in partida.campania.ultima_consecuencia.texto.lower()


def test_cerrar_sin_terminal_sigue_funcionando_como_antes():
    partida = Partida()
    m = _mazmorra_lista(ZONA_COLEGIO)
    assert partida.cerrar_mazmorra(m, PURIFICACION_EXITOSA)
    assert partida.progreso.mazmorras_completadas == 1
    assert partida.campania.ultima_consecuencia is None


def test_reiniciar_limpia_toda_la_campania():
    partida = Partida()
    campania = partida.campania
    campania.dialogo_prologo()
    campania.dialogo_capitulo(ZONA_COLEGIO)
    for _ in range(3):
        campania.revelar_evidencia(ZONA_COLEGIO)
    campania.estado.aplicar({"desinformacion": 50})
    campania.puntos = 500
    partida.reiniciar()
    assert campania.dialogo_prologo() is not None
    assert campania.pistas == [] and campania.puntos == 0
    assert campania.estado.como_dict() == INDICADORES_INICIALES
    assert campania.estado_evidencia(ZONA_COLEGIO) == SIN_PRUEBAS
    assert campania.reputacion == REPUTACION_INICIAL
    assert partida.colapso.valor == 0.0


def test_fabrica_de_zona_sin_escenario_cae_al_arbol_original():
    partida = Partida()
    arbol = partida.fabrica_arbol("Plaza")()
    assert arbol.raiz.etiqueta == "Publicación Viral"
    assert partida.campania.escenario_activo is None
