"""Arte real del Colegio (solo presentación): su fachada en Ciudad Nova y
el aula de su mazmorra, con el "Traditional School Asset pack"
(assets/colegio/, piezas en assets.PIEZAS_COLEGIO).

    fachada(...)    -> el Colegio entero (techo, dos pisos de pared con
        ventanas, puerta) a la resolución del pack y con escala entera,
        del tamaño exacto de su huella (assets.ARTE_EDIFICIOS).
    plan_aula(cara, piso, ...) -> dónde va cada mueble del aula: pizarra y
        reloj en la cara del muro, pupitres en filas, escritorio del
        profesor, casilleros, estantes y macetas, siempre fuera de las
        zonas libres (puertas y centro). Los dibuja decor_mazmorra (lo
        chico, horneado) y cobertura_render (los muebles, que son
        coberturas rompibles: src/dungeon/coberturas.py).
    multiplicar_piso(fondo, piso) -> tablones de madera multiplicados sobre
        el piso pintado (así conserva su luz, su viñeta y las grietas de
        NOVA según la toxicidad).

Si falta el pack, `disponible()` es False y el Colegio se pinta como siempre.
"""

import os
import random

import pygame

from src.core import assets
from src.ui import cargador_assets

ALTO_CARA_MURO_PX = 36  # la misma banda que temas_mazmorra.ALTO_CARA_MURO * P
# Pupitres del aula (48x58 px a escala 1.5; su base sólida mide 40x35).
COLUMNAS_PUPITRES = 2
PASO_PUPITRES = 124  # px entre columnas: 84 de pasillo
FILAS_PUPITRES = (158, 270, 382)  # px desde el borde superior del piso: 77 entre bases


def disponible():
    return all(os.path.exists(os.path.join(assets.RUTA_COLEGIO, archivo))
               for archivo, _ in assets.PIEZAS_COLEGIO.values())


# ----------------------------------------------------------------------
# Fachada en la ciudad
# ----------------------------------------------------------------------

def fachada(ancho, alto, columna_puerta, rect_placa, escala, tam_casilla):
    """Surface del Colegio para su huella de `ancho` x `alto` casillas,
    armada a la resolución nativa del pack y escalada por `escala` entera
    (vecino más cercano): mide exactamente ancho*tam_casilla x alto*tam_casilla.

    Techo arriba, dos pisos de pared crema (ventanas arriba; abajo, pared
    lisa detrás de la placa del rótulo y la puerta) y la puerta en la
    casilla `columna_puerta` de la fila de abajo. `rect_placa` va en px
    de pantalla dentro de la fachada. None si falta el pack."""
    ventana = cargador_assets.pieza_colegio("muro_ventana", assets.FACTOR_FACHADA_COLEGIO)
    liso = cargador_assets.pieza_colegio("muro_liso", assets.FACTOR_FACHADA_COLEGIO)
    alta = cargador_assets.pieza_colegio("muro_ventana_alta", assets.FACTOR_FACHADA_COLEGIO)
    if ventana is None or liso is None or alta is None:
        return None
    ancho_n, alto_n = ancho * tam_casilla // escala, alto * tam_casilla // escala
    lienzo = pygame.Surface((ancho_n, alto_n))
    lado = ventana.get_width()  # 64: dos tejas del pack
    techo = alto_n - 2 * lado
    # Techo plano con su alero de madera.
    lienzo.fill(assets.COLOR_TECHO_COLEGIO)
    pygame.draw.rect(lienzo, assets.COLOR_MARCO_PUERTA_COLEGIO, (0, techo - 3, ancho_n, 3))
    pygame.draw.line(lienzo, _aclarar(assets.COLOR_TECHO_COLEGIO, 18), (0, 1), (ancho_n, 1))
    # Dos pisos de pared, centrados (las piezas de los bordes se recortan igual a cada lado).
    columnas = -(-ancho_n // lado) + 1
    inicio = (ancho_n - columnas * lado) // 2
    placa = pygame.Rect(rect_placa)
    placa = pygame.Rect(placa.x // escala, placa.y // escala, -(-placa.w // escala), -(-placa.h // escala))
    centro_puerta = (columna_puerta * tam_casilla + tam_casilla // 2) // escala
    puerta = pygame.Rect(0, 0, tam_casilla // escala, tam_casilla // escala)
    puerta.midbottom = (centro_puerta, alto_n)
    for piso in range(2):
        y = techo + piso * lado
        for i in range(columnas):
            destino = pygame.Rect(inicio + i * lado, y, lado, lado)
            if piso == 1 and (destino.colliderect(placa.inflate(4, 4)) or destino.colliderect(puerta)):
                pieza = liso
            else:
                pieza = (ventana, alta)[i % 2]
            lienzo.blit(pieza, destino)
    # Puerta con marco de madera y vidrio oscuro (la casilla 'E' del mapa).
    pygame.draw.rect(lienzo, assets.COLOR_MARCO_PUERTA_COLEGIO, puerta)
    pygame.draw.rect(lienzo, assets.COLOR_PUERTA_COLEGIO, puerta.inflate(-4, -3).move(0, 2))
    pygame.draw.line(lienzo, assets.COLOR_MARCO_PUERTA_COLEGIO, (puerta.centerx, puerta.top + 2),
                     (puerta.centerx, puerta.bottom))
    return pygame.transform.scale(lienzo, (ancho_n * escala, alto_n * escala))


def _aclarar(color, d):
    return tuple(min(255, c + d) for c in color)


# ----------------------------------------------------------------------
# Aula de la mazmorra
# ----------------------------------------------------------------------

def plan_aula(cara, piso, semilla, libres):
    """[(nombre, rect)] del aula: pizarra y reloj en la cara del muro,
    escritorio del profesor y estantes al fondo, casilleros a los costados,
    pupitres en dos bloques con pasillos anchos (son coberturas: entre
    filas y columnas cabe cualquier enemigo) y macetas en las esquinas.
    `cara` y `piso`: pygame.Rect en px de la Surface del mundo; `libres`:
    rects que no se pueden tapar. Los nombres son "pack:<pieza>"."""
    rng = random.Random(f"aula-{semilla}")
    ocupados = [pygame.Rect(r) for r in libres]
    colocados = []

    def poner(nombre, x, y, en_piso=True):
        escala = assets.ESCALA_MUEBLES_COLEGIO if en_piso else 1
        pieza = cargador_assets.pieza_colegio(nombre, assets.FACTOR_MUEBLES_COLEGIO, escala)
        if pieza is None:
            return False
        destino = pieza.get_rect(topleft=(round(x), round(y)))
        zona = piso if en_piso else cara
        if not zona.contains(destino) or any(destino.inflate(6, 6).colliderect(o) for o in ocupados):
            return False
        ocupados.append(destino)
        colocados.append((f"pack:{nombre}", tuple(destino)))
        return True

    # En la cara del muro: pizarra a la izquierda, reloj al centro-derecha.
    poner("pizarra", cara.left + 70, cara.top + 2, en_piso=False)
    poner("reloj", cara.centerx + 120, cara.top + 6, en_piso=False)
    # Escritorio del profesor y estantes junto al muro del fondo.
    poner("escritorio", piso.left + 190, piso.top + 6)
    poner("estante", piso.right - 78, piso.top + 4)
    poner("estante", piso.right - 156, piso.top + 4)
    # Casilleros a los costados.
    for y in range(piso.top + 172, piso.bottom - 110, 170):
        poner("casillero", piso.left + 6, y)
        poner("casillero", piso.right - 51, y)
    # Pupitres: dos columnas por lado y hasta cuatro filas (algunos faltan:
    # el aula quedó a medias). Los pasos entre ellos miden 72 px o más.
    for columna in range(COLUMNAS_PUPITRES):
        for fila, y in enumerate(FILAS_PUPITRES):
            for x in (piso.left + 150 + columna * PASO_PUPITRES, piso.right - 198 - columna * PASO_PUPITRES):
                if rng.random() < 0.18:
                    continue
                poner("pupitre", x, piso.top + y)
    # Macetas en las esquinas de abajo.
    poner("maceta", piso.left + 8, piso.bottom - 70)
    poner("maceta", piso.right - 53, piso.bottom - 70)
    return colocados


def multiplicar_piso(fondo, piso):
    """Tablones del pack sobre el piso (también para la biblioteca y el laboratorio)."""
    _multiplicar_piso(fondo, piso)


def _multiplicar_piso(fondo, piso):
    """Tablones del pack multiplicados sobre el piso pintado (luz, viñeta y
    grietas quedan visibles a través de la textura)."""
    tablon = cargador_assets.pieza_colegio("piso")
    if tablon is None:
        return
    textura = pygame.Surface(piso.size)
    for y in range(0, piso.height, tablon.get_height()):
        for x in range(0, piso.width, tablon.get_width()):
            textura.blit(tablon, (x, y))
    region = fondo.subsurface(piso)
    region.blit(textura, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
