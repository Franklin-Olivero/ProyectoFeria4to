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

from src.core import assets
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


def sprite_jugador(color_rol, escala=assets.ESCALA_PIXEL, rol=None, tiempo=0.0,
                   caminando=False, dash=False):
    """Imagen del jugador. Con `rol` (clave de STATS_POR_ROL) y su hoja en
    assets/sprites/jugadores/<rol>.png devuelve el cuadro de "caminar"
    para `tiempo` (quieto = primer cuadro) o el de "dash"; sin hoja, el
    muñeco dibujado en código teñido con `color_rol`."""
    hoja = _cargar_hoja(ruta_sprite(rol, assets.RUTA_SPRITES_JUGADORES), escala) if rol else None
    if hoja is None:
        return sprite(JUGADOR, {**PALETA_JUGADOR, "c": color_rol}, escala)
    if dash and assets.ANIMACION_DASH in hoja:
        return cuadro_de_hoja(hoja, assets.ANIMACION_DASH, 0.0)
    return cuadro_de_hoja(hoja, assets.ANIMACION_CAMINAR, tiempo if caminando else 0.0)


def sprite_jefe(tiempo=0.0, furia=False, escala=assets.ESCALA_SPRITE_JEFE):
    """Cuadro del jefe para `tiempo` ("furia" en la última fase); sin hoja,
    el pixel art JEFE."""
    hoja = _cargar_hoja(ruta_sprite(assets.ID_SPRITE_JEFE, assets.RUTA_SPRITES_JEFE), escala)
    if hoja is None:
        return sprite(JEFE, PALETA_JEFE, escala)
    animacion = assets.ANIMACION_JEFE_FURIA if furia else assets.ANIMACION_JEFE_IDLE
    return cuadro_de_hoja(hoja, animacion, tiempo)


_cache_retratos = {}


def retrato_rol(rol, alto):
    """Ilustración grande del rol (assets/sprites/retratos/<rol>.png)
    escalada a `alto` px, o None si no existe: el que llama decide el
    fallback (normalmente sprite_jugador a escala grande)."""
    if (rol, alto) not in _cache_retratos:
        imagen = _cargar_png(ruta_sprite(rol, assets.RUTA_SPRITES_RETRATOS))
        if imagen is not None:
            ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
            imagen = pygame.transform.smoothscale(imagen, (ancho, alto))
        _cache_retratos[(rol, alto)] = imagen
    return _cache_retratos[(rol, alto)]


_cache_enemigos = {}


def sprite_enemigo(tipo, frame=0, tiempo=None):
    """Única fuente de la imagen de un enemigo: todo el render la pide aquí.

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
    if tipo is None:
        return sprite(ENEMIGO, PALETA_ENEMIGO)
    clave = getattr(tipo, "value", tipo)
    cuadros_v2 = _cuadros_enemigo_v2(clave)
    if cuadros_v2:
        if tiempo is None:
            return cuadros_v2[frame % len(cuadros_v2)]
        return cuadros_v2[int(tiempo / assets.DURACION_CUADRO_ENEMIGO_V2) % len(cuadros_v2)]
    hoja = _cargar_hoja(ruta_sprite_enemigo(assets.ID_SPRITE_ENEMIGO[clave]), assets.ESCALA_PIXEL)
    if hoja is not None:
        superficies, duraciones = hoja.get(assets.ANIMACION_CAMINAR) or next(iter(hoja.values()))
        if tiempo is None:
            return superficies[frame % len(superficies)]
        return superficies[indice_por_tiempo(duraciones, tiempo)]
    if clave not in _cache_enemigos:
        _cache_enemigos[clave] = sprite(PIXEL_ART_ENEMIGO[clave], paleta_enemigo(clave))
    return _cache_enemigos[clave]


_cache_enemigos_v2 = {}


def _cuadros_enemigo_v2(clave):
    """Cuadros de la tira Walk de "enemigos 2.0" para el tipo `clave`,
    recortados a una caja común (así no vibra al animar) y escalados;
    None si el tipo no usa el arte nuevo o falta el PNG."""
    nombre = assets.ENEMIGO_V2.get(clave)
    if nombre is None:
        return None
    if clave not in _cache_enemigos_v2:
        ruta = os.path.join(assets.RUTA_SPRITES_ENEMIGOS_V2, nombre, nombre, f"{nombre}_Walk.png")
        _cache_enemigos_v2[clave] = _leer_tira_v2(ruta)
    return _cache_enemigos_v2[clave]


def _leer_tira_v2(ruta):
    tira = _cargar_png(ruta)
    if tira is None:
        return None
    lado = assets.CUADRO_ENEMIGO_V2
    cuadros = [tira.subsurface((x, 0, lado, tira.get_height())) for x in range(0, tira.get_width(), lado)]
    caja = cuadros[0].get_bounding_rect()
    for cuadro in cuadros[1:]:
        caja.union_ip(cuadro.get_bounding_rect())
    escala = assets.ESCALA_ENEMIGO_V2
    return [pygame.transform.scale(c.subsurface(caja), (caja.w * escala, caja.h * escala)) for c in cuadros]


def limpiar_cache_enemigos():
    _cache_enemigos_v2.clear()
    """Olvida las imágenes cargadas (p. ej. tras copiar arte nuevo)."""
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
