"""Selección de zona en el mapa de la ciudad (lógica pura, sin Pygame).

Las flechas izquierda/derecha recorren la lista de zonas dando la
vuelta en los extremos; ENTER (en Main.py) viaja a la seleccionada.
"""

from src.ui.terminal_decision import DERECHA, IZQUIERDA


class SelectorZona:
    def __init__(self, zonas, inicial):
        self.zonas = list(zonas)
        self.indice = self.zonas.index(inicial)

    @property
    def seleccionada(self):
        return self.zonas[self.indice]

    def mover(self, direccion):
        if direccion == IZQUIERDA:
            self.indice = (self.indice - 1) % len(self.zonas)
        elif direccion == DERECHA:
            self.indice = (self.indice + 1) % len(self.zonas)
