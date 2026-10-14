"""Escenas de la máquina de estados de Main.py (sin Pygame).

    MAPA_CIUDAD --(ENTER en una zona)--> MAZMORRA --(cuarto final limpio)--> DECISION
    DECISION --(resultado)--> RESULTADO --(ENTER)--> MAPA_CIUDAD
    MAPA_CIUDAD --(ENTER en Alcaldía, si está desbloqueada)--> JEFE --> VICTORIA
    VICTORIA --(ENTER)--> MAPA_CIUDAD          VICTORIA --(ESC)--> salir
    cualquiera --(colapso al 100%)--> DERROTA --(ENTER)--> MAPA_CIUDAD (partida nueva)

Vive aparte de Main.py para poder probar la transición a la derrota
global sin abrir ventana.
"""

from enum import Enum


class Escena(Enum):
    MAPA_CIUDAD = "mapa_ciudad"  # elegir zona y viajar: sin combate
    MAZMORRA = "mazmorra"  # combate en los cuartos de una mazmorra normal
    DECISION = "decision"  # terminal de decisión: input solo para la terminal
    RESULTADO = "resultado"  # pantalla con el resultado de la decisión: ENTER sigue
    JEFE = "jefe"  # combate en la arena del jefe final
    VICTORIA = "victoria"  # jefe derrotado: ENTER o ESC, sin combate
    DERROTA = "derrota"  # colapso total: ENTER o ESC, sin combate


ESCENAS_DE_COMBATE = (Escena.MAZMORRA, Escena.JEFE)


def escena_tras_colapso(escena, colapso):
    """DERROTA si la barra llegó al 100%; si no, la misma escena."""
    return Escena.DERROTA if colapso.esta_colapsado() else escena
