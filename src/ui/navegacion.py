"""Acciones abstractas de navegación de menús y nombres de sonidos (sin Pygame).

Main.py traduce teclado, control y ratón a estas acciones; el menú
principal (src/ui/menu_principal.py) y el modal de ajustes
(src/ui/ajustes.py) solo reciben acciones, así su lógica se prueba sin
ventana y un mismo comando vale igual venga de donde venga.

Cada acción devuelve el sonido que corresponde (o None): el sonido sale
de un cambio real de estado, nunca de cada frame ni de cada evento.
"""

from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA

ARRIBA = "arriba"
ABAJO = "abajo"
VOLVER = "volver"  # Esc, Retroceso o ○
PESTANA_ANTERIOR = "pestana_anterior"  # Q o L1
PESTANA_SIGUIENTE = "pestana_siguiente"  # E o R1

__all__ = [
    "ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA", "CONFIRMAR", "VOLVER",
    "PESTANA_ANTERIOR", "PESTANA_SIGUIENTE",
    "SONIDO_NAVEGAR", "SONIDO_CONFIRMAR", "SONIDO_VOLVER",
]

# Sonidos de interfaz (src/audio/gestor_audio.py los carga por este nombre).
SONIDO_NAVEGAR = "navegar"
SONIDO_CONFIRMAR = "confirmar"
SONIDO_VOLVER = "volver"
