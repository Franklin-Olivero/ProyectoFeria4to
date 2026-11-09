"""Casas de Ciudad Nova: geometría de fachada y ventanas que parpadean (puro).

Cada casa de ciudad_mapa.CASAS tiene huella (col, fila, ancho, alto) y
plantilla (assets.ESTILOS_CASA). Aquí, sin Pygame, se decide:

    vecinas(casas, distancia)          -> pares de índices de casas a <= distancia casillas
    pisos(alto)                         -> cuántos pisos de ventanas caben bajo el techo
    ventanas(ancho, alto, patron)       -> rects (px nativos, 16 por casilla) de cada ventana
    puerta(ancho, alto)                 -> rect de la puerta (centrada abajo)
    encendida(semilla, indice, t)       -> si esa ventana está prendida a los t segundos

Las ventanas no usan azar con estado: un hash de (semilla de la casa,
índice) decide si está prendida, si parpadea y con qué período; así el
mismo instante siempre se ve igual y dos casas nunca laten a la vez.
"""

from src.core import assets

LADO = 16  # px nativos por casilla
ALTO_TECHO = {"tejas": 12, "mansarda": 12, "plano": 4, "terraza": 6}
ALTO_PISO = 14
ALTO_PLANTA_BAJA = 16


def _distancia(a, b):
    """Casillas de separación entre dos rects (0 si se tocan)."""
    ac, af, aw, ah = a
    bc, bf, bw, bh = b
    dx = max(bc - (ac + aw), ac - (bc + bw), 0)
    dy = max(bf - (af + ah), af - (bf + bh), 0)
    return max(dx, dy)


def vecinas(huellas, distancia=2):
    """Pares (i, j) de huellas a `distancia` casillas o menos."""
    return [(i, j) for i in range(len(huellas)) for j in range(i + 1, len(huellas))
            if _distancia(huellas[i], huellas[j]) <= distancia]


def diferencia(estilo_a, estilo_b, atributos=assets.ATRIBUTOS_ESTILO):
    """Cuántos atributos visibles cambian entre dos plantillas."""
    return sum(1 for clave in atributos if estilo_a[clave] != estilo_b[clave])


def alto_techo(techo):
    return ALTO_TECHO[techo]


def pisos(alto, techo):
    """Pisos de ventanas entre el techo y la planta baja."""
    return max(0, (alto * LADO - alto_techo(techo) - ALTO_PLANTA_BAJA) // ALTO_PISO)


def ventanas(ancho, alto, patron, techo):
    """Rects (x, y, w, h) en px nativos de las ventanas de los pisos altos.
    "doble": dos por casilla; "vertical": una alta por casilla; "banda": una
    franja por piso partida en paños; "cuadricula": muro cortina de paños."""
    salida = []
    w = ancho * LADO
    for piso in range(pisos(alto, techo)):
        y = alto_techo(techo) + piso * ALTO_PISO + 3
        if patron == "doble":
            for c in range(ancho):
                salida += [(c * LADO + 2, y, 5, 8), (c * LADO + 9, y, 5, 8)]
        elif patron == "vertical":
            salida += [(c * LADO + 6, y - 1, 4, 10) for c in range(ancho)]
        elif patron == "banda":
            salida += [(x, y + 1, 5, 6) for x in range(3, w - 7, 6)]
        elif patron == "cuadricula":
            for fila in range(2):
                salida += [(x, y - 2 + fila * 6, 5, 5) for x in range(2, w - 6, 6)]
        else:
            raise ValueError(f"patrón de ventanas desconocido: {patron!r}")
    return salida


def puerta(ancho, alto):
    """(x, y, w, h) de la puerta en px nativos, centrada en la planta baja."""
    x = (ancho * LADO) // 2 - 4
    return (x, alto * LADO - 13, 8, 12)


def vitrinas(ancho, alto):
    """Ventanas de la planta baja a los lados de la puerta (dos o cuatro)."""
    px, _, pw, _ = puerta(ancho, alto)
    y = alto * LADO - 12
    salida = []
    if px >= 10:
        salida.append((3, y, px - 6, 7))
    derecha = px + pw + 3
    if ancho * LADO - 3 - derecha >= 6:
        salida.append((derecha, y, ancho * LADO - 3 - derecha, 7))
    return salida


def _hash(*numeros):
    x = 2166136261
    for n in numeros:
        x = ((x ^ (n & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 2 ** 32


def semilla(huella):
    col, fila, ancho, alto = huella
    return col * 131 + fila * 17 + ancho * 7 + alto


def parpadea(semilla_casa, indice):
    return (_hash(semilla_casa, indice, 1) < assets.FRACCION_VENTANAS_ENCENDIDAS
            and _hash(semilla_casa, indice, 2) < assets.FRACCION_VENTANAS_PARPADEAN)


def encendida(semilla_casa, indice, t=0.0):
    """Prendida o no a los `t` segundos. Las que parpadean pasan el 75 % de
    su período prendidas, cada una con su período y su fase."""
    if _hash(semilla_casa, indice, 1) >= assets.FRACCION_VENTANAS_ENCENDIDAS:
        return False
    if not parpadea(semilla_casa, indice):
        return True
    minimo, maximo = assets.PERIODO_VENTANA
    periodo = minimo + (maximo - minimo) * _hash(semilla_casa, indice, 3)
    fase = _hash(semilla_casa, indice, 4) * periodo
    return ((t + fase) % periodo) < 0.75 * periodo


def color_ventana(semilla_casa):
    colores = assets.COLORES_VENTANA_CASA
    return colores[int(_hash(semilla_casa, 99) * len(colores)) % len(colores)]
