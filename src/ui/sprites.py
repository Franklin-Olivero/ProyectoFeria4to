"""Sprites en pixel art dibujados en código (solo presentación).

Cada sprite es una lista de filas de caracteres; cada carácter es un
color de la leyenda ('.' = transparente). `sprite(nombre, escala,
paleta)` lo convierte en una Surface escalada y la cachea, así el
dibujo por frame es un solo blit. Los enemigos se piden siempre con
`sprite_enemigo(tipo)`, que ya intenta cargar un PNG real antes de caer
al placeholder. Cuando llegue arte real basta con
reemplazar estas funciones por `pygame.image.load`, sin tocar las
entidades que los usan.
"""

import json
import os

import pygame

from src.core import assets, balance
from src.core.apariencia import PREDETERMINADA
from src.ui import mezcla_jugador, tinte_jugador
from src.ui.ruta_sprites import (
    cuadros_de_atlas,
    cuadros_por_nombre,
    indice_por_tiempo,
    ruta_atlas,
    ruta_sprite,
    ruta_sprite_enemigo,
)

# Colores comunes de la leyenda
_NEGRO = (16, 14, 30)
_PIEL = (242, 200, 160)
_PELO = (92, 56, 36)
_BLANCO = (246, 246, 252)
_GRIS = (70, 66, 100)

# Jugador (12x16): cabeza, cuerpo y piernas. 'c' = color del rol.
JUGADOR = [
    "...hhhhhh...",
    "..hhhhhhhh..",
    "..hpppppph..",
    "..ppkppkpp..",
    "..pppppppp..",
    "...pppppp...",
    "....pppp....",
    "..cccccccc..",
    ".cccccccccc.",
    ".c.cccccc.c.",
    ".p.cccccc.p.",
    "...cccccc...",
    "...dddddd...",
    "...dd..dd...",
    "...dd..dd...",
    "..nnn..nnn..",
]
PALETA_JUGADOR = {
    "h": _PELO, "p": _PIEL, "k": _NEGRO, "d": (40, 36, 70), "n": _NEGRO,
}

# Enemigo "monitor con cara" (14x14): pantalla rosada con antena.
ENEMIGO = [
    ".....k..k.....",
    ".....k..k.....",
    "..kkkkkkkkkk..",
    ".kccccccccccck",
    ".kcwwccccwwcck",
    ".kcwkccccwkcck",
    ".kccccccccccck",
    ".kccccccccccck",
    ".kcckkkkkkccck",
    ".kccccccccccck",
    "..kkkkkkkkkk..",
    "....kk..kk....",
    "...kkk..kkk...",
    "..kk......kk..",
]
PALETA_ENEMIGO = {"k": _NEGRO, "c": assets.COLOR_ENEMIGO, "w": _BLANCO}
PALETA_ENEMIGO_MORADO = {"k": _NEGRO, "c": assets.COLOR_ENEMIGO_SECUNDARIO, "w": _BLANCO}

# Placeholders por tipo de enemigo (14x14). 'c' = color principal del
# tipo, 's' = secundario (assets.COLOR_*_ENEMIGO[tipo]).
# Perseguidor: cuernos y boca con dientes, agresivo.
PERSEGUIDOR = [
    "k............k",
    "kk..........kk",
    ".kck......kck.",
    ".kcckkkkkkcck.",
    "..kcccccccck..",
    ".kccwwccwwcck.",
    ".kccwkccwkcck.",
    ".kcccccccccck.",
    ".kcssssssssck.",
    ".kcswswswswck.",
    "..kcccccccck..",
    "...kkkkkkkk...",
    "..kk..kk..kk..",
    ".kk...kk...kk.",
]
# Tirador: un solo ojo y un cañón a la derecha.
TIRADOR = [
    "....kkkkkk....",
    "...kcccccck...",
    "..kcccccccck..",
    ".kccswwwwscck.",
    ".kccswkkwscck.",
    ".kccswwwwscck.",
    ".kcccsssscckkk",
    ".kccccccccckss",
    ".kccccccccckkk",
    "..kcccccccck..",
    "...kkkkkkkk...",
    "....kk..kk....",
    "...kkk..kkk...",
    "..............",
]
# Curandero: cuerpo redondo con una cruz.
CURANDERO = [
    "....kkkkkk....",
    "..kkcccccckk..",
    ".kccccsscccck.",
    ".kccccsscccck.",
    "kcccssssssccck",
    "kcccssssssccck",
    ".kccccsscccck.",
    ".kccccsscccck.",
    ".kcccccccccck.",
    "..kcccccccck..",
    "...kkcccckk...",
    ".....kkkk.....",
    "..............",
    "..............",
]
PIXEL_ART_ENEMIGO = {"perseguidor": PERSEGUIDOR, "tirador": TIRADOR, "curandero": CURANDERO}


def paleta_enemigo(clave):
    return {"k": _NEGRO, "w": _BLANCO, "c": assets.COLOR_PRINCIPAL_ENEMIGO[clave],
            "s": assets.COLOR_SECUNDARIO_ENEMIGO[clave]}

# Jefe "Servidor Central" (22x22): torre de servidor con luces.
JEFE = [
    "..kkkkkkkkkkkkkkkkkk..",
    ".kccccccccccccccccccck",
    ".kcwwcccccccccccccwwck",
    ".kcwkcccccccccccckwcck",
    ".kccccccccccccccccccck",
    ".kckkkkkkkkkkkkkkkkcck",
    ".kcccccccccccccccccc.k",
    ".kcmmccmmccmmccmmcccck",
    ".kccccccccccccccccccck",
    ".kckkkkkkkkkkkkkkkkcck",
    ".kccccccccccccccccccck",
    ".kcmmccmmccmmccmmcccck",
    ".kccccccccccccccccccck",
    ".kckkkkkkkkkkkkkkkkcck",
    ".kccccccccccccccccccck",
    ".kcmmccmmccmmccmmcccck",
    ".kccccccccccccccccccck",
    ".kckkkkkkkkkkkkkkkkcck",
    ".kccccccccccccccccccck",
    ".kcggccccccccccccggcck",
    ".kccccccccccccccccccck",
    "..kkkkkkkkkkkkkkkkkk..",
]
PALETA_JEFE = {"k": _NEGRO, "c": assets.COLOR_JEFE, "w": _BLANCO, "m": assets.COLOR_MAGENTA,
               "g": assets.COLOR_TEAL}

# Corazón (7x6)
CORAZON = [
    ".cc.cc.",
    "ccccccc",
    "ccccccc",
    ".ccccc.",
    "..ccc..",
    "...c...",
]
PALETA_CORAZON_LLENO = {"c": assets.COLOR_MAGENTA}
PALETA_CORAZON_VACIO = {"c": (74, 60, 110)}

# Muñeco corriendo (10x10) para el indicador del dash; 'c' = color del rol.
CORRIENDO = [
    "......cc..",
    "......cc..",
    "...cccc...",
    "..c.cc.c..",
    "....cc..c.",
    "....ccc...",
    "...c...c..",
    "..c....c..",
    ".c......c.",
    "..........",
]

# Candado (8x10)
CANDADO = [
    "..aaaa..",
    ".aa..aa.",
    ".aa..aa.",
    "cccccccc",
    "cccccccc",
    "ccckkccc",
    "ccckkccc",
    "cccccccc",
    "cccccccc",
    "........",
]
PALETA_CANDADO = {"a": (210, 170, 70), "c": assets.COLOR_AMARILLO, "k": _NEGRO}

# Terminal del cuarto (14x18): monitor con candado y base.
TERMINAL = [
    "kkkkkkkkkkkkkk",
    "kggggggggggggk",
    "kggggggggggggk",
    "kgggaaaaaagggk",
    "kggaa....aaggk",
    "kggaa....aaggk",
    "kgccccccccccgk",
    "kgccccccccccgk",
    "kgcccckkccccgk",
    "kgcccckkccccgk",
    "kgccccccccccgk",
    "kggggggggggggk",
    "kkkkkkkkkkkkkk",
    "..kkkkkkkkkk..",
    "..kmmmmmmmmk..",
    "..kmmmmmmmmk..",
    "..kkkkkkkkkk..",
    "..............",
]
PALETA_TERMINAL_BLOQUEADA = {"k": _NEGRO, "g": assets.COLOR_TEAL_OSCURO, "a": assets.COLOR_AMARILLO,
                             "c": assets.COLOR_AMARILLO, "m": assets.COLOR_MORADO_OSCURO}
PALETA_TERMINAL_LISTA = {"k": _NEGRO, "g": assets.COLOR_TEAL, "a": assets.COLOR_TEAL,
                         "c": assets.COLOR_TEAL, "m": assets.COLOR_MORADO}

# Chulo (14x10) para la pantalla de purificación.
CHULO = [
    "............cc",
    "...........ccc",
    "..........ccc.",
    ".........ccc..",
    "cc......ccc...",
    "ccc....ccc....",
    ".ccc..ccc.....",
    "..ccccccc.....",
    "...ccccc......",
    "....ccc.......",
]
PALETA_CHULO = {"c": assets.COLOR_TEAL}

# Explosión (15x15) para la pantalla de detonación.
EXPLOSION = [
    ".......m.......",
    "......mmm......",
    "..m...mmm...m..",
    "..mm.mmmmm.mm..",
    "...mmmmammmm...",
    "....mmaaamm....",
    ".mmmmaaaaammmm.",
    "mmmmaaawaaammmm",
    ".mmmmaaaaammmm.",
    "....mmaaamm....",
    "...mmmmammmm...",
    "..mm.mmmmm.mm..",
    "..m...mmm...m..",
    "......mmm......",
    ".......m.......",
]
PALETA_EXPLOSION = {"m": assets.COLOR_MAGENTA, "a": assets.COLOR_AMARILLO, "w": _BLANCO}

# Avatar de la publicación (10x10): robot morado.
AVATAR = [
    "...k..k...",
    ".kkkkkkkk.",
    "kcccccccck",
    "kcwccccwck",
    "kcccccccck",
    "kcckkkkcck",
    "kcccccccck",
    ".kkkkkkkk.",
    "..kk..kk..",
    ".kk....kk.",
]
PALETA_AVATAR = {"k": _NEGRO, "c": assets.COLOR_MORADO, "w": _BLANCO}

# Destello (5x5) decorativo.
DESTELLO = [
    "..w..",
    "..w..",
    "wwwww",
    "..w..",
    "..w..",
]
PALETA_DESTELLO = {"w": (200, 230, 220)}

# --- Menú principal ----------------------------------------------------

# Letras del título (5x7). '#' = color del título; las dos filas de
# arriba se aclaran en palabra_titulo() para darle un brillo de neón.
LETRAS_TITULO = {
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "V": ["#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}
_FILAS_LUZ_TITULO = 2


def _componer_palabra(palabra):
    """Filas de la palabra completa, con una columna vacía entre letras."""
    filas = []
    for y in range(7):
        fila = ".".join(LETRAS_TITULO[letra][y] for letra in palabra)
        filas.append(fila.replace("#", "l") if y < _FILAS_LUZ_TITULO else fila)
    return filas


TITULO = _componer_palabra("CIVITAS")


def palabra_titulo(color, color_luz):
    """(filas, paleta) del título CIVITAS para sprite()."""
    return TITULO, {"#": color, "l": color_luz}


# Nave (11x5) mirando a la derecha: el fondo del menú la voltea si va a la izquierda.
NAVE = [
    "....kkk....",
    "..kccwwk...",
    "kcccccccckl",
    ".kkcccccck.",
    "...kkkkk...",
]
PALETA_NAVE = {"k": _NEGRO, "c": (92, 84, 150), "w": assets.COLOR_CIAN_NEON, "l": assets.COLOR_CIAN_NEON}

# Engranaje del botón de ajustes (12x12); 'c' = color según el estado.
ENGRANAJE = [
    ".....cc.....",
    "..c.cccc.c..",
    ".cccccccccc.",
    "..cccccccc..",
    ".cccc..cccc.",
    "cccc....cccc",
    "cccc....cccc",
    ".cccc..cccc.",
    "..cccccccc..",
    ".cccccccccc.",
    "..c.cccc.c..",
    ".....cc.....",
]


_cache = {}


def sprite(filas, paleta, escala=assets.ESCALA_PIXEL):
    """Surface con el sprite escalado (cacheada por filas, paleta y escala)."""
    clave = (id(filas), tuple(sorted(paleta.items())), escala)
    if clave not in _cache:
        alto, ancho = len(filas), len(filas[0])
        base = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for y, fila in enumerate(filas):
            for x, caracter in enumerate(fila):
                if caracter != ".":
                    base.set_at((x, y), paleta[caracter])
        _cache[clave] = pygame.transform.scale(base, (ancho * escala, alto * escala))
    return _cache[clave]


# --- Hojas de sprites (arte real) --------------------------------------
#
# Una hoja es `<carpeta>/<id>.png` (tira a resolución nativa) más su
# `<id>.atlas.json` de Pixelbolt. Se carga una vez por escala y queda
# como {animacion: ([Surface, ...], [duracion_ms, ...])}; el cuadro que
# toca se elige con ruta_sprites.indice_por_tiempo. Un PNG sin atlas se
# trata como una imagen suelta de un solo cuadro (sin escalar).

_cache_hojas = {}
_cache_cuadros = {}  # (ruta, escala) -> {nombre_del_cuadro: Surface}


def _cargar_hoja(ruta_png, escala):
    """Hoja cargada y escalada, o None si no hay PNG legible."""
    clave = (ruta_png, escala)
    if clave not in _cache_hojas:
        _cache_hojas[clave] = _leer_hoja(ruta_png, escala)
    return _cache_hojas[clave]


def _leer_hoja(ruta_png, escala):
    imagen = _cargar_png(ruta_png)
    if imagen is None:
        return None
    try:
        with open(ruta_atlas(ruta_png), encoding="utf-8") as archivo:
            atlas = json.load(archivo)
        cuadros = cuadros_de_atlas(atlas)
        por_nombre = cuadros_por_nombre(atlas)
    except (OSError, ValueError, KeyError):
        return {"default": ([imagen], [100])}

    escalados = {}

    def escalado(rect):
        if rect not in escalados:
            x, y, w, h = rect
            escalados[rect] = pygame.transform.scale(imagen.subsurface(rect), (w * escala, h * escala))
        return escalados[rect]

    hoja = {}
    for nombre, lista in cuadros.items():
        superficies = [escalado(rect) for rect, _ in lista]
        duraciones = [duracion for _, duracion in lista]
        hoja[nombre] = (superficies, duraciones)
    _cache_cuadros[(ruta_png, escala)] = {nombre: escalado(rect) for nombre, (rect, _) in por_nombre.items()}
    return hoja


def cuadro_por_nombre(ruta_png, nombre, escala=assets.ESCALA_PIXEL):
    """Surface del cuadro `nombre` de la hoja en `ruta_png`, o None si no
    hay hoja o no existe ese cuadro (piso, muro, puertas)."""
    if ruta_png is None or _cargar_hoja(ruta_png, escala) is None:
        return None
    return _cache_cuadros.get((ruta_png, escala), {}).get(nombre)


def cuadro_de_hoja(hoja, animacion, tiempo):
    """Surface de `animacion` en el segundo `tiempo` (bucle). Si la hoja
    no tiene esa animación usa la primera que tenga."""
    if animacion not in hoja:
        animacion = next(iter(hoja))
    superficies, duraciones = hoja[animacion]
    return superficies[indice_por_tiempo(duraciones, tiempo)]


def limpiar_cache_hojas():
    """Olvida las hojas cargadas (p. ej. tras copiar arte nuevo)."""
    _cache_hojas.clear()
    _cache_cuadros.clear()
    _cache_enemigos.clear()
    _cache_retratos.clear()
    _cache_pixeles.clear()
    _cache_retratos_vestidos.clear()
    _cache_vestidos.clear()
    _cache_partes.clear()


# --- Cuarto: piso, muro, puertas y charco ------------------------------

def cuadro_cuarto(nombre):
    """Baldosa o muro (`assets.CUADROS_PISO`, `CUADRO_MURO`...) a ESCALA_PIXEL,
    o None sin hoja."""
    return cuadro_por_nombre(ruta_sprite(assets.ID_SPRITE_CUARTO, assets.RUTA_SPRITES_CUARTO), nombre)


def cuadro_puerta(estado):
    """Puerta horizontal (27x6 por ESCALA_PIXEL) en `estado` = "abierta" /
    "bloqueada" / "sellada", o None sin hoja."""
    return cuadro_por_nombre(ruta_sprite(assets.ID_SPRITE_PUERTA, assets.RUTA_SPRITES_CUARTO),
                             assets.CUADRO_PUERTA[estado])


def sprite_charco(activo, tiempo, radio):
    """Charco tóxico de diámetro ~2*radio (la hoja es de 30 px, se escala
    al entero más cercano), en "aviso" (solo contorno) o "activo"
    (burbujeando); None sin hoja."""
    escala = max(1, round(2 * radio / 30))
    hoja = _cargar_hoja(ruta_sprite(assets.ID_SPRITE_CHARCO, assets.RUTA_SPRITES_CUARTO), escala)
    if hoja is None:
        return None
    animacion = assets.ANIMACION_CHARCO_ACTIVO if activo else assets.ANIMACION_CHARCO_AVISO
    return cuadro_de_hoja(hoja, animacion, tiempo)


# --- Proyectiles -------------------------------------------------------
#
# Plantillas pequeñas que se tiñen con el color de cada proyectil
# ('c' = color, 'd' = su sombra, 'w' = brillo) y se escalan x2 hasta el
# tamaño lógico del proyectil (tamanio = lado del rect de colisión).

BALA_4 = [".kk.", "kwck", "kcdk", ".kk."]
BALA_5 = [".kkk.", "kwcck", "kccck", "kcddk", ".kkk."]
BALA_6 = ["..kk..", ".kwck.", "kwccck", "kcccdk", ".kcdk.", "..kk.."]
# Onda de sonido del Influencer (13x13), apuntando a la derecha.
ONDA_13 = [
    "......kk.....",
    "....kkcc.....",
    "...kcc..kk...",
    "..kc...kcc...",
    "..kc..kc..kk.",
    ".kc...kc..kcc",
    ".kc...kc..kcc",
    ".kc...kc..kcc",
    "..kc..kc..kk.",
    "..kc...kcc...",
    "...kcc..kk...",
    "....kkcc.....",
    "......kk.....",
]
# Punta del rayo del Periodista (5x5).
RAYO_5 = ["..k..", ".kck.", "kcwck", ".kck.", "..k.."]
PLANTILLAS_PROYECTIL = {8: BALA_4, 10: BALA_5, 12: BALA_6, 26: ONDA_13}
ESCALA_PROYECTIL = 2


def _sombra(color):
    return tuple(max(0, int(v * 0.55)) for v in color[:3])


def sprite_proyectil(color, tamanio, plantilla=None):
    """Sprite del proyectil de lado `tamanio` teñido con `color`; None si
    no hay plantilla para ese tamaño (el que llama dibuja un rect)."""
    filas = plantilla or PLANTILLAS_PROYECTIL.get(tamanio)
    if filas is None:
        return None
    paleta = {"k": _NEGRO, "c": tuple(color[:3]), "d": _sombra(color), "w": _BLANCO}
    return sprite(filas, paleta, ESCALA_PROYECTIL)


def escala_hd(escala):
    """Escala para las hojas del jugador hechas desde Higgsfield (cuadros de
    assets.ALTO_JUGADOR_HF = 40 px, el doble que las viejas de 16x20): la
    mitad de `escala`, redondeando hacia arriba. Así cada llamador sigue
    pidiendo la escala de siempre y los píxeles quedan enteros."""
    return max(1, -(-int(escala) // 2))


def sprite_jugador(color_rol, escala=assets.ESCALA_PIXEL, rol=None, tiempo=0.0,
                   caminando=False, dash=False, apariencia=None):
    """Imagen del jugador. Con `rol` (clave de STATS_POR_ROL) y su hoja en
    assets/sprites/jugadores/<rol>.png (el personaje de Higgsfield) devuelve
    el cuadro de "caminar" para `tiempo` (quieto = primer cuadro) o el de
    "dash", a escala_hd(escala); sin hoja, el muñeco dibujado en código
    teñido con `color_rol`. Con una `apariencia` (src/core/apariencia.py)
    que cambie algún color, la hoja sale teñida (_hoja_vestida)."""
    hoja = None
    if rol and (tinte_jugador.objetivos(apariencia) or _mezcla(rol, apariencia)):
        hoja = _hoja_vestida(rol, apariencia, escala_hd(escala))
    if hoja is None and rol:
        hoja = _cargar_hoja(ruta_sprite(rol, assets.RUTA_SPRITES_JUGADORES), escala_hd(escala))
    if hoja is None:
        return sprite(JUGADOR, {**PALETA_JUGADOR, "c": color_rol}, escala)
    if dash and assets.ANIMACION_DASH in hoja:
        return cuadro_de_hoja(hoja, assets.ANIMACION_DASH, 0.0)
    return cuadro_de_hoja(hoja, assets.ANIMACION_CAMINAR, tiempo if caminando else 0.0)


# --- Jugador vestido (vestidores) ---------------------------------------
#
# La hoja del rol y su mapa de partes (<rol>.partes.png) se leen una vez
# como cuadros de píxeles; cada combinación de rol, colores y escala se
# tiñe una sola vez (src/ui/tinte_jugador.py) y queda con la misma forma
# que una hoja cargada. Probar colores en el vestidor crea hojas nuevas:
# se guardan a lo sumo MAX_HOJAS_VESTIDAS y al pasarse se olvida la más vieja.

MAX_HOJAS_VESTIDAS = 64
_cache_pixeles = {}  # rol -> datos de la hoja en píxeles (o None si falta algo)
_cache_vestidos = {}  # (rol, colores, escala) -> hoja teñida (o None)
_cache_partes = {}  # (simbolos, rol, colores, escala) -> Surface (o None)


def _pixeles_de(superficie, rect):
    x0, y0, w, h = rect
    return tuple(
        tuple(_rgba_o_none(superficie.get_at((x0 + x, y0 + y))) for x in range(w))
        for y in range(h))


def _rgba_o_none(pixel):
    return None if pixel.a == 0 else (pixel.r, pixel.g, pixel.b, pixel.a)


def _datos_hoja(rol):
    """{"cuadros": {nombre: píxeles}, "partes": {nombre: [[parte]]},
    "animaciones": {anim: ([nombre], [ms])}, "refs": {parte: RGB}} del rol,
    leídos una vez; None si falta la hoja, su atlas o su mapa de partes."""
    if rol not in _cache_pixeles:
        _cache_pixeles[rol] = _leer_datos_hoja(rol)
    return _cache_pixeles[rol]


def _leer_datos_hoja(rol):
    ruta = ruta_sprite(rol, assets.RUTA_SPRITES_JUGADORES)
    if ruta is None:
        return None
    imagen = _cargar_png(ruta)
    mapa = _cargar_png(os.path.join(assets.RUTA_SPRITES_JUGADORES, f"{rol}.partes.png"))
    if imagen is None or mapa is None or mapa.get_size() != imagen.get_size():
        return None
    try:
        with open(ruta_atlas(ruta), encoding="utf-8") as archivo:
            atlas = json.load(archivo)
        por_nombre = cuadros_por_nombre(atlas)
        animaciones = {nombre: ([_nombre_de(atlas, rect) for rect, _ in lista], [ms for _, ms in lista])
                       for nombre, lista in cuadros_de_atlas(atlas).items()}
    except (OSError, ValueError, KeyError):
        return None
    cuadros = {nombre: _pixeles_de(imagen, rect) for nombre, (rect, _) in por_nombre.items()}
    partes = {nombre: [[tinte_jugador.parte_de(c) for c in fila] for fila in _pixeles_de(mapa, rect)]
              for nombre, (rect, _) in por_nombre.items()}
    primero = "quieto" if "quieto" in cuadros else next(iter(cuadros))
    return {"cuadros": cuadros, "partes": partes, "animaciones": animaciones,
            "refs": tinte_jugador.referencias(cuadros[primero], partes[primero]), "primero": primero}


def _nombre_de(atlas, rect):
    """Nombre del cuadro del atlas que ocupa `rect`."""
    for nombre, (otro, _) in cuadros_por_nombre(atlas).items():
        if tuple(otro) == tuple(rect):
            return nombre
    raise KeyError(rect)


def _colores(apariencia):
    """Clave de caché de los colores de una apariencia."""
    return tuple(sorted(tinte_jugador.objetivos(apariencia).items()))


def _mezcla(rol, apariencia):
    """(cabeza, cuerpo) si la apariencia mezcla personajes (pestañas HAT y
    SKIN del vestidor), o None si el jugador es su propio personaje. Solo
    cuentan los personajes con hoja de Higgsfield (assets.ROLES_APARIENCIA)."""
    if apariencia is None or rol not in assets.ROLES_APARIENCIA:
        return None
    cabeza = apariencia.cabeza_para(rol)
    cuerpo = apariencia.traje_para(rol)
    if cabeza not in assets.ROLES_APARIENCIA:
        cabeza = rol
    if cuerpo not in assets.ROLES_APARIENCIA:
        cuerpo = rol
    return None if cabeza == cuerpo == rol else (cabeza, cuerpo)


_cache_mezclas = {}  # (cabeza, cuerpo) -> datos de la hoja mezclada (o None)


def _datos_de(rol, apariencia):
    """Los datos en píxeles del personaje que se dibuja: la hoja del rol o,
    si la apariencia mezcla cabeza y cuerpo, la hoja compuesta."""
    mezcla = _mezcla(rol, apariencia)
    if mezcla is None:
        return _datos_hoja(rol)
    if mezcla not in _cache_mezclas:
        _cache_mezclas[mezcla] = _componer_datos(*mezcla)
    return _cache_mezclas[mezcla]


def _componer_datos(cabeza, cuerpo):
    """Como _datos_hoja, pero cada cuadro del CUERPO con la cabeza de otro
    personaje (src/ui/mezcla_jugador.py). El cuerpo pone los cuadros, las
    animaciones y el accesorio."""
    datos_c, datos_t = _datos_hoja(cabeza), _datos_hoja(cuerpo)
    if datos_c is None or datos_t is None:
        return datos_t
    cuadros, partes = {}, {}
    for nombre in datos_t["cuadros"]:
        fuente = nombre if nombre in datos_c["cuadros"] else datos_c["primero"]
        cuadros[nombre], partes[nombre] = mezcla_jugador.componer(
            datos_c["cuadros"][fuente], datos_c["partes"][fuente], datos_t["cuadros"][nombre], datos_t["partes"][nombre])
    primero = datos_t["primero"]
    return {"cuadros": cuadros, "partes": partes, "animaciones": datos_t["animaciones"],
            "refs": tinte_jugador.referencias(cuadros[primero], partes[primero]), "primero": primero}


def _recordar(cache, clave, crear):
    if clave not in cache:
        if len(cache) >= MAX_HOJAS_VESTIDAS:
            del cache[next(iter(cache))]  # los dict guardan el orden de inserción
        cache[clave] = crear()
    return cache[clave]


def _cuadro_teñido(datos, nombre, elegidos):
    return tinte_jugador.teñir_cuadro(datos["cuadros"][nombre], datos["partes"][nombre], datos["refs"], elegidos)


def _hoja_vestida(rol, apariencia, escala):
    """Hoja del rol (o la mezcla de cabeza y cuerpo) teñida con los colores
    de `apariencia` (escala ya HD), o None."""
    def crear():
        datos = _datos_de(rol, apariencia)
        if datos is None:
            return None
        elegidos = tinte_jugador.objetivos(apariencia)
        teñidos = {}
        hoja = {}
        for animacion, (nombres, duraciones) in datos["animaciones"].items():
            superficies = []
            for nombre in nombres:
                if nombre not in teñidos:
                    teñidos[nombre] = _superficie_pixeles(_cuadro_teñido(datos, nombre, elegidos), escala)
                superficies.append(teñidos[nombre])
            hoja[animacion] = (superficies, duraciones)
        return hoja
    return _recordar(_cache_vestidos, (rol, _mezcla(rol, apariencia), _colores(apariencia), escala), crear)


def sprite_parte_jugador(simbolos, rol_fuente, piel=None, escala=assets.ESCALA_PIXEL, colores=None):
    """Vista previa de una parte para el vestidor: la mitad de arriba
    (assets.SIMBOLOS_CABEZA: pelo y cara) o la de abajo (SIMBOLOS_TRAJE:
    ropa, pantalón y zapatos) del personaje de `rol_fuente`, con la piel
    `piel` (un RGB de assets.TONOS_PIEL; None = la del dibujo) y los
    colores de `colores` (una Apariencia; None = los del dibujo). None si
    no hay hoja. Escala como la de sprite_jugador."""
    apariencia = colores or PREDETERMINADA
    if piel is not None and tuple(piel) in [tuple(t) for t in assets.TONOS_PIEL]:
        apariencia = apariencia.con("piel", [tuple(t) for t in assets.TONOS_PIEL].index(tuple(piel)))
    clave = (tuple(simbolos), rol_fuente, _colores(apariencia), escala)

    def crear():
        datos = _datos_hoja(rol_fuente)
        if datos is None:
            return None
        cuadro = _cuadro_teñido(datos, datos["primero"], tinte_jugador.objetivos(apariencia))
        alto = len(cuadro)
        corte = round(alto * assets.CORTE_CABEZA_JUGADOR)
        filas = cuadro[:corte] if tuple(simbolos) == tuple(assets.SIMBOLOS_CABEZA) else cuadro[corte:]
        ocupadas = [y for y, fila in enumerate(filas) if any(c is not None for c in fila)]
        if not ocupadas:
            return None
        return _superficie_pixeles(filas[ocupadas[0]:ocupadas[-1] + 1], escala_hd(escala))
    return _recordar(_cache_partes, clave, crear)


def _superficie_pixeles(pixeles, escala):
    """Cuadro armado (filas de RGB o None) -> Surface escalada."""
    alto, ancho = len(pixeles), len(pixeles[0])
    base = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y, fila in enumerate(pixeles):
        for x, color in enumerate(fila):
            if color is not None:
                base.set_at((x, y), color)
    return pygame.transform.scale(base, (ancho * escala, alto * escala))


def _cuadros_jefe_v2(animacion):
    """Cuadros del jefe con arte "enemigos 2.0" (`animacion` = "Idle" o
    "Walk"), o None si no está activado o falta el PNG."""
    if not assets.JEFE_V2:
        return None
    clave = ("jefe", animacion)
    if clave not in _cache_enemigos_v2:
        nombre = assets.JEFE_V2
        ruta = assets.ruta_tira_variante(nombre, animacion)
        _cache_enemigos_v2[clave] = _leer_tira_v2(ruta, assets.ESCALA_JEFE_V2)
    return _cache_enemigos_v2[clave]


def sprite_jefe(tiempo=0.0, furia=False, escala=assets.ESCALA_SPRITE_JEFE):
    """Cuadro del jefe para `tiempo` ("furia" en la última fase); sin hoja,
    el pixel art JEFE."""
    cuadros_v2 = _cuadros_jefe_v2("Walk" if furia else "Idle")
    if cuadros_v2:
        duracion = assets.DURACION_CUADRO_JEFE_V2_FURIA if furia else assets.DURACION_CUADRO_JEFE_V2
        return cuadros_v2[int(tiempo / duracion) % len(cuadros_v2)]
    hoja = _cargar_hoja(ruta_sprite(assets.ID_SPRITE_JEFE, assets.RUTA_SPRITES_JEFE), escala)
    if hoja is None:
        return sprite(JEFE, PALETA_JEFE, escala)
    animacion = assets.ANIMACION_JEFE_FURIA if furia else assets.ANIMACION_JEFE_IDLE
    return cuadro_de_hoja(hoja, animacion, tiempo)


_cache_retratos = {}


_cache_sombras = {}


def dibujar_sombra(pantalla, centro, ancho):
    """Sombra elíptica en el suelo: asienta personajes y objetos en el escenario."""
    if ancho not in _cache_sombras:
        alto = max(4, ancho // 3)
        sombra = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, assets.COLOR_SOMBRA_ENTIDAD, sombra.get_rect())
        _cache_sombras[ancho] = sombra
    pantalla.blit(_cache_sombras[ancho], _cache_sombras[ancho].get_rect(center=centro))


def retrato_rol(rol, alto, apariencia=None):
    """Ilustración grande del rol (assets/sprites/retratos/<rol>.png)
    escalada a `alto` px, o None si no existe: el que llama decide el
    fallback (normalmente sprite_jugador a escala grande). Con una
    `apariencia` que cambie colores, el retrato base del rol sale teñido
    con su mapa de partes (<rol>.partes.png); sin mapa, sin teñir."""
    if _mezcla(str(rol).split("_")[0], apariencia) is not None:
        return None  # cabeza y cuerpo de personajes distintos: no hay retrato así; el que llama usa sprite_jugador
    elegidos = tinte_jugador.objetivos(apariencia)
    if elegidos:
        base = str(rol).split("_")[0]
        clave = (base, alto, _colores(apariencia))
        return _recordar(_cache_retratos_vestidos, clave,
                         lambda: _retrato_teñido(base, alto, elegidos) or retrato_rol(base, alto))
    if (rol, alto) not in _cache_retratos:
        imagen = _cargar_png(ruta_sprite(rol, assets.RUTA_SPRITES_RETRATOS))
        if imagen is None and "_" in str(rol):
            # "periodista_preocupado" sin archivo: el retrato base del rol.
            imagen = _cargar_png(ruta_sprite(str(rol).split("_")[0], assets.RUTA_SPRITES_RETRATOS))
        if imagen is None and "_" in str(rol):
            # "periodista_preocupado" sin archivo: el retrato base del rol.
            imagen = _cargar_png(ruta_sprite(str(rol).split("_")[0], assets.RUTA_SPRITES_RETRATOS))
        if imagen is not None:
            ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
            imagen = pygame.transform.smoothscale(imagen, (ancho, alto))
        _cache_retratos[(rol, alto)] = imagen
    return _cache_retratos[(rol, alto)]


_cache_retratos_vestidos = {}  # (rol, alto, colores) -> Surface teñida


def _retrato_teñido(rol, alto, elegidos):
    """Retrato del rol a `alto` px con `elegidos` ({parte: RGB}) teñidos, o None."""
    imagen = _cargar_png(ruta_sprite(rol, assets.RUTA_SPRITES_RETRATOS))
    mapa = _cargar_png(os.path.join(assets.RUTA_SPRITES_RETRATOS, f"{rol}.partes.png"))
    if imagen is None or mapa is None or mapa.get_size() != imagen.get_size():
        return None
    ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
    imagen = pygame.transform.smoothscale(imagen, (ancho, alto))
    mapa = pygame.transform.scale(mapa, (ancho, alto))  # sin mezclar: cada píxel conserva su parte
    rect = (0, 0, ancho, alto)
    cuadro = _pixeles_de(imagen, rect)
    partes = [[tinte_jugador.parte_de(c) for c in fila] for fila in _pixeles_de(mapa, rect)]
    teñido = tinte_jugador.teñir_cuadro(cuadro, partes, tinte_jugador.referencias(cuadro, partes), elegidos)
    return _superficie_pixeles(teñido, 1)


_cache_enemigos = {}


def sprite_enemigo(tipo, frame=0, tiempo=None, variante=None, ataque_t=None, mirando_izquierda=False):
    """Única fuente de la imagen de un enemigo: todo el render la pide aquí
    (el combate y las tarjetas de instrucciones), así lo que se ve en una
    tarjeta es lo mismo que se ve peleando.

    Con `variante` (nombre de una variante de "enemigos 2.0") devuelve su
    cuadro de caminar o de ataque (`ataque_t`), volteado si mira a la
    izquierda; si esa variante no tiene arte, sigue como sin variante.

    `tipo` es un TipoEnemigo (o su valor "perseguidor"/"tirador"/
    "curandero"); None = el enemigo genérico original. Con `tiempo`
    (segundos, p. ej. enemigo.reloj) devuelve el cuadro de "caminar"
    que toca; `frame` se conserva por compatibilidad (índice fijo).

    Arte real: guardar `assets/sprites/enemigos/<id>.png`, con <id> =
    assets.ID_SPRITE_ENEMIGO[tipo] (p. ej. perseguidor.png). Si va con
    su <id>.atlas.json es una hoja de 16x16 por cuadro que se escala por
    ESCALA_PIXEL; sin atlas, es una imagen suelta de ~42x42 px. Si no
    existe o no se puede leer, se usa el pixel art de PIXEL_ART_ENEMIGO.
    No hay que tocar nada más del código.
    """
    if variante is not None:
        imagen = sprite_variante(variante, tiempo or 0.0, ataque_t, mirando_izquierda)
        if imagen is not None:
            return imagen
    if tipo is None:
        return sprite(ENEMIGO, PALETA_ENEMIGO)
    clave = getattr(tipo, "value", tipo)
    hoja =_cargar_hoja(ruta_sprite_enemigo(assets.ID_SPRITE_ENEMIGO[clave]), assets.ESCALA_PIXEL)
    if hoja is not None:
        superficies, duraciones = hoja.get(assets.ANIMACION_CAMINAR) or next(iter(hoja.values()))
        if tiempo is None:
            return superficies[frame % len(superficies)]
        return superficies[indice_por_tiempo(duraciones, tiempo)]
    if clave not in _cache_enemigos:
        _cache_enemigos[clave] = sprite(PIXEL_ART_ENEMIGO[clave], paleta_enemigo(clave))
    return _cache_enemigos[clave]


_cache_enemigos_v2 = {}


def _celdas_tira_v2(ruta):
    """Cuadros de 100x100 de una tira de "enemigos 2.0", o None si falta."""
    tira = _cargar_png(ruta)
    if tira is None:
        return None
    lado = assets.CUADRO_ENEMIGO_V2
    return [tira.subsurface((x, 0, lado, tira.get_height())) for x in range(0, tira.get_width(), lado)]


def _caja_comun(celdas):
    caja = celdas[0].get_bounding_rect()
    for celda in celdas[1:]:
        caja.union_ip(celda.get_bounding_rect())
    return caja


def _leer_tira_v2(ruta, escala):
    """Tira recortada a una caja común (así no vibra al animar) y escalada."""
    celdas = _celdas_tira_v2(ruta)
    if celdas is None:
        return None
    caja = _caja_comun(celdas)
    return [pygame.transform.scale(c.subsurface(caja), (caja.w * escala, caja.h * escala)) for c in celdas]


def _leer_variante(nombre):
    """{"mover": [...], "ataque": [...]} de la variante, o None sin arte.

    Los cuadros de las dos tiras se recortan con la MISMA caja, centrada en
    la del movimiento: así el cuerpo no salta al empezar a atacar y, al
    dibujar centrado en el rect del enemigo, el personaje queda donde
    estaba al caminar."""
    arte = assets.ARTE_VARIANTE.get(nombre)
    if arte is None:
        return None
    mover = _celdas_tira_v2(assets.ruta_tira_variante(nombre, arte["tira_mov"]))
    ataque = _celdas_tira_v2(assets.ruta_tira_variante(nombre, arte["tira_ataque"]))
    if mover is None or ataque is None:
        return None
    caja_mov = _caja_comun(mover)
    caja = caja_mov.union(_caja_comun(ataque))
    cx, cy = caja_mov.center
    mitad_x = max(cx - caja.left, caja.right - cx)
    mitad_y = max(cy - caja.top, caja.bottom - cy)
    escala = arte["escala"]

    def recortado(celda):
        lienzo = pygame.Surface((2 * mitad_x, 2 * mitad_y), pygame.SRCALPHA)
        lienzo.blit(celda, (mitad_x - cx, mitad_y - cy))
        return pygame.transform.scale(lienzo, (lienzo.get_width() * escala, lienzo.get_height() * escala))

    mover = [recortado(c) for c in mover]
    ataque = [recortado(c) for c in ataque]
    return {
        "mover": mover, "ataque": ataque,
        "mover_izq": [pygame.transform.flip(c, True, False) for c in mover],
        "ataque_izq": [pygame.transform.flip(c, True, False) for c in ataque],
    }


def sprite_variante(nombre, tiempo=0.0, ataque_t=None, mirando_izquierda=False):
    """Cuadro de la variante `nombre`: el de su tira de ataque según
    `ataque_t` (segundos desde que empezó el ataque; None = no ataca) o el
    de caminar según `tiempo`. Volteado si mira a la izquierda; None si
    la variante no tiene arte."""
    if nombre not in _cache_enemigos_v2:
        _cache_enemigos_v2[nombre] = _leer_variante(nombre)
    cuadros = _cache_enemigos_v2[nombre]
    if cuadros is None:
        return None
    sufijo = "_izq" if mirando_izquierda else ""
    if ataque_t is not None:
        lista = cuadros["ataque" + sufijo]
        return lista[min(len(lista) - 1, int(ataque_t / balance.DURACION_CUADRO_ATAQUE_S))]
    lista = cuadros["mover" + sufijo]
    return lista[int(tiempo / assets.DURACION_CUADRO_ENEMIGO_V2) % len(lista)]


def limpiar_cache_enemigos():
    """Olvida las imágenes cargadas (p. ej. tras copiar arte nuevo)."""
    _cache_enemigos_v2.clear()
    limpiar_cache_hojas()


def _cargar_png(ruta):
    """Surface del PNG en `ruta`, o None si no hay ruta o no se pudo leer."""
    if ruta is None:
        return None
    try:
        imagen = pygame.image.load(ruta)
    except (pygame.error, FileNotFoundError):
        return None
    if pygame.display.get_surface() is not None:
        imagen = imagen.convert_alpha()
    return imagen


def dibujar_centrado(pantalla, superficie, centro):
    pantalla.blit(superficie, superficie.get_rect(center=centro))


_cache_fondos = {}


def fondo_historia(nombre, tamanio=None):
    """Ilustración de assets/story/<nombre>.png escalada a `tamanio`
    (por defecto, tal cual), o None si no existe: quien la pide dibuja
    su fondo de siempre."""
    clave = (nombre, tamanio)
    if clave not in _cache_fondos:
        imagen = _cargar_png(ruta_sprite(nombre, assets.RUTA_FONDOS_HISTORIA))
        if imagen is not None and tamanio is not None and imagen.get_size() != tuple(tamanio):
            imagen = pygame.transform.smoothscale(imagen, tamanio)
        _cache_fondos[clave] = imagen
    return _cache_fondos[clave]
