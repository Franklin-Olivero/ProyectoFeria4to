"""Minijuego de decisión contra reloj (lógica pura, sin Pygame).

Aparece al limpiar una mazmorra normal: el jugador ve una situación de
redes sociales y navega un árbol N-ario (src/structures/tree.py) hasta
llegar a una hoja final. El árbol fijo de este módulo es:

    Publicación Viral
    ├── Verificar  -> Purificación Exitosa
    ├── Me gusta   -> Detonación
    ├── Compartir  -> Detonación
    ├── Reportar   -> Purificación Exitosa
    └── Ignorar    -> Detonación

El cursor es un puntero a un NodoArbol: "izquierda"/"derecha" mueven un
índice sobre la lista `.hijos` del nodo actual y "confirmar" desciende
al hijo seleccionado. Si el reloj llega a 0 antes de alcanzar una hoja,
el resultado es "Detonación" automática.

El dibujo vive aparte, en src/ui/terminal_decision_render.py, para que
esta lógica se pueda probar con pytest sin Pygame.
"""

from src.structures.tree import ArbolDecision

DURACION_TERMINAL = 10.0  # segundos

PURIFICACION_EXITOSA = "Purificación Exitosa"
DETONACION = "Detonación"

IZQUIERDA = "izquierda"
DERECHA = "derecha"
CONFIRMAR = "confirmar"

# (opción, hoja final a la que lleva). Verificar y Reportar purifican;
# Me gusta, Compartir e Ignorar detonan: darle me gusta a una publicación
# viral sin verificar también la amplifica. Verificar va primero porque
# es la opción segura que queda bajo el cursor al abrir la terminal.
OPCIONES_PUBLICACION = [
    ("Verificar", PURIFICACION_EXITOSA),
    ("Me gusta", DETONACION),
    ("Compartir", DETONACION),
    ("Reportar", PURIFICACION_EXITOSA),
    ("Ignorar", DETONACION),
]


def construir_arbol_publicacion():
    """Arma el árbol fijo de la situación "Publicación Viral".

    Ids: raíz = 0, opciones = 1..5, hojas = 11, 21, ..., 51 (opción * 10 + 1),
    para que dos hojas con la misma etiqueta no compartan id.

    Complejidad: O(k^2) con k = 5 opciones, porque cada insertar() busca
    al padre y verifica el id con DFS sobre el árbol en construcción.
    Con un árbol de 11 nodos es despreciable.
    """
    arbol = ArbolDecision(0, "Publicación Viral")
    for numero, (opcion, hoja) in enumerate(OPCIONES_PUBLICACION, start=1):
        arbol.insertar(0, numero, opcion)
        arbol.insertar(numero, numero * 10 + 1, hoja)
    return arbol


class TerminalDecision:
    """Estado del minijuego: nodo actual, hijo seleccionado y reloj.

    Atributos:
        arbol: ArbolDecision ya armado que se va a navegar.
        nodo_actual: NodoArbol donde está parado el cursor.
        indice_seleccionado: posición dentro de `nodo_actual.hijos`.
        tiempo_restante: segundos que quedan antes de la detonación.
        activa: True entre iniciar() y la llegada a un resultado.
    """

    def __init__(self, arbol, duracion=DURACION_TERMINAL, descender_resultados=False):
        """`descender_resultados`: al elegir una opción cuyo único hijo es
        el nodo de resultado se llega a él de una vez. El modo historia lo usa:
        el jugador no ve la hoja, así que el resultado no se le anticipa."""
        self.descender_resultados = descender_resultados
        self.arbol = arbol
        self.duracion = duracion
        self.nodo_actual = arbol.raiz
        self.indice_seleccionado = 0
        self.tiempo_restante = duracion
        self.activa = False
        self._resultado = None

    def iniciar(self):
        """Arranca el reloj y posiciona el cursor en la raíz."""
        self.nodo_actual = self.arbol.raiz
        self.indice_seleccionado = 0
        self.tiempo_restante = self.duracion
        self._resultado = None
        self.activa = True

    @property
    def resultado(self):
        """None mientras no se llegue a una hoja final; si no, su texto."""
        return self._resultado

    @property
    def hijo_seleccionado(self):
        if not self.nodo_actual.hijos:
            return None
        return self.nodo_actual.hijos[self.indice_seleccionado]

    def camino(self):
        """Lista de nodos desde la raíz hasta `nodo_actual` (inclusive).

        Lo usa la pantalla para resaltar el camino recorrido y las migas
        de pan. Complejidad: O(n), DFS hasta encontrar el nodo actual.
        """
        return self._camino_hasta(self.arbol.raiz, self.nodo_actual) or [self.nodo_actual]

    def _camino_hasta(self, nodo, objetivo):
        if nodo is objetivo:
            return [nodo]
        for hijo in nodo.hijos:
            resto = self._camino_hasta(hijo, objetivo)
            if resto:
                return [nodo] + resto
        return None

    @property
    def opcion_elegida(self):
        """Etiqueta de la opción de primer nivel por la que se bajó, o None
        si el cursor sigue en la raíz."""
        camino = self.camino()
        return camino[1].etiqueta if len(camino) > 1 else None

    def navegar(self, direccion):
        """Mueve el cursor entre hijos ("izquierda"/"derecha") o desciende
        al hijo seleccionado ("confirmar").

        Moverse da la vuelta al llegar a un extremo (módulo la cantidad
        de hijos). Se ignora si la terminal no está activa.

        Complejidad: O(1); solo se cambia un índice o un puntero a nodo.
        """
        if not self.activa or not self.nodo_actual.hijos:
            return

        cantidad = len(self.nodo_actual.hijos)
        if direccion == IZQUIERDA:
            self.indice_seleccionado = (self.indice_seleccionado - 1) % cantidad
        elif direccion == DERECHA:
            self.indice_seleccionado = (self.indice_seleccionado + 1) % cantidad
        elif direccion == CONFIRMAR:
            self.nodo_actual = self.hijo_seleccionado
            self.indice_seleccionado = 0
            if self.descender_resultados and len(self.nodo_actual.hijos) == 1 \
                    and not self.nodo_actual.hijos[0].hijos:
                self.nodo_actual = self.nodo_actual.hijos[0]
            if not self.nodo_actual.hijos:
                self._terminar(self.nodo_actual.etiqueta)

    def actualizar(self, dt):
        """Descuenta el reloj; si llega a 0 sin resultado, detona."""
        if not self.activa:
            return
        self.tiempo_restante = max(0.0, self.tiempo_restante - dt)
        if self.tiempo_restante == 0.0:
            self._terminar(DETONACION)

    def _terminar(self, resultado):
        self._resultado = resultado
        self.activa = False
