"""Dibujo de la terminal de decisión con Pygame (solo presentación).

Lee el estado de una TerminalDecision (src/ui/terminal_decision.py) y
lo pinta a pantalla completa:
    - título, subtítulo y reloj grande con barra de tiempo;
    - la tarjeta de la publicación viral (la situación a decidir);
    - el árbol N-ario como diagrama: el camino recorrido resaltado, los
      hijos del nodo actual como opciones elegibles (la seleccionada en
      teal), las ramas no abiertas apagadas y las hojas de resultado
      como vista previa con línea discontinua;
    - las migas de pan del camino y la leyenda.
No modifica la terminal. El diagrama es genérico: funciona con
cualquier árbol que construya la lógica.
"""

import pygame

from src.core import assets
from src.ui import dibujo, sprites
from src.ui.fuentes import fuente
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA

TITULO = "Terminal de decisión"

# Contenido fijo de la tarjeta (presentación de la situación "Publicación Viral").
PUBLICACION = {
    "usuario": "@NoticiaReal_Ya",
    "hace": "hace 3 min",
    "texto": "URGENTE: filtran que las urnas del puesto 14 ya vienen marcadas. ¡Comparte antes de que lo borren!",
    "imagen": "[imagen sin fuente]",
    "etiqueta": "Sin fuente oficial",
    "compartidos": "12.4 mil compartidos",
    "comentarios": "3.1 mil comentarios",
}

LEYENDA = [
    ("Camino recorrido", assets.COLOR_NODO_RECORRIDO, assets.COLOR_BORDE_RECORRIDO),
    ("Nodo elegible ahora", assets.COLOR_NODO_ELEGIBLE, assets.COLOR_NODO_ELEGIBLE),
    ("Rama sin abrir", assets.COLOR_NODO_CERRADO, assets.COLOR_BORDE_CERRADO),
    ("Resultado final (hoja)", assets.COLOR_FONDO_PANEL, assets.COLOR_MAGENTA),
]

ESTADO_RECORRIDO = "recorrido"
ESTADO_ELEGIBLE = "elegible"
ESTADO_CERRADO = "cerrado"
ESTADO_HOJA = "hoja"


def dibujar_terminal(pantalla, terminal, subtitulo=""):
    pantalla.fill(assets.COLOR_FONDO_TERMINAL)
    _dibujar_cuadricula(pantalla)
    dibujo.texto(pantalla, TITULO, (40, 36), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    if subtitulo:
        dibujo.texto(pantalla, subtitulo, (40, 82), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)

    _dibujar_reloj(pantalla, terminal)
    _dibujar_tarjeta(pantalla)
    _dibujar_arbol(pantalla, terminal)
    _dibujar_migas(pantalla, terminal)


def _dibujar_cuadricula(pantalla):
    """Cuadrícula tenue de fondo, como una pantalla de consola."""
    paso = 40
    color = (22, 20, 46)
    for x in range(0, pantalla.get_width(), paso):
        pygame.draw.line(pantalla, color, (x, 0), (x, pantalla.get_height()))
    for y in range(0, pantalla.get_height(), paso):
        pygame.draw.line(pantalla, color, (0, y), (pantalla.get_width(), y))


def _dibujar_reloj(pantalla, terminal):
    x, y = assets.POSICION_TIEMPO_TERMINAL
    dibujo.texto(pantalla, "Tiempo restante", (x, y - 34), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="midright")
    dibujo.texto(pantalla, f"{terminal.tiempo_restante:.1f} s", (x, y + 4), assets.COLOR_TIEMPO_TERMINAL,
                 assets.TAMANIO_FUENTE_ENORME, negrita=True, ancla="midright")
    rect = pygame.Rect(assets.RECT_BARRA_TIEMPO)
    fraccion = terminal.tiempo_restante / terminal.duracion if terminal.duracion else 0
    dibujo.barra(pantalla, rect, fraccion, assets.COLOR_TIEMPO_TERMINAL, borde=assets.COLOR_TIEMPO_TERMINAL)
    for i in range(1, 10):  # marcas cada 10 %
        mx = rect.left + rect.width * i // 10
        pygame.draw.line(pantalla, assets.COLOR_FONDO, (mx, rect.top + 2), (mx, rect.bottom - 2), 1)


def _dibujar_tarjeta(pantalla):
    rect = dibujo.panel(pantalla, assets.RECT_TARJETA_PUBLICACION, assets.COLOR_FONDO_TARJETA, None, 0, radio=4)
    x = rect.left + 20
    y = rect.top + 18
    dibujo.chip(pantalla, "Publicación viral", (x, y), assets.COLOR_TEXTO_HUD, assets.COLOR_MAGENTA,
                assets.COLOR_MAGENTA, alto=24)
    y += 44
    avatar = sprites.sprite(sprites.AVATAR, sprites.PALETA_AVATAR, escala=3)
    pantalla.blit(avatar, (x, y))
    dibujo.texto(pantalla, PUBLICACION["usuario"], (x + 40, y), assets.COLOR_TEXTO_TARJETA,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    dibujo.texto(pantalla, PUBLICACION["hace"], (x + 40, y + 20), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)
    y += 52
    y = dibujo.parrafo(pantalla, PUBLICACION["texto"], (x, y), rect.width - 40, assets.COLOR_TEXTO_TARJETA,
                       assets.TAMANIO_FUENTE_NORMAL, interlineado=6)
    y += 12
    imagen = pygame.Rect(x, y, rect.width - 40, 96)
    pygame.draw.rect(pantalla, assets.COLOR_IMAGEN_TARJETA, imagen, border_radius=3)
    for i, (ancho, alto) in enumerate(((120, 6), (80, 10), (170, 6), (60, 6))):
        linea = pygame.Rect(imagen.left + (8 if i % 2 == 0 else 24), imagen.top + 12 + i * 20, ancho, alto)
        pygame.draw.rect(pantalla, assets.COLOR_MAGENTA, linea)
    dibujo.texto(pantalla, PUBLICACION["imagen"], imagen.center, assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
    y = imagen.bottom + 16
    dibujo.chip(pantalla, PUBLICACION["etiqueta"], (x, y), assets.COLOR_MAGENTA, (252, 232, 238),
                assets.COLOR_MAGENTA, alto=24)
    y += 40
    dibujo.texto(pantalla, PUBLICACION["compartidos"], (x, y), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, PUBLICACION["comentarios"], (x, y + 18), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)


# ----------------------------------------------------------------------
# Diagrama del árbol
# ----------------------------------------------------------------------


def _nodos_visibles(terminal):
    """Decide qué nodos se dibujan y con qué estado.

    Se muestran: el camino raíz -> nodo actual, los hermanos de cada
    nodo del camino (cerrados), los hijos del nodo actual (elegibles) y
    los hijos de esos (vista previa como hojas). Retorna
    {nodo: estado} y el diccionario {nodo: padre}.
    """
    camino = terminal.camino()
    en_camino = set(id(n) for n in camino)
    estados, padres = {}, {}

    def registrar(nodo, padre, estado):
        estados[id(nodo)] = (nodo, estado)
        padres[id(nodo)] = padre

    registrar(camino[0], None, ESTADO_RECORRIDO)
    for padre in camino:
        for hijo in padre.hijos:
            if id(hijo) in en_camino:
                registrar(hijo, padre, ESTADO_RECORRIDO)
            elif padre is terminal.nodo_actual:
                registrar(hijo, padre, ESTADO_ELEGIBLE)
                for nieto in hijo.hijos:
                    registrar(nieto, hijo, ESTADO_HOJA)
            else:
                registrar(hijo, padre, ESTADO_CERRADO)
    return estados, padres


def _posicionar(terminal, panel):
    """Posición (centro) de cada nodo visible: por niveles, repartiendo
    el ancho entre los subárboles visibles (cada hoja ocupa 1 unidad)."""
    estados, padres = _nodos_visibles(terminal)
    hijos_visibles = {}
    for clave, (nodo, _) in estados.items():
        padre = padres[clave]
        if padre is not None:
            hijos_visibles.setdefault(id(padre), []).append(nodo)

    def unidades(nodo):
        hijos = hijos_visibles.get(id(nodo), [])
        return max(1, sum(unidades(h) for h in hijos))

    raiz = terminal.arbol.raiz
    total = unidades(raiz)
    ancho_unidad = min(assets.ANCHO_NODO_HOJA + 20, (panel.width - 40) / total)
    ancho_total = ancho_unidad * total
    izquierda = panel.centerx - ancho_total / 2

    niveles = {}

    def profundidad(nodo, nivel=0):
        niveles[id(nodo)] = nivel
        for h in hijos_visibles.get(id(nodo), []):
            profundidad(h, nivel + 1)

    profundidad(raiz)
    max_nivel = max(niveles.values())
    paso_y = min(125, (panel.height - 110) / max(1, max_nivel))
    posiciones = {}

    def asignar(nodo, x0):
        u = unidades(nodo)
        posiciones[id(nodo)] = (round(x0 + u * ancho_unidad / 2), round(panel.top + 42 + niveles[id(nodo)] * paso_y))
        x = x0
        for h in hijos_visibles.get(id(nodo), []):
            asignar(h, x)
            x += unidades(h) * ancho_unidad

    asignar(raiz, izquierda)
    return estados, padres, posiciones, ancho_unidad


def _rect_nodo(nodo, estado, centro, ancho_unidad):
    """Rect del nodo: el ancho preferido por tipo, sin pasar del espacio
    de su columna (el texto largo se parte en dos líneas)."""
    ancho = assets.ANCHO_NODO_HOJA if estado == ESTADO_HOJA else assets.ANCHO_NODO_ARBOL
    f = fuente(assets.TAMANIO_FUENTE_NORMAL, True)
    ancho = max(ancho, f.size(str(nodo.etiqueta))[0] + 28)
    ancho = min(ancho, int(ancho_unidad) - 14)
    rect = pygame.Rect(0, 0, ancho, assets.ALTO_NODO_ARBOL)
    rect.center = centro
    return rect


def _curva(pantalla, color, inicio, fin, grosor, punteada=False):
    """Curva suave (Bézier cúbica) de un nodo padre a un hijo."""
    (x0, y0), (x1, y1) = inicio, fin
    c0, c1 = (x0, y0 + (y1 - y0) * 0.5), (x1, y0 + (y1 - y0) * 0.5)
    puntos = []
    pasos = 24
    for i in range(pasos + 1):
        t = i / pasos
        x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * c0[0] + 3 * (1 - t) * t**2 * c1[0] + t**3 * x1
        y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * c0[1] + 3 * (1 - t) * t**2 * c1[1] + t**3 * y1
        puntos.append((x, y))
    if punteada:
        for a, b in zip(puntos[::2], puntos[1::2]):
            pygame.draw.line(pantalla, color, a, b, grosor)
    else:
        pygame.draw.lines(pantalla, color, False, puntos, grosor)


def _dibujar_arbol(pantalla, terminal):
    panel = dibujo.panel(pantalla, assets.RECT_PANEL_ARBOL, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1)
    estados, padres, posiciones, ancho_unidad = _posicionar(terminal, panel)
    seleccionado = terminal.hijo_seleccionado
    rects = {
        clave: _rect_nodo(nodo, estado, posiciones[clave], ancho_unidad)
        for clave, (nodo, estado) in estados.items()
    }

    # Ramas primero, para que los nodos queden encima.
    for clave, (nodo, estado) in estados.items():
        padre = padres[clave]
        if padre is None:
            continue
        rect, rect_padre = rects[clave], rects[id(padre)]
        if estado == ESTADO_RECORRIDO:
            color, grosor = assets.COLOR_RAMA_RECORRIDA, assets.GROSOR_RAMA_RECORRIDA
        elif estado == ESTADO_ELEGIBLE and nodo is seleccionado:
            color, grosor = assets.COLOR_RAMA_RECORRIDA, assets.GROSOR_RAMA
        else:
            color, grosor = assets.COLOR_RAMA, assets.GROSOR_RAMA
        _curva(pantalla, color, rect_padre.midbottom, rect.midtop, grosor, punteada=estado == ESTADO_HOJA)

    for clave, (nodo, estado) in estados.items():
        _dibujar_nodo(pantalla, nodo, estado, rects[clave], nodo is seleccionado)

    _dibujar_leyenda(pantalla, panel)


def _dibujar_nodo(pantalla, nodo, estado, rect, seleccionado):
    etiqueta = str(nodo.etiqueta)
    if estado == ESTADO_RECORRIDO:
        dibujo.panel(pantalla, rect, assets.COLOR_NODO_RECORRIDO, assets.COLOR_BORDE_RECORRIDO, 2)
        color_texto = assets.COLOR_TEXTO_HUD
    elif estado == ESTADO_ELEGIBLE and seleccionado:
        dibujo.panel(pantalla, rect.inflate(8, 8), None, assets.COLOR_NODO_ELEGIBLE, 1, radio=9)
        dibujo.panel(pantalla, rect, assets.COLOR_NODO_ELEGIBLE, assets.COLOR_NODO_ELEGIBLE, 2)
        color_texto = assets.COLOR_TEXTO_ELEGIBLE
        # Flecha a la izquierda del nodo seleccionado.
        px, py = rect.left - 16, rect.centery
        pygame.draw.polygon(pantalla, assets.COLOR_NODO_ELEGIBLE, [(px - 6, py - 7), (px + 4, py), (px - 6, py + 7)])
    elif estado == ESTADO_ELEGIBLE:
        dibujo.panel(pantalla, rect, assets.COLOR_NODO_CERRADO, assets.COLOR_NODO_ELEGIBLE, 2)
        color_texto = assets.COLOR_TEXTO_HUD
    elif estado == ESTADO_HOJA:
        borde = assets.COLOR_TEAL if etiqueta == PURIFICACION_EXITOSA else assets.COLOR_MAGENTA
        if etiqueta not in (PURIFICACION_EXITOSA, DETONACION):
            borde = assets.COLOR_BORDE_CERRADO
        dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, borde, 2)
        color_texto = borde
    else:
        dibujo.panel(pantalla, rect, assets.COLOR_NODO_CERRADO, assets.COLOR_BORDE_CERRADO, 2)
        color_texto = assets.COLOR_TEXTO_SECUNDARIO
        if nodo.hijos:
            dibujo.texto(pantalla, "▸", (rect.right - 10, rect.centery), assets.COLOR_TEXTO_APAGADO,
                         assets.TAMANIO_FUENTE_PEQUENA, ancla="midright")

    # Texto en una o dos líneas según quepa.
    lineas = dibujo.ajustar_texto(etiqueta, assets.TAMANIO_FUENTE_NORMAL, rect.width - 24, negrita=True)
    alto = fuente(assets.TAMANIO_FUENTE_NORMAL, True).get_height()
    y = rect.centery - (len(lineas) - 1) * alto / 2
    for linea in lineas[:2]:
        dibujo.texto(pantalla, linea, (rect.centerx, y), color_texto, assets.TAMANIO_FUENTE_NORMAL,
                     negrita=True, ancla="center")
        y += alto


def _dibujar_leyenda(pantalla, panel):
    x = panel.right - 230
    y = panel.bottom - 108
    for nombre, relleno, borde in LEYENDA:
        dibujo.panel(pantalla, (x, y, 22, 16), relleno, borde, 2, radio=3)
        dibujo.texto(pantalla, nombre, (x + 32, y + 8), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft")
        y += 26


def _dibujar_migas(pantalla, terminal):
    x, y = assets.POSICION_CAMINO_TERMINAL
    dibujo.texto(pantalla, "Camino", (x, y - 20), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    for nodo in terminal.camino():
        rect = dibujo.chip(pantalla, nodo.etiqueta, (x, y), assets.COLOR_TEAL, assets.COLOR_NODO_RECORRIDO,
                           assets.COLOR_TEAL, assets.TAMANIO_FUENTE_NORMAL, alto=30, margen=10)
        x = rect.right + 8
        dibujo.texto(pantalla, "›", (x, y + 15), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MEDIA,
                     ancla="midleft")
        x += 16
    if terminal.nodo_actual.hijos:
        dibujo.chip(pantalla, "?", (x, y), assets.COLOR_AMARILLO, assets.COLOR_FONDO_PANEL, assets.COLOR_AMARILLO,
                    assets.TAMANIO_FUENTE_NORMAL, alto=30, margen=10)
