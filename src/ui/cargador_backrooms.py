"""Cargador del arte Backrooms (solo presentación).

    disponible(grade)                  -> True si el grade está empaquetado
    tile(grade, id, escala)            -> Surface 16x16 * escala
    prop(grade, zona, nombre, escala)  -> Surface del prop (su borde inferior toca el suelo)
    animacion(grade, nombre, escala)   -> [(Surface, ms)] cuadros de la animación, o None
    light_pool(grade, nombre, escala)  -> Surface del halo de luz
    tiene_prop / tiene_animacion       -> consultas sin aviso

Lee cada atlas y cada hoja una vez y cachea cada pieza por (grade,
clase, nombre, escala); escala entera, vecino más cercano. Si algo falta,
tile/prop/light_pool devuelven un damero magenta del tamaño esperado (se
ve que falta, pero el juego sigue) y avisan UNA vez por asset; animacion
devuelve None para que quien la pide use la versión quieta. Las rutas y
rects salen de src/ui/rutas_backrooms.py (puro).
"""

import sys

import pygame

from src.core import assets
from src.ui import rutas_backrooms as rutas

_atlas = {}  # grade -> dict o None
_hojas = {}  # (grade, tipo) -> Surface o None
_piezas = {}  # (grade, clase, nombre, escala) -> Surface / lista
_avisados = set()


def limpiar_cache():
    _atlas.clear()
    _hojas.clear()
    _piezas.clear()
    _avisados.clear()


def _avisar(grade, clase, nombre):
    clave = (grade, clase, nombre)
    if clave not in _avisados:
        _avisados.add(clave)
        print(f"[backrooms] falta {clase} {nombre!r} en el grade {grade!r} "
              f"(¿tools/empaquetar_backrooms.py?)", file=sys.stderr)


def avisos():
    """Assets que faltaron (para pruebas y para el humo headless)."""
    return set(_avisados)


def atlas(grade):
    if grade not in _atlas:
        _atlas[grade] = rutas.leer_atlas(grade) if rutas.es_grade(grade) else None
    return _atlas[grade]


def disponible(grade):
    """True si el grade tiene atlas y todas sus hojas en disco."""
    datos = atlas(grade)
    if datos is None:
        return False
    return all(_hoja(grade, tipo) is not None for tipo, entradas in datos.items()
               if tipo in assets.HOJAS_BACKROOMS and entradas)


def _hoja(grade, tipo):
    clave = (grade, tipo)
    if clave not in _hojas:
        imagen = None
        try:
            imagen = pygame.image.load(rutas.ruta_hoja(grade, tipo))
            if pygame.display.get_surface() is not None:
                imagen = imagen.convert_alpha()
        except (pygame.error, FileNotFoundError, ValueError):
            imagen = None
        _hojas[clave] = imagen
    return _hojas[clave]


def _recortar(grade, tipo, rect, escala):
    hoja = _hoja(grade, tipo)
    if hoja is None or rect is None or not hoja.get_rect().contains(pygame.Rect(rect)):
        return None
    pieza = hoja.subsurface(rect).copy()
    if escala != 1:
        pieza = pygame.transform.scale(pieza, (pieza.get_width() * escala, pieza.get_height() * escala))
    return pieza


def faltante(ancho, alto, escala=1):
    """Damero magenta y negro de (ancho, alto) px nativos * escala."""
    clave = ("_faltante", ancho, alto, escala)
    if clave not in _piezas:
        superficie = pygame.Surface((max(1, ancho) * escala, max(1, alto) * escala), pygame.SRCALPHA)
        lado = max(1, 4 * escala)
        for y in range(0, superficie.get_height(), lado):
            for x in range(0, superficie.get_width(), lado):
                if (x // lado + y // lado) % 2 == 0:
                    superficie.fill(assets.COLOR_FALTANTE_BACKROOMS, (x, y, lado, lado))
                else:
                    superficie.fill((0, 0, 0), (x, y, lado, lado))
        _piezas[clave] = superficie
    return _piezas[clave]


def _pieza(grade, clase, nombre, escala, armar, tamanio_faltante):
    clave = (grade, clase, nombre, escala)
    if clave not in _piezas:
        pieza = armar()
        if pieza is None:
            _avisar(grade, clase, nombre)
            pieza = faltante(*tamanio_faltante, escala)
        _piezas[clave] = pieza
    return _piezas[clave]


def tile(grade, id_tile, escala=assets.ESCALA_BACKROOMS):
    lado = assets.TAM_TILE_BACKROOMS
    return _pieza(grade, "tile", str(id_tile), escala,
                  lambda: _recortar(grade, "tiles", rutas.rect_tile(atlas(grade), id_tile), escala), (lado, lado))


def tiene_prop(grade, nombre):
    return rutas.rect_prop(atlas(grade), nombre) is not None


def prop(grade, zona, nombre, escala=assets.ESCALA_BACKROOMS, tamanio=(16, 16)):
    """Prop `nombre` de la `zona` ("hotel", "fx"...). `tamanio`: px nativos
    del damero si falta."""
    completo = rutas.nombre_prop(zona, nombre)
    return _pieza(grade, "prop", completo, escala,
                  lambda: _recortar(grade, "props", rutas.rect_prop(atlas(grade), completo), escala), tamanio)


def light_pool(grade, nombre, escala=assets.ESCALA_BACKROOMS):
    return _pieza(grade, "luz", nombre, escala,
                  lambda: _recortar(grade, "luces", rutas.rect_luz(atlas(grade), nombre), escala), (32, 32))


def tiene_animacion(grade, nombre):
    return rutas.info_animacion(atlas(grade), nombre) is not None


def animacion(grade, nombre, escala=assets.ESCALA_BACKROOMS):
    """[(Surface, ms)] de cada cuadro, o None si el grade no la trae."""
    clave = (grade, "animacion", nombre, escala)
    if clave not in _piezas:
        info = rutas.info_animacion(atlas(grade), nombre)
        cuadros = None
        if info is not None:
            cuadros = []
            for i in range(info["cuadros"]):
                pieza = _recortar(grade, "animaciones", rutas.rect_cuadro(info, i), escala)
                if pieza is None:
                    cuadros = None
                    break
                cuadros.append((pieza, info["ms"][i]))
        if cuadros is None:
            _avisar(grade, "animacion", nombre)
        _piezas[clave] = cuadros
    return _piezas[clave]
