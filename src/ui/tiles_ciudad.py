"""Suelo de Ciudad Nova (solo dibujo).

src/dungeon/autotile_ciudad.py (puro) dice qué lleva cada casilla según
sus vecinas; aquí se pegan las piezas, pedidas SOLO por
src/ui/arte_ciudad.py (lista blanca y ajuste de paleta), y el resultado se
cachea por descriptor: dos casillas con los mismos vecinos comparten Surface.

    disponible()               -> True si el atlas de la ciudad está
    casilla(col, fila, cuadro) -> Surface de 48x48 (cuadro = fotograma del agua)
    origen(col, fila)          -> "nuevo" (packs cyberpunk) o "antiguo" (pixel art en código)
    es_agua(col, fila)         -> casillas que se redibujan animadas cada frame
    cuadro_agua(tiempo)        -> fotograma del agua a los `tiempo` segundos

Calle (packs cyberpunk): asfalto con el grano a lo largo del tramo ->
bordillo gris donde da a otra cosa (y un taco en cada esquina interna) ->
línea central a trazos -> cebra antes de un cruce o de la plaza.
Banqueta y plaza: la losa gris del mismo pack. Pasto y jardines: el pasto
oscuro de siempre; los jardines con un bordillo de piedra hacia lo que no
es jardín. Alberca y fuentes: agua del pack desaturada con su borde.
Sin el atlas, cada casilla vuelve a su pixel art de casillas_ciudad.py.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import autotile_ciudad as at
from src.dungeon import ciudad_mapa
from src.ui import arte_ciudad, casillas_ciudad

T = TAM_CASILLA
_cache = {}
_ROTACION = {"N": 0, "O": 90, "S": 180, "E": 270}  # grados (antihorario) para llevar una tira "N" a su lado


def disponible():
    return arte_ciudad.imagen("ciudad:" + assets.TEXTURA_TERRENO_CIUDAD["calle"]) is not None


def _dentro(rect, col, fila):
    c, f, ancho, alto = rect
    return c <= col < c + ancho and f <= fila < f + alto


def _es_explanada(col, fila):
    """Plazas peatonales: la cebra se pinta donde una calle desemboca en ellas."""
    return _dentro(ciudad_mapa.PLAZA, col, fila)


def _descriptor(col, fila):
    clave = ("desc", col, fila)
    if clave not in _cache:
        _cache[clave] = at.descriptor(ciudad_mapa.MAPA, col, fila, _es_explanada)
    return _cache[clave]


# ----------------------------------------------------------------------
# Piezas
# ----------------------------------------------------------------------

def _pieza(nombre):
    return arte_ciudad.imagen("ciudad:" + nombre)


def _trozo(nombre, paridad, desplazamiento=0):
    """48x48 de la textura `nombre`: el tramo que toca por paridad si es
    más grande que una casilla, o la textura repetida si es más chica."""
    pieza = _pieza(nombre)
    ancho, alto = pieza.get_size()
    salida = pygame.Surface((T, T), pygame.SRCALPHA)
    x0 = (paridad[0] * T) % ancho if ancho >= 2 * T else 0
    y0 = (paridad[1] * T) % alto if alto >= 2 * T else 0
    x0 = (x0 + desplazamiento) % ancho
    for y in range(-y0, T, alto):
        for x in range(-x0, T, ancho):
            salida.blit(pieza, (x, y))
    return salida


def _tira(nombre, lado, grosor, paridad=(0, 0)):
    """Tira horizontal de la pieza (largo de una casilla, `grosor` px de
    alto, su lado "de afuera" arriba), girada para apoyarse en `lado`."""
    clave = ("tira", nombre, lado, grosor, paridad)
    if clave not in _cache:
        pieza = _pieza(nombre)
        ancho, alto = pieza.get_size()
        if alto != grosor:
            pieza = pygame.transform.scale(pieza, (ancho, grosor))
        x0 = (paridad[0] * T + paridad[1] * T // 2) % max(1, ancho - T + 1)
        tira = pygame.Surface((T, grosor), pygame.SRCALPHA)
        for x in range(-x0, T, ancho):
            tira.blit(pieza, (x, 0))
        _cache[clave] = pygame.transform.rotate(tira, _ROTACION[lado])
    return _cache[clave]


def _pegar_tira(superficie, tira, lado):
    destino = {"N": (0, 0), "S": (0, T - tira.get_height()), "O": (0, 0), "E": (T - tira.get_width(), 0)}[lado]
    superficie.blit(tira, destino)


def _bordes(superficie, nombre, lados, esquinas, grosor, paridad):
    for lado in lados:
        _pegar_tira(superficie, _tira(nombre, lado, grosor, paridad), lado)
    if esquinas:  # un taco cuadrado cierra la L del borde en cada esquina interna
        taco = _tira(nombre, "N", grosor).subsurface((0, 0, grosor, grosor))
        for esquina in esquinas:
            superficie.blit(taco, (T - grosor if "E" in esquina else 0, T - grosor if esquina.startswith("S") else 0))


def _linea_carril(superficie, lado):
    """Medio trazo amarillo pegado al lado que da al otro carril: con el de
    la casilla vecina forma la línea central."""
    pieza = _pieza(assets.PIEZA_LINEA_CARRIL)
    ancho = pieza.get_width()
    trazo = pygame.transform.scale(pieza, (ancho, assets.LARGO_TRAZO_CARRIL))
    if lado in ("N", "S"):
        trazo = pygame.transform.rotate(trazo, 90)
    medio = ancho // 2 + 1
    if lado == "E":
        superficie.blit(trazo, (T - medio, (T - trazo.get_height()) // 2))
    elif lado == "O":
        superficie.blit(trazo, (medio - ancho, (T - trazo.get_height()) // 2))
    elif lado == "S":
        superficie.blit(trazo, ((T - trazo.get_width()) // 2, T - medio))
    else:
        superficie.blit(trazo, ((T - trazo.get_width()) // 2, medio - ancho))


def _cebra(superficie, orientacion):
    pieza = _pieza(assets.PIEZA_CEBRA)
    if orientacion == "v":
        pieza = pygame.transform.rotate(pieza, 90)
    superficie.blit(pieza, pieza.get_rect(center=(T // 2, T // 2)))


def _pasto(oscuro=False):
    clave = ("pasto", oscuro)
    if clave not in _cache:
        base = casillas_ciudad.casilla_pasto().copy()
        if oscuro:
            tinte = round(255 * assets.FACTOR_PASTO_JARDIN)
            base.fill((tinte, tinte, tinte), special_flags=pygame.BLEND_RGB_MULT)
        _cache[clave] = base
    return _cache[clave]


# ----------------------------------------------------------------------
# Casillas
# ----------------------------------------------------------------------

def _componer(descriptor, cuadro):
    nombre, lados, esquinas, extra = descriptor
    texturas = assets.TEXTURA_TERRENO_CIUDAD
    if nombre == at.CALLE:
        tramo, linea, cebra, _, paridad = extra
        superficie = _trozo(texturas["calle"], paridad)
        if tramo == "h":  # el grano del asfalto corre a lo largo de la calle
            superficie = pygame.transform.rotate(superficie, 90)
        _bordes(superficie, assets.PIEZA_BORDILLO, lados, esquinas, assets.GROSOR_BORDILLO, paridad)
        if linea is not None:
            _linea_carril(superficie, linea)
        if cebra is not None:
            _cebra(superficie, cebra)
        return superficie
    if nombre == at.ACERA:
        _, paridad = extra
        return _trozo(texturas["acera"], paridad)
    if nombre == at.PASTO:
        return _pasto().copy()
    (paridad,) = extra
    if nombre == at.AGUA:
        superficie = _trozo(texturas["agua"], paridad, cuadro * assets.DESPLAZAMIENTO_CUADRO_AGUA)
        _bordes(superficie, assets.PIEZA_BORDILLO, lados, esquinas, assets.GROSOR_BORDILLO, paridad)
        return superficie
    if nombre == at.VERDE:
        superficie = _pasto(oscuro=True).copy()
        _bordes(superficie, assets.PIEZA_BORDILLO, lados, esquinas, assets.GROSOR_BORDILLO // 2, paridad)
        return superficie
    return _trozo(texturas["acera"], paridad)  # bajo casas y edificios (queda tapado)


def _antigua(col, fila):
    """La casilla en pixel art de código (respaldo sin atlas)."""
    letra = ciudad_mapa.MAPA[fila][col]
    if letra in (ciudad_mapa.PASTO, ciudad_mapa.JARDIN, ciudad_mapa.CAMELLON, ciudad_mapa.AGUA, ciudad_mapa.FUENTE):
        return casillas_ciudad.casilla_pasto()
    if letra in ciudad_mapa.CALLES:
        return casillas_ciudad.casilla_calle(None)
    if _dentro(ciudad_mapa.PLAZA, col, fila):
        return casillas_ciudad.casilla_plaza()
    return casillas_ciudad.casilla_acera()


def es_agua(col, fila):
    return _descriptor(col, fila)[0] == at.AGUA


def cuadro_agua(tiempo):
    return int(tiempo / assets.DURACION_CUADRO_AGUA) % assets.CUADROS_AGUA


def casilla(col, fila, cuadro=0):
    """Surface 48x48 de la casilla (cacheada por descriptor y cuadro)."""
    if not disponible():
        return _antigua(col, fila)
    descriptor = _descriptor(col, fila)
    clave = ("casilla", descriptor, cuadro if descriptor[0] == at.AGUA else 0)
    if clave not in _cache:
        superficie = _componer(descriptor, clave[2])
        _cache[clave] = superficie.convert_alpha() if pygame.display.get_surface() else superficie
    return _cache[clave]


def origen(col, fila):
    """De dónde sale el dibujo de la casilla: 'nuevo' (packs cyberpunk) o 'antiguo'."""
    if not disponible():
        return "antiguo"
    return "antiguo" if _descriptor(col, fila)[0] in (at.PASTO, at.VERDE) else "nuevo"
