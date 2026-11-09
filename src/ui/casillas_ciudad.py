"""Pixel art de Ciudad Nova dibujado en código (solo presentación).

Mismo mecanismo que src/ui/sprites.py: cada casilla es una lista de 16
filas de 16 caracteres y cada carácter un color de la paleta; se
convierte con `sprites.sprite`, que la escala por ESCALA_PIXEL y la
cachea. Las casillas que comparten fondo (farola sobre acera, árbol
sobre pasto) se arman "estampando" una figura con '.' transparentes
sobre las filas del fondo, así siguen siendo filas de caracteres.

Las fachadas de los edificios de zona se generan con el mismo formato
(una grilla de ancho*16 x alto*16 caracteres) según el tamaño del
edificio, con ventanas, puerta, placa del rótulo y un emblema por zona.
"""

import pygame

from src.core import assets
from src.ui import sprites

LADO = 16  # caracteres por lado de casilla


def _estampar(fondo, figura):
    """Filas de `fondo` con los caracteres no '.' de `figura` encima."""
    return [
        "".join(f if f != "." else b for b, f in zip(fila_fondo, fila_figura))
        for fila_fondo, fila_figura in zip(fondo, figura)
    ]


def _baldosas():
    """Acera / plaza: adoquines de 8x8 con junta y un borde de brillo."""
    filas = []
    for y in range(LADO):
        fila = ""
        for x in range(LADO):
            if y % 8 == 0 or x % 8 == 0:
                fila += "j"
            elif y % 8 == 1 or x % 8 == 1:
                fila += "l"
            else:
                fila += "a"
        filas.append(fila)
    return filas


PASTO = [
    "gggggggggggggggg",
    "ggggggggghgggggg",
    "gggggggghgghgggg",
    "gghggggggggggggg",
    "ghghgggggggggsgg",
    "gggggggggggggggg",
    "gggggggggggggggg",
    "ggggggsggggggggg",
    "gggggggggghggggg",
    "ggggggggghghgggg",
    "gggggggggggggggg",
    "gghggggggggggggg",
    "ghgghggggggsgggg",
    "gggggggggggggggg",
    "ggggggggggggghgg",
    "gggggggggggghghg",
]
PALETA_PASTO = {"g": assets.COLOR_PASTO, "h": assets.COLOR_PASTO_BROTE, "s": assets.COLOR_PASTO_SOMBRA}

ACERA = _baldosas()
PALETA_ACERA = {"a": assets.COLOR_ACERA, "j": assets.COLOR_ACERA_JUNTA, "l": assets.COLOR_ACERA_BRILLO}

# Baldosa de la Plaza: losa grande con un rombo al centro.
PLAZA = [
    "jjjjjjjjjjjjjjjj",
    "jbbbbbbbbbbbbbbb",
    "jbbbbbbrrbbbbbbb",
    "jbbbbbrrrrbbbbbb",
    "jbbbbrrbbrrbbbbb",
    "jbbbrrbbbbrrbbbb",
    "jbbrrbbbbbbrrbbb",
    "jbrrbbbbbbbbrrbb",
    "jbrrbbbbbbbbrrbb",
    "jbbrrbbbbbbrrbbb",
    "jbbbrrbbbbrrbbbb",
    "jbbbbrrbbrrbbbbb",
    "jbbbbbrrrrbbbbbb",
    "jbbbbbbrrbbbbbbb",
    "jbbbbbbbbbbbbbbb",
    "jbbbbbbbbbbbbbbb",
]
PALETA_PLAZA = {"b": assets.COLOR_PLAZA, "r": assets.COLOR_PLAZA_ROMBO, "j": assets.COLOR_PLAZA_JUNTA}

CALLE = [
    "kkkkkkkkkkkkkkkk",
    "kkkkkkkkkkkskkkk",
    "kkskkkkkkkkkkkkk",
    "kkkkkkkkkkkkkkkk",
    "kkkkkkkskkkkkkkk",
    "kkkkkkkkkkkkkksk",
    "kkkkkkkkkkkkkkkk",
    "kkkskkkkkkkkkkkk",
    "kkkkkkkkkkkkkkkk",
    "kkkkkkkkkskkkkkk",
    "kskkkkkkkkkkkkkk",
    "kkkkkkkkkkkkkkkk",
    "kkkkkkskkkkkkskk",
    "kkkkkkkkkkkkkkkk",
    "kkkkkkkkkkkkkkkk",
    "kkkskkkkkkskkkkk",
]
PALETA_CALLE = {"k": assets.COLOR_ASFALTO, "s": assets.COLOR_ASFALTO_GRANO, "y": assets.COLOR_CARRIL}

# Marca de carril: un trazo centrado por casilla (al repetirse, discontinua).
CALLE_HORIZONTAL = _estampar(CALLE, ["." * LADO] * 7 + ["...yyyyyyyyyy..."] * 2 + ["." * LADO] * 7)
CALLE_VERTICAL = _estampar(CALLE, ["." * LADO] * 3 + [".......yy......."] * 10 + ["." * LADO] * 3)

ARBOL = _estampar(PASTO, [
    ".....dddddd.....",
    "...ddhhhhhhdd...",
    "..dhhhhhhhhhhd..",
    ".dhhhllhhhhhhhd.",
    ".dhhllhhhhhhhhd.",
    "dhhhlhhhhhhhhhhd",
    "dhhhhhhhhhhhhmhd",
    "dhhhhhhhhhhhmmhd",
    "dhhhhhhhhhhhhhhd",
    ".dhhhhhhhhhmmhd.",
    ".dhhhhhhhhmmhhd.",
    "..ddhhhhhhhhdd..",
    "...sddddddddds..",
    "....ssstttsss...",
    ".......tt.......",
    "......sttss.....",
])
PALETA_ARBOL = {**PALETA_PASTO, "d": assets.COLOR_COPA_BORDE, "h": assets.COLOR_COPA,
                "l": assets.COLOR_COPA_BRILLO, "m": assets.COLOR_COPA_SOMBRA,
                "t": assets.COLOR_TRONCO, "s": assets.COLOR_SOMBRA_SUELO}

FAROLA = _estampar(ACERA, [
    "......oooo......",
    ".....owwwwo.....",
    ".....owwwwo.....",
    "......oooo......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    ".......pq.......",
    "......ppqq......",
    ".....ppppqq.....",
    ".....ssssss.....",
    "................",
])
PALETA_FAROLA = {**PALETA_ACERA, "o": assets.COLOR_POSTE_OSCURO, "w": assets.COLOR_LAMPARA,
                 "p": assets.COLOR_POSTE, "q": assets.COLOR_POSTE_OSCURO, "s": assets.COLOR_ACERA_JUNTA}

# Casa decorativa: muro con dos filas de ventanas; la casilla de arriba
# de cada bloque lleva techo.
CASA_MURO = [
    "mmmmmmmmmmmmmmmm",
    "mmkkkkkmmkkkkkmm",
    "mmkuuukmmkvvvkmm",
    "mmkuuukmmkvvvkmm",
    "mmkuuukmmkvvvkmm",
    "mmkkkkkmmkkkkkmm",
    "mmmmmmmmmmmmmmmm",
    "jjjjjjjjjjjjjjjj",
    "mmmmmmmmmmmmmmmm",
    "mmkkkkkmmkkkkkmm",
    "mmkvvvkmmkuuukmm",
    "mmkvvvkmmkuuukmm",
    "mmkvvvkmmkuuukmm",
    "mmkkkkkmmkkkkkmm",
    "mmmmmmmmmmmmmmmm",
    "jjjjjjjjjjjjjjjj",
]
CASA_TECHO = [
    "RRRRRRRRRRRRRRRR",
    "RRRRRRRRRRRRRRRR",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
    "mmmmmmmmmmmmmmmm",
    "mmmmmmmmmmmmmmmm",
    "jjjjjjjjjjjjjjjj",
]
_PALETA_CASA_BASE = {"m": assets.COLOR_MURO_CASA, "j": assets.COLOR_MURO_CASA_JUNTA,
                     "k": assets.COLOR_MARCO_VENTANA, "R": assets.COLOR_TECHO_CASA_BRILLO,
                     "r": assets.COLOR_TECHO_CASA, "q": assets.COLOR_TECHO_CASA_LINEA,
                     "e": assets.COLOR_ALERO}
# Tres combinaciones de ventanas (u, v): se elige una por casilla.
PALETAS_CASA = [
    {**_PALETA_CASA_BASE, "u": assets.COLOR_VENTANA_ENCENDIDA, "v": assets.COLOR_VENTANA_APAGADA},
    {**_PALETA_CASA_BASE, "u": assets.COLOR_VENTANA_APAGADA, "v": assets.COLOR_VENTANA_APAGADA},
    {**_PALETA_CASA_BASE, "u": assets.COLOR_VENTANA_APAGADA, "v": assets.COLOR_VENTANA_NEON},
]

# Barricada (16x16, fondo transparente): tablón con franjas y dos patas.
BARRICADA = [
    "................",
    "................",
    "................",
    "kkkkkkkkkkkkkkkk",
    "kaabbaabbaabbaak",
    "kabbaabbaabbaabk",
    "kbbaabbaabbaabbk",
    "kbaabbaabbaabbak",
    "kkkkkkkkkkkkkkkk",
    "..pp........pp..",
    "..pp........pp..",
    "..pp........pp..",
    ".pppp......pppp.",
    "................",
    "................",
    "................",
]
PALETA_BARRICADA = {"k": assets.COLOR_BARRICADA_B, "a": assets.COLOR_BARRICADA_A,
                    "b": assets.COLOR_BARRICADA_B, "p": assets.COLOR_PATA_BARRICADA}


def casilla_pasto():
    return sprites.sprite(PASTO, PALETA_PASTO)


def casilla_acera():
    return sprites.sprite(ACERA, PALETA_ACERA)


def casilla_plaza():
    return sprites.sprite(PLAZA, PALETA_PLAZA)


def casilla_calle(marca=None):
    """marca: None, "horizontal" o "vertical"."""
    filas = {None: CALLE, "horizontal": CALLE_HORIZONTAL, "vertical": CALLE_VERTICAL}[marca]
    return sprites.sprite(filas, PALETA_CALLE)


def casilla_arbol():
    return sprites.sprite(ARBOL, PALETA_ARBOL)


def casilla_farola():
    return sprites.sprite(FAROLA, PALETA_FAROLA)


def casilla_casa(con_techo, variante):
    return sprites.sprite(CASA_TECHO if con_techo else CASA_MURO, PALETAS_CASA[variante % len(PALETAS_CASA)])


def casilla_barricada():
    return sprites.sprite(BARRICADA, PALETA_BARRICADA)


_mosaico = {}


def mosaico_plaza():
    """Anillos concéntricos del centro de la Plaza, dibujados a la
    resolución del pixel art y escalados (bordes en escalera, no lisos)."""
    if "mosaico" not in _mosaico:
        radio_max = assets.ANILLOS_MOSAICO_PLAZA[0][0] * LADO
        lado = round(radio_max * 2) + 2
        base = pygame.Surface((lado, lado), pygame.SRCALPHA)
        for radio, color in assets.ANILLOS_MOSAICO_PLAZA:
            pygame.draw.circle(base, color, (lado // 2, lado // 2), round(radio * LADO))
        _mosaico["mosaico"] = pygame.transform.scale_by(base, assets.ESCALA_PIXEL)
    return _mosaico["mosaico"]


# ----------------------------------------------------------------------
# Fachadas de los edificios de zona
# ----------------------------------------------------------------------

_fachadas = {}


def _oscurecer(color, factor):
    return tuple(round(c * factor) for c in color)


class _Lienzo:
    """Grilla de caracteres para componer una fachada."""

    def __init__(self, ancho, alto, relleno):
        self.celdas = [[relleno] * ancho for _ in range(alto)]

    def rect(self, x, y, ancho, alto, caracter):
        for fila in range(max(0, y), min(len(self.celdas), y + alto)):
            for col in range(max(0, x), min(len(self.celdas[0]), x + ancho)):
                self.celdas[fila][col] = caracter

    def punto(self, x, y, caracter):
        self.rect(x, y, 1, 1, caracter)

    def filas(self):
        return ["".join(fila) for fila in self.celdas]


def filas_fachada(zona, ancho, alto, columna_puerta):
    """Filas de caracteres de la fachada de `zona`: `ancho` x `alto`
    casillas, con la puerta en la casilla `columna_puerta` (relativa) de
    la última fila. Techo en la primera fila, ventanas en las del medio,
    placa del rótulo justo encima de la puerta."""
    w, h = ancho * LADO, alto * LADO
    lienzo = _Lienzo(w, h, "w")
    # Techo con tejas, alero y hiladas del muro.
    lienzo.rect(0, 0, w, LADO, "r")
    lienzo.rect(0, 0, w, 2, "R")
    for y in (5, 9):
        lienzo.rect(0, y, w, 1, "q")
    lienzo.rect(0, LADO - 3, w, 3, "e")
    for y in range(LADO + 7, h, 8):
        lienzo.rect(0, y, w, 1, "d")
    # Ventanas: una por casilla bajo el techo, salvo detrás de la placa
    # del rótulo y junto a la puerta.
    x_placa, _, ancho_placa, _ = placa_rotulo(ancho, alto, columna_puerta)
    for fila in range(1, alto):
        for col in range(ancho):
            x, y = col * LADO + 4, fila * LADO + 3
            if fila == alto - 2 and x + 8 > x_placa and x < x_placa + ancho_placa:
                continue
            if fila == alto - 1 and abs(col - columna_puerta) <= 1:
                continue
            lienzo.rect(x, y, 8, 9, "k")
            vidrio = "yno"[(col * 7 + fila * 3) % 5 % 3]
            lienzo.rect(x + 1, y + 1, 6, 7, vidrio)
            if vidrio != "o":
                lienzo.rect(x + 1, y + 1, 2, 2, "l")
    # Base del edificio y puerta.
    lienzo.rect(0, h - 3, w, 3, "b")
    px = columna_puerta * LADO
    lienzo.rect(px + 2, h - LADO, 12, LADO, "k")
    lienzo.rect(px + 3, h - LADO + 1, 10, LADO - 1, "p")
    lienzo.rect(px + 8, h - LADO + 1, 1, LADO - 1, "k")
    lienzo.punto(px + 6, h - 8, "n")
    lienzo.punto(px + 10, h - 8, "n")
    # Placa del rótulo, centrada sobre la puerta (el texto lo pone el render).
    x0, y0, ancho_placa, alto_placa = placa_rotulo(ancho, alto, columna_puerta)
    lienzo.rect(x0, y0, ancho_placa, alto_placa, "n")
    lienzo.rect(x0 + 1, y0 + 1, ancho_placa - 2, alto_placa - 2, "k")
    _emblema(lienzo, zona, w, h, px)
    return lienzo.filas()


def placa_rotulo(ancho, alto, columna_puerta):
    """(x, y, ancho, alto) de la placa del rótulo en píxeles de arte
    dentro de la fachada (multiplicar por ESCALA_PIXEL para pantalla)."""
    w, h = ancho * LADO, alto * LADO
    placa = assets.ANCHO_ROTULO_CASILLAS * LADO
    centro_puerta = columna_puerta * LADO + LADO // 2
    x0 = max(2, min(w - placa - 2, centro_puerta - placa // 2))
    return (x0, h - 2 * LADO + 2, placa, 12)


def _emblema(lienzo, zona, w, h, px):
    """Un detalle reconocible por zona, en el techo o junto a la puerta."""
    cx = w // 2
    if zona == "Hospital":
        lienzo.rect(cx - 2, 2, 5, 11, "n")
        lienzo.rect(cx - 5, 5, 11, 5, "n")
    elif zona == "Colegio":
        lienzo.rect(cx - 5, 1, 11, 12, "k")
        lienzo.rect(cx - 4, 2, 9, 10, "y")
        lienzo.rect(cx, 3, 1, 5, "k")
        lienzo.rect(cx, 7, 3, 1, "k")
    elif zona == "Empresa de Medios":
        lienzo.rect(cx - 6, 3, 9, 7, "n")
        lienzo.rect(cx - 5, 4, 7, 5, "k")
        lienzo.rect(cx - 2, 6, 1, 1, "n")
        lienzo.rect(cx + 4, 0, 1, 13, "c")
        lienzo.rect(cx + 3, 0, 3, 2, "n")
    elif zona == "Alcaldía":
        lienzo.rect(cx - 1, 0, 1, 12, "c")
        lienzo.rect(cx, 0, 7, 5, "n")
        for x in (px - 10, px - 4, px + LADO + 2, px + LADO + 8):
            lienzo.rect(x, h - 2 * LADO + 14, 3, 2 * LADO - 17, "c")


def fachada(zona, ancho, alto, columna_puerta, escala=assets.ESCALA_PIXEL):
    """Surface de la fachada de `zona` en pixel art (16 px por casilla) a
    `escala` entera (cacheada por zona, tamaño y escala)."""
    clave = (zona, ancho, alto, columna_puerta, escala)
    if clave not in _fachadas:
        neon = assets.COLORES_NEON_ZONA[zona]
        paleta = {
            "w": assets.COLOR_MURO_EDIFICIO, "d": assets.COLOR_MURO_EDIFICIO_LINEA,
            "R": assets.COLOR_TECHO_CASA_BRILLO, "r": assets.COLOR_TECHO_CASA,
            "q": assets.COLOR_TECHO_CASA_LINEA, "e": assets.COLOR_ALERO,
            "k": assets.COLOR_MARCO_VENTANA, "y": assets.COLOR_VENTANA_ENCENDIDA,
            "o": assets.COLOR_VENTANA_APAGADA, "n": neon, "l": (255, 255, 255),
            "p": _oscurecer(neon, assets.FACTOR_PUERTA_OSCURA), "b": assets.COLOR_BASE_EDIFICIO,
            "c": assets.COLOR_COLUMNA,
        }
        # sprites.sprite cachea por id(filas): las filas se guardan aquí
        # junto con la Surface para que no se recolecten.
        filas = filas_fachada(zona, ancho, alto, columna_puerta)
        _fachadas[clave] = (filas, sprites.sprite(filas, paleta, escala))
    return _fachadas[clave][1]
