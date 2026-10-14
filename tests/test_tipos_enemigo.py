"""Tests de composicion_cuarto: qué tipos de enemigo aparecen según el
tramo de toxicidad (sin pygame)."""

import os
import random
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    MAX_CURANDEROS_ALTA,
    MAX_CURANDEROS_MEDIA,
    MIN_CURANDEROS_FINAL_ALTA,
    MIN_TIRADORES_FINAL_ALTA,
    PROB_CURANDERO_MEDIA,
    STATS_TIPO_ENEMIGO,
)
from src.dungeon.clasificador_toxicidad import (  # noqa: E402
    DIFICULTAD_ALTA,
    DIFICULTAD_BAJA,
    DIFICULTAD_MEDIA,
)
from src.entities.tipos_enemigo import (  # noqa: E402
    CONFIG_TIPO,
    TRAMO_ALTO,
    TRAMO_BAJO,
    TRAMO_MEDIO,
    TipoEnemigo,
    composicion_cuarto,
    tramo_de,
)

P, T, C = TipoEnemigo.PERSEGUIDOR, TipoEnemigo.TIRADOR, TipoEnemigo.CURANDERO
SEMILLAS = range(300)
DIFICULTADES = [DIFICULTAD_BAJA, DIFICULTAD_MEDIA, DIFICULTAD_ALTA]


def comp(dificultad, final=False, semilla=0, inicial=False):
    return Counter(composicion_cuarto(dificultad, final, random.Random(semilla), es_cuarto_inicial=inicial))


def test_config_de_cada_tipo_sale_de_balance():
    assert set(CONFIG_TIPO) == set(TipoEnemigo)
    for tipo, stats in CONFIG_TIPO.items():
        assert stats is STATS_TIPO_ENEMIGO[tipo.value]
    assert CONFIG_TIPO[P].velocidad_mult == 1.15
    assert CONFIG_TIPO[T].velocidad_mult == 0.8
    assert CONFIG_TIPO[C].velocidad_mult == 0.7


def test_tramo_de_cada_dificultad():
    assert tramo_de(DIFICULTAD_BAJA) == TRAMO_BAJO
    assert tramo_de(DIFICULTAD_MEDIA) == TRAMO_MEDIO
    assert tramo_de(DIFICULTAD_ALTA) == TRAMO_ALTO


@pytest.mark.parametrize("dificultad", DIFICULTADES)
@pytest.mark.parametrize("final", [False, True])
@pytest.mark.parametrize("inicial", [False, True])
def test_suma_la_cantidad_base_y_siempre_hay_un_no_curandero(dificultad, final, inicial):
    for semilla in SEMILLAS:
        tipos = comp(dificultad, final, semilla, inicial)
        assert sum(tipos.values()) == dificultad["cantidad_enemigos"]
        assert tipos[P] + tipos[T] >= 1
        assert tipos[C] <= tipos[P] + tipos[T]


def test_la_misma_semilla_da_la_misma_composicion():
    for dificultad in DIFICULTADES:
        for semilla in range(30):
            assert comp(dificultad, True, semilla) == comp(dificultad, True, semilla)


def test_orden_perseguidores_tiradores_curanderos():
    for semilla in SEMILLAS:
        tipos = composicion_cuarto(DIFICULTAD_ALTA, True, random.Random(semilla))
        orden = [list(TipoEnemigo).index(t) for t in tipos]
        assert orden == sorted(orden)


def test_cuarto_vacio():
    assert composicion_cuarto({"cantidad_enemigos": 0, "multiplicador_velocidad": 1.0}, False, random.Random()) == []


# ----------------------------------------------------------------------
# Por tramo
# ----------------------------------------------------------------------

def test_baja_solo_perseguidores_en_cuartos_normales():
    for semilla in SEMILLAS:
        assert comp(DIFICULTAD_BAJA, False, semilla) == Counter({P: 2})


def test_baja_el_final_puede_traer_un_tirador():
    vistos = {comp(DIFICULTAD_BAJA, True, s)[T] for s in SEMILLAS}
    assert vistos == {0, 1}
    for semilla in SEMILLAS:
        assert comp(DIFICULTAD_BAJA, True, semilla)[C] == 0


def test_media_60_40_y_a_veces_un_curandero():
    con_curandero = 0
    for semilla in SEMILLAS:
        tipos = comp(DIFICULTAD_MEDIA, False, semilla)
        assert tipos[C] <= MAX_CURANDEROS_MEDIA
        con_curandero += tipos[C]
        if tipos[C] == 0:
            assert tipos == Counter({P: 2, T: 1})  # ~60 % / ~40 %
        else:
            assert tipos == Counter({P: 1, T: 1, C: 1})
    frecuencia = con_curandero / len(SEMILLAS)
    assert abs(frecuencia - PROB_CURANDERO_MEDIA) < 0.08


def test_alta_40_40_20_con_maximo_de_curanderos():
    vistos = set()
    for semilla in SEMILLAS:
        tipos = comp(DIFICULTAD_ALTA, False, semilla)
        assert tipos[T] == 2  # 40 %
        assert 1 <= tipos[C] <= MAX_CURANDEROS_ALTA  # ~20 %, a veces 2
        assert tipos[C] <= tipos[P] + tipos[T]
        vistos.add(tipos[C])
    assert vistos == {1, 2}


def test_final_alta_garantiza_curandero_y_dos_tiradores():
    for semilla in SEMILLAS:
        tipos = comp(DIFICULTAD_ALTA, True, semilla)
        assert tipos[C] >= MIN_CURANDEROS_FINAL_ALTA
        assert tipos[T] >= MIN_TIRADORES_FINAL_ALTA


@pytest.mark.parametrize("dificultad", DIFICULTADES)
def test_cuarto_inicial_nunca_tiene_curanderos(dificultad):
    for semilla in SEMILLAS:
        assert comp(dificultad, False, semilla, inicial=True)[C] == 0


def test_tipos_enemigo_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = (
        "import sys, src.entities.tipos_enemigo, src.ai.nodos_combate, src.dungeon.spawn,"
        " src.dungeon.gracia_entrada, src.ui.ruta_sprites;"
        "print('pygame' in sys.modules)"
    )
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"
