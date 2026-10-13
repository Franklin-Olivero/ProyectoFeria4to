"""Progreso de la partida entre mazmorras (sin Pygame).

Lleva cuántas mazmorras normales se completaron y aplica el resultado
del minijuego de decisión sobre el Colapso Electoral. Una mazmorra
cuenta como completada SOLO si la decisión fue "Purificación
Exitosa"; una "Detonación" suma colapso pero no cuenta. Ese contador
es el que desbloquea la mazmorra final (ver
src/dungeon/mazmorra_final.esta_desbloqueada).
"""

from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA


class ProgresoPartida:
    def __init__(self):
        self.mazmorras_completadas = 0

    def registrar_decision(self, resultado, colapso):
        """Aplica el resultado de la terminal de decisión."""
        if resultado == PURIFICACION_EXITOSA:
            colapso.restar_exito()
            self.mazmorras_completadas += 1
        elif resultado == DETONACION:
            colapso.sumar_fallo()
