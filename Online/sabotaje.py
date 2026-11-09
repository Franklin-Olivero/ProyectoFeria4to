"""Bloqueo del sabotaje del impostor en la terminal de decisión del modo Online (lógica pura).

Al final de cada mazmorra normal el equipo comparte un cursor sobre el árbol
de decisión: cualquiera lo mueve (← →) o confirma (Enter). El impostor
también, pero al abrirse la terminal queda bloqueado un tiempo que el host
sortea entre COOLDOWN_SABOTAJE_MIN y COOLDOWN_SABOTAJE_MAX (10 a 15 s).
Mientras tanto los demás buscan la respuesta correcta; después el impostor
elige normal, sin límite de movimientos, y así sabotea.

El host lleva el bloqueo (autoritativo) y lo manda en el ESTADO; cada
invitado solo lo muestra. Sin pygame, para probarse en aislado. El azar va
por un random.Random inyectable (los tests le pasan uno con semilla).
Todo es O(1).
"""

import random

from src.core.balance import COOLDOWN_SABOTAJE_MAX, COOLDOWN_SABOTAJE_MIN


class Sabotaje:
    """Bloqueo del impostor para una terminal a la vez."""

    def __init__(self, minimo=COOLDOWN_SABOTAJE_MIN, maximo=COOLDOWN_SABOTAJE_MAX, azar=None):
        self.minimo = minimo
        self.maximo = maximo
        self._azar = azar if azar is not None else random.Random()
        self.espera = maximo  # s de bloqueo sorteados para la terminal actual
        self.restante = maximo  # s que faltan para que el impostor pueda elegir
        self.activo = False  # True con una terminal de decisión abierta
        self._terminal = None  # la última terminal que se siguió

    def seguir_terminal(self, terminal):
        """Cada frame, con la terminal abierta (o None si no hay ninguna).
        Una terminal nueva sortea su bloqueo y empieza a contarlo; la misma
        terminal sigue su cuenta (una por mazmorra: cada decisión crea la suya)."""
        if terminal is not None and terminal is not self._terminal:
            self.espera = self._azar.uniform(self.minimo, self.maximo)
            self.restante = self.espera
            self._terminal = terminal
        self.activo = terminal is not None

    def actualizar(self, dt):
        if self.activo:
            self.restante = max(0.0, self.restante - dt)

    @property
    def listo(self):
        """True cuando terminó el bloqueo: el impostor mueve y confirma
        normal, todas las veces que quiera, hasta que se cierre la terminal."""
        return self.activo and self.restante <= 0.0
