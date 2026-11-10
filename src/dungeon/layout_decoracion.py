"""Decoración de Ciudad Nova por datos y reglas (lógica pura, sin Pygame).

`generar(...)` recibe el mapa de casillas y lo que no se puede tapar y
devuelve una tupla de Prop: (tipo, casilla, orientación, capa, sólido,
variante). Nada se pone a mano casilla por casilla: las reglas viven
aquí y los números (espaciados, semilla) en balance.py.

Reglas:
    - Aceras: las líneas de acera de cada tramo recto se miden en el mapa
      (lineas_de_acera: desde el eje se avanza en perpendicular por la
      calle hasta la primera casilla que no es calle). En cada acera,
      farolas cada ESPACIADO_FAROLAS casillas desde MARGEN_FAROLAS_CRUCE y,
      corrido medio espaciado, mobiliario por turnos (cajas eléctricas,
      papeleras, transformadores, hidrantes). Si una cae sobre algo
      reservado o sobre un puente se salta (el hueco queda múltiplo del
      espaciado).
    - Camellón de la avenida ('k'): una hilera de árboles cada
      ESPACIADO_ARBOLES_AVENIDA casillas.
    - Plaza: bancas en pares simétricos respecto de su centro, mirando al
      centro; faroles y canteros en sus cuatro cuadrantes y árboles neón
      en las esquinas de abajo.
    - Parque: sendero libre; pares de bancas a los lados del sendero
      mirándolo; farolas a lo largo de él; ARBOLES_PARQUE árboles
      agrupados al azar (semilla fija) sin pisar el sendero ni tocarse.
    - Zonas (src/dungeon/zonas_ciudad.py): cada farola toma el modelo de
      su zona y cada árbol una especie de su zona; los hitos de cada zona
      (máquinas, tótems, servidores, terrazas...) van en sus casillas, con
      su huella de varias casillas si la tienen.
    - Arboledas: ARBOLEDAS (rect, cantidad, separación) sobre los jardines
      tecno ('J'), con la semilla fija, sin tocarse entre sí.

Nunca se coloca un prop sobre: calles, el eje de un tramo, la sección de
una barricada, un nodo, una puerta, la casilla frente a una puerta (y sus
vecinas), el spawn o un sendero. Las aceras miden una casilla: un prop
sobre ellas no corta el paso, porque la calle de al lado sigue libre.
"""

import random
from dataclasses import dataclass

from src.dungeon import zonas_ciudad
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
ACERA, PASTO, JARDIN, CAMELLON, AGUA = ":", ".", "J", "k", "~"
# Letras del mapa donde puede ir un prop: pasto y acera/plaza; los árboles
# además en los jardines tecno y el camellón (ya sólidos). Nunca calle,
# edificio, casa, muro, agua ni puerta.
LIBRES = (PASTO, ACERA, JARDIN, CAMELLON)
SOLO_ARBOLES = (JARDIN, CAMELLON)
FAROLAS = ("farola", "farola_ornamental", "farola_baja", "farola_curva", "farola_jardin", "farola_farol")

# Variantes de árbol (número del pack Trees_Vol2; arte en assets.RUTA_ARBOLES).
ARBOLES_AVENIDA = (57, 62, 67)
ARBOLES_PARQUE_VARIANTES = (9, 12, 18, 52, 47, 24, 1, 3)
ARBOLES_NEON = (75, 78, 84)
MOBILIARIO_ACERA = ("caja_electrica", "basurero", "transformador", "hidrante")


@dataclass(frozen=True)
class Prop:
    tipo: str  # "farola", "banca", "arbol"... (el arte lo resuelve src/ui/decoracion_ciudad.py)
    casilla: tuple
    orientacion: str = SUR  # hacia dónde mira (las bancas, al paseo)
    capa: str = CAPA_OBJETO
    solido: bool = True
    variante: int = 0  # árboles: número del pack
    ancho: int = 1  # huella en casillas desde `casilla` (esquina superior izquierda)
    alto: int = 1

    @property
    def casillas(self):
        col, fila = self.casilla
        return tuple((col + dc, fila + df) for df in range(self.alto) for dc in range(self.ancho))

    @property
    def base(self):
        """(col, fila) de la casilla inferior central de la huella: donde se apoya."""
        return (self.casilla[0] + self.ancho // 2, self.casilla[1] + self.alto - 1)


def generar(mapa, calles, tramos, nodos, entradas, spawn, plaza, parque, senderos, edificios=(), arboledas=(),
            semilla=SEMILLA_DECORACION, zonas=None):
    """Tupla de Prop de toda la ciudad.

    mapa: lista de cadenas (ciudad_mapa.MAPA); calles: letras de calle;
    tramos: [(puntos, seccion)] de cada arista; nodos y entradas: casillas;
    plaza y parque: rects (col, fila, ancho, alto); senderos: casillas del
    sendero del parque; edificios: rects de sus huellas (ningún árbol a
    menos de 2 casillas: su copa taparía la fachada); arboledas:
    [(rect, cantidad, separación)]; zonas: {id: Zona} (por defecto las de
    zonas_ciudad)."""
    rng = random.Random(semilla)
    zonas = zonas_ciudad.ZONAS if zonas is None else zonas
    reservadas = _reservadas(mapa, calles, tramos, nodos, entradas, spawn, senderos)
    ocupadas = {}  # casilla -> Prop (una sola cosa por casilla)

    def poner(prop):
        celdas = prop.casillas
        if any(c in ocupadas or c in reservadas for c in celdas):
            return False
        if not all(0 <= f < len(mapa) and 0 <= c < len(mapa[0]) and mapa[f][c] in LIBRES for c, f in celdas):
            return False
        if prop.tipo != "arbol" and any(mapa[f][c] in SOLO_ARBOLES for c, f in celdas):
            return False  # en jardines y camellón solo van árboles
        for celda in celdas:
            ocupadas[celda] = prop
        return True

    def arbol_cerca(casilla, separacion):
        return any(p.tipo == "arbol" and max(abs(casilla[0] - c[0]), abs(casilla[1] - c[1])) < separacion
                   for c, p in ocupadas.items())

    for id_zona in zonas_ciudad.ORDEN_ZONAS:  # primero los hitos: son la identidad de cada zona
        for hito in zonas[id_zona].hitos:
            capa = CAPA_ARBOL if hito.tipo == "arbol" else CAPA_OBJETO
            poner(Prop(hito.tipo, hito.casilla, hito.orientacion, capa, True, hito.variante, hito.ancho, hito.alto))
    _plaza(poner, plaza)
    _parque(poner, mapa, parque, senderos, rng, arbol_cerca)
    _aceras(poner, mapa, calles, tramos, plaza)
    _camellon(poner, mapa, rng)
    for rect, cantidad, separacion in arboledas:
        _arboleda(poner, mapa, rect, cantidad, separacion, rng, arbol_cerca, edificios)
    unicos = {id(p): p for p in ocupadas.values()}.values()
    return tuple(sorted(unicos, key=lambda p: (p.casilla[1], p.casilla[0])))


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


def lineas_de_acera(mapa, calles, inicio, fin):
    """Desplazamientos perpendiculares (con signo) de las aceras de un
    tramo recto de `inicio` a `fin`: desde la casilla de calle del eje más
    cercana a su punto medio se avanza hacia cada lado mientras haya calle;
    si se llega a una acera, ese es su desplazamiento. Si en el camino hay
    un camellón, se cruza y se sigue (la avenida tiene aceras a los dos
    lados de sus dos calzadas). Un segmento sin calle (el que cruza la
    Plaza) no tiene aceras.
    Devuelve [(desplazamiento, letra)] con letra ':' (acera) o 'k' (camellón)."""
    (c0, f0), (c1, f1) = inicio, fin
    horizontal = f0 == f1
    centro = ((c0 + c1) / 2, (f0 + f1) / 2)
    en_calle = [c for c in casillas_eje((inicio, fin)) if _letra(mapa, c) in calles]
    if not en_calle:
        return []
    medio = min(en_calle, key=lambda c: (abs(c[0] - centro[0]) + abs(c[1] - centro[1]), c))
    lineas = []
    for signo in (-1, 1):
        paso = 0
        while True:
            paso += signo
            casilla = (medio[0], medio[1] + paso) if horizontal else (medio[0] + paso, medio[1])
            letra = _letra(mapa, casilla)
            if letra in calles:
                continue
            if letra == CAMELLON:
                lineas.append((paso, CAMELLON))
                continue
            if letra == ACERA:
                lineas.append((paso, ACERA))
            break
    return lineas


# ----------------------------------------------------------------------
# Reglas
# ----------------------------------------------------------------------

def _junto_al_agua(mapa, casilla):
    c, f = casilla
    return any(_letra(mapa, (c + dc, f + df)) == AGUA for dc, df in ((0, -1), (0, 1), (-1, 0), (1, 0)))


def _aceras(poner, mapa, calles, tramos, plaza):
    """Farolas a intervalos regulares y mobiliario por turnos en las
    aceras de cada tramo recto (fuera de la Plaza y de los puentes)."""
    turno = 0
    for puntos, _ in tramos:
        for (c0, f0), (c1, f1) in zip(puntos, puntos[1:]):
            horizontal = f0 == f1
            desde, hasta = (min(c0, c1), max(c0, c1)) if horizontal else (min(f0, f1), max(f0, f1))
            for lado, letra in lineas_de_acera(mapa, calles, (c0, f0), (c1, f1)):
                if letra != ACERA:
                    continue
                for paso in range(desde + MARGEN_FAROLAS_CRUCE, hasta - MARGEN_FAROLAS_CRUCE + 1):
                    casilla = (paso, f0 + lado) if horizontal else (c0 + lado, paso)
                    if _dentro(plaza, casilla) or _letra(mapa, casilla) != ACERA or _junto_al_agua(mapa, casilla):
                        continue
                    desplazamiento = paso - desde - MARGEN_FAROLAS_CRUCE
                    if desplazamiento % ESPACIADO_FAROLAS == 0:
                        poner(Prop(zonas_ciudad.farola_de(*casilla), casilla, SUR if lado < 0 else NORTE))
                    elif desplazamiento % ESPACIADO_MOBILIARIO_ACERA == ESPACIADO_FAROLAS // 2:
                        if poner(Prop(MOBILIARIO_ACERA[turno % len(MOBILIARIO_ACERA)], casilla)):
                            turno += 1


def _camellon(poner, mapa, rng):
    """Hilera de árboles sobre el camellón de la avenida, a paso fijo."""
    for fila, linea in enumerate(mapa):
        columnas = [c for c, letra in enumerate(linea) if letra == CAMELLON]
        for i, col in enumerate(columnas):
            if i % ESPACIADO_ARBOLES_AVENIDA == 1:
                poner(Prop("arbol", (col, fila), SUR, CAPA_ARBOL, True, rng.choice(ARBOLES_AVENIDA)))


def _plaza(poner, plaza):
    """Simetría respecto del centro de la Plaza: los ejes de los radios y
    el emblema central quedan libres."""
    col, fila, ancho, alto = plaza
    cx, cy = col + ancho // 2, fila + alto // 2
    for dx in (-3, 3):
        for dy in (-4, 4):
            mira = SUR if dy < 0 else NORTE  # hacia el centro
            poner(Prop("banca", (cx + dx, cy + dy), mira))
            poner(Prop("jardinera", (cx + dx + (2 if dx > 0 else -2), cy + dy)))
            casilla = (cx + (6 if dx > 0 else -6), cy + (3 if dy > 0 else -3))
            poner(Prop(zonas_ciudad.farola_de(*casilla), casilla))
    for dx in (-7, 7):
        poner(Prop("arbol", (cx + dx, cy + 5), SUR, CAPA_ARBOL, True, ARBOLES_NEON[0 if dx < 0 else 2]))


def _parque(poner, mapa, parque, senderos, rng, arbol_cerca=lambda casilla, separacion: False):
    """Bancas enfrentadas a ambos lados del sendero, farolas a lo largo de
    él y árboles agrupados (semilla fija) en el pasto."""
    col, fila, ancho, alto = parque
    horizontales = sorted(c for c in senderos
                          if _letra(mapa, (c[0], c[1] - 1)) == PASTO and _letra(mapa, (c[0], c[1] + 1)) == PASTO)
    for indice, (c, f) in enumerate(horizontales):
        if indice % ESPACIADO_FAROLAS == 1:
            poner(Prop(zonas_ciudad.farola_de(c, f - 1), (c, f - 1), SUR))
        elif indice % ESPACIADO_FAROLAS == 3:
            poner(Prop("banca", (c, f - 1), SUR))  # par simétrico: una mira al sur...
            poner(Prop("banca", (c, f + 1), NORTE))  # ...y la otra al norte, al sendero
    libres = [(c, f) for f in range(fila, fila + alto) for c in range(col, col + ancho)
              if _letra(mapa, (c, f)) == PASTO and all(abs(c - s[0]) + abs(f - s[1]) > 1 for s in senderos)]
    rng.shuffle(libres)
    puestos = []
    for casilla in libres:
        if len(puestos) >= ARBOLES_PARQUE:
            break
        if arbol_cerca(casilla, SEPARACION_ARBOLES_PARQUE):
            continue
        variante = rng.choice(zonas_ciudad.arboles_de(*casilla, ARBOLES_PARQUE_VARIANTES))
        if poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, variante)):
            puestos.append(casilla)


def _arboleda(poner, mapa, rect, cantidad, separacion, rng, arbol_cerca=lambda casilla, separacion: False,
              edificios=()):
    """`cantidad` árboles de la especie de su zona en el jardín de `rect`,
    al azar con la semilla fija, a `separacion` casillas o más entre sí y
    nunca pegados a una fachada."""
    col, fila, ancho, alto = rect
    libres = [(c, f) for f in range(fila, fila + alto) for c in range(col, col + ancho)
              if _letra(mapa, (c, f)) in (JARDIN, PASTO)
              and not any(distancia_a_rect((c, f), huella) <= 1 for huella in edificios)]
    rng.shuffle(libres)
    puestos = []
    for casilla in libres:
        if len(puestos) >= cantidad:
            break
        if arbol_cerca(casilla, separacion):
            continue
        especie = rng.choice(zonas_ciudad.arboles_de(*casilla, ARBOLES_PARQUE_VARIANTES))
        if poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, especie)):
            puestos.append(casilla)


def distancia_a_rect(casilla, rect):
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
