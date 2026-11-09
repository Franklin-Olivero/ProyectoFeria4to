"""Pantalla de instrucciones de mazmorra (lógica pura, sin Pygame)."""

import random

from src.core import textos_enemigos
from src.core.balance import RETARDO_INSTRUCCIONES
from src.core.preferencias import INSTRUCCIONES_PRIMERA_VEZ, INSTRUCCIONES_SIEMPRE
from src.dungeon import arena_jefe
from src.dungeon.clasificador_toxicidad import nivel_a_dificultad
from src.entities.tipos_enemigo import TipoEnemigo, composicion_cuarto
from src.ui.instrucciones import (
    ENEMIGO,
    JEFE,
    REGLAS_CUARTO,
    REGLAS_JEFE,
    TIPO_JEFE,
    InstruccionesMazmorra,
    claves_vistas,
    debe_mostrarse,
    tarjetas_jefe,
    tipos_de_mazmorra,
)
from src.ui.navegacion import CONFIRMAR, DERECHA, IZQUIERDA


def _tipos_generados(nivel, semillas=300):
    """Todos los tipos que composicion_cuarto genera de verdad para ese nivel."""
    dificultad = nivel_a_dificultad(nivel)
    vistos = set()
    for semilla in range(semillas):
        for es_final in (False, True):
            for es_inicial in (False, True):
                vistos.update(composicion_cuarto(dificultad, es_final, random.Random(semilla), es_inicial))
    return vistos


def test_los_tipos_mostrados_coinciden_con_la_composicion():
    for nivel in range(0, 101, 5):
        assert set(tipos_de_mazmorra(nivel)) == _tipos_generados(nivel), nivel


def test_cada_tipo_aparece_una_sola_vez_y_hay_reglas():
    for nivel in (10, 50, 90):
        tarjetas = InstruccionesMazmorra.para_mazmorra("Colegio", nivel).tarjetas
        tipos = [t.tipo for t in tarjetas if t.clase == ENEMIGO]
        assert len(tipos) == len(set(tipos))
        assert tarjetas[-1].clase == REGLAS_CUARTO


def test_el_jefe_incluye_sus_subditos():
    tarjetas = tarjetas_jefe()
    tipos = {t.tipo for t in tarjetas if t.clase == ENEMIGO}
    assert tipos == set(arena_jefe.TIPOS_SUBDITOS)
    clases = [t.clase for t in tarjetas]
    assert JEFE in clases and clases[-1] == REGLAS_JEFE
    jefe = InstruccionesMazmorra.para_jefe(100.0)
    assert jefe.es_jefe and jefe.dificultad == "Máxima"


def test_hay_texto_para_cada_tipo_de_enemigo():
    for tipo in TipoEnemigo:
        ficha = textos_enemigos.ficha(tipo)
        assert ficha.nombre and ficha.que_hace and ficha.comportamiento and ficha.consejo
        assert 1 <= ficha.amenaza <= textos_enemigos.AMENAZA_MAXIMA
    assert textos_enemigos.FICHA_JEFE.amenaza == textos_enemigos.AMENAZA_MAXIMA
    assert len(textos_enemigos.REGLAS_CUARTO) == 2 and len(textos_enemigos.REGLAS_JEFE) == 2


def test_retardo_anti_salto():
    inst = InstruccionesMazmorra.para_mazmorra("Hospital", 50)
    assert not inst.puede_comenzar
    assert inst.accion(CONFIRMAR) is None and not inst.comenzada  # el Enter de la puerta no la salta
    inst.actualizar(RETARDO_INSTRUCCIONES / 2)
    assert inst.accion(CONFIRMAR) is None and not inst.comenzada
    inst.actualizar(RETARDO_INSTRUCCIONES / 2)
    assert inst.puede_comenzar
    assert inst.accion(CONFIRMAR) is not None and inst.comenzada


def test_actualizar_solo_corre_su_propio_reloj():
    inst = InstruccionesMazmorra.para_mazmorra("Hospital", 90)
    antes = (list(inst.tarjetas), inst.pagina, inst.comenzada)
    for _ in range(600):
        inst.actualizar(1 / 60)
    assert (list(inst.tarjetas), inst.pagina, inst.comenzada) == antes
    assert abs(inst.tiempo - 10.0) < 1e-6


def test_paginacion():
    inst = InstruccionesMazmorra("X", 90, "Alta", tarjetas_jefe() * 2, por_pagina=4)
    assert inst.paginas == 2 and len(inst.tarjetas_visibles()) == 4
    assert inst.accion(IZQUIERDA) is None  # ya en la primera
    assert inst.accion(DERECHA) is not None and inst.pagina == 1
    assert inst.tarjetas_visibles() == inst.tarjetas[4:8]
    assert inst.accion(DERECHA) is None and inst.pagina == 1
    una = InstruccionesMazmorra.para_mazmorra("Colegio", 10)
    assert una.paginas == 1 and una.accion(DERECHA) is None


def test_debe_mostrarse_segun_la_preferencia():
    tarjetas = tarjetas_jefe()
    claves = claves_vistas(tarjetas)
    assert TIPO_JEFE in claves and TipoEnemigo.TIRADOR in claves
    assert debe_mostrarse(INSTRUCCIONES_SIEMPRE, tarjetas, claves)
    assert debe_mostrarse(INSTRUCCIONES_PRIMERA_VEZ, tarjetas, set())
    assert not debe_mostrarse(INSTRUCCIONES_PRIMERA_VEZ, tarjetas, claves)
    # Un tipo nuevo vuelve a mostrarla.
    assert debe_mostrarse(INSTRUCCIONES_PRIMERA_VEZ, tarjetas, claves - {TipoEnemigo.TIRADOR})
