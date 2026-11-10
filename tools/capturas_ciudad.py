"""Capturas de Ciudad Nova para revisión visual (sin ventana).

    python tools/capturas_ciudad.py                 # -> docs/capturas/ciudad/ y docs/capturas/ciudad_despues.png
    python tools/capturas_ciudad.py --salida otra/carpeta --sin-despues

Guarda la panorámica (el mapa entero, reducido a la mitad) y un recorte a
tamaño real de cada zona: plaza central, parque, paseo comercial, zonas
escolar, hospitalaria, de medios y cívica, la Avenida Nova con sus cruces,
el canal con sus puentes y el lote del Distrito Liminal. Los recortes son
del tamaño de la vista del juego. La panorámica también se copia a
docs/capturas/ciudad_despues.png (la de antes del rediseño es
docs/capturas/ciudad_antes.png).
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
    "plaza_central": (17, 17),
    "parque": (33, 9),
    "zona_comercial": (20, 28),
    "zona_escolar": (0, 2),
    "zona_civica": (30, 0),
    "zona_hospitalaria": (2, 28),
    "zona_medios": (36, 30),
    "avenida_cruces": (0, 18),
    "canal_puentes": (27, 3),
    "distrito_liminal_reservado": (14, 32),
}
DESPUES = os.path.join("docs", "capturas", "ciudad_despues.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", default=os.path.join("docs", "capturas", "ciudad"))
    parser.add_argument("--sin-despues", action="store_true", help="no reemplazar " + DESPUES)
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from src.dungeon.partida import Partida
    from src.ui import ciudad_render

    mundo = ciudad_render.render_panoramico(Partida())
    panoramica = pygame.transform.smoothscale_by(mundo, 0.5)
    pygame.image.save(panoramica, os.path.join(args.salida, "panoramica.png"))
    if not args.sin_despues:
        pygame.image.save(panoramica, DESPUES)
    for nombre, (col, fila) in RECORTES.items():
        rect = pygame.Rect(col * TAM, fila * TAM, 1280, 720).clamp(mundo.get_rect())
        pygame.image.save(mundo.subsurface(rect), os.path.join(args.salida, f"{nombre}.png"))
    print("capturas en", args.salida)


if __name__ == "__main__":
    main()
