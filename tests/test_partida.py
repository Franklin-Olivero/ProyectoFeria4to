"""Tests de la partida: entrar a los edificios, decisión, barricadas y derrota global (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.core.balance import (  # noqa: E402
    CRUCE_ESTE,
    CRUCE_NORTE,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_PLAZA,
)
from src.core.escenas import Escena, escena_tras_colapso  # noqa: E402
from src.dungeon import ciudad_mapa  # noqa: E402
from src.dungeon.grafo_ciudad import PESOS_INICIALES_CIUDAD  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.ui.mapa_ciudad import SelectorZona  # noqa: E402
from src.ui.terminal_decision import (  # noqa: E402
    DERECHA,
    DETONACION,
    IZQUIERDA,
    PURIFICACION_EXITOSA,
)


def test_partida_nueva_empieza_en_la_plaza_sin_colapso():
    partida = Partida()
    assert partida.ubicacion == ZONA_PLAZA
    assert partida.colapso.valor == 0.0
    assert partida.progreso.mazmorras_completadas == 0
    assert not partida.alcaldia_desbloqueada()


def test_partida_nueva_aparece_en_la_plaza():
    partida = Partida()
    assert partida.posicion_aparicion() == ciudad_mapa.centro_casilla(*ciudad_mapa.SPAWN)
    assert not partida.es_solida(*ciudad_mapa.SPAWN)


def test_entrar_es_gratis_y_se_reaparece_frente_a_esa_puerta():
    partida = Partida()
    partida.entrar(ZONA_EMPRESA_MEDIOS)
    assert partida.colapso.valor == 0.0
    assert partida.ubicacion == ZONA_EMPRESA_MEDIOS
    assert partida.posicion_aparicion() == ciudad_mapa.posicion_aparicion(ZONA_EMPRESA_MEDIOS)


def test_ruta_sugerida_desde_la_posicion_del_jugador():
    partida = Partida()
    posicion = ciudad_mapa.centro_casilla(*ciudad_mapa.SPAWN)
    nodos, costo = partida.ruta_sugerida(posicion, ZONA_COLEGIO)
    assert nodos == [ZONA_PLAZA, CRUCE_NORTE, ZONA_COLEGIO] and costo == 6


def test_decision_aplica_colapso_progreso_y_pesos_de_la_zona():
    partida = Partida()
    partida.registrar_decision(ZONA_COLEGIO, PURIFICACION_EXITOSA)
    assert partida.progreso.mazmorras_completadas == 1
    assert partida.ciudad.grafo.peso(CRUCE_NORTE, ZONA_COLEGIO) == 1
    assert partida.alcaldia_desbloqueada()

    partida.registrar_decision(ZONA_EMPRESA_MEDIOS, DETONACION)
    assert partida.progreso.mazmorras_completadas == 1
    assert partida.ciudad.grafo.peso(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE) == 8
    assert partida.ciudad.esta_bloqueada(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE)
    # La barricada es física: sus casillas son sólidas para el jugador.
    seccion = ciudad_mapa.tramo(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE).seccion
    assert all(partida.es_solida(*casilla) for casilla in seccion)


def test_colapso_en_100_activa_la_escena_de_derrota():
    partida = Partida()
    assert escena_tras_colapso(Escena.MAZMORRA, partida.colapso) == Escena.MAZMORRA
    partida.colapso.valor = 100.0
    assert partida.hay_derrota_global()
    for escena in (Escena.CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE):
        assert escena_tras_colapso(escena, partida.colapso) == Escena.DERROTA


def test_colapso_justo_bajo_100_no_es_derrota():
    partida = Partida()
    partida.colapso.valor = 99.9
    assert escena_tras_colapso(Escena.CIUDAD, partida.colapso) == Escena.CIUDAD


def test_una_detonacion_puede_llevar_el_colapso_al_100():
    partida = Partida()
    partida.colapso.valor = 99.9
    partida.registrar_decision(ZONA_COLEGIO, DETONACION)
    assert partida.colapso.valor == 100.0
    assert escena_tras_colapso(Escena.CIUDAD, partida.colapso) == Escena.DERROTA


def test_sumar_fallos_hasta_el_100_tolera_el_error_de_float():
    partida = Partida()
    partida.colapso.valor = 99.0
    for _ in range(5):
        partida.colapso.sumar_fallo()  # 99.0 + 5 * 0.2 puede quedar en 99.999...
    assert partida.hay_derrota_global()


def test_reinicio_deja_todo_en_estado_inicial():
    partida = Partida()
    partida.entrar(ZONA_COLEGIO)
    partida.registrar_decision(ZONA_COLEGIO, DETONACION)
    partida.registrar_decision(ZONA_EMPRESA_MEDIOS, DETONACION)
    partida.registrar_decision(ZONA_COLEGIO, PURIFICACION_EXITOSA)
    assert partida.ciudad.bloqueadas
    partida.colapso.valor = 100.0

    partida.reiniciar()

    assert partida.colapso.valor == 0.0
    assert not partida.hay_derrota_global()
    assert partida.progreso.mazmorras_completadas == 0
    assert partida.ubicacion == ZONA_PLAZA
    assert partida.posicion_aparicion() == ciudad_mapa.centro_casilla(*ciudad_mapa.SPAWN)
    for a, b, peso in PESOS_INICIALES_CIUDAD:
        assert partida.ciudad.grafo.peso(a, b) == peso
    assert not partida.ciudad.bloqueadas
    # Solo quedan las barricadas de la Alcaldía (sellada de nuevo).
    assert partida.barricadas_activas() == ciudad_mapa.BARRICADAS_ALCALDIA
    assert escena_tras_colapso(Escena.CIUDAD, partida.colapso) == Escena.CIUDAD


def test_selector_de_zona_da_la_vuelta():
    selector = SelectorZona(["a", "b", "c"], "a")
    selector.mover(IZQUIERDA)
    assert selector.seleccionada == "c"
    selector.mover(DERECHA)
    selector.mover(DERECHA)
    assert selector.seleccionada == "b"
