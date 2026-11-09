"""Decoración de Ciudad Nova por datos y reglas (lógica pura, sin Pygame).

`generar(...)` recibe el mapa de casillas y lo que no se puede tapar y
devuelve una tupla de Prop: (tipo, casilla, orientación, capa, sólido,
variante). Nada se pone a mano casilla por casilla: las reglas viven
aquí y los números (espaciados, semilla) en balance.py.

Reglas:
    - Farolas: a lo largo de cada tramo de calle, en las dos aceras
      (eje ± 2), cada ESPACIADO_FAROLAS casillas desde MARGEN_FAROLAS_CRUCE.
      Si una cae sobre algo reservado se salta (el hueco queda múltiplo del
      espaciado).
    - Mobiliario de acera: papeleras, canteros, buzones e hidrantes, por
      turnos, cada ESPACIADO_MOBILIARIO_ACERA casillas en las mismas aceras,
      corridos medio espaciado de farola para no chocar con ellas.
    - Plaza: bancas en pares simétricos respecto de su centro, mirando al
      paseo; farolas, canteros y árboles de acento en sus cuatro esquinas.
    - Parque: sendero libre; pares de bancas a los lados del sendero
      mirándolo; farolas a lo largo del sendero; ARBOLES_PARQUE árboles
      agrupados al azar (semilla fija) sin pisar el sendero ni tocarse.
    - Hileras en avenidas: árboles cada ESPACIADO_ARBOLES_AVENIDA casillas
      sobre los setos ('T') que dan a una acera (ya eran sólidos).
    - Jardines decorativos (fila libre del norte, patio del Colegio y
      jardín entre edificios): árboles y mobiliario por posiciones fijas.

Nunca se coloca un prop sobre: calles, el eje de un tramo, la sección de
una barricada, un nodo, una puerta, la casilla frente a una puerta (y sus
vecinas), el spawn o un sendero. Todo prop es sólido salvo los de capa
"suelo" (hoy ninguno), así que tampoco corta un paso: las aceras corren
junto a calles que siguen libres.
"""

import random
from dataclasses import dataclass

from src.core.balance import (
    ARBOLES_PARQUE,
    ESPACIADO_ARBOLES_AVENIDA,
    ESPACIADO_FAROLAS,
    ESPACIADO_MOBILIARIO_ACERA,
    MARGEN_FAROLAS_CRUCE,
    SEMILLA_DECORACION,
    SEPARACION_ARBOLES_PARQUE,
)

CAPA_SUELO = "suelo"
CAPA_OBJETO = "objeto"
CAPA_ARBOL = "arbol"

NORTE, SUR, ESTE, OESTE = "N", "S", "E", "O"

# Variantes de árbol (número del pack Trees_Vol2; arte en assets.RUTA_ARBOLES).
ARBOLES_AVENIDA = (57, 62, 67)
ARBOLES_PARQUE_VARIANTES = (9, 12, 18, 52, 47, 24, 1, 3)
ARBUSTOS = (36, 38)
ARBOLES_NEON = (75, 78, 84)
MOBILIARIO_ACERA = ("basurero", "jardinera", "buzon", "hidrante")


@dataclass(frozen=True)
class Prop:
    tipo: str  # "farola", "banca", "arbol"... (el arte lo resuelve src/ui/decoracion_ciudad.py)
    casilla: tuple
    orientacion: str = SUR  # hacia dónde mira (las bancas, al paseo)
    capa: str = CAPA_OBJETO
    solido: bool = True
    variante: int = 0  # árboles: número del pack


def generar(mapa, calles, tramos, nodos, entradas, spawn, plaza, parque, senderos, jardines, edificios=(),
            semilla=SEMILLA_DECORACION):
    """Tupla de Prop de toda la ciudad.

    mapa: lista de cadenas (ciudad_mapa.MAPA); calles: letras de calle;
    tramos: [(puntos, seccion)] de cada arista; nodos y entradas: casillas;
    plaza y parque: rects (col, fila, ancho, alto); senderos: casillas del
    sendero del parque; jardines: [(tipo, casilla, variante)] fijos;
    edificios: rects de sus huellas (ningún árbol de hilera a menos de 2
    casillas: su copa taparía la fachada)."""
    rng = random.Random(semilla)
    reservadas = _reservadas(mapa, calles, tramos, nodos, entradas, spawn, senderos)
    props = {}  # casilla -> Prop (una sola cosa por casilla)

    def poner(prop):
        col, fila = prop.casilla
        if prop.casilla in props or prop.casilla in reservadas:
            return False
        if not (0 <= fila < len(mapa) and 0 <= col < len(mapa[0])):
            return False
        props[prop.casilla] = prop
        return True

    _plaza(poner, plaza)
    _parque(poner, mapa, parque, senderos, rng)
    _aceras(poner, mapa, tramos, plaza)
    _hileras_de_avenida(poner, mapa, rng, edificios)
    for tipo, casilla, variante in jardines:
        capa = CAPA_ARBOL if tipo == "arbol" else CAPA_OBJETO
        poner(Prop(tipo, casilla, SUR, capa, True, variante))
    return tuple(sorted(props.values(), key=lambda p: (p.casilla[1], p.casilla[0])))


# ----------------------------------------------------------------------
# Lo que nunca se tapa
# ----------------------------------------------------------------------

def _reservadas(mapa, calles, tramos, nodos, entradas, spawn, senderos):
    reservadas = set(nodos) | set(senderos) | {spawn}
    for fila, linea in enumerate(mapa):
        for col, letra in enumerate(linea):
            if letra in calles:
                reservadas.add((col, fila))
    for puntos, seccion in tramos:
        reservadas |= set(casillas_eje(puntos)) | set(seccion)
    for col, fila in entradas:
        for dc in (-1, 0, 1):
            for df in (0, 1, 2):
                reservadas.add((col + dc, fila + df))  # la puerta y el paso frente a ella
    return reservadas


def casillas_eje(puntos):
    """Casillas del eje de un tramo (de punto en punto, en línea recta)."""
    casillas = [puntos[0]]
    for (c0, f0), (c1, f1) in zip(puntos, puntos[1:]):
        paso_c, paso_f = (c1 > c0) - (c1 < c0), (f1 > f0) - (f1 < f0)
        col, fila = c0, f0
        while (col, fila) != (c1, f1):
            col, fila = col + paso_c, fila + paso_f
            casillas.append((col, fila))
    return casillas


def _dentro(rect, casilla):
    col, fila, ancho, alto = rect
    return col <= casilla[0] < col + ancho and fila <= casilla[1] < fila + alto


# ----------------------------------------------------------------------
# Reglas
# ----------------------------------------------------------------------

def _aceras(poner, mapa, tramos, plaza):
    """Farolas a intervalos regulares y mobiliario por turnos en las dos
    aceras de cada tramo recto (fuera de la Plaza, que tiene las suyas)."""
    turno = 0
    for puntos, _ in tramos:
        for (c0, f0), (c1, f1) in zip(puntos, puntos[1:]):
            horizontal = f0 == f1
            desde, hasta = (min(c0, c1), max(c0, c1)) if horizontal else (min(f0, f1), max(f0, f1))
            for lado in (-2, 2):
                for paso in range(desde + MARGEN_FAROLAS_CRUCE, hasta - MARGEN_FAROLAS_CRUCE + 1):
                    casilla = (paso, f0 + lado) if horizontal else (c0 + lado, paso)
                    if _dentro(plaza, casilla) or _letra(mapa, casilla) != ":":
                        continue
                    desplazamiento = paso - desde - MARGEN_FAROLAS_CRUCE
                    if desplazamiento % ESPACIADO_FAROLAS == 0:
                        poner(Prop("farola", casilla, SUR if lado < 0 else NORTE))
                    elif desplazamiento % ESPACIADO_MOBILIARIO_ACERA == ESPACIADO_FAROLAS // 2:
                        if poner(Prop(MOBILIARIO_ACERA[turno % len(MOBILIARIO_ACERA)], casilla)):
                            turno += 1


def _plaza(poner, plaza):
    """Simetría respecto del centro de la Plaza: el paseo en cruz queda libre."""
    col, fila, ancho, alto = plaza
    cx, cy = col + ancho // 2, fila + alto // 2
    for dx in (-5, 5):
        for dy in (-4, 4):
            mira = SUR if dy < 0 else NORTE  # hacia el centro
            poner(Prop("banca", (cx + dx, cy + dy), mira))
            poner(Prop("jardinera", (cx + dx + (2 if dx > 0 else -2), cy + dy)))
            poner(Prop("farola", (cx + (6 if dx > 0 else -6), cy + (3 if dy > 0 else -3))))
    for dx in (-7, 7):
        poner(Prop("arbol", (cx + dx, cy + 5), SUR, CAPA_ARBOL, True, ARBOLES_NEON[0 if dx < 0 else 2]))


def _parque(poner, mapa, parque, senderos, rng):
    """Bancas enfrentadas a ambos lados del sendero, farolas a lo largo de
    él y árboles agrupados (semilla fija) en el pasto."""
    col, fila, ancho, alto = parque
    horizontales = sorted(c for c in senderos if _letra(mapa, (c[0], c[1] - 1)) == "." and _letra(mapa, (c[0], c[1] + 1)) == ".")
    for indice, (c, f) in enumerate(horizontales):
        if indice % ESPACIADO_FAROLAS == 1:
            poner(Prop("farola", (c, f - 1), SUR))
        elif indice % ESPACIADO_FAROLAS == 4:
            poner(Prop("banca", (c, f - 1), SUR))  # par simétrico: una mira al sur...
            poner(Prop("banca", (c, f + 1), NORTE))  # ...y la otra al norte, al sendero
    libres = [(c, f) for f in range(fila, fila + alto) for c in range(col, col + ancho)
              if _letra(mapa, (c, f)) == "." and all(abs(c - s[0]) + abs(f - s[1]) > 1 for s in senderos)]
    rng.shuffle(libres)
    puestos = []
    for casilla in libres:
        if len(puestos) >= ARBOLES_PARQUE:
            break
        if any(max(abs(casilla[0] - p[0]), abs(casilla[1] - p[1])) < SEPARACION_ARBOLES_PARQUE for p in puestos):
            continue
        variante = rng.choice(ARBOLES_PARQUE_VARIANTES)
        if poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, variante)):
            puestos.append(casilla)


def _hileras_de_avenida(poner, mapa, rng, edificios):
    """Árboles cada ESPACIADO_ARBOLES_AVENIDA casillas sobre los tramos
    rectos de seto que dan a una acera, lejos de las fachadas."""
    for horizontal in (True, False):
        for corrida in _corridas_de_seto(mapa, horizontal):
            for i, casilla in enumerate(corrida):
                if any(_distancia_a_rect(casilla, rect) <= 2 for rect in edificios):
                    continue
                if i % ESPACIADO_ARBOLES_AVENIDA == 1:
                    poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, rng.choice(ARBOLES_AVENIDA)))


def _corridas_de_seto(mapa, horizontal, minimo=4):
    """Listas de casillas 'T' seguidas (en fila o en columna) que tocan una acera."""
    filas, columnas = len(mapa), len(mapa[0])

    def da_a_acera(c, f):
        return any(_letra(mapa, (c + dc, f + df)) == ":" for dc, df in ((0, -1), (0, 1), (-1, 0), (1, 0)))

    corridas = []
    externo = range(filas) if horizontal else range(columnas)
    interno = range(columnas) if horizontal else range(filas)
    for a in externo:
        actual = []
        for b in interno:
            c, f = (b, a) if horizontal else (a, b)
            if _letra(mapa, (c, f)) == "T" and da_a_acera(c, f):
                actual.append((c, f))
                continue
            if len(actual) >= minimo:
                corridas.append(actual)
            actual = []
        if len(actual) >= minimo:
            corridas.append(actual)
    return corridas


def _distancia_a_rect(casilla, rect):
    """Distancia de Chebyshev (en casillas) de `casilla` a un rect (col, fila, ancho, alto)."""
    col, fila, ancho, alto = rect
    dx = max(col - casilla[0], 0, casilla[0] - (col + ancho - 1))
    dy = max(fila - casilla[1], 0, casilla[1] - (fila + alto - 1))
    return max(dx, dy)


def _letra(mapa, casilla):
    col, fila = casilla
    if 0 <= fila < len(mapa) and 0 <= col < len(mapa[fila]):
        return mapa[fila][col]
    return None
