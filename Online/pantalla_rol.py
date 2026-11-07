"""Pantalla de revelación de rol del modo Online (estilo Among Us).

Sale en cada PC justo al iniciar la partida desde el lobby. A quien el host
sorteó le dice IMPOSTOR, sobre fondo negro con un óvalo rojo que pulsa; a los
demás, "Tu rol es" y el rol que eligieron, en cian sobre negro limpio. En el
centro flota el jugador con la ropa que se puso en los vestidores: es el mismo
sprite vestido de la sala y de la partida (sprites.sprite_jugador con su
Apariencia), no una imagen aparte.

Línea de tiempo: fundido desde negro, jugador fijo y fundido a negro. Espacio
o Enter la acortan pasados TIEMPO_MINIMO_OMITIR_REVELACION segundos. La red
sigue corriendo en sus hilos mientras tanto, así que nadie se desconecta por
esperar aquí. Constantes en assets.py.
"""

import math

import pygame

from src.core import assets
from src.core.config import FPS
from src.ui import dibujo, sprites
from src.ui.fuentes import fuente

TECLAS_OMITIR = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

_cache_resplandor = {}  # tamaño de la pantalla -> Surface con el óvalo rojo


def textos_revelacion(es_impostor, nombre_rol, descripcion_rol=None):
    """(encabezado, título, subtítulo). El impostor no lleva encabezado y
    `descripcion_rol` (p. ej. la habilidad del rol) reemplaza al subtítulo."""
    if es_impostor:
        return None, assets.TEXTO_TITULO_IMPOSTOR, descripcion_rol or assets.TEXTO_SUBTITULO_IMPOSTOR
    return assets.TEXTO_ENCABEZADO_TRIPULANTE, nombre_rol, descripcion_rol or assets.TEXTO_SUBTITULO_TRIPULANTE


def alfa_del_velo(tiempo, duracion, fundido=assets.DURACION_FUNDIDO_REVELACION):
    """Cuánto tapa el negro en el segundo `tiempo` (0 = nada, 255 = todo):
    baja en el fundido de entrada y sube en el de salida."""
    visible = min(tiempo / fundido, max(0.0, duracion - tiempo) / fundido, 1.0)
    return round(255 * (1 - visible))


def tiempo_al_omitir(tiempo, duracion):
    """A qué segundo salta la línea de tiempo con Espacio o Enter: al fundido
    de salida, nunca a un corte seco. Antes del mínimo no hace nada."""
    if tiempo < assets.TIEMPO_MINIMO_OMITIR_REVELACION:
        return tiempo
    return max(tiempo, duracion - assets.DURACION_FUNDIDO_REVELACION)


def _texto_pixelado(cadena, tamanio, ampliacion, color):
    """La fuente del juego sin suavizado y ampliada sin interpolar."""
    base = fuente(tamanio, True).render(cadena, False, color)
    return pygame.transform.scale(base, (base.get_width() * ampliacion, base.get_height() * ampliacion))


def _bloque_de_texto(cadena, medidas, color):
    """[(Surface, centro), ...] de `cadena` partida en las líneas que quepan
    en la zona segura. `medidas` = (tamaño, ampliación, y del centro)."""
    tamanio, ampliacion, y_centro = medidas
    ancho = assets.RECT_ZONA_SEGURA[2] // ampliacion
    lineas = [_texto_pixelado(linea, tamanio, ampliacion, color)
              for linea in dibujo.ajustar_texto(cadena, tamanio, ancho, negrita=True)]
    y = y_centro - sum(linea.get_height() for linea in lineas) // 2
    bloque = []
    for linea in lineas:
        bloque.append((linea, (assets.CENTRO_REVELACION[0], y + linea.get_height() // 2)))
        y += linea.get_height()
    return bloque


def _textos_de_pantalla(es_impostor, nombre_rol, descripcion_rol):
    """Todos los textos ya dibujados: se calculan una vez, no en cada frame."""
    encabezado, titulo, subtitulo = textos_revelacion(es_impostor, nombre_rol, descripcion_rol)
    color = assets.COLOR_IMPOSTOR if es_impostor else assets.COLOR_TRIPULANTE
    medidas_titulo = (assets.TEXTO_TITULO_IMPOSTOR_REVELACION if es_impostor
                      else assets.TEXTO_TITULO_TRIPULANTE_REVELACION)
    textos = _bloque_de_texto(titulo, medidas_titulo, color)
    textos += _bloque_de_texto(subtitulo, assets.TEXTO_SUBTITULO_REVELACION, color)
    if encabezado:
        textos += _bloque_de_texto(encabezado, assets.TEXTO_ENCABEZADO_REVELACION, color)
    return textos


def _resplandor(tamanio):
    """Óvalo rojo difuminado (se calcula una vez): elipses concéntricas cada
    vez más brillantes en baja resolución, ampliadas con suavizado."""
    if tamanio not in _cache_resplandor:
        base = pygame.Surface((tamanio[0] // 4, tamanio[1] // 4))
        ancho, alto = assets.TAMANIO_OVALO_RESPLANDOR
        for paso in range(assets.PASOS_OVALO_RESPLANDOR, 0, -1):
            fraccion = paso / assets.PASOS_OVALO_RESPLANDOR  # 1 = borde exterior
            brillo = (1 - fraccion) ** 2
            elipse = pygame.Rect(0, 0, round(ancho * fraccion) // 4, round(alto * fraccion) // 4)
            elipse.center = (assets.CENTRO_REVELACION[0] // 4, assets.CENTRO_REVELACION[1] // 4)
            pygame.draw.ellipse(base, [round(c * brillo) for c in assets.COLOR_RESPLANDOR_IMPOSTOR], elipse)
        _cache_resplandor[tamanio] = pygame.transform.smoothscale(base, tamanio)
    return _cache_resplandor[tamanio]


def _dibujar_fondo(pantalla, es_impostor, tiempo, reducir_movimiento):
    if not es_impostor:
        pantalla.fill(assets.COLOR_FONDO_TRIPULANTE)
        return
    pantalla.fill(assets.COLOR_FONDO_IMPOSTOR)
    pulso = 1.0 if reducir_movimiento else (1 + math.sin(tiempo * assets.FRECUENCIA_PULSO_RESPLANDOR)) / 2
    brillo = round(255 * (assets.BRILLO_MINIMO_RESPLANDOR + (1 - assets.BRILLO_MINIMO_RESPLANDOR) * pulso))
    capa = _resplandor(pantalla.get_size()).copy()
    capa.fill((brillo, brillo, brillo), special_flags=pygame.BLEND_RGB_MULT)
    pantalla.blit(capa, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def _dibujar_cuadro(pantalla, es_impostor, avatar, textos, velo, tiempo, duracion, reducir_movimiento):
    _dibujar_fondo(pantalla, es_impostor, tiempo, reducir_movimiento)
    flotacion = 0 if reducir_movimiento else round(
        math.sin(tiempo * assets.FRECUENCIA_FLOTACION_REVELACION) * assets.AMPLITUD_FLOTACION_REVELACION)
    cx, cy = assets.CENTRO_REVELACION
    pantalla.blit(avatar, avatar.get_rect(center=(cx, cy + flotacion)))
    for superficie, centro in textos:
        pantalla.blit(superficie, superficie.get_rect(center=centro))
    velo.set_alpha(alfa_del_velo(tiempo, duracion))
    pantalla.blit(velo, (0, 0))


def mostrar_pantalla_revelacion_rol(pantalla, reloj, es_impostor, nombre_rol, apariencia, descripcion_rol=None,
                                    duracion=assets.DURACION_REVELACION, presentar=None, reducir_movimiento=False):
    """Muestra la revelación de rol hasta que termina o se omite.

    `nombre_rol` es el rol con el que se jugará ("Ciudadano"...), también si
    es el impostor: de él sale el accesorio del avatar. `apariencia` es lo que
    el jugador se puso en los vestidores. `presentar` es el del juego (aplica
    el filtro de daltonismo antes del flip). Retorna False si se cierra la
    ventana y True en cualquier otro caso."""
    presentar = presentar or pygame.display.flip
    color = assets.COLOR_IMPOSTOR if es_impostor else assets.COLOR_TRIPULANTE
    avatar = sprites.sprite_jugador(color, escala=assets.ESCALA_AVATAR_REVELACION, rol=nombre_rol.lower(),
                                    apariencia=apariencia)
    textos = _textos_de_pantalla(es_impostor, nombre_rol, descripcion_rol)
    velo = pygame.Surface(pantalla.get_size())
    velo.fill(assets.COLOR_VELO_REVELACION)
    tiempo = 0.0
    while tiempo < duracion:
        tiempo += reloj.tick(FPS) / 1000
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return False
            if evento.type == pygame.KEYDOWN and evento.key in TECLAS_OMITIR:
                tiempo = tiempo_al_omitir(tiempo, duracion)
        _dibujar_cuadro(pantalla, es_impostor, avatar, textos, velo, tiempo, duracion, reducir_movimiento)
        presentar()
    return True
