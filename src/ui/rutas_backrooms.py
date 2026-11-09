"""Rutas y atlas del arte Backrooms por grade (puro, sin Pygame).

assets/backrooms/<grade>/atlas.json describe qué hay en cada hoja del
grade (lo escribe tools/empaquetar_backrooms.py):

    tiles:       {"<id>": [x, y]}                       (16x16 en tiles.png)
    props:       {"<nombre>": [x, y, w, h]}             (props.png)
    animaciones: {"<nombre>": {"rect": [x, y, w, h], "cuadros": n,
                               "ancho": w, "alto": h, "ms": [ms por cuadro]}}  (animaciones.png)
    luces:       {"<nombre>": [x, y, w, h]}             (luces.png)

Todo grade tiene el mismo layout de origen, así que un id o un nombre
significa lo mismo en cualquiera: el grade es solo un parámetro. Aquí se
decide qué ruta y qué rect pedir; src/ui/cargador_backrooms.py carga y
recorta.
"""

import json
import os

from src.core import assets

# Sufijos de una animación que no existen en su versión quieta
# ("hotel_sconce_flicker_lit" -> "hotel_sconce_lit").
SUFIJOS_ANIMACION = ("flicker", "blink", "buzz", "hum", "static", "roll", "cycle", "drop", "drip", "stir",
                     "dust", "ringing", "glow", "dying", "sway", "swing", "shimmer", "sweep", "drift")


def es_grade(grade):
    return grade in assets.GRADES_BACKROOMS


def carpeta_grade(grade, raiz=None):
    if not es_grade(grade):
        raise ValueError(f"grade desconocido: {grade!r} (válidos: {', '.join(assets.GRADES_BACKROOMS)})")
    return os.path.join(raiz or assets.RUTA_BACKROOMS, grade)


def ruta_atlas(grade, raiz=None):
    return os.path.join(carpeta_grade(grade, raiz), assets.ARCHIVO_ATLAS_BACKROOMS)


def ruta_hoja(grade, tipo, raiz=None):
    """Ruta de la hoja `tipo` ("tiles", "props", "animaciones", "luces") del grade."""
    return os.path.join(carpeta_grade(grade, raiz), assets.HOJAS_BACKROOMS[tipo])


def grades_disponibles(raiz=None, existe=os.path.exists):
    """Grades empaquetados (los que tienen atlas.json), en el orden de GRADES_BACKROOMS."""
    return [g for g in assets.GRADES_BACKROOMS if existe(ruta_atlas(g, raiz))]


def elegir_grade(pedido, disponibles):
    """El grade pedido si está; si no, el de por defecto; si no, el primero
    que haya; None si no hay ninguno."""
    if pedido in disponibles:
        return pedido
    if assets.GRADE_POR_DEFECTO in disponibles:
        return assets.GRADE_POR_DEFECTO
    return disponibles[0] if disponibles else None


def leer_atlas(grade, raiz=None, abrir=open):
    """El atlas del grade como dict, o None si falta o está roto."""
    try:
        with abrir(ruta_atlas(grade, raiz), encoding="utf-8") as archivo:
            atlas = json.load(archivo)
    except (OSError, ValueError):
        return None
    for tipo in assets.HOJAS_BACKROOMS:
        atlas.setdefault(tipo, {})
    return atlas


def nombre_prop(zona, nombre):
    """Nombre completo del prop: los del pack llevan la zona como prefijo
    ("hotel", "lobby_sofa" -> "hotel_lobby_sofa"); si ya lo trae, igual."""
    if not zona or nombre.startswith(f"{zona}_"):
        return nombre
    return f"{zona}_{nombre}"


def rect_tile(atlas, id_tile):
    """(x, y, 16, 16) del tile en tiles.png, o None."""
    pos = atlas["tiles"].get(str(id_tile)) if atlas else None
    if pos is None:
        return None
    lado = assets.TAM_TILE_BACKROOMS
    return (pos[0], pos[1], lado, lado)


def rect_prop(atlas, nombre):
    rect = atlas["props"].get(nombre) if atlas else None
    return tuple(rect) if rect else None


def rect_luz(atlas, nombre):
    rect = atlas["luces"].get(nombre) if atlas else None
    return tuple(rect) if rect else None


def info_animacion(atlas, nombre):
    return atlas["animaciones"].get(nombre) if atlas else None


def rect_cuadro(info, indice):
    """Rect del cuadro `indice` dentro de la tira de la animación."""
    x, y = info["rect"][:2]
    return (x + indice * info["ancho"], y, info["ancho"], info["alto"])


def cuadro_por_tiempo(duraciones_ms, t):
    """Índice del cuadro que toca a los `t` segundos (la animación se repite)."""
    total = sum(duraciones_ms)
    if total <= 0:
        return 0
    resto = (t * 1000) % total
    for i, ms in enumerate(duraciones_ms):
        if resto < ms:
            return i
        resto -= ms
    return len(duraciones_ms) - 1


def prop_estatico_de(nombre_animacion, props):
    """La versión quieta de una animación entre los nombres de `props`:
    primero el mismo nombre, luego sin sus sufijos de movimiento. None si
    no hay ninguna."""
    if nombre_animacion in props:
        return nombre_animacion
    partes = nombre_animacion.split("_")
    sin_sufijos = [p for p in partes if p not in SUFIJOS_ANIMACION]
    candidatos = ["_".join(sin_sufijos)]
    for i in range(len(partes) - 1, 1, -1):
        candidatos.append("_".join(partes[:i]))
    return next((c for c in candidatos if c in props), None)
