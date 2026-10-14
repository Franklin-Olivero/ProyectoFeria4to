"""Efectos visuales del combate (solo presentación).

Cono de apuntado del jugador, marco sobre el enemigo apuntado, línea
discontinua hacia él, números de daño flotantes, mira del mouse y el
globo que muestra qué nodo del behavior tree ejecutó un enemigo en el
último frame (tecla Tab). Nada de esto cambia el estado del juego: los
textos flotantes son el único estado y es puramente decorativo.
"""

import math

import pygame

from src.core import assets
from src.core.balance import MOSTRAR_LINEA_APUNTADO
from src.ui import dibujo


class TextosFlotantes:
    """Lista de ("-1", posición, tiempo restante) que suben y desaparecen."""

    def __init__(self):
        self.textos = []

    def agregar(self, cadena, centro, color=assets.COLOR_TEXTO_DANIO):
        self.textos.append([cadena, pygame.Vector2(centro), assets.DURACION_TEXTO_DANIO, color])

    def actualizar(self, dt):
        for texto in self.textos:
            texto[1].y -= assets.VELOCIDAD_TEXTO_DANIO * dt
            texto[2] -= dt
        self.textos = [texto for texto in self.textos if texto[2] > 0]

    def limpiar(self):
        self.textos.clear()

    def dibujar(self, pantalla):
        for cadena, posicion, _, color in self.textos:
            dibujo.texto(pantalla, cadena, (round(posicion.x), round(posicion.y)), color,
                         assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")


def dibujar_cono_apuntado(pantalla, jugador, angulo_medio):
    """Abanico translúcido desde el jugador en su dirección de mirada."""
    origen = pygame.Vector2(jugador.rect.center)
    direccion = pygame.Vector2(jugador.direccion_mirada)
    if direccion.length_squared() == 0:
        return
    largo = assets.LARGO_CONO_APUNTADO
    puntos = [origen]
    pasos = 6
    for i in range(pasos + 1):
        angulo = -angulo_medio + (2 * angulo_medio) * i / pasos
        puntos.append(origen + direccion.rotate(angulo) * largo)
    dibujo.poligono_alfa(pantalla, assets.COLOR_CONO_APUNTADO, puntos)


def enemigo_apuntado(jugador, enemigos):
    """Enemigo vivo más cercano a la recta de apuntado (delante del
    jugador), o None si ninguno está a menos de TOLERANCIA_OBJETIVO px."""
    origen = pygame.Vector2(jugador.rect.center)
    direccion = pygame.Vector2(jugador.direccion_mirada)
    if direccion.length_squared() == 0:
        return None
    direccion = direccion.normalize()
    mejor, mejor_distancia = None, None
    for enemigo in enemigos:
        if not enemigo.vivo:
            continue
        hacia = pygame.Vector2(enemigo.rect.center) - origen
        avance = hacia.dot(direccion)
        if avance <= 0:
            continue
        desvio = (hacia - direccion * avance).length()
        tolerancia = assets.TOLERANCIA_OBJETIVO + max(enemigo.rect.width, enemigo.rect.height) / 2
        if desvio <= tolerancia and (mejor_distancia is None or avance < mejor_distancia):
            mejor, mejor_distancia = enemigo, avance
    return mejor


def dibujar_objetivo(pantalla, jugador, enemigo):
    """Línea discontinua jugador -> enemigo y marco de esquinas sobre él."""
    dibujo.linea_punteada(pantalla, assets.COLOR_LINEA_OBJETIVO, jugador.rect.center,
                          enemigo.rect.center, largo=5, hueco=7, grosor=2)
    dibujo.corchetes(pantalla, enemigo.rect, assets.COLOR_OBJETIVO, assets.LARGO_ESQUINA_OBJETIVO,
                     assets.GROSOR_OBJETIVO, assets.MARGEN_OBJETIVO)


def dibujar_globo_arbol(pantalla, enemigo):
    """Globo junto al enemigo con la ruta de nodos del último tick."""
    ruta = getattr(enemigo, "nodo_activo", None)
    if not ruta:
        return
    cadena = " › ".join(ruta)
    from src.ui.fuentes import fuente

    ancho_texto = fuente(assets.TAMANIO_FUENTE_NORMAL, True).size(cadena)[0]
    ancho = ancho_texto + 32
    alto = 58
    dx, dy = assets.DESPLAZAMIENTO_GLOBO
    y = enemigo.rect.centery + dy
    # Se abre hacia el lado donde hay más pantalla (en la mitad derecha
    # del cuarto va a la izquierda, para no tapar la terminal).
    if enemigo.rect.centerx > pantalla.get_width() // 2:
        x = enemigo.rect.centerx - dx - ancho
    else:
        x = enemigo.rect.centerx + dx
    y = max(assets.ALTO_HUD + 8, min(y, pantalla.get_height() - assets.ALTO_BARRA_CONTROLES - alto - 8))
    rect = pygame.Rect(x, y, ancho, alto)
    # Conector desde el borde del enemigo hasta el globo.
    ancla = rect.midleft if rect.left >= enemigo.rect.centerx else rect.midright
    pygame.draw.line(pantalla, assets.COLOR_BORDE_GLOBO, enemigo.rect.center, ancla, 2)
    dibujo.panel(pantalla, rect, assets.COLOR_FONDO_GLOBO, assets.COLOR_BORDE_GLOBO, 2)
    dibujo.texto(pantalla, "Árbol de comportamiento", (rect.left + 14, rect.top + 9),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    pygame.draw.rect(pantalla, assets.COLOR_TEAL, (rect.right - 20, rect.top + 11, 8, 8))
    dibujo.texto(pantalla, cadena, (rect.left + 14, rect.top + 29), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True)


def dibujar_mira(pantalla, jugador, sacudida):
    """Mira en la posición del mouse, sobre el HUD (no tiembla), y una
    línea tenue desde el jugador tal como se ve en pantalla."""
    mouse = pygame.mouse.get_pos()
    if MOSTRAR_LINEA_APUNTADO:
        origen = (jugador.rect.centerx + sacudida[0], jugador.rect.centery + sacudida[1])
        dibujo.linea_punteada(pantalla, assets.COLOR_LINEA_APUNTADO, origen, mouse,
                              largo=4, hueco=8, grosor=assets.GROSOR_LINEA_APUNTADO)
    radio, brazo = assets.RADIO_MIRA, assets.LARGO_CRUZ_MIRA
    pygame.draw.circle(pantalla, assets.COLOR_MIRA, mouse, radio, assets.GROSOR_MIRA)
    x, y = mouse
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        inicio = (x + dx * radio, y + dy * radio)
        fin = (x + dx * (radio + brazo), y + dy * (radio + brazo))
        pygame.draw.line(pantalla, assets.COLOR_MIRA, inicio, fin, assets.GROSOR_MIRA)


def dibujar_gracia(pantalla, jugador, fraccion):
    """Anillo de cuenta regresiva alrededor del jugador durante la gracia
    de entrada: el arco lleno se vacía de `fraccion` = 1 a 0."""
    radio = assets.RADIO_ANILLO_GRACIA
    caja = pygame.Rect(0, 0, radio * 2, radio * 2)
    caja.center = jugador.rect.center
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_ANILLO_GRACIA, caja.center, radio, assets.GROSOR_ANILLO_GRACIA)
    if fraccion > 0:
        inicio = math.pi / 2  # desde arriba, en sentido antihorario de pygame
        pygame.draw.arc(pantalla, assets.COLOR_ANILLO_GRACIA, caja, inicio, inicio + 2 * math.pi * fraccion,
                        assets.GROSOR_ANILLO_GRACIA)
