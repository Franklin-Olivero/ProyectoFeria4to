"""Configuración global de pantalla y reloj (sin lógica de juego)."""

import pygame

ANCHO_PANTALLA = 800
ALTO_PANTALLA = 600
FPS = 60

TITULO_VENTANA = "Civitas - Cuarto de prueba"

COLOR_FONDO = (40, 44, 52)


def crear_pantalla():
    """Inicializa la ventana del juego con el tamaño y título del proyecto."""
    pantalla = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA))
    pygame.display.set_caption(TITULO_VENTANA)
    return pantalla


def crear_reloj():
    """Crea el reloj usado para limitar el loop principal a FPS."""
    return pygame.time.Clock()
