"""Reduce árboles del pack Trees_Vol2 a sprites chicos para la ciudad.

    python tools/reducir_arboles.py 1 3 9 12             # -> assets/sprites/props/arboles/arbol_NN.png
    python tools/reducir_arboles.py --todos --salida carpeta_temporal   # hoja de contacto

Los PNG del pack (_packs/extraidos/trees_vol2/, fuera de git) son
ilustraciones de ~900x1150 px. Se recortan a su caja visible, se reducen
(suavizado) a ALTO_ARBOL px de alto conservando la proporción y el alfa se
umbraliza (>= 128 -> opaco, si no transparente) para que el contorno quede
nítido como pixel art. El juego los dibuja a ESCALA_PIXEL.
"""

import argparse
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

PACK = os.path.join(RAIZ, "_packs", "extraidos", "trees_vol2", "Trees_Vol2", "without_shadow")
SALIDA = os.path.join(RAIZ, "assets", "sprites", "props", "arboles")


ALTO_ARBOL = 48
UMBRAL_ALFA = 128


def reducir(ruta, alto=ALTO_ARBOL):
    imagen = pygame.image.load(ruta).convert_alpha()
    imagen = imagen.subsurface(imagen.get_bounding_rect()).copy()
    ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
    chica = pygame.transform.smoothscale(imagen, (ancho, alto))
    for y in range(alto):
        for x in range(ancho):
            r, g, b, a = chica.get_at((x, y))
            chica.set_at((x, y), (r, g, b, 255 if a >= UMBRAL_ALFA else 0))
    return chica.subsurface(chica.get_bounding_rect()).copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("numeros", nargs="*", type=int)
    parser.add_argument("--todos", action="store_true")
    parser.add_argument("--salida", default=SALIDA)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    numeros = range(1, 101) if args.todos else args.numeros
    os.makedirs(args.salida, exist_ok=True)
    for numero in numeros:
        origen = os.path.join(PACK, f"tree_medium_{numero:02d}.png")
        if not os.path.exists(origen):
            print(f"falta {origen}")
            continue
        sprite = reducir(origen)
        pygame.image.save(sprite, os.path.join(args.salida, f"arbol_{numero:02d}.png"))
        print(f"arbol_{numero:02d}: {sprite.get_width()}x{sprite.get_height()}")


if __name__ == "__main__":
    main()
