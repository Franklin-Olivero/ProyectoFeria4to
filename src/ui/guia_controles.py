"""Asignaciones reales de controles para la guía de la pestaña CONTROLES.

Las teclas y botones salen de las mismas constantes que lee el juego
(src/core/entrada.py y src/core/balance.py): si cambia una asignación,
la guía cambia sola. Solo se listan acciones que existen; el juego no
tiene pausa ni botón de interacción, así que no aparecen.
"""

import pygame

from src.core.balance import CLICK_DISPARA
from src.core.entrada import (
    BOTON_DASH,
    BOTON_HABILIDAD,
    EJE_DISPARO,
    TECLA_ARBOL,
    TECLA_DISPARAR,
    TECLA_HABILIDAD,
    TECLA_MINIMAPA,
    TECLAS_DASH,
)

# Nombres en pantalla de teclas cuyo nombre de SDL es largo o en inglés.
_NOMBRES_TECLA = {"space": "Espacio", "left shift": "Shift", "right shift": "Shift", "tab": "Tab"}

# Botones y ejes de SDL -> rótulo en un DualShock 4 (el control compatible).
ETIQUETAS_PS4 = {
    ("boton", pygame.CONTROLLER_BUTTON_A): "✕",
    ("boton", pygame.CONTROLLER_BUTTON_B): "○",
    ("boton", pygame.CONTROLLER_BUTTON_X): "□",
    ("boton", pygame.CONTROLLER_BUTTON_Y): "△",
    ("boton", pygame.CONTROLLER_BUTTON_LEFTSHOULDER): "L1",
    ("boton", pygame.CONTROLLER_BUTTON_RIGHTSHOULDER): "R1",
    ("eje", pygame.CONTROLLER_AXIS_TRIGGERLEFT): "L2",
    ("eje", pygame.CONTROLLER_AXIS_TRIGGERRIGHT): "R2",
}

NOTA_TECLADO = "El Candidato no usa el ratón: apunta hacia donde camina."
NOTA_MANDO = "En la partida, el control de PS4 maneja al J2 (cooperativo local)."
NOTA_MENUS_MANDO = "Menús: cruceta o stick izq. para moverse · ✕ confirmar · ○ volver · L1/R1 pestañas"


def nombre_tecla(tecla):
    nombre = pygame.key.name(tecla)
    return _NOMBRES_TECLA.get(nombre, nombre.upper())


def acciones_teclado():
    """[(acción, [teclas], nota o None)] del J1 (teclado y ratón)."""
    disparar = [nombre_tecla(TECLA_DISPARAR)] + (["Clic izq."] if CLICK_DISPARA else [])
    return [
        ("Mover", ["W", "A", "S", "D"], "o flechas"),
        ("Apuntar", ["Ratón"], None),
        ("Disparar", disparar, "mantener"),
        ("Habilidad", [nombre_tecla(TECLA_HABILIDAD)], None),
        ("Dash", [nombre_tecla(TECLAS_DASH[0])], None),
        ("Minimapa", [nombre_tecla(TECLA_MINIMAPA)], None),
        ("Ver árbol de IA", [nombre_tecla(TECLA_ARBOL)], None),
        ("Menús", ["↑ ↓ ← →", "Enter"], None),
        ("Volver / menú", ["Esc"], None),
    ]


def acciones_mando():
    """{elemento del dibujo del control: (rótulo, acción)} del J2."""
    return {
        "stick_izq": ("Stick izq.", "Mover"),
        "stick_der": ("Stick der.", "Apuntar"),
        "gatillo_der": (ETIQUETAS_PS4[("eje", EJE_DISPARO)], "Disparar"),
        "hombro_izq": (ETIQUETAS_PS4[("boton", BOTON_HABILIDAD)], "Habilidad"),
        "cruz": (ETIQUETAS_PS4[("boton", BOTON_DASH)], "Dash"),
        "cruceta": ("Cruceta", "Menús"),
    }
