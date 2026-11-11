"""Capturas de los escenarios de mazmorra: varios cuartos por zona y la arena del jefe.

    python tools/capturas_mazmorras.py                      # -> docs/capturas/mazmorras/
    python tools/capturas_mazmorras.py --salida otra/carpeta

Sin ventana (SDL dummy). Cada captura dibuja el cuarto real (Cuarto.dibujar)
con su toxicidad, sus puertas, sus enemigos y un jugador en el centro, para
juzgar legibilidad y no solo el fondo. Guarda <tema>_<n>.png y jefe.png.
"""

import argparse
import os
import random
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ZONAS = (("Colegio", 72), ("Hospital", 48), ("Empresa de Medios", 30))
# Cada muestra: semilla visual y puertas, como cuartos distintos de una mazmorra.
MUESTRAS = ((1, ("N", "E", "S", "W")), (2, ("E", "W")), (3, ("N", "S")), (4, ("S",)))


def _jugador():
    import Main
    clase = Main.CLASES_ROL[0]
    jugador = clase(640, 360)
    return jugador


def capturar_cuarto(pantalla, zona, toxicidad, semilla, puertas, ruta):
    from src.dungeon.cuarto import Cuarto
    from src.ui import hud  # noqa: F401  (carga fuentes como en el juego)

    cuarto = Cuarto(nombre_zona=zona, direcciones_puertas=puertas, nivel_toxicidad=toxicidad,
                    es_final=semilla == 4, rng=random.Random(semilla), semilla_visual=semilla)
    jugador = _jugador()
    jugador.rect.center = cuarto.rect.center
    pantalla.fill((0, 0, 0))
    cuarto.dibujar(pantalla)
    jugador.dibujar(pantalla)
    pygame.image.save(pantalla, ruta)


def capturar_jefe(pantalla, ruta):
    from src.dungeon.arena_jefe import ArenaJefe
    jugador = _jugador()
    from src.core.colapso import ColapsoElectoral
    arena = ArenaJefe(ColapsoElectoral(), [jugador])
    pantalla.fill((0, 0, 0))
    arena.dibujar(pantalla)
    pygame.image.save(pantalla, ruta)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", default=os.path.join("docs", "capturas", "mazmorras"))
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    pygame.init()
    pantalla = pygame.display.set_mode((1280, 720))
    from src.core import assets
    for zona, toxicidad in ZONAS:
        tema = assets.TEMA_POR_ZONA[zona]
        for semilla, puertas in MUESTRAS:
            capturar_cuarto(pantalla, zona, toxicidad, semilla, puertas,
                            os.path.join(args.salida, f"{tema}_{semilla}.png"))
    capturar_jefe(pantalla, os.path.join(args.salida, "jefe.png"))
    print("Capturas en", args.salida)


if __name__ == "__main__":
    main()
