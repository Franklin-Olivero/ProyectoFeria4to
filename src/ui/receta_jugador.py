"""El jugador armado por partes desde las recetas de Pixelbolt (lógica pura).

Cada receta (assets/sprites/fuentes/<rol>.pixel.json) dibuja sus cuadros
"estampando" símbolos (cabeza, torso, piernas y accesorio) con la paleta
de su rol, y la hoja PNG del rol es exactamente ese resultado. Para vestir
a un jugador se repiten las mismas estampas de su rol, pero la cabeza sale
de la receta elegida en HAT y el torso y las piernas de la elegida en SKIN
(cada símbolo con la paleta de la receta de donde sale); la letra de la
piel (assets.SIMBOLO_PIEL) se pinta con el tono elegido en COLOR. Las
posiciones, las duraciones y el accesorio son siempre los del rol. No hay
arte nuevo: solo se separa y se recombina el que ya existe.

Un cuadro armado es una tupla de filas y cada fila una tupla de colores
RGB o None (transparente); src/ui/sprites.py lo convierte en Surface.
Armar un cuadro cuesta O(ancho * alto).
"""

import json
import os

from src.core import assets
from src.core.apariencia import PREDETERMINADA


def leer_receta(rol, carpeta=None):
    """Receta de `<carpeta>/<rol>.pixel.json` (por defecto
    assets.RUTA_RECETAS_SPRITES), o None si falta o no se puede leer."""
    carpeta = assets.RUTA_RECETAS_SPRITES if carpeta is None else carpeta
    try:
        with open(os.path.join(carpeta, f"{rol}.pixel.json"), encoding="utf-8") as archivo:
            receta = json.load(archivo)
    except (OSError, ValueError):
        return None
    return receta if _es_receta(receta) else None


def _es_receta(receta):
    """Forma mínima para armar cuadros sin fallar a mitad de una partida:
    tamaño, símbolos como listas de filas, cuadros con estampas y colores
    '#rrggbb'. Si no la tiene, el jugador se dibuja con su hoja PNG."""
    try:
        return (isinstance(receta["width"], int) and isinstance(receta["height"], int)
                and all(isinstance(filas, list) for filas in receta["symbols"].values())
                and isinstance(receta["frames"], list) and len(receta["frames"]) > 0
                and all(isinstance(c, dict) and isinstance(c.get("ops", []), list) for c in receta["frames"])
                and all(len(color_hex(valor)) == 3 for valor in receta["palette"].values()))
    except (KeyError, TypeError, AttributeError, ValueError):
        return False


def color_hex(texto):
    """'#c8905a' -> (200, 144, 90)."""
    texto = texto.lstrip("#")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def piel_original(receta):
    """Tono de piel con el que fue dibujada la receta, o None si no tiene."""
    color = receta["palette"].get(assets.SIMBOLO_PIEL)
    return color_hex(color) if color else None


def tono_de_piel(apariencia, recetas, rol):
    """Color de la piel del jugador: el tono elegido o, sin elegir, el
    original de la cabeza que lleva (así la mano del Candidato combina)."""
    if apariencia.piel is not None:
        return assets.TONOS_PIEL[apariencia.piel]
    return piel_original(recetas[apariencia.cabeza_para(rol)])


def _receta_del_simbolo(simbolo, rol, apariencia, recetas):
    if simbolo in assets.SIMBOLOS_CABEZA:
        return recetas[apariencia.cabeza_para(rol)]
    if simbolo in assets.SIMBOLOS_TRAJE:
        return recetas[apariencia.traje_para(rol)]
    return recetas[rol]  # el accesorio es del rol


def armar_cuadro(cuadro, recetas, rol, apariencia, piel, simbolos=None):
    """Píxeles de `cuadro` (un frame de la receta de `rol`) con las partes
    de `apariencia` y la piel pintada de `piel` (RGB; None = la de cada
    receta). `simbolos` limita qué estampas se dibujan (vista previa de
    una sola parte)."""
    base = recetas[rol]
    pixeles = [[None] * base["width"] for _ in range(base["height"])]
    for estampa in cuadro.get("ops", ()):
        simbolo = estampa.get("symbol")
        if estampa.get("op") != "stamp" or (simbolos is not None and simbolo not in simbolos):
            continue
        receta = _receta_del_simbolo(simbolo, rol, apariencia, recetas)
        if simbolo not in receta["symbols"]:
            receta = base  # la receta de la parte no lo trae: se usa el del rol
        filas = receta["symbols"].get(simbolo)
        if filas:
            _estampar(pixeles, filas, receta["palette"], estampa.get("x", 0), estampa.get("y", 0), piel)
    return tuple(tuple(fila) for fila in pixeles)


def _estampar(pixeles, filas, paleta, x0, y0, piel):
    """Copia las filas de un símbolo en (x0, y0); '.' es transparente."""
    colores = {letra: color_hex(valor) for letra, valor in paleta.items()}
    if piel is not None:
        colores[assets.SIMBOLO_PIEL] = tuple(piel)
    alto, ancho = len(pixeles), len(pixeles[0])
    for dy, fila in enumerate(filas):
        y = y0 + dy
        if not 0 <= y < alto:
            continue
        for dx, letra in enumerate(fila):
            x = x0 + dx
            if letra != "." and 0 <= x < ancho and letra in colores:
                pixeles[y][x] = colores[letra]


def armar_animaciones(recetas, rol, apariencia):
    """{animacion: ([cuadro armado, ...], [duracion_ms, ...])} del jugador
    de rol `rol` vestido con `apariencia`: mismas animaciones y duraciones
    que su hoja. None si falta alguna receta (el que llama usa la hoja)."""
    necesarias = {rol, apariencia.cabeza_para(rol), apariencia.traje_para(rol)}
    if any(recetas.get(r) is None for r in necesarias):
        return None
    base = recetas[rol]
    piel = tono_de_piel(apariencia, recetas, rol)
    cuadros = {cuadro.get("name"): cuadro for cuadro in base["frames"]}
    armados = {}

    def armado(nombre):
        if nombre not in armados:
            armados[nombre] = armar_cuadro(cuadros[nombre], recetas, rol, apariencia, piel)
        return armados[nombre]

    animaciones = base.get("animations") or {"default": {"frames": list(cuadros)}}
    resultado = {}
    for nombre, animacion in animaciones.items():
        nombres = [n for n in animacion.get("frames", ()) if n in cuadros]
        if nombres:
            resultado[nombre] = ([armado(n) for n in nombres],
                                 [int(cuadros[n].get("duration", 100)) for n in nombres])
    return resultado or None


def armar_parte(recetas, rol_fuente, simbolos, piel):
    """Vista previa de una sola parte para el vestidor: los `simbolos`
    (assets.SIMBOLOS_CABEZA o SIMBOLOS_TRAJE) de la receta de `rol_fuente`
    en su cuadro de vista previa, recortada a las filas que ocupa (a lo
    ancho de la hoja, así todas las de una pestaña miden lo mismo). None
    si no hay receta o la parte está vacía."""
    receta = recetas.get(rol_fuente)
    if receta is None:
        return None
    cuadro = next((c for c in receta["frames"] if c.get("name") == assets.CUADRO_VISTA_PREVIA),
                  receta["frames"][0])
    pixeles = armar_cuadro(cuadro, recetas, rol_fuente, PREDETERMINADA, piel, simbolos)
    ocupadas = [y for y, fila in enumerate(pixeles) if any(color is not None for color in fila)]
    if not ocupadas:
        return None
    return pixeles[ocupadas[0]:ocupadas[-1] + 1]
