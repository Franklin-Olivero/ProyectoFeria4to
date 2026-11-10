"""La sala de espera del modo Online como un salón del hotel Backrooms (lógica pura).

Online/datos/sala_hotel.json describe el salón con rectángulos, en el mismo
formato que las composiciones del lobby del hotel (src/dungeon/
compositor_interior.py), y marca en cada objeto qué es: "rol": "recepcion"
(ahí se elige el rol), "rol": "vestidor" (los cuatro carritos de equipaje
abren el vestidor) y "obstaculo": true (no se camina a través). Aquí todo eso
se pasa a px de pantalla para Online/lobby.py; el dibujo está en
Online/sala_hotel_render.py. Sin pygame, para probarse en aislado.

    cargar_composicion()      -> dict de la composición (o None si falta)
    plantilla()               -> plantilla armada por el compositor (o None)
    disposicion(composicion)  -> Disposicion en px de pantalla
"""

import json
import os
from dataclasses import dataclass

from src.core import assets
from src.dungeon import compositor_interior

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_COMPOSICION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "sala_hotel.json")
ORIGEN = (70, 50)  # esquina de la sala en pantalla (a su derecha van los paneles de la sala)
ESCALA = assets.ESCALA_BACKROOMS
FRACCION_BASE = 0.45  # lo que estorba de un objeto es la parte de abajo (sus "pies")
MARGEN_BASE = 0.12  # y un poco más angosta que el dibujo
ALTO_PARED = 48  # px nativos de la pared del fondo (tapa de 16 + cara de 32)
MARGEN_PISO = 12  # px de pantalla entre el borde de la sala y el cuadro del jugador
SEPARACION_APARICION = (46, 30)  # px entre los puntos de aparición (2x2 en el centro)
BAJADA_APARICION = 40  # px bajo el centro del piso: lejos de la recepción y de su cartel


@dataclass(frozen=True)
class Disposicion:
    """Todo en px de pantalla, como tuplas (x, y, ancho, alto)."""

    sala: tuple  # el salón entero
    piso: tuple  # donde puede estar el cuadro de 32x32 de un jugador
    recepcion: tuple  # base de la recepción (elegir rol)
    vestidores: tuple  # bases de los vestidores, en el orden del archivo
    obstaculos: tuple  # bases de todo lo que estorba (incluye recepción y vestidores)
    apariciones: tuple  # (x, y) donde aparece cada jugador (0 = host)


def cargar_composicion(ruta=RUTA_COMPOSICION):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return None


def plantilla(composicion=None, raiz=RAIZ):
    """Plantilla armada (capas de tiles y objetos) o None si falta algo."""
    composicion = composicion if composicion is not None else cargar_composicion()
    if composicion is None:
        return None
    try:
        with open(os.path.join(raiz, assets.RUTA_TERRENOS_BACKROOMS), encoding="utf-8") as archivo:
            terrenos = json.load(archivo)
        return compositor_interior.componer(composicion, terrenos)
    except (OSError, ValueError, KeyError):
        return None


def a_pantalla(x, y):
    """px nativos de la composición -> px de pantalla."""
    return ORIGEN[0] + x * ESCALA, ORIGEN[1] + y * ESCALA


def rect_objeto(obj):
    """Lo que ocupa el dibujo del objeto: (x, y) de la composición es su esquina inferior izquierda."""
    ancho, alto = obj.get("ancho", 16) * ESCALA, obj.get("alto", 16) * ESCALA
    x, abajo = a_pantalla(obj["x"], obj["y"])
    return (x, abajo - alto, ancho, alto)


def base_objeto(obj):
    """La parte de abajo del objeto, la que choca con los pies de los jugadores."""
    x, y, ancho, alto = rect_objeto(obj)
    alto_base = round(alto * FRACCION_BASE)
    margen = round(ancho * MARGEN_BASE)
    return (x + margen, y + alto - alto_base, ancho - 2 * margen, alto_base)


def disposicion(composicion):
    """Disposicion de la sala en px de pantalla a partir de la composición."""
    ancho, alto = composicion["ancho"] * composicion.get("tile", 16), composicion["alto"] * composicion.get("tile", 16)
    sala = (ORIGEN[0], ORIGEN[1], ancho * ESCALA, alto * ESCALA)
    piso_y = ORIGEN[1] + ALTO_PARED * ESCALA - 16  # se puede pegar a la pared (la cabeza tapa el zócalo)
    piso = (sala[0] + MARGEN_PISO, piso_y, sala[2] - 2 * MARGEN_PISO, sala[1] + sala[3] - MARGEN_PISO - piso_y)
    objetos = composicion.get("objetos", [])
    recepcion = next((base_objeto(o) for o in objetos if o.get("rol") == "recepcion"), None)
    vestidores = tuple(base_objeto(o) for o in objetos if o.get("rol") == "vestidor")
    obstaculos = tuple(base_objeto(o) for o in objetos if o.get("obstaculo"))
    cx = sala[0] + sala[2] // 2
    cy = piso[1] + piso[3] // 2 + BAJADA_APARICION
    dx, dy = SEPARACION_APARICION
    apariciones = ((cx - dx, cy - dy), (cx + dx, cy - dy), (cx - dx, cy + dy), (cx + dx, cy + dy))
    return Disposicion(sala, piso, recepcion, vestidores, obstaculos, apariciones)
