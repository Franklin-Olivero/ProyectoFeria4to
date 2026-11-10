"""Mide la paleta de la panorámica de Ciudad Nova (sin ventana).

    python tools/medir_paleta_ciudad.py                       # renderiza la ciudad actual
    python tools/medir_paleta_ciudad.py --imagen otra.png     # mide una imagen (p. ej. la de antes)

Muestrea uno de cada PASO x PASO píxeles y reporta el % de píxeles de
neón saturado (src/core/medicion_paleta.es_saturado), el reparto por
familia de color y cuántas familias dominan, contra los topes de
balance.py (MAX_FRACCION_SATURADA_CIUDAD, MAX_FAMILIAS_DOMINANTES_CIUDAD).
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

from src.core.balance import MAX_FAMILIAS_DOMINANTES_CIUDAD, MAX_FRACCION_SATURADA_CIUDAD  # noqa: E402
from src.core.medicion_paleta import medir  # noqa: E402

PASO = 3


def pixeles(superficie, paso=PASO):
    """(r, g, b) de uno de cada paso x paso píxeles."""
    ancho, alto = superficie.get_size()
    datos = pygame.image.tobytes(superficie, "RGB")
    for y in range(0, alto, paso):
        fila = y * ancho * 3
        for x in range(0, ancho, paso):
            i = fila + x * 3
            yield datos[i], datos[i + 1], datos[i + 2]


def panoramica():
    from src.dungeon.partida import Partida
    from src.ui import ciudad_render
    return ciudad_render.render_panoramico(Partida())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--imagen", default=None)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1280, 720))
    superficie = pygame.image.load(args.imagen) if args.imagen else panoramica()
    resultado = medir(pixeles(superficie))
    print(f"Píxeles de neón saturado: {100 * resultado['fraccion_saturada']:.1f} %"
          f" (tope {100 * MAX_FRACCION_SATURADA_CIUDAD:.0f} %)")
    print(f"Familias dominantes ({len(resultado['dominantes'])}, tope {MAX_FAMILIAS_DOMINANTES_CIUDAD}):",
          ", ".join(f"{n} {100 * resultado['familias'][n]:.0f} %" for n in resultado["dominantes"]))
    otras = sorted(((f, n) for n, f in resultado["familias"].items() if n not in resultado["dominantes"]), reverse=True)
    print("Resto:", ", ".join(f"{n} {100 * f:.1f} %" for f, n in otras))


if __name__ == "__main__":
    main()
