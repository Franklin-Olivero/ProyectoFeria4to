"""Tests de la mazmorra multi-cuarto sobre el Grafo (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    PROPAGACION_INCREMENTO,
    PROPAGACION_INTERVALO,
    REPORTES_POR_ZONA,
    TOXICIDAD_MAXIMA_CUARTO,
    ZONA_HOSPITAL,
)
from src.dungeon.clasificador_toxicidad import nivel_a_dificultad  # noqa: E402
from src.dungeon.mazmorra import DESPLAZAMIENTOS, OPUESTA, Mazmorra  # noqa: E402

REPORTES = REPORTES_POR_ZONA[ZONA_HOSPITAL]  # nivel 50.0
SEMILLAS = range(40)


def crear(semilla=0, cantidad=6):
    return Mazmorra(REPORTES, ZONA_HOSPITAL, cantidad_cuartos=cantidad, semilla=semilla)


def aristas(mazmorra):
    g = mazmorra.grafo
    return {(a, b) for a in g.nodos() for b in g.vecinos(a) if a < b}


def test_misma_semilla_da_el_mismo_layout():
    for semilla in SEMILLAS:
        a, b = crear(semilla), crear(semilla)
        assert a.celdas == b.celdas
        assert aristas(a) == aristas(b)
        assert a.cuarto_final == b.cuarto_final


def test_semillas_distintas_dan_layouts_distintos():
    layouts = {tuple(sorted(crear(s).celdas.values())) for s in SEMILLAS}
    assert len(layouts) > 1


@pytest.mark.parametrize("cantidad", range(2, 10))
def test_siempre_conexo_con_cantidad_cuartos_nodos(cantidad):
    for semilla in SEMILLAS:
        m = crear(semilla, cantidad)
        assert len(m.grafo) == cantidad
        assert m.grafo.es_conexo()
        assert len(set(m.celdas.values())) == cantidad  # una celda por cuarto
        # Árbol del DFS (V - 1 aristas) + a lo sumo 1 arista extra.
        assert len(aristas(m)) in (cantidad - 1, cantidad)


def test_cantidad_fuera_de_rango_lanza_error():
    with pytest.raises(ValueError):
        crear(cantidad=1)
    with pytest.raises(ValueError):
        crear(cantidad=10)


def test_agrega_arista_extra_cuando_hay_vecinas_sin_pasillo():
    for semilla in SEMILLAS:
        m = crear(semilla, 9)  # cuadrícula llena: siempre hay pares vecinos libres
        assert len(aristas(m)) == 9


def test_puertas_solo_donde_hay_arista_y_entre_celdas_vecinas():
    for semilla in SEMILLAS:
        m = crear(semilla)
        for cuarto in m.grafo.nodos():
            puertas = m.puertas(cuarto)
            assert sorted(puertas.values()) == sorted(m.grafo.vecinos(cuarto))
            x, y = m.celdas[cuarto]
            for direccion, vecino in puertas.items():
                dx, dy = DESPLAZAMIENTOS[direccion]
                assert m.celdas[vecino] == (x + dx, y + dy)
                assert m.puertas(vecino)[OPUESTA[direccion]] == cuarto


def test_cuarto_final_es_el_mas_lejano_por_bfs_con_desempate_por_id():
    for semilla in SEMILLAS:
        m = crear(semilla)
        _, distancias, _ = m.grafo.bfs(m.entrada)
        maxima = max(distancias.values())
        assert distancias[m.cuarto_final] == maxima
        assert m.cuarto_final == min(c for c, d in distancias.items() if d == maxima)
        assert m.cuarto_final != m.entrada


def test_entrada_empieza_sin_enemigos_y_es_el_cuarto_actual():
    m = crear()
    assert m.actual == m.entrada == 0
    assert m.dificultad[m.entrada]["cantidad_enemigos"] == 0
    assert m.entrada in m.limpiados and m.entrada in m.visitados
    assert m.esta_generado(m.entrada)
    assert not any(m.esta_generado(c) for c in m.grafo.nodos() if c != m.entrada)


def test_cuarto_se_genera_al_entrar_con_su_toxicidad_local():
    m = crear()
    direccion, vecino = next(iter(m.puertas(m.entrada).items()))
    m.toxicidad[vecino] = 90.0
    assert m.mover(direccion) == vecino
    assert m.actual == vecino
    assert m.dificultad[vecino] == nivel_a_dificultad(90.0)
    # Cambiar la toxicidad después no regenera el cuarto.
    m.toxicidad[vecino] = 0.0
    m.entrar(vecino)
    assert m.dificultad[vecino] == nivel_a_dificultad(90.0)


def test_mover_sin_pasillo_no_hace_nada():
    for semilla in SEMILLAS:
        m = crear(semilla)
        sin_puerta = [d for d in DESPLAZAMIENTOS if d not in m.puertas(m.entrada)]
        for direccion in sin_puerta:
            assert m.mover(direccion) is None
            assert m.actual == m.entrada


def test_toxicidad_inicial_es_el_nivel_de_la_zona():
    m = crear()
    assert m.nivel_zona == pytest.approx(50.0)
    assert all(t == pytest.approx(50.0) for t in m.toxicidad.values())


def test_propagacion_suma_incremento_sobre_distancia_solo_a_no_generados():
    for semilla in SEMILLAS:
        m = crear(semilla)
        direccion = next(iter(m.puertas(m.entrada)))
        m.mover(direccion)  # ahora hay 2 cuartos generados
        antes = dict(m.toxicidad)
        _, distancias, _ = m.grafo.bfs(m.actual)

        m.actualizar(PROPAGACION_INTERVALO, hay_enemigos_vivos=True)

        for cuarto, d in distancias.items():
            if m.esta_generado(cuarto):
                assert m.toxicidad[cuarto] == antes[cuarto]
            else:
                assert m.toxicidad[cuarto] == pytest.approx(
                    antes[cuarto] + PROPAGACION_INCREMENTO / d
                )


def test_sin_enemigos_vivos_no_hay_propagacion_ni_se_acumula_tiempo():
    m = crear()
    antes = dict(m.toxicidad)
    m.actualizar(PROPAGACION_INTERVALO * 3, hay_enemigos_vivos=False)
    assert m.toxicidad == antes
    assert m.tiempo_en_cuarto == 0.0


def test_propagacion_espera_el_intervalo_completo_y_conserva_el_sobrante():
    m = crear()
    antes = dict(m.toxicidad)
    m.actualizar(PROPAGACION_INTERVALO - 0.5, True)
    assert m.toxicidad == antes
    m.actualizar(1.0, True)
    assert m.toxicidad != antes
    assert m.tiempo_en_cuarto == pytest.approx(0.5)


def test_propagacion_no_pasa_del_tope():
    m = crear()
    for _ in range(50):
        m.propagar_desde(m.actual)
    assert max(m.toxicidad.values()) == TOXICIDAD_MAXIMA_CUARTO
    m2 = crear()
    vecino = m2.grafo.vecinos(m2.entrada)[0]
    m2.toxicidad[vecino] = TOXICIDAD_MAXIMA_CUARTO - 1
    m2.propagar_desde(m2.entrada)
    assert m2.toxicidad[vecino] == TOXICIDAD_MAXIMA_CUARTO


def test_ruta_al_final_es_el_camino_bfs_mas_corto():
    for semilla in SEMILLAS:
        m = crear(semilla)
        ruta = m.ruta_al_final()
        _, distancias, _ = m.grafo.bfs(m.actual)
        assert ruta[0] == m.actual and ruta[-1] == m.cuarto_final
        assert len(ruta) - 1 == distancias[m.cuarto_final]
        for a, b in zip(ruta, ruta[1:]):
            assert m.grafo.existe_arista(a, b)


def test_final_descubierto_solo_al_visitarlo():
    m = crear()
    assert not m.final_descubierto
    m.entrar(m.cuarto_final)
    assert m.final_descubierto
