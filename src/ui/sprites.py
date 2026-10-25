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

import pygame

from src.core import assets
from src.ui.ruta_sprites import ruta_sprite_enemigo

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


def sprite_jugador(color_rol, escala=assets.ESCALA_PIXEL):
    return sprite(JUGADOR, {**PALETA_JUGADOR, "c": color_rol}, escala)


_cache_enemigos = {}


def sprite_enemigo(tipo, frame=0):
    """Única fuente de la imagen de un enemigo: todo el render la pide aquí.

    `tipo` es un TipoEnemigo (o su valor "perseguidor"/"tirador"/
    "curandero"); None = el enemigo genérico original. `frame` queda
    para animaciones futuras (hoy cada tipo tiene un solo cuadro).

    Arte real: guardar `assets/sprites/enemigos/<id>.png`, con <id> =
    assets.ID_SPRITE_ENEMIGO[tipo] (p. ej. perseguidor.png), con fondo
    transparente y ~42x42 px (el tamaño del placeholder). Si el archivo
    existe se carga una vez y se cachea; si no existe o no se puede
    leer, se usa el pixel art de PIXEL_ART_ENEMIGO. No hay que tocar
    nada más del código.
    """
    if tipo is None:
        return sprite(ENEMIGO, PALETA_ENEMIGO)
    clave = getattr(tipo, "value", tipo)
    if (clave, frame) not in _cache_enemigos:
        imagen = _cargar_png(ruta_sprite_enemigo(assets.ID_SPRITE_ENEMIGO[clave]))
        if imagen is None:
            imagen = sprite(PIXEL_ART_ENEMIGO[clave], paleta_enemigo(clave))
        _cache_enemigos[(clave, frame)] = imagen
    return _cache_enemigos[(clave, frame)]


def limpiar_cache_enemigos():
    """Olvida las imágenes cargadas (p. ej. tras copiar arte nuevo)."""
    _cache_enemigos.clear()


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
