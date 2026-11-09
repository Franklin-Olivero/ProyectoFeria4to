"""Configuración global de pantalla y reloj (sin lógica de juego)."""

import pygame

ANCHO_PANTALLA = 1280
ALTO_PANTALLA = 720
FPS = 60

TITULO_VENTANA = "Civitas"


def crear_pantalla():
    """Inicializa la ventana del juego con el tamaño y título del proyecto."""
    # La lógica siempre es 1280×720; la ventana se puede agrandar y SDL escala
    # la imagen con barras negras (sirve para un proyector o pantalla completa).
    try:
        pantalla = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA), pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        pantalla = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA))
    pygame.display.set_caption(TITULO_VENTANA)
    return pantalla


def crear_reloj():
    """Crea el reloj usado para limitar el loop principal a FPS."""
    return pygame.time.Clock()
