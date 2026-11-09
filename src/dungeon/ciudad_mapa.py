"""Ciudad Nova como mapa 2D de casillas (datos y funciones puras, sin Pygame).

El mundo es una cuadrícula de 64x44 casillas de TAM_CASILLA px (48),
más grande que la ventana: la cámara sigue al jugador. Cada carácter de
MAPA es una casilla:

    .  pasto (transitable)            #  edificio de zona (sólido)
    :  acera / plaza (transitable)    H  casa decorativa (sólida)
    c  calle (transitable)            T  árbol (sólido)
    =  calle con carril horizontal    F  farola (sólida)
    |  calle con carril vertical      E  entrada de edificio (transitable)
    X  barricada de la Alcaldía (sólida solo mientras está sellada)

Las calles forman un grafo (src/dungeon/grafo_ciudad.py): NODOS_CALLE
dice en qué casilla está cada nodo y TRAMOS, por qué casillas pasa cada
arista y cuál es su sección transversal, donde se levanta su barricada
cuando la calle se satura. Cada sección va de un sólido a otro (acera,
3 casillas de calle, acera), así una barricada corta el paso de verdad.

PROPS: mobiliario urbano sólido (bancas, basureros, parada de bus,
bicicletas...) en casillas que no cortan ninguna calle ni acera de paso:
el patio cerrado junto al Colegio, la acera de su puerta y las esquinas
de la Plaza. Su dibujo es el pack urbano (src/ui/ciudad_render.py).

Funciones para el movimiento y la cámara: es_solida, casilla_de,
entrada_cercana, mover_con_colision y calcular_camara.
"""

import math
from dataclasses import dataclass

from src.core.balance import (
    CRUCE_ESTE,
    CRUCE_NORTE,
    CRUCE_OESTE,
    CRUCE_SUR,
    ENTRADA_ALCANCE,
    TAM_CASILLA,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
    ZONA_PLAZA,
)
from src.structures.graph import Grafo

# Leyenda
PASTO = "."
ACERA = ":"
CALLE = "c"
CALLE_HORIZONTAL = "="
CALLE_VERTICAL = "|"
EDIFICIO = "#"
CASA = "H"
ARBOL = "T"
FAROLA = "F"
ENTRADA = "E"
BARRICADA = "X"

CALLES = (CALLE, CALLE_HORIZONTAL, CALLE_VERTICAL)
SOLIDAS = (EDIFICIO, CASA, ARBOL, FAROLA)

MAPA = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "T.............###########.............#############............T",
    "THHHHH........###########.HHHHH.HHHHH.#############.......HHHHHT",
    "THHHHH........###########.HHHHH.HHHHH.#############.......HHHHHT",
    "THHHHH........###########.HHHHH.HHHHH.#############.......HHHHHT",
    "THHHHH........###########.HHHHH.HHHHH.#############.......HHHHHT",
    "THHHHHTTTTTTTT#####E#####THHHHHTHHHHHT######E######TTTTTTTHHHHHT",
    "T.....T:::::::::::::::::::::F::::::F:::::::XXX:::::::::::T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:ccc====================ccc===================ccc:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:c|c:::F::::::::::::::::ccc:::::::::::::::F:::c|c:T.....T",
    "T.....T:c|c:TTTTTTTTTTTTTTTTTT:c|c:TTTTTTTTTTTTTTTTT:c|c:T.....T",
    "THHHHHT:c|c:THHHHHH..HHHHHHH.T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:THHHHHH..HHHHHHH.T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:THHHHHH..HHHHHHH.T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:THHHHHH.....TTTTTT:c|c:TTTTTT....HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|cFTHHHHHH.....T:::::::::::::::T....HHHHHHTFc|c:THHHHHT",
    "THHHHHT:c|c:THHHHHH.....T:F:::::::::::F:T....HHHHHHT:c|c:THHHHHT",
    "T.....T:c|c:TTTTTTTTTTTTT:::::::::::::::TTTTTTTTTTTT:c|c:T.....T",
    "T.....T:c|c::::::::::::::::::::::::::::::::::::::::::c|c:T.....T",
    "T.....T:ccccccccccccccccc:::::::::::::::cccccccccccccccc:T.....T",
    "T.....T:cccc=============:::::::::::::::============cccc:T.....T",
    "T.....T:ccccccccccccccccc:::::::::::::::cccccccccccccccc:T.....T",
    "T.....T:c|c::::::::::::::::::::::::::::::::::::::::::c|c:T.....T",
    "THHHHHT:c|c:TTTTTTTTTTTTT:::::::::::::::TTTTTTTTTTTT:c|c:THHHHHT",
    "THHHHHT:c|c:T###########T:F:::::::::::F:T###########:c|c:THHHHHT",
    "THHHHHT:c|cFT###########T:::::::::::::::T###########Fc|c:THHHHHT",
    "THHHHHT:c|c:T###########TTTTTT:c|c:TTTTTT###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########.....T:c|c:T.....###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########.....T:c|c:T.....###########:c|c:THHHHHT",
    "T.....T:c|c:T#####E#####TTTTTT:c|c:TTTTTT#####E#####:c|c:T.....T",
    "T.....T:c|c:::F::::::::::::::::ccc:F:::::::::::::::::c|c:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:ccc====================ccc===================ccc:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:::::::::::::::F:::::::::::::::::::F::::::::::::::T.....T",
    "T.....TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT.....T",
    "T............HHHHHH..HHHHHHH........HHHHHHH..HHHHHHH...........T",
    "T............HHHHHH..HHHHHHH........HHHHHHH..HHHHHHH...........T",
    "T............HHHHHH..HHHHHHH........HHHHHHH..HHHHHHH...........T",
    "T............HHHHHH..HHHHHHH........HHHHHHH..HHHHHHH...........T",
    "T............HHHHHH..HHHHHHH........HHHHHHH..HHHHHHH...........T",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]

COLUMNAS = len(MAPA[0])
FILAS = len(MAPA)
TAM_MUNDO = (COLUMNAS * TAM_CASILLA, FILAS * TAM_CASILLA)

# Edificios de zona: (columna, fila, ancho, alto) en casillas. Todas las
# puertas miran al sur (fachada estilo Pokémon) y dan a una acera.
EDIFICIOS = {
    ZONA_COLEGIO: (14, 1, 11, 6),
    ZONA_ALCALDIA: (38, 1, 13, 6),
    ZONA_HOSPITAL: (13, 26, 11, 6),
    ZONA_EMPRESA_MEDIOS: (41, 26, 11, 6),
}
# Casilla de la puerta (una 'E' del mapa) de cada edificio.
ENTRADAS = {
    ZONA_COLEGIO: (19, 6),
    ZONA_ALCALDIA: (44, 6),
    ZONA_HOSPITAL: (18, 31),
    ZONA_EMPRESA_MEDIOS: (46, 31),
}
# Casillas 'X' frente a la Alcaldía: sólidas mientras está sellada.
BARRICADAS_ALCALDIA = frozenset(
    (col, fila) for fila, linea in enumerate(MAPA) for col, letra in enumerate(linea) if letra == BARRICADA
)

# Mobiliario urbano sólido: casilla -> nombre del prop (assets.PROPS_URBANOS).
PROPS = {
    # Patio del Colegio (cerrado por árboles: solo decora).
    (8, 2): "banca", (11, 2): "jardinera", (13, 2): "maceta_grande",
    (7, 5): "bicicletero", (9, 5): "bicicleta", (10, 5): "bicicleta", (12, 5): "cartelera",
    # Acera frente al Colegio, sin tapar su puerta (19, 6).
    (15, 7): "basurero", (23, 7): "buzon",
    # Esquinas de la Plaza (las columnas 30-34 quedan libres para el camino al norte y al sur).
    (25, 17): "jardinera", (27, 17): "banca", (37, 17): "banca", (39, 17): "jardinera",
    (25, 27): "jardinera", (27, 27): "banca", (37, 27): "banca", (39, 27): "jardinera",
    # Aceras de la avenida central.
    (14, 20): "parada_bus", (16, 20): "maquina", (48, 20): "hidrante", (20, 24): "reciclaje",
    (44, 24): "basurero",
}

# Plaza central: (columna, fila, ancho, alto). Es acera ':' para la
# lógica; solo cambia su dibujo (losas y mosaico).
PLAZA = (25, 17, 15, 11)

# Aparición inicial: en la Plaza, junto a su nodo.
SPAWN = (32, 23)

# Nodos del grafo de calles: la casilla de calle donde está cada uno.
# Los de los edificios están en la calle frente a su puerta.
NODOS_CALLE = {
    ZONA_PLAZA: (32, 22),
    CRUCE_NORTE: (32, 9),
    CRUCE_SUR: (32, 34),
    CRUCE_OESTE: (9, 22),
    CRUCE_ESTE: (54, 22),
    ZONA_COLEGIO: (19, 9),
    ZONA_ALCALDIA: (44, 9),
    ZONA_HOSPITAL: (18, 34),
    ZONA_EMPRESA_MEDIOS: (46, 34),
}


@dataclass(frozen=True)
class Tramo:
    """Una arista del grafo de calles sobre el mapa.

    puntos: casillas por las que pasa el eje de la calle, de `a` a `b`
        (extremos y codos; entre dos puntos seguidos el tramo es recto).
    seccion: casillas de la barricada (corte transversal de la calle,
        de un sólido a otro).
    """

    a: str
    b: str
    puntos: tuple
    seccion: tuple


def _columna(col, fila_desde, fila_hasta):
    return tuple((col, fila) for fila in range(fila_desde, fila_hasta + 1))


def _fila(fila, col_desde, col_hasta):
    return tuple((col, fila) for col in range(col_desde, col_hasta + 1))


TRAMOS = [
    # Radios de la Plaza
    Tramo(ZONA_PLAZA, CRUCE_NORTE, ((32, 22), (32, 9)), _fila(14, 30, 34)),
    Tramo(ZONA_PLAZA, CRUCE_SUR, ((32, 22), (32, 34)), _fila(30, 30, 34)),
    Tramo(ZONA_PLAZA, CRUCE_OESTE, ((32, 22), (9, 22)), _columna(18, 20, 24)),
    Tramo(ZONA_PLAZA, CRUCE_ESTE, ((32, 22), (54, 22)), _columna(46, 20, 24)),
    # Anillo exterior
    Tramo(CRUCE_NORTE, ZONA_COLEGIO, ((32, 9), (19, 9)), _columna(25, 7, 11)),
    Tramo(ZONA_COLEGIO, CRUCE_OESTE, ((19, 9), (9, 9), (9, 22)), _fila(15, 7, 11)),
    Tramo(CRUCE_OESTE, ZONA_HOSPITAL, ((9, 22), (9, 34), (18, 34)), _fila(28, 7, 11)),
    Tramo(ZONA_HOSPITAL, CRUCE_SUR, ((18, 34), (32, 34)), _columna(25, 32, 36)),
    Tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS, ((32, 34), (46, 34)), _columna(39, 32, 36)),
    Tramo(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE, ((46, 34), (54, 34), (54, 22)), _fila(28, 52, 56)),
    Tramo(CRUCE_ESTE, ZONA_ALCALDIA, ((54, 22), (54, 9), (44, 9)), _fila(15, 52, 56)),
    Tramo(ZONA_ALCALDIA, CRUCE_NORTE, ((44, 9), (32, 9)), _columna(38, 7, 11)),
]


def tramo(a, b):
    """El Tramo que une a con b (en cualquier orden). KeyError si no hay."""
    for candidato in TRAMOS:
        if {candidato.a, candidato.b} == {a, b}:
            return candidato
    raise KeyError(f"No hay tramo de calle entre {a!r} y {b!r}.")


def largo_tramo(t):
    """Largo del tramo `t` en casillas: los pasos de su eje de `a` a `b`
    (los codos cuentan; siempre es el recorrido real por la calle)."""
    return len(casillas_de_tramo(t.puntos)) - 1


def punto_medio_tramo(t):
    """(col, fila) fraccionarios a mitad del recorrido del tramo `t`
    (donde el mapa del mundo pone la etiqueta de su peso)."""
    restante = largo_tramo(t) / 2
    for (c0, f0), (c1, f1) in zip(t.puntos, t.puntos[1:]):
        largo = abs(c1 - c0) + abs(f1 - f0)
        if restante <= largo:
            fraccion = restante / largo if largo else 0.0
            return (c0 + (c1 - c0) * fraccion, f0 + (f1 - f0) * fraccion)
        restante -= largo
    return t.puntos[-1]


def casillas_de_tramo(puntos):
    """Todas las casillas del eje de un tramo, recorriendo sus puntos en
    línea recta (horizontal o vertical) de uno al siguiente."""
    casillas = [puntos[0]]
    for (c0, f0), (c1, f1) in zip(puntos, puntos[1:]):
        paso_c = (c1 > c0) - (c1 < c0)
        paso_f = (f1 > f0) - (f1 < f0)
        col, fila = c0, f0
        while (col, fila) != (c1, f1):
            col, fila = col + paso_c, fila + paso_f
            casillas.append((col, fila))
    return casillas


def polilinea_ruta(posicion, nodos):
    """Puntos (px del mundo) para dibujar una ruta sobre las calles: del
    jugador al primer nodo, luego cada tramo por sus codos, y al final
    hasta la puerta si el último nodo es un edificio."""
    puntos = [tuple(posicion), centro_casilla(*NODOS_CALLE[nodos[0]])]
    for a, b in zip(nodos, nodos[1:]):
        t = tramo(a, b)
        recorrido = t.puntos if t.a == a else tuple(reversed(t.puntos))
        puntos.extend(centro_casilla(*punto) for punto in recorrido[1:])
    if nodos[-1] in ENTRADAS:
        puntos.append(centro_casilla(*ENTRADAS[nodos[-1]]))
    return puntos


# ----------------------------------------------------------------------
# Casillas y coordenadas
# ----------------------------------------------------------------------

def casilla(col, fila):
    """Carácter de la casilla, o None fuera del mundo."""
    if 0 <= fila < FILAS and 0 <= col < COLUMNAS:
        return MAPA[fila][col]
    return None


def es_solida(col, fila, barricadas=frozenset()):
    """True si no se puede pisar: edificio, casa, árbol, farola, un prop,
    fuera del mundo o una casilla de `barricadas` (las barricadas activas)."""
    letra = casilla(col, fila)
    if letra is None or letra in SOLIDAS or (col, fila) in PROPS:
        return True
    return (col, fila) in barricadas


def casilla_de(x, y):
    """(columna, fila) de la casilla que contiene el punto (x, y) del mundo."""
    return (math.floor(x / TAM_CASILLA), math.floor(y / TAM_CASILLA))


def centro_casilla(col, fila):
    """Centro de la casilla en coordenadas del mundo (px)."""
    return ((col + 0.5) * TAM_CASILLA, (fila + 0.5) * TAM_CASILLA)


def entrada_cercana(posicion, alcance=ENTRADA_ALCANCE):
    """Zona cuya puerta está a menos de `alcance` px de `posicion` (la
    más cercana si hubiera varias), o None."""
    mejor, mejor_distancia = None, alcance
    for zona, puerta in ENTRADAS.items():
        cx, cy = centro_casilla(*puerta)
        distancia = math.hypot(posicion[0] - cx, posicion[1] - cy)
        if distancia < mejor_distancia:
            mejor, mejor_distancia = zona, distancia
    return mejor


def posicion_aparicion(zona):
    """Dónde aparece el jugador al llegar a `zona` (px del mundo): en la
    Plaza, el SPAWN; en un edificio, dos casillas frente a su puerta
    (en la calle, fuera del alcance para no volver a entrar sin querer)."""
    if zona not in ENTRADAS:
        return centro_casilla(*SPAWN)
    col, fila = ENTRADAS[zona]
    return centro_casilla(col, fila + 2)


# ----------------------------------------------------------------------
# Movimiento y cámara
# ----------------------------------------------------------------------

_EPSILON = 1e-6


def _casillas_que_cubre(minimo, maximo):
    """Índices de casilla que toca el intervalo [minimo, maximo)."""
    return range(math.floor(minimo / TAM_CASILLA), math.floor((maximo - _EPSILON) / TAM_CASILLA) + 1)


def _choca(x, y, ancho, alto, es_solida_fn):
    for fila in _casillas_que_cubre(y - alto / 2, y + alto / 2):
        for col in _casillas_que_cubre(x - ancho / 2, x + ancho / 2):
            if es_solida_fn(col, fila):
                return True
    return False


def _mover_eje(x, y, desplazamiento, ancho, alto, es_solida_fn, eje):
    """Mueve el centro en un solo eje (0 = x, 1 = y). Si el rect nuevo
    pisa una casilla sólida, lo deja pegado al borde de esa casilla."""
    if desplazamiento == 0:
        return x if eje == 0 else y
    if eje == 0:
        nuevo = x + desplazamiento
        if not _choca(nuevo, y, ancho, alto, es_solida_fn):
            return nuevo
        medio = ancho / 2
    else:
        nuevo = y + desplazamiento
        if not _choca(x, nuevo, ancho, alto, es_solida_fn):
            return nuevo
        medio = alto / 2
    if desplazamiento > 0:
        borde = math.floor((nuevo + medio - _EPSILON) / TAM_CASILLA) * TAM_CASILLA
        pegado = borde - medio
    else:
        borde = (math.floor((nuevo - medio) / TAM_CASILLA) + 1) * TAM_CASILLA
        pegado = borde + medio
    actual = x if eje == 0 else y
    # Solo se acepta si no retrocede ni choca (p. ej. si ya empezó encimado).
    hacia_adelante = (pegado - actual) * desplazamiento >= 0
    libre = not (_choca(pegado, y, ancho, alto, es_solida_fn) if eje == 0
                 else _choca(x, pegado, ancho, alto, es_solida_fn))
    return pegado if hacia_adelante and libre else actual


def mover_con_colision(posicion, delta, tamano, es_solida_fn):
    """Nueva posición (centro) tras intentar moverse `delta` px con un
    rect de `tamano` = (ancho, alto) contra las casillas sólidas.

    Se mueve por ejes separados: primero x, después y. Si un eje choca,
    el otro igual avanza, así el jugador "resbala" a lo largo de un muro
    al caminar en diagonal. Un desplazamiento grande se parte en pasos
    de media casilla para no atravesar casillas.
    """
    x, y = posicion
    dx, dy = delta
    ancho, alto = tamano
    pasos = max(1, math.ceil(max(abs(dx), abs(dy)) / (TAM_CASILLA / 2)))
    for _ in range(pasos):
        x = _mover_eje(x, y, dx / pasos, ancho, alto, es_solida_fn, 0)
        y = _mover_eje(x, y, dy / pasos, ancho, alto, es_solida_fn, 1)
    return (x, y)


def calcular_camara(pos_jugador, tam_mundo, tam_vista):
    """Esquina superior izquierda (x, y) de la vista dentro del mundo:
    centrada en el jugador y limitada a los bordes del mundo. Si el
    mundo es más chico que la vista en un eje, lo centra (valor negativo)."""
    camara = []
    for eje in (0, 1):
        sobrante = tam_mundo[eje] - tam_vista[eje]
        if sobrante <= 0:
            camara.append(round(sobrante / 2))
        else:
            deseada = pos_jugador[eje] - tam_vista[eje] / 2
            camara.append(round(max(0, min(sobrante, deseada))))
    return tuple(camara)


# ----------------------------------------------------------------------
# Grafo de casillas (validación del mapa y "nodo más cercano a pie")
# ----------------------------------------------------------------------

def grafo_casillas(es_solida_fn):
    """Grafo no dirigido con una arista entre cada par de casillas
    transitables vecinas (arriba/abajo/izquierda/derecha). Con ~2800
    casillas, O(V + E) para construirlo y para recorrerlo con BFS."""
    grafo = Grafo()
    for fila in range(FILAS):
        for col in range(COLUMNAS):
            if es_solida_fn(col, fila):
                continue
            grafo.agregar_nodo((col, fila))
            for vecino in ((col + 1, fila), (col, fila + 1)):
                if not es_solida_fn(*vecino):
                    grafo.agregar_arista((col, fila), vecino)
    return grafo
