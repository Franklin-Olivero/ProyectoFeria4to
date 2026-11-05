"""Prueba corta con ventana y audio REALES, a tiempo real (unos 25 s).

Abre el juego de verdad, recorre menú, intro con su video, ciudad y un cuarto, y
reporta los FPS reales y si el mezclador está sonando. La ventana toma el foco del
teclado: no escribas en otra aplicación mientras corre.

    python tools/prueba_ventana.py [carpeta_capturas]
"""

import os
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools"))
os.chdir(RAIZ)

import recorrido_campania as rc  # noqa: E402

marcas = {}


def medir(c, nombre, frames):
    inicio = time.perf_counter()
    yield frames
    marcas[nombre] = frames / (time.perf_counter() - inicio)


def guion(c, _):
    import pygame
    pg = c.pygame
    yield from medir(c, "menú", 120)
    c.captura("ventana_menu")
    c.tecla(pg.K_RETURN)
    yield 20
    c.tecla(pg.K_1)
    yield 30
    c.tecla(pg.K_RIGHT, pg.K_RIGHT)
    yield 5
    c.tecla(pg.K_RETURN)
    while c.locales() is None:
        yield 1
    yield from medir(c, "intro con video", 240)
    c.captura("ventana_intro_video")
    print("música sonando en la intro:", pygame.mixer.get_busy(), "| canales:", pygame.mixer.get_num_channels(), flush=True)
    while c.locales()["dialogo"] is not None:
        c.tecla(pg.K_ESCAPE)
        yield 8
        c.tecla(pg.K_RETURN)
        yield 8
    yield from medir(c, "Ciudad Nova", 120)
    c.captura("ventana_ciudad")
    from src.dungeon import ciudad_mapa
    col, fila = ciudad_mapa.ENTRADAS["Hospital"]
    x, y = ciudad_mapa.centro_casilla(col, fila)
    c.locales()["jugador"].colocar_en((x, y + 8))
    yield 3
    c.tecla(pg.K_e)
    yield 10
    while c.locales()["dialogo"] is not None:
        c.tecla(pg.K_ESCAPE)
        yield 8
    yield from medir(c, "mazmorra Hospital", 240)
    c.captura("ventana_hospital")
    print("música sonando en combate:", pygame.mixer.get_busy(), flush=True)
    raise rc.FinDelGuion


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else None
    rc.ejecutar(guion=guion, carpeta=carpeta, ventana=True, tiempo_real=True)
    print("Driver de video: real. FPS medidos:")
    for nombre, fps in marcas.items():
        print(f"  {nombre:22s} {fps:5.1f}")
