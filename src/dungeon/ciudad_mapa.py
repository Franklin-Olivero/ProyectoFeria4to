"""Ciudad Nova como mapa 2D de casillas (datos y funciones puras, sin Pygame).

El mundo es una cuadrícula de 64x47 casillas de TAM_CASILLA px (48),
más grande que la ventana: la cámara sigue al jugador. Cada carácter de
MAPA es una casilla:

    .  césped (parques, transitable)  #  edificio de zona (sólido)
    :  banqueta / plaza / sendero     H  edificio secundario (sólido; uno de CASAS)
    c  calle (2 carriles)             J  jardín: pasto con árboles y arbustos (sólido)
    k  camellón arbolado (sólido)     ~  alberca del parque (sólida)
    E  entrada de edificio            F  fuente (sólida)
    X  barricada de la Alcaldía (sólida solo mientras está sellada)

Plano verde: las calles son la estructura (Avenida Nova con camellón
arbolado de oeste a este, radios en molinete desde la Plaza, codo al
norte y Z al sur hacia Medios) y entre ellas casi todo es verde: el
Parque Central (abierto a la Plaza, senderos en cruz y una alberca
chica), el Jardín del Colegio, jardines al frente de cada edificio y
manzanas de jardín con árboles. Pocos edificios bien separados: los 4
de zona (puerta al sur, jardín delante y un sendero hasta la banqueta)
y 6 secundarios (CASAS). Bolsillos sin salida (cada uno da a un solo
tramo o a un nodo): Plaza cívica, Parque Central (a la Plaza), Jardín
del Colegio, Paseo comercial (al radio sur), los senderos de los
secundarios y el lote del Distrito Liminal (bajo el Cruce Sur). Ninguno
permite rodear una barricada.

Las calles forman un grafo (src/dungeon/grafo_ciudad.py): NODOS_CALLE
dice en qué casilla está cada nodo y TRAMOS, por qué casillas pasa cada
arista y cuál es su sección transversal, donde se levanta su barricada
cuando la calle se satura. Cada sección va de un sólido a otro (banqueta,
calle, banqueta; el camellón ya es sólido), así una barricada corta el paso.

Decoración (farolas, bancas, árboles...): se genera por reglas en
src/dungeon/layout_decoracion.py sobre este mapa; las casillas de los
props sólidos se suman a es_solida (PROPS_SOLIDOS). El dibujo por
auto-tiling vive en src/dungeon/autotile_ciudad.py (puro) y
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
JARDIN = "J"
ENTRADA = "E"
BARRICADA = "X"
FUENTE = "F"
AGUA = "~"

CALLES = (CALLE,)
SOLIDAS = (EDIFICIO, CASA, JARDIN, CAMELLON, FUENTE, AGUA)
VERDES = (PASTO, JARDIN, CAMELLON)  # vegetación (para medir el área verde)

MAPA = [
    "JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
    "JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
    "JJJJJJJJJJ###########JJJJJJJJJJJJJJJJJJ::::::J###########JJJJJJJ",
    "JJHHHHHHJJ###########JJJHHHHHHJJJJJJJJJ::FF::J###########JJJJJJJ",
    "JJHHHHHHJJ###########JJJHHHHHHJJJJJJJJJ::FF::J###########JJJJJJJ",
    "JJHHHHHHJJ###########JJJHHHHHHJJJJJJJJJ::::::J#####E#####JJJJJJJ",
    "JJJJJ:JJJJ###########JJJHHHHHHJJJJJJJJJ::::::JJJJJXXXJJJJJJJJJJJ",
    "JJJJJ:JJJJ#####E#####JJJJJJ:JJJJJ::::::::::::::::::::::::JJJJJJJ",
    "JJJJJ:JJJJJJJJJ:JJJJJJJJJJJ:JJJJJ:cccccccccccccccccccccc:JJJJJJJ",
    "JJJJJ:::::::::::::::::::::::::::::cccccccccccccccccccccc:JJJJJJJ",
    "JJJJJ:cccccccccccccccccccccccccccccc::::::::::::::::::cc:JJJJJJJ",
    "JJJJJ:cccccccccccccccccccccccccccccc:JJJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc::::::::::::::::::::::::::cc:J......:.......J:cc:JJJJJJJ",
    "JJJJJ:cc:JJJJJJ::JJJJJJJJJJJJJJJJ:cc:J......:.~~~...J:cc:JJJJJJJ",
    "JJJJJ:cc:J.....::...............J:cc:J......:.~~~...J:cc:HHHHHJJ",
    "JJJJJ:cc:J.....::...............J:cc:J......:.......J:cc:HHHHHJJ",
    "JJJJJ:cc:J.....::...............J:cc:J......:.......J:cc:HHHHHJJ",
    "JJJJJ:cc:J::::::::::::::::::::::J:cc:J::::::::::::::J:cc:HHHHHJJ",
    "JJJJJ:cc:J............JJJJJJJJJJJ:cc:J......:.......J:cc::::..JJ",
    "JJJJJ:cc:J............J::::::::::::::::.....:.......J:cc:JJJJJJJ",
    "JJJJJ:cc:J............J::::::FF::::::::.....:.......J:cc:JJJJJJJ",
    "JJJJJ:cc:J............J::::::FF::::::::.....:.......J:cc:JJJJJJJ",
    "JJJJJ:cc:JJJJJJJJJJJJJJ:::::::::::::::JJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc::::::::::::::::::::::::::::::::::::::::::::::cc:JJJJJJJ",
    "JJJJJ:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:JJJJJJJ",
    "JJJJJ:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:JJJJJJJ",
    "JJJJJ:cccckkkkkkkkkkkcc:::::::::::::::ccckkkkkkkkkkkcccc:JJJJJJJ",
    "JJJJJ:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:JJJJJJJ",
    "JJJJJ:ccccccccccccccccc:::::::::::::::cccccccccccccccccc:JJJJJJJ",
    "JJJJJ:cc::::::::::::::::::::::::::::::::::::::::::::::cc:JJJJJJJ",
    "JJJJJ:cc:###########JJJ:::::::::::::::JJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc:###########JJJ:::::::::::::::JJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc:###########JJJJ:cc:HHHHHJHHHHJJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc:###########JJJJ:cc:HHHHHJHHHHJJJJJJJJJJJJJJJ:cc:JJJJJJJ",
    "JJJJJ:cc:###########JJJJ:cc:::::::::::JJJ###########J:cc:JJJJJJJ",
    "JJJJJ:cc:#####E#####JJJJ:cc:::::::::::JJJ###########J:cc:JJJJJJJ",
    "JJJJJ:cc:JJJJJ:JJJJJJJJJ:cc:JJJJJJJJJJJJJ###########J:cc:JJJJJJJ",
    "JJJJJ:cc:::::::::::::::::cc:::::::JJJJJJJ###########J:cc:JJJJJJJ",
    "JJJJJ:ccccccccccccccccccccccccccc:JJJJJJJ###########J:cc:HHHHHJJ",
    "JJJJJ:ccccccccccccccccccccccccccc:JJJJJJJ#####E#####J:cc:HHHHHJJ",
    "JJJJJ::::::::::::::::::::::::::cc:JJJJJJJJJJJJ:JJJJJJ:cc:HHHHHJJ",
    "JJJJJJJJJJJJJJJJJJJJJJ:::::::J:cc:::::::::::::::::::::cc:HHHHHJJ",
    "JJJJJJJJJJJJJJJJJJJJJJ:::::::J:ccccccccccccccccccccccccc::::..JJ",
    "JJJJJJJJJJJJJJJJJJJJJJ:::::::J:ccccccccccccccccccccccccc:JJJJJJJ",
    "JJJJJJJJJJJJJJJJJJJJJJ:::::::J:::::::::::::::::::::::::::JJJJJJJ",
    "JJJJJJJJJJJJJJJJJJJJJJ:::::::JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
    "JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
]

COLUMNAS = len(MAPA[0])
FILAS = len(MAPA)
TAM_MUNDO = (COLUMNAS * TAM_CASILLA, FILAS * TAM_CASILLA)

# Edificios de zona: (columna, fila, ancho, alto) en casillas. Todas las
# puertas miran al sur (fachada estilo Pokémon); delante, una fila de
# jardín con un sendero de la puerta a la banqueta.
EDIFICIOS = {
    ZONA_COLEGIO: (10, 2, 11, 6),
    ZONA_ALCALDIA: (46, 2, 11, 4),
    ZONA_HOSPITAL: (9, 30, 11, 6),
    ZONA_EMPRESA_MEDIOS: (41, 34, 11, 6),
}
# Casilla de la puerta (una 'E' del mapa) de cada edificio.
ENTRADAS = {
    ZONA_COLEGIO: (15, 7),
    ZONA_ALCALDIA: (51, 5),
    ZONA_HOSPITAL: (14, 35),
    ZONA_EMPRESA_MEDIOS: (46, 39),
}
# Casillas 'X' en el jardín de la Alcaldía, sobre su sendero: sólidas
# mientras está sellada.
BARRICADAS_ALCALDIA = frozenset(
    (col, fila) for fila, linea in enumerate(MAPA) for col, letra in enumerate(linea) if letra == BARRICADA
)

# Plaza central: (columna, fila, ancho, alto). Es banqueta ':' para la
# lógica (losa gris, como el parque) con una fuente chica al norte.
PLAZA = (23, 19, 15, 13)
FUENTE_PLAZA = (29, 20, 2, 2)

# Plaza de la Alcaldía (zona cívica): losas con una fuente chica; se entra
# desde la banqueta norte de su calle.
PLAZA_CIVICA = (39, 2, 6, 5)
FUENTE_CIVICA = (41, 3, 2, 2)

# Parque Central (cuadrante noreste): césped, senderos en cruz y una
# alberca chica; se entra desde la Plaza (columna 38, filas 19-21).
PARQUE = (38, 12, 14, 10)
ALBERCA = (46, 13, 3, 2)
ENTRADA_PARQUE = ((38, 19), (38, 20), (38, 21))
# Jardín del Colegio (cuadrante noroeste): césped con senderos; un seto lo
# rodea (también frente a la Plaza) y se entra solo por (15-16, 13), desde
# la banqueta de la calle del Colegio.
JARDIN_COLEGIO = (10, 13, 22, 9)
PARQUES = (PARQUE, JARDIN_COLEGIO)
SENDEROS_PARQUE = frozenset(  # las losas de la Plaza (que asoman en el rect del jardín) no cuentan
    (col, fila) for c0, f0, ancho, alto in PARQUES for fila in range(f0, f0 + alto)
    for col in range(c0, c0 + ancho) if MAPA[fila][col] == ACERA
    and not (PLAZA[0] <= col < PLAZA[0] + PLAZA[2] and PLAZA[1] <= fila < PLAZA[1] + PLAZA[3])
)
PASEO_COMERCIAL = (28, 34, 10, 2)  # calle peatonal con tiendas al norte y jardín al sur, abierta al radio sur
# Entradas de los bolsillos y senderos de los edificios secundarios: la
# decoración nunca los tapa (como los senderos del parque).
ACCESOS_BOLSILLOS = frozenset([
    (27, 34), (27, 35),  # Paseo comercial, desde la banqueta del radio sur
    (15, 12), (16, 12), (15, 13), (16, 13),  # Jardín del Colegio
    (41, 7), (42, 7),  # plaza cívica
    (37, 19), (37, 20), (37, 21),  # Parque Central, desde la Plaza
    (24, 40), (25, 40), (26, 40),  # lote del Distrito Liminal (zonas_ciudad.ACCESO_LIMINAL)
    (5, 6), (5, 7), (5, 8), (5, 9),  # sendero de la tienda de barrio
    (27, 7), (27, 8), (27, 9),  # sendero de los apartamentos junto al Colegio
    (57, 18), (58, 18), (59, 18), (56, 18),  # sendero de los apartamentos del este (su patio: 60-61)
    (57, 42), (58, 42), (59, 42), (56, 42),  # sendero de los apartamentos del sureste (su patio: 60-61)
])

# Edificios secundarios: sprites completos (pixel art de casas_render) con
# su huella (col, fila, ancho, alto) y su estilo (assets.ESTILOS_CASA).
# Juntos cubren exactamente las 'H' del mapa; nunca dos iguales cerca.
CASAS = (
    ((28, 32, 5, 2), "salvia"),  # tienda con toldo del Paseo comercial
    ((34, 32, 4, 2), "madera"),  # café con toldo del Paseo comercial
    ((24, 3, 6, 4), "ladrillo"),  # apartamentos junto al Colegio
    ((57, 14, 5, 4), "pizarra"),  # apartamentos del este
    ((57, 38, 5, 4), "estuco"),  # apartamentos del sureste
    ((2, 3, 6, 3), "terracota"),  # tienda de barrio del noroeste
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
    """True si no se puede pisar: edificio, casa, jardín, camellón, agua, un prop,
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
    PLAZA, PARQUES, SENDEROS_PARQUE | ACCESOS_BOLSILLOS,
    list(EDIFICIOS.values()) + [huella for huella, _ in CASAS],
)
# Casillas que la decoración vuelve sólidas (las suma es_solida).
PROPS_SOLIDOS = frozenset(casilla for prop in DECORACION if prop.solido for casilla in prop.casillas)
