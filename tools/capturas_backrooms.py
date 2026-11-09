"""Capturas del lobby del hotel y de una muestra por grade empaquetado.

    python tools/capturas_backrooms.py                 # -> docs/capturas/backrooms/
    python tools/capturas_backrooms.py --salida otra/carpeta

Sin ventana (SDL dummy). Guarda:
    lobby_1j.png, lobby_2j.png   el lobby con 1 y 2 jugadores (uno confirmado)
    grade_<grade>.png            cada tile y prop del atlas de ese grade a ×3
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


def capturar_lobby(pantalla, jugadores, ruta):
    import Main
    from src.ui import escena_lobby_render, hud
    from src.ui.seleccion import SeleccionRoles
    from src.ui.seleccion_rol import VistaSeleccion

    seleccion = SeleccionRoles(jugadores, len(Main.CLASES_ROL))
    seleccion.cursores[0].indice = 1
    if jugadores > 1:
        seleccion.cursores[1].indice = 3
        seleccion.cursores[1].confirmar()
    vista = VistaSeleccion(len(Main.CLASES_ROL), escena_lobby_render.crear(), Main._tablero_mazmorras())
    for _ in range(90):
        vista.actualizar(1 / 60, seleccion)
    vista.dibujar(pantalla, Main.CLASES_ROL, seleccion, 80, False)
    hud.dibujar_barra_controles(pantalla, hud.CONTROLES_SELECCION_DOS if jugadores > 1 else hud.CONTROLES_SELECCION)
    pygame.image.save(pantalla, ruta)


def capturar_grade(grade, ruta):
    """Muestra del atlas del grade: todos sus tiles en fila y luego sus props, a ×3."""
    from src.core import assets
    from src.ui import cargador_backrooms

    atlas = cargador_backrooms.atlas(grade)
    escala = assets.ESCALA_BACKROOMS
    piezas = [cargador_backrooms.tile(grade, int(i), escala) for i in sorted(atlas["tiles"], key=int)]
    piezas += [cargador_backrooms.prop(grade, "", n, escala) for n in sorted(atlas["props"])]
    piezas += [cargador_backrooms.light_pool(grade, n, escala) for n in sorted(atlas["luces"])]
    ancho, margen = 1280, 8
    x = y = margen
    alto_fila = 0
    posiciones = []
    for pieza in piezas:
        if x + pieza.get_width() > ancho - margen:
            x, y, alto_fila = margen, y + alto_fila + margen, 0
        posiciones.append((pieza, (x, y)))
        x += pieza.get_width() + margen
        alto_fila = max(alto_fila, pieza.get_height())
    lienzo = pygame.Surface((ancho, y + alto_fila + margen))
    lienzo.fill((24, 20, 30))
    for pieza, pos in posiciones:
        lienzo.blit(pieza, pos)
    pygame.image.save(lienzo, ruta)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", default=os.path.join("docs", "capturas", "backrooms"))
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    pygame.init()
    pantalla = pygame.display.set_mode((1280, 720))
    from src.ui import rutas_backrooms
    capturar_lobby(pantalla, 1, os.path.join(args.salida, "lobby_1j.png"))
    capturar_lobby(pantalla, 2, os.path.join(args.salida, "lobby_2j.png"))
    for grade in rutas_backrooms.grades_disponibles():
        capturar_grade(grade, os.path.join(args.salida, f"grade_{grade}.png"))
    print("capturas en", args.salida)


if __name__ == "__main__":
    main()
