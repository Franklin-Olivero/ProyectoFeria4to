"""Auto-tiling compuesto de Ciudad Nova (lógica pura, sin Pygame).

Los packs cyberpunk no traen un tileset en grilla (son láminas de 1024 px
con celdas de tamaños distintos), así que cada casilla de 48 px se ARMA
con piezas de textura 1:1 (asfalto, losa, bordillo de peligro, línea de
carril, cebra, agua, canto metálico). Este módulo decide QUÉ piezas lleva
cada casilla mirando a sus vecinas; src/ui/tiles_ciudad.py solo las pega.

    terreno(letra)                  -> nombre del terreno de una letra del mapa
    bordes(es, c, f)                -> lados (N, E, S, O) cuya vecina es de otro terreno
    esquinas_internas(es, c, f)     -> diagonales (NE, SE, SO, NO) con muesca: las dos
                                       vecinas de lado son iguales pero la diagonal no
    tramo_calle(es_calle, c, f)     -> "h" (brazo horizontal), "v" (vertical) o "cruce"
    linea_carril(es_calle, c, f)    -> lado donde va la línea central del brazo, o None
    paso_cebra(es_calle, es_paso, c, f) -> "h"/"v" si la casilla es el último tramo antes de un
                                       cruce o de la plaza (rayas a lo ancho de la calle)
    descriptor(mapa, c, f)          -> tupla con todo lo anterior: la clave de caché del dibujo

`es(c, f)` es una función que dice si la casilla (c, f) es del mismo
terreno; fuera del mapa cuenta como distinta. Todo es O(1) por casilla
salvo tramo_calle, que mide el largo de la corrida de calle en fila y
columna (O(ancho del mapa)).
"""

CALLE, ACERA, PASTO, AGUA, VERDE, MURO, BASE = "calle", "acera", "pasto", "agua", "verde", "muro", "base"

TERRENOS = {
    "c": CALLE,
    ":": ACERA, "E": ACERA, "X": ACERA,
    ".": PASTO,
    "~": AGUA, "F": AGUA,
    "k": VERDE, "J": VERDE,
    "W": MURO,
    "#": BASE, "H": BASE,
}
TRANSITABLES = (CALLE, ACERA, PASTO)

LADOS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "O": (-1, 0)}
DIAGONALES = {"NE": ("N", "E"), "SE": ("S", "E"), "SO": ("S", "O"), "NO": ("N", "O")}
ANCHO_BRAZO = 2  # una calle de 2 carriles: más ancho que esto en ambos ejes es un cruce


def terreno(letra):
    return TERRENOS.get(letra, BASE)


def _mueve(c, f, lado):
    dc, df = LADOS[lado]
    return c + dc, f + df


def bordes(es, c, f):
    """Lados cuya vecina NO es del mismo terreno, en orden N, E, S, O."""
    return tuple(lado for lado in LADOS if not es(*_mueve(c, f, lado)))


def esquinas_internas(es, c, f):
    """Diagonales con muesca: ambos lados vecinos son del terreno, la
    diagonal no (la esquina cóncava de una L)."""
    salida = []
    for diagonal, (vertical, horizontal) in DIAGONALES.items():
        dc = LADOS[horizontal][0]
        df = LADOS[vertical][1]
        if es(*_mueve(c, f, vertical)) and es(*_mueve(c, f, horizontal)) and not es(c + dc, f + df):
            salida.append(diagonal)
    return tuple(salida)


def _corrida(es, c, f, dc, df):
    """Casillas seguidas del terreno a través de (c, f) en la dirección (dc, df)."""
    largo = 1
    for signo in (-1, 1):
        x, y = c + dc * signo, f + df * signo
        while es(x, y):
            largo += 1
            x, y = x + dc * signo, y + df * signo
    return largo


def tramo_calle(es_calle, c, f):
    """'h' si la calle corre de oeste a este por aquí (su corrida vertical
    mide a lo sumo ANCHO_BRAZO), 'v' si corre de norte a sur, 'cruce' si
    se ensancha en los dos ejes (intersección, codo o curva)."""
    horizontal = _corrida(es_calle, c, f, 1, 0)
    vertical = _corrida(es_calle, c, f, 0, 1)
    if vertical <= ANCHO_BRAZO < horizontal:
        return "h"
    if horizontal <= ANCHO_BRAZO < vertical:
        return "v"
    return "cruce"


def linea_carril(es_calle, c, f):
    """Lado de la casilla donde se pinta la línea central de su brazo: el
    que da al otro carril. None en un cruce o en una calle de 1 carril."""
    tipo = tramo_calle(es_calle, c, f)
    if tipo == "v":
        if es_calle(c + 1, f) and not es_calle(c - 1, f):
            return "E"
        if es_calle(c - 1, f) and not es_calle(c + 1, f):
            return "O"
    elif tipo == "h":
        if es_calle(c, f + 1) and not es_calle(c, f - 1):
            return "S"
        if es_calle(c, f - 1) and not es_calle(c, f + 1):
            return "N"
    return None


def paso_cebra(es_calle, es_paso, c, f):
    """Orientación de las rayas si (c, f) es la última casilla de un brazo
    antes de un cruce o de una explanada peatonal (`es_paso`: plaza): 'h'
    = rayas horizontales (el brazo es vertical), 'v' = verticales."""
    tipo = tramo_calle(es_calle, c, f)
    if tipo == "cruce":
        return None
    adelante = (("N", "S") if tipo == "v" else ("E", "O"))
    for lado in adelante:
        vecina = _mueve(c, f, lado)
        if es_calle(*vecina) and tramo_calle(es_calle, *vecina) == "cruce":
            return "h" if tipo == "v" else "v"
        if not es_calle(*vecina) and es_paso(*vecina):
            return "h" if tipo == "v" else "v"
    return None


def barandas(es_agua, c, f):
    """Lados de una casilla transitable que dan al agua (un puente o la orilla)."""
    return tuple(lado for lado in LADOS if es_agua(*_mueve(c, f, lado)))


def _consulta(mapa, terreno_buscado):
    alto, ancho = len(mapa), len(mapa[0])

    def es(c, f):
        return 0 <= c < ancho and 0 <= f < alto and terreno(mapa[f][c]) == terreno_buscado
    return es


def descriptor(mapa, c, f, es_paso=lambda c, f: False):
    """Todo lo que hace falta para dibujar la casilla (c, f), como tupla
    hashable: (terreno, bordes, esquinas internas, extra). `extra` para
    calles es (tramo, línea, cebra, barandas, paridad); para aceras y
    pasto, (barandas, paridad); para el resto, (paridad,). La paridad
    (c % 2, f % 2) elige el cuarto de la textura de 96 px que toca, así
    dos casillas vecinas nunca repiten el mismo recorte."""
    nombre = terreno(mapa[f][c])
    es = _consulta(mapa, nombre)
    paridad = (c % 2, f % 2)
    agua = _consulta(mapa, AGUA)
    if nombre == CALLE:
        extra = (tramo_calle(es, c, f), linea_carril(es, c, f), paso_cebra(es, es_paso, c, f),
                 barandas(agua, c, f), paridad)
    elif nombre in (ACERA, PASTO):
        extra = (barandas(agua, c, f), paridad)
    else:
        extra = (paridad,)
    return (nombre, bordes(es, c, f), esquinas_internas(es, c, f), extra)
