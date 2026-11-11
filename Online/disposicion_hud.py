"""Dónde van los botones REPORTAR y SABOTEAR del modo Online (lógica pura).

Siempre a la izquierda: a la derecha el juego muestra el feed de Civitas
(los comentarios de los ciudadanos), el minimapa y los paneles de J2 y J4.

    Ciudad              abajo a la izquierda.
    Mazmorra o jefe     con 2 jugadores, en el margen izquierdo, bajo el
                        panel de J1; con 3 o 4 (el margen es del panel de
                        J3), dentro del rincón inferior izquierdo del cuarto.
                        Con el "HUD detallado" (el panel de misión abajo a la
                        izquierda), suben por encima de ese panel.
    Terminal            REPORTAR chico, a la izquierda de la barra de
                        controles (ahí no hay SABOTEAR).

Los rectángulos son tuplas (x, y, ancho, alto) en px de pantalla (1280x720).
"""

from src.core.escenas import Escena

ANCHO_BOTON, ALTO_BOTON = 100, 92
SEPARACION_BOTONES = 8
ALTO_MINIMO_BOTON_GRANDE = 70  # más bajo que esto, el botón se dibuja en una sola fila

ORIGEN_CIUDAD = (16, 548)  # abajo a la izquierda, sobre la barra de controles
ORIGEN_MARGEN = (10, 452)  # combate con 2 jugadores: uno sobre otro, bajo el panel de J1
ORIGEN_CUARTO = (148, 548)  # combate con 3-4: rincón inferior izquierdo del cuarto
SUBIDA_HUD_DETALLADO = 116  # alto del panel de misión de combate (assets.RECT_PANEL_MISION_COMBATE)
RECT_REPORTAR_TERMINAL = (12, 666, 224, 48)


def _lado_a_lado(origen):
    x, y = origen
    return (x, y, ANCHO_BOTON, ALTO_BOTON), (x + ANCHO_BOTON + SEPARACION_BOTONES, y, ANCHO_BOTON, ALTO_BOTON)


def rects_botones(escena, cantidad_jugadores=2, hud_detallado=False):
    """(rect de REPORTAR, rect de SABOTEAR o None) para `escena`."""
    if escena == Escena.DECISION:
        return RECT_REPORTAR_TERMINAL, None
    if escena in (Escena.MAZMORRA, Escena.JEFE):
        if cantidad_jugadores <= 2:
            x, y = ORIGEN_MARGEN
            reportar = (x, y, ANCHO_BOTON + 4, ALTO_BOTON)
            return reportar, (x, y + ALTO_BOTON + SEPARACION_BOTONES + 4, ANCHO_BOTON + 4, ALTO_BOTON)
        x, y = ORIGEN_CUARTO
        return _lado_a_lado((x, y - SUBIDA_HUD_DETALLADO if hud_detallado else y))
    return _lado_a_lado(ORIGEN_CIUDAD)
