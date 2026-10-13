"""Mapa de la ciudad como grafo ponderado (lógica pura, sin Pygame).

Nodos: las zonas de la ciudad. "Plaza" es el inicio (sin mazmorra),
"Colegio", "Hospital" y "Empresa de Medios" tienen una mazmorra normal
cada una y "Alcaldía" es la mazmorra final. El peso de cada arista es
la saturación de esa calle (PESOS_INICIALES_CIUDAD en balance.py).

Mecánicas que gobierna el grafo:
    - ruta_mas_segura(): Dijkstra elige la ruta de menor saturación
      total, que no siempre es la de menos calles. Su costo se cobra en
      Colapso Electoral al viajar (ver src/dungeon/partida.py).
    - Pesos dinámicos: limpiar bien una zona (Purificación Exitosa)
      descongestiona sus calles (-1, mínimo 1); una Detonación las
      satura más (+1, máximo 10). Así las decisiones del jugador
      cambian las rutas que conviene tomar después.
"""

from src.core.balance import (
    AJUSTE_PESO_CIUDAD,
    PESO_MAXIMO_CIUDAD,
    PESO_MINIMO_CIUDAD,
    PESOS_INICIALES_CIUDAD,
    REPORTES_POR_ZONA,
    ZONA_ALCALDIA,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
    ZONA_PLAZA,
)
from src.structures.graph import Grafo

ZONA_INICIO = ZONA_PLAZA
ZONA_FINAL = ZONA_ALCALDIA
# Orden de las zonas en el mapa (las flechas recorren esta lista).
ZONAS = [ZONA_PLAZA, ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS, ZONA_ALCALDIA]


class GrafoCiudad:
    def __init__(self):
        self.restablecer()

    def restablecer(self):
        """Vuelve a los pesos iniciales (reinicio de partida)."""
        self.grafo = Grafo()
        for zona in ZONAS:
            self.grafo.agregar_nodo(zona)
        for a, b, peso in PESOS_INICIALES_CIUDAD:
            self.grafo.agregar_arista(a, b, peso)

    def zonas(self):
        return list(ZONAS)

    @staticmethod
    def tiene_mazmorra_normal(zona):
        return zona in REPORTES_POR_ZONA

    @staticmethod
    def reportes(zona):
        """Reportes de toxicidad de la zona (KeyError si no tiene mazmorra normal)."""
        return REPORTES_POR_ZONA[zona]

    def ruta_mas_segura(self, origen, destino):
        """(camino, costo) de menor saturación total, con Dijkstra.

        Retorna (None, INFINITO) si no hay ruta. Complejidad:
        O((V + E) log V); con 5 zonas y 7 calles es instantáneo.
        """
        distancias, predecesores = self.grafo.dijkstra(origen)
        return Grafo.camino(predecesores, origen, destino), distancias[destino]

    def actualizar_tras_mazmorra(self, zona, exito):
        """Ajusta en AJUSTE_PESO_CIUDAD todas las calles de `zona`:
        baja si `exito` (Purificación Exitosa), sube si no (Detonación),
        siempre dentro de [PESO_MINIMO_CIUDAD, PESO_MAXIMO_CIUDAD]."""
        ajuste = -AJUSTE_PESO_CIUDAD if exito else AJUSTE_PESO_CIUDAD
        for vecino in self.grafo.vecinos(zona):
            nuevo = self.grafo.peso(zona, vecino) + ajuste
            nuevo = max(PESO_MINIMO_CIUDAD, min(PESO_MAXIMO_CIUDAD, nuevo))
            self.grafo.cambiar_peso(zona, vecino, nuevo)

    def calles(self):
        """Lista de (a, b, peso) sin repetir cada calle (para dibujarlas)."""
        vistas = []
        for a in self.grafo.nodos():
            for b in self.grafo.vecinos(a):
                if ZONAS.index(a) < ZONAS.index(b):
                    vistas.append((a, b, self.grafo.peso(a, b)))
        return vistas
