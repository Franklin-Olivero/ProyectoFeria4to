"""Punto de entrada del juego."""

import sys

import pygame

from src.core.config import COLOR_FONDO, FPS, crear_pantalla, crear_reloj
from src.dungeon.cuarto import Cuarto


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    cuarto = Cuarto()

    ejecutando = True
    while ejecutando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            else:
                cuarto.manejar_evento(evento)

        pantalla.fill(COLOR_FONDO)
        cuarto.dibujar(pantalla)
        pygame.display.flip()

        reloj.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
