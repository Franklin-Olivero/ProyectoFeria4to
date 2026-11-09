"""Ciudad Nova como mapa 2D de casillas (datos y funciones puras, sin Pygame).

El mundo es una cuadrícula de 64x47 casillas de TAM_CASILLA px (48),
más grande que la ventana: la cámara sigue al jugador. Cada carácter de
MAPA es una casilla:

    .  pasto (transitable)            #  edificio de zona (sólido)
    :  acera / plaza / sendero        H  casa decorativa (sólida)
    c  calle (transitable)            T  seto de árboles (sólido)
    =  calle con carril horizontal    E  entrada de edificio (transitable)
    |  calle con carril vertical
    X  barricada de la Alcaldía (sólida solo mientras está sellada)

Manzanas: arriba, tres filas libres y el jardín entre el Colegio y la
Alcaldía (así ningún edificio toca el borde del mundo); al noroeste, el
parque, con un sendero y una sola entrada desde la Plaza (un callejón sin
salida: no permite rodear ninguna barricada).

Las calles forman un grafo (src/dungeon/grafo_ciudad.py): NODOS_CALLE
dice en qué casilla está cada nodo y TRAMOS, por qué casillas pasa cada
arista y cuál es su sección transversal, donde se levanta su barricada
cuando la calle se satura. Cada sección va de un sólido a otro (acera,
3 casillas de calle, acera), así una barricada corta el paso de verdad.

Decoración (farolas, bancas, árboles, canteros...): se genera por reglas
en src/dungeon/layout_decoracion.py sobre este mapa; las casillas de los
props sólidos se suman a es_solida (PROPS_SOLIDOS).

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
from src.dungeon import layout_decoracion
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
ENTRADA = "E"
BARRICADA = "X"

CALLES = (CALLE, CALLE_HORIZONTAL, CALLE_VERTICAL)
SOLIDAS = (EDIFICIO, CASA, ARBOL)

MAPA = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "T..............................................................T",
    "T..............................................................T",
    "T..............................................................T",
    "T.............###########.............#############............T",
    "THHHHH........###########.............#############.......HHHHHT",
    "THHHHH........###########.............#############.......HHHHHT",
    "THHHHH........###########.............#############.......HHHHHT",
    "THHHHH........###########.............#############.......HHHHHT",
    "THHHHHTTTTTTTT#####E#####TTTTTTTTTTTTT######E######TTTTTTTHHHHHT",
    "T.....T::::::::::::::::::::::::::::::::::::XXX:::::::::::T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:ccc====================ccc===================ccc:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:c|c::::::::::::::::::::ccc:::::::::::::::::::c|c:T.....T",
    "T.....T:c|c:TTTTTTTTTTTTTTTTTT:c|c:TTTTTTTTTTTTTTTTT:c|c:T.....T",
    "THHHHHT:c|c:T.....:..........T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:T.....:..........T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:T.....:..........T:c|c:THHHHHHH..HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:T.....:.....TTTTTT:c|c:TTTTTT....HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:T:::::::::::::::::::::::::::T....HHHHHHT:c|c:THHHHHT",
    "THHHHHT:c|c:T...........T:::::::::::::::T....HHHHHHT:c|c:THHHHHT",
    "T.....T:c|c:TTTTTTTTTTTTT:::::::::::::::TTTTTTTTTTTT:c|c:T.....T",
    "T.....T:c|c::::::::::::::::::::::::::::::::::::::::::c|c:T.....T",
    "T.....T:ccccccccccccccccc:::::::::::::::cccccccccccccccc:T.....T",
    "T.....T:cccc=============:::::::::::::::============cccc:T.....T",
    "T.....T:ccccccccccccccccc:::::::::::::::cccccccccccccccc:T.....T",
    "T.....T:c|c::::::::::::::::::::::::::::::::::::::::::c|c:T.....T",
    "THHHHHT:c|c:TTTTTTTTTTTTT:::::::::::::::TTTTTTTTTTTT:c|c:THHHHHT",
    "THHHHHT:c|c:T###########T:::::::::::::::T###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########T:::::::::::::::T###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########TTTTTT:c|c:TTTTTT###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########.....T:c|c:T.....###########:c|c:THHHHHT",
    "THHHHHT:c|c:T###########.....T:c|c:T.....###########:c|c:THHHHHT",
    "T.....T:c|c:T#####E#####TTTTTT:c|c:TTTTTT#####E#####:c|c:T.....T",
    "T.....T:c|c::::::::::::::::::::ccc:::::::::::::::::::c|c:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T:ccc====================ccc===================ccc:T.....T",
    "T.....T:cccccccccccccccccccccccccccccccccccccccccccccccc:T.....T",
    "T.....T::::::::::::::::::::::::::::::::::::::::::::::::::T.....T",
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
    ZONA_COLEGIO: (14, 4, 11, 6),
    ZONA_ALCALDIA: (38, 4, 13, 6),
    ZONA_HOSPITAL: (13, 29, 11, 6),
    ZONA_EMPRESA_MEDIOS: (41, 29, 11, 6),
}
# Casilla de la puerta (una 'E' del mapa) de cada edificio.
ENTRADAS = {
    ZONA_COLEGIO: (19, 9),
    ZONA_ALCALDIA: (44, 9),
    ZONA_HOSPITAL: (18, 34),
    ZONA_EMPRESA_MEDIOS: (46, 34),
}
# Casillas 'X' frente a la Alcaldía: sólidas mientras está sellada.
BARRICADAS_ALCALDIA = frozenset(
    (col, fila) for fila, linea in enumerate(MAPA) for col, letra in enumerate(linea) if letra == BARRICADA
)

# Plaza central: (columna, fila, ancho, alto). Es acera ':' para la
# lógica; solo cambia su dibujo (losas y mosaico).
PLAZA = (25, 20, 15, 11)

# Parque (manzana noroeste): pasto con un sendero en T; su única entrada
# es (24, 20), desde la Plaza.
PARQUE = (13, 16, 16, 6)
SENDEROS_PARQUE = frozenset([(col, 20) for col in range(13, 25)] + [(18, fila) for fila in range(16, 20)])
# Jardines decorativos que no se ven desde la calle por reglas: la fila
# libre del norte (coníferas), el patio del Colegio y el jardín entre el
# Colegio y la Alcaldía. (tipo, casilla, variante de árbol).
JARDINES = (
    [("arbol", (col, 2), (1, 3)[i % 2]) for i, col in enumerate(range(3, 62, 5))]
    + [("bicicletero", (7, 6), 0), ("bicicleta", (8, 6), 0), ("bicicleta", (9, 6), 0), ("cartelera", (11, 5), 0),
       ("arbol", (12, 7), 36), ("arbol", (7, 8), 38)]
    + [("arbol", (27, 6), 75), ("arbol", (35, 6), 75), ("arbol", (31, 5), 38),
       ("jardinera", (29, 7), 0), ("jardinera", (33, 7), 0)]
)

# Aparición inicial: en la Plaza, junto a su nodo.
SPAWN = (32, 26)

# Nodos del grafo de calles: la casilla de calle donde está cada uno.
# Los de los edificios están en la calle frente a su puerta.
NODOS_CALLE = {
    ZONA_PLAZA: (32, 25),
    CRUCE_NORTE: (32, 12),
    CRUCE_SUR: (32, 37),
    CRUCE_OESTE: (9, 25),
    CRUCE_ESTE: (54, 25),
    ZONA_COLEGIO: (19, 12),
    ZONA_ALCALDIA: (44, 12),
    ZONA_HOSPITAL: (18, 37),
    ZONA_EMPRESA_MEDIOS: (46, 37),
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
    Tramo(ZONA_PLAZA, CRUCE_NORTE, ((32, 25), (32, 12)), _fila(17, 30, 34)),
    Tramo(ZONA_PLAZA, CRUCE_SUR, ((32, 25), (32, 37)), _fila(33, 30, 34)),
    Tramo(ZONA_PLAZA, CRUCE_OESTE, ((32, 25), (9, 25)), _columna(18, 23, 27)),
    Tramo(ZONA_PLAZA, CRUCE_ESTE, ((32, 25), (54, 25)), _columna(46, 23, 27)),
    # Anillo exterior
    Tramo(CRUCE_NORTE, ZONA_COLEGIO, ((32, 12), (19, 12)), _columna(25, 10, 14)),
    Tramo(ZONA_COLEGIO, CRUCE_OESTE, ((19, 12), (9, 12), (9, 25)), _fila(18, 7, 11)),
    Tramo(CRUCE_OESTE, ZONA_HOSPITAL, ((9, 25), (9, 37), (18, 37)), _fila(31, 7, 11)),
    Tramo(ZONA_HOSPITAL, CRUCE_SUR, ((18, 37), (32, 37)), _columna(25, 35, 39)),
    Tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS, ((32, 37), (46, 37)), _columna(39, 35, 39)),
    Tramo(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE, ((46, 37), (54, 37), (54, 25)), _fila(31, 52, 56)),
    Tramo(CRUCE_ESTE, ZONA_ALCALDIA, ((54, 25), (54, 12), (44, 12)), _fila(18, 52, 56)),
    Tramo(ZONA_ALCALDIA, CRUCE_NORTE, ((44, 12), (32, 12)), _columna(38, 10, 14)),
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
    if letra is None or letra in SOLIDAS or (col, fila) in PROPS_SOLIDOS:
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


# ----------------------------------------------------------------------
# Decoración (farolas, bancas, árboles...): reglas en layout_decoracion.py
# ----------------------------------------------------------------------

DECORACION = layout_decoracion.generar(
    MAPA, CALLES, [(t.puntos, t.seccion) for t in TRAMOS], NODOS_CALLE.values(), ENTRADAS.values(), SPAWN,
    PLAZA, PARQUE, SENDEROS_PARQUE, JARDINES, EDIFICIOS.values(),
)
# Casillas que la decoración vuelve sólidas (las suma es_solida).
PROPS_SOLIDOS = frozenset(prop.casilla for prop in DECORACION if prop.solido)
