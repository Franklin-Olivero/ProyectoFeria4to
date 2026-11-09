"""Pantalla «El origen de la señal», capítulo 3 (solo presentación).

Dibuja el rastreo por DFS sobre el grafo de cuentas: a la izquierda el grafo
con lo que el jugador ya conoce (las cuentas sin visitar aparecen como nodos
apagados), en el centro la pila del hilo actual y a la derecha la ficha de la
cuenta con sus señales y las opciones. Al señalar una cuenta se ve el veredicto
y el orden en que el algoritmo DFS real habría recorrido la red.
Lee una Investigacion (src/story/investigacion.py); no la modifica.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, kit, layout

_RECT_GRAFO = pygame.Rect(40, 110, 520, 500)
_RECT_FICHA = pygame.Rect(576, 110, 664, 500)


def _posiciones(investigacion, rect):
    """Árbol por capas desde la cuenta inicial (BFS del Grafo real): posición estable."""
    _, distancias, _ = investigacion.grafo.bfs(investigacion.inicio)
    capas = {}
    for nodo, distancia in sorted(distancias.items(), key=lambda par: par[1]):
        capas.setdefault(distancia, []).append(nodo)
    posiciones = {}
    filas = max(capas) + 1
    for distancia, nodos in capas.items():
        y = rect.top + 60 + distancia * (rect.height - 130) / max(1, filas - 1)
        for i, nodo in enumerate(nodos):
            x = rect.left + (i + 1) * rect.width / (len(nodos) + 1)
            posiciones[nodo] = (round(x), round(y))
    return posiciones


def dibujar_investigacion(pantalla, investigacion, tiempo=0.0):
    pantalla.fill(assets.COLOR_NOCHE)
    kit.cabecera(pantalla, "Capítulo 3 · Investigación", "El origen de la señal", x=40, y=24, ancho=800)
    if not investigacion.terminada:
        kit.rotulo(pantalla, f"Profundidad del hilo: {len(investigacion.pila)}", (pantalla.get_width() - 40, 30),
                   assets.COLOR_TEXTO_SECUNDARIO, ancla="topright")
    _dibujar_grafo(pantalla, investigacion, tiempo)
    if investigacion.terminada:
        _dibujar_veredicto(pantalla, investigacion)
    else:
        _dibujar_ficha(pantalla, investigacion, tiempo)
    if not investigacion.terminada:
        kit.tecla(pantalla, "← →", "elegir", (_RECT_FICHA.left + 80, 640), ancla="center")
        kit.tecla(pantalla, "Enter", "confirmar", (_RECT_FICHA.left + 230, 640), ancla="center")


def _dibujar_grafo(pantalla, investigacion, tiempo):
    kit.panel(pantalla, _RECT_GRAFO, assets.COLOR_CIVITAS)
    kit.rotulo(pantalla, "Red de cuentas", (_RECT_GRAFO.left + 20, _RECT_GRAFO.top + 14), assets.COLOR_CIVITAS)
    posiciones = _posiciones(investigacion, _RECT_GRAFO)
    visitadas = set(investigacion.visitadas)
    pila = investigacion.pila
    en_pila = set(zip(pila, pila[1:])) | set(zip(pila[1:], pila))
    for a in investigacion.grafo.nodos():
        for b in investigacion.grafo.vecinos(a):
            if a < b:
                conocida = a in visitadas or b in visitadas
                if not conocida:
                    continue
                color = assets.COLOR_VERIFICADO if (a, b) in en_pila else assets.COLOR_ARISTA_RED
                pygame.draw.line(pantalla, color, posiciones[a], posiciones[b], 2 if (a, b) in en_pila else 1)
    for nodo, centro in posiciones.items():
        conocida = nodo in visitadas or any(v in visitadas for v in investigacion.grafo.vecinos(nodo))
        if not conocida:
            continue
        actual = nodo == investigacion.actual and not investigacion.terminada
        color = assets.COLOR_VERIFICADO if nodo in pila else assets.COLOR_CIVITAS if nodo in visitadas else assets.COLOR_NODO_NEUTRO
        radio = 11
        if actual:
            pygame.draw.circle(pantalla, color, centro, radio + 6 + round(2 * math.sin(tiempo * 4)), 1)
        pygame.draw.circle(pantalla, color, centro, radio)
        pygame.draw.circle(pantalla, assets.COLOR_NOCHE, centro, radio, 2)
        nombre = investigacion.cuentas[nodo]["nombre"] if nodo in visitadas else "?"
        dibujo.texto(pantalla, nombre, (centro[0], centro[1] + 15), assets.COLOR_TEXTO_HUD if nodo in visitadas else assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="midtop")
    pie = _RECT_GRAFO.bottom - 44
    kit.rotulo(pantalla, "Pila del hilo actual", (_RECT_GRAFO.left + 20, pie), assets.COLOR_VERIFICADO)
    layout.texto_en_ancho(pantalla, " › ".join(investigacion.cuentas[c]["nombre"] for c in pila), (_RECT_GRAFO.left + 20, pie + 20),
                          _RECT_GRAFO.width - 40, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, minimo=11)


def _dibujar_ficha(pantalla, investigacion, tiempo):
    kit.panel(pantalla, _RECT_FICHA, assets.COLOR_VERIFICADO)
    cuenta = investigacion.cuenta_actual
    x = _RECT_FICHA.left + 26
    y = _RECT_FICHA.top + 18
    kit.rotulo(pantalla, "Cuenta en revisión", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, cuenta["nombre"], (x, y + 18), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    y = layout.parrafo_en_caja(pantalla, cuenta["descripcion"], pygame.Rect(x, y + 52, _RECT_FICHA.width - 52, 62), assets.COLOR_TEXTO_HUD,
                               assets.TAMANIO_FUENTE_NORMAL, interlineado=4) + 6
    kit.rotulo(pantalla, "Señales", (x, y), assets.COLOR_VERIFICADO)
    y += 22
    for senal in cuenta["senales"]:
        pygame.draw.circle(pantalla, assets.COLOR_VERIFICADO, (x + 4, y + 9), 3)
        y = layout.parrafo_en_caja(pantalla, senal, pygame.Rect(x + 16, y, _RECT_FICHA.width - 68, 46), assets.COLOR_TEXTO_SECUNDARIO,
                                   assets.TAMANIO_FUENTE_NORMAL, interlineado=3) + 6
    opciones = investigacion.opciones()
    alto = 48
    y_op = _RECT_FICHA.bottom - 16 - len(opciones) * (alto + 8) + 8
    for i, opcion in enumerate(opciones):
        fila = pygame.Rect(x, y_op + i * (alto + 8), _RECT_FICHA.width - 52, alto)
        kit.opcion(pantalla, fila, opcion.etiqueta, i == investigacion.indice, tiempo)


def _dibujar_veredicto(pantalla, investigacion):
    resultado = investigacion.resultado
    color = assets.COLOR_VERIFICADO if resultado.correcto else assets.COLOR_ALERTA if resultado.tipo == "amplificador" else assets.COLOR_GRAVE
    kit.panel(pantalla, _RECT_FICHA, color, filo="arriba")
    x = _RECT_FICHA.left + 26
    y = _RECT_FICHA.top + 24
    kit.rotulo(pantalla, "Señalaste a", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, resultado.cuenta["nombre"], (x, y + 18), color, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    y = layout.parrafo_en_caja(pantalla, resultado.texto, pygame.Rect(x, y + 56, _RECT_FICHA.width - 52, 110), assets.COLOR_TEXTO_HUD,
                               assets.TAMANIO_FUENTE_MEDIA, interlineado=6) + 12
    kit.rotulo(pantalla, "Tu recorrido", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    y = layout.parrafo_en_caja(pantalla, " › ".join(investigacion.cuentas[c]["nombre"] for c in investigacion.visitadas),
                               pygame.Rect(x, y + 20, _RECT_FICHA.width - 52, 62), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, interlineado=3) + 12
    kit.rotulo(pantalla, "Orden del DFS real desde la misma cuenta", (x, y), assets.COLOR_VERIFICADO)
    layout.parrafo_en_caja(pantalla, " › ".join(investigacion.cuentas[c]["nombre"] for c in investigacion.orden_dfs_referencia()),
                           pygame.Rect(x, y + 20, _RECT_FICHA.width - 52, 62), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, interlineado=3)
    kit.tecla(pantalla, "Enter", "continuar", (_RECT_FICHA.centerx, _RECT_FICHA.bottom - 24), ancla="center")
