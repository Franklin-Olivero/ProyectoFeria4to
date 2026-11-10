"""Casas de Ciudad Nova: los edificios secundarios (solo dibujo).

Cada casa de ciudad_mapa.CASAS es un sprite completo: se pinta una vez en pixel art (16 px por
casilla) con su plantilla de assets.ESTILOS_CASA: color del muro y sus
hiladas, techo (tejas, mansarda con buhardillas, plano con pretil o
terraza con plantas), patrón de ventanas (dobles, verticales, en banda o
muro cortina) y planta baja con puerta y escalón (o vitrinas con toldo si
es una tienda). Se escala a ESCALA_PIXEL (vecino más cercano) y mide
exactamente su huella. Encima se apoyan piezas del pack urbano (toldo,
aire acondicionado, macetas) pedidas por src/ui/arte_ciudad.py.

    imagen(indice)                  -> Surface de la casa (cacheada)
    rect(indice)                    -> dónde va en el mundo (px)
    dibujar_ventanas(pantalla, ...) -> solo las ventanas que parpadean, cada frame

La lógica (ventanas, parpadeo, vecinas) está en src/dungeon/casas_ciudad.py.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import casas_ciudad, ciudad_mapa
from src.ui import arte_ciudad

ESCALA = assets.ESCALA_PIXEL
LADO = casas_ciudad.LADO
_cache = {}


def _oscuro(color, factor):
    return tuple(max(0, min(255, round(c * factor))) for c in color)


def rect(indice):
    col, fila, ancho, alto = ciudad_mapa.CASAS[indice][0]
    return pygame.Rect(col * TAM_CASILLA, fila * TAM_CASILLA, ancho * TAM_CASILLA, alto * TAM_CASILLA)


def _techo(lienzo, estilo, w):
    techo, color = estilo["techo"], estilo["color_techo"]
    alto = casas_ciudad.alto_techo(techo)
    if techo == "tejas":
        lienzo.fill(color, (0, 0, w, alto))
        for y in range(2, alto - 2, 3):
            lienzo.fill(_oscuro(color, 0.75), (0, y, w, 1))
        lienzo.fill(_oscuro(color, 1.35), (0, 0, w, 1))
        lienzo.fill(_oscuro(color, 0.5), (0, alto - 2, w, 2))  # alero
    elif techo == "mansarda":
        lienzo.fill(color, (0, 0, w, alto))
        for x in range(0, w, 4):
            lienzo.fill(_oscuro(color, 0.8), (x, 0, 1, alto))
        for x in range(LADO // 2 - 3, w - 6, LADO * 2):  # buhardillas
            lienzo.fill(_oscuro(color, 1.4), (x - 1, 2, 8, 8))
            lienzo.fill(assets.COLOR_VIDRIO_CASA, (x + 1, 4, 4, 5))
        lienzo.fill(_oscuro(color, 0.5), (0, alto - 1, w, 1))
    elif techo == "plano":
        lienzo.fill(color, (0, 0, w, alto))
        lienzo.fill(_oscuro(color, 1.3), (0, 0, w, 1))
    elif techo == "terraza":
        lienzo.fill(color, (0, 0, w, alto))
        for x in range(1, w - 2, 5):
            lienzo.fill(_oscuro(color, 1.35), (x, 1, 3, 2))
        lienzo.fill(_oscuro(estilo["muro"], 0.6), (0, alto - 1, w, 1))


def _muro(lienzo, estilo, w, h, y0):
    lienzo.fill(estilo["muro"], (0, y0, w, h - y0))
    for y in range(y0 + 5, h, 6):
        lienzo.fill(estilo["junta"], (0, y, w, 1))
    if estilo["techo"] == "tejas" and estilo["muro"][0] > estilo["muro"][2]:  # ladrillo: juntas verticales trabadas
        for i, y in enumerate(range(y0, h - 1, 6)):
            for x in range(3 * (i % 2), w, 6):
                lienzo.fill(estilo["junta"], (x, y, 1, 5))


def _ventana(lienzo, x, y, w, h, color):
    lienzo.fill(assets.COLOR_MARCO_CASA, (x - 1, y - 1, w + 2, h + 2))
    lienzo.fill(color, (x, y, w, h))
    if color != assets.COLOR_VIDRIO_CASA:
        lienzo.fill(_oscuro(color, 1.15), (x, y, max(1, w // 2), 1))


def _base(indice):
    """Fachada en px nativos (sin escalar), con las ventanas quietas pintadas."""
    (col, fila, ancho, alto), nombre = ciudad_mapa.CASAS[indice]
    estilo = assets.ESTILOS_CASA[nombre]
    w, h = ancho * LADO, alto * LADO
    lienzo = pygame.Surface((w, h))
    alto_techo = casas_ciudad.alto_techo(estilo["techo"])
    _muro(lienzo, estilo, w, h, alto_techo)
    _techo(lienzo, estilo, w)
    semilla = casas_ciudad.semilla((col, fila, ancho, alto))
    luz = casas_ciudad.color_ventana(semilla)
    for i, (x, y, vw, vh) in enumerate(casas_ciudad.ventanas(ancho, alto, estilo["ventanas"], estilo["techo"])):
        prendida = casas_ciudad.encendida(semilla, i) and not casas_ciudad.parpadea(semilla, i)
        _ventana(lienzo, x, y, vw, vh, luz if prendida else assets.COLOR_VIDRIO_CASA)
    # Planta baja: zócalo, puerta con escalón y vitrinas a los lados.
    lienzo.fill(_oscuro(estilo["muro"], 0.7), (0, h - 3, w, 3))
    for x, y, vw, vh in casas_ciudad.vitrinas(ancho, alto):
        _ventana(lienzo, x, y, vw, vh, luz if estilo["toldo"] else assets.COLOR_VIDRIO_CASA)
    px, py, pw, ph = casas_ciudad.puerta(ancho, alto)
    lienzo.fill(assets.COLOR_MARCO_CASA, (px - 1, py - 1, pw + 2, ph + 1))
    lienzo.fill(assets.COLOR_PUERTA_CASA, (px, py, pw, ph))
    lienzo.fill(luz, (px + pw - 2, py + ph // 2, 1, 1))  # pomo
    lienzo.fill(assets.COLOR_ESCALON_CASA, (px - 2, h - 2, pw + 4, 2))
    return lienzo, estilo


def imagen(indice):
    if indice not in _cache:
        lienzo, estilo = _base(indice)
        figura = pygame.transform.scale(lienzo, (lienzo.get_width() * ESCALA, lienzo.get_height() * ESCALA))
        (_, _, ancho, alto), _ = ciudad_mapa.CASAS[indice]
        _piezas_del_pack(figura, estilo, ancho, alto)
        _cache[indice] = figura
    return _cache[indice]


def _piezas_del_pack(figura, estilo, ancho, alto):
    """Toldo sobre las vitrinas de las tiendas, aire acondicionado en el pretil
    y macetas en las terrazas (piezas del pack urbano; sin PNG, nada)."""
    w, h = figura.get_size()
    if estilo["toldo"]:
        toldo = arte_ciudad.imagen("urbano:toldo")
        if toldo is not None:
            for x, _, vw, _ in casas_ciudad.vitrinas(ancho, alto):
                pieza = pygame.transform.scale(toldo, (vw * ESCALA + 6, toldo.get_height() * (vw * ESCALA + 6) // toldo.get_width()))
                figura.blit(pieza, pieza.get_rect(midbottom=((x + vw / 2) * ESCALA, h - 12 * ESCALA)))
    if estilo["techo"] == "plano":
        aire = arte_ciudad.imagen("urbano:aire_acondicionado")
        if aire is not None:
            pieza = pygame.transform.scale_by(aire, 0.6)
            figura.blit(pieza, pieza.get_rect(topright=(w - 6, casas_ciudad.alto_techo("plano") * ESCALA + 4)))
    if estilo["techo"] == "terraza":
        maceta = arte_ciudad.imagen("urbano:maceta_planta")
        if maceta is not None:
            pieza = pygame.transform.scale_by(maceta, 0.5)
            for x in range(LADO * ESCALA // 2, w, LADO * ESCALA * 2):
                figura.blit(pieza, pieza.get_rect(midbottom=(x, casas_ciudad.alto_techo("terraza") * ESCALA + 2)))


def dibujar_todas(superficie, desplazamiento=(0, 0)):
    for indice in range(len(ciudad_mapa.CASAS)):
        figura = imagen(indice)
        destino = figura.get_rect(**{assets.ANCLA_EDIFICIOS: getattr(rect(indice), assets.ANCLA_EDIFICIOS)})
        superficie.blit(figura, destino.move(desplazamiento))


def dibujar_ventanas(pantalla, rect_mundo, dx, dy, tiempo):
    """Las ventanas que parpadean, prendidas o apagadas según `tiempo`."""
    for indice, ((col, fila, ancho, alto), nombre) in enumerate(ciudad_mapa.CASAS):
        casa = rect(indice)
        if not casa.colliderect(rect_mundo):
            continue
        estilo = assets.ESTILOS_CASA[nombre]
        semilla = casas_ciudad.semilla((col, fila, ancho, alto))
        luz = casas_ciudad.color_ventana(semilla)
        for i, (x, y, w, h) in enumerate(casas_ciudad.ventanas(ancho, alto, estilo["ventanas"], estilo["techo"])):
            if casas_ciudad.parpadea(semilla, i):
                color = luz if casas_ciudad.encendida(semilla, i, tiempo) else assets.COLOR_VIDRIO_CASA
                pantalla.fill(color, (casa.x + x * ESCALA + dx, casa.y + y * ESCALA + dy, w * ESCALA, h * ESCALA))
