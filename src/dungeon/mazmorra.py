"""Mazmorra normal de varios cuartos sobre un Grafo (lógica pura, sin Pygame).

Cada nodo del grafo (src/structures/graph.py) es un cuarto, numerado
0, 1, 2... en el orden en que se eligió, y cada arista es un pasillo.
El grafo gobierna toda la mecánica:

    - Generación: DFS aleatorio sobre una cuadrícula 3x3 hasta tener
      `cantidad_cuartos` celdas; las aristas del DFS son los pasillos y
      se agrega 1 arista extra entre celdas vecinas ya elegidas (un
      ciclo: hay más de un camino). Una puerta N/S/E/W existe solo
      donde hay arista.
    - Entrada = primera celda elegida (cuarto 0, sin enemigos).
      Cuarto final = el más lejano por BFS desde la entrada (desempate:
      menor id). Solo ahí aparece el minijuego de decisión.
    - Generación perezosa: un cuarto decide su dificultad la primera
      vez que se entra, con nivel_a_dificultad(toxicidad_local).
    - Propagación de toxicidad: cada PROPAGACION_INTERVALO s en un
      cuarto con enemigos vivos, BFS desde ese cuarto y cada cuarto aún
      NO generado a distancia d >= 1 suma PROPAGACION_INCREMENTO / d
      (tope TOXICIDAD_MAXIMA_CUARTO). Quedarse mucho endurece los
      cuartos cercanos; los lejanos casi no cambian.

La parte física (Cuarto de Pygame, cruzar puertas, colocar al jugador)
vive en src/dungeon/mazmorra_jugable.py.
"""

import random

from src.core.balance import (
    CANTIDAD_CUARTOS_MAZMORRA,
    DIFICULTAD_ENTRADA,
    LADO_CUADRICULA_MAZMORRA,
    PROPAGACION_INCREMENTO,
    PROPAGACION_INTERVALO,
    TOXICIDAD_MAXIMA_CUARTO,
)
from src.dungeon.clasificador_toxicidad import (
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)
from src.structures.graph import Grafo

# Dirección de una puerta -> (dx, dy) en la cuadrícula (y crece hacia abajo).
DESPLAZAMIENTOS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPUESTA = {"N": "S", "S": "N", "E": "W", "W": "E"}


class Mazmorra:
    """Layout, estado de cada cuarto y propagación de toxicidad.

    Atributos principales:
        grafo: Grafo de cuartos (pesos 1).
        celdas: {cuarto: (x, y)} en la cuadrícula.
        entrada, cuarto_final, actual: ids de cuarto.
        toxicidad: {cuarto: nivel 0-100}; arranca en el nivel de la zona.
        dificultad: {cuarto: dict} solo para los cuartos ya generados.
        visitados, limpiados: conjuntos de ids.
        tiempo_en_cuarto: segundos acumulados con enemigos vivos.
    """

    def __init__(self, reportes, nombre_zona, cantidad_cuartos=CANTIDAD_CUARTOS_MAZMORRA, semilla=None):
        total_celdas = LADO_CUADRICULA_MAZMORRA**2
        if not 2 <= cantidad_cuartos <= total_celdas:
            raise ValueError(
                f"cantidad_cuartos debe estar entre 2 y {total_celdas}, no {cantidad_cuartos}."
            )
        self.nombre_zona = nombre_zona
        self.rng = random.Random(semilla)
        self.nivel_zona = calcular_nivel_toxicidad(construir_arbol_reportes(reportes, nombre_zona))

        self.grafo = Grafo()
        self.celdas = {}
        self._generar_layout(cantidad_cuartos)
        # Garantía de diseño (DFS, O(V + E)): todo cuarto es alcanzable.
        if not self.grafo.es_conexo():
            raise RuntimeError("La mazmorra generada no es conexa.")

        self.entrada = 0
        self.cuarto_final = self._elegir_cuarto_final()
        self.toxicidad = {cuarto: self.nivel_zona for cuarto in self.grafo.nodos()}
        self.dificultad = {}
        self.visitados = set()
        self.limpiados = set()
        self.tiempo_en_cuarto = 0.0
        self.actual = None
        self.entrar(self.entrada)

    # ------------------------------------------------------------------
    # Generación
    # ------------------------------------------------------------------

    def _generar_layout(self, cantidad):
        """DFS aleatorio con pila explícita sobre la cuadrícula.

        Desde la celda del tope de la pila se elige al azar una celda
        vecina libre: se agrega como cuarto nuevo, se une con un pasillo
        y se apila. Si no hay vecinas libres se desapila (backtracking).
        Como el DFS puede recorrer toda la cuadrícula, siempre llega a
        `cantidad` cuartos, y el resultado es un árbol (conexo, sin
        ciclos) al que luego se le agrega una arista extra.
        Complejidad: O(C) con C = celdas de la cuadrícula (9).
        """
        lado = LADO_CUADRICULA_MAZMORRA
        inicio = (self.rng.randrange(lado), self.rng.randrange(lado))
        cuarto_por_celda = {inicio: 0}
        self.celdas[0] = inicio
        self.grafo.agregar_nodo(0)
        pila = [inicio]
        while len(cuarto_por_celda) < cantidad:
            celda = pila[-1]
            libres = [v for v in self._celdas_vecinas(celda) if v not in cuarto_por_celda]
            if not libres:
                pila.pop()
                continue
            nueva = self.rng.choice(libres)
            nuevo_id = len(cuarto_por_celda)
            cuarto_por_celda[nueva] = nuevo_id
            self.celdas[nuevo_id] = nueva
            self.grafo.agregar_arista(cuarto_por_celda[celda], nuevo_id)
            pila.append(nueva)

        # Arista extra entre dos cuartos vecinos en la cuadrícula que aún
        # no tienen pasillo: crea un ciclo (si existe tal par).
        candidatas = []
        for cuarto, celda in self.celdas.items():
            for vecina in self._celdas_vecinas(celda):
                otro = cuarto_por_celda.get(vecina)
                if otro is not None and cuarto < otro and not self.grafo.existe_arista(cuarto, otro):
                    candidatas.append((cuarto, otro))
        if candidatas:
            a, b = self.rng.choice(candidatas)
            self.grafo.agregar_arista(a, b)

    @staticmethod
    def _celdas_vecinas(celda):
        """Celdas N/S/E/W de `celda` que caen dentro de la cuadrícula."""
        x, y = celda
        lado = LADO_CUADRICULA_MAZMORRA
        vecinas = []
        for dx, dy in DESPLAZAMIENTOS.values():
            nx, ny = x + dx, y + dy
            if 0 <= nx < lado and 0 <= ny < lado:
                vecinas.append((nx, ny))
        return vecinas

    def _elegir_cuarto_final(self):
        """El cuarto con mayor distancia BFS desde la entrada; si empatan,
        el de menor id. O(V + E)."""
        _, distancias, _ = self.grafo.bfs(self.entrada)
        return max(distancias, key=lambda cuarto: (distancias[cuarto], -cuarto))

    # ------------------------------------------------------------------
    # Puertas y movimiento
    # ------------------------------------------------------------------

    def puertas(self, cuarto):
        """{dirección: cuarto vecino} solo para las direcciones con pasillo."""
        x, y = self.celdas[cuarto]
        resultado = {}
        for vecino in self.grafo.vecinos(cuarto):
            vx, vy = self.celdas[vecino]
            for direccion, (dx, dy) in DESPLAZAMIENTOS.items():
                if (x + dx, y + dy) == (vx, vy):
                    resultado[direccion] = vecino
        return resultado

    def mover(self, direccion):
        """Pasa al cuarto vecino por la puerta `direccion` del cuarto
        actual. Retorna el id del cuarto nuevo, o None si no hay pasillo.
        (Que la puerta esté abierta lo decide el cuarto físico.)"""
        vecino = self.puertas(self.actual).get(direccion)
        if vecino is None:
            return None
        self.entrar(vecino)
        return vecino

    def entrar(self, cuarto):
        """Hace de `cuarto` el actual y lo genera si es la primera vez.

        Generar = fijar su dificultad con nivel_a_dificultad sobre su
        toxicidad local en ese momento (ya incluye la propagación que
        haya recibido). La entrada no tiene enemigos.
        """
        self.actual = cuarto
        self.visitados.add(cuarto)
        self.tiempo_en_cuarto = 0.0
        if cuarto not in self.dificultad:
            if cuarto == self.entrada:
                self.dificultad[cuarto] = dict(DIFICULTAD_ENTRADA)
            else:
                self.dificultad[cuarto] = nivel_a_dificultad(self.toxicidad[cuarto])
        if self.dificultad[cuarto]["cantidad_enemigos"] == 0:
            self.limpiados.add(cuarto)

    def esta_generado(self, cuarto):
        return cuarto in self.dificultad

    def marcar_limpiado(self, cuarto):
        self.limpiados.add(cuarto)

    @property
    def final_descubierto(self):
        return self.cuarto_final in self.visitados

    # ------------------------------------------------------------------
    # Propagación de toxicidad
    # ------------------------------------------------------------------

    def actualizar(self, dt, hay_enemigos_vivos):
        """Acumula tiempo solo si quedan enemigos vivos en el cuarto
        actual; cada PROPAGACION_INTERVALO s propaga la toxicidad."""
        if not hay_enemigos_vivos:
            return
        self.tiempo_en_cuarto += dt
        while self.tiempo_en_cuarto >= PROPAGACION_INTERVALO:
            self.tiempo_en_cuarto -= PROPAGACION_INTERVALO
            self.propagar_desde(self.actual)

    def propagar_desde(self, origen):
        """BFS desde `origen`: cada cuarto NO generado a distancia d >= 1
        suma PROPAGACION_INCREMENTO / d, sin pasar de
        TOXICIDAD_MAXIMA_CUARTO. Los generados no cambian (su dificultad
        ya está fija). O(V + E)."""
        _, distancias, _ = self.grafo.bfs(origen)
        for cuarto, distancia in distancias.items():
            if distancia >= 1 and not self.esta_generado(cuarto):
                self.toxicidad[cuarto] = min(
                    TOXICIDAD_MAXIMA_CUARTO,
                    self.toxicidad[cuarto] + PROPAGACION_INCREMENTO / distancia,
                )

    # ------------------------------------------------------------------
    # Minimapa
    # ------------------------------------------------------------------

    def ruta_al_final(self):
        """Camino más corto (en cuartos) del actual al final, por BFS."""
        _, _, predecesores = self.grafo.bfs(self.actual)
        return Grafo.camino(predecesores, self.actual, self.cuarto_final)
