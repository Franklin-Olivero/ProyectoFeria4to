"""Personalización del jugador sobre el arte de Higgsfield (lógica pura, sin pygame).

Cada hoja de jugador (assets/sprites/jugadores/<rol>.png, hecha por
tools/generar_jugadores_higgsfield.py) trae al lado su mapa de partes
(<rol>.partes.png): cada píxel pintado con el color de su parte en
assets.COLOR_PARTE_JUGADOR (piel, pelo, ropa, pantalón, zapatos) o
transparente si no se tiñe (contorno, ojos, blancos, accesorios).

Teñir una parte es pasar cada uno de sus píxeles a la familia del color
elegido conservando su luz: `teñir(original, referencia, objetivo)` deja
la referencia (el color más usado de esa parte) exactamente en el
objetivo y los más claros u oscuros en proporción, así las sombras y los
brillos del dibujo siguen ahí.

Qué color se elige sale de una Apariencia (src/core/apariencia.py):
    piel -> assets.TONOS_PIEL        pelo     -> assets.TONOS_PELO
    ropa -> assets.COLORES_ROPA      pantalon -> assets.COLORES_PANTALON
    zapatos -> assets.COLORES_ZAPATOS
None en un campo = el color original del dibujo.

Un cuadro es una tupla de filas y cada fila una tupla de RGBA (o None si
es transparente). Teñir un cuadro cuesta O(ancho * alto).
"""

from src.core import assets

PALETAS = {
    "piel": assets.TONOS_PIEL,
    "pelo": assets.TONOS_PELO,
    "ropa": assets.COLORES_ROPA,
    "pantalon": assets.COLORES_PANTALON,
    "zapatos": assets.COLORES_ZAPATOS,
}
PARTE_DE_COLOR = {tuple(color): parte for parte, color in assets.COLOR_PARTE_JUGADOR.items()}


def luminancia(color):
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def teñir(original, referencia, objetivo):
    """`original` pasado a la familia de `objetivo` (RGB): la referencia
    queda exactamente en `objetivo` y los demás tonos, en proporción a su luz."""
    factor = luminancia(original) / max(1.0, luminancia(referencia))
    return tuple(max(0, min(255, round(canal * factor))) for canal in objetivo)


def objetivos(apariencia):
    """{parte: RGB elegido} de las partes que la apariencia cambia."""
    if apariencia is None:
        return {}
    elegidos = {}
    for parte, paleta in PALETAS.items():
        indice = getattr(apariencia, parte, None)
        if indice is not None and 0 <= indice < len(paleta):
            elegidos[parte] = tuple(paleta[indice])
    return elegidos


def referencias(cuadro, partes):
    """{parte: color más usado} de cada parte en `cuadro` (el de "quieto")."""
    cuentas = {}
    for fila, fila_partes in zip(cuadro, partes):
        for color, parte in zip(fila, fila_partes):
            if color is not None and parte is not None:
                por_color = cuentas.setdefault(parte, {})
                rgb = tuple(color[:3])
                por_color[rgb] = por_color.get(rgb, 0) + 1
    return {parte: max(por_color.items(), key=lambda kv: (kv[1], kv[0]))[0] for parte, por_color in cuentas.items()}


def teñir_cuadro(cuadro, partes, refs, elegidos):
    """`cuadro` con cada parte de `elegidos` teñida (los demás píxeles, iguales)."""
    if not elegidos:
        return cuadro
    resultado = []
    for fila, fila_partes in zip(cuadro, partes):
        nueva = []
        for color, parte in zip(fila, fila_partes):
            if color is not None and parte in elegidos and parte in refs:
                rgb = teñir(color[:3], refs[parte], elegidos[parte])
                color = (*rgb, color[3]) if len(color) > 3 else rgb
            nueva.append(color)
        resultado.append(tuple(nueva))
    return tuple(resultado)


def parte_de(color):
    """Parte que marca un píxel del mapa de partes (RGBA o None), o None."""
    if color is None or (len(color) > 3 and color[3] == 0):
        return None
    return PARTE_DE_COLOR.get(tuple(color[:3]))
