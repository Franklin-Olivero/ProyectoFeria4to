"""Viste los cuartos de mazmorra con el arte generado (solo presentación).

Cada tema (Colegio, Hospital, Medios, Alcaldía/Servidor) tiene en
assets/mazmorras/<carpeta>/ su piso repetible, la franja frontal de su
muro y sus objetos (props/), generados con Higgsfield y reducidos a pixel
art con tools/procesar_higgsfield.py. Este módulo:

    disponible(tema)          -> ¿hay arte para el tema? (sin él, se pinta como siempre)
    variante(tema, semilla)   -> qué tipo de cuarto es (aula, biblioteca, urgencias...)
    plan(...)                 -> [(nombre, rect, solido, base)]: dónde va cada objeto
        (plan puro en src/ui/plan_decor.py; el aula, en arte_colegio.plan_aula).
        Los sólidos son las coberturas rompibles del cuarto
        (src/dungeon/coberturas.py): los crea la lógica con este mismo plan.
    imagen(tema, nombre)      -> la imagen de un objeto del plan
    vestir(fondo, cuarto, ...) -> multiplica el piso, pone el muro y hornea en
        el fondo SOLO los objetos sin hitbox (libros, mochilas, pizarra...).
        Los sólidos los dibuja src/ui/cobertura_render.py cada frame, porque
        se agrietan, se rompen y se ordenan por Y con los personajes.
    dibujar_focos(pantalla, focos, tiempo) -> el halo que late sobre pantallas y LEDs.
"""

import math
import random

import pygame

from src.core import assets
from src.core.balance import HUECO_CERRADO_COBERTURA, PASO_MINIMO_COBERTURA
from src.dungeon.coberturas import es_solido
from src.ui import arte_colegio, cargador_assets, plan_decor

ALTO_CARA_MURO_PX = 36  # la misma banda que temas_mazmorra.ALTO_CARA_MURO * P
NIVELES_HALO = 8
_halos = {}  # (w, h, color, nivel) -> Surface
_planes = {}  # clave del cuarto -> plan


def disponible(tema):
    if tema == "colegio":
        return arte_colegio.disponible()
    return cargador_assets.pieza_mazmorra(tema, "piso") is not None


def variante(tema, semilla):
    opciones = assets.VARIANTES_CUARTO.get(tema, ())
    return opciones[semilla % len(opciones)] if opciones else None


def _zonas(cuarto):
    cara = pygame.Rect(cuarto.left, cuarto.top, cuarto.width, ALTO_CARA_MURO_PX)
    piso = pygame.Rect(cuarto.left, cara.bottom, cuarto.width, cuarto.height - ALTO_CARA_MURO_PX)
    return cara, piso


def plan(tema, semilla, cuarto, libres, banda, con_terminal=True):
    """[(nombre, (x, y, w, h), solido, base)] de los objetos del cuarto, en px
    de la Surface del mundo (`base` = la hitbox del objeto si es sólido). `cuarto`: el cuarto en esos px; `libres`: rects que
    no se pueden tapar (puertas y centro). `con_terminal`: reserva además el
    lugar de la terminal (solo el cuarto final la tiene). Guardado: el
    fondo y la lógica piden el mismo plan."""
    cuarto = pygame.Rect(cuarto)
    clave = (tema, semilla, tuple(cuarto), tuple(tuple(r) for r in libres), banda, con_terminal)
    if clave not in _planes:
        if len(_planes) > 64:
            _planes.clear()
        _planes[clave] = _armar_plan(tema, semilla, cuarto, libres, banda, con_terminal)
    return _planes[clave]


def _armar_plan(tema, semilla, cuarto, libres, banda, con_terminal):
    cara, piso = _zonas(cuarto)
    libres = [tuple(r) for r in libres]
    if con_terminal:
        # La terminal del cuarto final y su rótulo van junto al muro derecho, a media altura.
        ancho_t, alto_t = assets.ZONA_LIBRE_TERMINAL
        libres.append((cuarto.right - ancho_t, cuarto.centery - alto_t // 2, ancho_t, alto_t))
    tipo = variante(tema, semilla)
    if tema == "colegio" and tipo == "aula":
        colocados = arte_colegio.plan_aula(cara, piso, semilla, libres)
    else:
        reglas = assets.DECORADO_VARIANTE.get((tema, tipo), ())
        tamanos = {}
        for _, objetos, _ in reglas:
            for nombre in objetos:
                if nombre not in tamanos:
                    figura = imagen(tema, nombre)
                    if figura is not None:
                        tamanos[nombre] = figura.get_size()
        rng = random.Random(f"decor-{tema}-{semilla}")
        colocados = plan_decor.planificar(reglas, tamanos, tuple(piso), libres, banda, rng,
                                          assets.SEPARACION_PROPS, PASO_MINIMO_COBERTURA,
                                          cerrado=HUECO_CERRADO_COBERTURA)
    # Cada sólido lleva su base (la hitbox de su cobertura), con la misma
    # cuenta que usó el planificador para dejar los pasos.
    return [(nombre, rect, _solido(nombre), plan_decor.base(rect, tuple(piso)))
            for nombre, rect in colocados]


def _solido(nombre):
    return es_solido(nombre) and nombre.split(":")[-1] not in assets.PIEZAS_COLEGIO_DE_MURO


def vestir(fondo, cuarto, tema, semilla, objetos, direcciones):
    """Viste `fondo` (px de la Surface del mundo): piso, muro y los objetos
    sin hitbox de `objetos` (el plan del cuarto). Devuelve [(rect, color)] de
    los horneados que brillan."""
    cara, piso = _zonas(cuarto)
    if tema == "colegio":
        arte_colegio.multiplicar_piso(fondo, piso)
    else:
        _multiplicar_piso(fondo, piso, tema)
        _poner_muro(fondo, cara, tema, direcciones)
    focos = []
    # Por la base: lo de más abajo tapa a lo de más arriba (perspectiva 3/4).
    for nombre, rect, solido, _ in sorted(objetos, key=lambda e: e[1][1] + e[1][3]):
        figura = imagen(tema, nombre)
        if solido or figura is None:
            continue
        rect = pygame.Rect(rect)
        if piso.contains(rect):
            _sombra(fondo, rect)
        fondo.blit(figura, rect)
        if foco_de(nombre) is not None:
            focos.append((rect, foco_de(nombre)))
    return focos


def foco_de(nombre):
    """Color del halo del objeto si brilla (pantallas, LEDs), o None."""
    return assets.FOCO_PROP.get(nombre.split(":")[-1])


def imagen(tema, nombre):
    """Imagen del objeto `nombre` del tema ("pack:<pieza>" = pack escolar), o None."""
    if nombre.startswith("pack:"):
        pieza = nombre[5:]
        escala = 1 if pieza in assets.PIEZAS_COLEGIO_DE_MURO else assets.ESCALA_MUEBLES_COLEGIO
        return cargador_assets.pieza_colegio(pieza, assets.FACTOR_MUEBLES_COLEGIO, escala)
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


def sombra(rect):
    """(Surface, rect destino) de la sombra elíptica bajo un objeto."""
    alto = max(6, rect.height // 7)
    clave = ("sombra", rect.width, alto)
    if clave not in _halos:
        figura = pygame.Surface((round(rect.width * 0.9), alto), pygame.SRCALPHA)
        pygame.draw.ellipse(figura, assets.COLOR_SOMBRA_PROP, figura.get_rect())
        _halos[clave] = figura
    figura = _halos[clave]
    return figura, figura.get_rect(center=(rect.centerx, rect.bottom - alto // 3))


def _sombra(fondo, rect):
    fondo.blit(*sombra(rect))


# ----------------------------------------------------------------------
# Lo que brilla
# ----------------------------------------------------------------------

def dibujar_focos(pantalla, focos, tiempo, origen_y):
    """Halo que late sobre cada pantalla o LED. Los halos se precalculan en
    NIVELES_HALO intensidades: cada frame son unos pocos blits aditivos."""
    for rect, color in focos:
        rect = pygame.Rect(rect)
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
