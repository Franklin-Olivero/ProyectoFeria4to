"""Celular del modo Online: dibujo y ratón (solo presentación).

Mismo lenguaje visual que la terminal tipo celular
(src/ui/terminal_decision_render.py): el cuerpo con canto violeta, la isla, la
barra de estado, los iconos, los avatares y las fotos salen de
src/ui/celular_render.py; el logo es el mismo pixel art del menú
(sprites.palabra_titulo) y los muñecos del chat son los de la partida
(sprites.sprite_jugador, con la ropa de los vestidores). No hay imágenes nuevas.

    dibujar_boton    el botón CELULAR (grande en la partida, píldora en la
                     sala) con la insignia roja de mensajes sin leer.
    dibujar_aviso    el globo del mensaje entrante con el celular cerrado.
    dibujar_celular  el celular abierto: barra de estado, barra de la app,
                     pestañas Inicio / Chat y su contenido desplazable.
    objetivo_en      qué hay bajo el ratón (la fachada decide qué hacer).
    controles        la barra de controles con el celular abierto.

Pantalla del celular, de arriba abajo: barra de estado (28) -> barra de la app
(40: cerrar, logo, "EN VIVO") -> pestañas (36) -> franja ámbar si el personaje
sigue en la mazmorra -> contenido con recorte (set_clip) y desplazamiento ->
indicador de inicio.

Animaciones sin estado: el banner de notificación, el mensaje en vivo que sube
y el último comentario que entra se calculan con la EDAD de cada cosa en el
reloj del feed (`segundos` menos su instante): no hay que recordar nada entre
cuadros y todas las PCs las ven igual. Solo el "+N" de las cifras usa
Celular.notar_cifra, porque necesita el valor anterior.

Rendimiento (el celular abierto cuesta pocos ms por cuadro): se cachea todo
lo caro, cada texto renderizado (por cadena, tamaño y color), las líneas
partidas (por texto, ancho y tamaño), los avatares, las fotos redondeadas, la
sombra y el fondo del botón; las tarjetas que no se ven no se dibujan.

Ningún texto se sale de su caja: una línea baja de tamaño y luego se recorta
con "…" (como layout.texto_en_ancho) y un párrafo se parte por palabras (y por
letras si una palabra sola no entra) con tope de líneas. `dibujar_celular`
devuelve un DibujoCelular con lo clicable y cada texto con su caja permitida,
para el ratón y para los tests de layout.
"""

import math
import zlib
from dataclasses import dataclass, field

import pygame

from Online.celular import CHAT, DETALLE, FEED, Perfil, formatear_cifra
from src.core import assets
from src.ui import celular_render, dibujo, sprites
from src.ui.fuentes import fuente

# ----------------------------------------------------------------------
# Acciones del ratón (objetivo_en) y tecla del botón
# ----------------------------------------------------------------------
FUERA = "fuera"
DENTRO = "dentro"
CERRAR = "cerrar"
PESTANA = "pestana"
ENVIAR = "enviar"
ENTRADA = "entrada"
RESPUESTA = "respuesta"
ME_GUSTA = "me_gusta"
NUEVAS = "nuevas"
COMPARTIR = "compartir"  # repost propio
ABRIR = "abrir"  # abrir una publicación con todos sus comentarios
VOLVER = "volver"  # de la publicación abierta al feed
TECLA_BOTON = "C"

# Tipos de mensaje del chat: los mismos valores que Online/chat_celular.py.
MENSAJE_JUGADOR = "jugador"
MENSAJE_ENTRO = "entro"
MENSAJE_SALIO = "salio"

# ----------------------------------------------------------------------
# Textos
# ----------------------------------------------------------------------
TEXTO_BOTON = "CELULAR"
TEXTO_BOTON_DETALLE = " · chat y feed"
TEXTO_EN_VIVO = "EN VIVO"
TEXTO_INICIO = "Inicio"
TEXTO_CHAT = "Chat"
TEXTO_VIENDO = "{} viendo"
TEXTO_PELIGRO = "Sigues en la mazmorra: tu personaje está quieto"
TEXTO_CHAT_VACIO = "Escríbele a tu equipo: todos los jugadores de la sala leen este chat."
TEXTO_PISTA_ENTRADA = "Escribe un mensaje..."
TEXTO_FANTASMA = "Eres un fantasma: solo puedes leer"
TEXTO_NUEVAS = "Nuevas publicaciones"
TEXTO_NUEVOS_MENSAJES = "Nuevos mensajes"
TEXTO_ENTRO = "{} entró a la sala"
TEXTO_SALIO = "{} salió de la sala"
TEXTO_BANNER = "Civitas · ahora"
TEXTO_TENDENCIA = "Tendencia"
TEXTO_SIN_FEED = "Conectando con Civitas..."
TEXTO_ESPERANDO_VIVO = "Esperando comentarios..."
TEXTO_PUBLICACION = "Publicación"
TEXTO_COMENTARIOS = "Comentarios"
TEXTO_PISTA_COMENTARIO = "Escribe un comentario..."
TEXTO_TU = "Tú"
SUFIJO_FANTASMA = " · fantasma"
CUENTA_OFICIAL = "@civitasoficial"  # su avatar es el retrato de Civitas (comparación sin mayúsculas)

# ----------------------------------------------------------------------
# Colores propios del celular Online (los demás se leen de assets)
# ----------------------------------------------------------------------
COLOR_TARJETA = (20, 22, 52)  # fondo de cada tarjeta del feed y de los chips
COLOR_BORDE_TARJETA = assets.COLOR_SEPARADOR_CELULAR
COLOR_ROJO_VIVO = (206, 38, 58)  # "EN VIVO": más oscuro que COLOR_GRAVE para que el texto blanco contraste
COLOR_BURBUJA_PROPIA = (104, 64, 190)  # violeta oscuro: texto blanco con contraste > 4.5
COLOR_BURBUJA_AJENA = assets.COLOR_FONDO_AVATAR_POST
COLOR_ENTRADA = (22, 24, 56)  # caja de texto del chat
COLOR_ENTRADA_APAGADA = (16, 17, 40)  # caja del fantasma
COLOR_PISTA_ENTRADA = (128, 126, 166)  # "Escribe un mensaje...": más claro que COLOR_TEXTO_APAGADO
COLOR_TEXTO_FRANJA = (44, 28, 6)  # texto oscuro sobre la franja ámbar
COLOR_BANNER = (32, 32, 72)
COLOR_BOTON_ABAJO = assets.COLOR_MARCO_CELULAR_ABAJO  # el botón tiene el degradado del canto del celular
COLOR_ME_GUSTA = assets.COLOR_GRAVE  # corazón propio
COLORES_CIFRA = (assets.COLOR_GRAVE, assets.COLOR_VERIFICADO, assets.COLOR_CIVITAS)  # me gusta, compartidos, comentarios
COLORES_PROPIO = (COLOR_ME_GUSTA, assets.COLOR_VERIFICADO, assets.COLOR_CIVITAS)  # ícono marcado por esta PC
COLORES_NOMBRES_VIVO = (assets.COLOR_VERIFICADO, assets.COLOR_ALERTA, assets.COLOR_CIVITAS, assets.COLOR_MAGENTA,
                        assets.COLOR_TEAL, assets.COLOR_TITULO_LUZ)
COLOR_ETIQUETA = {  # chip de cada etiqueta de publicación
    "Sin fuente": assets.COLOR_ALERTA,
    "Verificado": assets.COLOR_VERIFICADO,
    "Oficial": assets.COLOR_CIVITAS,
    "Campaña": assets.COLOR_CIVITAS,
}
COLOR_ICONO_NOTIFICACION = {  # icono del banner: (fondo del cuadrito, color del dibujo)
    "corazon": (assets.COLOR_GRAVE, assets.COLOR_TEXTO_HUD),
    "compartir": (assets.COLOR_VERIFICADO, assets.COLOR_NOCHE),
    "comentario": (assets.COLOR_CIVITAS, assets.COLOR_TEXTO_HUD),
    "tendencia": (assets.COLOR_MAGENTA, assets.COLOR_TEXTO_HUD),
    "mencion": (assets.COLOR_ALERTA, assets.COLOR_NOCHE),
    "vivo": (COLOR_ROJO_VIVO, assets.COLOR_TEXTO_HUD),
}
ALFA_SOMBRA = 80  # sombra del celular sobre el mundo

# ----------------------------------------------------------------------
# Medidas (px)
# ----------------------------------------------------------------------
ALTO_BARRA_APP = 40
ALTO_PESTANAS = 36
ALTO_FRANJA_PELIGRO = 38  # dos renglones: "Sigues en la mazmorra:" / "tu personaje está quieto"
ALTO_ZONA_INICIO = 16  # abajo de todo: el indicador de inicio
MARGEN = 10  # entre el borde de la pantalla y las tarjetas
RELLENO = 12  # dentro de cada tarjeta
SEPARACION = 10  # entre tarjetas
RADIO_TARJETA = 14
UMBRAL_ARRIBA = 4  # px: con menos de esto se considera "arriba del todo" / "pegado abajo"
BATERIA = 0.82

# Feed
ALTO_FOTO_VIVO = 124
ALTO_BANDA_VIVO = 46  # degradado oscuro bajo el título de la transmisión
LINEAS_VIVO = 4  # mensajes del chat en vivo a la vista
ALTO_LINEA_VIVO = 17
ALTO_TARJETA_VIVO = ALTO_FOTO_VIVO + 6 + LINEAS_VIVO * ALTO_LINEA_VIVO + 8
RADIO_AVATAR_POST = 17
ALTO_CABECERA_POST = 36
LINEAS_POST = 5
ALTO_LINEA_POST = 19
ALTO_FOTO_POST = 110
ALTO_FILA_DATOS = 28
LINEAS_COMENTARIO = 2
ALTO_LINEA_COMENTARIO = 16
ALTO_CHIP_POST = 17
SUBIDA_CIFRA = 14  # px que sube el "+N" mientras se desvanece
DESLIZAR = 0.35  # s: el mensaje en vivo que llega y el comentario nuevo entran deslizándose
DURACION_BANNER = 3.5  # s que se ve la notificación más reciente
ENTRADA_BANNER = 0.3  # s que tarda en bajar (y en subir al irse)
ALTO_BANNER = 62
ALTO_PILDORA = 26

# Chat
ALTO_ENTRADA = 40
DIAMETRO_ENVIAR = 38
ALTO_RESPUESTA = 28
SEPARACION_RESPUESTAS = 6
DIAMETRO_AVATAR_CHAT = 28
ALTO_ETIQUETA_CHAT = 17
ALTO_LINEA_CHAT = 18
RELLENO_BURBUJA = (12, 7)  # horizontal, vertical
RADIO_BURBUJA = 12
SEPARACION_GRUPO = 10  # entre mensajes de distinto autor
SEPARACION_MISMO = 3  # entre mensajes seguidos del mismo autor
ALTO_SISTEMA = 22
AVISO_LARGO = 15  # se muestra "n/80" cuando faltan menos de estas letras

# Botón y globo
ALTO_MINIMO_BOTON_GRANDE = 60  # más bajo que esto (la píldora de la sala), una sola fila
RADIO_INSIGNIA = 10
COLA_GLOBO = 9  # px que sale la colita del globo hacia el botón
ENTRA_AVISO = 0.08  # fracción del tiempo del globo en que aparece
SALE_AVISO = 0.15  # y en que se desvanece

# Fuentes
T_MIN = assets.TAMANIO_FUENTE_CELULAR_MINIMA  # 10
T_CHIP = 11
T_CHICO = assets.TAMANIO_FUENTE_CELULAR  # 12
T_TEXTO = assets.TAMANIO_FUENTE_PEQUENA  # 13

# ----------------------------------------------------------------------
# Lo que se dibujó
# ----------------------------------------------------------------------


@dataclass
class DibujoCelular:
    """Lo que dibujó dibujar_celular: rects clicables (para objetivo_en) y cada
    texto con la caja en la que tenía que caber (para los tests de layout)."""

    cuerpo: pygame.Rect
    pantalla: pygame.Rect
    contenido: pygame.Rect
    cerrar: pygame.Rect | None = None
    pestanas: list = field(default_factory=list)  # [(app, rect)]
    enviar: pygame.Rect | None = None
    entrada: pygame.Rect | None = None
    respuestas: list = field(default_factory=list)  # [(indice, rect)]
    corazones: list = field(default_factory=list)  # [(id_publicacion, rect)]
    reposts: list = field(default_factory=list)  # [(id_publicacion, rect)] el ícono de compartir
    publicaciones: list = field(default_factory=list)  # [(id_publicacion, rect)] clic en la tarjeta = abrirla
    volver: pygame.Rect | None = None  # flecha de la publicación abierta
    nuevas: pygame.Rect | None = None  # píldora "Nuevas publicaciones" / "Nuevos mensajes"
    textos: list = field(default_factory=list)  # [(texto_dibujado, rect, caja_permitida)]
    alto_contenido: int = 0  # alto total de la lista de la app activa
    banner: pygame.Rect | None = None  # notificación que bajó (tapa lo de abajo: un clic ahí no es "me gusta")


# ----------------------------------------------------------------------
# Cachés
# ----------------------------------------------------------------------
MAX_CACHE_TEXTOS = 1500  # al pasarse, el caché se vacía y se vuelve a llenar
MAX_CACHE_IMAGENES = 96

_cache_superficies = {}  # (cadena, tamaño, negrita, color) -> Surface
_cache_ajustes = {}  # (cadena, ancho, tamaño, negrita, mínimo) -> (tamaño, cadena)
_cache_lineas = {}  # (cadena, ancho, tamaño, negrita, máximo) -> tupla de líneas
_cache_imagenes = {}  # avatares, fotos, sombra, fondos de botón, degradados y globos


def _cachear(cache, clave, maximo, crear):
    """Devuelve cache[clave] o lo crea con `crear()`. Al llegar a `maximo`
    se vacía entero: es más simple que una LRU y en la práctica no pasa."""
    try:
        if clave in cache:
            return cache[clave]
    except TypeError:  # clave que no se puede hashear: no se cachea
        return crear()
    if len(cache) >= maximo:
        cache.clear()
    valor = crear()
    cache[clave] = valor
    return valor


def _superficie(cadena, tamanio, negrita, color):
    return _cachear(_cache_superficies, (cadena, tamanio, negrita, color), MAX_CACHE_TEXTOS,
                    lambda: fuente(tamanio, negrita).render(cadena, True, color))


def _ajustar(cadena, ancho, tamanio, negrita, minimo):
    """(tamaño, cadena) que entra en `ancho` en una línea: baja de a 1 px hasta
    `minimo` y luego recorta con "…" (la misma regla que layout.texto_en_ancho)."""
    def crear():
        tam = tamanio
        while tam > minimo and fuente(tam, negrita).size(cadena)[0] > ancho:
            tam -= 1
        f = fuente(tam, negrita)
        if f.size("…")[0] > ancho:
            return tam, ""
        texto = cadena
        while len(texto) > 1 and f.size(texto)[0] > ancho:
            texto = texto[:-2].rstrip() + "…"
        return tam, texto
    return _cachear(_cache_ajustes, (cadena, ancho, tamanio, negrita, minimo), MAX_CACHE_TEXTOS, crear)


def _corte(f, linea, ancho):
    """Cuántas letras de `linea` entran en `ancho` (búsqueda binaria, al menos 1)."""
    bajo, alto = 1, len(linea)
    while bajo < alto:
        medio = (bajo + alto + 1) // 2
        if f.size(linea[:medio])[0] <= ancho:
            bajo = medio
        else:
            alto = medio - 1
    return bajo


def _lineas(cadena, ancho, tamanio, negrita=False, maximo=99):
    """Líneas de `cadena` que entran en `ancho`: por palabras
    (dibujo.ajustar_texto) y, si una palabra sola no entra (un "jajajaja" de
    80 letras), por letras. Con más de `maximo` líneas, la última termina en
    "…". Cacheado por texto, ancho, tamaño y tope."""
    def crear():
        f = fuente(tamanio, negrita)
        lineas = []
        for linea in dibujo.ajustar_texto(str(cadena), tamanio, max(1, ancho), negrita):
            while len(linea) > 1 and f.size(linea)[0] > ancho:
                corte = _corte(f, linea, ancho)
                lineas.append(linea[:corte])
                linea = linea[corte:].lstrip()
            if linea:
                lineas.append(linea)
        if len(lineas) > maximo:
            lineas = lineas[:maximo]
            ultima = lineas[-1].rstrip(" .,;:")
            while ultima and f.size(ultima + "…")[0] > ancho:
                ultima = ultima[:-1].rstrip()
            lineas[-1] = ultima + "…"
        return tuple(lineas)
    return _cachear(_cache_lineas, (str(cadena), ancho, tamanio, negrita, maximo), MAX_CACHE_TEXTOS, crear)


def _final_que_entra(texto, ancho, tamanio):
    """El final más largo de `texto` que entra en `ancho` (la caja del chat
    muestra lo último que se escribió). Búsqueda binaria: O(log n) medidas."""
    f = fuente(tamanio)
    if f.size(texto)[0] <= ancho:
        return texto
    bajo, alto = 0, len(texto)
    while bajo < alto:
        medio = (bajo + alto) // 2
        if f.size(texto[medio:])[0] <= ancho:
            alto = medio
        else:
            bajo = medio + 1
    return texto[bajo:]


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------


def _float(valor, defecto=0.0):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return defecto
    return valor if math.isfinite(valor) else defecto


def _entero(valor):
    try:
        return max(0, int(valor))
    except (TypeError, ValueError, OverflowError):
        return 0


def _rgb(color, defecto=assets.COLOR_TEXTO_SECUNDARIO):
    try:
        return tuple(max(0, min(255, int(c))) for c in tuple(color)[:3])
    except (TypeError, ValueError):
        return defecto


def _mezclar(a, b, t):
    """Color entre `a` (t = 0) y `b` (t = 1)."""
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _suave(t):
    """Desaceleración (ease-out cúbico) de 0 a 1."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _blit(pantalla, superficie, posicion, alfa=255):
    if alfa >= 255:
        pantalla.blit(superficie, posicion)
        return
    superficie.set_alpha(max(0, round(alfa)))
    pantalla.blit(superficie, posicion)
    superficie.set_alpha(255)  # está en un caché: se deja como estaba


def _texto(d, pantalla, cadena, caja, color, tamanio=T_CHICO, negrita=False, ancla="topleft", posicion=None,
           minimo=T_MIN, visible=None, alfa=255):
    """Una línea que nunca pasa del ancho de `caja` (baja de tamaño y luego
    recorta con "…"), desde el caché de superficies. Se anota en d.textos con
    su caja. `visible`: la zona que se ve (la lista desplazada); lo que cae
    fuera no se dibuja ni se anota. Retorna el rect completo del texto."""
    caja = pygame.Rect(caja)
    tam, texto = _ajustar(str(cadena), caja.width, tamanio, negrita, minimo)
    if not texto:
        return pygame.Rect(caja.left, caja.top, 0, 0)
    superficie = _superficie(texto, tam, negrita, _rgb(color))
    rect = superficie.get_rect(**{ancla: posicion if posicion is not None else getattr(caja, ancla)})
    vista = rect if visible is None else rect.clip(visible)
    if vista.width <= 0 or vista.height <= 0 or alfa <= 0:
        return rect
    _blit(pantalla, superficie, rect, alfa)
    if d is not None:
        d.textos.append((texto, vista, caja))
    return rect


def _con_recorte(pantalla, rect):
    """Pone el recorte en `rect` (dentro del que ya había) y devuelve el anterior."""
    anterior = pantalla.get_clip()
    pantalla.set_clip(pygame.Rect(rect).clip(anterior))
    return anterior


class _Perfiles:
    """perfil(id_red) con memoria durante un dibujo (el chat pregunta lo
    mismo por cada mensaje). Si no hay perfil, uno genérico "J<n>"."""

    def __init__(self, perfil):
        self._perfil = perfil
        self._vistos = {}

    def __call__(self, id_red):
        if id_red not in self._vistos:
            resultado = self._perfil(id_red) if callable(self._perfil) else None
            if resultado is None:
                numero = id_red + 1 if isinstance(id_red, int) else "?"
                resultado = Perfil(f"J{numero}", assets.COLOR_TEXTO_SECUNDARIO)
            self._vistos[id_red] = resultado
        return self._vistos[id_red]


def _duracion(segundos):
    """12:34 o 1:02:03 (lo que lleva la transmisión)."""
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas}:{minutos:02d}:{segundos:02d}" if horas else f"{minutos}:{segundos:02d}"


# ----------------------------------------------------------------------
# Iconos que no están en src/ui/celular_render.py (primitivas)
# ----------------------------------------------------------------------


def _icono_globo(pantalla, centro, tamanio, color, grosor=2):
    """Globo de diálogo: el chat y los comentarios."""
    cx, cy = centro
    caja = pygame.Rect(0, 0, round(tamanio * 0.86), round(tamanio * 0.62))
    caja.center = (cx, cy - round(tamanio * 0.08))
    pygame.draw.rect(pantalla, color, caja, grosor, border_radius=max(2, round(tamanio * 0.22)))
    cola = [(caja.left + round(tamanio * 0.18), caja.bottom - 2), (caja.left + round(tamanio * 0.12), caja.bottom + round(tamanio * 0.2)),
            (caja.left + round(tamanio * 0.42), caja.bottom - 2)]
    pygame.draw.polygon(pantalla, color, cola)


def _icono_celular(pantalla, centro, alto, color, color_pantalla):
    """Celular de frente: cuerpo, pantalla, isla y dos burbujitas de chat."""
    ancho = round(alto * 0.62)
    cuerpo = pygame.Rect(0, 0, ancho, alto)
    cuerpo.center = centro
    pygame.draw.rect(pantalla, color, cuerpo, border_radius=max(3, ancho // 4))
    vidrio = cuerpo.inflate(-max(3, ancho // 6) * 2, -max(4, alto // 8) * 2)
    pygame.draw.rect(pantalla, color_pantalla, vidrio, border_radius=max(2, ancho // 8))
    isla = pygame.Rect(0, 0, max(4, ancho // 3), max(2, alto // 16))
    isla.midtop = (cuerpo.centerx, cuerpo.top + max(1, alto // 20))
    pygame.draw.rect(pantalla, color_pantalla, isla, border_radius=1)
    alto_burbuja = max(3, vidrio.height // 5)
    for i, (fraccion, lado) in enumerate(((0.62, "izquierda"), (0.5, "derecha"))):
        burbuja = pygame.Rect(0, 0, max(4, round(vidrio.width * fraccion)), alto_burbuja)
        burbuja.top = vidrio.top + max(2, vidrio.height // 6) + i * (alto_burbuja + max(2, vidrio.height // 8))
        if lado == "izquierda":
            burbuja.left = vidrio.left + max(1, vidrio.width // 8)
        else:
            burbuja.right = vidrio.right - max(1, vidrio.width // 8)
        pygame.draw.rect(pantalla, color, burbuja, border_radius=max(1, alto_burbuja // 2))


def _icono_ojo(pantalla, centro, tamanio, color):
    caja = pygame.Rect(0, 0, tamanio, round(tamanio * 0.62))
    caja.center = centro
    pygame.draw.ellipse(pantalla, color, caja, 2)
    pygame.draw.circle(pantalla, color, centro, max(2, tamanio // 5))


def _icono_tendencia(pantalla, centro, tamanio, color):
    """Línea en zigzag que sube con su flecha (tendencia)."""
    cx, cy = centro
    s = tamanio
    puntos = [(cx - s * 0.40, cy + s * 0.26), (cx - s * 0.10, cy - s * 0.04), (cx + s * 0.06, cy + s * 0.12),
              (cx + s * 0.36, cy - s * 0.20)]
    pygame.draw.lines(pantalla, color, False, [(round(x), round(y)) for x, y in puntos], 3)
    punta = [(cx + s * 0.42, cy - s * 0.30), (cx + s * 0.14, cy - s * 0.26), (cx + s * 0.40, cy - s * 0.02)]
    pygame.draw.polygon(pantalla, color, [(round(x), round(y)) for x, y in punta])


def _flecha(pantalla, centro, tamanio, color, hacia_arriba=True):
    cx, cy = centro
    s = tamanio / 2
    signo = -1 if hacia_arriba else 1
    pygame.draw.line(pantalla, color, (cx, round(cy - signo * s)), (cx, round(cy + signo * s)), 2)
    pygame.draw.lines(pantalla, color, False, [(round(cx - s * 0.7), round(cy + signo * s * 0.1)),
                                                (cx, round(cy + signo * s)), (round(cx + s * 0.7), round(cy + signo * s * 0.1))], 2)


def _icono_notificacion(pantalla, cuadro, icono):
    """Cuadrito redondeado con el icono de la notificación ("corazon",
    "compartir", "comentario", "tendencia", "mencion" o "vivo")."""
    fondo, tinta = COLOR_ICONO_NOTIFICACION.get(icono, (assets.COLOR_CIVITAS, assets.COLOR_TEXTO_HUD))
    pygame.draw.rect(pantalla, fondo, cuadro, border_radius=9)
    centro = cuadro.center
    if icono == "corazon":
        celular_render.dibujar_icono(pantalla, "corazon", centro, 22, tinta, grosor=0)
    elif icono == "compartir":
        celular_render.dibujar_icono(pantalla, "compartir", centro, 22, tinta)
    elif icono == "tendencia":
        _icono_tendencia(pantalla, centro, 22, tinta)
    elif icono == "mencion":
        superficie = _superficie("@", assets.TAMANIO_FUENTE_MEDIA, True, tinta)
        pantalla.blit(superficie, superficie.get_rect(center=(centro[0], centro[1] - 1)))
    elif icono == "vivo":
        pygame.draw.circle(pantalla, tinta, centro, 5)
        for radio in (9, 13):
            caja = pygame.Rect(0, 0, radio * 2, radio * 2)
            caja.center = centro
            pygame.draw.arc(pantalla, tinta, caja, math.radians(-50), math.radians(50), 2)
            pygame.draw.arc(pantalla, tinta, caja, math.radians(130), math.radians(230), 2)
    else:  # "comentario" y cualquier otro: el globo de diálogo
        _icono_globo(pantalla, centro, 22, tinta)


def _insignia(pantalla, centro, cantidad, radio=RADIO_INSIGNIA, pulso=None):
    """Círculo rojo (assets.COLOR_GRAVE) con la cantidad ("9+" si pasa de 9).
    `pulso` (0-1): un halo suave que crece y se apaga alrededor."""
    texto = "9+" if cantidad > 9 else str(cantidad)
    superficie = _superficie(texto, T_CHIP, True, assets.COLOR_TEXTO_HUD)
    rect = pygame.Rect(0, 0, max(2 * radio, superficie.get_width() + 8), 2 * radio)
    rect.center = centro
    if pulso is not None:
        crecer = round(4 + 6 * pulso)
        dibujo.panel_alfa(pantalla, rect.inflate(crecer, crecer), (*assets.COLOR_GRAVE, round(110 * (1 - pulso))),
                          radio=radio + crecer // 2)
    pygame.draw.rect(pantalla, assets.COLOR_GRAVE, rect, border_radius=radio)
    pantalla.blit(superficie, superficie.get_rect(center=rect.center))
    return rect


def _pildora_vivo(d, pantalla, topleft, reloj, reducir, visible=None):
    """Píldora roja "● EN VIVO" con el punto que late."""
    superficie = _superficie(TEXTO_EN_VIVO, T_CHIP, True, assets.COLOR_TEXTO_HUD)
    rect = pygame.Rect(topleft[0], topleft[1], superficie.get_width() + 26, 20)
    pygame.draw.rect(pantalla, COLOR_ROJO_VIVO, rect, border_radius=10)
    latido = 0.0 if reducir else 0.5 + 0.5 * math.sin(reloj * 5.0)
    pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, (rect.left + 10, rect.centery), 3 + round(latido))
    _texto(d, pantalla, TEXTO_EN_VIVO, pygame.Rect(rect.left + 17, rect.top, rect.width - 20, rect.height),
           assets.COLOR_TEXTO_HUD, T_CHIP, True, ancla="midleft", visible=visible)
    return rect


# ----------------------------------------------------------------------
# Superficies cacheadas: sombra, fotos, avatares, degradados, botón
# ----------------------------------------------------------------------


def _sombra(pantalla, cuerpo):
    """Sombra suave del celular sobre el mundo (anillos con alfa creciente)."""
    margen = 16

    def crear():
        superficie = pygame.Surface((cuerpo.width + 2 * margen, cuerpo.height + 2 * margen), pygame.SRCALPHA)
        for paso in range(margen, 0, -2):
            alfa = round(ALFA_SOMBRA * (1 - paso / margen) ** 1.6)
            caja = pygame.Rect(margen - paso, margen - paso + 6, cuerpo.width + 2 * paso, cuerpo.height + 2 * paso - 6)
            pygame.draw.rect(superficie, (0, 0, 0, alfa), caja, border_radius=assets.RADIO_CELULAR + paso)
        return superficie
    sombra = _cachear(_cache_imagenes, ("sombra", cuerpo.size), MAX_CACHE_IMAGENES, crear)
    pantalla.blit(sombra, (cuerpo.left - margen, cuerpo.top - margen))


def _redondear(superficie, radio, solo_arriba=False):
    """Copia con las esquinas redondeadas (máscara con BLEND_RGBA_MIN)."""
    resultado = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
    resultado.blit(superficie, (0, 0))
    mascara = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
    if solo_arriba:
        pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_top_left_radius=radio,
                         border_top_right_radius=radio)
    else:
        pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=radio)
    resultado.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return resultado


def _foto(nombre, tamanio, radio, solo_arriba=False):
    """Ilustración de assets/story recortada (celular_render.foto_recortada) y
    con las esquinas redondeadas."""
    tamanio = (max(1, int(tamanio[0])), max(1, int(tamanio[1])))

    def crear():
        base = celular_render.foto_recortada(nombre, assets.RECORTE_FOTO_POST.get(nombre), tamanio)
        return _redondear(base, radio, solo_arriba)
    return _cachear(_cache_imagenes, ("foto", nombre, tamanio, radio, solo_arriba), MAX_CACHE_IMAGENES, crear)


def _degradado(ancho, alto, color_rgba):
    """Banda que va de transparente (arriba) a `color_rgba` (abajo): el título
    de la transmisión se lee sobre cualquier foto."""
    def crear():
        superficie = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for y in range(alto):
            t = (y / max(1, alto - 1)) ** 0.8
            pygame.draw.line(superficie, (*color_rgba[:3], round(color_rgba[3] * t)), (0, y), (ancho, y))
        return superficie
    return _cachear(_cache_imagenes, ("degradado", ancho, alto, tuple(color_rgba)), MAX_CACHE_IMAGENES, crear)


def _recorte_civitas():
    for rol, _, recorte in assets.HISTORIAS_CELULAR:
        if rol == assets.ID_RETRATO_CIVITAS:
            return recorte
    return (0.5, 0.5, 0.6)


def _avatar_cuenta(nombre, usuario, radio):
    """Avatar de quien publica: el retrato de Civitas para @CivitasOficial y,
    para el resto, las iniciales del nombre (celular_render.avatar_iniciales)."""
    def crear():
        superficie = pygame.Surface((2 * radio + 2, 2 * radio + 2), pygame.SRCALPHA)
        centro = (radio + 1, radio + 1)
        cara = None
        if str(usuario).lower() == CUENTA_OFICIAL:
            cara = celular_render.retrato_redondo(assets.ID_RETRATO_CIVITAS, 2 * radio, _recorte_civitas())
        if cara is not None:
            superficie.blit(cara, cara.get_rect(center=centro))
        else:
            celular_render.avatar_iniciales(superficie, centro, radio, nombre or usuario, anillo=False)
        return superficie
    return _cachear(_cache_imagenes, ("cuenta", nombre, usuario, radio), MAX_CACHE_IMAGENES, crear)


def _avatar_jugador(perfil, diametro):
    """El muñeco del jugador (sprites.sprite_jugador a escala 2, con la ropa de
    los vestidores) recortado en un círculo con un anillo de su color. El
    fantasma se ve transparente."""
    color = _rgb(perfil.color)

    def crear():
        muneco = sprites.sprite_jugador(color, escala=2, rol=perfil.rol, apariencia=perfil.apariencia)
        circulo = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
        centro = (diametro // 2, diametro // 2)
        pygame.draw.circle(circulo, assets.COLOR_FONDO_AVATAR_POST, centro, diametro // 2)
        # El busto: la cabeza y los hombros quedan al centro del círculo.
        circulo.blit(muneco, (round(centro[0] - muneco.get_width() * 0.45), round(centro[1] - muneco.get_height() * 0.36)))
        mascara = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), centro, diametro // 2)
        circulo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        superficie = pygame.Surface((diametro + 4, diametro + 4), pygame.SRCALPHA)
        superficie.blit(circulo, (2, 2))
        pygame.draw.circle(superficie, color, (diametro // 2 + 2, diametro // 2 + 2), diametro // 2 + 2, 2)
        if perfil.fantasma:
            superficie.set_alpha(130)
        return superficie
    clave = ("jugador", color, perfil.rol, perfil.apariencia, diametro, bool(perfil.fantasma))
    return _cachear(_cache_imagenes, clave, MAX_CACHE_IMAGENES, crear)


def _fondo_boton(tamanio, radio):
    """Fondo del botón CELULAR: el degradado violeta del canto del celular
    (assets.COLOR_CIVITAS arriba, más oscuro abajo, donde va el texto blanco)
    con el borde blanco de los botones del HUD (como REPORTAR)."""
    def crear():
        ancho, alto = tamanio
        superficie = pygame.Surface(tamanio, pygame.SRCALPHA)
        for y in range(alto):
            pygame.draw.line(superficie, _mezclar(assets.COLOR_CIVITAS, COLOR_BOTON_ABAJO, y / max(1, alto - 1)),
                             (0, y), (ancho, y))
        forma = pygame.Surface(tamanio, pygame.SRCALPHA)
        pygame.draw.rect(forma, (255, 255, 255, 255), forma.get_rect(), border_radius=radio)
        superficie.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(superficie, assets.COLOR_TEXTO_HUD, superficie.get_rect(), 2, border_radius=radio)
        return superficie
    return _cachear(_cache_imagenes, ("boton", tuple(tamanio), radio), MAX_CACHE_IMAGENES, crear)


# ----------------------------------------------------------------------
# Botón CELULAR y globo del mensaje entrante (celular cerrado)
# ----------------------------------------------------------------------


def dibujar_boton(pantalla, rect, no_leidos, tiempo, compacto=False):
    """Botón CELULAR: panel violeta con un celular dibujado, "CELULAR", el
    chip de la tecla C y, si hay mensajes sin leer, la insignia roja con la
    cantidad ("9+" si pasa de 9) y un pulso suave. Compacto (alto < 60, la
    píldora de la sala): todo en una fila, "CELULAR · chat y feed"."""
    rect = pygame.Rect(rect)
    cantidad = _entero(no_leidos)
    tiempo = _float(tiempo)
    compacto = compacto or rect.height < ALTO_MINIMO_BOTON_GRANDE
    pulso = (tiempo * 0.9) % 1.0  # 0 -> 1: el halo de la insignia crece y se apaga
    radio = rect.height // 2 if compacto else 14
    if cantidad > 0:  # el botón entero respira un poco: hay algo que leer
        brillo = 0.5 + 0.5 * math.sin(tiempo * 3.0)
        crecer = round(6 + 4 * brillo)
        dibujo.panel_alfa(pantalla, rect.inflate(crecer, crecer), (*assets.COLOR_CIVITAS, round(40 + 50 * brillo)),
                          radio=radio + crecer // 2)
    pantalla.blit(_fondo_boton(rect.size, radio), rect)
    if compacto:
        _boton_compacto(pantalla, rect, cantidad, pulso)
        return
    icono_centro = (rect.centerx, rect.top + 33)
    _icono_celular(pantalla, icono_centro, 34, assets.COLOR_TEXTO_HUD, COLOR_BOTON_ABAJO)
    _texto(None, pantalla, TEXTO_BOTON, pygame.Rect(rect.left + 5, rect.bottom - 30, rect.width - 10, 22),
           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, True, ancla="center", minimo=9)
    dibujo.chip(pantalla, TECLA_BOTON, (rect.right - 6, rect.top + 6), ancla="topright")
    if cantidad > 0:
        _insignia(pantalla, (icono_centro[0] + 13, icono_centro[1] - 15), cantidad, pulso=pulso)


def _boton_compacto(pantalla, rect, cantidad, pulso):
    """Una fila: celular, "CELULAR · chat y feed", insignia y chip C."""
    _icono_celular(pantalla, (rect.left + 22, rect.centery), 24, assets.COLOR_TEXTO_HUD, COLOR_BOTON_ABAJO)
    chip = dibujo.chip(pantalla, TECLA_BOTON, (rect.right - 6, rect.centery), ancla="midright",
                       alto=min(assets.ALTO_CHIP, rect.height - 8))
    derecha = chip.left - 8
    if cantidad > 0:
        insignia = _insignia(pantalla, (chip.left - 8 - RADIO_INSIGNIA, rect.centery), cantidad, pulso=pulso)
        derecha = insignia.left - 8
    izquierda = rect.left + 38
    principal = _texto(None, pantalla, TEXTO_BOTON, pygame.Rect(izquierda, rect.top, derecha - izquierda, rect.height),
                       assets.COLOR_TEXTO_HUD, T_TEXTO, True, ancla="midleft")
    detalle = pygame.Rect(principal.right, rect.top, derecha - principal.right, rect.height)
    if detalle.width >= fuente(T_MIN).size(TEXTO_BOTON_DETALLE)[0]:  # si no entra ni chico, solo "CELULAR"
        _texto(None, pantalla, TEXTO_BOTON_DETALLE, detalle, assets.COLOR_TITULO_LUZ, T_CHICO, ancla="midleft")


def dibujar_aviso(pantalla, rect, perfil, texto, fraccion):
    """Globo del mensaje entrante con el celular cerrado: el muñeco de quien
    escribe, su nombre en su color y el texto en una o dos líneas (si no
    entra, "…": nunca se sale). Aparece y se desvanece con alfa según
    `fraccion` (1 al llegar -> 0 al irse). La colita apunta al botón."""
    fraccion = _float(fraccion)
    alfa = 255 * max(0.0, min(1.0, (1.0 - fraccion) / ENTRA_AVISO, fraccion / SALE_AVISO))
    if alfa <= 0:
        return
    rect = pygame.Rect(rect)
    if not isinstance(perfil, Perfil):
        perfil = Perfil(str(getattr(perfil, "etiqueta", "") or "?"), _rgb(getattr(perfil, "color", None)),
                        getattr(perfil, "rol", None), getattr(perfil, "apariencia", None))
    clave = ("globo", rect.size, perfil.etiqueta, _rgb(perfil.color), perfil.rol, perfil.apariencia, str(texto or ""))
    globo = _cachear(_cache_imagenes, clave, MAX_CACHE_IMAGENES, lambda: _componer_globo(rect.size, perfil, str(texto or "")))
    _blit(pantalla, globo, rect.topleft, alfa)


def _componer_globo(tamanio, perfil, texto):
    """El globo armado una sola vez en una superficie (luego solo cambia el alfa)."""
    ancho, alto = tamanio
    color = _rgb(perfil.color)
    superficie = pygame.Surface((ancho + COLA_GLOBO, alto), pygame.SRCALPHA)
    cuerpo = pygame.Rect(0, 0, ancho, alto)
    radio = min(14, alto // 2)
    pygame.draw.rect(superficie, (*assets.COLOR_FONDO_PANEL, 244), cuerpo, border_radius=radio)
    pygame.draw.rect(superficie, color, cuerpo, 2, border_radius=radio)
    centro_y = alto // 2
    cola = [(ancho - 2, centro_y - 7), (ancho + COLA_GLOBO - 1, centro_y), (ancho - 2, centro_y + 7)]
    pygame.draw.polygon(superficie, (*assets.COLOR_FONDO_PANEL, 244), cola)
    pygame.draw.line(superficie, color, cola[0], cola[1], 2)
    pygame.draw.line(superficie, color, cola[1], cola[2], 2)
    compacto = alto < 50
    diametro = alto - 12 if compacto else 36
    avatar = _avatar_jugador(perfil, diametro)
    superficie.blit(avatar, avatar.get_rect(center=(8 + avatar.get_width() // 2, centro_y)))
    izquierda = 8 + avatar.get_width() + 8
    ancho_texto = ancho - izquierda - 12
    if compacto:  # una fila: "J2 · Candidato: hola"
        nombre = _texto(None, superficie, f"{perfil.etiqueta}:", pygame.Rect(izquierda, 0, round(ancho_texto * 0.55), alto),
                        color, T_CHICO, True, ancla="midleft")
        _texto(None, superficie, texto, pygame.Rect(nombre.right + 6, 0, ancho - 12 - nombre.right - 6, alto),
               assets.COLOR_TEXTO_HUD, T_CHICO, ancla="midleft")
        return superficie
    lineas = _lineas(texto, ancho_texto, T_CHICO, False, 2)
    bloque = 16 + len(lineas) * 16
    y = max(4, centro_y - bloque // 2)
    _texto(None, superficie, perfil.etiqueta, pygame.Rect(izquierda, y, ancho_texto, 16), color, T_CHICO, True)
    for numero, linea in enumerate(lineas):
        _texto(None, superficie, linea, pygame.Rect(izquierda, y + 16 + numero * 16, ancho_texto, 16),
               assets.COLOR_TEXTO_HUD, T_CHICO)
    return superficie


# ----------------------------------------------------------------------
# El celular abierto
# ----------------------------------------------------------------------


def dibujar_celular(pantalla, rect_cuerpo, celular, feed, mensajes, perfil, id_local, puede_escribir, respuestas,
                    segundos, en_peligro=False, no_leidos=None):
    """Dibuja el celular abierto en `rect_cuerpo` (disposicion_celular.rect_celular
    da RECT_CELULAR_ABIERTO desplazado según la animación de abrir).

    feed: objeto con .publicaciones (la más nueva primero), .en_vivo,
    .notificaciones y .total_publicaciones (Online/feed_celular.py), o None;
    mensajes: los del chat, con .numero .autor .texto .segundos .tipo
    (Online/chat_celular.py); perfil: id_red -> Perfil; respuestas: textos de
    las respuestas rápidas; segundos: reloj del feed (estadísticas, espectadores,
    "hace X" y el banner); en_peligro: franja ámbar (mazmorra y jefe);
    no_leidos: para la insignia de la pestaña Chat (None = la cuenta el celular
    con lo que vio). Ajusta el desplazamiento a lo que mide la lista y
    devuelve un DibujoCelular."""
    cuerpo = pygame.Rect(rect_cuerpo)
    segundos = _float(segundos)
    reducir = bool(celular.reducir_movimiento)
    mensajes = tuple(mensajes or ())
    perfiles = _Perfiles(perfil)
    _sombra(pantalla, cuerpo)
    s = celular_render.dibujar_celular(pantalla, cuerpo)
    d = DibujoCelular(cuerpo=cuerpo, pantalla=s, contenido=pygame.Rect(s))
    anterior = _con_recorte(pantalla, s)
    try:
        celular_render.dibujar_barra_estado(pantalla, s, BATERIA)
        barra = pygame.Rect(s.left, s.top + assets.ALTO_BARRA_ESTADO_CELULAR, s.width, ALTO_BARRA_APP)
        _barra_app(d, pantalla, barra, celular.reloj, reducir)
        pestanas = pygame.Rect(s.left, barra.bottom, s.width, ALTO_PESTANAS)
        cantidad = 0
        if celular.app != CHAT:
            cantidad = _no_leidos(celular, mensajes, id_local) if no_leidos is None else _entero(no_leidos)
        _pestanas(d, pantalla, pestanas, celular.app, cantidad, celular.reloj, reducir)
        arriba = pestanas.bottom
        if en_peligro:
            franja = pygame.Rect(s.left, arriba, s.width, ALTO_FRANJA_PELIGRO)
            _franja_peligro(d, pantalla, franja)
            arriba = franja.bottom
        if celular.app == CHAT:
            _dibujar_chat(d, pantalla, s, arriba, celular, mensajes, perfiles, id_local, puede_escribir, respuestas,
                          segundos, reducir)
        elif getattr(celular, "publicacion_abierta", None) is not None and feed is not None:
            _dibujar_detalle(d, pantalla, s, arriba, celular, feed, segundos, reducir)
        else:
            _dibujar_feed(d, pantalla, s, arriba, celular, feed, segundos, reducir)
        celular_render.indicador_inicio(pantalla, s)
    finally:
        pantalla.set_clip(anterior)
    return d


def _no_leidos(celular, mensajes, id_local):
    """Mensajes de OTROS jugadores que llegaron después del último que se vio
    en el chat. La primera vez cuenta como visto lo que ya había: si hubiera
    algo sin leer, el celular se habría abierto directo en el Chat."""
    if celular.mensajes_vistos is None:
        celular.mensajes_vistos = _entero(getattr(mensajes[-1], "numero", 0)) if mensajes else 0
    vistos = celular.mensajes_vistos
    return sum(1 for m in mensajes if getattr(m, "tipo", MENSAJE_JUGADOR) == MENSAJE_JUGADOR
               and m.autor != id_local and _entero(m.numero) > vistos)


def _barra_app(d, pantalla, barra, reloj, reducir):
    """Flecha para cerrar, el logo de Civitas (el pixel art del menú) y "EN VIVO"."""
    centro = (barra.left + 26, barra.centery)
    celular_render.dibujar_icono(pantalla, "chevron_abajo", centro, 26, assets.COLOR_TEXTO_HUD, 3)
    d.cerrar = pygame.Rect(0, 0, 44, barra.height)
    d.cerrar.center = centro
    logo = sprites.sprite(*sprites.palabra_titulo(assets.COLOR_TITULO, assets.COLOR_TITULO_LUZ), escala=3)
    pantalla.blit(logo, logo.get_rect(center=barra.center))
    ancho = fuente(T_CHIP, True).size(TEXTO_EN_VIVO)[0] + 26
    _pildora_vivo(d, pantalla, (barra.right - 12 - ancho, barra.centery - 10), reloj, reducir)


def _pestanas(d, pantalla, rect, app, no_leidos, reloj, reducir):
    """Inicio y Chat; la activa en blanco con el subrayado violeta y la del
    chat con la insignia de no leídos."""
    mitad = rect.width // 2
    pulso = None if reducir else (reloj * 0.9) % 1.0
    for indice, (clave, nombre) in enumerate(((FEED, TEXTO_INICIO), (CHAT, TEXTO_CHAT))):
        celda = pygame.Rect(rect.left + indice * mitad, rect.top, mitad if indice == 0 else rect.width - mitad, rect.height)
        activa = app == clave
        color = assets.COLOR_TEXTO_HUD if activa else assets.COLOR_TEXTO_SECUNDARIO
        ancho_nombre = fuente(T_TEXTO, True).size(nombre)[0]
        insignia = clave == CHAT and no_leidos > 0
        total = 20 + 7 + ancho_nombre + (6 + 2 * RADIO_INSIGNIA if insignia else 0)
        x = celda.centerx - total // 2
        if clave == FEED:
            celular_render.dibujar_icono(pantalla, "inicio", (x + 10, celda.centery - 1), 18, color)
        else:
            _icono_globo(pantalla, (x + 10, celda.centery), 20, color)
        caja = pygame.Rect(x + 27, celda.top + 4, celda.right - x - 31, celda.height - 8)
        texto = _texto(d, pantalla, nombre, caja, color, T_TEXTO, True, ancla="midleft")
        if insignia:
            _insignia(pantalla, (texto.right + 6 + RADIO_INSIGNIA, celda.centery), no_leidos, pulso=pulso)
        if activa:
            pygame.draw.rect(pantalla, assets.COLOR_CIVITAS, (celda.left + 18, celda.bottom - 3, celda.width - 36, 3),
                             border_radius=2)
        d.pestanas.append((clave, celda))
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))


def _franja_peligro(d, pantalla, rect):
    """Franja ámbar: en la mazmorra el mundo sigue y el personaje está quieto."""
    pygame.draw.rect(pantalla, assets.COLOR_ALERTA, rect)
    celular_render.dibujar_icono(pantalla, "alerta", (rect.left + 22, rect.centery), 20, COLOR_TEXTO_FRANJA)
    caja = pygame.Rect(rect.left + 40, rect.top, rect.width - 50, rect.height)
    if fuente(T_CHICO, True).size(TEXTO_PELIGRO)[0] <= caja.width:
        _texto(d, pantalla, TEXTO_PELIGRO, caja, COLOR_TEXTO_FRANJA, T_CHICO, True, ancla="midleft")
        return
    primera, _, segunda = TEXTO_PELIGRO.partition(": ")
    alto = 16
    y = rect.centery - alto
    _texto(d, pantalla, primera + ":", pygame.Rect(caja.left, y, caja.width, alto), COLOR_TEXTO_FRANJA, T_CHICO, True)
    _texto(d, pantalla, segunda, pygame.Rect(caja.left, y + alto, caja.width, alto), COLOR_TEXTO_FRANJA, T_CHICO)


def _pildora(d, pantalla, texto, punto, ancla, hacia_arriba):
    """Píldora violeta "Nuevas publicaciones ↑" / "Nuevos mensajes ↓"."""
    ancho = fuente(T_CHICO, True).size(texto)[0] + 46
    rect = pygame.Rect(0, 0, ancho, ALTO_PILDORA)
    setattr(rect, ancla, punto)
    dibujo.panel_alfa(pantalla, rect.move(0, 3), (0, 0, 0, 110), radio=ALTO_PILDORA // 2)
    pygame.draw.rect(pantalla, COLOR_BURBUJA_PROPIA, rect, border_radius=ALTO_PILDORA // 2)
    pygame.draw.rect(pantalla, assets.COLOR_CIVITAS, rect, 1, border_radius=ALTO_PILDORA // 2)
    _flecha(pantalla, (rect.left + 17, rect.centery), 11, assets.COLOR_TEXTO_HUD, hacia_arriba)
    _texto(d, pantalla, texto, pygame.Rect(rect.left + 28, rect.top, rect.width - 36, rect.height), assets.COLOR_TEXTO_HUD,
           T_CHICO, True, ancla="midleft")
    d.nuevas = rect
    return rect


# ----------------------------------------------------------------------
# Inicio: transmisión en vivo, publicaciones y banners
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class _MedidasPost:
    alto: int
    lineas: tuple  # el texto, ya partido (a lo sumo LINEAS_POST)
    comentario: object  # el último comentario o None
    lineas_comentario: tuple  # "Nombre: texto" partido (a lo sumo LINEAS_COMENTARIO)


def _medir_post(pub, ancho, lineas_max=LINEAS_POST, con_comentario=True):
    """Alto de la tarjeta de una publicación (sin dibujarla). Abierta: todo el
    texto y sin el último comentario (abajo están todos)."""
    interior = ancho - 2 * RELLENO
    lineas = _lineas(pub.texto, interior, T_TEXTO, False, lineas_max)
    comentarios = list(pub.comentarios or ()) if con_comentario else []
    comentario = comentarios[-1] if comentarios else None
    lineas_comentario = ()
    if comentario is not None:
        lineas_comentario = _lineas(f"{comentario.autor}: {comentario.texto}", interior, T_CHICO, False, LINEAS_COMENTARIO)
    alto = RELLENO + ALTO_CABECERA_POST + 8 + len(lineas) * ALTO_LINEA_POST
    if pub.foto:
        alto += 8 + ALTO_FOTO_POST
    alto += 6 + ALTO_FILA_DATOS
    if lineas_comentario:
        alto += 2 + len(lineas_comentario) * ALTO_LINEA_COMENTARIO
    alto += RELLENO - 4
    return _MedidasPost(alto, lineas, comentario, lineas_comentario)


def _dibujar_feed(d, pantalla, s, arriba, celular, feed, segundos, reducir):
    """La transmisión EN VIVO arriba y las publicaciones debajo, desplazables."""
    contenido = pygame.Rect(s.left, arriba, s.width, s.bottom - ALTO_ZONA_INICIO - arriba)
    d.contenido = contenido
    if feed is None:
        _texto(d, pantalla, TEXTO_SIN_FEED, contenido.inflate(-40, 0), assets.COLOR_TEXTO_SECUNDARIO, T_TEXTO,
               ancla="center")
        return
    ancho = s.width - 2 * MARGEN
    items = []  # (clave, alto, objeto, medidas)
    vivo = feed.en_vivo
    if vivo is not None:
        items.append((("vivo",), ALTO_TARJETA_VIVO, vivo, None))
    for pub in list(feed.publicaciones or ()):
        medidas = _medir_post(pub, ancho)
        items.append((("pub", pub.id), medidas.alto, pub, medidas))
    posiciones = []
    y = SEPARACION
    for item in items:
        posiciones.append(y)
        y += item[1] + SEPARACION
    d.alto_contenido = y

    # Si se está leyendo más abajo y llegan publicaciones arriba, la vista no
    # salta: el desplazamiento crece lo mismo que bajó la tarjeta que se leía.
    if celular.ancla_feed is not None and celular.scroll_feed > 0:
        for item, posicion in zip(items, posiciones):
            if item[0] == celular.ancla_feed[0]:
                celular.scroll_feed += posicion - celular.ancla_feed[1]
                break
    celular.limitar_scroll(FEED, d.alto_contenido, contenido.height)
    scroll = round(celular.scroll_feed)
    celular.ancla_feed = None
    for item, posicion in zip(items, posiciones):
        if posicion + item[1] > scroll:
            celular.ancla_feed = (item[0], posicion)
            break
    total = _entero(feed.total_publicaciones)
    if scroll <= UMBRAL_ARRIBA:
        celular.publicaciones_vistas = total

    anterior = _con_recorte(pantalla, contenido)
    visible = pantalla.get_clip()
    try:
        for item, posicion in zip(items, posiciones):
            top = contenido.top + posicion - scroll
            if top + item[1] <= contenido.top:
                continue
            if top >= contenido.bottom:
                break  # las de más abajo tampoco se ven
            rect = pygame.Rect(s.left + MARGEN, top, ancho, item[1])
            if item[0][0] == "vivo":
                _dibujar_vivo(d, pantalla, rect, item[2], celular, segundos, reducir, visible)
            else:
                _dibujar_post(d, pantalla, rect, item[2], item[3], celular, segundos, reducir, visible)
    finally:
        pantalla.set_clip(anterior)
    if scroll > UMBRAL_ARRIBA and total > celular.publicaciones_vistas:
        _pildora(d, pantalla, TEXTO_NUEVAS, (contenido.centerx, contenido.top + 8), "midtop", True)
    _banner(d, pantalla, s, feed, segundos, reducir)
    # Un clic sobre la píldora o el banner no es un "me gusta" de lo que hay debajo.
    tapan = [rect for rect in (d.nuevas, d.banner) if rect is not None]
    d.corazones = [(id_pub, rect) for id_pub, rect in d.corazones if not any(rect.colliderect(t) for t in tapan)]
    d.reposts = [(id_pub, rect) for id_pub, rect in d.reposts if not any(rect.colliderect(t) for t in tapan)]
    d.publicaciones = [(id_pub, rect) for id_pub, rect in d.publicaciones
                       if not any(rect.colliderect(t) for t in tapan)]


def _fondo_tarjeta(pantalla, rect):
    pygame.draw.rect(pantalla, COLOR_TARJETA, rect, border_radius=RADIO_TARJETA)
    pygame.draw.rect(pantalla, COLOR_BORDE_TARJETA, rect, 1, border_radius=RADIO_TARJETA)


def _dibujar_vivo(d, pantalla, rect, vivo, celular, segundos, reducir, visible):
    """Tarjeta EN VIVO: foto con "EN VIVO", "N viendo" y el título; debajo,
    las últimas líneas del chat en vivo, que suben cuando llega una nueva."""
    _fondo_tarjeta(pantalla, rect)
    foto = pygame.Rect(rect.left, rect.top, rect.width, ALTO_FOTO_VIVO)
    pantalla.blit(_foto(vivo.foto, foto.size, RADIO_TARJETA, solo_arriba=True), foto)
    pantalla.blit(_degradado(foto.width, ALTO_BANDA_VIVO, assets.COLOR_LEYENDA_FOTO), (foto.left, foto.bottom - ALTO_BANDA_VIVO))
    _pildora_vivo(d, pantalla, (foto.left + 10, foto.top + 10), celular.reloj, reducir, visible)

    viendo = TEXTO_VIENDO.format(formatear_cifra(vivo.espectadores(segundos)))
    ancho_viendo = fuente(T_CHIP, True).size(viendo)[0] + 34
    chip = pygame.Rect(0, 0, min(ancho_viendo, foto.width // 2), 20)
    chip.topright = (foto.right - 10, foto.top + 10)
    dibujo.panel_alfa(pantalla, chip, assets.COLOR_LEYENDA_FOTO, radio=10)
    _icono_ojo(pantalla, (chip.left + 13, chip.centery), 13, assets.COLOR_TEXTO_HUD)
    _texto(d, pantalla, viendo, pygame.Rect(chip.left + 24, chip.top, chip.width - 30, chip.height), assets.COLOR_TEXTO_HUD,
           T_CHIP, True, ancla="midleft", visible=visible)

    ancho = foto.width - 2 * RELLENO
    _texto(d, pantalla, vivo.titulo, pygame.Rect(foto.left + RELLENO, foto.bottom - 40, ancho, 18), assets.COLOR_TEXTO_HUD,
           T_TEXTO, True, minimo=T_CHIP, visible=visible)
    meta = f"{vivo.usuario} · {_duracion(vivo.duracion(segundos))}"
    _texto(d, pantalla, meta, pygame.Rect(foto.left + RELLENO, foto.bottom - 21, ancho, 16), assets.COLOR_TITULO_LUZ,
           T_CHIP, visible=visible)

    area = pygame.Rect(rect.left + RELLENO, foto.bottom + 6, ancho, LINEAS_VIVO * ALTO_LINEA_VIVO)
    _chat_en_vivo(d, pantalla, area, vivo.mensajes, segundos, reducir, visible)


def _chat_en_vivo(d, pantalla, area, mensajes, segundos, reducir, visible):
    """Las últimas LINEAS_VIVO líneas del chat en vivo ("Nombre: texto"). Cuando
    llega una, todas suben una línea en DESLIZAR s (la de arriba se va por el
    borde) y las más viejas se ven más tenues."""
    lista = list(mensajes or ())[-(LINEAS_VIVO + 1):]
    recorte = area.clip(visible)
    if recorte.width <= 0 or recorte.height <= 0:
        return
    if not lista:
        _texto(d, pantalla, TEXTO_ESPERANDO_VIVO, pygame.Rect(area.left, area.bottom - ALTO_LINEA_VIVO, area.width,
                                                              ALTO_LINEA_VIVO),
               assets.COLOR_TEXTO_SECUNDARIO, T_CHICO, visible=recorte)
        return
    desliz = 0
    if not reducir:
        edad = segundos - _float(lista[-1].segundos)
        if 0 <= edad < DESLIZAR:
            desliz = round((1 - _suave(edad / DESLIZAR)) * ALTO_LINEA_VIVO)
    anterior = _con_recorte(pantalla, recorte)
    try:
        for orden, mensaje in enumerate(reversed(lista)):  # 0 = el más nuevo, abajo
            y = area.bottom - (orden + 1) * ALTO_LINEA_VIVO + desliz
            if y + ALTO_LINEA_VIVO <= area.top:
                break
            alfa = 255 if orden < 2 else 200 if orden == 2 else 130
            _linea_vivo(d, pantalla, pygame.Rect(area.left, y, area.width, ALTO_LINEA_VIVO), mensaje, recorte, alfa)
    finally:
        pantalla.set_clip(anterior)


def _linea_vivo(d, pantalla, caja, mensaje, recorte, alfa):
    nombre = str(mensaje.autor or "")
    color = COLORES_NOMBRES_VIVO[zlib.crc32(nombre.encode("utf-8")) % len(COLORES_NOMBRES_VIVO)]
    caja_nombre = pygame.Rect(caja.left, caja.top, round(caja.width * 0.45), caja.height)
    rect_nombre = _texto(d, pantalla, f"{nombre}:", caja_nombre, color, T_CHICO, True, ancla="midleft", visible=recorte,
                         alfa=alfa)
    izquierda = rect_nombre.right + 6
    _texto(d, pantalla, mensaje.texto, pygame.Rect(izquierda, caja.top, caja.right - izquierda, caja.height),
           assets.COLOR_TEXTO_HUD, T_CHICO, ancla="midleft", visible=recorte, alfa=alfa)


def _chip(d, pantalla, texto, color, topright, visible):
    """Chip de contexto de una publicación: texto y borde de su color sobre un
    fondo apenas teñido."""
    ancho = fuente(T_CHIP, True).size(texto)[0] + 14
    rect = pygame.Rect(0, 0, ancho, ALTO_CHIP_POST)
    rect.topright = topright
    pygame.draw.rect(pantalla, _mezclar(COLOR_TARJETA, color, 0.16), rect, border_radius=ALTO_CHIP_POST // 2)
    pygame.draw.rect(pantalla, color, rect, 1, border_radius=ALTO_CHIP_POST // 2)
    _texto(d, pantalla, texto, rect, color, T_CHIP, True, ancla="center", visible=visible)
    return rect


def _dibujar_post(d, pantalla, rect, pub, medidas, celular, segundos, reducir, visible):
    """Tarjeta de una publicación: cabecera (avatar, nombre, "@usuario · hace
    X" y chips), texto, foto opcional, fila de estadísticas que suben en vivo
    y el último comentario."""
    _fondo_tarjeta(pantalla, rect)
    tarjeta = rect.clip(visible)
    if tarjeta.width > 0 and tarjeta.height > 0:
        d.publicaciones.append((pub.id, tarjeta))  # clic en la tarjeta: se abre con todos sus comentarios
    x = rect.left + RELLENO
    interior = rect.width - 2 * RELLENO
    derecha = rect.right - RELLENO
    y = rect.top + RELLENO
    autor = str(pub.autor or "")
    usuario = str(pub.usuario or "")
    avatar = _avatar_cuenta(autor, usuario, RADIO_AVATAR_POST)
    pantalla.blit(avatar, avatar.get_rect(center=(x + RADIO_AVATAR_POST, y + RADIO_AVATAR_POST)))

    chips = []
    etiqueta = str(pub.etiqueta or "")
    if etiqueta:
        chips.append((etiqueta, COLOR_ETIQUETA.get(etiqueta, assets.COLOR_CIVITAS)))
    if pub.en_tendencia(segundos):
        chips.append((TEXTO_TENDENCIA, assets.COLOR_MAGENTA))
    limites = [derecha, derecha]  # dónde termina el nombre y dónde la línea de abajo
    for fila, (texto_chip, color_chip) in enumerate(chips):
        chip = _chip(d, pantalla, texto_chip, color_chip, (derecha, y + 1 + fila * (ALTO_CHIP_POST + 2)), visible)
        limites[fila] = chip.left - 8
    texto_x = x + 2 * RADIO_AVATAR_POST + 10
    _texto(d, pantalla, autor or usuario, pygame.Rect(texto_x, y, limites[0] - texto_x, 18), assets.COLOR_TEXTO_HUD,
           T_TEXTO, True, visible=visible)
    hace = str(pub.hace(segundos))
    meta = f"{usuario} · {hace}" if usuario and usuario != autor else hace
    _texto(d, pantalla, meta, pygame.Rect(texto_x, y + 19, limites[1] - texto_x, 16), assets.COLOR_TEXTO_SECUNDARIO,
           T_CHICO, visible=visible)

    y += ALTO_CABECERA_POST + 8
    for linea in medidas.lineas:
        _texto(d, pantalla, linea, pygame.Rect(x, y, interior, ALTO_LINEA_POST), assets.COLOR_TEXTO_HUD, T_TEXTO,
               visible=visible)
        y += ALTO_LINEA_POST
    if pub.foto:
        y += 8
        pantalla.blit(_foto(pub.foto, (interior, ALTO_FOTO_POST), 10), (x, y))
        y += ALTO_FOTO_POST
    y += 6
    fila = pygame.Rect(x, y, interior, ALTO_FILA_DATOS)
    _fila_datos(d, pantalla, fila, rect, pub, celular, segundos, visible)
    if medidas.lineas_comentario:
        area = pygame.Rect(x, fila.bottom + 2, interior, len(medidas.lineas_comentario) * ALTO_LINEA_COMENTARIO)
        _comentario(d, pantalla, area, medidas, segundos, reducir, visible)


def _fila_datos(d, pantalla, fila, tarjeta, pub, celular, segundos, visible):
    """Me gusta, compartidos y comentarios. Al subir, el número destella con
    el color de su ícono y sale un "+N" que sube y se desvanece."""
    valores = [_entero(v) for v in tuple(pub.estadisticas(segundos))[:3]]
    valores += [0] * (3 - len(valores))
    propio = pub.id in celular.me_gusta
    compartida = pub.id in getattr(celular, "reposts", ())
    valores[0] += int(propio)
    valores[1] += int(compartida)
    valores[2] += len(getattr(celular, "comentarios_propios", {}).get(pub.id, ()))
    marcados = (propio, compartida, False)
    paso = fila.width // 3
    for indice, valor in enumerate(valores):
        izquierda = fila.left + indice * paso
        centro = (izquierda + 10, fila.centery)
        golpe = celular.golpe((pub.id, indice)) if indice < 2 and hasattr(celular, "golpe") else None
        _icono_dato(pantalla, indice, centro, marcados[indice], golpe)
        animacion = celular.notar_cifra((pub.id, indice), valor)
        base = COLORES_PROPIO[indice] if marcados[indice] else assets.COLOR_TEXTO_SECUNDARIO
        color = _mezclar(base, COLORES_CIFRA[indice], animacion[1]) if animacion else base
        caja = pygame.Rect(izquierda + 24, fila.top, paso - 28, fila.height)
        numero = _texto(d, pantalla, formatear_cifra(valor), caja, color, T_CHICO, True, ancla="midleft", visible=visible)
        if animacion:
            _mas_n(d, pantalla, animacion, numero, tarjeta, COLORES_CIFRA[indice], visible)
        if indice < 2:
            zona = pygame.Rect(izquierda - 4, fila.top, max(64, numero.right - izquierda + 10), fila.height).clip(visible)
            if zona.width > 0 and zona.height > 0:
                (d.corazones if indice == 0 else d.reposts).append((pub.id, zona))


def _icono_dato(pantalla, indice, centro, marcado, golpe):
    """Ícono de una estadística. Marcado (me gusta o repost propio): lleno y de
    su color. Al tocarlo "salta": crece y vuelve, con un anillo que se abre y
    se desvanece (golpe = avance 0..1 de esa animación)."""
    tamanio = (20, 18, 18)[indice]
    color = COLORES_PROPIO[indice] if marcado else assets.COLOR_TEXTO_SECUNDARIO
    if golpe is not None:
        tamanio = round(tamanio * (1 + 0.55 * math.sin(math.pi * golpe)))
        radio = round(8 + 16 * golpe)
        anillo = pygame.Surface((radio * 2 + 4, radio * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(anillo, (*_rgb(COLORES_PROPIO[indice]), round(200 * (1 - golpe))), (radio + 2, radio + 2), radio, 2)
        pantalla.blit(anillo, anillo.get_rect(center=centro))
    if indice == 0:
        celular_render.dibujar_icono(pantalla, "corazon", centro, tamanio, color, grosor=0 if marcado else 2)
    elif indice == 1:
        celular_render.dibujar_icono(pantalla, "compartir", centro, tamanio, color, grosor=3 if marcado else 2)
    else:
        _icono_globo(pantalla, centro, tamanio, color)


def _mas_n(d, pantalla, animacion, numero, tarjeta, color, visible):
    """El "+N" de una cifra que subió: sale del número, sube y se desvanece."""
    delta, queda = animacion
    texto = f"+{formatear_cifra(delta)}"
    superficie = _superficie(texto, T_CHIP, True, _rgb(color))
    rect = superficie.get_rect(midbottom=(numero.centerx, numero.top + 3 - round((1 - queda) * SUBIDA_CIFRA)))
    caja = tarjeta.inflate(-6, -6)
    rect.clamp_ip(caja)
    _texto(d, pantalla, texto, caja, color, T_CHIP, True, posicion=rect.topleft, visible=visible,
           alfa=255 * min(1.0, queda * 1.6))


def _comentario(d, pantalla, area, medidas, segundos, reducir, visible):
    """El último comentario en gris ("Nombre:" más claro). El nuevo entra
    desde abajo de su renglón mientras aparece."""
    comentario = medidas.comentario
    recorte = area.clip(visible)
    if recorte.width <= 0 or recorte.height <= 0:
        return
    bajada, alfa = 0, 255
    edad = segundos - _float(comentario.segundos)
    if not reducir and 0 <= edad < DESLIZAR:
        avance = _suave(edad / DESLIZAR)
        bajada, alfa = round((1 - avance) * area.height), 255 * avance
    nombre = f"{comentario.autor}:"
    anterior = _con_recorte(pantalla, recorte)
    try:
        for numero, linea in enumerate(medidas.lineas_comentario):
            caja = pygame.Rect(area.left, area.top + numero * ALTO_LINEA_COMENTARIO + bajada, area.width, ALTO_LINEA_COMENTARIO)
            if numero == 0 and linea.startswith(nombre):
                rect_nombre = _texto(d, pantalla, nombre, pygame.Rect(caja.left, caja.top, caja.width, caja.height),
                                     assets.COLOR_TEXTO_HUD, T_CHICO, True, visible=recorte, alfa=alfa)
                resto = pygame.Rect(rect_nombre.right, caja.top, caja.right - rect_nombre.right, caja.height)
                _texto(d, pantalla, linea[len(nombre):], resto, assets.COLOR_TEXTO_SECUNDARIO, T_CHICO, visible=recorte,
                       alfa=alfa)
            else:
                _texto(d, pantalla, linea, caja, assets.COLOR_TEXTO_SECUNDARIO, T_CHICO, visible=recorte, alfa=alfa)
    finally:
        pantalla.set_clip(anterior)


def _banner(d, pantalla, s, feed, segundos, reducir):
    """La notificación más reciente baja desde arriba de la pantalla, se queda
    y vuelve a subir (DURACION_BANNER s en total)."""
    notificaciones = list(feed.notificaciones or ())
    if not notificaciones:
        return
    notificacion = notificaciones[-1]
    edad = segundos - _float(notificacion.segundos, -1e9)
    if not 0 <= edad < DURACION_BANNER:
        return
    avance = 1.0 if reducir else _suave(min(1.0, edad / ENTRADA_BANNER, (DURACION_BANNER - edad) / ENTRADA_BANNER))
    final = s.top + assets.ALTO_BARRA_ESTADO_CELULAR + 4
    inicio = s.top - ALTO_BANNER - 8
    rect = pygame.Rect(s.left + 8, round(inicio + (final - inicio) * avance), s.width - 16, ALTO_BANNER)
    visible = rect.clip(pantalla.get_clip())
    if visible.width <= 0 or visible.height <= 0:
        return
    dibujo.panel_alfa(pantalla, rect.move(0, 4), (0, 0, 0, 120), radio=16)
    dibujo.panel(pantalla, rect, COLOR_BANNER, assets.COLOR_BORDE_VIDRIO, 1, radio=16)
    cuadro = pygame.Rect(rect.left + 11, rect.centery - 18, 36, 36)
    _icono_notificacion(pantalla, cuadro, str(notificacion.icono))
    x = cuadro.right + 11
    ancho = rect.right - 12 - x
    lineas = _lineas(str(notificacion.texto), ancho, T_CHICO, False, 2)
    bloque = 15 + 2 + len(lineas) * 16
    y = rect.centery - bloque // 2
    _texto(d, pantalla, TEXTO_BANNER, pygame.Rect(x, y, ancho, 15), assets.COLOR_TEXTO_SECUNDARIO, T_CHIP, True,
           visible=visible)
    for numero, linea in enumerate(lineas):
        _texto(d, pantalla, linea, pygame.Rect(x, y + 17 + numero * 16, ancho, 16), assets.COLOR_TEXTO_HUD, T_CHICO,
               visible=visible)
    d.banner = visible


# ----------------------------------------------------------------------
# Publicación abierta: completa, con todos sus comentarios y para comentar
# ----------------------------------------------------------------------
ALTO_CABECERA_DETALLE = 36
ALTO_TITULO_COMENTARIOS = 30
RADIO_AVATAR_COMENTARIO = 13
LINEAS_COMENTARIO_DETALLE = 4
LINEAS_POST_DETALLE = 30


@dataclass(frozen=True)
class _FilaComentario:
    autor: str
    texto: str
    segundos: float
    propio: bool
    lineas: tuple
    alto: int


def _comentarios_detalle(celular, feed, pub, ancho):
    """Del más nuevo al más viejo: los propios y los que llegan en vivo, y
    después los que ya tenía (feed.comentarios_anteriores, iguales en todas las PCs)."""
    recientes = [(c.autor, c.texto, _float(c.segundos), False) for c in (pub.comentarios or ())]
    recientes += [(TEXTO_TU, texto, _float(segundos), True)
                  for texto, segundos in getattr(celular, "comentarios_propios", {}).get(pub.id, ())]
    recientes.sort(key=lambda fila: fila[2], reverse=True)
    anteriores = getattr(feed, "comentarios_anteriores", None)
    viejos = [(c.autor, c.texto, _float(c.segundos), False) for c in (anteriores(pub) if callable(anteriores) else ())]
    filas = []
    interior = ancho - 2 * RELLENO - 2 * RADIO_AVATAR_COMENTARIO - 10
    for autor, texto, segundos, propio in recientes + viejos:
        lineas = _lineas(str(texto), interior, T_CHICO, False, LINEAS_COMENTARIO_DETALLE)
        filas.append(_FilaComentario(str(autor), str(texto), segundos, propio, lineas,
                                     8 + 17 + len(lineas) * ALTO_LINEA_COMENTARIO + 6))
    return filas


def _dibujar_detalle(d, pantalla, s, arriba, celular, feed, segundos, reducir):
    """La publicación abierta: flecha para volver, la tarjeta completa (con me
    gusta y repost), todos sus comentarios (los nuevos entran deslizándose) y
    la caja para comentar."""
    pub = next((p for p in (feed.publicaciones or ()) if p.id == celular.publicacion_abierta), None)
    if pub is None:  # salió del feed (solo se guardan las últimas): de vuelta al feed
        celular.cerrar_publicacion()
        _dibujar_feed(d, pantalla, s, arriba, celular, feed, segundos, reducir)
        return
    cabecera = pygame.Rect(s.left, arriba, s.width, ALTO_CABECERA_DETALLE)
    centro = (cabecera.left + 22, cabecera.centery)
    pygame.draw.lines(pantalla, assets.COLOR_TEXTO_HUD, False,
                      [(centro[0] + 5, centro[1] - 8), (centro[0] - 3, centro[1]), (centro[0] + 5, centro[1] + 8)], 3)
    d.volver = pygame.Rect(cabecera.left, cabecera.top, 120, cabecera.height)
    _texto(d, pantalla, TEXTO_PUBLICACION, pygame.Rect(cabecera.left + 40, cabecera.top, 160, cabecera.height),
           assets.COLOR_TEXTO_HUD, T_TEXTO, True, ancla="midleft")
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (s.left, cabecera.bottom - 1),
                     (s.right - 1, cabecera.bottom - 1))

    abajo = s.bottom - ALTO_ZONA_INICIO
    entrada = pygame.Rect(s.left + MARGEN, abajo - ALTO_ENTRADA, s.width - 2 * MARGEN - DIAMETRO_ENVIAR - 8, ALTO_ENTRADA)
    enviar = pygame.Rect(entrada.right + 8, entrada.centery - DIAMETRO_ENVIAR // 2, DIAMETRO_ENVIAR, DIAMETRO_ENVIAR)
    contenido = pygame.Rect(s.left, cabecera.bottom, s.width, entrada.top - 8 - cabecera.bottom)
    d.contenido = contenido
    ancho = s.width - 2 * MARGEN
    medidas = _medir_post(pub, ancho, LINEAS_POST_DETALLE, con_comentario=False)
    filas = _comentarios_detalle(celular, feed, pub, ancho)
    d.alto_contenido = SEPARACION + medidas.alto + ALTO_TITULO_COMENTARIOS + sum(f.alto for f in filas) + SEPARACION
    celular.limitar_scroll(DETALLE, d.alto_contenido, contenido.height)
    y = contenido.top + SEPARACION - round(celular.scroll_detalle)

    anterior = _con_recorte(pantalla, contenido)
    visible = pantalla.get_clip()
    try:
        tarjeta = pygame.Rect(s.left + MARGEN, y, ancho, medidas.alto)
        if tarjeta.bottom > contenido.top:
            _dibujar_post(d, pantalla, tarjeta, pub, medidas, celular, segundos, reducir, visible)
        d.publicaciones = []  # ya está abierta: un clic en la tarjeta no hace nada
        y = tarjeta.bottom
        total = formatear_cifra(_entero(tuple(pub.estadisticas(segundos))[2])
                                + len(celular.comentarios_propios.get(pub.id, ())))
        _texto(d, pantalla, f"{TEXTO_COMENTARIOS} · {total}", pygame.Rect(s.left + MARGEN + 4, y + 8, ancho, 18),
               assets.COLOR_TEXTO_HUD, T_TEXTO, True, visible=visible)
        y += ALTO_TITULO_COMENTARIOS
        for fila in filas:
            if y >= contenido.bottom:
                break
            if y + fila.alto > contenido.top:
                _dibujar_fila_comentario(d, pantalla, pygame.Rect(s.left + MARGEN, y, ancho, fila.alto), fila,
                                         segundos, reducir, visible)
            y += fila.alto
    finally:
        pantalla.set_clip(anterior)
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (s.left, contenido.bottom + 3),
                     (s.right - 1, contenido.bottom + 3))
    _caja_texto(d, pantalla, entrada, enviar, celular, True, reducir, texto=celular.texto_comentario,
                pista=TEXTO_PISTA_COMENTARIO)


def _dibujar_fila_comentario(d, pantalla, rect, fila, segundos, reducir, visible):
    """Avatar, nombre (el propio, "Tú" en violeta), "hace X" y el texto. El
    comentario que acaba de llegar entra desde la derecha mientras aparece."""
    desliz, alfa = 0, 255
    edad = segundos - fila.segundos
    if not reducir and 0 <= edad < DESLIZAR:
        avance = _suave(edad / DESLIZAR)
        desliz, alfa = round((1 - avance) * 40), 255 * avance
    x = rect.left + RELLENO + desliz
    centro = (x + RADIO_AVATAR_COMENTARIO, rect.top + 8 + RADIO_AVATAR_COMENTARIO)
    if fila.propio:
        pygame.draw.circle(pantalla, assets.COLOR_CIVITAS, centro, RADIO_AVATAR_COMENTARIO)
        _texto(d, pantalla, "TÚ", pygame.Rect(centro[0] - 12, centro[1] - 8, 24, 16), assets.COLOR_TEXTO_HUD, T_MIN,
               True, ancla="center", visible=visible, alfa=alfa)
    else:
        avatar = _avatar_cuenta(fila.autor, "", RADIO_AVATAR_COMENTARIO).copy()
        avatar.set_alpha(round(alfa))
        pantalla.blit(avatar, avatar.get_rect(center=centro))
    izquierda = x + 2 * RADIO_AVATAR_COMENTARIO + 10
    ancho = rect.right - RELLENO - izquierda
    color_nombre = assets.COLOR_CIVITAS if fila.propio else assets.COLOR_TEXTO_HUD
    nombre = _texto(d, pantalla, fila.autor, pygame.Rect(izquierda, rect.top + 6, ancho * 2 // 3, 17), color_nombre,
                    T_CHICO, True, visible=visible, alfa=alfa)
    _texto(d, pantalla, f"· {_hace_corto(segundos - fila.segundos)}",
           pygame.Rect(nombre.right + 6, rect.top + 6, max(1, rect.right - RELLENO - nombre.right - 6), 17),
           assets.COLOR_TEXTO_SECUNDARIO, T_CHIP, visible=visible, alfa=alfa)
    color = assets.COLOR_TEXTO_HUD if fila.propio else assets.COLOR_TEXTO_SECUNDARIO
    for numero, linea in enumerate(fila.lineas):
        caja = pygame.Rect(izquierda, rect.top + 25 + numero * ALTO_LINEA_COMENTARIO, ancho, ALTO_LINEA_COMENTARIO)
        _texto(d, pantalla, linea, caja, color, T_CHICO, visible=visible, alfa=alfa)
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (rect.left + RELLENO, rect.bottom - 1),
                     (rect.right - RELLENO, rect.bottom - 1))


def _hace_corto(edad):
    """"ahora", "3 min", "2 h" (al lado del nombre en cada comentario)."""
    edad = max(0.0, _float(edad))
    if edad < 60:
        return "ahora"
    if edad < 3600:
        return f"{int(edad // 60)} min"
    return f"{int(edad // 3600)} h"

# ----------------------------------------------------------------------
# Chat de la sala
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Burbuja:
    mensaje: object
    clase: str  # "sistema", "propia" o "ajena"
    alto: int  # con la separación de arriba
    separacion: int
    lineas: tuple
    ancho: int  # ancho de la burbuja (o de la píldora del sistema)
    etiqueta: bool  # primera de un grupo ajeno: nombre y avatar
    perfil: object


def _medir_mensajes(mensajes, perfiles, id_local, ancho_contenido):
    """Una _Burbuja por mensaje, en orden. Los mensajes seguidos del mismo
    jugador forman un grupo: el nombre y el avatar van solo en el primero."""
    ancho_max = ancho_contenido - 2 * MARGEN - (DIAMETRO_AVATAR_CHAT + 8) - 30
    ancho_texto = ancho_max - 2 * RELLENO_BURBUJA[0]
    burbujas = []
    anterior = None
    for mensaje in mensajes:
        tipo = getattr(mensaje, "tipo", MENSAJE_JUGADOR)
        perfil = perfiles(mensaje.autor)
        if tipo in (MENSAJE_ENTRO, MENSAJE_SALIO):
            plantilla = TEXTO_ENTRO if tipo == MENSAJE_ENTRO else TEXTO_SALIO
            texto = plantilla.format(perfil.etiqueta)
            ancho = min(ancho_contenido - 2 * MARGEN, fuente(T_CHICO).size(texto)[0] + 24)
            burbujas.append(_Burbuja(mensaje, "sistema", SEPARACION_GRUPO + ALTO_SISTEMA, SEPARACION_GRUPO, (texto,),
                                     ancho, False, perfil))
            anterior = None
            continue
        propia = mensaje.autor == id_local
        sigue = anterior is not None and anterior.autor == mensaje.autor
        lineas = _lineas(mensaje.texto, ancho_texto, T_TEXTO) or ("",)
        f = fuente(T_TEXTO)
        ancho = max(44, max(f.size(linea)[0] for linea in lineas) + 2 * RELLENO_BURBUJA[0])
        alto_burbuja = len(lineas) * ALTO_LINEA_CHAT + 2 * RELLENO_BURBUJA[1]
        etiqueta = not propia and not sigue
        separacion = SEPARACION_MISMO if sigue else SEPARACION_GRUPO
        alto = separacion + (ALTO_ETIQUETA_CHAT if etiqueta else 0) + alto_burbuja
        burbujas.append(_Burbuja(mensaje, "propia" if propia else "ajena", alto, separacion, lineas, ancho, etiqueta, perfil))
        anterior = mensaje
    return burbujas


def _dibujar_chat(d, pantalla, s, arriba, celular, mensajes, perfiles, id_local, puede_escribir, respuestas, segundos,
                  reducir):
    """Burbujas (propias a la derecha, ajenas a la izquierda con nombre y
    muñeco, del sistema al centro), respuestas rápidas y la caja de texto."""
    abajo = s.bottom - ALTO_ZONA_INICIO
    respuestas = [str(r) for r in (respuestas or ()) if str(r).strip()] if puede_escribir else []
    entrada = pygame.Rect(s.left + MARGEN, abajo - ALTO_ENTRADA, s.width - 2 * MARGEN, ALTO_ENTRADA)
    enviar = None
    if puede_escribir:
        entrada.width -= DIAMETRO_ENVIAR + 8
        enviar = pygame.Rect(entrada.right + 8, entrada.centery - DIAMETRO_ENVIAR // 2, DIAMETRO_ENVIAR, DIAMETRO_ENVIAR)
    base = entrada.top
    fila = None
    if respuestas:
        fila = pygame.Rect(s.left + MARGEN, entrada.top - 8 - ALTO_RESPUESTA, s.width - 2 * MARGEN, ALTO_RESPUESTA)
        base = fila.top
    contenido = pygame.Rect(s.left, arriba, s.width, base - 8 - arriba)
    d.contenido = contenido

    burbujas = _medir_mensajes(mensajes, perfiles, id_local, contenido.width)
    posiciones = []
    y = 0
    for burbuja in burbujas:
        posiciones.append(y)
        y += burbuja.alto
    d.alto_contenido = y + (SEPARACION if burbujas else 0)

    # Leyendo mensajes viejos: si llegan nuevos abajo, la vista no se mueve.
    if celular.ancla_chat is not None and celular.scroll_chat > 0:
        for burbuja, posicion in zip(burbujas, posiciones):
            if burbuja.mensaje.numero == celular.ancla_chat[0]:
                celular.scroll_chat += (d.alto_contenido - posicion) - celular.ancla_chat[1]
                break
    celular.limitar_scroll(CHAT, d.alto_contenido, contenido.height)
    scroll = round(celular.scroll_chat)
    origen = contenido.bottom - d.alto_contenido + scroll  # y en pantalla del comienzo de la lista
    celular.ancla_chat = None
    for burbuja, posicion in zip(burbujas, posiciones):
        if origen + posicion + burbuja.alto > contenido.top:
            celular.ancla_chat = (burbuja.mensaje.numero, d.alto_contenido - posicion)
            break
    if scroll <= UMBRAL_ARRIBA or celular.mensajes_vistos is None:  # pegado abajo: se vio todo
        celular.mensajes_vistos = _entero(burbujas[-1].mensaje.numero) if burbujas else 0

    anterior = _con_recorte(pantalla, contenido)
    visible = pantalla.get_clip()
    try:
        if not burbujas:
            _chat_vacio(d, pantalla, contenido, visible)
        for burbuja, posicion in zip(burbujas, posiciones):
            top = origen + posicion
            if top + burbuja.alto <= contenido.top:
                continue
            if top >= contenido.bottom:
                break
            _dibujar_burbuja(d, pantalla, contenido, top + burbuja.separacion, burbuja, visible)
    finally:
        pantalla.set_clip(anterior)
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (s.left, contenido.bottom + 3),
                     (s.right - 1, contenido.bottom + 3))
    nuevos = sum(1 for b in burbujas if b.clase == "ajena" and _entero(b.mensaje.numero) > _entero(celular.mensajes_vistos))
    if scroll > UMBRAL_ARRIBA and nuevos:
        _pildora(d, pantalla, TEXTO_NUEVOS_MENSAJES, (contenido.centerx, contenido.bottom - 8), "midbottom", False)
    if fila is not None:
        _respuestas_rapidas(d, pantalla, fila, respuestas, celular.respuesta_rapida)
    _caja_texto(d, pantalla, entrada, enviar, celular, puede_escribir, reducir)


def _chat_vacio(d, pantalla, contenido, visible):
    centro = (contenido.centerx, contenido.centery - 34)
    _icono_globo(pantalla, centro, 44, assets.COLOR_TEXTO_APAGADO, 3)
    ancho = contenido.width - 70
    lineas = _lineas(TEXTO_CHAT_VACIO, ancho, T_TEXTO, False, 4)
    y = centro[1] + 34
    for linea in lineas:
        _texto(d, pantalla, linea, pygame.Rect(contenido.left + 35, y, ancho, ALTO_LINEA_POST), assets.COLOR_TEXTO_SECUNDARIO,
               T_TEXTO, ancla="midtop", visible=visible)
        y += ALTO_LINEA_POST


def _dibujar_burbuja(d, pantalla, contenido, y, burbuja, visible):
    izquierda = contenido.left + MARGEN
    derecha = contenido.right - MARGEN
    if burbuja.clase == "sistema":
        pildora = pygame.Rect(0, 0, burbuja.ancho, ALTO_SISTEMA)
        pildora.midtop = (contenido.centerx, y)
        pygame.draw.rect(pantalla, COLOR_TARJETA, pildora, border_radius=ALTO_SISTEMA // 2)
        _texto(d, pantalla, burbuja.lineas[0], pildora.inflate(-12, 0), assets.COLOR_TEXTO_SECUNDARIO, T_CHICO,
               ancla="center", visible=visible)
        return
    alto = len(burbuja.lineas) * ALTO_LINEA_CHAT + 2 * RELLENO_BURBUJA[1]
    if burbuja.clase == "propia":
        rect = pygame.Rect(derecha - burbuja.ancho, y, burbuja.ancho, alto)
        pygame.draw.rect(pantalla, COLOR_BURBUJA_PROPIA, rect, border_radius=RADIO_BURBUJA, border_bottom_right_radius=4)
    else:
        x = izquierda + DIAMETRO_AVATAR_CHAT + 8
        if burbuja.etiqueta:
            avatar = _avatar_jugador(burbuja.perfil, DIAMETRO_AVATAR_CHAT)
            pantalla.blit(avatar, (izquierda - 2, y))
            perfil = burbuja.perfil
            nombre = perfil.etiqueta + (SUFIJO_FANTASMA if perfil.fantasma else "")
            color = assets.COLOR_TEXTO_SECUNDARIO if perfil.fantasma else _rgb(perfil.color)
            _texto(d, pantalla, nombre, pygame.Rect(x + 2, y, derecha - x - 2, ALTO_ETIQUETA_CHAT), color, T_CHIP, True,
                   visible=visible)
            y += ALTO_ETIQUETA_CHAT
        rect = pygame.Rect(x, y, burbuja.ancho, alto)
        esquina = 4 if burbuja.etiqueta else RADIO_BURBUJA
        pygame.draw.rect(pantalla, COLOR_BURBUJA_AJENA, rect, border_radius=RADIO_BURBUJA, border_top_left_radius=esquina)
    for numero, linea in enumerate(burbuja.lineas):
        caja = pygame.Rect(rect.left + RELLENO_BURBUJA[0], rect.top + RELLENO_BURBUJA[1] + numero * ALTO_LINEA_CHAT,
                           rect.width - 2 * RELLENO_BURBUJA[0], ALTO_LINEA_CHAT)
        _texto(d, pantalla, linea, caja, assets.COLOR_TEXTO_HUD, T_TEXTO, visible=visible)


def _respuestas_rapidas(d, pantalla, fila, respuestas, enfocada):
    """Chips clicables sobre la caja. Si no entran con su ancho natural,
    todos toman el mismo ancho (y el texto se recorta con "…")."""
    f = fuente(T_CHICO, True)
    anchos = [f.size(texto)[0] + 22 for texto in respuestas]
    total = sum(anchos) + SEPARACION_RESPUESTAS * (len(respuestas) - 1)
    if total > fila.width:
        anchos = [(fila.width - SEPARACION_RESPUESTAS * (len(respuestas) - 1)) // len(respuestas)] * len(respuestas)
    x = fila.left
    for indice, (texto, ancho) in enumerate(zip(respuestas, anchos)):
        rect = pygame.Rect(x, fila.top, ancho, fila.height)
        foco = indice == enfocada
        dibujo.panel(pantalla, rect, assets.COLOR_FOCO_FONDO if foco else COLOR_TARJETA,
                     assets.COLOR_CIVITAS if foco else assets.COLOR_BORDE_VIDRIO, 1, radio=fila.height // 2)
        _texto(d, pantalla, texto, rect.inflate(-12, 0), assets.COLOR_TEXTO_HUD, T_CHICO, True, ancla="center")
        d.respuestas.append((indice, rect))
        x = rect.right + SEPARACION_RESPUESTAS


def _caja_texto(d, pantalla, entrada, enviar, celular, puede_escribir, reducir, texto=None,
                pista=TEXTO_PISTA_ENTRADA):
    """La caja de texto: pista o lo escrito (se ve el final) con el cursor que
    parpadea, y el botón enviar. Al fantasma, apagada y sin enviar."""
    radio = entrada.height // 2
    if not puede_escribir:
        pygame.draw.rect(pantalla, COLOR_ENTRADA_APAGADA, entrada, border_radius=radio)
        pygame.draw.rect(pantalla, assets.COLOR_BORDE_VIDRIO, entrada, 1, border_radius=radio)
        celular_render.dibujar_icono(pantalla, "candado", (entrada.left + 22, entrada.centery), 16,
                                     assets.COLOR_TEXTO_SECUNDARIO)
        _texto(d, pantalla, TEXTO_FANTASMA, pygame.Rect(entrada.left + 38, entrada.top, entrada.width - 50, entrada.height),
               assets.COLOR_TEXTO_SECUNDARIO, T_CHICO, ancla="midleft")
        return
    pygame.draw.rect(pantalla, COLOR_ENTRADA, entrada, border_radius=radio)
    pygame.draw.rect(pantalla, assets.COLOR_CIVITAS, entrada, 1, border_radius=radio)
    d.entrada = entrada
    texto = celular.texto if texto is None else texto
    izquierda, derecha = entrada.left + 16, entrada.right - 14
    if len(texto) >= celular.largo_maximo - AVISO_LARGO:
        lleno = len(texto) >= celular.largo_maximo
        contador = _texto(d, pantalla, f"{len(texto)}/{celular.largo_maximo}",
                          pygame.Rect(derecha - 46, entrada.top, 46, entrada.height),
                          assets.COLOR_ALERTA if lleno else assets.COLOR_TEXTO_SECUNDARIO, T_MIN, ancla="midright")
        derecha = contador.left - 8
    caja = pygame.Rect(izquierda, entrada.top, derecha - izquierda, entrada.height)
    if texto:
        escrito = _texto(d, pantalla, _final_que_entra(texto, caja.width - 4, T_TEXTO), caja, assets.COLOR_TEXTO_HUD,
                         T_TEXTO, ancla="midleft")
        cursor_x = escrito.right + 1
    else:
        _texto(d, pantalla, pista, caja, COLOR_PISTA_ENTRADA, T_TEXTO, ancla="midleft")
        cursor_x = izquierda - 3
    if reducir or int(celular.reloj * 2) % 2 == 0:
        pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (cursor_x, entrada.centery - 9), (cursor_x, entrada.centery + 9), 2)
    if enviar is not None:
        activo = bool(texto.strip())
        pygame.draw.circle(pantalla, assets.COLOR_CIVITAS if activo else assets.COLOR_FONDO_CHIP, enviar.center,
                           enviar.width // 2)
        cx, cy = enviar.center
        t = enviar.width * 0.24
        avion = [(cx - t, cy - t), (cx + t * 1.2, cy), (cx - t, cy + t), (cx - t * 0.4, cy)]
        pygame.draw.polygon(pantalla, assets.COLOR_TEXTO_HUD if activo else assets.COLOR_TEXTO_APAGADO,
                            [(round(px + 1), round(py)) for px, py in avion])
        d.enviar = enviar


# ----------------------------------------------------------------------
# Ratón y barra de controles
# ----------------------------------------------------------------------


def objetivo_en(dibujado, posicion):
    """Qué hay bajo `posicion` en el último celular dibujado: (FUERA, None),
    (CERRAR, None), (PESTANA, app), (NUEVAS, None), (ENVIAR, None),
    (ENTRADA, None), (RESPUESTA, i), (ME_GUSTA, id) o (DENTRO, None)."""
    if dibujado is None:
        return FUERA, None
    try:
        punto = (int(posicion[0]), int(posicion[1]))
    except (TypeError, ValueError, IndexError):
        return FUERA, None
    if not dibujado.cuerpo.collidepoint(punto):
        return FUERA, None
    if dibujado.nuevas is not None and dibujado.nuevas.collidepoint(punto):
        return NUEVAS, None
    if dibujado.banner is not None and dibujado.banner.collidepoint(punto):
        return DENTRO, None
    if dibujado.cerrar is not None and dibujado.cerrar.collidepoint(punto):
        return CERRAR, None
    for app, rect in dibujado.pestanas:
        if rect.collidepoint(punto):
            return PESTANA, app
    if dibujado.enviar is not None and dibujado.enviar.collidepoint(punto):
        return ENVIAR, None
    if dibujado.entrada is not None and dibujado.entrada.collidepoint(punto):
        return ENTRADA, None
    for indice, rect in dibujado.respuestas:
        if rect.collidepoint(punto):
            return RESPUESTA, indice
    if dibujado.volver is not None and dibujado.volver.collidepoint(punto):
        return VOLVER, None
    for id_publicacion, rect in dibujado.corazones:
        if rect.collidepoint(punto):
            return ME_GUSTA, id_publicacion
    for id_publicacion, rect in dibujado.reposts:
        if rect.collidepoint(punto):
            return COMPARTIR, id_publicacion
    for id_publicacion, rect in dibujado.publicaciones:
        if rect.collidepoint(punto):
            return ABRIR, id_publicacion
    return DENTRO, None


def controles(celular, puede_escribir):
    """[(tecla, acción)] para hud.dibujar_barra_controles con el celular abierto."""
    if celular.app == CHAT:
        if puede_escribir:
            return [("Enter", "enviar"), ("Tab", "inicio"), ("↑ ↓ / rueda", "desplazar"), ("Esc", "cerrar")]
        return [("Tab", "inicio"), ("↑ ↓ / rueda", "desplazar"), ("Esc", "cerrar")]
    if getattr(celular, "publicacion_abierta", None) is not None:
        return [("Enter", "comentar"), ("Clic", "me gusta / compartir"), ("↑ ↓ / rueda", "desplazar"),
                ("Esc", "volver")]
    return [("Clic", "abrir / me gusta / compartir"), ("↑ ↓ / rueda", "desplazar"), ("Tab", "chat"),
            ("C / Esc", "cerrar")]
