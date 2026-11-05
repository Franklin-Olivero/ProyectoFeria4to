"""Misión de redención «Segunda oportunidad» (lógica pura, sin Pygame).

Cuando la reputación de un jugador cae a -60 o menos, la crisis ofrece
aceptar la responsabilidad o negarse. Si acepta, esta misión reutiliza las
estructuras del juego; no se recupera nada pulsando un botón:

    Etapa 1, RECONOCER (árbol N-ario): identificar la publicación que dañó
        y, con las pruebas a la vista, decidir cómo responder.
    Etapa 2, CORREGIR (grafo social + BFS): elegir desde qué ciudadano sale
        la corrección. RedSocial.corregir hace un BFS real hasta
        SALTOS_CORRECCION_REDENCION saltos; debe alcanzar al menos
        COBERTURA_REDENCION de los ciudadanos expuestos al rumor.
    Etapa 3, CONFIANZA (árbol N-ario): ayudar a un ciudadano afectado a
        distinguir qué fuente sirve para responder su pregunta.

Condiciones justas y visibles: cada error gasta una de las
OPORTUNIDADES_REDENCION y explica por qué estuvo mal; sin oportunidades, la
misión se reintenta REINTENTOS_REDENCION veces desde la etapa en curso (sin
perder lo ya hecho). Solo entonces queda fallida. Etapas 2 y 3 se abren en
puntos de la ciudad, así que la misión se puede pausar y entrar a una mazmorra
con el equipo en medio de ella.
"""

from dataclasses import dataclass

from src.core.balance import (
    COBERTURA_REDENCION,
    OPORTUNIDADES_REDENCION,
    PUBLICACIONES_REDENCION,
    REINTENTOS_REDENCION,
    SALTOS_CORRECCION_REDENCION,
)
from src.structures.tree import ArbolDecision

ETAPA_RECONOCER = "reconocer"
ETAPA_CORREGIR = "corregir"
ETAPA_CONFIANZA = "confianza"
ETAPA_COMPLETA = "completa"
ETAPA_FALLIDA = "fallida"
ETAPAS = (ETAPA_RECONOCER, ETAPA_CORREGIR, ETAPA_CONFIANZA)

IZQUIERDA = "izquierda"
DERECHA = "derecha"
CONFIRMAR = "confirmar"


class EleccionCrisis:
    """Las dos salidas de la crisis. Moverse no decide nada: hay que
    confirmar, sin reloj, para que nadie falle por la interfaz."""

    ACEPTAR = "aceptar"
    RECHAZAR = "rechazar"

    def __init__(self):
        self.seleccion = self.ACEPTAR
        self.resultado = None

    def navegar(self, direccion):
        if self.resultado is not None:
            return
        if direccion == CONFIRMAR:
            self.resultado = self.seleccion
        else:
            self.seleccion = self.RECHAZAR if self.seleccion == self.ACEPTAR else self.ACEPTAR


@dataclass(frozen=True)
class Respuesta:
    """Datos de una opción de los árboles de las etapas 1 y 3."""

    correcta: bool
    explicacion: str = ""


class ArbolEtapa:
    """Un árbol N-ario navegable donde una respuesta incorrecta explica su
    error y deja al jugador en el mismo nodo para volver a intentarlo. O(1)
    por movimiento."""

    def __init__(self, titulo, niveles):
        """`niveles`: lista de {"pregunta", "opciones": [{texto, correcta, explicacion}]}.
        Cada opción correcta baja al siguiente nivel; la última termina."""
        self.arbol = ArbolDecision(0, titulo)
        self.respuestas = {}
        self.preguntas = {0: niveles[0]["pregunta"]}
        siguiente_id = 1
        padre = 0
        for numero, nivel in enumerate(niveles):
            siguiente_padre = None
            for opcion in nivel["opciones"]:
                self.arbol.insertar(padre, siguiente_id, opcion["texto"])
                self.respuestas[siguiente_id] = Respuesta(bool(opcion.get("correcta")), opcion.get("explicacion", ""))
                if opcion.get("correcta") and siguiente_padre is None:
                    siguiente_padre = siguiente_id
                    if numero + 1 < len(niveles):
                        self.preguntas[siguiente_id] = niveles[numero + 1]["pregunta"]
                siguiente_id += 1
            padre = siguiente_padre
        self.nodo = self.arbol.raiz
        self.indice = 0
        self.terminado = False

    @property
    def pregunta(self):
        return self.preguntas.get(self.nodo.id, "")

    @property
    def opciones(self):
        return self.nodo.hijos

    def mover(self, paso):
        if self.opciones:
            self.indice = (self.indice + paso) % len(self.opciones)

    def confirmar(self):
        """Respuesta elegida. Si es correcta baja por el árbol; si no hay
        más niveles, termina. Si es incorrecta, se queda donde estaba."""
        elegido = self.opciones[self.indice]
        respuesta = self.respuestas[elegido.id]
        if respuesta.correcta:
            self.nodo = elegido
            self.indice = 0
            self.terminado = not self.nodo.hijos
        return respuesta


class MisionRedencion:
    def __init__(self, datos, publicacion, pruebas, red, ayuda, reintentos=REINTENTOS_REDENCION):
        """`datos`: content "redencion"; `publicacion`: post que dañó el
        jugador; `pruebas`: evidencias de esa zona; `red`: la RedSocial de
        la campaña; `ayuda`: {pregunta, ciudadano, opciones} de la etapa 3."""
        self.datos = datos
        self.publicacion = publicacion
        self.pruebas = list(pruebas)
        self.red = red
        self.ayuda = ayuda
        self.etapa = ETAPA_RECONOCER
        self.oportunidades = OPORTUNIDADES_REDENCION
        self.reintentos = reintentos
        self.aviso = ""  # explicación del último error o de lo que falta
        self.errores = 0
        # Etapa 2.
        self.objetivo_correccion = sorted(red.expuestos - red.corregidos)
        self.publicaciones_restantes = PUBLICACIONES_REDENCION
        # El cursor empieza en quien tiene menos contactos: elegir bien pide leer el grafo.
        ciudadanos = red.ciudadanos()
        self.indice_ciudadano = min(range(len(ciudadanos)), key=lambda i: len(red.grafo.vecinos(ciudadanos[i])))
        self.correcciones = []  # Propagacion de cada corrección publicada
        self.alcanzados = set()
        # Árboles.
        self.arbol_reconocer = self._armar_arbol_reconocer()
        self.arbol_confianza = None

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    @property
    def terminada(self):
        return self.etapa in (ETAPA_COMPLETA, ETAPA_FALLIDA)

    @property
    def completada(self):
        return self.etapa == ETAPA_COMPLETA

    @property
    def fallida(self):
        return self.etapa == ETAPA_FALLIDA

    @property
    def numero_etapa(self):
        return ETAPAS.index(self.etapa) + 1 if self.etapa in ETAPAS else len(ETAPAS)

    # ------------------------------------------------------------------
    # Etapa 1: reconocer
    # ------------------------------------------------------------------
    def _armar_arbol_reconocer(self):
        """Primer nivel: cuál publicación dañó (la real entre señuelos del
        contenido, en orden fijo para que nada delate la respuesta). Segundo
        nivel: cómo responder con las pruebas a la vista."""
        reales = {"texto": self.publicacion["usuario"] + ": " + self.publicacion["texto"], "correcta": True}
        senuelos = [{"texto": s["usuario"] + ": " + s["texto"], "correcta": False, "explicacion": s["explicacion"]}
                    for s in self.datos["senuelos"]]
        indice = len(self.publicacion["texto"]) % (len(senuelos) + 1)
        opciones = senuelos[:indice] + [reales] + senuelos[indice:]
        niveles = [{"pregunta": self.datos["pregunta_publicacion"], "opciones": opciones},
                   {"pregunta": self.datos["pregunta_responsabilidad"], "opciones": self.datos["respuestas_responsabilidad"]}]
        return ArbolEtapa("Reconocer el error", niveles)

    # ------------------------------------------------------------------
    # Etapa 2: corregir (BFS real)
    # ------------------------------------------------------------------
    @property
    def ciudadanos(self):
        return self.red.ciudadanos()

    @property
    def ciudadano_elegido(self):
        return self.ciudadanos[self.indice_ciudadano]

    def cobertura(self):
        """Fracción de los ciudadanos expuestos que ya recibió la corrección."""
        if not self.objetivo_correccion:
            return 1.0
        return len(self.alcanzados & set(self.objetivo_correccion)) / len(self.objetivo_correccion)

    def sin_corregir(self):
        return [n for n in self.objetivo_correccion if n not in self.alcanzados]

    def publicar_correccion(self, origen=None):
        """BFS exacto desde `origen`: RedSocial.corregir marca a los
        alcanzados, que rebotan menos el rumor. Si llega a la cobertura
        pedida, pasa a la etapa 3. Sin publicaciones ni cobertura, se pierde
        una oportunidad y se concede una publicación más."""
        origen = origen if origen is not None else self.ciudadano_elegido
        correccion = self.red.corregir(origen, SALTOS_CORRECCION_REDENCION)
        self.correcciones.append(correccion)
        self.alcanzados.update(correccion.alcanzados)
        self.publicaciones_restantes -= 1
        if self.cobertura() >= COBERTURA_REDENCION:
            self.aviso = ""
            self.etapa = ETAPA_CONFIANZA
            self.arbol_confianza = ArbolEtapa("Recuperar la confianza", [
                {"pregunta": self.ayuda["pregunta"], "opciones": self.ayuda["opciones"]}])
            return correccion
        if self.publicaciones_restantes <= 0:
            self._error(self.datos["aviso_cobertura"])
            if not self.terminada:
                self.publicaciones_restantes = 1
        else:
            self.aviso = self.datos["aviso_quedan"]
        return correccion

    # ------------------------------------------------------------------
    # Navegación común
    # ------------------------------------------------------------------
    def navegar(self, direccion):
        if self.terminada:
            return
        paso = -1 if direccion == IZQUIERDA else 1
        if self.etapa == ETAPA_CORREGIR:
            if direccion == CONFIRMAR:
                self.publicar_correccion()
            else:
                self.indice_ciudadano = (self.indice_ciudadano + paso) % len(self.ciudadanos)
            return
        arbol = self.arbol_reconocer if self.etapa == ETAPA_RECONOCER else self.arbol_confianza
        if direccion != CONFIRMAR:
            arbol.mover(paso)
            return
        respuesta = arbol.confirmar()
        if not respuesta.correcta:
            self._error(respuesta.explicacion)
            return
        self.aviso = ""
        if arbol.terminado:
            self.etapa = ETAPA_CORREGIR if self.etapa == ETAPA_RECONOCER else ETAPA_COMPLETA

    def _error(self, explicacion):
        """Un error cuesta una oportunidad y siempre explica el porqué."""
        self.errores += 1
        self.aviso = explicacion
        self.oportunidades -= 1
        if self.oportunidades > 0:
            return
        if self.reintentos > 0:
            self.reintentos -= 1
            self.oportunidades = OPORTUNIDADES_REDENCION
            self.aviso = self.datos["aviso_reintento"]
            return
        self.etapa = ETAPA_FALLIDA
