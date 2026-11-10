"""Medición de la paleta de una imagen (lógica pura, sin Pygame).

Sirve para comprobar que Ciudad Nova se ve sobria: pocos píxeles de neón
saturado y pocas familias de color dominantes. Trabaja sobre tuplas
(r, g, b) de 0 a 255; quien llama decide cuántos píxeles muestrea.

    es_saturado(rgb)              -> True si el píxel es un acento de neón
                                     (saturación y brillo altos)
    familia(rgb)                  -> "neutro" o el sector de tono (cada 30°) del píxel
    medir(pixeles)                -> {"fraccion_saturada", "familias", "dominantes"}

Umbrales en src/core/balance.py (UMBRAL_SATURACION_ALTA, UMBRAL_BRILLO_SATURADO,
UMBRAL_SATURACION_COLOR, FRACCION_FAMILIA_DOMINANTE).
"""

import colorsys

from src.core.balance import (
    FRACCION_FAMILIA_DOMINANTE,
    UMBRAL_BRILLO_SATURADO,
    UMBRAL_SATURACION_ALTA,
    UMBRAL_SATURACION_COLOR,
)

NOMBRES_TONO = ("rojo", "naranja", "amarillo", "lima", "verde", "verde_agua", "cian", "azul_cielo", "azul",
                "violeta", "magenta", "rosa")
NEUTRO = "neutro"


def _hsv(rgb):
    r, g, b = rgb
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def es_saturado(rgb):
    _, s, v = _hsv(rgb)
    return s >= UMBRAL_SATURACION_ALTA and v >= UMBRAL_BRILLO_SATURADO


def familia(rgb):
    """Familia de color: "neutro" si casi no tiene saturación (grises,
    negros, azul-gris nocturno muy apagado), si no el sector de tono."""
    h, s, v = _hsv(rgb)
    if s < UMBRAL_SATURACION_COLOR or v < 0.12:
        return NEUTRO
    return NOMBRES_TONO[int((h * 360 + 15) % 360 // 30)]


def medir(pixeles):
    """Fracción de píxeles saturados, cuenta por familia y familias
    dominantes (las que pasan FRACCION_FAMILIA_DOMINANTE del total)."""
    total = saturados = 0
    familias = {}
    for rgb in pixeles:
        total += 1
        saturados += es_saturado(rgb)
        nombre = familia(rgb)
        familias[nombre] = familias.get(nombre, 0) + 1
    if total == 0:
        return {"fraccion_saturada": 0.0, "familias": {}, "dominantes": []}
    fracciones = {nombre: cuenta / total for nombre, cuenta in familias.items()}
    dominantes = sorted((n for n, f in fracciones.items() if f >= FRACCION_FAMILIA_DOMINANTE),
                        key=lambda n: -fracciones[n])
    return {"fraccion_saturada": saturados / total, "familias": fracciones, "dominantes": dominantes}
