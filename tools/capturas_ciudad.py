"""Capturas de Ciudad Nova para revisión visual (sin ventana).

    python tools/capturas_ciudad.py                 # -> docs/capturas/ciudad/
    python tools/capturas_ciudad.py --salida otra/carpeta

Guarda la panorámica (el mapa entero, reducido a la mitad) y un recorte a
tamaño real de cada zona: plaza central, parque, zonas escolar,
hospitalaria, de medios y cívica, la avenida y el lote del Distrito
Liminal. Los recortes son del tamaño de la vista del juego.
"""

import argparse
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

TAM = 48
# Esquina superior izquierda (en casillas) de cada recorte de 1280x720.
RECORTES = {
    "plaza_central": (19, 17),
    "parque": (10, 13),
    "zona_escolar": (0, 1),
    "zona_civica": (24, 1),
    "zona_hospitalaria": (0, 26),
    "zona_medios": (36, 26),
    "avenida": (24, 8),
    "distrito_liminal_reservado": (19, 32),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", default=os.path.join("docs", "capturas", "ciudad"))
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from src.dungeon.partida import Partida
    from src.ui import ciudad_render

    mundo = ciudad_render.render_panoramico(Partida())
    pygame.image.save(pygame.transform.smoothscale_by(mundo, 0.5), os.path.join(args.salida, "panoramica.png"))
    for nombre, (col, fila) in RECORTES.items():
        rect = pygame.Rect(col * TAM, fila * TAM, 1280, 720).clamp(mundo.get_rect())
        pygame.image.save(mundo.subsurface(rect), os.path.join(args.salida, f"{nombre}.png"))
    print("capturas en", args.salida)


if __name__ == "__main__":
    main()
