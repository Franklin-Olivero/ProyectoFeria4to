"""Viste los cuartos de mazmorra con el arte generado (solo presentación).

Cada tema (Colegio, Hospital, Medios, Alcaldía/Servidor) tiene en
assets/mazmorras/<carpeta>/ su piso repetible, la franja frontal de su
muro y sus objetos (props/), generados con Higgsfield y reducidos a pixel
art con tools/procesar_higgsfield.py. Este módulo:

    disponible(tema)          -> ¿hay arte para el tema? (sin él, se pinta como siempre)
    variante(tema, semilla)   -> qué tipo de cuarto es (aula, biblioteca, urgencias...)
    vestir(fondo, cuarto, ...) -> multiplica el piso, pone el muro y coloca los
        objetos (plan puro en src/ui/plan_decor.py). Devuelve los focos que
        brillan (pantallas, LEDs) para `dibujar_focos`.
    dibujar_focos(pantalla, focos, tiempo) -> el halo que late sobre esos objetos.

Nada de esto toca colisiones, puertas ni tamaños: los objetos son fondo,
quedan junto a los muros y el centro del cuarto queda libre para combatir.
"""

import math
import random

import pygame

from src.core import assets
from src.ui import arte_colegio, cargador_assets, plan_decor

ALTO_CARA_MURO_PX = 36  # la misma banda que temas_mazmorra.ALTO_CARA_MURO * P
NIVELES_HALO = 8
_halos = {}  # (w, h, color, nivel) -> Surface


def disponible(tema):
    if tema == "colegio":
        return arte_colegio.disponible()
    return cargador_assets.pieza_mazmorra(tema, "piso") is not None


def variante(tema, semilla):
    opciones = assets.VARIANTES_CUARTO.get(tema, ())
    return opciones[semilla % len(opciones)] if opciones else None


def vestir(fondo, cuarto, tema, semilla, libres, direcciones, banda):
    """Viste `fondo` (px de la Surface del mundo). `cuarto`: el cuarto en esos
    px; `libres`: rects que no se pueden tapar (puertas y centro).
    Devuelve [(rect en px de `fondo`, color)] de los objetos que brillan."""
    cara = pygame.Rect(cuarto.left, cuarto.top, cuarto.width, ALTO_CARA_MURO_PX)
    piso = pygame.Rect(cuarto.left, cara.bottom, cuarto.width, cuarto.height - ALTO_CARA_MURO_PX)
    tipo = variante(tema, semilla)
    if tema == "colegio":
        if tipo == "aula":
            return []  # el aula del pack ya la viste arte_colegio.vestir_aula
        arte_colegio.multiplicar_piso(fondo, piso)
    else:
        _multiplicar_piso(fondo, piso, tema)
        _poner_muro(fondo, cara, tema, direcciones)

    reglas = assets.DECORADO_VARIANTE.get((tema, tipo), ())
    imagenes = {}
    for _, objetos, _ in reglas:
        for nombre in objetos:
            if nombre not in imagenes:
                imagen = _imagen(tema, nombre)
                if imagen is not None:
                    imagenes[nombre] = imagen
    tamanos = {nombre: imagen.get_size() for nombre, imagen in imagenes.items()}
    rng = random.Random(f"decor-{tema}-{semilla}")
    # La terminal del cuarto final y su rótulo van junto al muro derecho, a media
    # altura: esa zona queda libre en todos los cuartos (el fondo se cachea sin
    # saber si el cuarto es el final).
    ancho_t, alto_t = assets.ZONA_LIBRE_TERMINAL
    terminal = pygame.Rect(cuarto.right - ancho_t, cuarto.centery - alto_t // 2, ancho_t, alto_t)
    libres = [tuple(r) for r in libres] + [tuple(terminal)]
    plan = plan_decor.planificar(reglas, tamanos, tuple(piso), libres, banda, rng, assets.SEPARACION_PROPS)
    focos = []
    # Por la base: lo de más abajo tapa a lo de más arriba (perspectiva 3/4).
    for nombre, rect in sorted(plan, key=lambda e: e[1][1] + e[1][3]):
        rect = pygame.Rect(rect)
        _sombra(fondo, rect)
        fondo.blit(imagenes[nombre], rect)
        clave = nombre.split(":")[-1]
        if clave in assets.FOCO_PROP:
            focos.append((rect, assets.FOCO_PROP[clave]))
    return focos


def _imagen(tema, nombre):
    if nombre.startswith("pack:"):
        return cargador_assets.pieza_colegio(nombre[5:], assets.FACTOR_MUEBLES_COLEGIO)
    return cargador_assets.pieza_mazmorra(tema, nombre, factor=assets.FACTOR_PROPS_TEMA.get(tema, 1.0))


def _multiplicar_piso(fondo, piso, tema):
    """La textura se multiplica sobre el piso pintado (luz, viñeta y grietas
    de NOVA siguen visibles a través de ella)."""
    baldosa = cargador_assets.pieza_mazmorra(tema, "piso")
    if baldosa is None:
        return
    textura = pygame.Surface(piso.size)
    for y in range(0, piso.height, baldosa.get_height()):
        for x in range(0, piso.width, baldosa.get_width()):
            textura.blit(baldosa, (x, y))
    fondo.subsurface(piso).blit(textura, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def _poner_muro(fondo, cara, tema, direcciones):
    """Franja del muro repetida en la cara, sin tapar el vano de la puerta norte."""
    franja = cargador_assets.pieza_mazmorra(tema, "muro", escala=assets.ESCALA_MURO_MAZMORRA)
    if franja is None:
        return
    capa = pygame.Surface(cara.size)
    for x in range(0, cara.width, franja.get_width()):
        capa.blit(franja, (x, cara.height - franja.get_height()))
    capa.fill(assets.TINTE_MURO_TEMA.get(tema, (255, 255, 255)), special_flags=pygame.BLEND_RGB_MULT)
    huecos = []
    if "N" in direcciones:
        # El mismo vano que pinta temas_mazmorra._hueco_puertas (puerta + marco).
        ancho = (assets.ANCHO_PUERTA // 3 + 6) * 3
        huecos.append(pygame.Rect(cara.centerx - ancho // 2, cara.top, ancho, cara.height))
    recorte = fondo.get_clip()
    for x0, x1 in _tramos(cara.left, cara.right, huecos):
        fondo.set_clip(pygame.Rect(x0, cara.top, x1 - x0, cara.height))
        fondo.blit(capa, cara)
    fondo.set_clip(recorte)
    # Sombra donde el muro toca el piso, como la del pintor.
    sombra = pygame.Surface((cara.width, 6), pygame.SRCALPHA)
    for i in range(6):
        pygame.draw.line(sombra, (0, 0, 16, 120 - i * 20), (0, i), (cara.width, i))
    fondo.blit(sombra, (cara.left, cara.bottom))


def _tramos(izquierda, derecha, huecos):
    tramos, x = [], izquierda
    for hueco in sorted(huecos, key=lambda r: r.left):
        if hueco.left > x:
            tramos.append((x, hueco.left))
        x = max(x, hueco.right)
    if x < derecha:
        tramos.append((x, derecha))
    return tramos


def _sombra(fondo, rect):
    alto = max(6, rect.height // 7)
    sombra = pygame.Surface((round(rect.width * 0.9), alto), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, assets.COLOR_SOMBRA_PROP, sombra.get_rect())
    fondo.blit(sombra, sombra.get_rect(center=(rect.centerx, rect.bottom - alto // 3)))


# ----------------------------------------------------------------------
# Lo que brilla
# ----------------------------------------------------------------------

def dibujar_focos(pantalla, focos, tiempo, origen_y):
    """Halo que late sobre cada pantalla o LED. Los halos se precalculan en
    NIVELES_HALO intensidades: cada frame son unos pocos blits aditivos."""
    for rect, color in focos:
        fase = 0.5 + 0.5 * math.sin(tiempo * 2.4 + rect.x * 0.037)
        nivel = min(NIVELES_HALO - 1, int(fase * NIVELES_HALO))
        halo = _halo(rect.width, rect.height, color, nivel)
        destino = halo.get_rect(center=(rect.centerx, rect.top + origen_y + rect.height // 3))
        pantalla.blit(halo, destino, special_flags=pygame.BLEND_RGB_ADD)


def _halo(ancho, alto, color, nivel):
    clave = (ancho, alto, color, nivel)
    if clave not in _halos:
        radio = max(ancho, alto) // 2 + 10
        capa = pygame.Surface((radio * 2, radio * 2))
        fuerza = assets.ALFA_FOCO_MAXIMO * (nivel + 1) / NIVELES_HALO
        for r in range(radio, 0, -2):
            t = 1 - r / radio
            pygame.draw.circle(capa, tuple(round(k * fuerza / 255 * t * t) for k in color), (radio, radio), r)
        _halos[clave] = capa
    return _halos[clave]
