"""Quita el fondo verde de un retrato generado y lo deja listo para el juego.

    python tools/procesar_retrato.py entrada.png assets/sprites/retratos/rosa.png

Clave de croma sin dependencias: los píxeles verdes se vuelven transparentes y se
le quita el tinte verde al borde del personaje. Sale a 512×512, como los demás.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402


def procesar(entrada, salida, lado=512):
    pygame.init()
    pygame.display.set_mode((1, 1))
    imagen = pygame.image.load(entrada).convert_alpha()
    ancho, alto = imagen.get_size()
    for y in range(alto):
        for x in range(ancho):
            r, g, b, a = imagen.get_at((x, y))
            verde = g - max(r, b)
            if g > 120 and verde > 50:
                imagen.set_at((x, y), (0, 0, 0, 0))
            elif verde > 16:  # borde teñido por el fondo
                imagen.set_at((x, y), (r, max(r, b), b, a))
    if (ancho, alto) != (lado, lado):
        imagen = pygame.transform.smoothscale(imagen, (lado, lado))
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    pygame.image.save(imagen, salida)


if __name__ == "__main__":
    procesar(sys.argv[1], sys.argv[2])
