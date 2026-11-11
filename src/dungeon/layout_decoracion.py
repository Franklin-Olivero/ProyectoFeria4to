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
      corrido medio espaciado, mobiliario discreto por turnos (papeleras,
      buzones, jardineras). Si una cae sobre algo reservado se salta (el
      hueco queda múltiplo del espaciado).
    - Camellón de la avenida ('k'): una hilera de árboles cada
      ESPACIADO_ARBOLES_AVENIDA casillas.
    - Plaza: bancas en pares simétricos respecto de su centro, mirando al
      centro; faroles y canteros en sus cuatro cuadrantes y árboles neón
      en las esquinas de abajo.
    - Parques (Parque Central y Jardín del Colegio): sendero libre; pares
      de bancas a los lados del sendero mirándolo; farolas a lo largo de
      él; ARBOLES_PARQUE árboles por parque, al azar (semilla fija), sin
      pisar el sendero ni tocarse.
    - Zonas (src/dungeon/zonas_ciudad.py): cada farola toma el modelo de
      su zona y cada árbol una especie de su zona; los hitos de cada zona
      (paradas, terrazas, bicicletas...) van en sus casillas, con su
      huella de varias casillas si la tienen.
    - Jardines ('J'): árboles en grupos naturales (centros separados,
      2-4 árboles por grupo alrededor de cada centro) y arbustos en el borde
      de los canteros que dan a la banqueta. Nunca un árbol pegado a un
      edificio ni a menos de ALTO_COPA_CASILLAS bajo su fachada (la copa la
      taparía).

Nunca se coloca un prop sobre: calles, el eje de un tramo, la sección de
una barricada, un nodo, una puerta, la casilla frente a una puerta (y sus
vecinas), el spawn o un sendero. Las aceras miden una casilla: un prop
sobre ellas no corta el paso, porque la calle de al lado sigue libre.
"""

import random
from dataclasses import dataclass

from src.dungeon import zonas_ciudad
from src.core.balance import (
    ALTO_COPA_CASILLAS,
    ARBOLES_PARQUE,
    ARBOLES_POR_GRUPO,
    ESPACIADO_ARBUSTOS,
    ESPACIADO_ARBOLES_AVENIDA,
    ESPACIADO_FAROLAS,
    ESPACIADO_MOBILIARIO_ACERA,
    MARGEN_FAROLAS_CRUCE,
    RADIO_GRUPO_ARBOLES,
    SEMILLA_DECORACION,
    SEPARACION_ARBOLES_JARDIN,
    SEPARACION_ARBOLES_PARQUE,
    SEPARACION_GRUPOS_ARBOLES,
)

CAPA_SUELO = "suelo"
CAPA_OBJETO = "objeto"
CAPA_ARBOL = "arbol"

NORTE, SUR, ESTE, OESTE = "N", "S", "E", "O"
ACERA, PASTO, JARDIN, CAMELLON, AGUA = ":", ".", "J", "k", "~"
# Letras del mapa donde puede ir un prop: pasto y banqueta/plaza; los
# árboles y arbustos además en los jardines y el camellón (ya sólidos).
# Nunca calle, edificio, casa, agua ni puerta.
LIBRES = (PASTO, ACERA, JARDIN, CAMELLON)
SOLO_ARBOLES = (JARDIN, CAMELLON)
FILAS_FAROLA = 2  # filas que una farola sube por encima de su casilla
FAROLAS = ("farola", "farola_ornamental", "farola_baja", "farola_curva", "farola_jardin", "farola_farol")

# Variantes de árbol (número del pack Trees_Vol2; arte en assets.RUTA_ARBOLES).
ARBOLES_AVENIDA = (57, 62, 67)
ARBOLES_PARQUE_VARIANTES = (9, 12, 18, 52, 47, 24, 1, 3)
ARBOLES_PLAZA = (27, 33)  # otoñales: acento cálido en las esquinas de la Plaza
ARBUSTOS = (36, 38)
MOBILIARIO_ACERA = ("basurero", "buzon", "jardinera")


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


def generar(mapa, calles, tramos, nodos, entradas, spawn, plaza, parques, senderos, edificios=(),
            semilla=SEMILLA_DECORACION, zonas=None):
    """Tupla de Prop de toda la ciudad.

    mapa: lista de cadenas (ciudad_mapa.MAPA); calles: letras de calle;
    tramos: [(puntos, seccion)] de cada arista; nodos y entradas: casillas;
    plaza: rect (col, fila, ancho, alto); parques: rects de los parques;
    senderos: casillas que ningún prop tapa (senderos de los parques y
    entradas de los bolsillos); edificios: huellas de todos los edificios
    (ningún árbol encima de su fachada); zonas: {id: Zona} (por defecto
    las de zonas_ciudad)."""
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
    for parque in parques:
        _parque(poner, mapa, parque, senderos, rng, arbol_cerca)
    _aceras(poner, mapa, calles, tramos, plaza, edificios)
    _camellon(poner, mapa, rng)
    _jardines(poner, mapa, rng, arbol_cerca, edificios)
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


def bajo_fachada(casilla, edificios, filas=FILAS_FAROLA):
    """True si un poste alto en `casilla` taparía un edificio: la huella
    queda a `filas` filas o menos por encima, en su misma columna (una
    farola mide dos jugadores y media: sube casi tres casillas)."""
    col, fila = casilla
    for c0, f0, ancho, alto in edificios:
        if c0 <= col < c0 + ancho and 0 < fila - (f0 + alto - 1) <= filas:
            return True
    return False


def _aceras(poner, mapa, calles, tramos, plaza, edificios=()):
    """Farolas a intervalos regulares y mobiliario por turnos en las
    aceras de cada tramo recto (fuera de la Plaza y de los puentes). Una
    farola que taparía la fachada de un edificio se salta."""
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
                        if bajo_fachada(casilla, edificios):
                            continue
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
            # Las farolas miden dos jugadores: arriba van en la esquina de la
            # acera (una columna más afuera y una fila más abajo), así no
            # tapan el cantero que queda detrás de ellas.
            casilla = (cx + (6 if dx > 0 else -6), cy + 3) if dy > 0 else (cx + (7 if dx > 0 else -7), cy - 2)
            poner(Prop(zonas_ciudad.farola_de(*casilla), casilla))
    for dx in (-7, 7):
        poner(Prop("arbol", (cx + dx, cy + 5), SUR, CAPA_ARBOL, True, ARBOLES_PLAZA[0 if dx < 0 else 1]))


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


def tapa_fachada(casilla, edificios):
    """True si un árbol en `casilla` taparía un edificio: a 2 casillas o
    menos de él (la copa de los grandes mide casi 3 de ancho) o debajo de su
    fachada a menos de ALTO_COPA_CASILLAS filas (la copa sube y cubriría la
    puerta y las ventanas)."""
    col, fila = casilla
    for huella in edificios:
        if distancia_a_rect(casilla, huella) <= 2:
            return True
        c0, f0, ancho, alto = huella
        debajo = fila - (f0 + alto - 1)
        if c0 - 1 <= col <= c0 + ancho and 0 < debajo <= ALTO_COPA_CASILLAS:
            return True
    return False


def _jardines(poner, mapa, rng, arbol_cerca, edificios):
    """Árboles en grupos naturales sobre los jardines y arbustos en sus bordes.

    1) Centros de grupo: casillas de jardín al azar (semilla fija) a
       SEPARACION_GRUPOS_ARBOLES o más de otro centro.
    2) Alrededor de cada centro, ARBOLES_POR_GRUPO árboles a lo sumo a
       RADIO_GRUPO_ARBOLES, a SEPARACION_ARBOLES_JARDIN o más de cualquier
       otro árbol; la especie, la de la zona.
    3) Arbustos en las casillas de jardín que dan a una banqueta, cada
       ESPACIADO_ARBUSTOS, lejos de los árboles."""
    jardin = [(c, f) for f, linea in enumerate(mapa) for c, letra in enumerate(linea)
              if letra == JARDIN and f > 0 and not tapa_fachada((c, f), edificios)]
    rng.shuffle(jardin)
    centros = []
    for casilla in jardin:
        if all(max(abs(casilla[0] - c[0]), abs(casilla[1] - c[1])) >= SEPARACION_GRUPOS_ARBOLES for c in centros):
            centros.append(casilla)
    disponibles = set(jardin)
    for cx, cy in centros:
        cuantos = rng.randint(*ARBOLES_POR_GRUPO)
        alrededor = [(cx + dx, cy + dy) for dy in range(-RADIO_GRUPO_ARBOLES, RADIO_GRUPO_ARBOLES + 1)
                     for dx in range(-RADIO_GRUPO_ARBOLES, RADIO_GRUPO_ARBOLES + 1)]
        rng.shuffle(alrededor)
        alrededor.sort(key=lambda c: c != (cx, cy))  # el centro primero
        puestos = 0
        for casilla in alrededor:
            if puestos >= cuantos:
                break
            if casilla not in disponibles or arbol_cerca(casilla, SEPARACION_ARBOLES_JARDIN):
                continue
            especie = rng.choice(zonas_ciudad.arboles_de(*casilla, ARBOLES_PARQUE_VARIANTES))
            if poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, especie)):
                puestos += 1
    vecinas = ((0, -1), (0, 1), (-1, 0), (1, 0))
    borde = sorted(c for c in disponibles if any(_letra(mapa, (c[0] + dc, c[1] + df)) == ACERA for dc, df in vecinas))
    for i, casilla in enumerate(borde):
        if i % ESPACIADO_ARBUSTOS == 0 and not arbol_cerca(casilla, SEPARACION_ARBOLES_JARDIN):
            poner(Prop("arbol", casilla, SUR, CAPA_ARBOL, True, rng.choice(ARBUSTOS)))


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
