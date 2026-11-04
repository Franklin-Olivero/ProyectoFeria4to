"""Grafo social de Ciudad Nova: propagación por BFS y rastreo por DFS (sin Pygame).

Es un grafo DISTINTO del de calles (src/dungeon/grafo_ciudad.py): aquí
cada nodo es un ciudadano ficticio (content/campaign.json, "red_social")
y cada arista no dirigida (peso 1) dice que se siguen en Civitas. Usa el
mismo Grafo manual de src/structures/graph.py.

Mecánicas:
    - propagar(origen): BFS desde quien publica, capa por capa, hasta
      SALTOS_MAXIMOS_PROPAGACION saltos. Cada contacto recibe la
      publicación con una probabilidad (rng inyectable, reproducible);
      un ciudadano se cuenta UNA sola vez aunque le llegue por varios
      lados (conjunto de visitados del BFS). Devuelve las capas, el orden
      de llegada, los predecesores y las aristas usadas: con eso la
      pantalla dibuja la onda y "La publicación llegó a X ciudadanos".
    - corregir(origen): una corrección publicada desde `origen` llega
      (BFS sin azar) a sus contactos cercanos y los marca como
      corregidos: en adelante reenvían con PROBABILIDAD_REBOTE_CORREGIDA
      en vez de la base. La corrección NO borra la memoria: quien ya
      vio el rumor sigue en `expuestos`.
    - rastrear(nodo): DFS iterativo desde `nodo` sobre las conexiones,
      en orden de visita: a quién pudo haber llegado una publicación
      suya. cadena_hasta(id) reconstruye la ruta real de contagio de la
      última propagación (origen -> ... -> id) con los predecesores.
"""

import random
from dataclasses import dataclass, field

from src.core.balance import (
    PROBABILIDAD_REBOTE_BASE,
    PROBABILIDAD_REBOTE_CORREGIDA,
    SALTOS_MAXIMOS_PROPAGACION,
)
from src.structures.graph import Grafo

RUMOR = "rumor"
CORRECCION = "correccion"


@dataclass
class Propagacion:
    tipo: str  # RUMOR o CORRECCION
    origen: str
    capas: list = field(default_factory=list)  # [[ids a 0 saltos], [a 1 salto], ...]
    predecesores: dict = field(default_factory=dict)  # id -> de quién lo recibió (origen: None)
    aristas: list = field(default_factory=list)  # (de, a) por las que viajó
    probabilidad_extra: float = 0.0

    @property
    def alcanzados(self):
        """Ids en orden de llegada (el origen primero), sin repetir."""
        return [nodo for capa in self.capas for nodo in capa]

    @property
    def total(self):
        return len(self.alcanzados)

    @property
    def saltos(self):
        return max(0, len(self.capas) - 1)

    def cadena_hasta(self, nodo):
        """Ruta de contagio origen -> ... -> nodo, o [] si no le llegó. O(L)."""
        if nodo not in self.predecesores:
            return []
        ruta = []
        actual = nodo
        while actual is not None:
            ruta.append(actual)
            actual = self.predecesores[actual]
        ruta.reverse()
        return ruta


class RedSocial:
    def __init__(self, datos, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.grafo = Grafo()
        self.nombres = {}
        self.roles = {}
        for ciudadano in datos["ciudadanos"]:
            self.grafo.agregar_nodo(ciudadano["id"])
            self.nombres[ciudadano["id"]] = ciudadano["nombre"]
            self.roles[ciudadano["id"]] = ciudadano.get("rol", "")
        for a, b in datos["conexiones"]:
            self.grafo.agregar_arista(a, b, 1)
        self.expuestos = set()  # ya vieron algún rumor (memoria: no se borra)
        self.corregidos = set()  # recibieron una corrección (rebotan menos)
        self.historial = []  # Propagacion en orden

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def ciudadanos(self):
        return self.grafo.nodos()

    def nombre(self, nodo):
        return self.nombres.get(nodo, nodo)

    def probabilidad_de(self, nodo, extra=0.0):
        """Con qué probabilidad `nodo` reenvía lo que recibe."""
        base = PROBABILIDAD_REBOTE_CORREGIDA if nodo in self.corregidos else PROBABILIDAD_REBOTE_BASE
        return min(1.0, base + extra)

    def ciudadano_al_azar(self):
        return self.rng.choice(self.ciudadanos())

    # ------------------------------------------------------------------
    # BFS: propagación
    # ------------------------------------------------------------------

    def propagar(self, origen, saltos_max=SALTOS_MAXIMOS_PROPAGACION, probabilidad_extra=0.0, tipo=RUMOR):
        """BFS con azar desde `origen`. El origen siempre cuenta. Cada
        vecino no visitado de un nodo de la capa d recibe la publicación
        con probabilidad_de(emisor) y pasa a la capa d+1 (si d+1 <=
        saltos_max). Visitados = conjunto: nadie se cuenta dos veces.
        Complejidad: O(V + E), como el BFS normal."""
        if origen not in self.grafo:
            raise KeyError(f"El ciudadano {origen!r} no existe en la red.")
        resultado = Propagacion(tipo, origen, probabilidad_extra=probabilidad_extra)
        visitados = {origen}
        resultado.predecesores[origen] = None
        capa = [origen]
        resultado.capas.append(capa)
        distancia = 0
        while capa and distancia < saltos_max:
            siguiente = []
            for emisor in capa:
                for vecino in self.grafo.vecinos(emisor):
                    if vecino in visitados:
                        continue
                    if self.rng.random() < self.probabilidad_de(emisor, probabilidad_extra):
                        visitados.add(vecino)
                        resultado.predecesores[vecino] = emisor
                        resultado.aristas.append((emisor, vecino))
                        siguiente.append(vecino)
            if not siguiente:
                break
            resultado.capas.append(siguiente)
            capa = siguiente
            distancia += 1
        if tipo == RUMOR:
            self.expuestos.update(resultado.alcanzados)
        else:
            self.corregidos.update(resultado.alcanzados)
        self.historial.append(resultado)
        return resultado

    def corregir(self, origen, saltos_max=SALTOS_MAXIMOS_PROPAGACION):
        """Corrección publicada desde `origen`: llega sin azar a todo lo
        que esté a <= saltos_max (BFS exacto, Grafo.bfs) y marca a esos
        ciudadanos como corregidos. Devuelve la Propagacion de la
        corrección. No quita a nadie de `expuestos`."""
        _, distancias, predecesores = self.grafo.bfs(origen)
        resultado = Propagacion(CORRECCION, origen)
        capas = {}
        for nodo, d in distancias.items():
            if d <= saltos_max:
                capas.setdefault(d, []).append(nodo)
                resultado.predecesores[nodo] = predecesores[nodo]
                if predecesores[nodo] is not None:
                    resultado.aristas.append((predecesores[nodo], nodo))
        resultado.capas = [capas[d] for d in sorted(capas)]
        self.corregidos.update(resultado.alcanzados)
        self.historial.append(resultado)
        return resultado

    # ------------------------------------------------------------------
    # DFS: rastreo
    # ------------------------------------------------------------------

    def rastrear(self, nodo):
        """Orden DFS desde `nodo` (pila explícita, Grafo.dfs): todos los
        ciudadanos a los que una publicación suya puede llegar por la red
        de contactos, en el orden en que un investigador los recorrería
        siguiendo cada hilo hasta el final antes de volver."""
        return self.grafo.dfs(nodo)

    def ultima(self, tipo=None):
        for propagacion in reversed(self.historial):
            if tipo is None or propagacion.tipo == tipo:
                return propagacion
        return None
