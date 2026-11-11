"""Cómo rodean los enemigos las coberturas de un cuarto (puro, sin Pygame).

El piso del cuarto se cuadricula en celdas de NAV_CELDA px. Cada celda
libre (su centro queda a más de NAV_HOLGURA px de toda cobertura) es un
NODO de un Grafo (src/structures/graph.py, hecho a mano) y hay ARISTA
entre dos celdas vecinas libres (en diagonal solo si no se corta una
esquina). Es el grafo que gobierna la persecución:

    direccion(desde, hacia)  hacia dónde caminar para llegar a `hacia`:
        en línea recta si nada estorba; si hay un mueble en medio, por el
        camino más corto que da un BFS desde la celda del objetivo.
    alcanzable(punto, desde) ¿se puede llegar caminando de `desde` a `punto`?
        (los enemigos nunca aparecen encerrados entre muebles)
    reconstruir(obstaculos)  rehace el grafo cuando se rompe una cobertura:
        el hueco que deja se vuelve camino.

Complejidad: reconstruir es O(celdas * obstáculos); un BFS, O(V + E) con
V <= celdas y E <= 8V; se guarda un BFS por celda de objetivo (hasta
NAV_MAX_RUTAS) y `direccion` consulta el predecesor en O(1), así que
muchos enemigos persiguiendo al mismo jugador comparten un solo BFS.
Por qué BFS y no Dijkstra: todas las celdas cuestan lo mismo.
"""

import math

from src.core.balance import NAV_CELDA, NAV_HOLGURA, NAV_MAX_RUTAS, NAV_PASOS_VISTA
from src.structures.graph import Grafo

VECINAS_RECTAS = ((1, 0), (-1, 0), (0, 1), (0, -1))
VECINAS_DIAGONALES = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _inflar(rect, holgura):
    x, y, ancho, alto = rect
    return (x - holgura, y - holgura, ancho + 2 * holgura, alto + 2 * holgura)


def _contiene(rect, punto):
    x, y, ancho, alto = rect
    return x < punto[0] < x + ancho and y < punto[1] < y + alto


def segmento_corta(a, b, rect):
    """¿El segmento a-b pasa por dentro de `rect`? Recorte de Liang-Barsky:
    se acota el tramo del segmento que cae dentro de las 4 caras. O(1)."""
    x, y, ancho, alto = rect
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x), (dx, x + ancho - a[0]), (-dy, a[1] - y), (dy, y + alto - a[1])):
        if p == 0:
            if q <= 0:
                return False  # paralelo y por fuera (o sobre el borde)
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


class NavegacionCuarto:
    def __init__(self, limites, obstaculos=(), celda=NAV_CELDA, holgura=NAV_HOLGURA):
        """`limites` = (izquierda, arriba, derecha, abajo) del cuarto."""
        self.limites = limites
        self.celda = celda
        self.holgura = holgura
        izquierda, arriba, derecha, abajo = limites
        self.columnas = max(1, int((derecha - izquierda) // celda))
        self.filas = max(1, int((abajo - arriba) // celda))
        self.grafo = Grafo()
        self.obstaculos = []
        self._inflados = []
        self._rutas = {}  # celda del objetivo -> predecesores del BFS desde ella
        self.reconstruir(obstaculos)

    # ------------------------------------------------------------------
    # El grafo de celdas
    # ------------------------------------------------------------------

    def celda_de(self, punto):
        """(columna, fila) de la celda que contiene `punto`, acotada al cuarto."""
        izquierda, arriba = self.limites[0], self.limites[1]
        columna = int((punto[0] - izquierda) // self.celda)
        fila = int((punto[1] - arriba) // self.celda)
        return (min(max(columna, 0), self.columnas - 1), min(max(fila, 0), self.filas - 1))

    def centro(self, celda):
        return (self.limites[0] + (celda[0] + 0.5) * self.celda,
                self.limites[1] + (celda[1] + 0.5) * self.celda)

    def reconstruir(self, obstaculos):
        """Rehace el grafo con los `obstaculos` (hitboxes) que quedan en pie."""
        self.obstaculos = [tuple(o) for o in obstaculos]
        self._inflados = [_inflar(o, self.holgura) for o in self.obstaculos]
        self._rutas = {}
        grafo = Grafo()
        libres = set()
        for fila in range(self.filas):
            for columna in range(self.columnas):
                centro = self.centro((columna, fila))
                if not any(_contiene(inflado, centro) for inflado in self._inflados):
                    libres.add((columna, fila))
                    grafo.agregar_nodo((columna, fila))
        for columna, fila in libres:
            # Cada arista se agrega una vez: solo hacia la derecha y hacia abajo.
            for dc, df in ((1, 0), (0, 1)):
                if (columna + dc, fila + df) in libres:
                    grafo.agregar_arista((columna, fila), (columna + dc, fila + df))
            for dc, df in ((1, 1), (-1, 1)):
                vecina = (columna + dc, fila + df)
                # En diagonal solo si las dos celdas del cruce están libres
                # (si no, se cortaría la esquina de un mueble).
                if vecina in libres and (columna + dc, fila) in libres and (columna, fila + df) in libres:
                    grafo.agregar_arista((columna, fila), vecina)
        self.grafo = grafo

    def libre(self, celda):
        return celda in self.grafo

    def celda_libre_cercana(self, punto):
        """La celda libre más cercana a `punto` (por anillos alrededor de
        la suya), o None si el cuarto no tiene ninguna."""
        origen = self.celda_de(punto)
        if self.libre(origen):
            return origen
        for radio in range(1, max(self.columnas, self.filas)):
            anillo = [(origen[0] + dc, origen[1] + df)
                      for dc in range(-radio, radio + 1) for df in range(-radio, radio + 1)
                      if max(abs(dc), abs(df)) == radio]
            candidatas = [c for c in anillo if self.libre(c)]
            if candidatas:
                return min(candidatas, key=lambda c: math.dist(self.centro(c), punto))
        return None

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def linea_libre(self, a, b, radio=None):
        """¿Se puede caminar de a hasta b en línea recta sin rozar un mueble?
        `radio`: medio ancho de quien camina (por defecto, la holgura del grafo)."""
        if radio is None or radio <= self.holgura:
            inflados = self._inflados
        else:
            inflados = [_inflar(o, radio) for o in self.obstaculos]
        return not any(segmento_corta(a, b, inflado) for inflado in inflados)

    def _ruta_hacia(self, celda_objetivo):
        """Predecesores del BFS desde `celda_objetivo` (guardado): para
        cualquier celda, su predecesor es el siguiente paso hacia el objetivo."""
        if celda_objetivo not in self._rutas:
            if len(self._rutas) >= NAV_MAX_RUTAS:
                self._rutas.pop(next(iter(self._rutas)))  # la más antigua
            self._rutas[celda_objetivo] = self.grafo.bfs(celda_objetivo)[2]
        return self._rutas[celda_objetivo]

    def direccion(self, desde, hacia, radio=None):
        """Vector unitario (dx, dy) para ir de `desde` a `hacia`. `radio`:
        medio ancho de quien camina (un enemigo grande necesita más margen
        para ir derecho).

        Sin muebles, o con la línea despejada: derecho al objetivo. Si
        no, se sigue el camino del BFS: desde la celda propia se avanza
        por los predecesores y se apunta a la celda más lejana del
        camino que se ve en línea recta (así no camina en escalera)."""
        if not self._inflados or self.linea_libre(desde, hacia, radio):
            return _unitario(desde, hacia)
        objetivo = self.celda_libre_cercana(hacia)
        actual = self.celda_libre_cercana(desde)
        if objetivo is None or actual is None:
            return _unitario(desde, hacia)
        # Si va rozando un mueble (su celda no es libre) el camino arranca en
        # la celda libre más cercana: sigue avanzando en vez de retroceder a ella.
        predecesores = self._ruta_hacia(objetivo)
        if actual not in predecesores:
            return _unitario(desde, hacia)  # no hay camino (encerrado): empuja derecho
        meta = None
        celda = actual
        for _ in range(NAV_PASOS_VISTA):
            celda = predecesores[celda]
            if celda is None:
                break
            centro = self.centro(celda)
            if meta is not None and not self.linea_libre(desde, centro, radio):
                break
            meta = centro
        if meta is None:
            return _unitario(desde, hacia)  # ya está en la celda del objetivo
        return _unitario(desde, meta)

    def alcanzable(self, punto, desde):
        """¿Hay camino caminando de `desde` a `punto`? Un BFS (guardado). O(V + E)."""
        origen = self.celda_libre_cercana(desde)
        celda = self.celda_de(punto)
        if origen is None or not self.libre(celda):
            return False
        return celda in self._ruta_hacia(origen)


def _unitario(desde, hacia):
    dx, dy = hacia[0] - desde[0], hacia[1] - desde[1]
    largo = math.hypot(dx, dy)
    if largo == 0:
        return (0.0, 0.0)
    return (dx / largo, dy / largo)
