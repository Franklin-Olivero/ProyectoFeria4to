"""Estadísticas de los roles en escala 1-10 (lógica pura, sin Pygame).

El lobby no muestra multiplicadores (×0.95, 2.4/s): muestra "Velocidad 7/10".
puntaje_stat lleva un valor real a esa escala, lineal entre el mínimo y
el máximo de esa estadística entre los 4 roles (balance.RANGOS_STATS):
el rol con más saca 10, el que menos 1. En las estadísticas inversas
(Carga: menos kills para llenar la habilidad es mejor) se da vuelta.
Redondeo consistente: al entero más cercano, x.5 sube.
"""

import math

from src.core.balance import ESTADISTICAS_INVERSAS, PUNTAJE_MAXIMO, PUNTAJE_MINIMO, RANGOS_STATS, STATS_POR_ROL


def puntaje_stat(valor, minimo, maximo, inverso=False):
    """Entero en 1..10 de `valor` dentro de [minimo, maximo]."""
    if maximo <= minimo:
        return PUNTAJE_MAXIMO
    fraccion = (valor - minimo) / (maximo - minimo)
    fraccion = max(0.0, min(1.0, fraccion))
    if inverso:
        fraccion = 1.0 - fraccion
    return PUNTAJE_MINIMO + math.floor(fraccion * (PUNTAJE_MAXIMO - PUNTAJE_MINIMO) + 0.5)


def puntaje_de(rol, atributo):
    """Puntaje 1-10 de la estadística `atributo` del `rol`."""
    minimo, maximo = RANGOS_STATS[atributo]
    valor = getattr(STATS_POR_ROL[rol], atributo)
    return puntaje_stat(valor, minimo, maximo, atributo in ESTADISTICAS_INVERSAS)


def puntajes(rol):
    """{atributo: puntaje} de todas las estadísticas visibles del rol."""
    return {atributo: puntaje_de(rol, atributo) for atributo in RANGOS_STATS}
