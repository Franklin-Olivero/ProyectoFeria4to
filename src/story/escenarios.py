"""Escenarios de decisión por zona sobre el árbol N-ario (sin Pygame).

Cada zona con mazmorra normal tiene en content/campaign.json una
publicación de Civitas, una lista de evidencias y las opciones de su
árbol. Aquí se arma un ArbolDecision (src/structures/tree.py) con esa
forma:

    Publicación (raíz, id 0)
    ├── Verificar ── Publicar aclaración...  -> hoja
    │             └─ Creer el rumor          -> hoja
    ├── Me gusta                             -> hoja
    ├── Compartir                            -> hoja
    ├── Reportar ─── Reportar con evidencia  -> hoja
    │             └─ Reportar en masa        -> hoja
    └── Ignorar                              -> hoja

La forma del árbol no depende de la evidencia (así host e invitado
comparten ids); lo que cambia con el estado_de_evidencia es a qué
RESULTADO lleva cada hoja y su consecuencia. Una hoja con
`por_evidencia` define alternativas para "sin_pruebas" y "parcial":
publicar una aclaración sin tener el comunicado no purifica nada.
"Me gusta" amplifica como un compartir más suave: detona o purifica
según la veracidad real, igual que "Compartir", pero con menos efecto.

Las hojas llevan como etiqueta el texto del resultado (Purificación
Exitosa / Detonación), igual que el árbol original: TerminalDecision y
Partida.cerrar_mazmorra siguen funcionando sin cambios. La consecuencia
completa (texto, efectos sobre los indicadores y puntos) se busca por
el id del nodo hoja donde terminó la terminal. La reputación no viene
escrita en la hoja: cada hoja declara su `accion` y src/story/reputacion.py
la valora según la veracidad real y lo que el jugador podía saber.
"""

from dataclasses import dataclass, field

from src.story.contenido import RESULTADO_PURIFICACION
from src.structures.tree import ArbolDecision
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA

SIN_PRUEBAS = "sin_pruebas"
PARCIAL = "parcial"
VERIFICADO = "verificado"
DESMENTIDO = "desmentido"
ESTADOS_EVIDENCIA = (SIN_PRUEBAS, PARCIAL, VERIFICADO, DESMENTIDO)

NOMBRES_ESTADO_EVIDENCIA = {
    SIN_PRUEBAS: "Sin pruebas",
    PARCIAL: "Pruebas parciales",
    VERIFICADO: "Verificada",
    DESMENTIDO: "Desmentida",
}

ID_RAIZ = 0


def estado_evidencia(reveladas, total, veredicto):
    """Estado según cuántas evidencias de `total` se revelaron y el
    veredicto real de la publicación (content: "cierto", "falso",
    "fuera_de_contexto", "sin_verificar")."""
    if total <= 0 or reveladas <= 0:
        return SIN_PRUEBAS
    if reveladas < total:
        return PARCIAL
    if veredicto == "cierto":
        return VERIFICADO
    if veredicto in ("falso", "fuera_de_contexto"):
        return DESMENTIDO
    return PARCIAL  # "sin_verificar": ni con todo se puede cerrar


@dataclass
class Consecuencia:
    resultado: str  # PURIFICACION_EXITOSA o DETONACION
    texto: str
    efectos: dict = field(default_factory=dict)
    reputacion: int = 0  # cambio real de reputación (lo llena Campania al aplicarla)
    puntos: int = 0
    camino: tuple = ()  # etiquetas de las opciones elegidas (raíz excluida)
    estado_evidencia: str = SIN_PRUEBAS
    accion: str = ""  # clave de balance.VALORACION_ACCIONES

    @property
    def exito(self):
        return self.resultado == PURIFICACION_EXITOSA

    @property
    def opcion(self):
        """Opción de primer nivel ("Verificar", "Compartir"...), o None."""
        return self.camino[0] if self.camino else None


def _resultado_texto(clave):
    return PURIFICACION_EXITOSA if clave == RESULTADO_PURIFICACION else DETONACION


def _resolver_hoja(datos, estado):
    """Datos efectivos de una hoja según el estado de evidencia."""
    alternativa = datos.get("por_evidencia", {}).get(estado)
    return alternativa if alternativa is not None else datos


def consecuencia_de_datos(datos, estado, camino=(), accion=None):
    return Consecuencia(
        resultado=_resultado_texto(datos["resultado"]),
        texto=datos["texto"],
        efectos=dict(datos.get("efectos", {})),
        puntos=int(datos.get("puntos", 0)),
        camino=tuple(camino),
        estado_evidencia=estado,
        accion=accion if accion is not None else datos.get("accion", ""),
    )


class EscenarioDecision:
    """Árbol de una zona ya armado para un estado de evidencia dado.

    Atributos:
        datos: el diccionario del escenario en el contenido.
        estado: estado de evidencia con el que se armó.
        arbol: ArbolDecision navegable por TerminalDecision.
        hojas: {id de nodo hoja: Consecuencia}.
    """

    def __init__(self, datos, estado):
        self.datos = datos
        self.estado = estado
        self.hojas = {}
        self._siguiente_id = ID_RAIZ + 1
        self.arbol = ArbolDecision(ID_RAIZ, datos["titulo"])
        for opcion in datos["opciones"]:
            self._insertar(ID_RAIZ, opcion, ())

    def _insertar(self, id_padre, opcion, camino):
        """Inserta la opción y, recursivamente, sus hijos; una hoja
        agrega además el nodo de resultado y registra su consecuencia.
        Complejidad: O(n) por insertar() (DFS del árbol), n = nodos; con
        ~15 nodos por escenario es despreciable."""
        id_opcion = self._nuevo_id()
        self.arbol.insertar(id_padre, id_opcion, opcion["etiqueta"])
        camino = camino + (opcion["etiqueta"],)
        if "hijos" in opcion:
            for hijo in opcion["hijos"]:
                self._insertar(id_opcion, hijo, camino)
            return
        efectivos = _resolver_hoja(opcion, self.estado)
        # La acción es de la hoja: la alternativa por evidencia solo cambia el desenlace.
        consecuencia = consecuencia_de_datos(efectivos, self.estado, camino, opcion.get("accion", ""))
        id_hoja = self._nuevo_id()
        self.arbol.insertar(id_opcion, id_hoja, consecuencia.resultado)
        self.hojas[id_hoja] = consecuencia

    def _nuevo_id(self):
        nuevo = self._siguiente_id
        self._siguiente_id += 1
        return nuevo

    @property
    def post(self):
        return self.datos["post"]

    @property
    def titulo(self):
        return self.datos["titulo"]

    @property
    def resultado_verificacion(self):
        """Lo que descubre el jugador al elegir "Verificar", según sus pruebas."""
        textos = self.datos.get("verificacion", {})
        clave = self.estado if self.estado in (SIN_PRUEBAS, PARCIAL) else "completa"
        return textos.get(clave, "")

    def consecuencia_tiempo_agotado(self):
        return consecuencia_de_datos(self.datos["tiempo_agotado"], self.estado, ())

    def consecuencia_para(self, terminal):
        """Consecuencia del estado final de una TerminalDecision armada
        con este árbol: la de la hoja donde quedó, o la de tiempo
        agotado si el reloj venció antes de llegar a una hoja."""
        nodo = terminal.nodo_actual
        if nodo.id in self.hojas and not nodo.hijos:
            return self.hojas[nodo.id]
        return self.consecuencia_tiempo_agotado()

    def consecuencia_por_camino(self, *etiquetas):
        """Consecuencia a la que llevan las opciones `etiquetas` (para
        tests y para la guía de sustentación). None si no es una hoja."""
        for consecuencia in self.hojas.values():
            if consecuencia.camino == tuple(etiquetas):
                return consecuencia
        return None
