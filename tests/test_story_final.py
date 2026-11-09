"""Tests del capítulo 3 (origen de la señal) y del final (elecciones y tres finales), sin pygame."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import (  # noqa: E402
    PUNTOS_ORIGEN_RASTREADO,
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


def _ruta_hasta_el_origen(inv):
    """Sigue el hilo correcto eligiendo la opción por su cuenta."""
    for cuenta in ("nova_despierta", "repetidor", "nova_root"):
        while inv.opcion_seleccionada.cuenta != cuenta:
            inv.navegar(DERECHA)
        inv.navegar(CONFIRMAR)


def test_investigacion_es_un_dfs_con_pila_y_backtracking():
    partida = Partida()
    campania = partida.campania
    assert not campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    _purificar(partida, ZONA_EMPRESA_MEDIOS)
    assert campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    assert not campania.investigacion_pendiente(ZONA_COLEGIO)

    inv = campania.nueva_investigacion()
    assert inv.actual == "datos_nova" and inv.pila == ["datos_nova"]
    # Bajar por un hilo que termina en una persona y volver (backtracking).
    while inv.opcion_seleccionada.cuenta != "eco_nova":
        inv.navegar(DERECHA)
    inv.navegar(CONFIRMAR)
    assert inv.pila == ["datos_nova", "eco_nova"]
    while inv.opcion_seleccionada.tipo != "volver":
        inv.navegar(IZQUIERDA)
    inv.navegar(CONFIRMAR)
    assert inv.pila == ["datos_nova"] and "eco_nova" in inv.visitadas
    # Una cuenta visitada no se ofrece otra vez.
    assert "eco_nova" not in inv.vecinas_sin_visitar()
    _ruta_hasta_el_origen(inv)
    assert inv.pila == ["datos_nova", "nova_despierta", "repetidor", "nova_root"]
    assert sorted(inv.orden_dfs_referencia()) == sorted(inv.cuentas)  # DFS real sobre el Grafo
    while inv.opcion_seleccionada.tipo != "senalar":
        inv.navegar(DERECHA)
    inv.navegar(CONFIRMAR)
    assert inv.terminada and inv.resultado.correcto and inv.resultado.tipo == "origen"

    puntos = campania.puntos
    assert campania.registrar_investigacion(inv.resultado)
    assert campania.puntos == puntos + PUNTOS_ORIGEN_RASTREADO
    assert campania.origen_rastreado
    assert not campania.investigacion_pendiente(ZONA_EMPRESA_MEDIOS)
    assert not campania.registrar_investigacion(inv.resultado)  # una sola vez
    assert campania.puntos == puntos + PUNTOS_ORIGEN_RASTREADO


def test_senalar_a_una_persona_inocente_cuesta_pero_no_bloquea():
    inv = Investigacion(Partida().campania.contenido["red_cuentas"])
    victima = inv.senalar("elena")
    assert not victima.correcto and victima.efectos["conflictos"] > 0 and victima.reputacion == -20
    error = inv.senalar("hugo")
    assert not error.correcto and error.puntos == 0 and error.reputacion == -10
    pieza = inv.senalar("eco_nova")
    assert not pieza.correcto and pieza.reputacion == 0


def test_no_quedan_rastros_de_un_modo_impostor():
    datos = Partida().campania.contenido
    assert "sospechosos" not in datos
    assert datos["capitulos"][ZONA_EMPRESA_MEDIOS]["titulo"] == "El origen de la señal"
    texto = str(datos).lower()
    for palabra in ("impostor", "infiltrado", "traidor", "votar para expulsar"):
        assert palabra not in texto


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
    assert determinar_final(campania) == FINAL_RENACE  # falta rastrear el origen
    campania.registrar_investigacion(campania.nueva_investigacion().senalar("nova_root"))
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
    assert not campania.jefe_derrotado and campania.origen_elegido is None and campania.puntos == 0
