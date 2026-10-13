"""Grafo ponderado implementado a mano (sin librerías de terceros).

Gobierna dos mecánicas del juego:

1. Mazmorra multi-cuarto (src/dungeon/mazmorra.py): cada nodo es un
cuarto y cada arista un pasillo (peso 1). Con él se genera el layout,
se ubican las puertas, se elige el cuarto final, se propaga la
toxicidad a los cuartos cercanos y se dibuja la ruta del minimapa.

2. Mapa de la ciudad (src/dungeon/grafo_ciudad.py): cada nodo es una
zona y el peso de cada arista es la saturación de esa calle. Con él se
calcula la ruta más segura y su costo en Colapso Electoral.

Representación: lista de adyacencia como diccionario
    nodo -> {vecino: peso}
Así `vecinos(nodo)` es O(grado) y `existe_arista`/`peso` son O(1)
promedio. Con V nodos y E aristas ocupa O(V + E) de memoria (una
matriz de adyacencia ocuparía O(V^2), un desperdicio para grafos
dispersos como un mapa de cuartos o de calles).

Este módulo no importa pygame.
"""

from collections import deque

from src.structures.min_heap import MinHeap

INFINITO = float("inf")


class Grafo:
    """Grafo con aristas ponderadas; cada arista puede ser dirigida o no.

    Una arista no dirigida se guarda como dos entradas (a -> b y b -> a)
    con el mismo peso. Los pesos deben ser >= 0 (Dijkstra lo exige).
    En las complejidades, V = número de nodos y E = número de aristas.
    """

    def __init__(self):
        self._adyacencia = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def agregar_nodo(self, nodo):
        """Agrega un nodo aislado (si ya existe no hace nada). O(1)."""
        if nodo not in self._adyacencia:
            self._adyacencia[nodo] = {}

    def eliminar_nodo(self, nodo):
        """Quita el nodo y todas las aristas que llegan o salen de él. O(V).

        Hay que revisar a todos los demás nodos porque, con aristas
        dirigidas, cualquiera puede apuntar a `nodo`.
        Lanza KeyError si el nodo no existe.
        """
        self._exigir_nodo(nodo)
        del self._adyacencia[nodo]
        for vecinos in self._adyacencia.values():
            vecinos.pop(nodo, None)

    def agregar_arista(self, a, b, peso=1, dirigida=False):
        """Une a con b (y b con a si no es dirigida). Crea los nodos que
        falten. Si la arista ya existía, reemplaza su peso. O(1)."""
        self._validar_peso(peso)
        self.agregar_nodo(a)
        self.agregar_nodo(b)
        self._adyacencia[a][b] = peso
        if not dirigida:
            self._adyacencia[b][a] = peso

    def eliminar_arista(self, a, b, dirigida=False):
        """Quita a -> b (y b -> a si no es dirigida). O(1).
        Lanza KeyError si la arista no existe."""
        self._exigir_arista(a, b)
        del self._adyacencia[a][b]
        if not dirigida:
            self._adyacencia[b].pop(a, None)

    def existe_arista(self, a, b):
        """True si hay arista a -> b. O(1)."""
        return a in self._adyacencia and b in self._adyacencia[a]

    def peso(self, a, b):
        """Peso de la arista a -> b. O(1). KeyError si no existe."""
        self._exigir_arista(a, b)
        return self._adyacencia[a][b]

    def cambiar_peso(self, a, b, nuevo_peso):
        """Cambia el peso de a -> b, y también el de b -> a si esa
        arista de vuelta existe (arista no dirigida). O(1)."""
        self._exigir_arista(a, b)
        self._validar_peso(nuevo_peso)
        self._adyacencia[a][b] = nuevo_peso
        if self.existe_arista(b, a):
            self._adyacencia[b][a] = nuevo_peso

    def vecinos(self, nodo):
        """Lista de vecinos de `nodo` en orden de inserción. O(grado)."""
        self._exigir_nodo(nodo)
        return list(self._adyacencia[nodo])

    def nodos(self):
        """Lista de nodos en orden de inserción. O(V)."""
        return list(self._adyacencia)

    def copia(self):
        """Grafo nuevo con los mismos nodos y aristas (los diccionarios
        se copian; los nodos se comparten). O(V + E)."""
        nuevo = Grafo()
        nuevo._adyacencia = {nodo: dict(vecinos) for nodo, vecinos in self._adyacencia.items()}
        return nuevo

    def __contains__(self, nodo):
        return nodo in self._adyacencia

    def __len__(self):
        return len(self._adyacencia)

    # ------------------------------------------------------------------
    # Recorridos
    # ------------------------------------------------------------------

    def bfs(self, origen):
        """Búsqueda en anchura desde `origen`.

        Retorna (orden_de_visita, distancias_en_saltos, predecesores):
            orden_de_visita: lista de nodos en el orden en que salen de la cola.
            distancias_en_saltos: {nodo alcanzado: cantidad de aristas desde origen}.
            predecesores: {nodo alcanzado: nodo anterior en el camino}; el
                origen tiene predecesor None.

        Complejidad: O(V + E). Cada nodo entra a la cola una sola vez y
        cada lista de vecinos se recorre una sola vez.

        Por qué BFS en el juego: los pasillos de la mazmorra no tienen
        peso (todos cuestan "un cuarto"), y BFS visita por capas de
        distancia, así que da la distancia en saltos exacta. Con eso se
        elige el cuarto final (el más lejano), se reparte la propagación
        de toxicidad (incremento / distancia) y se marca en el minimapa
        el camino más corto hasta el cuarto final.
        """
        self._exigir_nodo(origen)
        distancias = {origen: 0}
        predecesores = {origen: None}
        orden = []
        cola = deque([origen])
        while cola:
            actual = cola.popleft()
            orden.append(actual)
            for vecino in self._adyacencia[actual]:
                if vecino not in distancias:
                    distancias[vecino] = distancias[actual] + 1
                    predecesores[vecino] = actual
                    cola.append(vecino)
        return orden, distancias, predecesores

    def dfs(self, origen):
        """Búsqueda en profundidad iterativa (pila explícita) desde `origen`.

        Retorna la lista de nodos en orden de visita. Los vecinos se
        apilan al revés para visitarlos en su orden de inserción, igual
        que la versión recursiva.

        Complejidad: O(V + E). Cada nodo se procesa una sola vez; la pila
        puede recibir hasta una entrada por arista.

        Por qué DFS en el juego: solo hay que saber "a qué se puede
        llegar", no a qué distancia; DFS lo responde con una pila simple
        y sin recursión (no hay riesgo de pasar el límite de recursión
        de Python). Lo usa es_conexo() para garantizar que toda mazmorra
        generada se pueda recorrer completa.
        """
        self._exigir_nodo(origen)
        visitados = set()
        orden = []
        pila = [origen]
        while pila:
            actual = pila.pop()
            if actual in visitados:
                continue
            visitados.add(actual)
            orden.append(actual)
            for vecino in reversed(list(self._adyacencia[actual])):
                if vecino not in visitados:
                    pila.append(vecino)
        return orden

    def es_conexo(self):
        """True si desde un nodo se alcanzan todos los demás (pensado
        para grafos no dirigidos). Un grafo vacío se considera conexo.

        Complejidad: O(V + E), un solo DFS.
        """
        if not self._adyacencia:
            return True
        primero = next(iter(self._adyacencia))
        return len(self.dfs(primero)) == len(self._adyacencia)

    @staticmethod
    def camino(predecesores, origen, destino):
        """Reconstruye origen -> destino siguiendo `predecesores` (el
        diccionario que devuelven bfs o dijkstra). Retorna la lista de
        nodos, o None si `destino` no fue alcanzado.

        Complejidad: O(L), con L la longitud del camino.
        """
        if destino not in predecesores:
            return None
        recorrido = []
        actual = destino
        while actual is not None:
            recorrido.append(actual)
            if actual == origen:
                break
            actual = predecesores[actual]
        if recorrido[-1] != origen:
            return None
        recorrido.reverse()
        return recorrido

    def dijkstra(self, origen):
        """Caminos de menor peso desde `origen` (pesos >= 0).

        Retorna (distancias, predecesores):
            distancias: {nodo: peso total mínimo desde origen}; INFINITO
                para los nodos que no se alcanzan.
            predecesores: {nodo alcanzado: nodo anterior}; el origen
                tiene predecesor None.

        Usa un MinHeap como cola de prioridad con "borrado perezoso":
        si un nodo mejora, se vuelve a insertar, y las entradas viejas se
        descartan al salir (su distancia ya no coincide).

        Complejidad: O((V + E) log V). Cada arista puede insertar una
        entrada en el montículo (O(log V) cada una) y cada nodo se
        extrae y se procesa una vez.

        Por qué Dijkstra en el juego: en la ciudad cada calle tiene una
        saturación distinta y la ruta con menos saltos puede ser la más
        peligrosa. BFS contaría saltos; Dijkstra suma pesos y encuentra
        la ruta realmente más segura (la de menor saturación total).
        """
        self._exigir_nodo(origen)
        distancias = {nodo: INFINITO for nodo in self._adyacencia}
        distancias[origen] = 0
        predecesores = {origen: None}
        pendientes = MinHeap()
        pendientes.insertar(0, origen)
        while not pendientes.esta_vacio():
            distancia, actual = pendientes.extraer_minimo()
            if distancia > distancias[actual]:
                continue  # entrada vieja: ya se encontró algo mejor
            for vecino, peso in self._adyacencia[actual].items():
                candidata = distancia + peso
                if candidata < distancias[vecino]:
                    distancias[vecino] = candidata
                    predecesores[vecino] = actual
                    pendientes.insertar(candidata, vecino)
        return distancias, predecesores

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------

    def _exigir_nodo(self, nodo):
        if nodo not in self._adyacencia:
            raise KeyError(f"El nodo {nodo!r} no existe en el grafo.")

    def _exigir_arista(self, a, b):
        if not self.existe_arista(a, b):
            raise KeyError(f"No existe la arista {a!r} -> {b!r}.")

    @staticmethod
    def _validar_peso(peso):
        if peso < 0:
            raise ValueError(f"Peso {peso!r} inválido: los pesos deben ser >= 0.")
