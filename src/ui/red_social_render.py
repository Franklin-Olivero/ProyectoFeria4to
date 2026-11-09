"""Pantalla de propagación por la red social (solo presentación).

Dibuja el grafo de ciudadanos (nodos en círculo, aristas de contacto) y
anima la onda del BFS de la última publicación: cada SEGUNDOS_POR_CAPA
se enciende una capa más (magenta = recibió el rumor; teal = recibió
la corrección; amarillo = origen). A la derecha, los datos: a cuántos
llegó, en cuántos saltos, la cadena de contagio más larga, el rastreo
DFS desde el origen y, si hubo corrección, a quiénes alcanzó. No
modifica la red; lee Campania.red y Campania.ultima_propagacion.
"""

import math

import pygame

from src.core import assets
from src.story.red_social import CORRECCION
from src.ui import dibujo, kit, layout

TITULO = "Así viajó la publicación"
SUBTITULO = "Grafo social de Ciudad Nova · propagación por BFS (anchura), rastreo por DFS (profundidad)"


def _posiciones(red):
    """Centro de cada ciudadano, repartidos en un círculo (orden de inserción)."""
    nodos = red.ciudadanos()
    cx, cy = assets.CENTRO_GRAFO_SOCIAL
    posiciones = {}
    for i, nodo in enumerate(nodos):
        angulo = -math.pi / 2 + 2 * math.pi * i / max(1, len(nodos))
        posiciones[nodo] = (round(cx + math.cos(angulo) * assets.RADIO_GRAFO_SOCIAL),
                            round(cy + math.sin(angulo) * assets.RADIO_GRAFO_SOCIAL))
    return posiciones


def posiciones_en(red, rect):
    """Los mismos ciudadanos en círculo, dentro de `rect` (misión de redención)."""
    nodos = red.ciudadanos()
    radio_x, radio_y = rect.width / 2 - 40, rect.height / 2 - 30
    return {nodo: (round(rect.centerx + math.cos(-math.pi / 2 + 2 * math.pi * i / max(1, len(nodos))) * radio_x),
                   round(rect.centery + math.sin(-math.pi / 2 + 2 * math.pi * i / max(1, len(nodos))) * radio_y))
            for i, nodo in enumerate(nodos)}


def capas_visibles(propagacion, tiempo):
    """Cuántas capas del BFS se muestran ya en el instante `tiempo`."""
    if propagacion is None:
        return 0
    return min(len(propagacion.capas), 1 + int(tiempo / assets.SEGUNDOS_POR_CAPA))


def dibujar_pantalla_propagacion(pantalla, campania, tiempo):
    pantalla.fill(assets.COLOR_NOCHE)
    dibujo.texto(pantalla, TITULO, (60, 36), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    dibujo.texto(pantalla, SUBTITULO, (60, 82), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)
    red = campania.red
    rumor = campania.ultima_propagacion
    correccion = campania.correccion_reciente()
    if correccion is not None and rumor is not None and red.historial.index(correccion) < red.historial.index(rumor):
        correccion = None  # una corrección vieja, de otra zona
    verdad = rumor is not None and rumor.tipo == CORRECCION  # lo que viajó era verdadero
    if verdad:
        correccion = None

    panel = kit.panel(pantalla, assets.RECT_PANEL_GRAFO_SOCIAL, assets.COLOR_CIVITAS)
    posiciones = _posiciones(red)
    # Aristas de contacto.
    dibujadas = set()
    for a in red.ciudadanos():
        for b in red.grafo.vecinos(a):
            clave = frozenset((a, b))
            if clave in dibujadas:
                continue
            dibujadas.add(clave)
            pygame.draw.line(pantalla, assets.COLOR_ARISTA_SOCIAL, posiciones[a], posiciones[b], 2)

    visibles = capas_visibles(rumor, tiempo)
    alcanzados = set()
    if rumor is not None:
        for capa in rumor.capas[:visibles]:
            alcanzados.update(capa)
        for de, a in rumor.aristas:
            if a in alcanzados:
                pygame.draw.line(pantalla, assets.COLOR_ARISTA_CORRECCION if verdad else assets.COLOR_ARISTA_RUMOR,
                                 posiciones[de], posiciones[a], assets.GROSOR_ARISTA_PROPAGADA)
    corregidos = set()
    if correccion is not None and rumor is not None and visibles >= len(rumor.capas):
        retraso = tiempo - len(rumor.capas) * assets.SEGUNDOS_POR_CAPA
        for capa in correccion.capas[:capas_visibles(correccion, max(0.0, retraso))]:
            corregidos.update(capa)
        for de, a in correccion.aristas:
            if a in corregidos:
                pygame.draw.line(pantalla, assets.COLOR_ARISTA_CORRECCION, posiciones[de], posiciones[a], 2)

    for nodo, (x, y) in posiciones.items():
        if rumor is not None and nodo == rumor.origen:
            relleno = assets.COLOR_NODO_ORIGEN
        elif nodo in corregidos:
            relleno = assets.COLOR_NODO_CORREGIDO
        elif nodo in alcanzados:
            relleno = assets.COLOR_NODO_CORREGIDO if verdad else assets.COLOR_NODO_RUMOR
        else:
            relleno = assets.COLOR_NODO_SOCIAL
        pygame.draw.circle(pantalla, relleno, (x, y), assets.RADIO_NODO_SOCIAL)
        pygame.draw.circle(pantalla, assets.COLOR_BORDE_NODO_SOCIAL, (x, y), assets.RADIO_NODO_SOCIAL, 2)
        # Nombre afuera del círculo, hacia el lado donde queda el nodo.
        cx, cy = assets.CENTRO_GRAFO_SOCIAL
        if x > cx + 10:
            lado = "midleft"
        elif x < cx - 10:
            lado = "midright"
        else:
            lado = "midbottom" if y < cy else "midtop"
        dx = assets.RADIO_NODO_SOCIAL + 6
        destino = {"midleft": (x + dx, y), "midright": (x - dx, y), "midtop": (x, y + dx),
                   "midbottom": (x, y - dx)}[lado]
        dibujo.texto(pantalla, red.nombre(nodo).split()[0], destino, assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla=lado)
    _leyenda(pantalla, panel)
    _datos(pantalla, campania, rumor, correccion, visibles)

    chip = dibujo.chip(pantalla, "Enter", (640 - 40, 686), ancla="midright")
    dibujo.texto(pantalla, "para continuar", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")


def _leyenda(pantalla, panel):
    y = panel.bottom - 24
    x = panel.left + 20
    for texto, color in (("origen", assets.COLOR_NODO_ORIGEN), ("recibió el rumor", assets.COLOR_NODO_RUMOR),
                         ("recibió la corrección", assets.COLOR_NODO_CORREGIDO), ("no le llegó", assets.COLOR_NODO_SOCIAL)):
        pygame.draw.circle(pantalla, color, (x + 8, y), 8)
        r = dibujo.texto(pantalla, texto, (x + 22, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                         ancla="midleft")
        x = r.right + 18


def _datos(pantalla, campania, rumor, correccion, visibles):
    red = campania.red
    panel = kit.panel(pantalla, assets.RECT_PANEL_DATOS_SOCIAL, assets.COLOR_VERIFICADO)
    x, y = panel.left + 20, panel.top + 18
    if rumor is None:
        dibujo.texto(pantalla, "Esta publicación no salió de la zona.", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
        return
    total = len(red.ciudadanos())
    contados = sum(len(capa) for capa in rumor.capas[:visibles])
    verdad = rumor.tipo == CORRECCION
    layout.texto_en_ancho(pantalla, f"{'La información' if verdad else 'La publicación'} llegó a {contados} de {total} ciudadanos", (x, y), panel.width - 40,
                          assets.COLOR_NODO_CORREGIDO if verdad else assets.COLOR_NODO_RUMOR, assets.TAMANIO_FUENTE_MEDIA, negrita=True,
                          minimo=assets.TAMANIO_FUENTE_NORMAL)
    y += 30
    dibujo.texto(pantalla, f"Origen: {red.nombre(rumor.origen)} ({red.roles.get(rumor.origen, '')})", (x, y),
                 assets.COLOR_TEXTO_HUD)
    y += 22
    dibujo.texto(pantalla, f"Saltos (capas del BFS): {rumor.saltos}  ·  máximo permitido: 3", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    y += 22
    for d, capa in enumerate(rumor.capas[:visibles]):
        nombres = ", ".join(red.nombre(n).split()[0] for n in capa)
        for linea in dibujo.ajustar_texto(f"capa {d}: {nombres}", assets.TAMANIO_FUENTE_PEQUENA, panel.width - 40)[:2]:
            dibujo.texto(pantalla, linea, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
            y += 17
    y += 8
    lejano = max(rumor.alcanzados, key=lambda n: len(rumor.cadena_hasta(n)))
    cadena = " → ".join(red.nombre(n).split()[0] for n in rumor.cadena_hasta(lejano))
    dibujo.texto(pantalla, "Cadena de contagio más larga:", (x, y), assets.COLOR_TEXTO_HUD, negrita=True)
    y += 20
    for linea in dibujo.ajustar_texto(cadena, assets.TAMANIO_FUENTE_PEQUENA, panel.width - 40)[:2]:
        dibujo.texto(pantalla, linea, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
        y += 17
    y += 8
    dfs = red.rastrear(rumor.origen)
    rastro = " → ".join(red.nombre(n).split()[0] for n in dfs)
    dibujo.texto(pantalla, "Rastreo DFS desde el origen (a quién pudo llegar):", (x, y), assets.COLOR_TEXTO_HUD, negrita=True)
    y += 20
    for linea in dibujo.ajustar_texto(rastro, assets.TAMANIO_FUENTE_PEQUENA, panel.width - 40):
        dibujo.texto(pantalla, linea, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
        y += 17
    y += 10
    if verdad:
        texto = "Quienes la recibieron ya pueden actuar. Cada persona informada suma información verificada a la ciudad."
    elif correccion is not None:
        layout.texto_en_ancho(pantalla, f"Tu corrección alcanzó a {correccion.total} ciudadanos", (x, y), panel.width - 40,
                              assets.COLOR_NODO_CORREGIDO, assets.TAMANIO_FUENTE_MEDIA, negrita=True,
                              minimo=assets.TAMANIO_FUENTE_NORMAL)
        y += 26
        texto = ("Quienes la recibieron reenvían menos en adelante. Lo que ya vieron no se borra: "
                 f"{len(red.expuestos)} personas siguen expuestas al rumor.")
    else:
        texto = ("Sin corrección publicada, cada persona alcanzada suma desinformación y "
                 "sigue reenviando con la misma facilidad.")
    for linea in dibujo.ajustar_texto(texto, assets.TAMANIO_FUENTE_NORMAL, panel.width - 40):
        dibujo.texto(pantalla, linea, (x, y), assets.COLOR_TEXTO_SECUNDARIO)
        y += 20
