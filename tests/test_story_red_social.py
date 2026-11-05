"""Tests del grafo social (BFS/DFS), la propagación en la campaña y los eventos aleatorios (sin pygame).

Cubren: nadie se cuenta dos veces, máximo de saltos, semilla
reproducible, la corrección reduce rebotes futuros sin borrar la
memoria, rastreo DFS y cadena de contagio, propagación integrada al
cierre de una zona, matices por rol y eventos con efectos aplicados una
vez y titulares en el cintillo.
"""

import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    PROBABILIDAD_REBOTE_BASE,
    PROBABILIDAD_REBOTE_CORREGIDA,
    REPORTES_POR_ZONA,
    REPUTACION_INICIAL,
    SALTOS_MAXIMOS_PROPAGACION,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
)
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story import contenido  # noqa: E402
from src.story.campania import Campania  # noqa: E402
from src.story.eventos import sortear_evento  # noqa: E402
from src.story.red_social import CORRECCION, RUMOR, RedSocial  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR, DERECHA, DETONACION, PURIFICACION_EXITOSA, TerminalDecision  # noqa: E402


@pytest.fixture(scope="module")
def datos():
    return contenido.cargar()


def red_segura(datos, semilla=7):
    """Red con probabilidad 1 (vía rng fijo en 0): la propagación es el BFS exacto."""
    class Siempre(random.Random):
        def random(self):
            return 0.0
    return RedSocial(datos["red_social"], Siempre(semilla))


def test_red_social_es_un_grafo_distinto_al_de_calles(datos):
    red = RedSocial(datos["red_social"], random.Random(0))
    assert 8 <= len(red.grafo) <= 12
    assert "hugo" in red.grafo and "Plaza" not in red.grafo
    assert red.grafo.es_conexo()
    assert red.nombre("hugo") == "Hugo Salas"


def test_bfs_no_cuenta_dos_veces_y_respeta_saltos(datos):
    red = red_segura(datos)
    propagacion = red.propagar("hugo", saltos_max=1)
    assert propagacion.capas[0] == ["hugo"]
    assert set(propagacion.capas[1]) == set(red.grafo.vecinos("hugo"))
    assert propagacion.saltos == 1
    assert len(propagacion.alcanzados) == len(set(propagacion.alcanzados))

    completa = red.propagar("hugo", saltos_max=SALTOS_MAXIMOS_PROPAGACION)
    _, distancias, _ = red.grafo.bfs("hugo")
    esperado = {n for n, d in distancias.items() if d <= SALTOS_MAXIMOS_PROPAGACION}
    assert set(completa.alcanzados) == esperado
    assert len(completa.alcanzados) == len(esperado)  # sin duplicados pese al ciclo hugo-ana-cami
    for nodo in completa.alcanzados:
        cadena = completa.cadena_hasta(nodo)
        assert cadena[0] == "hugo" and cadena[-1] == nodo
        assert len(cadena) - 1 == distancias[nodo]


def test_semilla_reproducible_y_azar_influye(datos):
    a = RedSocial(datos["red_social"], random.Random(3)).propagar("hugo")
    b = RedSocial(datos["red_social"], random.Random(3)).propagar("hugo")
    assert a.alcanzados == b.alcanzados and a.aristas == b.aristas
    distintos = {tuple(RedSocial(datos["red_social"], random.Random(s)).propagar("hugo").alcanzados) for s in range(20)}
    assert len(distintos) > 1


def test_correccion_reduce_rebotes_sin_borrar_la_memoria(datos):
    red = red_segura(datos)
    rumor = red.propagar("hugo")
    expuestos = set(red.expuestos)
    assert expuestos == set(rumor.alcanzados)
    correccion = red.corregir("hugo", saltos_max=1)
    assert correccion.tipo == CORRECCION and "hugo" in correccion.alcanzados
    assert red.expuestos == expuestos  # la memoria no se borra
    assert red.probabilidad_de("hugo") == PROBABILIDAD_REBOTE_CORREGIDA
    assert red.probabilidad_de("julio") == PROBABILIDAD_REBOTE_BASE
    # Con azar real, un origen corregido reenvía menos en promedio.
    def alcance_medio(corregir):
        total = 0
        for semilla in range(60):
            r = RedSocial(datos["red_social"], random.Random(semilla))
            if corregir:
                r.corregir("hugo")
            total += r.propagar("hugo").total
        return total / 60
    assert alcance_medio(True) < alcance_medio(False)


def test_dfs_rastrea_desde_un_nodo(datos):
    red = red_segura(datos)
    orden = red.rastrear("elena")
    assert orden[0] == "elena" and set(orden) == set(red.ciudadanos())
    assert orden == red.grafo.dfs("elena")
    with pytest.raises(KeyError):
        red.propagar("nadie")


# ----------------------------------------------------------------------
# Integración con la campaña
# ----------------------------------------------------------------------


def _mazmorra_lista(zona, semilla=0):
    m = Mazmorra(REPORTES_POR_ZONA[zona], zona, semilla=semilla)
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.marcar_limpiado(cuarto)
    m.entrar(m.cuarto_final)
    return m


def _resolver(partida, zona, *pasos):
    m = _mazmorra_lista(zona)
    terminal = TerminalDecision(partida.fabrica_arbol(zona)(), 15.0)
    terminal.iniciar()
    for paso in pasos:
        terminal.navegar(paso)
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    return terminal


def test_detonacion_en_medios_propaga_y_pesa_segun_alcance():
    partida = Partida()
    campania = partida.campania
    campania.semilla = 5
    campania.reiniciar()
    terminal = _resolver(partida, ZONA_EMPRESA_MEDIOS, DERECHA, CONFIRMAR, CONFIRMAR)  # Compartir
    assert terminal.resultado == DETONACION
    propagacion = campania.ultima_propagacion
    assert propagacion is not None and propagacion.tipo == RUMOR and propagacion.origen == "fabio"
    base = campania.ultima_consecuencia.efectos["desinformacion"]
    assert campania.ultimos_deltas["desinformacion"] == base + propagacion.total
    assert campania.correccion_reciente() is None
    assert campania.resumen()["expuestos"] == propagacion.total


def test_purificacion_con_publicacion_falsa_publica_correccion():
    partida = Partida()
    campania = partida.campania
    campania.semilla = 5
    campania.reiniciar()
    for _ in range(3):
        campania.revelar_evidencia(ZONA_EMPRESA_MEDIOS)
    terminal = _resolver(partida, ZONA_EMPRESA_MEDIOS, CONFIRMAR, CONFIRMAR, CONFIRMAR)
    assert terminal.resultado == PURIFICACION_EXITOSA
    correccion = campania.correccion_reciente()
    assert correccion is not None and correccion.origen == "fabio"
    assert set(correccion.alcanzados) <= set(campania.red.corregidos)
    assert campania.ultimos_deltas["informacion_verificada"] >= campania.ultima_consecuencia.efectos["informacion_verificada"]


def test_publicacion_verdadera_compartida_no_expone_a_nadie_a_un_rumor():
    partida = Partida()
    campania = partida.campania
    campania.semilla = 5
    campania.reiniciar()
    for _ in range(3):
        campania.revelar_evidencia(ZONA_HOSPITAL)
    _resolver(partida, ZONA_HOSPITAL, CONFIRMAR, CONFIRMAR, CONFIRMAR)
    assert campania.ultima_propagacion.origen == "elena"
    assert campania.resumen()["expuestos"] == 0 and campania.resumen()["corregidos"] > 0


def test_ocultar_una_publicacion_verdadera_propaga_la_version_de_que_era_mentira():
    partida = Partida()
    campania = partida.campania
    campania.semilla = 5
    campania.reiniciar()
    # Reportar -> Reportar el pedido como falso.
    _resolver(partida, ZONA_HOSPITAL, DERECHA, DERECHA, CONFIRMAR, DERECHA, CONFIRMAR, CONFIRMAR)
    assert campania.ultima_consecuencia.camino[-1] == "Reportar el pedido como falso"
    assert campania.ultima_propagacion.tipo == RUMOR and campania.resumen()["expuestos"] > 0


def test_la_reputacion_decide_hasta_donde_llega_la_correccion():
    partida = Partida()
    campania = partida.campania
    assert campania.saltos_correccion(0) == 3
    campania.rep(0).valor = 70
    assert campania.saltos_correccion(0) == 4
    campania.rep(0).valor = -30
    assert campania.saltos_correccion(0) == 2
    campania.rep(0).valor = -70
    assert campania.saltos_correccion(0) == 1


def test_matices_por_rol():
    # Periodista: una evidencia al entrar.
    p = Partida()
    p.campania.establecer_rol("periodista")
    assert p.campania.al_entrar_zona(ZONA_COLEGIO)["id"] == "col_e1"
    assert p.campania.al_entrar_zona(ZONA_COLEGIO) is None
    q = Partida()
    assert q.campania.al_entrar_zona(ZONA_COLEGIO) is None
    # Candidato: la penalización reputacional pesa más.
    normal = Partida()
    normal.campania.semilla = 3
    normal.campania.reiniciar()
    _resolver(normal, ZONA_COLEGIO, DERECHA, CONFIRMAR, CONFIRMAR)  # Compartir
    c = Partida()
    c.campania.semilla = 3
    c.campania.reiniciar()
    c.campania.establecer_rol("candidato")
    _resolver(c, ZONA_COLEGIO, DERECHA, CONFIRMAR, CONFIRMAR)
    assert c.campania.reputacion < normal.campania.reputacion < REPUTACION_INICIAL
    # Ciudadano: confianza extra en cada éxito.
    for rol, esperado in (("ciudadano", 8 + 2), ("influencer", 8)):
        z = Partida()
        z.campania.establecer_rol(rol)
        for _ in range(3):
            z.campania.revelar_evidencia(ZONA_COLEGIO)
        _resolver(z, ZONA_COLEGIO, CONFIRMAR, CONFIRMAR, CONFIRMAR)
        assert z.campania.ultimos_deltas["confianza"] == esperado
    # Influencer: rebote extra al detonar una zona que propaga.
    i = Partida()
    i.campania.establecer_rol("influencer")
    i.campania.semilla = 1
    i.campania.reiniciar()
    _resolver(i, ZONA_EMPRESA_MEDIOS, DERECHA, CONFIRMAR, CONFIRMAR)
    assert i.campania.ultima_propagacion.probabilidad_extra > 0


# ----------------------------------------------------------------------
# Eventos aleatorios
# ----------------------------------------------------------------------


def test_eventos_con_semilla_y_requisitos(datos):
    eventos = datos["eventos"]
    sin_detonar = [sortear_evento(eventos, random.Random(s), None, False).id for s in range(30)]
    assert "rumor_reactivado" not in sin_detonar and len(set(sin_detonar)) >= 2
    con_detonar = [sortear_evento(eventos, random.Random(s), None, True).id for s in range(60)]
    assert "rumor_reactivado" in con_detonar
    assert sortear_evento(eventos, random.Random(4), None, True).id == sortear_evento(eventos, random.Random(4), None, True).id
    assert sortear_evento([], random.Random(0)) is None


def test_evento_propaga_por_la_red_y_la_campania_lo_aplica_una_vez(datos):
    campania = Campania(datos, semilla=11)
    antes = campania.estado.como_dict()
    evento = campania.sortear_evento()
    assert evento is not None and evento.id in {e["id"] for e in datos["eventos"]}
    despues = campania.estado.como_dict()
    assert despues != antes or evento.efectos == {} or all(v == 0 for v in evento.efectos.values())
    assert campania.titulares()[0].startswith("Civitas: ")
    assert len(campania.eventos_ocurridos) == 1
    if evento.propagacion is not None:
        assert evento.propagacion.total >= 1 and "llegó a" in evento.titular


def test_titulares_de_la_partida_incluyen_los_eventos():
    partida = Partida()
    partida.campania.semilla = 2
    partida.campania.reiniciar()
    partida.campania.sortear_evento()
    assert partida.titulares()[0].startswith("Civitas: ")
    partida.reiniciar()
    assert not partida.titulares()[0].startswith("Civitas: ")
