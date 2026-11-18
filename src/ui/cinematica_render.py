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
    titulares       publicaciones de Civitas contra el protagonista
    pelicula        video continuo (el prólogo) con rótulos cronometrados:
                    subtítulos, la alerta «COLAPSO TOTAL», lemas y el título

Una toma con `video` muestra sus cuadros (src/ui/video_cuadros.py). Si falta
el video se usa la ilustración, y si falta la ilustración se dibuja un fondo
de ciudad en código: la cinemática nunca depende de un archivo. Entre tomas
hay un fundido cruzado. No modifica la cinemática.
"""

import math
import random

import pygame

from src.core import assets
from src.story import cinematica as cine
from src.ui import dibujo, kit, layout, sprites, video_cuadros
from src.ui.fuentes import fuente

TEXTO_CONTINUAR = "Enter: continuar"
TEXTO_REVELAR = "Enter: mostrar todo"
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
    ("@NovaDespierta", "La enfermera miente. No hay falta de sangre."),
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
    pantalla.fill(assets.COLOR_LETTERBOX)
    _dibujar_fondo(pantalla, toma, tiempo, reducir_movimiento)

    if toma.efecto == cine.EFECTO_GLITCH:
        _glitch(pantalla, tiempo, reducir_movimiento)
    elif toma.efecto == cine.EFECTO_NOTIFICACIONES:
        _notificaciones(pantalla, tiempo, assets.CANTIDAD_NOTIFICACIONES_CIVITAS, falsas=False)
    elif toma.efecto == cine.EFECTO_CAOS:
        _notificaciones(pantalla, tiempo, assets.CANTIDAD_NOTIFICACIONES_CAOS, falsas=True)
    elif toma.efecto == cine.EFECTO_RETRATO:
        _retrato(pantalla, toma, tiempo)
    elif toma.efecto == cine.EFECTO_TITULARES:
        _titulares(pantalla, toma, tiempo)

    _letterbox(pantalla)
    if toma.rotulos:
        _rotulos_pelicula(pantalla, toma, tiempo, reducir_movimiento)
    if toma.efecto == cine.EFECTO_TITULO:
        _titulo(pantalla, toma, tiempo)
    elif toma.efecto == cine.EFECTO_TARJETA:
        _tarjeta(pantalla, toma, tiempo)
    elif toma.efecto == cine.EFECTO_OBJETIVOS:
        _objetivos(pantalla, toma, tiempo)
    if toma.texto and toma.efecto not in (cine.EFECTO_TITULO, cine.EFECTO_TARJETA, cine.EFECTO_OBJETIVOS):
        _subtitulo(pantalla, cinematica, toma, tiempo)
    _fundidos(pantalla, cinematica, toma, tiempo, reducir_movimiento)
    _controles(pantalla, cinematica, toma, tiempo)


# ----------------------------------------------------------------------
# Fondo
# ----------------------------------------------------------------------


def _dibujar_fondo(pantalla, toma, tiempo, reducir_movimiento):
    ancho, alto = pantalla.get_size()
    cuadro = video_cuadros.cuadro(toma.video, tiempo, (ancho, alto)) if toma.video else None
    if cuadro is not None:
        pantalla.blit(cuadro, (0, 0))
        return
    imagen = sprites.fondo_historia(toma.fondo, (ancho, alto)) if toma.fondo else None
    if imagen is None:
        imagen = _fondo_en_codigo((ancho, alto))
    if reducir_movimiento or toma.espera:
        pantalla.blit(imagen, (0, 0))
        return
    # Paneo lento y continuo: la imagen sigue viva mientras el jugador lee,
    # sin importar cuánto tarde. Se usa una versión algo mayor, ya escalada:
    # mover un blit no cuesta nada por frame.
    grande = _imagen_paneo(toma.fondo, imagen, (ancho, alto))
    semilla = sum(ord(c) for c in toma.id)
    margen_x, margen_y = grande.get_width() - ancho, grande.get_height() - alto
    fase = tiempo / assets.PERIODO_PANEO * 2 * math.pi + semilla
    dx = round(margen_x * (0.5 + 0.5 * math.sin(fase)))
    dy = round(margen_y * (0.5 + 0.5 * math.sin(fase * 0.7 + 1.3)))
    pantalla.blit(grande, (-dx, -dy))


_cache_paneo = {}


def _imagen_paneo(clave, imagen, tamanio):
    if (clave, tamanio) not in _cache_paneo:
        w, h = round(tamanio[0] * assets.ZOOM_KEN_BURNS), round(tamanio[1] * assets.ZOOM_KEN_BURNS)
        _cache_paneo[(clave, tamanio)] = pygame.transform.smoothscale(imagen, (w, h))
    return _cache_paneo[(clave, tamanio)]


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


_ultimo_frame = {"superficie": None, "toma": None}


def _fundidos(pantalla, cinematica, toma, tiempo, reducir_movimiento):
    """Fundido cruzado desde la toma anterior; la primera entra desde negro.
    Guarda una copia de cada frame terminado solo cuando la toma cambia."""
    d = assets.DURACION_FUNDIDO_TOMA
    clave = (id(cinematica), cinematica.indice)
    anterior = _ultimo_frame["superficie"]
    if _ultimo_frame["toma"] != clave:
        if _ultimo_frame["toma"] is None or _ultimo_frame["toma"][0] != id(cinematica):
            anterior = None
            _ultimo_frame["superficie"] = None
        _ultimo_frame["toma"] = clave
    if tiempo < d and not reducir_movimiento:
        alfa = round(255 * (1 - tiempo / d))
        if anterior is not None:
            anterior.set_alpha(alfa)
            pantalla.blit(anterior, (0, 0))
        else:
            kit.velo(pantalla, alfa, assets.COLOR_LETTERBOX)
    elif not toma.espera:
        duracion = cinematica.duracion_efectiva(toma)
        if duracion is not None and duracion - tiempo < d:
            kit.velo(pantalla, round(255 * (1 - max(0.0, duracion - tiempo) / d)), assets.COLOR_LETTERBOX)
    # Se guarda el frame ya estable para el próximo cambio de toma.
    if tiempo >= d or reducir_movimiento:
        if _ultimo_frame["superficie"] is None or _ultimo_frame["superficie"].get_size() != pantalla.get_size():
            _ultimo_frame["superficie"] = pygame.Surface(pantalla.get_size())
        _ultimo_frame["superficie"].set_alpha(None)
        _ultimo_frame["superficie"].blit(pantalla, (0, 0))


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


def _titulares(pantalla, toma, tiempo):
    """Publicaciones de Civitas contra el protagonista: entran una a una."""
    kit.velo(pantalla, 110, assets.COLOR_NOCHE)
    for i, titular in enumerate(toma.lineas):
        entrada = layout.fraccion_entrada(tiempo - 0.5 - i * 1.3, 0.6)
        if entrada <= 0:
            continue
        rect = pygame.Rect(0, 0, 780, 74)
        rect.center = (pantalla.get_width() // 2 + round((1 - entrada) * 60) + (-90, 70, -30)[i % 3], 170 + i * 92)
        kit.panel(pantalla, rect, assets.COLOR_GRAVE, alfa=238)
        kit.rotulo(pantalla, "Civitas · Tendencia", (rect.left + 18, rect.top + 10), assets.COLOR_GRAVE)
        layout.texto_en_ancho(pantalla, titular, (rect.left + 18, rect.top + 32), rect.width - 36, assets.COLOR_TEXTO_HUD,
                              assets.TAMANIO_FUENTE_MEDIA, negrita=True)


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
    """Presentación de capítulo: número, nombre, ubicación, contexto y objetivo.
    Pocas palabras, con jerarquía clara y entrada escalonada."""
    ancho, alto = pantalla.get_size()
    entrada = layout.fraccion_entrada(tiempo, 0.7)
    kit.velo(pantalla, round(150 * entrada), assets.COLOR_NOCHE)
    cx, cy = ancho // 2, alto // 2 - (46 if toma.lineas else 0)
    apertura = round((ancho // 2 - 160) * entrada)
    for y in (cy - 74, cy + 54):
        pygame.draw.line(pantalla, assets.COLOR_LINEA_TARJETA, (cx - apertura, y), (cx + apertura, y), 2)
    if toma.superior:
        sup = fuente(assets.TAMANIO_FUENTE_TARJETA_SUPERIOR, True).render(toma.superior, True, assets.COLOR_ALERTA)
        sup.set_alpha(round(255 * entrada))
        pantalla.blit(sup, sup.get_rect(center=(cx, cy - 46)))
    tam = assets.TAMANIO_FUENTE_TARJETA
    f = fuente(tam, True)
    while f.size(toma.titulo)[0] > ancho - 160 and tam > assets.TAMANIO_FUENTE_GRANDE:
        tam -= 2
        f = fuente(tam, True)
    titulo = f.render(toma.titulo, True, assets.COLOR_TARJETA_CAPITULO)
    titulo.set_alpha(round(255 * entrada))
    pantalla.blit(titulo, titulo.get_rect(center=(cx + round((1 - entrada) * 40), cy + 4)))
    y = cy + 76
    if toma.subtitulo and tiempo > 0.5:
        sub = fuente(assets.TAMANIO_FUENTE_NORMAL, True).render(toma.subtitulo, True, assets.COLOR_TEXTO_SECUNDARIO)
        sub.set_alpha(layout.alfa_entrada(tiempo - 0.5))
        pantalla.blit(sub, sub.get_rect(center=(cx, y)))
    y += 34
    for i, linea in enumerate(l for l in toma.lineas if l):
        if tiempo <= 0.9 + i * 0.4:
            break
        rotulo = "Lo que pasa" if i == 0 else "Tu objetivo"
        color = assets.COLOR_TEXTO_HUD if i == 0 else assets.COLOR_VERIFICADO
        alfa = layout.alfa_entrada(tiempo - (0.9 + i * 0.4))
        capa = pygame.Surface((860, 58), pygame.SRCALPHA)
        kit.rotulo(capa, rotulo, (430, 0), assets.COLOR_TEXTO_APAGADO, ancla="midtop")
        layout.parrafo_en_caja(capa, linea, pygame.Rect(0, 20, 860, 36), color, assets.TAMANIO_FUENTE_MEDIA, centrado=True)
        capa.set_alpha(alfa)
        pantalla.blit(capa, capa.get_rect(midtop=(cx, y)))
        y += 62


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
# Película: rótulos cronometrados
# ----------------------------------------------------------------------


def _rotulos_pelicula(pantalla, toma, tiempo, reducir_movimiento=False):
    visibles = toma.rotulos_en(tiempo)
    lemas = [r for r in visibles if r.estilo == cine.ROTULO_LEMA]
    if lemas:
        # Un solo velo detrás de los lemas, para que se lean sobre cualquier imagen.
        kit.velo(pantalla, round(assets.ALFA_VELO_LEMA * max(r.fraccion(tiempo, 0.5) for r in lemas)), assets.COLOR_NOCHE)
        _letterbox(pantalla)
    for rotulo in visibles:
        alfa = round(255 * rotulo.fraccion(tiempo))
        if rotulo.estilo == cine.ROTULO_ALERTA:
            _rotulo_alerta(pantalla, rotulo, tiempo, alfa, reducir_movimiento)
        elif rotulo.estilo == cine.ROTULO_LEMA:
            _rotulo_lema(pantalla, rotulo, alfa)
        elif rotulo.estilo == cine.ROTULO_TITULO:
            kit.velo(pantalla, round(150 * rotulo.fraccion(tiempo, 0.8)), assets.COLOR_NOCHE)
            _letterbox(pantalla)
            partes = rotulo.partes
            _titulo(pantalla, cine.Toma("titulo", titulo=partes[0]), tiempo - rotulo.inicio)
            if len(partes) > 1 and tiempo - rotulo.inicio > 0.7:
                # La pregunta final, grande y legible bajo el título.
                ancho, alto = pantalla.get_size()
                f = _texto_que_cabe(partes[1], assets.TAMANIO_FUENTE_ROTULO_PELICULA + 4, ancho - 120, negrita=True)
                _con_sombra(pantalla, f, partes[1], assets.COLOR_TEXTO_HUD, (ancho // 2, alto // 2 + 50),
                            layout.alfa_entrada(tiempo - rotulo.inicio - 0.7))
        elif rotulo.estilo == cine.ROTULO_MISION:
            _rotulo_mision(pantalla, rotulo, alfa)
        elif rotulo.estilo == cine.ROTULO_DESCARTADA:
            _rotulo_descartada(pantalla, rotulo, tiempo, alfa)
        elif rotulo.estilo == cine.ROTULO_DIA:
            _rotulo_dia(pantalla, rotulo, alfa)
        elif rotulo.estilo == cine.ROTULO_POST:
            _rotulo_post(pantalla, rotulo, tiempo, alfa)
        elif rotulo.estilo == cine.ROTULO_COLAPSO:
            _rotulo_colapso(pantalla, rotulo, tiempo, alfa)
        elif rotulo.estilo == cine.ROTULO_LUGAR:
            _rotulo_lugar(pantalla, rotulo, tiempo, alfa)
        else:
            _rotulo_subtitulo(pantalla, rotulo, alfa)


def _texto_que_cabe(texto, tamanio, ancho_max, negrita=False):
    """La superficie del texto, achicando la fuente hasta que quepa (nunca se corta)."""
    f = fuente(tamanio, negrita)
    while f.size(texto)[0] > ancho_max and tamanio > assets.TAMANIO_FUENTE_PEQUENA:
        tamanio -= 2
        f = fuente(tamanio, negrita)
    return f


def _con_sombra(pantalla, f, texto, color, centro, alfa):
    sombra = f.render(texto, True, assets.COLOR_SOMBRA_PELICULA)
    cara = f.render(texto, True, color)
    sombra.set_alpha(alfa)
    cara.set_alpha(alfa)
    rect = cara.get_rect(center=centro)
    pantalla.blit(sombra, rect.move(2, 2))
    pantalla.blit(cara, rect)
    return rect


def _rotulo_subtitulo(pantalla, rotulo, alfa):
    """Lo que alguien dice: el nombre en su color y la frase debajo, abajo y
    centrado, sobre una franja casi opaca (se lee sobre cualquier toma)."""
    ancho = pantalla.get_width()
    f = _texto_que_cabe(rotulo.texto, assets.TAMANIO_FUENTE_SUBTITULO_PELICULA, ancho - 160)
    alto_texto = f.get_height()
    nombre = rotulo.hablante if rotulo.hablante and rotulo.hablante != cine.HABLANTE_NARRADOR else None
    f_nombre = fuente(assets.TAMANIO_FUENTE_HABLANTE_PELICULA, True)
    alto = alto_texto + (f_nombre.get_height() + 2 if nombre else 0)
    base = assets.Y_SUBTITULO_PELICULA
    fondo = pygame.Rect(0, 0, min(ancho - 80, f.size(rotulo.texto)[0] + 56), alto + 18)
    fondo.midbottom = (ancho // 2, base + 8)
    capa = pygame.Surface(fondo.size, pygame.SRCALPHA)
    capa.fill((*assets.COLOR_FONDO_SUBTITULO_PELICULA[:3], round(assets.COLOR_FONDO_SUBTITULO_PELICULA[3] * alfa / 255)))
    pantalla.blit(capa, fondo)
    y = fondo.top + 9
    if nombre:
        color = assets.COLOR_POR_HABLANTE_PELICULA.get(nombre, assets.COLOR_HABLANTE_PELICULA)
        etiqueta = f_nombre.render(nombre, True, color)
        etiqueta.set_alpha(alfa)
        pantalla.blit(etiqueta, etiqueta.get_rect(midtop=(ancho // 2, y)))
        y += f_nombre.get_height() + 2
    color = assets.COLOR_NARRADOR_PELICULA
    _con_sombra(pantalla, f, rotulo.texto, color, (ancho // 2, y + alto_texto // 2), alfa)


def _rotulo_alerta(pantalla, rotulo, tiempo, alfa, reducir_movimiento):
    """«CIUDAD UMBRAL — COLAPSO TOTAL»: banda oscura y letras rojas que tiemblan."""
    ancho, alto = pantalla.get_size()
    banda = pygame.Rect(0, 0, ancho, 96)
    banda.center = (ancho // 2, alto // 2 - 120)
    capa = pygame.Surface(banda.size, pygame.SRCALPHA)
    capa.fill((0, 0, 0, round(170 * alfa / 255)))
    pantalla.blit(capa, banda)
    for y in (banda.top, banda.bottom - 2):
        linea = pygame.Surface((ancho, 2), pygame.SRCALPHA)
        linea.fill((*assets.COLOR_ALERTA_PELICULA, alfa))
        pantalla.blit(linea, (0, y))
    f = _texto_que_cabe(rotulo.texto, assets.TAMANIO_FUENTE_ALERTA_PELICULA, ancho - 120, negrita=True)
    dx = 0
    if not reducir_movimiento:
        _rng_glitch.seed(int(tiempo * 14))
        if _rng_glitch.random() < 0.3:
            dx = _rng_glitch.randint(-6, 6)
            fantasma = f.render(rotulo.texto, True, assets.COLOR_MAGENTA)
            fantasma.set_alpha(alfa // 2)
            pantalla.blit(fantasma, fantasma.get_rect(center=(banda.centerx - dx * 2, banda.centery)))
    _con_sombra(pantalla, f, rotulo.texto, assets.COLOR_ALERTA_PELICULA, (banda.centerx + dx, banda.centery), alfa)


def _caja_alfa(pantalla, rect, rgba, alfa, borde=None):
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    capa.fill((*rgba[:3], round(rgba[3] * alfa / 255)))
    if borde is not None:
        pygame.draw.rect(capa, (*borde, alfa), capa.get_rect(), 2)
    pantalla.blit(capa, rect)


def _rotulo_mision(pantalla, rotulo, alfa):
    """Tarjeta de misión como la del juego: título en ámbar y detalles debajo."""
    x, y, ancho, _ = assets.RECT_MISION_PELICULA
    if rotulo.x is not None:
        x = round(rotulo.x * pantalla.get_width())
    if rotulo.y is not None:
        y = round(rotulo.y * pantalla.get_height())
    partes = rotulo.partes
    f_rotulo = fuente(assets.TAMANIO_FUENTE_NORMAL, True)
    f_titulo = _texto_que_cabe(partes[0], assets.TAMANIO_FUENTE_ROTULO_PELICULA, ancho - 32, negrita=True)
    f_linea = fuente(assets.TAMANIO_FUENTE_MEDIA)
    alto = 18 + f_rotulo.get_height() + 6 + f_titulo.get_height() + 8 + len(partes[1:]) * (f_linea.get_height() + 4) + 12
    rect = pygame.Rect(x, y, ancho, alto)
    _caja_alfa(pantalla, rect, (10, 8, 22, 225), alfa, assets.COLOR_MISION_PELICULA)
    cy = rect.top + 14
    for superficie in (f_rotulo.render("MISIÓN", True, assets.COLOR_MISION_PELICULA),
                       f_titulo.render(partes[0], True, assets.COLOR_TEXTO_HUD)):
        superficie.set_alpha(alfa)
        pantalla.blit(superficie, (rect.left + 16, cy))
        cy += superficie.get_height() + 6
    cy += 2
    for linea in partes[1:]:
        superficie = _texto_que_cabe(linea, assets.TAMANIO_FUENTE_MEDIA, ancho - 32).render(
            linea, True, assets.COLOR_TEXTO_SECUNDARIO)
        superficie.set_alpha(alfa)
        pantalla.blit(superficie, (rect.left + 16, cy))
        cy += f_linea.get_height() + 4


def _rotulo_descartada(pantalla, rotulo, tiempo, alfa):
    """Sello rojo que cae sobre la misión: «MISIÓN DESCARTADA»."""
    x, y, ancho, _ = assets.RECT_MISION_PELICULA
    if rotulo.x is not None:
        x = round(rotulo.x * pantalla.get_width())
    if rotulo.y is not None:
        y = round(rotulo.y * pantalla.get_height())
    escala = 1.0 + 0.6 * max(0.0, 1.0 - (tiempo - rotulo.inicio) / 0.18)  # golpe del sello
    f = fuente(round(assets.TAMANIO_FUENTE_ALERTA_PELICULA * 0.7 * escala), True)
    texto = f.render(rotulo.texto, True, assets.COLOR_DESCARTADA_PELICULA)
    marco = texto.get_rect().inflate(28, 16)
    sello = pygame.Surface(marco.size, pygame.SRCALPHA)
    sello.fill((20, 0, 4, 170))
    pygame.draw.rect(sello, assets.COLOR_DESCARTADA_PELICULA, sello.get_rect(), 4)
    sello.blit(texto, texto.get_rect(center=sello.get_rect().center))
    sello = pygame.transform.rotate(sello, -8)
    sello.set_alpha(alfa)
    pantalla.blit(sello, sello.get_rect(center=(x + ancho // 2, y + 70)))


def _rotulo_dia(pantalla, rotulo, alfa):
    """Paso del tiempo, arriba a la izquierda: «DÍA 4 · 3 misiones sin completar»."""
    f = fuente(assets.TAMANIO_FUENTE_ROTULO_PELICULA, True)
    texto = f.render(rotulo.texto, True, assets.COLOR_ALERTA)
    rect = texto.get_rect(topleft=(40, assets.ALTO_LETTERBOX + 22)).inflate(24, 12)
    _caja_alfa(pantalla, rect, (0, 0, 0, 200), alfa)
    pygame.draw.rect(pantalla, assets.COLOR_ALERTA, (rect.left, rect.top, 4, rect.height))
    texto.set_alpha(alfa)
    pantalla.blit(texto, texto.get_rect(center=rect.center).move(2, 0))


def _rotulo_post(pantalla, rotulo, tiempo, alfa):
    """Publicación falsa que aparece sobre la toma (cuenta|texto)."""
    ancho, alto = pantalla.get_size()
    partes = rotulo.partes
    entrada = layout.fraccion_entrada(tiempo - rotulo.inicio, 0.3)
    x = round((rotulo.x if rotulo.x is not None else 0.06) * ancho)
    y = round((rotulo.y if rotulo.y is not None else 0.3) * alto) + round((1 - entrada) * 24)
    capa = pygame.Surface((assets.ANCHO_NOTIFICACION + 120, assets.ALTO_NOTIFICACION + 10), pygame.SRCALPHA)
    rect = capa.get_rect()
    pygame.draw.rect(capa, (*assets.COLOR_FONDO_NOTIFICACION_FALSA, 240), rect, border_radius=8)
    pygame.draw.rect(capa, (*assets.COLOR_BORDE_NOTIFICACION_FALSA, 255), rect, 2, border_radius=8)
    dibujo.texto(capa, partes[0], (14, 8), assets.COLOR_TEXTO_NOTIFICACION, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    compartidos = int(240 + (tiempo - rotulo.inicio) * 1900)  # el contador se dispara
    dibujo.texto(capa, f"↗ {compartidos}", (rect.width - 12, 8), assets.COLOR_MAGENTA, assets.TAMANIO_FUENTE_NORMAL,
                 negrita=True, ancla="topright")
    layout.texto_en_ancho(capa, partes[-1], (14, 32), rect.width - 28, assets.COLOR_TEXTO_NOTIFICACION,
                          assets.TAMANIO_FUENTE_MEDIA, minimo=13)
    capa.set_alpha(alfa)
    pantalla.blit(capa, (x, y))


def _rotulo_colapso(pantalla, rotulo, tiempo, alfa):
    """Barra de colapso de la ciudad que sube con el paso de los días."""
    x, y, ancho, alto = assets.RECT_BARRA_COLAPSO_PELICULA
    valor = rotulo.valor_en(tiempo)
    f = fuente(assets.TAMANIO_FUENTE_MEDIA, True)
    marco = pygame.Rect(x - 14, y - 10, ancho + 28, alto + f.get_height() + 26)
    _caja_alfa(pantalla, marco, (0, 0, 0, 200), alfa)
    etiqueta = f.render(f"{rotulo.texto}  {valor:4.0f}%", True, assets.COLOR_BARRA_COLAPSO_PELICULA)
    etiqueta.set_alpha(alfa)
    pantalla.blit(etiqueta, (x, y))
    barra = pygame.Rect(x, y + f.get_height() + 6, ancho, alto)
    _caja_alfa(pantalla, barra, (60, 20, 26, 255), alfa)
    lleno = barra.copy()
    lleno.width = round(ancho * max(0.0, min(100.0, valor)) / 100)
    _caja_alfa(pantalla, lleno, (*assets.COLOR_BARRA_COLAPSO_PELICULA, 255), alfa)


def _rotulo_lugar(pantalla, rotulo, tiempo, alfa):
    """Lugar que el jugador podrá investigar: rombo que late y su nombre."""
    ancho, alto = pantalla.get_size()
    cx = round((rotulo.x if rotulo.x is not None else 0.5) * ancho)
    cy = round((rotulo.y if rotulo.y is not None else 0.2) * alto)
    latido = 1.0 + 0.12 * math.sin((tiempo - rotulo.inicio) * 6)
    r = round(14 * latido)
    rombo = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    c = r + 2
    pygame.draw.polygon(rombo, (*assets.COLOR_LUGAR_PELICULA, alfa), [(c, 2), (c * 2 - 2, c), (c, c * 2 - 2), (2, c)])
    pantalla.blit(rombo, rombo.get_rect(center=(cx, cy)))
    f = fuente(assets.TAMANIO_FUENTE_ALERTA_PELICULA - 12, True)
    _con_sombra(pantalla, f, rotulo.texto, assets.COLOR_LUGAR_PELICULA, (cx, cy + r + 26), alfa)


def _rotulo_lema(pantalla, rotulo, alfa):
    """Frase grande, espaciada, en el centro de la imagen."""
    ancho, alto = pantalla.get_size()
    # Letras separadas (rótulo de cine) solo si la frase es corta; si no, no cabría grande.
    texto = " ".join(rotulo.texto) if len(rotulo.texto) <= 22 else rotulo.texto
    f = _texto_que_cabe(texto, assets.TAMANIO_FUENTE_LEMA_PELICULA, ancho - 120, negrita=True)
    y = alto // 2 - 60 + rotulo.fila * (f.get_height() + 16)
    _con_sombra(pantalla, f, texto, assets.COLOR_LEMA_PELICULA, (ancho // 2, y), alfa)


# ----------------------------------------------------------------------
# Subtítulos y controles
# ----------------------------------------------------------------------


def _subtitulo(pantalla, cinematica, toma, tiempo):
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
    caja = pygame.Rect(x, y, rect.width - 40, rect.bottom - 8 - y)
    texto = toma.texto
    visibles = cinematica.caracteres_visibles
    if es_nova and not cinematica.texto_completo and visibles > 0:
        # NOVA_404 "corrompe" algún carácter mientras escribe; al terminar se lee limpio.
        _rng_glitch.seed(int(tiempo * 9))
        letras = list(texto)
        for _ in range(2):
            i = _rng_glitch.randrange(visibles)
            if letras[i] not in " ." and _rng_glitch.random() < 0.35:
                letras[i] = _rng_glitch.choice("#%&/0_")
        texto = "".join(letras)
    layout.parrafo_progresivo(pantalla, texto, visibles, caja,
                              assets.COLOR_SUBTITULO_NOVA if es_nova else assets.COLOR_SUBTITULO,
                              assets.TAMANIO_FUENTE_SUBTITULO, interlineado=4)


def _controles(pantalla, cinematica, toma, tiempo=0.0):
    ancho, alto = pantalla.get_size()
    y = alto - assets.ALTO_LETTERBOX // 2
    actual, total = cinematica.progreso
    dibujo.texto(pantalla, f"{actual}/{total}", (assets.MARGEN_PANTALLA, y), assets.COLOR_TEXTO_APAGADO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft")
    x = ancho - assets.MARGEN_PANTALLA
    if not toma.espera and not toma.pelicula:
        if not cinematica.texto_completo:
            etiqueta, color = TEXTO_REVELAR, assets.COLOR_TEXTO_SECUNDARIO
        else:
            etiqueta = TEXTO_CONTINUAR
            # Late cuando el texto ya espera al jugador: sabe que depende de él.
            latido = cinematica.esperando_enter and math.sin(tiempo * 4) > -0.3
            color = assets.COLOR_TEXTO_HUD if latido else assets.COLOR_TEXTO_SECUNDARIO
        chip = dibujo.chip(pantalla, etiqueta, (x, y), color, assets.COLOR_FONDO_CHIP, assets.COLOR_BORDE_CHIP, ancla="midright")
        x = chip.left - 10
    if cinematica.saltable:
        dibujo.chip(pantalla, TEXTO_SALTAR, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.COLOR_FONDO_CHIP,
                    assets.COLOR_BORDE_CHIP, ancla="midright")
