"""Tests del capítulo 3 (infiltrado) y del final (elecciones y tres finales), sin pygame."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import (  # noqa: E402
    PUNTOS_INFILTRADO_CORRECTO,
    REPORTES_POR_ZONA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
)
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story.eleccion import (  # noqa: E402
    FINAL_ARQUITECTO,
    FINAL_DIVIDIDA,
    FINAL_RENACE,
    calcular_apoyos,
    determinar_final,
    resumen_final,
)
from src.story.investigacion import CONFIRMAR, DERECHA, IZQUIERDA, Investigacion  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR as T_CONFIRMAR, TerminalDecision  # noqa: E402


def _purificar(partida, zona):
    for _ in range(3):
        partida.campania.revelar_evidencia(zona)
    m = Mazmorra(REPORTES_POR_ZONA[zona], zona, semilla=0)
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.marcar_limpiado(cuarto)
    m.entrar(m.cuarto_final)
    terminal = TerminalDecision(partida.fabrica_arbol(zona)(), 15.0)
    terminal.iniciar()
    for _ in range(3):
        terminal.navegar(T_CONFIRMAR)
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)


def test_investigacion_navega_y_acusa_por_pistas():
    partida = Partida()
    campania = partida.campania
    assert not campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    _purificar(partida, ZONA_EMPRESA_MEDIOS)
    assert campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    assert not campania.investigacion_pendiente(ZONA_COLEGIO)

    inv = campania.nueva_investigacion()
    assert len(inv.cuentas) == 3 and inv.seleccionada["id"] == "hugo_oficial"
    inv.navegar(IZQUIERDA)
    assert inv.seleccionada["id"] == "elena_v"
    inv.navegar(DERECHA)
    inv.navegar(DERECHA)
    assert inv.seleccionada["id"] == "eco_nova_ok"  # la de 2 mil seguidores, no la popular
    inv.navegar(CONFIRMAR)
    assert inv.terminada and inv.resultado.correcto
    inv.navegar(DERECHA)  # terminada: no cambia
    assert inv.seleccionada["id"] == "eco_nova_ok"

    puntos = campania.puntos
    assert campania.registrar_investigacion(inv.resultado)
    assert campania.puntos == puntos + PUNTOS_INFILTRADO_CORRECTO
    assert campania.infiltrado_correcto
    assert not campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    assert not campania.registrar_investigacion(inv.resultado)  # una sola vez
    assert campania.puntos == puntos + PUNTOS_INFILTRADO_CORRECTO


def test_acusar_a_la_victima_cuesta():
    inv = Investigacion(Partida().campania.contenido["sospechosos"])
    resultado = inv.acusar("elena_v")
    assert not resultado.correcto and resultado.efectos["conflictos"] > 0 and resultado.reputacion < 0
    error = inv.acusar("hugo_oficial")
    assert not error.correcto and error.puntos == 0


def test_apoyos_son_deterministas_suman_100_y_dependen_del_estado():
    campania = Partida().campania
    candidatos = campania.contenido["candidatos"]
    a = calcular_apoyos(candidatos, campania.estado, campania.reputacion)
    b = calcular_apoyos(candidatos, campania.estado, campania.reputacion)
    assert a == b and abs(sum(p for _, p in a) - 100) < 0.5
    assert len({c["id"] for c, _ in a}) == 4
    lara_antes = dict((c["id"], p) for c, p in a)["lara"]
    campania.estado.aplicar({"desinformacion": 40})
    lara_despues = dict((c["id"], p) for c, p in calcular_apoyos(candidatos, campania.estado, campania.reputacion))["lara"]
    assert lara_despues > lara_antes  # el que se alimenta de la desinformación sube


def test_tres_finales_con_umbrales():
    partida = Partida()
    campania = partida.campania
    assert determinar_final(campania) == FINAL_DIVIDIDA  # estado inicial: ciudad a medias
    campania.estado.aplicar({"informacion_verificada": 30, "confianza": 10, "desinformacion": -10})
    assert determinar_final(campania) == FINAL_RENACE
    campania.pistas = ["col_e3", "hos_e3", "med_e3"]
    campania.jefe_derrotado = True
    assert determinar_final(campania) == FINAL_RENACE  # falta acusar bien
    campania.registrar_investigacion(campania.nueva_investigacion().acusar("eco_nova_ok"))
    assert determinar_final(campania) == FINAL_ARQUITECTO
    resumen = resumen_final(campania)
    assert resumen["titulo"] == "El arquitecto" and resumen["pistas_completas"]
    # Sin todas las pistas nunca hay final secreto, aunque todo lo demás esté.
    campania.pistas = ["col_e3"]
    assert determinar_final(campania) != FINAL_ARQUITECTO


def test_jefe_derrotado_una_vez_y_reinicio_limpia():
    partida = Partida()
    campania = partida.campania
    assert campania.registrar_jefe_derrotado()
    puntos = campania.puntos
    assert not campania.registrar_jefe_derrotado() and campania.puntos == puntos
    partida.reiniciar()
    assert not campania.jefe_derrotado and campania.infiltrado_elegido is None and campania.puntos == 0
