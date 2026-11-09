"""Red de calles de Ciudad Nova como grafo ponderado (lógica pura, sin Pygame).

Nodos: la Plaza (inicio, sin mazmorra), 4 cruces y la entrada de cada
edificio ("Colegio", "Hospital" y "Empresa de Medios" con mazmorra
normal; "Alcaldía" con la mazmorra final). Aristas: los tramos de
calle. Dónde queda cada nodo y cada tramo en el mapa de casillas lo dice
src/dungeon/ciudad_mapa.py.

Peso de una calle = peso base + saturación acumulada. El peso base sale
del largo real del tramo por el mapa (peso_base: casillas *
METROS_POR_CASILLA / METROS_POR_PUNTO_DE_PESO, redondeado): una calle
que se ve el doble de larga pesa el doble, y caminarla tarda el doble
(tiempo_recorrido).

Mecánicas que gobierna el grafo:
    - ruta_sugerida(): Dijkstra desde el nodo más cercano al jugador
      hasta un edificio, ignorando las calles bloqueadas. Es la línea
      punteada de la tecla G.
    - Pesos dinámicos: una Detonación satura las calles de la entrada
      de esa zona (+3) y una Purificación Exitosa las descongestiona
      (-2), siempre en [1, 10].
    - Barricadas: una calle se bloquea al llegar a BLOQUEO_PESO y se
      desbloquea al bajar de DESBLOQUEO_PESO, pero solo si al quitarla
      la ciudad sigue conexa (puede_bloquearse, con es_conexo/DFS). Su
      barricada es física: las casillas de su sección se vuelven sólidas.
Caminar es gratis: el costo de una calle saturada es que se bloquea y
hay que rodear.
"""

import math

from src.core.balance import (
    AJUSTE_DETONACION,
    AJUSTE_PURIFICACION,
    BLOQUEO_PESO,
    CRUCE_ESTE,
    CRUCE_NORTE,
    CRUCE_OESTE,
    CRUCE_SUR,
    DESBLOQUEO_PESO,
    PESO_MAXIMO_CIUDAD,
    METROS_POR_CASILLA,
    METROS_POR_PUNTO_DE_PESO,
    PESO_MINIMO_CIUDAD,
    REPORTES_POR_ZONA,
    VELOCIDAD_BASE,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
    ZONA_PLAZA,
)
from src.audio import eventos_sonido
from src.dungeon import ciudad_mapa
from src.structures.graph import INFINITO, Grafo

ZONA_INICIO = ZONA_PLAZA
ZONA_FINAL = ZONA_ALCALDIA
# Zonas con nombre (Plaza + edificios), en orden de presentación.
ZONAS = [ZONA_PLAZA, ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS, ZONA_ALCALDIA]
EDIFICIOS = [ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS, ZONA_ALCALDIA]
CRUCES = [CRUCE_NORTE, CRUCE_SUR, CRUCE_OESTE, CRUCE_ESTE]
NODOS = ZONAS + CRUCES


def metros_tramo(a, b):
    """Largo real de la calle a-b en metros (su recorrido por el mapa)."""
    return ciudad_mapa.largo_tramo(ciudad_mapa.tramo(a, b)) * METROS_POR_CASILLA


def peso_base(a, b):
    """Peso inicial de la calle a-b: sus metros en puntos de peso,
    redondeados al entero más cercano (x.5 sube) y nunca bajo el mínimo."""
    return max(PESO_MINIMO_CIUDAD, math.floor(metros_tramo(a, b) / METROS_POR_PUNTO_DE_PESO + 0.5))


def tiempo_recorrido(a, b, velocidad=VELOCIDAD_BASE):
    """Segundos que tarda en recorrer la calle a-b quien camina a
    `velocidad` px/s: proporcional a su largo."""
    largo_px = ciudad_mapa.largo_tramo(ciudad_mapa.tramo(a, b)) * ciudad_mapa.TAM_CASILLA
    return largo_px / velocidad


# (a, b, peso base) de cada calle, en el orden de ciudad_mapa.TRAMOS.
PESOS_INICIALES_CIUDAD = [(t.a, t.b, peso_base(t.a, t.b)) for t in ciudad_mapa.TRAMOS]


def _clave(a, b):
    """Identificador de una calle sin importar el sentido."""
    return frozenset((a, b))


class GrafoCiudad:
    def __init__(self):
        self.restablecer()

    def restablecer(self):
        """Vuelve a los pesos iniciales, sin barricadas (reinicio de partida)."""
        self.grafo = Grafo()
        for nodo in NODOS:
            self.grafo.agregar_nodo(nodo)
        for a, b, peso in PESOS_INICIALES_CIUDAD:
            self.grafo.agregar_arista(a, b, peso)
        self.bloqueadas = set()  # claves (frozenset) de las calles con barricada
        self._casillas_cache = None  # (bloqueadas, Grafo de casillas)
        self._nodo_cache = {}  # (bloqueadas, casilla) -> nodo más cercano a pie

    def zonas(self):
        return list(ZONAS)

    @staticmethod
    def tiene_mazmorra_normal(zona):
        return zona in REPORTES_POR_ZONA

    @staticmethod
    def reportes(zona):
        """Reportes de toxicidad de la zona (KeyError si no tiene mazmorra normal)."""
        return REPORTES_POR_ZONA[zona]

    # ------------------------------------------------------------------
    # Calles y barricadas
    # ------------------------------------------------------------------

    def calles(self):
        """Lista de (a, b, peso) sin repetir cada calle, en el orden de
        PESOS_INICIALES_CIUDAD."""
        return [(a, b, self.grafo.peso(a, b)) for a, b, _ in PESOS_INICIALES_CIUDAD]

    def esta_bloqueada(self, a, b):
        return _clave(a, b) in self.bloqueadas

    def calles_bloqueadas(self):
        """[(a, b)] de las calles con barricada, en orden fijo."""
        return [(a, b) for a, b, _ in self.calles() if self.esta_bloqueada(a, b)]

    def grafo_abierto(self):
        """Copia del grafo sin las calles bloqueadas. O(V + E)."""
        abierto = self.grafo.copia()
        for clave in self.bloqueadas:
            a, b = tuple(clave)
            abierto.eliminar_arista(a, b)
        return abierto

    def puede_bloquearse(self, arista):
        """True si al quitar `arista` = (a, b), además de las ya
        bloqueadas, la ciudad sigue conexa (un solo DFS: es_conexo).
        Así una barricada nunca deja un edificio inalcanzable.
        O(V + E)."""
        a, b = tuple(arista)
        abierto = self.grafo_abierto()
        if abierto.existe_arista(a, b):
            abierto.eliminar_arista(a, b)
        return abierto.es_conexo()

    def bloquear(self, arista):
        """Pone la barricada de `arista` si puede_bloquearse; True si quedó bloqueada."""
        if not self.puede_bloquearse(arista):
            return False
        self.bloqueadas.add(_clave(*arista))
        eventos_sonido.emitir("barricada")
        return True

    def desbloquear(self, arista):
        self.bloqueadas.discard(_clave(*arista))

    def barricadas_activas(self):
        """Casillas sólidas por barricadas de calle: la sección de cada
        calle bloqueada."""
        casillas = set()
        for a, b in self.calles_bloqueadas():
            casillas.update(ciudad_mapa.tramo(a, b).seccion)
        return frozenset(casillas)

    def es_solida(self, col, fila):
        """Mapa base + barricadas de calle (sin las de la Alcaldía, que
        dependen del colapso y el progreso: ver Partida.es_solida)."""
        return ciudad_mapa.es_solida(col, fila, self.barricadas_activas())

    # ------------------------------------------------------------------
    # Pesos dinámicos
    # ------------------------------------------------------------------

    def actualizar_tras_mazmorra(self, zona, exito):
        """Purificación Exitosa (`exito`) baja AJUSTE_PURIFICACION las
        calles del nodo de entrada de `zona`; una Detonación las sube
        AJUSTE_DETONACION. Siempre en [PESO_MINIMO_CIUDAD,
        PESO_MAXIMO_CIUDAD]. Después se revisan las barricadas."""
        ajuste = -AJUSTE_PURIFICACION if exito else AJUSTE_DETONACION
        for vecino in self.grafo.vecinos(zona):
            nuevo = self.grafo.peso(zona, vecino) + ajuste
            nuevo = max(PESO_MINIMO_CIUDAD, min(PESO_MAXIMO_CIUDAD, nuevo))
            self.grafo.cambiar_peso(zona, vecino, nuevo)
        self.revisar_barricadas()

    def revisar_barricadas(self):
        """Aplica la histéresis 8/6 a todas las calles, en orden fijo:
        primero quita las barricadas cuyo peso bajó de DESBLOQUEO_PESO y
        luego pone las de peso >= BLOQUEO_PESO. Una calle que no puede
        bloquearse (desconectaría la ciudad) queda abierta pero al máximo."""
        for a, b, peso in self.calles():
            if self.esta_bloqueada(a, b) and peso < DESBLOQUEO_PESO:
                self.desbloquear((a, b))
        for a, b, peso in self.calles():
            if not self.esta_bloqueada(a, b) and peso >= BLOQUEO_PESO:
                if not self.bloquear((a, b)):
                    self.grafo.cambiar_peso(a, b, PESO_MAXIMO_CIUDAD)

    # ------------------------------------------------------------------
    # Rutas
    # ------------------------------------------------------------------

    def ruta_mas_segura(self, origen, destino):
        """(camino, costo) de menor saturación total entre dos nodos, con
        Dijkstra sobre las calles abiertas. (None, INFINITO) si no hay.
        O((V + E) log V); con 9 nodos y 12 calles es instantáneo."""
        distancias, predecesores = self.grafo_abierto().dijkstra(origen)
        return Grafo.camino(predecesores, origen, destino), distancias[destino]

    def _grafo_casillas(self):
        """Grafo de casillas transitables con las barricadas actuales
        (se reconstruye solo cuando cambian las barricadas)."""
        clave = frozenset(self.bloqueadas)
        if self._casillas_cache is None or self._casillas_cache[0] != clave:
            self._casillas_cache = (clave, ciudad_mapa.grafo_casillas(self.es_solida))
        return self._casillas_cache[1]

    def nodo_mas_cercano(self, posicion):
        """Nodo de calle más cercano a `posicion` (px del mundo) caminando.

        BFS sobre el grafo de casillas desde la casilla del jugador: el
        primer nodo que aparece es el de menos pasos, y nunca uno que
        quede al otro lado de una barricada (la distancia en línea recta
        sí podría elegirlo). Si la casilla no es transitable, cae a la
        distancia en línea recta. O(V + E) sobre las casillas.
        """
        inicio = ciudad_mapa.casilla_de(*posicion)
        clave = (frozenset(self.bloqueadas), inicio)
        if clave in self._nodo_cache:
            return self._nodo_cache[clave]
        casillas = self._grafo_casillas()
        if inicio in casillas:
            por_casilla = {casilla: nodo for nodo, casilla in ciudad_mapa.NODOS_CALLE.items()}
            orden, _, _ = casillas.bfs(inicio)
            for casilla in orden:
                if casilla in por_casilla:
                    self._nodo_cache[clave] = por_casilla[casilla]
                    return por_casilla[casilla]

        def distancia(nodo):
            cx, cy = ciudad_mapa.centro_casilla(*ciudad_mapa.NODOS_CALLE[nodo])
            return (cx - posicion[0]) ** 2 + (cy - posicion[1]) ** 2

        return min(NODOS, key=distancia)

    def ruta_sugerida(self, posicion_jugador, destino):
        """(nodos, costo) de la ruta más segura desde el nodo más cercano
        al jugador hasta `destino`, o None si no hay ruta."""
        origen = self.nodo_mas_cercano(posicion_jugador)
        camino, costo = self.ruta_mas_segura(origen, destino)
        if camino is None or costo == INFINITO:
            return None
        return camino, costo
