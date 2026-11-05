"""Dibujo de la terminal de decisión con Pygame (solo presentación).

El momento central de cada mazmorra. A la izquierda la publicación tal como
circula, con su fuente; a la derecha las pruebas que el jugador alcanzó a
reunir (las que faltan se ven como huecos); abajo las opciones del nodo actual
del árbol N-ario como tarjetas grandes.

Regla de diseño: nada delata la respuesta. El foco es siempre violeta, las
opciones no tienen colores de "bien o mal" y el diagrama del árbol muestra
las ramas abiertas pero NUNCA a qué resultado lleva una hoja. El árbol sigue
siendo el real (src/structures/tree.py): el mini diagrama lee el mismo
ArbolDecision que navega la TerminalDecision.

Funciona también con el árbol fijo (sin escenario de campaña): usa la
publicación PUBLICACION de este módulo.
"""

import pygame

from src.core import assets
from src.ui import dibujo, kit, layout, tarjetas_render
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA

TITULO = "Terminal Civitas"

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

_RECT_POST = pygame.Rect(40, 96, 380, 400)
_RECT_PRUEBAS = pygame.Rect(436, 96, 804, 300)
_RECT_ARBOL = pygame.Rect(436, 404, 804, 92)
_RECT_OPCIONES = pygame.Rect(40, 508, 1200, 148)
_ETIQUETAS_FUENTE = {"conocida": "Fuente conocida", "desconocida": "Fuente desconocida"}
_HOJAS = (PURIFICACION_EXITOSA, DETONACION)


def dibujar_terminal(pantalla, terminal, subtitulo="", post=None, estado_evidencia=None,
                     evidencias=None, total_evidencias=0, verificacion="", exige_mas_pruebas=False, tiempo=0.0,
                     nota_decisor=""):
    """`post`: publicación (modo historia; None = la fija PUBLICACION);
    `evidencias`: pruebas reveladas de la zona; `verificacion`: lo que
    descubre el jugador al elegir Verificar; `exige_mas_pruebas`: con
    reputación cuestionada, la ciudad ya no acepta pruebas parciales."""
    pantalla.fill(assets.COLOR_NOCHE)
    _fondo_terminal(pantalla)
    kit.rotulo(pantalla, TITULO, (40, 22), assets.COLOR_CIVITAS)
    layout.texto_en_ancho(pantalla, subtitulo or "Decide qué hacer con esta publicación", (40, 42), 800,
                          assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, negrita=True)
    if nota_decisor:
        kit.rotulo(pantalla, nota_decisor, (40, 70), assets.COLOR_ALERTA)
    _dibujar_reloj(pantalla, terminal)
    tarjetas_render.dibujar_tarjeta_publicacion(pantalla, _RECT_POST, post if post is not None else PUBLICACION, None,
                                                chip=_texto_fuente(post))
    _dibujar_pruebas(pantalla, evidencias, total_evidencias, post, estado_evidencia, exige_mas_pruebas)
    _dibujar_arbol(pantalla, terminal)
    _dibujar_opciones(pantalla, terminal, verificacion, tiempo)


def _texto_fuente(post):
    fuente_post = (post or {}).get("fuente") or {}
    return _ETIQUETAS_FUENTE.get(fuente_post.get("tipo"), "Publicación en Civitas")


def _fondo_terminal(pantalla):
    """Trama tenue y una franja de luz: la pantalla de una consola."""
    paso = 32
    ancho, alto = pantalla.get_size()
    for x in range(0, ancho, paso):
        pygame.draw.line(pantalla, assets.COLOR_TRAMA_TERMINAL, (x, 0), (x, alto))
    for y in range(0, alto, paso):
        pygame.draw.line(pantalla, assets.COLOR_TRAMA_TERMINAL, (0, y), (ancho, y))


def _dibujar_reloj(pantalla, terminal):
    """Reloj discreto: presiona sin gritar. Solo se vuelve ámbar y rojo al final."""
    restante = terminal.tiempo_restante
    fraccion = restante / terminal.duracion if terminal.duracion else 0
    color = assets.COLOR_GRAVE if restante <= 5 else assets.COLOR_ALERTA if restante <= 12 else assets.COLOR_TEXTO_HUD
    x = pantalla.get_width() - 40
    kit.rotulo(pantalla, "Tiempo para decidir", (x, 22), assets.COLOR_TEXTO_SECUNDARIO, ancla="topright")
    dibujo.texto(pantalla, f"{restante:0.0f} s", (x, 40), color, assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="topright")
    barra = pygame.Rect(x - 280, 74, 280, 5)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_BARRA, barra, border_radius=2)
    pygame.draw.rect(pantalla, color, (barra.left, barra.top, round(barra.width * fraccion), barra.height), border_radius=2)


def _dibujar_pruebas(pantalla, evidencias, total, post, estado, exige_mas_pruebas):
    kit.panel(pantalla, _RECT_PRUEBAS, assets.COLOR_VERIFICADO)
    x = _RECT_PRUEBAS.left + 22
    y = _RECT_PRUEBAS.top + 14
    evidencias = evidencias or []
    kit.rotulo(pantalla, f"Pruebas reunidas · {len(evidencias)} de {total}", (x, y), assets.COLOR_VERIFICADO)
    fuente_post = (post or {}).get("fuente") or {}
    if fuente_post.get("detalle"):
        layout.texto_en_ancho(pantalla, fuente_post["detalle"], (_RECT_PRUEBAS.right - 22, y), 500, assets.COLOR_TEXTO_SECUNDARIO,
                              assets.TAMANIO_FUENTE_PEQUENA, ancla="topright", minimo=11)
    y += 28
    alto = (_RECT_PRUEBAS.bottom - y - 12 - 10 * max(0, total - 1)) // max(1, total)
    for indice in range(total):
        fila = pygame.Rect(x, y + indice * (alto + 10), _RECT_PRUEBAS.width - 44, alto)
        if indice < len(evidencias):
            _prueba(pantalla, fila, evidencias[indice])
        else:
            dibujo.panel(pantalla, fila, None, assets.COLOR_BORDE_VIDRIO, 1, radio=6)
            dibujo.texto(pantalla, "Prueba no encontrada", (fila.left + 14, fila.centery), assets.COLOR_TEXTO_APAGADO,
                         assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
    if exige_mas_pruebas:
        kit.rotulo(pantalla, "Por tu reputación, la ciudad ya no acepta pruebas parciales", (x, _RECT_PRUEBAS.bottom - 18),
                   assets.COLOR_ALERTA)


def _prueba(pantalla, fila, evidencia):
    dibujo.panel(pantalla, fila, assets.COLOR_OPCION_FONDO, assets.COLOR_BORDE_VIDRIO, 1, radio=6)
    layout.texto_en_ancho(pantalla, f"{evidencia['titulo']}  ·  {evidencia['fuente']}", (fila.left + 14, fila.top + 7), fila.width - 28,
                          assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, minimo=11)
    layout.parrafo_en_caja(pantalla, evidencia["fragmento"], pygame.Rect(fila.left + 14, fila.top + 26, fila.width - 28, fila.height - 30),
                           assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, interlineado=2)


# ----------------------------------------------------------------------
# Diagrama compacto del árbol (real, sin revelar resultados)
# ----------------------------------------------------------------------


def _rama_visible(nodo):
    """Hijos que se dibujan: las hojas de resultado nunca se muestran."""
    return [h for h in nodo.hijos if h.etiqueta not in _HOJAS]


def _dibujar_arbol(pantalla, terminal):
    kit.panel(pantalla, _RECT_ARBOL, assets.COLOR_CIVITAS)
    kit.rotulo(pantalla, "Árbol de decisión", (_RECT_ARBOL.left + 22, _RECT_ARBOL.top + 12), assets.COLOR_CIVITAS)
    camino = terminal.camino()
    en_camino = {id(n) for n in camino}
    raiz = terminal.arbol.raiz
    y_raiz, y_uno, y_dos = _RECT_ARBOL.top + 18, _RECT_ARBOL.top + 46, _RECT_ARBOL.top + 74
    cx = _RECT_ARBOL.centerx
    primeros = _rama_visible(raiz)
    ancho = (_RECT_ARBOL.width - 80) / max(1, len(primeros))
    pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, (cx, y_raiz), 6)
    seleccionado = terminal.hijo_seleccionado
    for i, hijo in enumerate(primeros):
        x = round(_RECT_ARBOL.left + 40 + ancho * (i + 0.5))
        activo = id(hijo) in en_camino
        pygame.draw.line(pantalla, assets.COLOR_CIVITAS if activo else assets.COLOR_ARISTA_RED, (cx, y_raiz), (x, y_uno), 2 if activo else 1)
        _punto_arbol(pantalla, (x, y_uno), hijo, activo, hijo is seleccionado)
        layout.texto_en_ancho(pantalla, hijo.etiqueta, (x + 10, y_uno), round(ancho) - 24,
                              assets.COLOR_TEXTO_HUD if activo or hijo is seleccionado else assets.COLOR_TEXTO_APAGADO,
                              assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft", minimo=11)
        segundos = _rama_visible(hijo) if activo else []
        for j, nieto in enumerate(segundos):
            x2 = round(x - 24 + j * 200 / max(1, len(segundos)))
            pygame.draw.line(pantalla, assets.COLOR_CIVITAS if id(nieto) in en_camino else assets.COLOR_ARISTA_RED, (x, y_uno), (x2, y_dos), 1)
            _punto_arbol(pantalla, (x2, y_dos), nieto, id(nieto) in en_camino, nieto is seleccionado)


def _punto_arbol(pantalla, centro, nodo, activo, seleccionado):
    if seleccionado:
        pygame.draw.circle(pantalla, assets.COLOR_CIVITAS, centro, 6)
        pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, centro, 8, 1)
    elif activo:
        pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, centro, 5)
    else:
        pygame.draw.circle(pantalla, assets.COLOR_ARISTA_RED, centro, 4)


# ----------------------------------------------------------------------
# Opciones
# ----------------------------------------------------------------------


def _dibujar_opciones(pantalla, terminal, verificacion, tiempo):
    rect = _RECT_OPCIONES
    opciones = _rama_visible(terminal.nodo_actual)
    if not opciones:
        return
    en_raiz = terminal.nodo_actual is terminal.arbol.raiz
    y = rect.top
    if not en_raiz:
        pregunta = verificacion if terminal.nodo_actual.etiqueta == "Verificar" and verificacion else _pregunta_de(terminal.nodo_actual.etiqueta)
        kit.rotulo(pantalla, terminal.nodo_actual.etiqueta, (rect.left, y), assets.COLOR_CIVITAS)
        layout.parrafo_en_caja(pantalla, pregunta, pygame.Rect(rect.left + 120, y - 2, rect.width - 120, 44), assets.COLOR_TEXTO_HUD,
                               assets.TAMANIO_FUENTE_NORMAL, negrita=True, interlineado=2)
        y += 44
    else:
        kit.rotulo(pantalla, "¿Qué vas a hacer?", (rect.left, y), assets.COLOR_TEXTO_SECUNDARIO)
        y += 22
    espacio = 14
    ancho = (rect.width - espacio * (len(opciones) - 1)) // len(opciones)
    alto = rect.bottom - y
    for i, nodo in enumerate(opciones):
        fila = pygame.Rect(rect.left + i * (ancho + espacio), y, ancho, alto)
        kit.opcion(pantalla, fila, nodo.etiqueta, nodo is terminal.hijo_seleccionado, tiempo, tamanio=assets.TAMANIO_FUENTE_MEDIA if en_raiz else assets.TAMANIO_FUENTE_NORMAL)


def _pregunta_de(etiqueta):
    return {"Reportar": "¿A quién o qué vas a reportar, y con qué?"}.get(etiqueta, "¿Cómo vas a hacerlo?")

