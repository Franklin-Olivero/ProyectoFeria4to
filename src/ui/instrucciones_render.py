"""Dibujo de la pantalla de instrucciones de mazmorra (solo presentación).

Fondo neón del lobby, nombre de la mazmorra con su toxicidad y
dificultad, y una tarjeta por cada Tarjeta de src/ui/instrucciones.py:

    enemigo -> su sprite grande, pedido SOLO a sprites.sprite_enemigo
               (el mismo que se ve en combate: el PNG de su tipo o, si
               trae arte "enemigos 2.0", sus variantes, que se van
               turnando), una fila con todos sus aspectos, nombre, qué
               hace, cómo se comporta, amenaza 1-5 y un consejo.
    jefe    -> el Servidor Central (sprites.sprite_jefe).
    reglas  -> las dos reglas del cuarto o del jefe.

Los textos vienen de src/core/textos_enemigos.py.
"""

import math

import pygame

from src.core import assets, textos_enemigos
from src.entities.variantes_enemigo import variantes_de
from src.ui import dibujo, kit, sprites
from src.ui.fuentes import fuente
from src.ui.instrucciones import ENEMIGO, JEFE, REGLAS_CUARTO
from src.ui.seleccion_rol import dibujar_fondo_neon

TEXTO_COMENZAR = "Pulsa Enter para comenzar"
TEXTO_ESPERA = "Prepárate…"
TEXTO_PAGINAS = "← → más tarjetas"
TEXTO_PAUSA = "Esc: pausa"


def rects_tarjetas(cantidad):
    """Rects de `cantidad` tarjetas, centradas en la pantalla."""
    ancho, paso = assets.ANCHO_TARJETA_INSTRUCCIONES, assets.ANCHO_TARJETA_INSTRUCCIONES + assets.SEPARACION_TARJETAS_INSTRUCCIONES
    total = cantidad * ancho + (cantidad - 1) * assets.SEPARACION_TARJETAS_INSTRUCCIONES
    x0 = (1280 - total) // 2
    return [pygame.Rect(x0 + i * paso, assets.Y_TARJETAS_INSTRUCCIONES, ancho, assets.ALTO_TARJETA_INSTRUCCIONES)
            for i in range(cantidad)]


def imagen_tarjeta(tarjeta, tiempo):
    """La imagen grande de una tarjeta de enemigo o del jefe (sin escalar)."""
    if tarjeta.clase == JEFE:
        return sprites.sprite_jefe(tiempo)
    nombres = [v.nombre for v in variantes_de(tarjeta.tipo)]
    variante = None
    if nombres:
        variante = nombres[int(tiempo / assets.DURACION_VARIANTE_INSTRUCCIONES) % len(nombres)]
    return sprites.sprite_enemigo(tarjeta.tipo, tiempo=tiempo, variante=variante)


def recortar(imagen):
    """La imagen sin el margen transparente de su cuadro (las tiras de
    animación traen mucho aire alrededor del personaje)."""
    caja = imagen.get_bounding_rect()
    return imagen.subsurface(caja) if caja.width and caja.height else imagen


def escala_entera(imagen, alto_objetivo=assets.ALTO_SPRITE_INSTRUCCIONES):
    """Recorta el aire y escala por el mayor entero (vecino más cercano, sin
    suavizado) que no pase de `alto_objetivo` ni del ancho de la tarjeta;
    nunca la achica."""
    imagen = recortar(imagen)
    factor = max(1, round(alto_objetivo / max(1, imagen.get_height())))
    ancho_maximo = assets.ANCHO_TARJETA_INSTRUCCIONES - 40
    while factor > 1 and (imagen.get_height() * factor > alto_objetivo
                          or imagen.get_width() * factor > ancho_maximo):
        factor -= 1
    if factor == 1:
        return imagen
    return pygame.transform.scale(imagen, (imagen.get_width() * factor, imagen.get_height() * factor))


def dibujar_instrucciones(pantalla, instrucciones, tiempo, reducir_movimiento=False):
    t = 0.0 if reducir_movimiento else tiempo
    dibujar_fondo_neon(pantalla, t)
    kit.velo(pantalla, 90)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        dibujo.texto(pantalla, instrucciones.titulo, (640 + dx, 44 + dy), assets.COLOR_MORADO_OSCURO,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
    dibujo.texto(pantalla, instrucciones.titulo, (640, 44), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="center")
    detalle = f"Toxicidad {instrucciones.nivel_toxicidad:.0f}  ·  Dificultad {instrucciones.dificultad}  ·  Conoce a tus enemigos"
    dibujo.texto(pantalla, detalle, (640, 82), assets.COLOR_NEON_LOBBY_2, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    visibles = instrucciones.tarjetas_visibles()
    for tarjeta, rect in zip(visibles, rects_tarjetas(len(visibles))):
        if tarjeta.clase in (ENEMIGO, JEFE):
            _tarjeta_enemigo(pantalla, rect, tarjeta, tiempo)
        else:
            _tarjeta_reglas(pantalla, rect, tarjeta)

    y = assets.Y_TARJETAS_INSTRUCCIONES + assets.ALTO_TARJETA_INSTRUCCIONES + 34
    if instrucciones.puede_comenzar:
        pulso = 0.6 + 0.4 * math.sin(tiempo * 4)
        color = tuple(round(c * pulso + 40 * (1 - pulso)) for c in assets.COLOR_TEAL)
        dibujo.chip(pantalla, TEXTO_COMENZAR, (640, y), color, assets.COLOR_PANEL_HUD, color,
                    assets.TAMANIO_FUENTE_MEDIA, ancla="center", alto=40, margen=18)
    else:
        dibujo.texto(pantalla, TEXTO_ESPERA, (640, y), assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MEDIA,
                     ancla="center")
    pie = TEXTO_PAUSA
    if instrucciones.paginas > 1:
        pie = f"Página {instrucciones.pagina + 1}/{instrucciones.paginas}  ·  {TEXTO_PAGINAS}  ·  {TEXTO_PAUSA}"
    dibujo.texto(pantalla, pie, (640, y + 36), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                 ancla="center")


def _tarjeta_enemigo(pantalla, rect, tarjeta, tiempo):
    if tarjeta.clase == JEFE:
        ficha, color = textos_enemigos.FICHA_JEFE, assets.COLOR_JEFE_INSTRUCCIONES
    else:
        ficha = textos_enemigos.ficha(tarjeta.tipo)
        color = assets.COLOR_PRINCIPAL_ENEMIGO.get(tarjeta.tipo.value, assets.COLOR_MAGENTA)
    kit.panel(pantalla, rect, color, alfa=236, filo="arriba")
    x = rect.left + 16
    dibujo.texto(pantalla, ficha.nombre, (rect.centerx, rect.top + 22), color, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True, ancla="center")

    # Sprite grande sobre un halo del color del tipo.
    base_y = rect.top + 46 + assets.ALTO_SPRITE_INSTRUCCIONES
    halo = pygame.Surface((180, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*color, 60), halo.get_rect())
    pantalla.blit(halo, halo.get_rect(center=(rect.centerx, base_y - 6)))
    imagen = escala_entera(imagen_tarjeta(tarjeta, tiempo))
    pantalla.blit(imagen, imagen.get_rect(midbottom=(rect.centerx, base_y)))

    y = base_y + 6
    if tarjeta.clase == ENEMIGO:
        y = _iconos_variantes(pantalla, rect, tarjeta.tipo, y)
    y += 4
    y = dibujo.parrafo(pantalla, ficha.que_hace, (rect.centerx, y), rect.width - 28, assets.COLOR_TEXTO_HUD,
                       assets.TAMANIO_FUENTE_PEQUENA, negrita=True, interlineado=2, centrado=True) + 4
    y = dibujo.parrafo(pantalla, ficha.comportamiento, (x, y), rect.width - 32, assets.COLOR_TEXTO_SECUNDARIO,
                       assets.TAMANIO_FUENTE_PEQUENA, interlineado=2) + 6
    dibujo.texto(pantalla, "Amenaza", (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    for i in range(textos_enemigos.AMENAZA_MAXIMA):
        punto = pygame.Rect(x + 80 + i * 18, y + 3, 12, 12)
        pygame.draw.rect(pantalla, color if i < ficha.amenaza else assets.COLOR_SEGMENTO_VACIO, punto, border_radius=3)
    consejo = "Consejo: " + ficha.consejo
    lineas = len(dibujo.ajustar_texto(consejo, assets.TAMANIO_FUENTE_PEQUENA, rect.width - 32))
    alto_linea = fuente(assets.TAMANIO_FUENTE_PEQUENA).get_height() + 2
    dibujo.parrafo(pantalla, consejo, (x, rect.bottom - 14 - lineas * alto_linea), rect.width - 32, assets.COLOR_TEAL,
                   assets.TAMANIO_FUENTE_PEQUENA, interlineado=2)


def _iconos_variantes(pantalla, rect, tipo, y):
    """Todos los aspectos que puede tener este tipo, en miniatura. Retorna la y final."""
    nombres = [v.nombre for v in variantes_de(tipo)]
    if not nombres:
        return y
    iconos = []
    for nombre in nombres:
        imagen = recortar(sprites.sprite_enemigo(tipo, variante=nombre))
        alto = assets.ALTO_ICONO_VARIANTE
        ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
        iconos.append(pygame.transform.scale(imagen, (ancho, alto)))
    total = sum(i.get_width() for i in iconos) + 2 * (len(iconos) - 1)
    escala = min(1.0, (rect.width - 24) / total)
    x = rect.centerx - total * escala / 2
    for icono in iconos:
        if escala < 1.0:
            icono = pygame.transform.scale(icono, (max(1, round(icono.get_width() * escala)),
                                                   max(1, round(icono.get_height() * escala))))
        pantalla.blit(icono, (round(x), y))
        x += icono.get_width() + 2 * escala
    return y + assets.ALTO_ICONO_VARIANTE + 2


def _tarjeta_reglas(pantalla, rect, tarjeta):
    if tarjeta.clase == REGLAS_CUARTO:
        titulo, reglas = textos_enemigos.TITULO_REGLAS_CUARTO, textos_enemigos.REGLAS_CUARTO
    else:
        titulo, reglas = textos_enemigos.TITULO_REGLAS_JEFE, textos_enemigos.REGLAS_JEFE
    color = assets.COLOR_REGLAS_INSTRUCCIONES
    kit.panel(pantalla, rect, color, alfa=236, filo="arriba")
    dibujo.texto(pantalla, titulo, (rect.centerx, rect.top + 22), color, assets.TAMANIO_FUENTE_TITULO, negrita=True,
                 ancla="center")
    y = rect.top + 70
    for numero, regla in enumerate(reglas, start=1):
        dibujo.chip(pantalla, str(numero), (rect.left + 16, y), assets.COLOR_FONDO, color, color,
                    assets.TAMANIO_FUENTE_NORMAL, alto=28, margen=10)
        y = dibujo.parrafo(pantalla, regla, (rect.left + 54, y + 4), rect.width - 70, assets.COLOR_TEXTO_HUD,
                           assets.TAMANIO_FUENTE_NORMAL, interlineado=4) + 22
