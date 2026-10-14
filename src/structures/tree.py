"""Árbol N-ario implementado a mano (sin librerías de terceros).

Gobierna dos mecánicas del juego:

1. Clasificador de reportes de toxicidad (lógica de fondo, invisible
para el jugador): la raíz representa una zona/edificio de la
ciudad y cada descendiente representa una publicación o reporte de mal
uso de redes (comentario, publicación viral, denuncia...) con su
gravedad. Recorrer el árbol permite agregar la toxicidad de la zona, y
ese valor decide la dificultad de la mazmorra que se genera (ver
src/dungeon/clasificador_toxicidad.py).

2. Minijuego de decisión al final de cada mazmorra normal: el jugador
navega activamente el árbol "Publicación Viral" desde la raíz hasta una
hoja final (ver src/ui/terminal_decision.py).

Este módulo no conoce el significado de las etiquetas: solo ofrece la
estructura, el CRUD y los recorridos, para poder probarse de forma
aislada y sin Pygame.
"""

from collections import deque


class NodoArbol:
    """Nodo de un árbol N-ario.

    Atributos:
        id: identificador único del nodo dentro del árbol.
        etiqueta: dato que representa el nodo. En el clasificador de
            toxicidad es el nombre de la zona (raíz) o el diccionario
            del reporte ({"id", "tipo", "gravedad"}) en los demás nodos.
        hijos: lista de NodoArbol, en el orden en que fueron insertados.
    """

    def __init__(self, id, etiqueta):
        self.id = id
        self.etiqueta = etiqueta
        self.hijos = []


class ArbolDecision:
    """Árbol N-ario con operaciones CRUD y los 4 recorridos clásicos.

    Uso en el juego (clasificador): al generar una mazmorra se construye un árbol cuya
    raíz es la zona/edificio y cuyos nodos son los reportes de toxicidad
    de esa zona. Un recorrido completo agrega la gravedad de los reportes
    y produce el nivel de toxicidad que determina cuántos enemigos
    aparecen y qué tan rápidos son. El jugador ve el efecto (una
    mazmorra más fácil o más difícil), nunca la estructura. El mismo
    árbol también se navega nodo a nodo en el minijuego de decisión.

    En todas las complejidades, n es el número total de nodos del árbol.
    No se usa ninguna estructura auxiliar (como un diccionario id -> nodo)
    a propósito: cada operación recorre el árbol explícitamente para que
    su costo sea fácil de explicar y sustentar en voz alta.
    """

    def __init__(self, id_raiz, etiqueta_raiz):
        self.raiz = NodoArbol(id_raiz, etiqueta_raiz)

    # ------------------------------------------------------------------
    # Búsqueda (usada internamente por insertar/eliminar)
    # ------------------------------------------------------------------

    def buscar(self, id):
        """Busca un nodo por id recorriendo el árbol en profundidad (DFS).

        Retorna el NodoArbol si existe, o None si no se encuentra.

        Complejidad: O(n) en el peor caso, porque hay que visitar cada
        nodo una vez hasta encontrar el id buscado (o agotar el árbol).
        """
        if self.raiz is None:
            return None
        return self._buscar_recursivo(self.raiz, id)

    def _buscar_recursivo(self, nodo, id):
        if nodo.id == id:
            return nodo
        for hijo in nodo.hijos:
            encontrado = self._buscar_recursivo(hijo, id)
            if encontrado is not None:
                return encontrado
        return None

    def _buscar_padre(self, nodo, id):
        """Helper interno: retorna el nodo padre del nodo con `id`.

        Retorna None si `id` pertenece a la raíz o no existe en el árbol.
        Complejidad: O(n), misma naturaleza que buscar().
        """
        for hijo in nodo.hijos:
            if hijo.id == id:
                return nodo
            resultado = self._buscar_padre(hijo, id)
            if resultado is not None:
                return resultado
        return None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def insertar(self, id_padre, id_nuevo, etiqueta):
        """Agrega un nuevo nodo hijo (id_nuevo, etiqueta) al nodo id_padre.

        Lanza ValueError si el árbol está vacío, si no existe un nodo
        con id_padre, o si id_nuevo ya está en uso por otro nodo.

        Complejidad: O(n). Ubicar al nodo padre con DFS cuesta O(n); una
        vez ubicado, adjuntar el hijo a su lista (`hijos.append`) es
        O(1) amortizado, así que el costo total lo domina la búsqueda.
        """
        if self.raiz is None:
            raise ValueError("El árbol está vacío; no hay ningún nodo padre.")
        if self.buscar(id_nuevo) is not None:
            raise ValueError(f"Ya existe un nodo con id {id_nuevo!r}.")
        padre = self.buscar(id_padre)
        if padre is None:
            raise ValueError(f"No existe un nodo padre con id {id_padre!r}.")
        nuevo_nodo = NodoArbol(id_nuevo, etiqueta)
        padre.hijos.append(nuevo_nodo)
        return nuevo_nodo

    def eliminar(self, id):
        """Elimina el nodo con `id` y todo su subárbol.

        Si `id` es el de la raíz, elimina el árbol completo (self.raiz
        queda en None). Retorna True si se eliminó algo, False si el id
        no existe.

        Complejidad: O(n). Encontrar al nodo padre con DFS es O(n); quitar
        al hijo de la lista `hijos` del padre es O(k), con k la cantidad
        de hijos de ese padre (k <= n). No hace falta recorrer el
        subárbol eliminado nodo por nodo: al desconectarlo de su padre,
        Python libera esas referencias automáticamente (garbage
        collection).
        """
        if self.raiz is None:
            return False
        if self.raiz.id == id:
            self.raiz = None
            return True
        padre = self._buscar_padre(self.raiz, id)
        if padre is None:
            return False
        padre.hijos = [hijo for hijo in padre.hijos if hijo.id != id]
        return True

    # ------------------------------------------------------------------
    # Recorridos
    # ------------------------------------------------------------------

    def preorden(self):
        """Recorrido preorden: nodo, luego cada hijo (izq. a der.), recursivo.

        Retorna una lista de etiquetas en ese orden.

        Complejidad: O(n), cada nodo se visita exactamente una vez.
        """
        resultado = []
        if self.raiz is not None:
            self._preorden_recursivo(self.raiz, resultado)
        return resultado

    def _preorden_recursivo(self, nodo, resultado):
        resultado.append(nodo.etiqueta)
        for hijo in nodo.hijos:
            self._preorden_recursivo(hijo, resultado)

    def inorden(self):
        """Recorrido inorden, adaptado a árboles N-arios.

        Convención usada (el inorden clásico "izquierda, nodo, derecha"
        solo está definido de forma natural para árboles binarios): para
        cada nodo se recorre primero el subárbol de su PRIMER hijo
        (haciendo de "rama izquierda"), luego se visita el nodo, y por
        último se recorren en orden los subárboles del RESTO de sus
        hijos (haciendo de "rama derecha"). Un nodo sin hijos se visita
        directamente a sí mismo.

        Retorna una lista de etiquetas en ese orden.

        Complejidad: O(n), cada nodo se visita exactamente una vez.
        """
        resultado = []
        if self.raiz is not None:
            self._inorden_recursivo(self.raiz, resultado)
        return resultado

    def _inorden_recursivo(self, nodo, resultado):
        if not nodo.hijos:
            resultado.append(nodo.etiqueta)
            return
        primer_hijo, *resto_hijos = nodo.hijos
        self._inorden_recursivo(primer_hijo, resultado)
        resultado.append(nodo.etiqueta)
        for hijo in resto_hijos:
            self._inorden_recursivo(hijo, resultado)

    def postorden(self):
        """Recorrido postorden: cada hijo (izq. a der.), recursivo, luego el nodo.

        Retorna una lista de etiquetas en ese orden.

        Complejidad: O(n), cada nodo se visita exactamente una vez.
        """
        resultado = []
        if self.raiz is not None:
            self._postorden_recursivo(self.raiz, resultado)
        return resultado

    def _postorden_recursivo(self, nodo, resultado):
        for hijo in nodo.hijos:
            self._postorden_recursivo(hijo, resultado)
        resultado.append(nodo.etiqueta)

    def por_niveles(self):
        """Recorrido por niveles (BFS), de arriba hacia abajo y de izq. a der.

        Usa una cola (collections.deque) para procesar los nodos en el
        orden en que fueron descubiertos.

        Retorna una lista de etiquetas en ese orden.

        Complejidad: O(n), cada nodo se encola y desencola exactamente
        una vez.
        """
        resultado = []
        if self.raiz is None:
            return resultado
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            resultado.append(nodo.etiqueta)
            cola.extend(nodo.hijos)
        return resultado
