"""Arte real del Colegio (solo presentación): su fachada en Ciudad Nova y
el aula de su mazmorra, con el "Traditional School Asset pack"
(assets/colegio/, piezas en assets.PIEZAS_COLEGIO).

    vestir_fachada(fachada, ...)  -> pared crema con ventanas en los pisos
        altos de la fachada pintada en código; el techo con el emblema y la
        planta baja (placa del rótulo y puerta) quedan como estaban.
    vestir_aula(fondo, rect, ...) -> tablones de madera multiplicados sobre
        el piso pintado (así conserva su luz, su viñeta y las grietas de
        NOVA según la toxicidad), pizarra y reloj en la cara del muro,
        pupitres en filas, escritorio del profesor, casilleros, estantes y
        macetas, siempre fuera de las zonas libres (puertas y centro).

Nada de esto toca colisiones: los muebles son fondo, como antes. Si falta
el pack, `disponible()` es False y el Colegio se pinta como siempre.
"""

import os
import random

import pygame

from src.core import assets
from src.ui import cargador_assets

ALTO_CARA_MURO_PX = 36  # la misma banda que temas_mazmorra.ALTO_CARA_MURO * P


def disponible():
    return all(os.path.exists(os.path.join(assets.RUTA_COLEGIO, archivo))
               for archivo, _ in assets.PIEZAS_COLEGIO.values())


# ----------------------------------------------------------------------
# Fachada en la ciudad
# ----------------------------------------------------------------------

def vestir_fachada(fachada, ancho, alto, columna_puerta, rect_placa):
    """Copia de `fachada` (Surface) con la pared del pack en los pisos
    altos. `ancho`/`alto` en casillas, `rect_placa` en px de pantalla
    dentro de la fachada (nunca se tapa)."""
    ventana = cargador_assets.pieza_colegio("muro_ventana", assets.FACTOR_FACHADA_COLEGIO)
    liso = cargador_assets.pieza_colegio("muro_liso", assets.FACTOR_FACHADA_COLEGIO)
    alta = cargador_assets.pieza_colegio("muro_ventana_alta", assets.FACTOR_FACHADA_COLEGIO)
    if ventana is None or liso is None or alta is None:
        return fachada
    resultado = fachada.copy()
    lado = fachada.get_width() // ancho
    lado_pieza = ventana.get_width()
    arriba = lado  # bajo la fila del techo
    abajo = (alto - 2) * lado  # la planta baja (placa y puerta) queda como está
    columnas = fachada.get_width() // lado_pieza
    margen = (fachada.get_width() - columnas * lado_pieza) // 2
    placa = pygame.Rect(rect_placa).inflate(8, 8)
    for fila, y in enumerate(range(arriba, abajo - lado_pieza + 1, lado_pieza)):
        for col in range(columnas):
            destino = pygame.Rect(margen + col * lado_pieza, y, lado_pieza, lado_pieza)
            if destino.colliderect(placa):
                continue
            pieza = (ventana, alta, ventana, liso)[(col + fila) % 4]
            resultado.blit(pieza, destino)
    return resultado


# ----------------------------------------------------------------------
# Aula de la mazmorra
# ----------------------------------------------------------------------

def vestir_aula(fondo, rect, origen_y, semilla, libres):
    """Viste `fondo` (la Surface del mundo del cuarto, ya escalada) en
    el lugar. `rect`: el cuarto en px de pantalla; `origen_y`: dónde
    empieza `fondo` en pantalla; `libres`: rects (px de `fondo`) que no
    se pueden tapar."""
    rng = random.Random(f"aula-{semilla}")
    cuarto = pygame.Rect(rect.left, rect.top - origen_y, rect.width, rect.height)
    cara = pygame.Rect(cuarto.left, cuarto.top, cuarto.width, ALTO_CARA_MURO_PX)
    piso = pygame.Rect(cuarto.left, cara.bottom, cuarto.width, cuarto.height - ALTO_CARA_MURO_PX)
    _multiplicar_piso(fondo, piso)
    ocupados = [pygame.Rect(r) for r in libres]

    def poner(nombre, x, y, en_piso=True):
        pieza = cargador_assets.pieza_colegio(nombre, assets.FACTOR_MUEBLES_COLEGIO)
        if pieza is None:
            return False
        destino = pieza.get_rect(topleft=(round(x), round(y)))
        zona = piso if en_piso else cara
        if not zona.contains(destino) or any(destino.inflate(6, 6).colliderect(o) for o in ocupados):
            return False
        fondo.blit(pieza, destino)
        ocupados.append(destino)
        return True

    # En la cara del muro: pizarra a la izquierda, reloj al centro-derecha.
    poner("pizarra", cara.left + 70, cara.top + 2, en_piso=False)
    poner("reloj", cara.centerx + 120, cara.top + 6, en_piso=False)
    # Escritorio del profesor y estantes junto al muro del fondo.
    poner("escritorio", piso.left + 150, piso.top + 6)
    poner("estante", piso.right - 60, piso.top + 4)
    poner("estante", piso.right - 112, piso.top + 4)
    # Casilleros a los costados.
    for y in range(piso.top + 110, piso.bottom - 80, 84):
        poner("casillero", piso.left + 6, y)
        poner("casillero", piso.right - 36, y)
    # Pupitres en filas a los dos lados del centro (algunos faltan: el aula quedó a medias).
    for columna in range(3):
        for fila in range(4):
            for x in (piso.left + 60 + columna * 54, piso.right - 92 - columna * 54):
                if rng.random() < 0.15:
                    continue
                y = piso.top + 100 + fila * 76
                if poner("pupitre", x, y) and rng.random() < 0.25:
                    poner("mochila", x + 30, y + 22)
    # Macetas en las esquinas de abajo.
    poner("maceta", piso.left + 8, piso.bottom - 50)
    poner("maceta", piso.right - 40, piso.bottom - 50)


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
