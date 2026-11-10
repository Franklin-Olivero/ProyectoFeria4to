"""Suelo de Ciudad Nova armado con las piezas de los packs (solo dibujo).

src/dungeon/autotile_ciudad.py (puro) dice qué lleva cada casilla según
sus vecinas; aquí se pegan las piezas del atlas (cargador_assets.pieza_ciudad)
a escala 1:1 y el resultado se cachea por descriptor: dos casillas con los
mismos vecinos comparten Surface.

    disponible()               -> True si el atlas de la ciudad está
    casilla(col, fila, cuadro) -> Surface de 48x48 (cuadro = fotograma del agua)
    origen(col, fila)          -> "nuevo" (packs cyberpunk) o "antiguo" (pixel art en código)
    es_agua(col, fila)         -> casillas que se redibujan animadas cada frame
    cuadro_agua(tiempo)        -> fotograma del agua a los `tiempo` segundos

Capas de una calle: asfalto -> bordillos de peligro en los lados que dan
a otra cosa (y un taco en cada esquina interna) -> línea central a trazos
-> cebra antes de un cruce o de la plaza -> barandas si cruza el canal.
Sin el atlas, cada casilla vuelve a su pixel art de casillas_ciudad.py.
"""

import pygame

from src.core import assets
from src.core.balance import TAM_CASILLA
from src.dungeon import autotile_ciudad as at
from src.dungeon import ciudad_mapa
from src.ui import cargador_assets, casillas_ciudad

T = TAM_CASILLA
_cache = {}
_ROTACION = {"N": 0, "O": 90, "S": 180, "E": 270}  # grados (antihorario) para llevar una tira "N" a su lado


def disponible():
    return cargador_assets.pieza_ciudad(assets.TEXTURA_TERRENO_CIUDAD["calle"]) is not None


def _dentro(rect, col, fila):
    c, f, ancho, alto = rect
    return c <= col < c + ancho and f <= fila < f + alto


def _es_explanada(col, fila):
    """Plazas peatonales: la cebra se pinta donde una calle desemboca en ellas."""
    return _dentro(ciudad_mapa.PLAZA, col, fila)


def variante_acera(col, fila):
    """Qué textura lleva una casilla de acera según dónde está."""
    if _dentro(ciudad_mapa.PLAZA, col, fila) or _dentro(ciudad_mapa.PLAZA_CIVICA, col, fila):
        return "plaza"
    if _dentro(ciudad_mapa.PASEO_COMERCIAL, col, fila) or _dentro(ciudad_mapa.PATIO_COLEGIO, col, fila):
        return "cancha"
    return "acera"


def _descriptor(col, fila):
    clave = ("desc", col, fila)
    if clave not in _cache:
        letra = ciudad_mapa.MAPA[fila][col]
        base = at.descriptor(ciudad_mapa.MAPA, col, fila, _es_explanada)
        if base[0] == at.ACERA:
            base = base + (variante_acera(col, fila),)
        elif letra == ciudad_mapa.FUENTE and _dentro(ciudad_mapa.MONUMENTO, col, fila):
            base = (at.ACERA, (), (), ((), (col % 2, fila % 2)), "plaza")  # bajo la Torre de Datos: losas
        _cache[clave] = base
    return _cache[clave]


# ----------------------------------------------------------------------
# Piezas
# ----------------------------------------------------------------------

def _pieza(nombre):
    return cargador_assets.pieza_ciudad(nombre, assets.FACTOR_TEXTURA_CIUDAD.get(nombre, 1.0))


def _trozo(nombre, paridad, desplazamiento=0):
    """48x48 de la textura `nombre`: el cuarto que toca por paridad si mide
    96, o la textura repetida si es más chica que una casilla."""
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
    alto), girada para apoyarse en `lado`."""
    pieza = _pieza(nombre)
    ancho, alto = pieza.get_size()
    if alto > ancho:  # las tiras verticales del atlas (canto metálico) se acuestan
        pieza = pygame.transform.rotate(pieza, 90)
        ancho, alto = alto, ancho
    x0 = (paridad[0] * T) % max(1, ancho - T + 1)
    tira = pygame.Surface((T, grosor), pygame.SRCALPHA)
    for x in range(-x0, T, ancho):
        tira.blit(pygame.transform.scale(pieza, (ancho, grosor)) if alto != grosor else pieza, (x, 0))
    return pygame.transform.rotate(tira, _ROTACION[lado])


def _pegar_tira(superficie, tira, lado):
    destino = {"N": (0, 0), "S": (0, T - tira.get_height()), "O": (0, 0), "E": (T - tira.get_width(), 0)}[lado]
    superficie.blit(tira, destino)


def _tacos(superficie, nombre, esquinas, grosor):
    """Un cuadrado de la tira en cada esquina interna (cierra la L del borde)."""
    if not esquinas:
        return
    taco = _tira(nombre, "N", grosor).subsurface((0, 0, grosor, grosor))
    for esquina in esquinas:
        x = T - grosor if "E" in esquina else 0
        y = T - grosor if esquina.startswith("S") else 0
        superficie.blit(taco, (x, y))


def _bordes(superficie, nombre, lados, esquinas, grosor, paridad):
    for lado in lados:
        _pegar_tira(superficie, _tira(nombre, lado, grosor, paridad), lado)
    _tacos(superficie, nombre, esquinas, grosor)


def _linea_carril(superficie, lado, paridad):
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


# ----------------------------------------------------------------------
# Casillas
# ----------------------------------------------------------------------

def _componer(descriptor, cuadro):
    nombre, lados, esquinas, extra = descriptor[:4]
    texturas = assets.TEXTURA_TERRENO_CIUDAD
    if nombre == at.CALLE:
        tramo, linea, cebra, barandas, paridad = extra
        superficie = _trozo(texturas["calle"], paridad)
        _bordes(superficie, assets.PIEZA_BORDILLO, lados, esquinas, assets.GROSOR_BORDILLO, paridad)
        if linea is not None:
            _linea_carril(superficie, linea, paridad)
        if cebra is not None:
            _cebra(superficie, cebra)
        _bordes(superficie, assets.PIEZA_CANTO, barandas, (), assets.GROSOR_CANTO, paridad)
        return superficie
    if nombre == at.ACERA:
        barandas, paridad = extra
        superficie = _trozo(texturas[descriptor[4]], paridad)
        _bordes(superficie, assets.PIEZA_CANTO, barandas, (), assets.GROSOR_CANTO, paridad)
        return superficie
    if nombre == at.PASTO:
        barandas, paridad = extra
        superficie = casillas_ciudad.casilla_pasto().copy()
        _bordes(superficie, assets.PIEZA_CANTO, barandas, (), assets.GROSOR_CANTO, paridad)
        return superficie
    (paridad,) = extra
    if nombre == at.AGUA:
        texturas_agua = texturas["agua"]
        superficie = _trozo(texturas_agua[(paridad[0] + paridad[1]) % len(texturas_agua)], paridad,
                            cuadro * assets.DESPLAZAMIENTO_CUADRO_AGUA)
        brillo = assets.BRILLO_AGUA[cuadro % len(assets.BRILLO_AGUA)]
        if brillo != 1.0:
            extra_luz = round(255 * (brillo - 1))
            superficie.fill((extra_luz, extra_luz, extra_luz), special_flags=pygame.BLEND_RGB_ADD)
        _bordes(superficie, assets.PIEZA_CANTO, lados, esquinas, assets.GROSOR_CANTO, paridad)
        return superficie
    if nombre == at.VERDE:
        superficie = _trozo(texturas["verde"], paridad)
        _bordes(superficie, assets.PIEZA_CANTO, lados, esquinas, assets.GROSOR_CANTO, paridad)
        return superficie
    if nombre == at.MURO:
        # Valla neón: la franja del pack corre a lo largo del muro (girada si el muro es vertical).
        superficie = _trozo(texturas["acera"], paridad)
        pieza = _pieza(texturas["muro"])
        vertical = "N" not in lados and "S" not in lados and ("E" in lados or "O" in lados)
        franja = pieza.subsurface(((paridad[0] * T) % (pieza.get_width() - T), 0, T, pieza.get_height()))
        if vertical:
            franja = pygame.transform.rotate(franja, 90)
        superficie.blit(franja, franja.get_rect(center=(T // 2, T // 2)))
        _bordes(superficie, assets.PIEZA_CANTO, lados, (), assets.GROSOR_CANTO // 2, paridad)
        return superficie
    return _trozo(texturas["acera"], paridad)  # bajo casas y edificios (queda tapado)


def _antigua(col, fila):
    """La casilla en pixel art de código (respaldo sin atlas)."""
    letra = ciudad_mapa.MAPA[fila][col]
    if letra == ciudad_mapa.PASTO:
        return casillas_ciudad.casilla_pasto()
    if letra in ciudad_mapa.CALLES:
        return casillas_ciudad.casilla_calle(None)
    if letra in (ciudad_mapa.MURO, ciudad_mapa.JARDIN, ciudad_mapa.CAMELLON):
        return casillas_ciudad.casilla_arbol()
    if letra in (ciudad_mapa.AGUA, ciudad_mapa.FUENTE):
        return casillas_ciudad.casilla_pasto()
    if variante_acera(col, fila) == "plaza":
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
        _cache[clave] = _componer(descriptor, clave[2]).convert_alpha() if pygame.display.get_surface() \
            else _componer(descriptor, clave[2])
    return _cache[clave]


def origen(col, fila):
    """De dónde sale el dibujo de la casilla: 'nuevo' (packs cyberpunk) o 'antiguo'."""
    if not disponible():
        return "antiguo"
    return "antiguo" if _descriptor(col, fila)[0] == at.PASTO else "nuevo"
