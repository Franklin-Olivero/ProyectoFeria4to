"""Sabotaje del impostor en la terminal de decisión del modo Online (lógica pura).

Al final de cada mazmorra normal el equipo comparte un cursor sobre el árbol
de decisión: cualquiera lo mueve (← →) o confirma (Enter). El impostor
también, pero cada movimiento suyo es un sabotaje y solo puede hacerlo con
la carga lista. La carga tarda COOLDOWN_SABOTAJE_IMPOSTOR segundos en
llenarse: al abrir la terminal y después de cada uso. Así los demás siempre
tienen ese tiempo para buscar la respuesta correcta.

El host lleva la carga (autoritativo) y la manda en el ESTADO; cada invitado
solo la muestra. Sin pygame, para probarse en aislado. Todo es O(1).
"""

from src.core.balance import COOLDOWN_SABOTAJE_IMPOSTOR


class Sabotaje:
    """Carga del sabotaje para una terminal a la vez."""

    def __init__(self, recarga=COOLDOWN_SABOTAJE_IMPOSTOR):
        self.recarga = recarga
        self.restante = recarga  # s que faltan para poder sabotear
        self._terminal = None

    def seguir_terminal(self, terminal):
        """Cada frame, con la terminal abierta (o None si no hay ninguna).
        Una terminal nueva empieza con la carga vacía; sin terminal no hay
        nada que sabotear y la carga queda vacía."""
        if terminal is None or terminal is not self._terminal:
            self.restante = self.recarga
        self._terminal = terminal

    def actualizar(self, dt):
        if self.activo:
            self.restante = max(0.0, self.restante - dt)

    @property
    def activo(self):
        """True con una terminal de decisión abierta."""
        return self._terminal is not None

    @property
    def listo(self):
        return self.activo and self.restante <= 0.0

    def intentar(self):
        """El impostor quiere mover o confirmar: True si tenía la carga
        lista (y la gasta); False si todavía se está recargando."""
        if not self.listo:
            return False
        self.restante = self.recarga
        return True
