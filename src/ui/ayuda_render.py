"""Panel de ayuda del modo historia (solo presentación).

Se abre con H en Ciudad Nova: objetivo, cómo ganar, controles, los
cuatro roles con su matiz narrativo y qué significa cada indicador.
Texto fijo en español; no modifica ningún estado.
"""

import pygame

from src.core import assets
from src.ui import dibujo, layout

TITULO = "Ayuda · Civitas: Código Nova"
SECCIONES = [
    ("Objetivo", [
        "Ciudad Nova elige alcalde y la red Civitas se llena de rumores firmados por NOVA_404.",
        "Entra a cada edificio, limpia sus cuartos (cada cuarto limpio revela una prueba) y decide",
        "qué hacer con la publicación de esa zona. Verificar antes de compartir y reportar con pruebas",
        "purifica la zona; compartir sin contexto o reportar en masa la detona.",
    ]),
    ("Cómo ganar", [
        "Purifica al menos una zona para abrir la Alcaldía y derrota al Servidor Central (3 fases, 180 s).",
        "Recorrido completo: Colegio → Hospital → Empresa de Medios → Alcaldía. Con las 3 pistas y la",
        "cuenta coordinadora bien señalada se desbloquea el final secreto. El colapso al 100 % es derrota.",
    ]),
    ("Controles", [
        "Ciudad: WASD caminar · E entrar · G ruta sugerida · TAB destino · M mapa · I estado · H ayuda · ESC menú.",
        "Combate: WASD mover · ratón apuntar · clic o ESPACIO disparar · F habilidad · SHIFT dash · M minimapa.",
        "Diálogos y terminal: ENTER avanza o confirma · ← → eligen · ESC salta el diálogo.",
    ]),
    ("Roles", [
        "Ciudadano: aguanta más; cada éxito refuerza la confianza vecinal.   Influencer: el más rápido;",
        "amplifica más lo que comparte.   Periodista: alto daño; identifica una fuente extra al entrar.",
        "Candidato: mayor daño por golpe; las penalizaciones a su reputación pesan doble.",
    ]),
    ("Indicadores (0-100)", [
        "Información verificada, confianza, convivencia, bienestar digital y participación responsable suben",
        "con buenas decisiones; desinformación y conflictos bajan. Deciden las elecciones simuladas y el final.",
        "El colapso electoral (barra superior) es aparte: sube con cada detonación y es la derrota global.",
    ]),
]
TEXTO_CERRAR = "H o Esc: cerrar"


def dibujar_ayuda(pantalla, transcurrido=1.0):
    rect = layout.entrada(assets.RECT_PANEL_AYUDA, transcurrido)
    dibujo.panel_alfa(pantalla, rect, assets.COLOR_FONDO_AYUDA, radio=10)
    dibujo.panel(pantalla, rect, None, assets.COLOR_BORDE_PANEL, 1, radio=10)
    x, y = rect.left + 28, rect.top + 18
    dibujo.texto(pantalla, TITULO, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    dibujo.chip(pantalla, TEXTO_CERRAR, (rect.right - 24, y + 2), ancla="topright")
    y += 44
    for titulo, lineas in SECCIONES:
        dibujo.texto(pantalla, titulo, (x, y), assets.COLOR_TEAL, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
        y += 22
        y = layout.parrafo_en_caja(pantalla, " ".join(lineas), (x, y, rect.width - 56, 18 * len(lineas) + 20),
                                   assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, interlineado=5)
        y += 8
