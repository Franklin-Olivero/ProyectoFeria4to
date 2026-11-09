"""Piezas de un celular dibujadas con primitivas (solo presentación).

La terminal de decisión se ve como dos capturas de la app Civitas
(src/ui/terminal_decision_render.py). Aquí vive lo que la hace parecer un
celular: el cuerpo con la pantalla, la barra de estado (hora, señal, wifi
y batería), los iconos de la app, los avatares redondos y los recortes de
las ilustraciones que se usan como fotos. Todo sale de pygame.draw o de
arte que ya existe (retratos de assets/sprites/retratos e ilustraciones de
assets/story): no hay imágenes nuevas.

Los colores se leen de src/core/assets.py en cada dibujo (así funcionan
las preferencias de color); solo se cachean las superficies caras: el
cuerpo del celular, el velo, los recortes de ilustraciones y los retratos
redondos, con los colores dentro de la clave.
"""

import math
import unicodedata

import pygame

from src.core import assets
from src.ui import dibujo, sprites

# Icono de cada opción del árbol, por su etiqueta sin tildes y en minúsculas.
ICONO_POR_OPCION = {
    "verificar": "lupa",
    "me gusta": "corazon",
    "compartir": "compartir",
    "reportar": "bandera",
    "ignorar": "saltar",
}
ICONO_GENERICO = "puntos"  # cualquier otra opción: los tres puntos de "más opciones"

_cache_cuerpos = {}
_cache_velos = {}
_cache_fotos = {}
_cache_retratos = {}


def normalizar(texto):
    """Minúsculas, sin tildes ni espacios de sobra: "  Me GUSTÁ " -> "me gusta"."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(sin_tildes.lower().split())


def icono_para(etiqueta):
    """Nombre del icono de una opción: "Verificar" -> "lupa", "Me gusta" ->
    "corazon", "Compartir" -> "compartir", "Reportar" -> "bandera", "Ignorar"
    -> "saltar"; una etiqueta que empieza con uno de esos verbos usa el mismo
    icono y cualquier otra, el genérico (tres puntos)."""
    clave = normalizar(etiqueta)
    if clave in ICONO_POR_OPCION:
        return ICONO_POR_OPCION[clave]
    for verbo, nombre in ICONO_POR_OPCION.items():
        if clave.startswith(verbo + " "):
            return nombre
    return ICONO_GENERICO


def iniciales(usuario):
    """Dos letras para el avatar: "@MamasNovaUnidas" -> "MN", "@eco" -> "EC"."""
    letras = [c for c in str(usuario) if c.isalpha()]
    mayusculas = [c for c in letras if c.isupper()]
    if len(mayusculas) >= 2:
        return "".join(mayusculas[:2])
    return "".join(letras[:2]).upper() or "?"


# ----------------------------------------------------------------------
# Cuerpo, barra de estado y velo
# ----------------------------------------------------------------------


def rect_pantalla(rect):
    """Pantalla encendida dentro del cuerpo del celular `rect`."""
    grosor = assets.GROSOR_MARCO_CELULAR
    return pygame.Rect(rect).inflate(-2 * grosor, -2 * grosor)


def dibujar_celular(pantalla, rect):
    """Cuerpo del celular (canto con degradado violeta, botones laterales y
    pantalla oscura). Retorna el rect de la pantalla. Cacheado por tamaño y colores."""
    rect = pygame.Rect(rect)
    arriba, abajo = assets.COLOR_MARCO_CELULAR_ARRIBA, assets.COLOR_MARCO_CELULAR_ABAJO
    clave = (rect.size, arriba, abajo, assets.COLOR_PANTALLA_CELULAR, assets.COLOR_BOTON_LATERAL_CELULAR)
    superficie = _cache_cuerpos.get(clave)
    if superficie is None:
        superficie = _cuerpo(rect.size, arriba, abajo)
        if len(_cache_cuerpos) > 16:
            _cache_cuerpos.clear()
        _cache_cuerpos[clave] = superficie
    lateral = assets.SALIENTE_BOTON_CELULAR
    # Botones laterales: asoman unos píxeles por fuera del cuerpo.
    for x, y, alto in ((rect.left - lateral, rect.top + 120, 34), (rect.left - lateral, rect.top + 166, 54),
                       (rect.right - 2, rect.top + 140, 70)):
        pygame.draw.rect(pantalla, assets.COLOR_BOTON_LATERAL_CELULAR, (x, y, lateral + 2, alto), border_radius=2)
    pantalla.blit(superficie, rect.topleft)
    return rect_pantalla(rect)


def _cuerpo(tamanio, arriba, abajo):
    ancho, alto = tamanio
    radio = assets.RADIO_CELULAR
    superficie = pygame.Surface(tamanio, pygame.SRCALPHA)
    for y in range(alto):
        t = y / max(1, alto - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo))
        pygame.draw.line(superficie, color, (0, y), (ancho, y))
    forma = pygame.Surface(tamanio, pygame.SRCALPHA)
    pygame.draw.rect(forma, (255, 255, 255, 255), forma.get_rect(), border_radius=radio)
    superficie.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    grosor = assets.GROSOR_MARCO_CELULAR
    interior = superficie.get_rect().inflate(-2 * grosor, -2 * grosor)
    pygame.draw.rect(superficie, assets.COLOR_PANTALLA_CELULAR, interior, border_radius=radio - grosor)
    return superficie


def velo_pantalla(pantalla, rect_pantalla_celular, color_rgba):
    """Oscurece la pantalla del celular respetando sus esquinas redondeadas."""
    rect = pygame.Rect(rect_pantalla_celular)
    radio = assets.RADIO_CELULAR - assets.GROSOR_MARCO_CELULAR
    clave = (rect.size, tuple(color_rgba), radio)
    capa = _cache_velos.get(clave)
    if capa is None:
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(capa, color_rgba, capa.get_rect(), border_radius=radio)
        if len(_cache_velos) > 16:
            _cache_velos.clear()
        _cache_velos[clave] = capa
    pantalla.blit(capa, rect.topleft)


def dibujar_barra_estado(pantalla, rect_pantalla_celular, bateria=1.0, color_bateria=None):
    """Barra de estado: hora a la izquierda, la isla de la cámara al centro y
    señal, wifi y batería a la derecha. `bateria` (0-1) llena la pila."""
    rect = pygame.Rect(rect_pantalla_celular)
    alto = assets.ALTO_BARRA_ESTADO_CELULAR
    centro_y = rect.top + alto // 2 + 2
    color = assets.COLOR_TEXTO_HUD
    dibujo.texto(pantalla, assets.HORA_CELULAR, (rect.left + 26, centro_y), color, assets.TAMANIO_FUENTE_PEQUENA,
                 negrita=True, ancla="midleft")
    isla = pygame.Rect(0, 0, assets.ANCHO_ISLA_CELULAR, 18)
    isla.center = (rect.centerx, centro_y)
    pygame.draw.rect(pantalla, assets.COLOR_ISLA_CELULAR, isla, border_radius=9)
    # Pila: contorno, borne y relleno según `bateria`.
    pila = pygame.Rect(0, 0, 22, 11)
    pila.midright = (rect.right - 26, centro_y)
    pygame.draw.rect(pantalla, color, pila, 1, border_radius=3)
    pygame.draw.rect(pantalla, color, (pila.right, pila.centery - 2, 2, 4))
    lleno = max(0.0, min(1.0, bateria))
    if lleno > 0:
        pygame.draw.rect(pantalla, color_bateria or color, (pila.left + 2, pila.top + 2, max(1, round((pila.width - 4) * lleno)),
                                                            pila.height - 4), border_radius=1)
    _wifi(pantalla, (pila.left - 15, centro_y + 5), color)
    _senal(pantalla, (pila.left - 46, centro_y + 5), color)
    return pygame.Rect(rect.left, rect.top, rect.width, alto)


def _senal(pantalla, base_izquierda, color):
    x, y = base_izquierda
    for i in range(4):
        alto = 3 + i * 2
        pygame.draw.rect(pantalla, color, (x + i * 4, y - alto, 3, alto), border_radius=1)


def _wifi(pantalla, punto, color):
    x, y = punto
    pygame.draw.circle(pantalla, color, (x, y - 1), 2)
    for radio in (5, 9):
        caja = pygame.Rect(0, 0, radio * 2, radio * 2)
        caja.center = (x, y)
        pygame.draw.arc(pantalla, color, caja, math.radians(45), math.radians(135), 2)


def indicador_inicio(pantalla, rect_pantalla_celular, color=None):
    """La rayita de "ir al inicio" abajo de la pantalla."""
    rect = pygame.Rect(rect_pantalla_celular)
    barra = pygame.Rect(0, 0, 108, 4)
    barra.midbottom = (rect.centerx, rect.bottom - 6)
    pygame.draw.rect(pantalla, color or assets.COLOR_TEXTO_SECUNDARIO, barra, border_radius=2)


# ----------------------------------------------------------------------
# Iconos (todos en una caja de `tamanio` x `tamanio` centrada en `centro`)
# ----------------------------------------------------------------------


def _p(centro, tamanio, x, y):
    return round(centro[0] + x * tamanio), round(centro[1] + y * tamanio)


def _puntos(centro, tamanio, pares):
    return [_p(centro, tamanio, x, y) for x, y in pares]


def _corazon(centro, tamanio):
    """Contorno de corazón (curva clásica 16 sen³t), escalado a la caja."""
    puntos = []
    escala = 0.46 / 16
    for i in range(36):
        t = 2 * math.pi * i / 36
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        puntos.append(_p(centro, tamanio, x * escala, (y - 2.5) * escala))
    return puntos


def dibujar_icono(pantalla, nombre, centro, tamanio, color, grosor=2):
    """Icono de línea dibujado con primitivas. Un nombre desconocido dibuja el genérico."""
    c, s, g = centro, tamanio, grosor
    if nombre == "lupa":
        pygame.draw.circle(pantalla, color, _p(c, s, -0.08, -0.08), round(s * 0.29), g)
        pygame.draw.line(pantalla, color, _p(c, s, 0.13, 0.13), _p(c, s, 0.40, 0.40), g + 1)
    elif nombre == "corazon":
        pygame.draw.polygon(pantalla, color, _corazon(c, s), g)
    elif nombre == "compartir":
        # Dos flechas que se persiguen: arriba va a la derecha, abajo a la izquierda.
        pygame.draw.lines(pantalla, color, False, _puntos(c, s, ((-0.36, 0.10), (-0.36, -0.20), (0.18, -0.20))), g)
        pygame.draw.polygon(pantalla, color, _puntos(c, s, ((0.42, -0.20), (0.16, -0.36), (0.16, -0.04))))
        pygame.draw.lines(pantalla, color, False, _puntos(c, s, ((0.36, -0.10), (0.36, 0.20), (-0.18, 0.20))), g)
        pygame.draw.polygon(pantalla, color, _puntos(c, s, ((-0.42, 0.20), (-0.16, 0.04), (-0.16, 0.36))))
    elif nombre == "bandera":
        pygame.draw.line(pantalla, color, _p(c, s, -0.30, -0.42), _p(c, s, -0.30, 0.44), g)
        tela = ((-0.30, -0.38), (-0.04, -0.30), (0.16, -0.38), (0.38, -0.32), (0.38, 0.06), (0.16, 0.0),
                (-0.04, 0.08), (-0.30, 0.02))
        pygame.draw.polygon(pantalla, color, _puntos(c, s, tela), g)
    elif nombre == "saltar":
        # Doble flecha hacia abajo: seguir bajando por el feed sin hacer nada.
        for dy in (-0.24, 0.04):
            pygame.draw.lines(pantalla, color, False, _puntos(c, s, ((-0.30, dy), (0.0, dy + 0.24), (0.30, dy))), g + 1)
    elif nombre == "mas":
        caja = pygame.Rect(0, 0, round(s * 0.8), round(s * 0.8))
        caja.center = c
        pygame.draw.rect(pantalla, color, caja, g, border_radius=max(2, round(s * 0.2)))
        pygame.draw.line(pantalla, color, _p(c, s, -0.2, 0), _p(c, s, 0.2, 0), g)
        pygame.draw.line(pantalla, color, _p(c, s, 0, -0.2), _p(c, s, 0, 0.2), g)
    elif nombre == "campana":
        domo = ((-0.30, 0.22), (-0.26, -0.06), (-0.18, -0.28), (0.0, -0.36), (0.18, -0.28), (0.26, -0.06), (0.30, 0.22))
        pygame.draw.lines(pantalla, color, False, _puntos(c, s, domo), g)
        pygame.draw.line(pantalla, color, _p(c, s, -0.40, 0.22), _p(c, s, 0.40, 0.22), g)
        pygame.draw.circle(pantalla, color, _p(c, s, 0, 0.34), max(2, round(s * 0.08)))
    elif nombre == "inicio":
        casa = ((-0.36, -0.02), (0.0, -0.38), (0.36, -0.02), (0.36, 0.38), (-0.36, 0.38))
        pygame.draw.polygon(pantalla, color, _puntos(c, s, casa), g)
    elif nombre == "videos":
        caja = pygame.Rect(0, 0, round(s * 0.8), round(s * 0.8))
        caja.center = c
        pygame.draw.rect(pantalla, color, caja, g, border_radius=max(2, round(s * 0.2)))
        pygame.draw.polygon(pantalla, color, _puntos(c, s, ((-0.10, -0.16), (0.18, 0.0), (-0.10, 0.16))))
    elif nombre == "perfil":
        pygame.draw.circle(pantalla, color, c, round(s * 0.42), g)
        pygame.draw.circle(pantalla, color, _p(c, s, 0, -0.10), round(s * 0.13), g)
        hombros = pygame.Rect(0, 0, round(s * 0.52), round(s * 0.40))
        hombros.midtop = _p(c, s, 0, 0.10)
        pygame.draw.arc(pantalla, color, hombros, math.radians(20), math.radians(160), g)
    elif nombre == "menu":
        for dy in (-0.26, 0.0, 0.26):
            pygame.draw.line(pantalla, color, _p(c, s, -0.36, dy), _p(c, s, 0.36, dy), g)
    elif nombre == "candado":
        # Arco arriba y cuerpo macizo: se lee como candado aun a 16 px.
        arco = pygame.Rect(0, 0, round(s * 0.50), round(s * 0.56))
        arco.midtop = _p(c, s, 0, -0.44)
        pygame.draw.rect(pantalla, color, arco, g, border_radius=round(s * 0.25))
        cuerpo = pygame.Rect(0, 0, round(s * 0.76), round(s * 0.52))
        cuerpo.midtop = _p(c, s, 0, -0.06)
        pygame.draw.rect(pantalla, color, cuerpo, border_radius=2)
    elif nombre == "alerta":
        pygame.draw.polygon(pantalla, color, _puntos(c, s, ((0.0, -0.40), (0.42, 0.36), (-0.42, 0.36))), g)
        pygame.draw.line(pantalla, color, _p(c, s, 0, -0.14), _p(c, s, 0, 0.10), g)
        pygame.draw.circle(pantalla, color, _p(c, s, 0, 0.22), max(1, g - 1))
    elif nombre == "info":
        pygame.draw.circle(pantalla, color, c, round(s * 0.42), g)
        pygame.draw.line(pantalla, color, _p(c, s, 0, -0.04), _p(c, s, 0, 0.24), g)
        pygame.draw.circle(pantalla, color, _p(c, s, 0, -0.20), max(1, g - 1))
    elif nombre == "chevron_derecha":
        pygame.draw.lines(pantalla, color, False, _puntos(c, s, ((-0.14, -0.30), (0.16, 0.0), (-0.14, 0.30))), g)
    elif nombre == "chevron_abajo":
        pygame.draw.lines(pantalla, color, False, _puntos(c, s, ((-0.26, -0.12), (0.0, 0.14), (0.26, -0.12))), g)
    elif nombre == "capturas":
        caja = pygame.Rect(0, 0, round(s * 0.56), round(s * 0.80))
        caja.center = c
        pygame.draw.rect(pantalla, color, caja, g, border_radius=3)
        pygame.draw.line(pantalla, color, (caja.left + 3, caja.bottom - 5), (caja.right - 4, caja.bottom - 5), 1)
    else:  # "puntos" y cualquier otro: tres puntos
        for dx in (-0.28, 0.0, 0.28):
            pygame.draw.circle(pantalla, color, _p(c, s, dx, 0), max(2, round(s * 0.08)))


# ----------------------------------------------------------------------
# Avatares
# ----------------------------------------------------------------------


def avatar_iniciales(pantalla, centro, radio, usuario, anillo=True):
    """Avatar redondo con las iniciales de la cuenta y, si `anillo`, el aro
    violeta de las historias de Civitas. Retorna el rect ocupado."""
    if anillo:
        pygame.draw.circle(pantalla, assets.COLOR_CIVITAS, centro, radio + 4, 2)
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_AVATAR_POST, centro, radio)
    tamanio = max(assets.TAMANIO_FUENTE_CELULAR_MINIMA, round(radio * 0.75))
    dibujo.texto(pantalla, iniciales(usuario), centro, assets.COLOR_TEXTO_HUD, tamanio, negrita=True, ancla="center")
    extra = 4 if anillo else 0
    return pygame.Rect(centro[0] - radio - extra, centro[1] - radio - extra, 2 * (radio + extra), 2 * (radio + extra))


def retrato_redondo(rol, diametro, recorte):
    """Cara del retrato `rol` (assets/sprites/retratos) recortada en un
    círculo de `diametro` px, o None si no hay retrato. `recorte` = (centro x
    en fracción del ancho, centro y y lado en fracción del alto)."""
    clave = (rol, diametro, tuple(recorte))
    if clave not in _cache_retratos:
        cx, cy, lado = recorte
        alto = max(1, round(diametro / lado))
        imagen = sprites.retrato_rol(rol, alto)
        circulo = None
        if imagen is not None:
            caja = pygame.Rect(0, 0, diametro, diametro)
            caja.center = (round(imagen.get_width() * cx), round(alto * cy))
            caja = caja.clamp(imagen.get_rect())
            circulo = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
            pygame.draw.circle(circulo, assets.COLOR_FONDO_AVATAR_POST, (diametro // 2, diametro // 2), diametro // 2)
            circulo.blit(imagen, (0, 0), caja.clip(imagen.get_rect()))
            mascara = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
            pygame.draw.circle(mascara, (255, 255, 255, 255), (diametro // 2, diametro // 2), diametro // 2)
            circulo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        _cache_retratos[clave] = circulo
    return _cache_retratos[clave]


# ----------------------------------------------------------------------
# Fotos: recorte de una ilustración existente (o una ciudad de respaldo)
# ----------------------------------------------------------------------


def foto_recortada(nombre, recorte, tamanio):
    """La ilustración assets/story/<nombre>.png recortada en `recorte`
    (x, y, ancho, alto; None = completa) y escalada para CUBRIR `tamanio`
    sin deformarse. Si falta el archivo, una ciudad de noche dibujada en
    código. Cacheada por nombre, recorte y tamaño."""
    tamanio = (max(1, int(tamanio[0])), max(1, int(tamanio[1])))
    clave = (nombre, tuple(recorte) if recorte else None, tamanio)
    if clave not in _cache_fotos:
        imagen = sprites.fondo_historia(nombre) if nombre else None
        if imagen is None:
            foto = _ciudad_de_respaldo(tamanio)
        else:
            fuente = pygame.Rect(recorte) if recorte else imagen.get_rect()
            fuente = fuente.clip(imagen.get_rect()) or imagen.get_rect()
            fuente = _ajustar_aspecto(fuente, tamanio[0] / tamanio[1]).clamp(imagen.get_rect())
            foto = pygame.transform.smoothscale(imagen.subsurface(fuente.clip(imagen.get_rect())), tamanio)
        if len(_cache_fotos) > 24:
            _cache_fotos.clear()
        _cache_fotos[clave] = foto
    return _cache_fotos[clave]


def _ajustar_aspecto(rect, aspecto):
    """El rect más grande con la proporción `aspecto` centrado dentro de `rect`."""
    if rect.width / rect.height > aspecto:
        ancho = max(1, round(rect.height * aspecto))
        return pygame.Rect(rect.centerx - ancho // 2, rect.top, ancho, rect.height)
    alto = max(1, round(rect.width / aspecto))
    return pygame.Rect(rect.left, rect.centery - alto // 2, rect.width, alto)


def _ciudad_de_respaldo(tamanio):
    """Cielo con degradado y siluetas de edificios con ventanas encendidas."""
    ancho, alto = tamanio
    foto = pygame.Surface(tamanio)
    arriba, abajo = assets.COLOR_CIELO_ARRIBA, assets.COLOR_CIELO_HORIZONTE
    for y in range(alto):
        t = y / max(1, alto - 1)
        pygame.draw.line(foto, tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo)), (0, y), (ancho, y))
    x, i = 0, 0
    while x < ancho:
        ancho_edificio = 26 + (i * 17) % 30
        alto_edificio = round(alto * (0.35 + ((i * 37) % 40) / 100))
        edificio = pygame.Rect(x, alto - alto_edificio, ancho_edificio - 4, alto_edificio)
        pygame.draw.rect(foto, assets.COLOR_MURO_CASA, edificio)
        for vy in range(edificio.top + 8, alto - 6, 12):
            for vx in range(edificio.left + 5, edificio.right - 5, 9):
                if (vx * 7 + vy * 3 + i) % 5 == 0:
                    pygame.draw.rect(foto, assets.COLOR_VENTANA_ENCENDIDA, (vx, vy, 4, 5))
        x += ancho_edificio
        i += 1
    return foto
