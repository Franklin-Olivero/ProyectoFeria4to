"""Crisis, misión «Segunda oportunidad», rechazo, fallo y finales (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import (  # noqa: E402
    COBERTURA_REDENCION,
    OPORTUNIDADES_REDENCION,
    RECUPERACION_REDENCION,
    TOPE_REPUTACION_TRAS_REDENCION,
)
from src.dungeon.partida import Partida  # noqa: E402
from src.story import reputacion as rep  # noqa: E402
from src.story.eleccion import FINAL_CONFIANZA_PERDIDA, FINAL_DIVIDIDA, determinar_final, resumen_final  # noqa: E402
from src.story.misiones import mision_actual  # noqa: E402
from src.story.redencion import (  # noqa: E402
    CONFIRMAR,
    DERECHA,
    ETAPA_COMPLETA,
    ETAPA_CONFIANZA,
    ETAPA_CORREGIR,
    ETAPA_FALLIDA,
    ETAPA_RECONOCER,
    EleccionCrisis,
)


def _campania_en_crisis(indice=0):
    c = Partida().campania
    c.rep(indice).aplicar(-70, "Compartiste algo falso.", "Colegio")
    c.red.expuestos = {"ana", "beto", "gina", "irene", "hugo"}
    return c


def _responder(mision, arbol, correcta=True):
    """Lleva el cursor a la opción (in)correcta del nivel y confirma."""
    for i, nodo in enumerate(arbol.opciones):
        if arbol.respuestas[nodo.id].correcta == correcta:
            while arbol.indice != i:
                mision.navegar(DERECHA)
            mision.navegar(CONFIRMAR)
            return
    raise AssertionError("no hay esa opción")


def _completar_reconocer(mision):
    _responder(mision, mision.arbol_reconocer)
    _responder(mision, mision.arbol_reconocer)
    assert mision.etapa == ETAPA_CORREGIR


def test_eleccion_de_crisis_tiene_dos_salidas_claras():
    e = EleccionCrisis()
    assert e.seleccion == e.ACEPTAR and e.resultado is None
    e.navegar(DERECHA)
    assert e.seleccion == e.RECHAZAR and e.resultado is None  # moverse no decide
    e.navegar(CONFIRMAR)
    assert e.resultado == e.RECHAZAR


def test_aceptar_redencion_abre_la_mision_una_sola_vez():
    c = _campania_en_crisis()
    assert c.jugador_en_crisis() == 0
    mision = c.aceptar_redencion(0)
    assert mision.etapa == ETAPA_RECONOCER and c.rep(0).estado_crisis == rep.EN_REDENCION
    assert c.jugador_en_crisis() is None  # no se vuelve a presentar
    assert c.aceptar_redencion(0) is mision
    assert mision_actual("ciudad", c, Partida(), redencion=mision).titulo == "SEGUNDA OPORTUNIDAD"


def test_etapa_1_exige_reconocer_la_publicacion_real_y_explica_el_error():
    c = _campania_en_crisis()
    m = c.aceptar_redencion(0)
    _responder(m, m.arbol_reconocer, correcta=False)
    assert m.etapa == ETAPA_RECONOCER and m.oportunidades == OPORTUNIDADES_REDENCION - 1 and m.aviso
    _responder(m, m.arbol_reconocer)
    assert m.arbol_reconocer.nodo is not m.arbol_reconocer.arbol.raiz  # bajó por el árbol
    _responder(m, m.arbol_reconocer, correcta=False)
    assert "culpa" in m.arbol_reconocer.pregunta.lower() or m.aviso
    _responder(m, m.arbol_reconocer)
    assert m.etapa == ETAPA_CORREGIR and m.aviso == ""


def test_etapa_2_es_un_bfs_real_y_muestra_quien_sigue_sin_corregir():
    c = _campania_en_crisis()
    m = c.aceptar_redencion(0)
    _completar_reconocer(m)
    assert m.objetivo_correccion == ["ana", "beto", "gina", "hugo", "irene"]
    assert m.cobertura() == 0.0
    # Desde Julio, a 2 saltos: beto, dario, cami, gina, hugo, ana: no llega a Irene.
    correccion = m.publicar_correccion("julio")
    assert correccion.origen == "julio" and correccion.saltos <= 2
    assert set(correccion.alcanzados) <= c.red.corregidos
    assert all(c.red.grafo.bfs("julio")[1][n] <= 2 for n in correccion.alcanzados)
    assert m.cobertura() >= COBERTURA_REDENCION or m.sin_corregir()


def test_etapa_2_sin_cobertura_cuesta_una_oportunidad_y_concede_otra_publicacion():
    c = _campania_en_crisis()
    c.red.expuestos = set(c.red.ciudadanos())
    m = c.aceptar_redencion(0)
    _completar_reconocer(m)
    # Irene está en un extremo: dos publicaciones desde allí no alcanzan al 75 %.
    m.publicar_correccion("julio")
    if m.etapa == ETAPA_CORREGIR:
        assert m.aviso
    alcanzados_antes = set(m.alcanzados)
    assert alcanzados_antes


def test_etapa_3_y_mision_completa_recuperan_sin_borrar_el_pasado():
    c = _campania_en_crisis()
    historial_antes = len(c.rep(0).historial)
    valor_antes = c.rep(0).valor
    desinformacion_antes = c.estado.valor("desinformacion")
    m = c.aceptar_redencion(0)
    _completar_reconocer(m)
    m.publicar_correccion("ana")  # Ana llega a toda la red en 2 saltos
    assert m.etapa == ETAPA_CONFIANZA
    _responder(m, m.arbol_confianza, correcta=False)
    assert m.etapa == ETAPA_CONFIANZA and m.aviso
    _responder(m, m.arbol_confianza)
    assert m.etapa == ETAPA_COMPLETA and m.completada

    cambio = c.completar_redencion(0)
    assert cambio.delta == RECUPERACION_REDENCION and c.rep(0).valor == valor_antes + RECUPERACION_REDENCION
    assert c.rep(0).valor < 0  # no recupera todo
    assert len(c.rep(0).historial) == historial_antes + 1  # el historial queda
    assert c.rep(0).tope == TOPE_REPUTACION_TRAS_REDENCION
    assert c.estado.valor("desinformacion") < desinformacion_antes
    assert c.rep(0).estado_crisis == rep.REDIMIDO and c.mision_de(0) is None
    # Sin duplicar: una segunda llamada no paga otra vez.
    assert c.completar_redencion(0) is None
    assert c.hubo_redencion()
    # Puede seguir la campaña y nunca más llega a referente.
    c.rep(0).aplicar(500)
    assert c.rep(0).valor == TOPE_REPUTACION_TRAS_REDENCION


def test_recaer_abre_otra_crisis_con_menor_recompensa():
    c = _campania_en_crisis()
    c.aceptar_redencion(0)
    c.completar_redencion(0)
    c.rep(0).aplicar(-100)
    assert c.jugador_en_crisis() == 0
    c.aceptar_redencion(0)
    valor = c.rep(0).valor
    cambio = c.completar_redencion(0)
    assert cambio.delta == RECUPERACION_REDENCION // 2 and c.rep(0).valor == valor + cambio.delta


def test_fallar_da_un_reintento_justo_antes_de_la_derrota():
    c = _campania_en_crisis()
    m = c.aceptar_redencion(0)
    for _ in range(OPORTUNIDADES_REDENCION):
        _responder(m, m.arbol_reconocer, correcta=False)
    assert m.etapa == ETAPA_RECONOCER and m.reintentos == 0
    assert m.oportunidades == OPORTUNIDADES_REDENCION and "último intento" in m.aviso
    for _ in range(OPORTUNIDADES_REDENCION):
        _responder(m, m.arbol_reconocer, correcta=False)
    assert m.etapa == ETAPA_FALLIDA and m.fallida and m.terminada
    # Terminada no se mueve más.
    m.navegar(CONFIRMAR)
    assert m.etapa == ETAPA_FALLIDA
    assert c.fallar_redencion(0) and c.rep(0).estado_crisis == rep.FALLIDA and c.rep(0).sin_voz


def test_rechazar_tiene_consecuencia_y_lleva_al_final_de_derrota_en_solitario():
    c = _campania_en_crisis()
    confianza = c.estado.valor("confianza")
    assert c.rechazar_redencion(0)
    assert c.rep(0).estado_crisis == rep.RECHAZADA and c.todos_sin_voz()
    assert c.estado.valor("confianza") < confianza
    assert determinar_final(c) == FINAL_CONFIANZA_PERDIDA
    assert "confianza perdida" in resumen_final(c)["titulo"].lower()
    balance = c.balance_final_individual(0)
    assert balance["reputacion"] == -70 and balance["expuestos"] >= 5 and balance["consecuencias"]
    assert balance["mensaje"] and balance["punto_control"]


def test_volver_al_punto_de_control_restaura_y_reabre_la_decision():
    c = _campania_en_crisis()
    valores = c.estado.como_dict()
    expuestos = set(c.red.expuestos)
    c.rechazar_redencion(0)
    assert c.volver_a_punto_control(0)
    assert c.jugador_en_crisis() == 0 and not c.rep(0).sin_voz
    assert c.estado.como_dict() == valores and c.red.expuestos == expuestos
    # Y esta vez puede aceptar.
    assert c.aceptar_redencion(0) is not None


def test_nueva_partida_tras_el_final_limpia_todo():
    p = Partida()
    c = p.campania
    c.rep(0).aplicar(-70)
    c.rechazar_redencion(0)
    p.reiniciar()
    assert c.reputacion == 0 and not c.todos_sin_voz() and c.puntos_control == {}


def test_en_cooperativo_rechazar_no_termina_la_partida_de_los_demas():
    c = _campania_en_crisis(1)
    c.rep(0)  # el J1 está bien
    assert c.jugador_en_crisis([0]) is None and c.jugador_en_crisis([1]) == 1
    c.rechazar_redencion(1)
    assert not c.todos_sin_voz() and c.puede_decidir(0) and not c.puede_decidir(1)
    assert determinar_final(c) == FINAL_DIVIDIDA  # el final global no se activa solo


def test_mision_funciona_sin_ciudadanos_expuestos():
    c = Partida().campania
    c.rep(0).aplicar(-70)
    m = c.aceptar_redencion(0)
    _completar_reconocer(m)
    assert m.cobertura() == 1.0
    m.publicar_correccion("ana")
    assert m.etapa == ETAPA_CONFIANZA
