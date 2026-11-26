"""Hojas del jugador hechas desde el arte de Higgsfield (los 4 personajes del pendón).

Lee assets/sprites/retratos/<rol>.png (Higgsfield, 512 px de alto) y escribe,
para cada rol de assets.ROLES_APARIENCIA:

    assets/sprites/jugadores/<rol>.png          hoja de 4 cuadros (quieto,
                                                paso_a, paso_b, dash) de
                                                assets.ALTO_JUGADOR_HF px
    assets/sprites/jugadores/<rol>.atlas.json   atlas con las animaciones
                                                "caminar" y "dash"
    assets/sprites/jugadores/<rol>.partes.png   la misma hoja, pero cada
                                                píxel pintado con el color
                                                de su parte (piel, pelo,
                                                camisa, pantalón, zapatos;
                                                transparente = no se tiñe)
    assets/sprites/retratos/<rol>.partes.png    el mapa de partes del retrato
                                                en tamaño completo (para
                                                teñir al que posa en la
                                                selección de personaje)

Cómo se reduce: se recorta el personaje, se reduce con promedio a su alto
de juego y el alfa queda binario (sin bordes semitransparentes), así se ve
como pixel art del mismo dibujo. Cada parte se reconoce en el original de
512 px (color más cercano a sus referencias, solo dentro de sus zonas; el
contorno, los blancos y los accesorios no son de ninguna) y se reduce por
mayoría de votos. Los pasos mueven un pie un píxel hacia arriba.

Uso:  venv/bin/python tools/generar_jugadores_higgsfield.py [--vista carpeta]
"""

import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from src.core import assets  # noqa: E402

UMBRAL_COLOR = 70  # distancia RGB máxima a una referencia para contar como esa parte
ALFA_MINIMO = 110  # por debajo, el píxel reducido queda transparente
VOTOS_MINIMOS = 0.4  # fracción de píxeles del bloque que deben ser de la parte
ALTO_PIES = 0.16  # fracción de abajo que se mueve al dar un paso

# Lo que nunca es una parte: contorno y blancos (camiseta, cordones, aretes...).
NEUTROS = [(0, 0, 30), (16, 6, 40), (3, 1, 20), (8, 6, 40), (0, 0, 36), (2, 0, 39), (6, 3, 46), (9, 6, 67),
           (248, 248, 249), (250, 249, 250), (247, 246, 246)]

# Por rol y parte: (colores de referencia, zonas donde puede estar). Las
# zonas van en fracciones del recorte (x0, y0, x1, y1), 0 = arriba/izquierda.
PARTES = {
    "ciudadano": {
        "pelo": ([(59, 27, 50), (92, 46, 57), (33, 16, 47), (120, 70, 60), (75, 40, 55)], [(0, 0, 0.62, 0.46)]),
        "piel": ([(221, 140, 105), (144, 76, 68), (240, 170, 130), (190, 110, 90), (250, 190, 160)],
                 [(0.05, 0.12, 0.6, 0.52), (0.55, 0.47, 0.72, 0.62), (0.05, 0.62, 0.3, 0.8)]),
        "ropa": ([(0, 181, 172), (0, 140, 140), (80, 220, 210), (0, 110, 115), (40, 200, 190)], [(0, 0.44, 0.8, 0.8)]),
        "pantalon": ([(52, 94, 147), (128, 149, 185), (30, 60, 110), (90, 120, 170)], [(0.08, 0.66, 0.62, 0.93)]),
        "zapatos": ([(230, 60, 100), (250, 130, 160), (180, 40, 80), (240, 90, 120)], [(0, 0.88, 0.75, 1)]),
    },
    "influencer": {
        "pelo": ([(130, 85, 77), (97, 58, 62), (160, 110, 90), (70, 45, 55)], [(0, 0, 0.66, 0.43)]),
        "pelo_rubio": ([(232, 192, 140), (250, 222, 170), (212, 160, 112), (240, 205, 150)], [(0, 0, 0.66, 0.24)]),
        "piel": ([(246, 194, 152), (207, 139, 114), (230, 170, 140)], [(0.05, 0.2, 0.66, 0.56), (0.5, 0.5, 0.7, 0.62)]),
        "ropa": ([(248, 77, 157), (199, 40, 120), (255, 120, 190), (150, 30, 90), (225, 60, 140)], [(0, 0.45, 0.7, 0.82)]),
        "pantalon": ([(57, 48, 72), (40, 32, 60), (80, 70, 100), (34, 24, 52)], [(0.1, 0.76, 0.72, 0.92)]),
        "zapatos": ([(240, 90, 150), (250, 150, 190), (200, 50, 110)], [(0, 0.9, 0.72, 1)]),
    },
    "periodista": {
        # El pelo largo va a los lados de la cara: los lentes (negros) quedan fuera.
        "pelo": ([(52, 48, 74), (32, 27, 58), (99, 94, 126), (70, 66, 100)],
                 [(0, 0, 1, 0.3), (0, 0.3, 0.27, 0.62), (0.86, 0.3, 1, 0.62)]),
        "piel": ([(249, 197, 161), (224, 141, 115), (236, 170, 140)], [(0.1, 0.18, 0.95, 0.75)]),
        "ropa": ([(240, 236, 243), (196, 189, 221), (156, 136, 178), (220, 215, 235)], [(0, 0.47, 1, 0.92)]),
        "pantalon": ([(52, 48, 74), (32, 27, 58), (70, 66, 100)], [(0.25, 0.77, 0.72, 0.93)]),
        "zapatos": ([(60, 58, 80), (40, 40, 60), (99, 94, 126), (80, 78, 100)], [(0.15, 0.925, 0.75, 1)]),
    },
    "candidato": {
        "pelo": ([(90, 79, 95), (60, 49, 71), (170, 163, 171), (207, 202, 205), (130, 109, 119)], [(0, 0, 1, 0.33)]),
        "piel": ([(249, 199, 152), (220, 146, 114), (235, 175, 135)], [(0, 0.18, 1, 0.75)]),
        "ropa": ([(39, 44, 99), (30, 32, 77), (60, 70, 130), (22, 19, 59)], [(0, 0.5, 1, 0.79)]),
        "pantalon": ([(39, 44, 99), (30, 32, 77), (60, 70, 130), (22, 19, 59)], [(0.12, 0.79, 0.88, 0.93)]),
        "zapatos": ([(30, 30, 44), (70, 70, 90), (110, 110, 130), (50, 50, 66)], [(0.12, 0.925, 0.88, 1)]),
    },
}


def _d2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def etiquetar(imagen, partes):
    """[[parte o None]] del tamaño de `imagen` (el original recortado)."""
    ancho, alto = imagen.get_size()
    referencias = [(c, None, None) for c in NEUTROS]
    for nombre, (colores, zonas) in partes.items():
        referencias += [(c, nombre.split("_")[0], zonas) for c in colores]
    etiquetas = [[None] * ancho for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            pixel = imagen.get_at((x, y))
            if pixel.a < 128:
                continue
            fx, fy = x / ancho, y / alto
            mejor = None
            for color, parte, zonas in referencias:
                if zonas and not any(x0 <= fx <= x1 and y0 <= fy <= y1 for x0, y0, x1, y1 in zonas):
                    continue
                distancia = _d2(pixel, color)
                if mejor is None or distancia < mejor[0]:
                    mejor = (distancia, parte)
            if mejor and mejor[1] and mejor[0] <= UMBRAL_COLOR ** 2:
                etiquetas[y][x] = mejor[1]
    return etiquetas


def reducir(imagen, etiquetas, alto):
    """(Surface reducida con alfa binario, [[parte]] reducidas)."""
    ancho_original, alto_original = imagen.get_size()
    ancho = max(1, round(ancho_original * alto / alto_original))
    chica = pygame.transform.smoothscale(imagen, (ancho, alto))
    partes = [[None] * ancho for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            pixel = chica.get_at((x, y))
            opaco = pixel.a >= ALFA_MINIMO
            chica.set_at((x, y), (pixel.r, pixel.g, pixel.b, 255 if opaco else 0))
            if not opaco:
                continue
            votos, total = {}, 0
            for yy in range(y * alto_original // alto, max(y * alto_original // alto + 1, (y + 1) * alto_original // alto)):
                for xx in range(x * ancho_original // ancho,
                                max(x * ancho_original // ancho + 1, (x + 1) * ancho_original // ancho)):
                    if imagen.get_at((xx, yy)).a >= 128:
                        total += 1
                        parte = etiquetas[yy][xx]
                        if parte:
                            votos[parte] = votos.get(parte, 0) + 1
            if votos:
                parte, cuantos = max(votos.items(), key=lambda kv: kv[1])
                if cuantos >= VOTOS_MINIMOS * total:
                    partes[y][x] = parte
    return chica, partes


def _centro_pies(superficie):
    """x promedio de los píxeles opacos de la franja de los pies."""
    ancho, alto = superficie.get_size()
    xs = [x for y in range(int(alto * (1 - ALTO_PIES)), alto) for x in range(ancho) if superficie.get_at((x, y)).a]
    return sum(xs) / len(xs) if xs else ancho / 2


def _paso(superficie, centro, lado):
    """Copia con el pie de `lado` ("izquierdo"/"derecho") un píxel más arriba."""
    ancho, alto = superficie.get_size()
    copia = superficie.copy()
    desde = int(alto * (1 - ALTO_PIES))
    for x in range(ancho):
        if (x < centro) != (lado == "izquierdo"):
            continue
        for y in range(desde, alto):
            copia.set_at((x, y), superficie.get_at((x, y + 1)) if y + 1 < alto else (0, 0, 0, 0))
    return copia


def _mapa(etiquetas, tamanio, desplazamiento=(0, 0)):
    """Surface de `tamanio` con cada parte pintada de su color."""
    mapa = pygame.Surface(tamanio, pygame.SRCALPHA)
    dx, dy = desplazamiento
    for y, fila in enumerate(etiquetas):
        for x, parte in enumerate(fila):
            if parte:
                mapa.set_at((x + dx, y + dy), assets.COLOR_PARTE_JUGADOR[parte])
    return mapa


def hojas_de_rol(rol):
    """(hoja, hoja_de_partes, ancho_cuadro, nombres, mapa del retrato) del rol."""
    retrato = pygame.image.load(os.path.join(assets.RUTA_SPRITES_RETRATOS, f"{rol}.png")).convert_alpha()
    recorte = retrato.get_bounding_rect(min_alpha=128)
    original = retrato.subsurface(recorte).copy()
    etiquetas = etiquetar(original, PARTES[rol])
    mapa_retrato = _mapa(etiquetas, retrato.get_size(), recorte.topleft)
    chica, partes = reducir(original, etiquetas, assets.ALTO_JUGADOR_HF)
    mapa = _mapa(partes, chica.get_size())
    # Cuadro centrado en los pies: así el personaje queda sobre su hitbox
    # aunque lleve el cartel o el aro de luz a un lado.
    centro = _centro_pies(chica)
    mitad = int(max(centro, chica.get_width() - centro) + 1)
    ancho = 2 * mitad
    dx = round(mitad - centro)
    cuadros = {"quieto": None, "paso_a": "izquierdo", "paso_b": "derecho", "dash": "izquierdo"}
    hoja = pygame.Surface((ancho * len(cuadros), assets.ALTO_JUGADOR_HF), pygame.SRCALPHA)
    hoja_partes = hoja.copy()
    for i, lado in enumerate(cuadros.values()):
        for origen, destino in ((chica, hoja), (mapa, hoja_partes)):
            cuadro = origen if lado is None else _paso(origen, centro, lado)
            destino.blit(cuadro, (i * ancho + dx, 0))
    return hoja, hoja_partes, ancho, list(cuadros), mapa_retrato


def atlas(rol, ancho, nombres):
    alto = assets.ALTO_JUGADOR_HF
    duraciones = {"quieto": 150, "paso_a": 150, "paso_b": 150, "dash": 120}
    return {
        "frames": {nombre: {"frame": {"x": i * ancho, "y": 0, "w": ancho, "h": alto}, "rotated": False,
                            "trimmed": False, "spriteSourceSize": {"x": 0, "y": 0, "w": ancho, "h": alto},
                            "sourceSize": {"w": ancho, "h": alto}, "duration": duraciones[nombre]}
                   for i, nombre in enumerate(nombres)},
        "animations": {
            assets.ANIMACION_CAMINAR: {"frames": ["quieto", "paso_a", "quieto", "paso_b"], "loop": True,
                                       "duration": 600},
            assets.ANIMACION_DASH: {"frames": ["dash"], "loop": False, "duration": 120},
        },
        "meta": {"app": "Higgsfield + tools/generar_jugadores_higgsfield.py", "version": "1", "image": f"{rol}.png",
                 "format": "RGBA8888", "size": {"w": ancho * len(nombres), "h": alto}, "scale": "1"},
    }


def main():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    for rol in assets.ROLES_APARIENCIA:
        hoja, hoja_partes, ancho, nombres, mapa_retrato = hojas_de_rol(rol)
        pygame.image.save(mapa_retrato, os.path.join(assets.RUTA_SPRITES_RETRATOS, f"{rol}.partes.png"))
        carpeta = assets.RUTA_SPRITES_JUGADORES
        pygame.image.save(hoja, os.path.join(carpeta, f"{rol}.png"))
        pygame.image.save(hoja_partes, os.path.join(carpeta, f"{rol}.partes.png"))
        with open(os.path.join(carpeta, f"{rol}.atlas.json"), "w", encoding="utf-8") as archivo:
            json.dump(atlas(rol, ancho, nombres), archivo, indent=2)
        print(rol, hoja.get_size(), "cuadro", ancho, "x", assets.ALTO_JUGADOR_HF)


if __name__ == "__main__":
    main()
