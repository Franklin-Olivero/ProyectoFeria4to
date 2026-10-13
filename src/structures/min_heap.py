"""Montículo binario de mínimos implementado a mano (sin heapq).

Lo usa Dijkstra (src/structures/graph.py) como cola de prioridad: en
cada paso hay que sacar el nodo con la menor distancia tentativa, y un
montículo lo hace en O(log n) en vez de recorrer todos los nodos.

Representación: una lista donde el hijo izquierdo de la posición i está
en 2i + 1, el derecho en 2i + 2 y el padre en (i - 1) // 2. Invariante:
la prioridad de cada nodo es <= que la de sus hijos, así que el mínimo
siempre está en la posición 0.

Cada entrada guarda (prioridad, orden_de_llegada, valor). El orden de
llegada desempata prioridades repetidas (sale primero el que entró
primero) y evita comparar los valores, que pueden no ser comparables.

Este módulo no importa pygame.
"""


class MinHeap:
    """Cola de prioridad: siempre extrae la entrada de menor prioridad.

    Complejidad (n = entradas guardadas):
        insertar        O(log n)  (sube a lo sumo la altura del árbol)
        extraer_minimo  O(log n)  (baja a lo sumo la altura del árbol)
        esta_vacio      O(1)
    """

    def __init__(self):
        self._datos = []
        self._contador = 0  # orden de llegada, para desempatar

    def __len__(self):
        return len(self._datos)

    def esta_vacio(self):
        return not self._datos

    def insertar(self, prioridad, valor):
        """Agrega `valor` con `prioridad` y reacomoda hacia arriba. O(log n)."""
        self._datos.append((prioridad, self._contador, valor))
        self._contador += 1
        self._subir(len(self._datos) - 1)

    def extraer_minimo(self):
        """Quita y retorna (prioridad, valor) de la menor prioridad. O(log n).

        Lanza IndexError si el montículo está vacío.
        """
        if not self._datos:
            raise IndexError("extraer_minimo() sobre un MinHeap vacío.")
        minimo = self._datos[0]
        ultimo = self._datos.pop()
        if self._datos:
            # El último ocupa la raíz y se hunde hasta su lugar.
            self._datos[0] = ultimo
            self._bajar(0)
        prioridad, _, valor = minimo
        return prioridad, valor

    def _menor(self, i, j):
        """True si la entrada i va antes que la j (prioridad, luego llegada)."""
        return self._datos[i][:2] < self._datos[j][:2]

    def _intercambiar(self, i, j):
        self._datos[i], self._datos[j] = self._datos[j], self._datos[i]

    def _subir(self, i):
        while i > 0:
            padre = (i - 1) // 2
            if not self._menor(i, padre):
                break
            self._intercambiar(i, padre)
            i = padre

    def _bajar(self, i):
        n = len(self._datos)
        while True:
            menor = i
            for hijo in (2 * i + 1, 2 * i + 2):
                if hijo < n and self._menor(hijo, menor):
                    menor = hijo
            if menor == i:
                break
            self._intercambiar(i, menor)
            i = menor
