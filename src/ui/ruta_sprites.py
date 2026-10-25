"""Dónde buscar el arte real de cada sprite y cómo leer su atlas (lógica
pura, sin Pygame).

Separado de src/ui/sprites.py para poder probar la regla de fallback
sin cargar imágenes: si el PNG existe se usa; si no, el pixel art
dibujado en código. También interpreta el atlas JSON que Pixelbolt
exporta junto a cada hoja y elige el cuadro de una animación según el
tiempo transcurrido.
"""

import os

from src.core import assets


def ruta_sprite(id_sprite, carpeta, existe=os.path.exists):
    """Ruta de `<carpeta>/<id_sprite>.png` si el archivo existe; si no,
    None (= usar el placeholder). `existe` se inyecta en los tests."""
    ruta = os.path.join(carpeta, f"{id_sprite}.png")
    return ruta if existe(ruta) else None


def ruta_sprite_enemigo(id_sprite, carpeta=None, existe=os.path.exists):
    """Igual que ruta_sprite, con assets.RUTA_SPRITES_ENEMIGOS por defecto."""
    carpeta = assets.RUTA_SPRITES_ENEMIGOS if carpeta is None else carpeta
    return ruta_sprite(id_sprite, carpeta, existe)


def ruta_atlas(ruta_png):
    """`<id>.atlas.json` que acompaña a `<id>.png`."""
    base, _ = os.path.splitext(ruta_png)
    return base + ".atlas.json"


def cuadros_de_atlas(atlas):
    """Atlas de Pixelbolt -> {animacion: [((x, y, w, h), duracion_ms), ...]}.

    `atlas["frames"]` trae cada cuadro con su rect y duración y
    `atlas["animations"]` la lista de nombres de cada animación. Si una
    hoja no declara animaciones, todos los cuadros en orden forman una
    sola llamada "default" (lo mismo que hace Pixelbolt al exportar)."""
    cuadros = atlas["frames"]

    def cuadro(nombre):
        datos = cuadros[nombre]
        r = datos["frame"]
        return (r["x"], r["y"], r["w"], r["h"]), int(datos.get("duration", 100))

    animaciones = atlas.get("animations") or {"default": {"frames": list(cuadros)}}
    return {nombre: [cuadro(n) for n in anim["frames"]] for nombre, anim in animaciones.items()}


def cuadros_por_nombre(atlas):
    """Atlas de Pixelbolt -> {nombre_del_cuadro: ((x, y, w, h), duracion_ms)}
    para las hojas que se usan por nombre (piso, puerta) y no por animación."""
    resultado = {}
    for nombre, datos in atlas["frames"].items():
        r = datos["frame"]
        resultado[nombre] = ((r["x"], r["y"], r["w"], r["h"]), int(datos.get("duration", 100)))
    return resultado


def indice_por_tiempo(duraciones_ms, tiempo_s):
    """Índice del cuadro que toca en `tiempo_s` segundos, repitiendo la
    animación en bucle. Con un solo cuadro (o duraciones vacías) es 0."""
    total = sum(duraciones_ms)
    if total <= 0 or len(duraciones_ms) <= 1:
        return 0
    restante = (max(0.0, tiempo_s) * 1000.0) % total
    for indice, duracion in enumerate(duraciones_ms):
        if restante < duracion:
            return indice
        restante -= duracion
    return len(duraciones_ms) - 1
