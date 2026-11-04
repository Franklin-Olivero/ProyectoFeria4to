"""Dibujo de una Cinematica (src/story/cinematica.py), solo presentación.

Pantalla completa con franjas de cine, la ilustración de la toma con un
paneo lento (efecto Ken Burns), fundido entre tomas y subtítulos en
español que se escriben letra a letra. Cada efecto añade su capa:

    paneo           solo la ilustración animada
    glitch          bandas desplazadas, tinte magenta y "ruido": NOVA_404
    notificaciones  tarjetas de Civitas que suben flotando (la red viva)
    caos            el mismo efecto pero multiplicado y con posts falsos
    retrato         el protagonista (retrato del rol) a la izquierda
    titulo          "CIVITAS: CÓDIGO NOVA" con resplandor y subtítulo
    tarjeta         rótulo de capítulo con líneas que se abren
    objetivos       lista de la misión y el botón COMENZAR MISIÓN

Si falta la ilustración de la toma se dibuja un fondo de ciudad en
código (degradado + siluetas), así la cinemática nunca depende de un
archivo. No modifica la cinemática.
"""

import math
import random

import pygame

from src.core import assets
from src.story import cinematica as cine
from src.ui import dibujo, layout, sprites
from src.ui.fuentes import fuente

TEXTO_CONTINUAR = "Enter: siguiente"
TEXTO_SALTAR = "Esc: saltar"
TEXTO_COMENZAR = "COMENZAR MISIÓN"
TEXTO_ENTER_COMENZAR = "Enter"

# Publicaciones ficticias para las notificaciones flotantes (sin personas reales).
POSTS_CIVITAS = (
    ("@NovaAlDia", "Hoy abre la feria del barrio. ¡Vamos todos!"),
    ("@ColegioCentral", "Recordatorio: reunión de padres el jueves."),
    ("@HospitalNova", "Campaña de vacunación este fin de semana."),
    ("@BetoTienda", "Promoción de pan recién hecho hasta las 10."),
    ("@AnaDocente", "Mis estudiantes ganaron el concurso de ciencia."),
    ("@RutaNova", "Cambio de horario en la ruta 14 desde el lunes."),
    ("@CamiEstudia", "¿Alguien tiene los apuntes de historia?"),
)
POSTS_FALSOS = (
    ("@MamasNovaUnidas", "URGENTE: mañana cierran TODOS los colegios."),
    ("@NovaDespierta", "¡ALERTA! El hospital deja de atender esta noche."),
    ("@DatosNovaHoy", "EXCLUSIVO: la encuesta ya tiene ganador. Los demás callan."),
    ("@eco_nova_ok", "Comparte antes de que lo borren."),
    ("@VerdadNova", "Un candidato acusado sin pruebas. ¿Casualidad?"),
)

_cache_fondo_codigo = {}
_rng_glitch = random.Random(404)


def dibujar_cinematica(pantalla, cinematica, dt=0.0, reducir_movimiento=False):
    toma = cinematica.actual
    if toma is None:
        return
    tiempo = cinematica.tiempo
    fraccion = cinematica.fraccion
    pantalla.fill(assets.COLOR_LETTERBOX)
    _dibujar_fondo(pantalla, toma, tiempo, fraccion, reducir_movimiento)

    if toma.efecto == cine.EFECTO_GLITCH:
        _glitch(pantalla, tiempo, reducir_movimiento)
    elif toma.efecto == cine.EFECTO_NOTIFICACIONES:
        _notificaciones(pantalla, tiempo, assets.CANTIDAD_NOTIFICACIONES_CIVITAS, falsas=False)
    elif toma.efecto == cine.EFECTO_CAOS:
        _notificaciones(pantalla, tiempo, assets.CANTIDAD_NOTIFICACIONES_CAOS, falsas=True)
    elif toma.efecto == cine.EFECTO_RETRATO:
        _retrato(pantalla, toma, tiempo)

    _letterbox(pantalla)
    if toma.efecto == cine.EFECTO_TITULO:
        _titulo(pantalla, toma, tiempo)
    elif toma.efecto == cine.EFECTO_TARJETA:
        _tarjeta(pantalla, toma, tiempo)
    elif toma.efecto == cine.EFECTO_OBJETIVOS:
        _objetivos(pantalla, toma, tiempo)
    if toma.texto and toma.efecto not in (cine.EFECTO_TITULO, cine.EFECTO_TARJETA, cine.EFECTO_OBJETIVOS):
        _subtitulo(pantalla, toma, tiempo)
    _fundidos(pantalla, toma, tiempo)
    _controles(pantalla, cinematica, toma)


# ----------------------------------------------------------------------
# Fondo
# ----------------------------------------------------------------------


def _dibujar_fondo(pantalla, toma, tiempo, fraccion, reducir_movimiento):
    ancho, alto = pantalla.get_size()
    imagen = sprites.fondo_historia(toma.fondo, (ancho, alto)) if toma.fondo else None
    if imagen is None:
        imagen = _fondo_en_codigo((ancho, alto))
    if reducir_movimiento or toma.espera:
        pantalla.blit(imagen, (0, 0))
        return
    # Ken Burns: acercamiento lento y paneo suave, distinto por toma (según su id).
    semilla = sum(ord(c) for c in toma.id)
    zoom = 1.0 + (assets.ZOOM_KEN_BURNS - 1.0) * (fraccion if semilla % 2 == 0 else 1 - fraccion)
    w, h = round(ancho * zoom), round(alto * zoom)
    escalada = pygame.transform.smoothscale(imagen, (w, h))
    direccion = 1 if semilla % 3 else -1
    dx = round((w - ancho) * (0.5 + 0.5 * direccion * (fraccion - 0.5)))
    dy = round((h - alto) * (0.5 + 0.3 * math.sin(fraccion * math.pi)))
    pantalla.blit(escalada, (-dx, -dy))


def _fondo_en_codigo(tamanio):
    """Ciudad nocturna en degradado con siluetas: fallback sin archivos."""
    if tamanio in _cache_fondo_codigo:
        return _cache_fondo_codigo[tamanio]
    ancho, alto = tamanio
    fondo = pygame.Surface(tamanio)
    arriba, abajo = (10, 8, 30), (36, 14, 54)
    for y in range(alto):
        t = y / max(1, alto - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo))
        pygame.draw.line(fondo, color, (0, y), (ancho, y))
    rng = random.Random(7)
    x = 0
    while x < ancho:
        w = rng.randint(30, 90)
        h = rng.randint(120, 380)
        rect = pygame.Rect(x, alto - h, w, h)
        pygame.draw.rect(fondo, (16, 12, 36), rect)
        for wy in range(rect.top + 10, rect.bottom - 10, 14):
            for wx in range(rect.left + 6, rect.right - 6, 10):
                if rng.random() < 0.35:
                    pygame.draw.rect(fondo, rng.choice((assets.COLOR_TEAL, assets.COLOR_AMARILLO, assets.COLOR_MORADO)),
                                     (wx, wy, 4, 6))
        x += w + rng.randint(4, 16)
    _cache_fondo_codigo[tamanio] = fondo
    return fondo


def _letterbox(pantalla):
    ancho, alto = pantalla.get_size()
    pygame.draw.rect(pantalla, assets.COLOR_LETTERBOX, (0, 0, ancho, assets.ALTO_LETTERBOX))
    pygame.draw.rect(pantalla, assets.COLOR_LETTERBOX, (0, alto - assets.ALTO_LETTERBOX, ancho, assets.ALTO_LETTERBOX))


def _fundidos(pantalla, toma, tiempo):
    """Fundido desde negro al empezar la toma y hacia negro al terminar."""
    d = assets.DURACION_FUNDIDO_TOMA
    alfa = 0
    if tiempo < d:
        alfa = round(255 * (1 - tiempo / d))
    elif not toma.espera and toma.duracion - tiempo < d:
        alfa = round(255 * (1 - max(0.0, toma.duracion - tiempo) / d))
    if alfa > 0:
        velo = pygame.Surface(pantalla.get_size())
        velo.fill(assets.COLOR_LETTERBOX)
        velo.set_alpha(min(255, alfa))
        pantalla.blit(velo, (0, 0))


# ----------------------------------------------------------------------
# Capas por efecto
# ----------------------------------------------------------------------


def _glitch(pantalla, tiempo, reducir_movimiento):
    ancho, alto = pantalla.get_size()
    tinte = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    tinte.fill(assets.COLOR_TINTE_NOVA)
    pantalla.blit(tinte, (0, 0))
    if reducir_movimiento:
        return
    # Bandas horizontales desplazadas que cambian cada pocos frames.
    _rng_glitch.seed(int(tiempo * 12))
    for _ in range(assets.FILAS_GLITCH_NOVA):
        y = _rng_glitch.randint(assets.ALTO_LETTERBOX, alto - assets.ALTO_LETTERBOX - 20)
        h = _rng_glitch.randint(3, 18)
        desplazamiento = _rng_glitch.randint(-assets.INTENSIDAD_GLITCH_NOVA, assets.INTENSIDAD_GLITCH_NOVA)
        banda = pantalla.subsurface((0, y, ancho, h)).copy()
        pantalla.blit(banda, (desplazamiento, y))
    # Líneas de escaneo tenues.
    scan = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y in range(0, alto, 4):
        pygame.draw.line(scan, (0, 0, 0, 40), (0, y), (ancho, y))
    pantalla.blit(scan, (0, 0))


def _notificaciones(pantalla, tiempo, cantidad, falsas):
    """Tarjetas que suben flotando; en el caos se multiplican con el tiempo."""
    ancho, alto = pantalla.get_size()
    rng = random.Random(99 if falsas else 11)
    visibles = cantidad if not falsas else min(cantidad, 3 + int(tiempo * 3.2))
    for i in range(visibles):
        x = rng.randint(40, ancho - assets.ANCHO_NOTIFICACION - 40)
        velocidad = rng.uniform(28, 55)
        desfase = rng.uniform(0, alto)
        y = (alto + desfase - tiempo * velocidad) % (alto + 120) - 60
        # Solo dentro de la imagen: ni sobre las franjas ni sobre el subtítulo.
        if y < assets.ALTO_LETTERBOX + 6 or y + assets.ALTO_NOTIFICACION > assets.RECT_SUBTITULO_CINEMATICA[1] - 6:
            continue
        es_falsa = falsas and (i % 3 != 1 or i >= 6)
        usuario, texto = rng.choice(POSTS_FALSOS if es_falsa else POSTS_CIVITAS)
        _tarjeta_notificacion(pantalla, (x, round(y)), usuario, texto, es_falsa, tiempo + i)


def _tarjeta_notificacion(pantalla, posicion, usuario, texto, falsa, fase):
    rect = pygame.Rect(posicion, (assets.ANCHO_NOTIFICACION, assets.ALTO_NOTIFICACION))
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    relleno = assets.COLOR_FONDO_NOTIFICACION_FALSA if falsa else assets.COLOR_FONDO_NOTIFICACION
    pygame.draw.rect(capa, (*relleno, 225), capa.get_rect(), border_radius=8)
    if falsa:
        pygame.draw.rect(capa, (*assets.COLOR_BORDE_NOTIFICACION_FALSA, 255), capa.get_rect(), 2, border_radius=8)
    avatar = sprites.sprite(sprites.AVATAR, sprites.PALETA_AVATAR, escala=2)
    capa.blit(avatar, (10, 10))
    dibujo.texto(capa, usuario, (46, 8), assets.COLOR_TEXTO_NOTIFICACION, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    layout.texto_en_ancho(capa, texto, (46, 28), rect.width - 56, assets.COLOR_TEXTO_NOTIFICACION,
                          assets.TAMANIO_FUENTE_PEQUENA, minimo=11)
    if falsa:
        # Contador de compartidos que crece: el rumor se multiplica.
        compartidos = int(120 + fase * 380)
        dibujo.texto(capa, f"↗ {compartidos}", (rect.width - 10, 8), assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="topright")
    pantalla.blit(capa, rect.topleft)


def _retrato(pantalla, toma, tiempo):
    """El protagonista: retrato grande del rol con un marco de luz."""
    imagen = sprites.retrato_rol(toma.retrato, assets.ALTO_RETRATO_CINEMATICA) if toma.retrato else None
    if imagen is None and toma.retrato:
        color = assets.COLOR_POR_ROL.get(toma.retrato, assets.COLOR_TEXTO_HUD)
        imagen = sprites.sprite_jugador(color, escala=10, rol=toma.retrato)
    if imagen is None:
        return
    cx, cy = assets.POSICION_RETRATO_CINEMATICA
    cy += round(4 * math.sin(tiempo * 1.6))  # respiración leve
    entrada = layout.fraccion_entrada(tiempo, 0.5)
    rect = imagen.get_rect(center=(cx - round((1 - entrada) * 60), cy))
    halo = pygame.Surface((rect.width + 80, rect.height + 80), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*assets.COLOR_MORADO, 60), halo.get_rect())
    pantalla.blit(halo, halo.get_rect(center=rect.center))
    imagen = imagen.copy()
    imagen.set_alpha(round(255 * entrada))
    pantalla.blit(imagen, rect)


def _titulo(pantalla, toma, tiempo):
    ancho, alto = pantalla.get_size()
    entrada = layout.fraccion_entrada(tiempo, 1.2)
    tam = assets.TAMANIO_FUENTE_TITULO_CINEMATICA
    f = fuente(tam, True)
    superficie = f.render(toma.titulo, True, assets.COLOR_TITULO_CINEMATICA)
    # Resplandor: la misma palabra, más grande y translúcida, varias veces.
    for radio in (18, 10, 4):
        brillo = pygame.transform.smoothscale(
            superficie, (superficie.get_width() + radio * 2, superficie.get_height() + radio * 2))
        brillo.set_alpha(assets.COLOR_RESPLANDOR_TITULO_CINE[3])
        pantalla.blit(brillo, brillo.get_rect(center=(ancho // 2, alto // 2 - 30)))
    superficie.set_alpha(round(255 * entrada))
    pantalla.blit(superficie, superficie.get_rect(center=(ancho // 2, alto // 2 - 30)))
    if tiempo > 0.9 and toma.subtitulo:
        alfa = layout.alfa_entrada(tiempo - 0.9)
        sub = fuente(assets.TAMANIO_FUENTE_MEDIA).render(toma.subtitulo, True, assets.COLOR_TEXTO_HUD)
        sub.set_alpha(alfa)
        pantalla.blit(sub, sub.get_rect(center=(ancho // 2, alto // 2 + 34)))
    # Líneas decorativas que se abren hacia los lados.
    apertura = round(260 * entrada)
    y = alto // 2 + 70
    pygame.draw.line(pantalla, assets.COLOR_LINEA_TARJETA, (ancho // 2 - apertura, y), (ancho // 2 + apertura, y), 2)


def _tarjeta(pantalla, toma, tiempo):
    """Presentación de capítulo: rótulo pequeño, título grande y dos líneas."""
    ancho, alto = pantalla.get_size()
    entrada = layout.fraccion_entrada(tiempo, 0.7)
    layout.velo(pantalla, (0, 0, 0, round(120 * entrada)))
    cx, cy = ancho // 2, alto // 2
    apertura = round((ancho // 2 - 120) * entrada)
    for y in (cy - 64, cy + 56):
        pygame.draw.line(pantalla, assets.COLOR_LINEA_TARJETA, (cx - apertura, y), (cx + apertura, y), 2)
    if toma.superior:
        sup = fuente(assets.TAMANIO_FUENTE_TARJETA_SUPERIOR, True).render(toma.superior, True, assets.COLOR_AMARILLO)
        sup.set_alpha(round(255 * entrada))
        pantalla.blit(sup, sup.get_rect(center=(cx, cy - 36)))
    tam = assets.TAMANIO_FUENTE_TARJETA
    f = fuente(tam, True)
    while f.size(toma.titulo)[0] > ancho - 160 and tam > assets.TAMANIO_FUENTE_GRANDE:
        tam -= 2
        f = fuente(tam, True)
    titulo = f.render(toma.titulo, True, assets.COLOR_TARJETA_CAPITULO)
    titulo.set_alpha(round(255 * entrada))
    desplazamiento = round((1 - entrada) * 40)
    pantalla.blit(titulo, titulo.get_rect(center=(cx + desplazamiento, cy + 4)))
    if toma.subtitulo and tiempo > 0.5:
        sub = fuente(assets.TAMANIO_FUENTE_NORMAL).render(toma.subtitulo, True, assets.COLOR_TEXTO_SECUNDARIO)
        sub.set_alpha(layout.alfa_entrada(tiempo - 0.5))
        pantalla.blit(sub, sub.get_rect(center=(cx, cy + 78)))


def _objetivos(pantalla, toma, tiempo):
    layout.velo(pantalla, (0, 0, 0, 150))
    rect = layout.entrada(assets.RECT_PANEL_OBJETIVOS, tiempo)
    dibujo.panel_alfa(pantalla, rect, (14, 12, 34, 232), radio=12)
    dibujo.panel(pantalla, rect, None, assets.COLOR_MENU_SELECCION, 2, radio=12)
    x, y = rect.left + 36, rect.top + 26
    dibujo.texto(pantalla, toma.titulo or "TU MISIÓN", (rect.centerx, y), assets.COLOR_TITULO_CINEMATICA,
                 assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="midtop")
    y += 54
    pygame.draw.line(pantalla, assets.COLOR_LINEA_TARJETA, (x, y), (rect.right - 36, y), 1)
    y += 18
    for i, objetivo in enumerate(toma.objetivos):
        # Cada objetivo aparece medio segundo después del anterior.
        if tiempo < 0.25 + i * 0.35:
            break
        alfa = layout.alfa_entrada(tiempo - (0.25 + i * 0.35))
        casilla = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.rect(casilla, (*assets.COLOR_TEAL, alfa), casilla.get_rect(), 2, border_radius=4)
        pantalla.blit(casilla, (x, y + 2))
        fila = pygame.Rect(x + 30, y, rect.width - 72 - 30, 46)
        layout.parrafo_en_caja(pantalla, objetivo, fila, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL,
                               interlineado=2)
        y += 50
    boton = pygame.Rect(assets.RECT_BOTON_COMENZAR)
    pulso = 0.5 + 0.5 * math.sin(tiempo * 4)
    dibujo.panel(pantalla, boton.inflate(round(8 * pulso), round(8 * pulso)), None, assets.COLOR_BOTON_COMENZAR, 1, radio=8)
    dibujo.panel(pantalla, boton, assets.COLOR_BOTON_COMENZAR, None, 0, radio=8)
    dibujo.texto(pantalla, TEXTO_COMENZAR, boton.center, assets.COLOR_TEXTO_BOTON_COMENZAR,
                 assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
    chip = dibujo.chip(pantalla, TEXTO_ENTER_COMENZAR, (boton.centerx - 6, boton.bottom + 24), ancla="midright")
    dibujo.texto(pantalla, "para empezar", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")


# ----------------------------------------------------------------------
# Subtítulos y controles
# ----------------------------------------------------------------------


def caracteres_visibles(texto, tiempo, velocidad=assets.VELOCIDAD_MAQUINA_ESCRIBIR):
    """Cuántos caracteres del subtítulo se ven ya (máquina de escribir). Puro."""
    return min(len(texto), int(max(0.0, tiempo - 0.15) * velocidad))


def _subtitulo(pantalla, toma, tiempo):
    rect = pygame.Rect(assets.RECT_SUBTITULO_CINEMATICA)
    es_nova = toma.hablante == cine.HABLANTE_NOVA
    dibujo.panel_alfa(pantalla, rect, assets.COLOR_FONDO_SUBTITULO, radio=8)
    if es_nova:
        dibujo.panel(pantalla, rect, None, assets.COLOR_SUBTITULO_NOVA, 1, radio=8)
    x, y = rect.left + 20, rect.top + 10
    if toma.hablante and toma.hablante != cine.HABLANTE_NARRADOR:
        color_nombre = assets.COLOR_SUBTITULO_NOVA if es_nova else assets.COLOR_SUBTITULO_HABLANTE
        etiqueta = dibujo.texto(pantalla, toma.hablante, (x, y), color_nombre, assets.TAMANIO_FUENTE_PEQUENA,
                                negrita=True)
        y = etiqueta.bottom + 2
    visible = toma.texto[: caracteres_visibles(toma.texto, tiempo)]
    if es_nova and visible:
        # NOVA_404 "corrompe" algún carácter al escribir.
        _rng_glitch.seed(int(tiempo * 9))
        letras = list(visible)
        for _ in range(2):
            i = _rng_glitch.randrange(len(letras))
            if letras[i] not in " ." and _rng_glitch.random() < 0.35:
                letras[i] = _rng_glitch.choice("#%&/0_")
        visible = "".join(letras)
    caja = pygame.Rect(x, y, rect.width - 40, rect.bottom - 8 - y)
    layout.parrafo_en_caja(pantalla, visible or " ", caja,
                           assets.COLOR_SUBTITULO_NOVA if es_nova else assets.COLOR_SUBTITULO,
                           assets.TAMANIO_FUENTE_SUBTITULO, interlineado=4)


def _controles(pantalla, cinematica, toma):
    ancho, alto = pantalla.get_size()
    y = alto - assets.ALTO_LETTERBOX // 2
    actual, total = cinematica.progreso
    dibujo.texto(pantalla, f"{actual}/{total}", (assets.MARGEN_PANTALLA, y), assets.COLOR_TEXTO_APAGADO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft")
    if cinematica.titulo:
        layout.texto_en_ancho(pantalla, cinematica.titulo, (ancho // 2, y), 600, assets.COLOR_TEXTO_APAGADO,
                              assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
    x = ancho - assets.MARGEN_PANTALLA
    if not toma.espera:
        chip = dibujo.chip(pantalla, TEXTO_CONTINUAR, (x, y), assets.COLOR_TEXTO_HUD, assets.COLOR_FONDO_CHIP,
                           assets.COLOR_BORDE_CHIP, ancla="midright")
        x = chip.left - 10
    if cinematica.saltable:
        dibujo.chip(pantalla, TEXTO_SALTAR, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.COLOR_FONDO_CHIP,
                    assets.COLOR_BORDE_CHIP, ancla="midright")
