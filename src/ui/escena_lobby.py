"""Lógica de la escena del lobby del hotel (pura, sin Pygame).

La escena sale de la composición src/dungeon/datos/composiciones/
lobby_hotel.json armada por compositor_interior. Aquí vive lo que se
puede probar sin ventana:

    cargar_plantilla(nombre)           -> plantilla armada (o None si falta algo)
    separar_por_profundidad(objs, y)   -> (detrás, delante) de la línea de los puestos
    es_dinamico(obj)                   -> si se redibuja cada frame (parpadea, anima, reloj)
    brillo(patron, t, semilla)         -> 0..1: cómo está una luz a los t segundos
    angulos_reloj(h, m, s)             -> grados de las manecillas (0 = arriba, horario)
    motas_polvo(cantidad, rect, t)     -> [(x, y, alfa)] en px nativos

Las luces que fallan no usan azar con estado: el brillo es una función del
tiempo (y de una semilla por luz), así dos luces nunca se apagan juntas y
"reducir movimiento" las deja fijas con t = 0.
"""

import json
import math
import os

from src.core import assets
from src.dungeon import compositor_interior

PATRONES = ("zumbido", "falla", "neon")


def cargar_plantilla(nombre=assets.COMPOSICION_LOBBY, raiz="."):
    """Plantilla armada de la composición `nombre`, o None si falta un archivo."""
    try:
        with open(os.path.join(raiz, assets.RUTA_COMPOSICIONES, f"{nombre}.json"), encoding="utf-8") as archivo:
            composicion = json.load(archivo)
        with open(os.path.join(raiz, assets.RUTA_TERRENOS_BACKROOMS), encoding="utf-8") as archivo:
            terrenos = json.load(archivo)
    except (OSError, ValueError):
        return None
    return compositor_interior.componer(composicion, terrenos)


def linea_puestos(plantilla):
    """y nativa (pies) de los puestos: lo que toca el suelo más abajo va delante."""
    return max(y for _, y in plantilla["puestos"])


def es_dinamico(obj):
    return obj["tipo"] == "animacion" or bool(obj.get("parpadeo")) or bool(obj.get("reloj"))


def separar_por_profundidad(objetos, y_corte):
    """Objetos (con su índice) que se dibujan detrás o delante de los
    personajes, cada lista ordenada por la y de su base (orden por Y
    inferior del pack)."""
    con_indice = sorted(enumerate(objetos), key=lambda par: (par[1]["y"], par[0]))
    detras = [(i, o) for i, o in con_indice if o["y"] <= y_corte]
    delante = [(i, o) for i, o in con_indice if o["y"] > y_corte]
    return detras, delante


def _azar(entero, semilla):
    """Hash entero -> [0, 1) (sin estado: el mismo tiempo da lo mismo)."""
    x = (entero * 2654435761 + semilla * 40503 + 12345) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    return x / 2 ** 32


def brillo(patron, t, semilla=0):
    """Brillo 0..1 de una luz con ese patrón:
    "zumbido": casi siempre prendida; de vez en cuando un corte cortito.
    "falla": tartamudea seguido y cada ~7 s se apaga un momento.
    "neon": late suave y cada ~5 s hace un doble parpadeo."""
    if patron is None or t <= 0:
        return 1.0
    corte = assets.DURACION_PARPADEO_LOBBY
    tramo = int(t / corte)
    if patron == "zumbido":
        return 0.25 if _azar(tramo, semilla) < 0.015 else 1.0
    if patron == "falla":
        if (t + semilla * 1.3) % 7.0 < 0.45:
            return 0.0
        return 0.15 if _azar(tramo, semilla) < 0.12 else 1.0
    if patron == "neon":
        fase = (t + semilla * 0.7) % 5.0
        if fase < 0.08 or 0.16 < fase < 0.24:
            return 0.2
        return 0.9 + 0.1 * math.sin(t * 9.0 + semilla)
    raise ValueError(f"patrón de parpadeo desconocido: {patron!r}")


def angulos_reloj(hora, minuto, segundo):
    """(horas, minutos, segundos) en grados, 0 = las 12 y en sentido horario."""
    return ((hora % 12 + minuto / 60) * 30.0, (minuto + segundo / 60) * 6.0, segundo * 6.0)


def punta_manecilla(centro, grados, largo):
    """Punto final de una manecilla (y crece hacia abajo, como en pantalla)."""
    radianes = math.radians(grados)
    return (centro[0] + largo * math.sin(radianes), centro[1] - largo * math.cos(radianes))


def motas_polvo(cantidad, rect, t):
    """Motas que flotan y bajan muy despacio dentro de `rect` (px nativos),
    cada una con su alfa que respira."""
    x0, y0, ancho, alto = rect
    motas = []
    for i in range(cantidad):
        velocidad = 1.5 + (i * 7) % 5 * 0.6
        x = x0 + (i * 73) % ancho + 5 * math.sin(t * 0.35 + i * 1.7)
        y = y0 + ((i * 41) % alto + t * velocidad) % alto
        alfa = round(70 + 60 * (0.5 + 0.5 * math.sin(t * 0.9 + i)))
        motas.append((x, y, alfa))
    return motas
