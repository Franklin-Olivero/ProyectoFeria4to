"""Ciudad Nova como mapa 2D de casillas (datos y funciones puras, sin Pygame).

El mundo es una cuadrícula de 64x47 casillas de TAM_CASILLA px (48),
más grande que la ventana: la cámara sigue al jugador. Cada carácter de
MAPA es una casilla:

    .  pasto (parque, patios)         #  edificio de zona (sólido)
    :  acera / plaza / sendero        H  casa (sólida; una de CASAS)
    c  calle (2 carriles)             W  muro / cerca (sólido)
    k  camellón de la avenida (sól.)  J  jardín tecno cercado (sólido)
    ~  canal de datos (sólido)        F  fuente o monumento (sólido)
    E  entrada de edificio            X  barricada de la Alcaldía (sólida
                                         solo mientras está sellada)

Plano (rehecho con los packs cyberpunk): la Avenida Nova cruza la ciudad
de oeste a este con camellón (carriles en las filas 24-25 y 27-28) y
atraviesa la Plaza central; los radios norte y sur salen de la Plaza
desplazados (en molinete) y el anillo exterior tiene un codo al norte
(las calles de la Alcaldía y del Colegio van por filas distintas) y una
Z al sur hacia la Empresa de Medios. El Canal de Datos baja de norte a
sur por las columnas 38-39, se cruza por tres puentes (calle norte,
avenida y calle sur) y al noreste se ensancha en la laguna del Parque.
Bolsillos sin salida (cada uno da a un solo tramo o a un nodo): Plaza
cívica, Parque (un portón a la avenida), patio del Colegio, Paseo
comercial (al radio sur), jardín del Hospital (a la Plaza) y el lote del
Distrito Liminal (bajo el Cruce Sur). Ninguno permite rodear una barricada.

Las calles forman un grafo (src/dungeon/grafo_ciudad.py): NODOS_CALLE
dice en qué casilla está cada nodo y TRAMOS, por qué casillas pasa cada
arista y cuál es su sección transversal, donde se levanta su barricada
cuando la calle se satura. Cada sección va de un sólido a otro (acera,
calle, acera; el camellón ya es sólido), así una barricada corta el paso.

Decoración (farolas, bancas, árboles, máquinas...): se genera por reglas
en src/dungeon/layout_decoracion.py sobre este mapa; las casillas de los
props sólidos se suman a es_solida (PROPS_SOLIDOS). El dibujo por
auto-tiling compuesto vive en src/dungeon/autotile_ciudad.py (puro) y
src/ui/tiles_ciudad.py.

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
CAMELLON = "k"
EDIFICIO = "#"
CASA = "H"
MURO = "W"
JARDIN = "J"
ENTRADA = "E"
BARRICADA = "X"
FUENTE = "F"
AGUA = "~"

CALLES = (CALLE,)
SOLIDAS = (EDIFICIO, CASA, MURO, JARDIN, CAMELLON, FUENTE, AGUA)

MAPA = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WHHHHHHHHHHHHHHHHHHHHJJJJJHHHHHHHJJJJJ~~WWWWWWWWWWWWWWWWWHHHHHHW",
    "WHHHHHHHHHHHHHHHHHHHHJJJJJHHHHHHHJJJJJ~~::::::###########HHHHHHW",
    "WHHHHHHHHH###########JJJJJHHHHHHHJJJJJ~~::FF::###########HHHHHHW",
    "WHHHHHHHHH###########HHHHHHHHHHHHHHHHH~~::FF::###########HHHHHHW",
    "WHHHHHHHHH###########HHHHHHHHHHHHHHHHH~~::::::###########HHHHHHW",
    "WHHHHHHHHH###########HHHHHHHHHHHHHHHHH~~::::::#####E#####HHHHHHW",
    "WHHHHHHHHH###########HHHHHHHHHHHH:::::::::::::::::XXX::::HHHHHHW",
    "WHHHHHHHHH#####E#####HHHHHHHHHHHH:cccccccccccccccccccccc:HHHHHHW",
    "WHHHH:::::::::::::::::::::::::::::cccccccccccccccccccccc:HHHHHHW",
    "WHHHH:cccccccccccccccccccccccccccccc::::::::::::::::::cc:HHHHHHW",
    "WHHHH:cccccccccccccccccccccccccccccc:W~~WWWWWWWWWWWWWWcc:HHHHHHW",
    "WHHHH:cc::::::::::::::::::::::::::cc:W~~......:.....W:cc:JJJJJJW",
    "WHHHH:cc:W.....::....HHHHHHHHHHHH:cc:W~~~~~~~.:.....W:cc:JJJJJJW",
    "WHHHH:cc:W.:::::::::.HHHHHHHHHHHH:cc:W~~~~~~~~:.....W:cc:JJJJJJW",
    "WHHHH:cc:W.:::::::::.HHHHHHHHHHHH:cc:W~~~~~~~~:.....W:cc:JJJJJJW",
    "WHHHH:cc:W.:::::::::.HHHHHHHHHHHH:cc:W~~~~~~~~:.....W:cc:HHHHHHW",
    "WJJJJ:cc:W.:::::::::.HHHHHHHHHHHH:cc:W~~~~~~~~::::::W:cc:HHHHHHW",
    "WJJJJ:cc:W...........HHHHHHHHHHHH:cc:W~~~~~~~~:.....W:cc:HHHHHHW",
    "WJJJJ:cc:WWWWWWHHHHHHHH:::::::::::::::~~~~~~~.:.....W:cc:HHHHHHW",
    "WJJJJ:cc:WJJJJJHHHHHHHH::::::FFF::::::~~......:.....W:cc:HHHHHHW",
    "WJJJJ:cc:WJJJJJHHHHHHHH::::::FFF::::::~~......:.....W:cc:HHHHHHW",
    "WHHHH:cc:WJJJJJHHHHHHHH:::::::::::::::~~WWWWWW::WWWWW:cc:HHHHHHW",
    "WHHHH:cc::::::::::::::::::::::::::::::::::::::::::::::cc:HHHHHHW",
    "WHHHH:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:HHHHHHW",
    "WHHHH:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:HHHHHHW",
    "WHHHH:cccckkkkkkkkkkkcc:::::::::::::::ccckkkkkkkkkkkcccc:HHHHHHW",
    "WHHHH:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:HHHHHHW",
    "WHHHH:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:HHHHHHW",
    "WJJJJ:cc::::::::::::::::::::::::::::::::::::::::::::::cc:HHHHHHW",
    "WJJJJ:cc:WWWWWWWWWWWWWW:::::::::::::::~~HHHHHHHWWWWWW:cc:HHHHHHW",
    "WJJJJ:cc:###########...:::::::::::::::~~HHHHHHHJJJJJJ:cc:JJJJJJW",
    "WJJJJ:cc:###########...W:cc:HHHHHHHHHH~~HHHHHHHJJJJJJ:cc:JJJJJJW",
    "WHHHH:cc:###########:::W:cc:HHHHHHHHHH~~HHHHHHHJJJJJJ:cc:JJJJJJW",
    "WHHHH:cc:###########...W:cc:::::::::::~~HHHHHHHWWWWWW:cc:JJJJJJW",
    "WHHHH:cc:###########...W:cc:::::::::::~~W###########W:cc:HHHHHHW",
    "WHHHH:cc:#####E#####WWWW:cc:JJJJJJJJJJ~~W###########W:cc:HHHHHHW",
    "WHHHH:cc:::::::::::::::::cc:::::::HHHH~~W###########W:cc:HHHHHHW",
    "WHHHH:ccccccccccccccccccccccccccc:HHHH~~W###########W:cc:HHHHHHW",
    "WHHHH:ccccccccccccccccccccccccccc:HHHH~~W###########W:cc:HHHHHHW",
    "WHHHH::::::::::::::::::::::::::cc:HHHH~~W#####E#####W:cc:HHHHHHW",
    "WHHHHHHHHJJJJJHHHHHHHH:::::::W:cc:::::::::::::::::::::cc:JJJJJJW",
    "WHHHHHHHHJJJJJHHHHHHHH:::::::W:ccccccccccccccccccccccccc:JJJJJJW",
    "WHHHHHHHHJJJJJHHHHHHHH:::::::W:ccccccccccccccccccccccccc:JJJJJJW",
    "WHHHHHHHHJJJJJHHHHHHHH:::::::W:::::::::::::::::::::::::::JJJJJJW",
    "WHHHHHHHHJJJJJHHHHHHHH:::::::WWWWWWWWW~~WWWWWWWWWWWWWWWWWJJJJJJW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

COLUMNAS = len(MAPA[0])
FILAS = len(MAPA)
TAM_MUNDO = (COLUMNAS * TAM_CASILLA, FILAS * TAM_CASILLA)

# Edificios de zona: (columna, fila, ancho, alto) en casillas. Todas las
# puertas miran al sur (fachada estilo Pokémon) y dan a una acera.
EDIFICIOS = {
    ZONA_COLEGIO: (10, 3, 11, 6),
    ZONA_ALCALDIA: (46, 2, 11, 5),
    ZONA_HOSPITAL: (9, 31, 11, 6),
    ZONA_EMPRESA_MEDIOS: (41, 35, 11, 6),
}
# Casilla de la puerta (una 'E' del mapa) de cada edificio.
ENTRADAS = {
    ZONA_COLEGIO: (15, 8),
    ZONA_ALCALDIA: (51, 6),
    ZONA_HOSPITAL: (14, 36),
    ZONA_EMPRESA_MEDIOS: (46, 40),
}
# Casillas 'X' frente a la Alcaldía: sólidas mientras está sellada.
BARRICADAS_ALCALDIA = frozenset(
    (col, fila) for fila, linea in enumerate(MAPA) for col, letra in enumerate(linea) if letra == BARRICADA
)

# Plaza central: (columna, fila, ancho, alto). Es acera ':' para la
# lógica; solo cambia su dibujo (losas, emblema al centro y el monumento).
PLAZA = (23, 19, 15, 13)
MONUMENTO = (29, 20, 3, 2)  # las 'F' de la Plaza: la Torre de Datos

# Plaza de la Alcaldía (zona cívica): losas con la fuente de datos; se
# entra desde la acera norte, entre el canal y la Alcaldía.
PLAZA_CIVICA = (40, 2, 6, 5)
FUENTE_CIVICA = (42, 3, 2, 2)

# Parque (cuadrante noreste): pasto, laguna del canal y un sendero en T;
# su único acceso es el portón de la fila 22, desde la Avenida Nova.
PARQUE = (40, 12, 12, 10)
PORTON_PARQUE = ((46, 22), (47, 22))
SENDEROS_PARQUE = frozenset(
    [(col, fila) for fila in range(PARQUE[1], PARQUE[1] + PARQUE[3])
     for col in range(PARQUE[0], PARQUE[0] + PARQUE[2]) if MAPA[fila][col] == ACERA] + list(PORTON_PARQUE)
)
# Otros bolsillos con identidad propia (dibujo y decoración).
PATIO_COLEGIO = (10, 13, 11, 6)  # cancha con pasto alrededor, abierta a la acera de la calle del Colegio
PASEO_COMERCIAL = (28, 34, 10, 2)  # calle peatonal con tiendas al norte y cantero al sur, abierta al radio sur
JARDIN_HOSPITAL = (20, 31, 3, 5)
# Entradas de los bolsillos: la decoración nunca las tapa (como los senderos).
ACCESOS_BOLSILLOS = frozenset([
    (27, 34), (27, 35),  # paseo comercial, desde la acera del radio sur
    (15, 12), (16, 12), (15, 13), (16, 13),  # patio del Colegio
    (42, 7), (43, 7),  # plaza cívica
    (22, 31), (23, 31),  # jardín del Hospital, desde la Plaza
    (24, 40), (25, 40), (26, 40),  # lote del Distrito Liminal (zonas_ciudad.ACCESO_LIMINAL)
])

# Casas: cada una es un edificio con su huella (col, fila, ancho, alto) y
# su estilo (assets.ESTILOS_CASA: techo, fachada y neón de los packs).
# Juntas cubren exactamente las 'H' del mapa; dos casas a 2 casillas o
# menos nunca comparten estilo.
CASAS = (
    ((1, 1, 6, 4), "lima"), ((7, 1, 6, 2), "magenta"), ((13, 1, 5, 2), "grafito"), ((18, 1, 3, 2), "magenta"),
    ((26, 1, 4, 4), "ambar"), ((30, 1, 3, 4), "magenta"), ((57, 1, 6, 4), "lima"), ((7, 3, 3, 4), "oliva"),
    ((21, 4, 5, 3), "acero"), ((33, 4, 5, 3), "oliva"), ((1, 5, 6, 4), "grafito"), ((26, 5, 4, 4), "grafito"),
    ((30, 5, 3, 4), "lima"), ((57, 5, 6, 4), "ambar"), ((7, 7, 3, 2), "cobalto"), ((21, 7, 5, 2), "oliva"),
    ((1, 9, 4, 4), "cobre"), ((57, 9, 6, 3), "cobre"), ((1, 13, 4, 4), "magenta"), ((21, 13, 6, 4), "lima"),
    ((27, 13, 6, 4), "acero"), ((57, 16, 6, 4), "cobre"), ((21, 17, 6, 2), "cobalto"),
    ((27, 17, 6, 2), "ambar"), ((15, 19, 5, 4), "ambar"), ((20, 19, 3, 4), "acero"),
    ((57, 20, 6, 4), "magenta"), ((1, 22, 4, 4), "ambar"), ((57, 24, 6, 4), "lima"), ((1, 26, 4, 3), "lima"),
    ((57, 28, 6, 3), "cobalto"), ((40, 30, 4, 3), "lima"), ((44, 30, 3, 3), "cobre"),
    ((28, 32, 6, 2), "magenta"), ((34, 32, 4, 2), "oliva"), ((1, 33, 4, 4), "lima"), ((40, 33, 4, 2), "acero"),
    ((44, 33, 3, 2), "grafito"), ((34, 37, 4, 4), "grafito"),
    ((57, 35, 6, 4), "cobalto"), ((1, 37, 4, 4), "cobre"), ((57, 39, 6, 2), "oliva"),
    ((1, 41, 5, 3), "magenta"), ((6, 41, 3, 3), "grafito"), ((14, 41, 5, 3), "acero"),
    ((19, 41, 3, 3), "magenta"), ((1, 44, 5, 2), "ambar"), ((6, 44, 3, 2), "cobre"), ((14, 44, 5, 2), "lima"),
    ((19, 44, 3, 2), "cobalto"),
)

# Arboledas: (rect, cantidad, separación mínima en casillas) sobre los
# jardines tecno cercados ('J'); la especie sale de la zona de cada casilla.
ARBOLEDAS = (
    ((1, 17, 4, 5), 3, 2), ((1, 29, 4, 4), 2, 2), ((57, 12, 6, 4), 3, 2), ((57, 31, 6, 4), 3, 2),
    ((21, 1, 5, 3), 2, 2), ((33, 1, 5, 3), 2, 2), ((10, 20, 5, 3), 2, 2), ((47, 31, 6, 3), 2, 2),
    ((9, 41, 5, 5), 3, 2), ((57, 41, 6, 5), 3, 2),
)

# Aparición inicial: en la Plaza, junto a su nodo.
SPAWN = (30, 26)

# Nodos del grafo de calles: la casilla de calle donde está cada uno.
# Los de los edificios están en la calle frente a su puerta.
NODOS_CALLE = {
    ZONA_PLAZA: (30, 25),
    CRUCE_NORTE: (34, 10),
    CRUCE_SUR: (25, 38),
    CRUCE_OESTE: (6, 25),
    CRUCE_ESTE: (54, 25),
    ZONA_COLEGIO: (15, 10),
    ZONA_ALCALDIA: (51, 8),
    ZONA_HOSPITAL: (14, 38),
    ZONA_EMPRESA_MEDIOS: (46, 42),
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


def _columna_salteando(col, filas):
    return tuple((col, fila) for fila in filas)


# Sección de la avenida: aceras y carriles; la fila 26 es el camellón (ya sólido).
SECCION_AVENIDA = (23, 24, 25, 27, 28, 29)

TRAMOS = [
    # Radios de la Plaza (el norte y el sur salen desplazados: molinete)
    # Dentro de la Plaza cada radio va por su propia fila (23 y 28): ningún eje comparte casillas con otro.
    Tramo(ZONA_PLAZA, CRUCE_NORTE, ((30, 25), (30, 23), (34, 23), (34, 10)), _fila(15, 33, 36)),
    Tramo(ZONA_PLAZA, CRUCE_SUR, ((30, 25), (30, 28), (25, 28), (25, 38)), _fila(36, 24, 27)),
    Tramo(ZONA_PLAZA, CRUCE_OESTE, ((30, 25), (6, 25)), _columna_salteando(14, SECCION_AVENIDA)),
    Tramo(ZONA_PLAZA, CRUCE_ESTE, ((30, 25), (54, 25)), _columna_salteando(48, SECCION_AVENIDA)),
    # Anillo exterior
    Tramo(CRUCE_NORTE, ZONA_COLEGIO, ((34, 10), (15, 10)), _columna(24, 9, 12)),
    Tramo(ZONA_COLEGIO, CRUCE_OESTE, ((15, 10), (6, 10), (6, 25)), _fila(17, 5, 8)),
    Tramo(CRUCE_OESTE, ZONA_HOSPITAL, ((6, 25), (6, 38), (14, 38)), _fila(32, 5, 8)),
    Tramo(ZONA_HOSPITAL, CRUCE_SUR, ((14, 38), (25, 38)), _columna(20, 37, 40)),
    Tramo(CRUCE_SUR, ZONA_EMPRESA_MEDIOS, ((25, 38), (31, 38), (31, 42), (46, 42)), _columna(42, 41, 44)),
    Tramo(ZONA_EMPRESA_MEDIOS, CRUCE_ESTE, ((46, 42), (54, 42), (54, 25)), _fila(36, 53, 56)),
    Tramo(CRUCE_ESTE, ZONA_ALCALDIA, ((54, 25), (54, 8), (51, 8)), _fila(17, 53, 56)),
    Tramo(ZONA_ALCALDIA, CRUCE_NORTE, ((51, 8), (34, 8), (34, 10)), _columna(37, 7, 10)),
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
    """True si no se puede pisar: edificio, casa, muro, jardín, canal, un prop,
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
    PLAZA, PARQUE, SENDEROS_PARQUE | ACCESOS_BOLSILLOS, EDIFICIOS.values(), ARBOLEDAS,
)
# Casillas que la decoración vuelve sólidas (las suma es_solida).
PROPS_SOLIDOS = frozenset(casilla for prop in DECORACION if prop.solido for casilla in prop.casillas)
