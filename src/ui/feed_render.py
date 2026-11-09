"""Señales pequeñas del mundo narrativo (solo presentación).

    dibujar_feed: comentario de un ciudadano, como una tarjeta de Civitas.
        Su borde dice cómo te ve la ciudad; nunca tapa el centro del juego.
    dibujar_prueba_suelta: la prueba que queda en el suelo de un cuarto limpio.
    dibujar_baliza: marca en la ciudad de la siguiente etapa de la misión de
        redención, o flecha en el borde de la vista si está fuera de pantalla.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, kit, layout

COLOR_POR_NIVEL = {
    "referente": assets.COLOR_VERIFICADO,
    "confiable": assets.COLOR_VERIFICADO,
    "neutral": assets.COLOR_CIVITAS,
    "cuestionada": assets.COLOR_ALERTA,
    "crisis": assets.COLOR_GRAVE,
}


def dibujar_feed(pantalla, texto, nivel, restante):
    entrada = layout.fraccion_entrada(assets.DURACION_FEED_CIVITAS - restante, 0.4)
    rect = pygame.Rect(assets.RECT_FEED_CIVITAS)
    rect.x += round((1 - entrada) * 40)
    color = COLOR_POR_NIVEL.get(nivel, assets.COLOR_CIVITAS)
    kit.panel(pantalla, rect, color, alfa=235)
    kit.rotulo(pantalla, "Civitas · Te mencionan", (rect.left + 16, rect.top + 8), color)
    layout.parrafo_en_caja(pantalla, texto, pygame.Rect(rect.left + 16, rect.top + 28, rect.width - 30, rect.height - 34),
                           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, interlineado=2)


def dibujar_prueba_suelta(superficie, punto, tiempo):
    """Carpeta de documentos que flota y brilla: se reconoce sin leer nada."""
    x, y = punto
    flote = round(3 * math.sin(tiempo * 3))
    radio = 20 + round(3 * math.sin(tiempo * 4))
    halo = pygame.Surface((radio * 4, radio * 4), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*assets.COLOR_VERIFICADO, 46), (radio * 2, radio * 2), radio * 2)
    pygame.draw.circle(halo, (*assets.COLOR_VERIFICADO, 90), (radio * 2, radio * 2), radio)
    superficie.blit(halo, halo.get_rect(center=(x, y)))
    pygame.draw.ellipse(superficie, assets.COLOR_SOMBRA_ENTIDAD[:3], (x - 14, y + 14, 28, 8))
    carpeta = pygame.Rect(x - 13, y - 11 + flote, 26, 20)
    pygame.draw.rect(superficie, assets.COLOR_ALERTA, (carpeta.left, carpeta.top - 4, 12, 6))
    pygame.draw.rect(superficie, assets.COLOR_ALERTA, carpeta)
    pygame.draw.rect(superficie, assets.COLOR_TEXTO_HUD, (carpeta.left + 4, carpeta.top + 5, 18, 2))
    pygame.draw.rect(superficie, assets.COLOR_TEXTO_HUD, (carpeta.left + 4, carpeta.top + 10, 12, 2))
    pygame.draw.rect(superficie, assets.COLOR_NOCHE, carpeta, 1)


def dibujar_baliza(pantalla, punto, vista, tiempo):
    x, y = punto
    if vista.collidepoint(x, y):
        for i in range(3):
            fase = (tiempo * 0.8 + i / 3) % 1.0
            radio = round(10 + fase * 42)
            capa = pygame.Surface((radio * 2 + 4, radio * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(capa, (*assets.COLOR_VERIFICADO, round(180 * (1 - fase))), (radio + 2, radio + 2), radio, 2)
            pantalla.blit(capa, capa.get_rect(center=(x, y)))
        pygame.draw.circle(pantalla, assets.COLOR_VERIFICADO, (x, y), 6)
        pygame.draw.line(pantalla, assets.COLOR_VERIFICADO, (x, y), (x, y - 42), 2)
        return
    # Fuera de la vista: flecha en el borde, hacia donde hay que caminar.
    centro = pygame.Vector2(vista.center)
    direccion = pygame.Vector2(x, y) - centro
    if direccion.length_squared() == 0:
        return
    direccion = direccion.normalize()
    escala = min((vista.width / 2 - 34) / max(abs(direccion.x), 0.001), (vista.height / 2 - 34) / max(abs(direccion.y), 0.001))
    punta = centro + direccion * escala
    normal = pygame.Vector2(-direccion.y, direccion.x)
    latido = 2 * math.sin(tiempo * 5)
    puntos = [punta + direccion * (10 + latido), punta - direccion * 8 + normal * 9, punta - direccion * 8 - normal * 9]
    pygame.draw.polygon(pantalla, assets.COLOR_VERIFICADO, puntos)
    pygame.draw.polygon(pantalla, assets.COLOR_NOCHE, puntos, 1)
    dibujo.texto(pantalla, "MISIÓN", punta - direccion * 26, assets.COLOR_VERIFICADO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
