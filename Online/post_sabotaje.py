"""Botón SABOTEAR del impostor: una publicación viral de emergencia (lógica pura).

El impostor aprieta SABOTEAR (se puede cada COOLDOWN_POST_SABOTAJE s) y a
todas las PCs les salta en el celular una publicación falsa, como la
terminal del final de la mazmorra pero con poco tiempo
(DURACION_POST_SABOTAJE): el equipo tiene que elegir rápido qué hacer con
ella. Verificar o Reportar la frenan; Me gusta, Compartir o Ignorar la
vuelven viral (el árbol fijo de src/ui/terminal_decision.py). El impostor
también puede elegir, pero recién después de BLOQUEO_POST_SABOTAJE s: si
nadie eligió bien antes, puede elegir una mala. Si se acaba el tiempo, el
rumor se vuelve viral. Nadie sabe quién lo lanzó.

El host lleva todo (autoritativo) y lo manda en el ESTADO (`a_dict`); cada
invitado solo lo muestra (`vista_de_dict`) y manda sus teclas como
DECISION_NAV. Las publicaciones salen de content/campaign.json ("sabotajes");
las dos PCs tienen el mismo contenido, así que basta mandar el índice. El
azar va por un random.Random inyectable. Todo es O(1) por frame.
"""

import random
from dataclasses import dataclass

from src.core.balance import (
    BLOQUEO_POST_SABOTAJE, COOLDOWN_POST_SABOTAJE, DURACION_POST_SABOTAJE, DURACION_RESULTADO_POST_SABOTAJE,
)
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA, TerminalDecision, construir_arbol_publicacion

RESULTADOS = (PURIFICACION_EXITOSA, DETONACION)


class ControlSabotajes:
    """El botón SABOTEAR, la publicación en curso y cómo terminó."""

    def __init__(self, cantidad_posts=1, recarga=COOLDOWN_POST_SABOTAJE, duracion=DURACION_POST_SABOTAJE,
                 bloqueo=BLOQUEO_POST_SABOTAJE, duracion_resultado=DURACION_RESULTADO_POST_SABOTAJE, azar=None):
        self.cantidad_posts = max(1, cantidad_posts)
        self.recarga = recarga
        self.duracion = duracion
        self.bloqueo = bloqueo
        self.duracion_resultado = duracion_resultado
        self._azar = azar if azar is not None else random.Random()
        self.recarga_restante = recarga  # el primero también espera
        self.terminal = None  # la publicación en curso (TerminalDecision del árbol fijo)
        self.indice_post = None
        self.bloqueo_restante = 0.0  # s que le faltan al impostor para poder elegir
        self.resultado = None  # {"res", "op", "i"}: cómo terminó la última, mientras se muestra
        self.resultado_restante = 0.0
        self.numero = 0  # sabotajes lanzados: el invitado nota cuándo empieza otro
        self._orden = []  # publicaciones que faltan salir (sin repetir hasta agotarlas)

    @property
    def activo(self):
        return self.terminal is not None

    @property
    def en_curso(self):
        """Hay publicación o se está mostrando cómo terminó: el mundo espera."""
        return self.activo or self.resultado_restante > 0.0

    def puede_sabotear(self):
        return not self.en_curso and self.recarga_restante <= 0.0

    def sabotear(self):
        """Lanza una publicación si el botón está listo. True si salió."""
        if not self.puede_sabotear():
            return False
        if not self._orden:
            self._orden = list(range(self.cantidad_posts))
            self._azar.shuffle(self._orden)
        self.indice_post = self._orden.pop()
        self.terminal = TerminalDecision(construir_arbol_publicacion(), self.duracion, descender_resultados=True)
        self.terminal.iniciar()
        self.bloqueo_restante = self.bloqueo
        self.resultado = None
        self.numero += 1
        return True

    def navegar(self, direccion, es_impostor=False):
        """Mueve o confirma en la publicación; el impostor, solo tras su bloqueo.
        True si se aplicó."""
        if self.terminal is None or (es_impostor and self.bloqueo_restante > 0.0):
            return False
        self.terminal.navegar(direccion)
        return True

    def actualizar(self, dt):
        """El reloj de la publicación, el del resultado o el del botón (uno a la
        vez). Retorna el resultado en el frame en que la publicación termina
        (el host aplica sus efectos una sola vez); si no, None."""
        if self.terminal is not None:
            self.terminal.actualizar(dt)
            self.bloqueo_restante = max(0.0, self.bloqueo_restante - dt)
            if self.terminal.resultado is not None:
                return self._cerrar()
        elif self.resultado_restante > 0.0:
            self.resultado_restante = max(0.0, self.resultado_restante - dt)
        else:
            self.recarga_restante = max(0.0, self.recarga_restante - dt)
        return None

    def _cerrar(self):
        self.resultado = {"res": self.terminal.resultado, "op": self.terminal.opcion_elegida, "i": self.indice_post}
        self.terminal = None
        self.resultado_restante = self.duracion_resultado
        self.recarga_restante = self.recarga
        return dict(self.resultado)

    def a_dict(self):
        """Lo que viaja en el ESTADO (claves cortas, solo listas y números)."""
        datos = {"rcd": round(self.recarga_restante, 2), "n": self.numero}
        if self.terminal is not None:
            t = self.terminal
            datos["post"] = {"i": self.indice_post, "nodo": t.nodo_actual.id, "idx": t.indice_seleccionado,
                             "t": round(t.tiempo_restante, 2), "dur": t.duracion, "bloq": round(self.bloqueo_restante, 2)}
        elif self.resultado is not None and self.resultado_restante > 0.0:
            datos["res"] = dict(self.resultado, tr=round(self.resultado_restante, 2))
        return datos


@dataclass(frozen=True)
class VistaSabotaje:
    """Lo que Main dibuja y consulta, igual en el host y en el invitado."""

    recarga: float = COOLDOWN_POST_SABOTAJE
    numero: int = 0
    activo: bool = False
    indice_post: int = 0
    nodo: int = 0  # id del nodo del árbol fijo donde está el cursor
    seleccion: int = 0
    restante: float = 0.0
    duracion: float = DURACION_POST_SABOTAJE
    bloqueo: float = 0.0  # s que le faltan al impostor
    resultado: str | None = None  # PURIFICACION_EXITOSA o DETONACION, mientras se muestra
    opcion: str | None = None  # la que eligieron (None: se acabó el tiempo)
    resultado_restante: float = 0.0

    @property
    def mostrando_resultado(self):
        return self.resultado is not None and self.resultado_restante > 0.0

    @property
    def en_curso(self):
        return self.activo or self.mostrando_resultado


def _numero(valor, por_defecto=0.0, maximo=1e4):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor != valor:
        return por_defecto
    return max(0.0, min(maximo, float(valor)))


def _entero(valor):
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0 else None


def vista_de_dict(datos):
    """VistaSabotaje a partir de `a_dict()`; lo que no tiene la forma esperada se descarta."""
    if not isinstance(datos, dict):
        return VistaSabotaje()
    campos = {"recarga": _numero(datos.get("rcd"), COOLDOWN_POST_SABOTAJE), "numero": int(_numero(datos.get("n")))}
    post = datos.get("post")
    if isinstance(post, dict) and _entero(post.get("i")) is not None:
        campos.update(activo=True, indice_post=post["i"], nodo=_entero(post.get("nodo")) or 0,
                      seleccion=_entero(post.get("idx")) or 0, restante=_numero(post.get("t")),
                      duracion=_numero(post.get("dur"), DURACION_POST_SABOTAJE) or DURACION_POST_SABOTAJE,
                      bloqueo=_numero(post.get("bloq")))
    resultado = datos.get("res")
    if isinstance(resultado, dict) and resultado.get("res") in RESULTADOS:
        opcion = resultado.get("op")
        campos.update(resultado=resultado["res"], opcion=opcion if isinstance(opcion, str) else None,
                      resultado_restante=_numero(resultado.get("tr")), indice_post=_entero(resultado.get("i")) or 0)
    return VistaSabotaje(**campos)
