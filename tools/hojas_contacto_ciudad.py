"""Hojas de contacto de los packs de exteriores (revisión, fuera de git).

    python tools/hojas_contacto_ciudad.py            # -> _packs/trabajo_ciudad/contacto/
    python tools/hojas_contacto_ciudad.py --paso 32

Por cada lámina de _packs/extraidos/<pack>/ guarda una copia con una
cuadrícula cada `--paso` px y sus coordenadas en px escritas cada 2 líneas,
para elegir los recortes de tools/empaquetar_ciudad.py con criterio. Las
láminas de estos packs no tienen grilla de tiles real (son ilustraciones
de 1024 px con celdas de ~170-216 px), por eso los recortes se dan en px.
"""

import argparse
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

PACKS = ("paths_roads", "edges_borders", "corners", "walls", "floors_interior", "liquids", "decorations")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paso", type=int, default=64)
    parser.add_argument("--salida", default=os.path.join("_packs", "trabajo_ciudad", "contacto"))
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    pygame.init()
    letra = pygame.font.SysFont("consolas", 14, bold=True)
    for pack in PACKS:
        carpeta = os.path.join("_packs", "extraidos", pack)
        if not os.path.isdir(carpeta):
            print("falta", carpeta, file=sys.stderr)
            continue
        for nombre in sorted(os.listdir(carpeta)):
            imagen = pygame.image.load(os.path.join(carpeta, nombre)).convert(24) if pygame.display.get_surface() \
                else pygame.image.load(os.path.join(carpeta, nombre))
            hoja = imagen.copy()
            ancho, alto = hoja.get_size()
            for x in range(0, ancho, args.paso):
                pygame.draw.line(hoja, (255, 0, 255), (x, 0), (x, alto), 1)
            for y in range(0, alto, args.paso):
                pygame.draw.line(hoja, (255, 0, 255), (0, y), (ancho, y), 1)
            for y in range(0, alto, args.paso * 2):
                for x in range(0, ancho, args.paso * 2):
                    texto = letra.render(f"{x},{y}", True, (255, 255, 0), (0, 0, 0))
                    hoja.blit(texto, (x + 2, y + 2))
            destino = os.path.join(args.salida, f"{pack}__{nombre.replace(' ', '_').replace('&', 'y')}")
            pygame.image.save(hoja, destino)
            print(destino, (ancho, alto))


if __name__ == "__main__":
    main()
