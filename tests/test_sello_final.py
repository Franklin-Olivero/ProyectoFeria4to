"""Tests del sello del cuarto final y del cierre de la mazmorra (sin pygame).

Regla: el cuarto final solo se abre cuando todos los demás cuartos están
limpios (aunque el ciclo del layout le dé dos puertas), y la mazmorra se
completa una sola vez, al resolver la decisión en ese cuarto.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import REPORTES_POR_ZONA, ZONA_HOSPITAL  # noqa: E402
from src.dungeon.mazmorra import OPUESTA, Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.structures.graph import Grafo  # noqa: E402
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA  # noqa: E402

SEMILLAS = range(200)


def crear(semilla=0, cantidad=6):
    return Mazmorra(REPORTES_POR_ZONA[ZONA_HOSPITAL], ZONA_HOSPITAL, cantidad, semilla)


def limpiar_todo_menos_final(m):
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.marcar_limpiado(cuarto)


def es_punto_de_corte(grafo, nodo):
    copia = grafo.copia()
    copia.eliminar_nodo(nodo)
    return not copia.es_conexo()


def semilla_con_dos_puertas_al_final():
    for semilla in range(3000):
        m = crear(semilla)
        if len(m.grafo.vecinos(m.cuarto_final)) >= 2:
            return semilla
    raise AssertionError("ninguna semilla genera un final con dos puertas")


# ----------------------------------------------------------------------
# Garantía de conectividad
# ----------------------------------------------------------------------


def test_copia_del_grafo_es_independiente():
    g = Grafo()
    g.agregar_arista(1, 2, 3)
    c = g.copia()
    c.eliminar_nodo(2)
    assert g.existe_arista(1, 2) and g.peso(1, 2) == 3
    assert 2 not in c


@pytest.mark.parametrize("cantidad", [3, 6, 9])
def test_sin_el_cuarto_final_el_resto_sigue_conexo(cantidad):
    for semilla in SEMILLAS:
        m = crear(semilla, cantidad)
        assert m.resto_conexo_sin(m.cuarto_final)
        assert not es_punto_de_corte(m.grafo, m.cuarto_final)
        assert m.cuarto_final != m.entrada


def test_final_es_el_mas_lejano_que_no_desconecta():
    for semilla in SEMILLAS:
        m = crear(semilla)
        _, distancias, _ = m.grafo.bfs(m.entrada)
        validos = [c for c in distancias if c != m.entrada and m.resto_conexo_sin(c)]
        esperado = min(validos, key=lambda c: (-distancias[c], c))
        assert m.cuarto_final == esperado


# ----------------------------------------------------------------------
# Pendientes y sello
# ----------------------------------------------------------------------


def test_al_inicio_solo_la_entrada_esta_limpia_y_el_final_sellado():
    m = crear()
    assert m.limpiados == {m.entrada}
    pendientes = m.cuartos_pendientes()
    assert sorted(pendientes) == sorted(
        c for c in m.grafo.nodos() if c not in (m.entrada, m.cuarto_final)
    )
    assert not m.final_desbloqueado()
    assert not m.puede_entrar(m.cuarto_final)
    assert all(m.puede_entrar(c) for c in m.grafo.nodos() if c != m.cuarto_final)


def test_cuarto_nunca_visitado_cuenta_como_pendiente():
    m = crear()
    nunca = [c for c in m.grafo.nodos() if c not in m.visitados and c != m.cuarto_final]
    assert nunca
    for cuarto in nunca:
        assert cuarto in m.cuartos_pendientes()


def test_visitar_sin_limpiar_sigue_pendiente():
    m = crear()
    direccion, vecino = next(iter(m.puertas(m.entrada).items()))
    m.mover(direccion)
    assert vecino in m.visitados
    assert vecino in m.cuartos_pendientes()


def test_se_desbloquea_exactamente_al_limpiar_el_ultimo_pendiente():
    for semilla in range(30):
        m = crear(semilla)
        pendientes = m.cuartos_pendientes()
        for cuarto in pendientes[:-1]:
            assert m.marcar_limpiado(cuarto) is False
            assert not m.puede_entrar(m.cuarto_final)
        assert len(m.cuartos_pendientes()) == 1
        assert not m.puede_entrar(m.cuarto_final)
        assert m.marcar_limpiado(pendientes[-1]) is True  # aviso de desbloqueo
        assert m.puede_entrar(m.cuarto_final)
        assert m.marcar_limpiado(pendientes[-1]) is False  # no se repite


def test_ciclo_con_dos_puertas_al_final_ambas_selladas():
    m = crear(semilla_con_dos_puertas_al_final())
    final = m.cuarto_final
    vecinos = m.grafo.vecinos(final)
    assert len(vecinos) >= 2

    def puerta_hacia_final(desde):
        return next(d for d, v in m.puertas(desde).items() if v == final)

    for vecino in vecinos:
        m.entrar(vecino)
        assert m.mover(puerta_hacia_final(vecino)) is None
        assert m.actual == vecino

    limpiar_todo_menos_final(m)
    for vecino in vecinos:
        m.entrar(vecino)
        direccion = puerta_hacia_final(vecino)
        assert m.mover(direccion) == final
        # Se llega por la puerta opuesta del final.
        assert m.puertas(final)[OPUESTA[direccion]] == vecino


# ----------------------------------------------------------------------
# Decisión y cierre
# ----------------------------------------------------------------------


def test_decision_no_se_inicia_con_el_final_sellado():
    m = crear()
    m.entrar(m.cuarto_final)  # llegada forzada, saltándose el sello
    assert not m.final_desbloqueado()
    assert not m.puede_iniciar_decision()
    assert m.completar() is False
    assert not m.completada


def test_decision_solo_en_el_cuarto_final():
    m = crear()
    limpiar_todo_menos_final(m)
    assert not m.puede_iniciar_decision()  # está en la entrada
    m.entrar(m.cuarto_final)
    assert m.puede_iniciar_decision()


@pytest.mark.parametrize("resultado", [PURIFICACION_EXITOSA, DETONACION])
def test_registrar_decision_se_aplica_una_sola_vez(resultado):
    partida = Partida()
    partida.colapso.valor = 50.0
    m = crear()
    limpiar_todo_menos_final(m)
    m.entrar(m.cuarto_final)

    assert partida.cerrar_mazmorra(m, resultado) is True
    colapso, completadas = partida.colapso.valor, partida.progreso.mazmorras_completadas
    pesos = partida.ciudad.calles()

    for _ in range(3):
        assert partida.cerrar_mazmorra(m, resultado) is False
    assert partida.colapso.valor == colapso
    assert partida.progreso.mazmorras_completadas == completadas
    assert partida.ciudad.calles() == pesos
    assert completadas == (1 if resultado == PURIFICACION_EXITOSA else 0)


def test_cerrar_mazmorra_sellada_no_aplica_nada():
    partida = Partida()
    m = crear()
    m.entrar(m.cuarto_final)
    assert partida.cerrar_mazmorra(m, PURIFICACION_EXITOSA) is False
    assert partida.progreso.mazmorras_completadas == 0
    assert partida.colapso.valor == 0.0


def test_hud_cuartos_limpios():
    m = crear()
    assert m.cuartos_limpios() == (1, 6)
    limpiar_todo_menos_final(m)
    assert m.cuartos_limpios() == (5, 6)
    m.entrar(m.cuarto_final)
    m.marcar_limpiado(m.cuarto_final)
    assert m.cuartos_limpios() == (6, 6)
