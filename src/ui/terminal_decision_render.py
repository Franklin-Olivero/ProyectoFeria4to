"""Dibujo de la terminal de decisión como un celular (solo presentación).

El momento central de cada mazmorra se ve como dos capturas de la app
Civitas, la red social de Ciudad Nova:

    - a la izquierda, el perfil de quien publicó (cuenta, alcance, fuente y
      descripción) y debajo las pruebas reunidas como capturas de pantalla;
      las que faltan se ven como huecos con candado;
    - a la derecha, la publicación en el feed (texto, foto armada con la
      ilustración de la zona y contadores) y la fila de botones de la app:
      cada botón es una opción del nodo raíz del árbol N-ario. Al entrar a
      Verificar o Reportar, el 2.º nivel sale como una hoja inferior, igual
      que el menú de reportar de un celular;
    - al centro, la consola: título, reloj y el mismo árbol en lista, con el
      camino recorrido y la opción enfocada.

Regla de diseño: nada delata la respuesta. El foco es siempre violeta, los
botones no tienen colores de "bien o mal" y las hojas de resultado
(Purificación Exitosa / Detonación) nunca se dibujan. El árbol es el real
(src/structures/tree.py): botones, hoja inferior y lista leen el mismo
ArbolDecision que navega la TerminalDecision.

Funciona también con el árbol fijo (sin escenario de campaña): usa la
publicación PUBLICACION de este módulo y una foto genérica.

`dibujar_terminal` devuelve un DibujoTerminal con lo que dibujó (rects de
celulares, botones, hoja, filas y cada texto con su caja) para los tests de
layout: ningún texto se sale de su caja y nada importante cae bajo el
indicador del impostor (assets.RECT_INDICADOR_SABOTAJE) ni bajo la barra de
controles.
"""

import math
from dataclasses import dataclass, field

import pygame

from src.core import assets
from src.ui import celular_render as celular
from src.ui import dibujo, kit, layout, sprites
from src.ui.fuentes import fuente
from src.ui.terminal_decision import DETONACION, PURIFICACION_EXITOSA

TITULO = "Terminal Civitas"
SUBTITULO_POR_DEFECTO = "Decide qué hacer con esta publicación"

# Contenido fijo de la publicación (árbol fijo "Publicación Viral", sin campaña).
PUBLICACION = {
    "usuario": "@NoticiaReal_Ya",
    "hace": "hace 3 min",
    "texto": "URGENTE: filtran que las urnas del puesto 14 ya vienen marcadas. ¡Comparte antes de que lo borren!",
    "imagen": "[imagen sin fuente]",
    "etiqueta": "Sin fuente oficial",
    "compartidos": "12.4 mil compartidos",
    "comentarios": "3.1 mil comentarios",
    "fuente": {"tipo": "desconocida", "detalle": "Cuenta creada esta semana. No dice de dónde salió la foto."},
}

TEXTO_RELOJ = "Tiempo para decidir"
TEXTO_ARBOL = "Árbol de decisión"
TEXTO_PRUEBAS = "Pruebas reunidas · {reveladas} de {total}"
TEXTO_CAPTURAS = "Capturas"
TEXTO_SIN_CAPTURAS = "Aún no hay capturas de pruebas"
TEXTO_PRUEBA_NO_ENCONTRADA = "Prueba no encontrada"
TEXTO_EXIGE_MAS_PRUEBAS = "Por tu reputación, la ciudad ya no acepta pruebas parciales"
TEXTO_LO_QUE_ENCONTRASTE = "Lo que encontraste"
TEXTO_CONFIRMAR = "Confirmar"
TEXTO_PISTA = "NOVA_404"
PREGUNTAS = {"Reportar": "¿A quién o qué vas a reportar, y con qué?"}
PREGUNTA_GENERICA = "¿Cómo vas a hacerlo?"
PREGUNTA_CONFIRMAR = "Presiona Enter para confirmar tu elección."
ETIQUETAS_FUENTE = {"conocida": "Fuente conocida", "desconocida": "Fuente desconocida"}
ETIQUETA_FUENTE_GENERICA = "Publicación en Civitas"
HOJAS_RESULTADO = (PURIFICACION_EXITOSA, DETONACION)

# Clases de texto: lo narrativo nunca se recorta con "…" (docs/ART_DIRECTION.md).
NARRATIVA = "narrativa"
APOYO = "apoyo"

ALTO_HUECO_PRUEBA = 34
SEPARACION_CAPTURAS = 6


@dataclass
class TextoDibujado:
    clase: str  # NARRATIVA o APOYO
    cadena: str  # lo que se dibujó (con "…" si hubo que recortar)
    rect: pygame.Rect
    caja: pygame.Rect  # dónde tenía que caber


@dataclass
class DibujoTerminal:
    """Lo que dibujó dibujar_terminal (para tests de layout)."""

    celular_perfil: pygame.Rect
    celular_feed: pygame.Rect
    pantalla_perfil: pygame.Rect
    pantalla_feed: pygame.Rect
    consola: pygame.Rect
    fila_acciones: pygame.Rect = None
    acciones: list = field(default_factory=list)  # [(etiqueta, rect del botón)]
    hoja: pygame.Rect = None  # hoja inferior del 2.º nivel, si está abierta
    filas_hoja: list = field(default_factory=list)  # [(etiqueta, rect)]
    filas_arbol: list = field(default_factory=list)  # [(etiqueta, rect)]
    textos: list = field(default_factory=list)  # [TextoDibujado]
    importantes: list = field(default_factory=list)  # [(nombre, rect)]

    @property
    def etiquetas_dibujadas(self):
        return [texto.cadena for texto in self.textos]


def dibujar_terminal(pantalla, terminal, subtitulo="", post=None, estado_evidencia=None,
                     evidencias=None, total_evidencias=0, verificacion="", exige_mas_pruebas=False, tiempo=0.0,
                     nota_decisor="", zona=None):
    """`post`: publicación (modo historia; None = la fija PUBLICACION);
    `evidencias`: pruebas reveladas de la zona; `verificacion`: lo que
    descubre el jugador al elegir Verificar; `exige_mas_pruebas`: con
    reputación cuestionada, la ciudad ya no acepta pruebas parciales;
    `zona`: nombre de la zona ("Colegio", "Hospital", "Empresa de Medios")
    para que la foto use su ilustración (si falta, se deduce del subtítulo).
    `estado_evidencia` se acepta por compatibilidad: el sello de evidencia
    no se muestra porque delataría la respuesta. Retorna un DibujoTerminal."""
    post = post if post is not None else PUBLICACION
    zona = zona or zona_de_subtitulo(subtitulo)
    dibujado = DibujoTerminal(
        celular_perfil=pygame.Rect(assets.RECT_CELULAR_PERFIL),
        celular_feed=pygame.Rect(assets.RECT_CELULAR_FEED),
        pantalla_perfil=celular.rect_pantalla(assets.RECT_CELULAR_PERFIL),
        pantalla_feed=celular.rect_pantalla(assets.RECT_CELULAR_FEED),
        consola=pygame.Rect(assets.RECT_CONSOLA_TERMINAL),
    )
    pantalla.fill(assets.COLOR_FONDO_TERMINAL_CIVITAS)
    _fondo_terminal(pantalla)
    _dibujar_consola(dibujado, pantalla, terminal, subtitulo, nota_decisor, tiempo)
    _dibujar_perfil(dibujado, pantalla, terminal, post, evidencias or [], total_evidencias, exige_mas_pruebas)
    _dibujar_feed(dibujado, pantalla, terminal, post, zona, verificacion, tiempo)
    return dibujado


# ----------------------------------------------------------------------
# Funciones de apoyo (sin estado)
# ----------------------------------------------------------------------


def opciones_visibles(nodo):
    """Hijos que se dibujan como opciones: las hojas de resultado nunca."""
    return [hijo for hijo in nodo.hijos if hijo.etiqueta not in HOJAS_RESULTADO]


def zona_de_subtitulo(subtitulo):
    """"Colegio  ·  El rumor" -> "Colegio" (None si no empieza con una zona conocida)."""
    for zona in assets.FONDO_POR_ZONA:
        if str(subtitulo or "").startswith(zona):
            return zona
    return None


def tipo_de_imagen(descripcion):
    """Qué se dibuja encima de la foto según su descripción en el contenido:
    "documento" (un comunicado), "grafico", "foto" (con hora) o "generico"."""
    clave = celular.normalizar(descripcion)
    if "grafico" in clave:
        return "grafico"
    if "comunicado" in clave or "documento" in clave:
        return "documento"
    if "hora" in clave or "foto" in clave:
        return "foto"
    return "generico"


def color_reloj(restante):
    """Reloj discreto: presiona sin gritar. Solo se vuelve ámbar y rojo al final."""
    if restante <= assets.SEGUNDOS_RELOJ_GRAVE:
        return assets.COLOR_GRAVE
    if restante <= assets.SEGUNDOS_RELOJ_ALERTA:
        return assets.COLOR_ALERTA
    return assets.COLOR_TEXTO_HUD


def rects_acciones(fila, cantidad):
    """Un botón por opción en la fila de acciones del feed, todos del mismo
    ancho y centrados (con 2 o 3 opciones no se estiran)."""
    fila = pygame.Rect(fila)
    if cantidad <= 0:
        return []
    margen = 4
    ancho = min(assets.ANCHO_MAXIMO_BOTON_ACCION, (fila.width - 2 * margen) // cantidad)
    x0 = fila.centerx - ancho * cantidad // 2
    return [pygame.Rect(x0 + i * ancho + 1, fila.top + 5, ancho - 2, fila.height - 10) for i in range(cantidad)]


def separar_dato(texto):
    """"8.9 mil compartidos" -> ("8.9 mil", "compartidos")."""
    numero, _, etiqueta = str(texto or "").rpartition(" ")
    return (numero, etiqueta) if numero else (etiqueta, "")


# ----------------------------------------------------------------------
# Texto que siempre cabe (y queda registrado para los tests)
# ----------------------------------------------------------------------


def _ajustar_linea(cadena, ancho, tamanio, negrita, minimo):
    tamanio_actual = tamanio
    while tamanio_actual > minimo and fuente(tamanio_actual, negrita).size(cadena)[0] > ancho:
        tamanio_actual -= 1
    f = fuente(tamanio_actual, negrita)
    while len(cadena) > 1 and f.size(cadena)[0] > ancho:
        cadena = cadena[:-2].rstrip() + "…"
    return tamanio_actual, cadena


def _linea(dibujado, pantalla, cadena, caja, color, tamanio, negrita=False, ancla="topleft", posicion=None,
           clase=APOYO, minimo=None):
    """Una sola línea que nunca pasa del ancho de `caja`: baja de tamaño y
    luego recorta con "…". `posicion` por defecto: el punto `ancla` de la caja."""
    caja = pygame.Rect(caja)
    tamanio_final, texto = _ajustar_linea(str(cadena), caja.width, tamanio, negrita,
                                          minimo or assets.TAMANIO_FUENTE_CELULAR_MINIMA)
    rect = dibujo.texto(pantalla, texto, posicion if posicion is not None else getattr(caja, ancla), color,
                        tamanio_final, negrita, ancla)
    dibujado.textos.append(TextoDibujado(clase, texto, rect, caja))
    return rect


def _rotulo(dibujado, pantalla, cadena, caja, color, ancla="topleft", posicion=None):
    """Rótulo pequeño en mayúsculas (kit.rotulo) que no se sale de su caja."""
    return _linea(dibujado, pantalla, cadena.upper(), caja, color, assets.TAMANIO_FUENTE_PEQUENA, True, ancla, posicion)


def _alto_parrafo(cadena, ancho, tamanio, negrita=False, interlineado=2):
    lineas = dibujo.ajustar_texto(str(cadena), tamanio, ancho, negrita)
    return max(1, len(lineas)) * (fuente(tamanio, negrita).get_height() + interlineado) - interlineado


def _parrafo(dibujado, pantalla, cadena, caja, color, tamanio, negrita=False, interlineado=2, clase=NARRATIVA,
             minimo=None, centrado=False):
    """Párrafo con word wrap dentro de `caja`; si no cabe baja de tamaño y,
    como último recurso, recorta la última línea con "…". Retorna la y
    donde termina la última línea."""
    caja = pygame.Rect(caja)
    tamanio_final, lineas = layout.texto_que_cabe(str(cadena), caja.width, caja.height, tamanio, negrita, interlineado,
                                                  minimo or assets.TAMANIO_FUENTE_CELULAR_MINIMA)
    alto_linea = fuente(tamanio_final, negrita).get_height() + interlineado
    y = caja.top
    for linea in lineas:
        if centrado:
            rect = dibujo.texto(pantalla, linea, (caja.centerx, y), color, tamanio_final, negrita, ancla="midtop")
        else:
            rect = dibujo.texto(pantalla, linea, (caja.left, y), color, tamanio_final, negrita)
        dibujado.textos.append(TextoDibujado(clase, linea, rect, caja))
        y += alto_linea
    return y - interlineado


def _foco(pantalla, rect, tiempo, radio=10, latir=True):
    """El foco de todo el juego (kit.opcion): filo y fondo violeta con un
    latido leve. Sin latido marca la opción por la que se bajó."""
    rect = pygame.Rect(rect)
    if latir:
        latido = 0.5 + 0.5 * math.sin(tiempo * 4)
        crecer = round(4 + 3 * latido)
        pygame.draw.rect(pantalla, assets.COLOR_CIVITAS, rect.inflate(crecer, crecer), 1, border_radius=radio + 2)
        dibujo.panel(pantalla, rect, assets.COLOR_FOCO_FONDO, assets.COLOR_CIVITAS, 2, radio=radio)
    else:
        dibujo.panel(pantalla, rect, assets.COLOR_FOCO_FONDO, assets.COLOR_CIVITAS, 1, radio=radio)


def _fondo_terminal(pantalla):
    """Trama tenue de consola."""
    paso = 32
    ancho, alto = pantalla.get_size()
    for x in range(0, ancho, paso):
        pygame.draw.line(pantalla, assets.COLOR_TRAMA_TERMINAL_CIVITAS, (x, 0), (x, alto))
    for y in range(0, alto, paso):
        pygame.draw.line(pantalla, assets.COLOR_TRAMA_TERMINAL_CIVITAS, (0, y), (ancho, y))


def _barra_estado(pantalla, rect_pantalla, terminal):
    """La pila del celular se gasta con el reloj de la terminal."""
    fraccion = terminal.tiempo_restante / terminal.duracion if terminal.duracion else 0.0
    celular.dibujar_barra_estado(pantalla, rect_pantalla, fraccion, color_reloj(terminal.tiempo_restante))


# ----------------------------------------------------------------------
# Consola central: título, reloj y árbol
# ----------------------------------------------------------------------


def _dibujar_consola(dibujado, pantalla, terminal, subtitulo, nota_decisor, tiempo):
    consola = pygame.Rect(assets.RECT_CONSOLA_TERMINAL)
    x, y = consola.left, consola.top
    _rotulo(dibujado, pantalla, TITULO, pygame.Rect(x, y, consola.width, 18), assets.COLOR_CIVITAS)
    y += 20
    _linea(dibujado, pantalla, subtitulo or SUBTITULO_POR_DEFECTO, pygame.Rect(x, y, consola.width, 30),
           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True, minimo=assets.TAMANIO_FUENTE_NORMAL)
    y += 34
    encabezado = pygame.Rect(x, consola.top, consola.width, y - consola.top)
    if nota_decisor:
        _rotulo(dibujado, pantalla, nota_decisor, pygame.Rect(x, y, consola.width, 18), assets.COLOR_ALERTA)
        y += 22
        encabezado.height = y - consola.top
    dibujado.importantes.append(("encabezado", encabezado))

    reloj = pygame.Rect(x, y + 6, consola.width, 108)
    _dibujar_reloj(dibujado, pantalla, reloj, terminal)
    arbol = pygame.Rect(x, reloj.bottom + 12, consola.width, consola.bottom - reloj.bottom - 12)
    _dibujar_arbol(dibujado, pantalla, arbol, terminal, tiempo)


def _dibujar_reloj(dibujado, pantalla, rect, terminal):
    restante = terminal.tiempo_restante
    fraccion = restante / terminal.duracion if terminal.duracion else 0.0
    color = color_reloj(restante)
    kit.panel(pantalla, rect, color)
    _rotulo(dibujado, pantalla, TEXTO_RELOJ, pygame.Rect(rect.left + 20, rect.top + 12, rect.width - 40, 18),
            assets.COLOR_TEXTO_SECUNDARIO)
    # Número grande y la "s" sobre la misma línea base.
    caja = pygame.Rect(rect.left + 20, rect.top + 24, 200, fuente(assets.TAMANIO_FUENTE_ENORME, True).get_height())
    numero = _linea(dibujado, pantalla, f"{restante:0.0f}", caja, color, assets.TAMANIO_FUENTE_ENORME, negrita=True)
    base = caja.top + fuente(assets.TAMANIO_FUENTE_ENORME, True).get_ascent()
    unidad_y = base - fuente(assets.TAMANIO_FUENTE_TITULO, True).get_ascent()
    _linea(dibujado, pantalla, "s", pygame.Rect(numero.right + 6, caja.top, 40, caja.height), color,
           assets.TAMANIO_FUENTE_TITULO, negrita=True, posicion=(numero.right + 6, unidad_y))
    barra = pygame.Rect(rect.left + 20, rect.bottom - 18, rect.width - 40, 6)
    dibujo.barra(pantalla, barra, fraccion, color, assets.COLOR_FONDO_BARRA, None)
    dibujado.importantes.append(("reloj", rect))


def _filas_arbol(terminal):
    """[(nodo, nivel)] en orden de lista: la raíz, sus opciones y, debajo de
    cada opción del camino recorrido, sus propias opciones. Sin hojas de resultado."""
    en_camino = {id(nodo) for nodo in terminal.camino()}
    filas = []

    def agregar(nodo, nivel):
        filas.append((nodo, nivel))
        if nivel == 0 or id(nodo) in en_camino:
            for hijo in opciones_visibles(nodo):
                agregar(hijo, nivel + 1)

    agregar(terminal.arbol.raiz, 0)
    return filas, en_camino


def _dibujar_arbol(dibujado, pantalla, rect, terminal, tiempo):
    """El árbol N-ario real en forma de lista: raíz, opciones y el 2.º nivel
    de la opción por la que se bajó. Nunca muestra a qué resultado lleva una hoja."""
    kit.panel(pantalla, rect, assets.COLOR_CIVITAS)
    dibujado.importantes.append(("arbol", rect))
    _rotulo(dibujado, pantalla, TEXTO_ARBOL, pygame.Rect(rect.left + 20, rect.top + 14, rect.width - 40, 18),
            assets.COLOR_CIVITAS)
    filas, en_camino = _filas_arbol(terminal)
    arriba = rect.top + 42
    alto_fila = max(24, min(42, (rect.bottom - 12 - arriba) // max(1, len(filas))))
    sangria = 28
    seleccionado = terminal.hijo_seleccionado
    hay_foco = terminal.activa or terminal.resultado is None
    centros = {}  # id(nodo) -> (x del punto, y del centro de su fila)
    for indice, (nodo, nivel) in enumerate(filas):
        izquierda = rect.left + 20 + nivel * sangria
        fila = pygame.Rect(izquierda, arriba + indice * alto_fila, rect.right - 14 - izquierda, alto_fila - 6)
        punto = (izquierda + 10, fila.centery)
        centros[id(nodo)] = punto
        if nivel > 0:
            padre = _centro_padre(filas, indice, centros)
            activo = id(nodo) in en_camino
            color_rama = assets.COLOR_CIVITAS if activo else assets.COLOR_ARISTA_RED
            pygame.draw.line(pantalla, color_rama, (padre[0], padre[1] + 6), (padre[0], punto[1]), 2 if activo else 1)
            pygame.draw.line(pantalla, color_rama, (padre[0], punto[1]), (punto[0] - 6, punto[1]), 2 if activo else 1)
        enfocada = hay_foco and nodo is seleccionado
        en_ruta = id(nodo) in en_camino
        if enfocada:
            _foco(pantalla, fila, tiempo, radio=8)
        if nivel == 0 or en_ruta:
            pygame.draw.circle(pantalla, assets.COLOR_CIVITAS if en_ruta and nivel else assets.COLOR_TEXTO_HUD, punto, 5)
        else:
            pygame.draw.circle(pantalla, assets.COLOR_ARISTA_RED, punto, 4)
        texto_x = punto[0] + 14
        color = assets.COLOR_TEXTO_HUD if enfocada or en_ruta or nivel == 0 else assets.COLOR_TEXTO_SECUNDARIO
        if nivel == 1:
            celular.dibujar_icono(pantalla, celular.icono_para(nodo.etiqueta), (texto_x + 8, fila.centery), 16, color)
            texto_x += 24
        tamanio = assets.TAMANIO_FUENTE_NORMAL if nivel < 2 else assets.TAMANIO_FUENTE_PEQUENA
        _linea(dibujado, pantalla, nodo.etiqueta, pygame.Rect(texto_x, fila.top, fila.right - 10 - texto_x, fila.height),
               color, tamanio, negrita=nivel == 0 or enfocada, ancla="midleft", minimo=11)
        if nivel > 0:
            dibujado.filas_arbol.append((nodo.etiqueta, fila))


def _centro_padre(filas, indice, centros):
    """Punto del padre de filas[indice]: la fila anterior con un nivel menos."""
    nivel = filas[indice][1]
    for anterior in range(indice - 1, -1, -1):
        nodo, nivel_anterior = filas[anterior]
        if nivel_anterior == nivel - 1:
            return centros[id(nodo)]
    return centros[id(filas[0][0])]


# ----------------------------------------------------------------------
# Celular izquierdo: perfil de quien publicó y capturas de las pruebas
# ----------------------------------------------------------------------


def _dibujar_perfil(dibujado, pantalla, terminal, post, evidencias, total, exige_mas_pruebas):
    cuerpo = pygame.Rect(assets.RECT_CELULAR_PERFIL)
    s = celular.dibujar_celular(pantalla, cuerpo)
    dibujado.importantes.append(("celular_perfil", cuerpo))
    _barra_estado(pantalla, s, terminal)
    x, ancho = s.left + 16, s.width - 32
    y = s.top + assets.ALTO_BARRA_ESTADO_CELULAR

    # Barra de la app: la cuenta y los iconos de siempre.
    barra = pygame.Rect(s.left, y, s.width, assets.ALTO_BARRA_APP_CELULAR)
    cuenta = _linea(dibujado, pantalla, str(post.get("usuario", "")).lstrip("@"),
                    pygame.Rect(x, barra.top, ancho - 92, barra.height), assets.COLOR_TEXTO_HUD,
                    assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="midleft")
    celular.dibujar_icono(pantalla, "chevron_abajo", (cuenta.right + 12, barra.centery + 1), 14, assets.COLOR_TEXTO_HUD)
    celular.dibujar_icono(pantalla, "mas", (s.right - 58, barra.centery), 20, assets.COLOR_TEXTO_HUD)
    celular.dibujar_icono(pantalla, "menu", (s.right - 26, barra.centery), 20, assets.COLOR_TEXTO_HUD)
    y = barra.bottom + 4

    # Avatar, alcance (compartidos y comentarios) y chip de la fuente.
    radio = 30
    centro = (x + radio + 4, y + radio + 4)
    celular.avatar_iniciales(pantalla, centro, radio, post.get("usuario", ""))
    columna = centro[0] + radio + 18
    ancho_dato = (s.right - 14 - columna) // 2
    for i, clave in enumerate(("compartidos", "comentarios")):
        numero, etiqueta = separar_dato(post.get(clave, ""))
        izquierda = columna + i * ancho_dato
        _linea(dibujado, pantalla, numero, pygame.Rect(izquierda, y + 2, ancho_dato - 6, 22), assets.COLOR_TEXTO_HUD,
               assets.TAMANIO_FUENTE_NORMAL, negrita=True)
        _linea(dibujado, pantalla, etiqueta, pygame.Rect(izquierda, y + 22, ancho_dato - 6, 16),
               assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_CELULAR)
    fuente_post = post.get("fuente") or {}
    chip = pygame.Rect(columna, y + 44, s.right - 14 - columna, 22)
    dibujo.panel(pantalla, chip, assets.COLOR_FONDO_CHIP, assets.COLOR_BORDE_CHIP, 1, radio=11)
    celular.dibujar_icono(pantalla, "info", (chip.left + 13, chip.centery), 13, assets.COLOR_TEXTO_SECUNDARIO, 1)
    _linea(dibujado, pantalla, ETIQUETAS_FUENTE.get(fuente_post.get("tipo"), ETIQUETA_FUENTE_GENERICA),
           pygame.Rect(chip.left + 24, chip.top, chip.width - 32, chip.height), assets.COLOR_TEXTO_HUD,
           assets.TAMANIO_FUENTE_CELULAR, ancla="midleft")
    y = max(centro[1] + radio + 4, chip.bottom) + 10

    # Descripción de la cuenta: lo que se sabe de la fuente.
    detalle = fuente_post.get("detalle", "")
    if detalle:
        alto = _alto_parrafo(detalle, ancho, assets.TAMANIO_FUENTE_CELULAR)
        y = _parrafo(dibujado, pantalla, detalle, pygame.Rect(x, y, ancho, alto), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_CELULAR) + 10

    # Pestaña de capturas: las pruebas reunidas.
    evidencias = list(evidencias)
    total = max(total, len(evidencias))
    pestana = pygame.Rect(s.left, y, s.width, 30)
    celular.dibujar_icono(pantalla, "capturas", (x + 7, pestana.centery - 2), 16, assets.COLOR_VERIFICADO)
    titulo = TEXTO_PRUEBAS.format(reveladas=len(evidencias), total=total) if total else TEXTO_CAPTURAS
    rotulo = _rotulo(dibujado, pantalla, titulo, pygame.Rect(x + 20, pestana.top, ancho - 20, pestana.height - 4),
                     assets.COLOR_VERIFICADO, ancla="midleft", posicion=(x + 20, pestana.centery - 2))
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (s.left, pestana.bottom), (s.right - 1, pestana.bottom))
    pygame.draw.line(pantalla, assets.COLOR_VERIFICADO, (x - 2, pestana.bottom), (rotulo.right + 2, pestana.bottom), 2)
    y = pestana.bottom + 8

    if exige_mas_pruebas:
        y = _aviso_mas_pruebas(dibujado, pantalla, pygame.Rect(x, y, ancho, 0)) + 8
    area = pygame.Rect(x, y, ancho, s.bottom - 20 - y)
    _dibujar_capturas(dibujado, pantalla, area, evidencias, total)
    celular.indicador_inicio(pantalla, s)


def _aviso_mas_pruebas(dibujado, pantalla, rect):
    """Aviso ámbar: con reputación cuestionada no bastan las pruebas parciales."""
    ancho_texto = rect.width - 44
    alto_texto = _alto_parrafo(TEXTO_EXIGE_MAS_PRUEBAS, ancho_texto, assets.TAMANIO_FUENTE_CELULAR)
    aviso = pygame.Rect(rect.left, rect.top, rect.width, alto_texto + 14)
    dibujo.panel(pantalla, aviso, assets.COLOR_FONDO_PANEL, assets.COLOR_ALERTA, 1, radio=8)
    celular.dibujar_icono(pantalla, "alerta", (aviso.left + 18, aviso.centery), 18, assets.COLOR_ALERTA)
    _parrafo(dibujado, pantalla, TEXTO_EXIGE_MAS_PRUEBAS, pygame.Rect(aviso.left + 34, aviso.top + 7, ancho_texto, alto_texto),
             assets.COLOR_ALERTA, assets.TAMANIO_FUENTE_CELULAR)
    dibujado.importantes.append(("aviso_mas_pruebas", aviso))
    return aviso.bottom


def _alto_captura(evidencia, ancho, tamanio):
    interior = ancho - 20
    titulo = _alto_parrafo(evidencia["titulo"], interior, assets.TAMANIO_FUENTE_PEQUENA, True, 1)
    fragmento = _alto_parrafo(evidencia["fragmento"], interior, tamanio, False, 1)
    return 20 + 5 + titulo + 3 + fragmento + 8


def _dibujar_capturas(dibujado, pantalla, area, evidencias, total):
    """Cada prueba revelada como captura legible (fuente, título y
    fragmento); las que faltan como huecos con candado."""
    if total <= 0:
        celular.dibujar_icono(pantalla, "capturas", (area.centerx, area.top + 40), 30, assets.COLOR_TEXTO_APAGADO)
        _linea(dibujado, pantalla, TEXTO_SIN_CAPTURAS, pygame.Rect(area.left, area.top + 64, area.width, 18),
               assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_CELULAR, ancla="midtop")
        return
    huecos = total - len(evidencias)
    separacion = SEPARACION_CAPTURAS * (total - 1)
    # La letra más grande con la que caben todas (13 px si hay lugar, nunca menos de 10).
    for tamanio in range(assets.TAMANIO_FUENTE_PEQUENA, assets.TAMANIO_FUENTE_CELULAR_MINIMA - 1, -1):
        altos = [_alto_captura(ev, area.width, tamanio) for ev in evidencias] + [ALTO_HUECO_PRUEBA] * huecos
        if sum(altos) + separacion <= area.height:
            break
    else:
        # Ni con la letra mínima: se reparte el alto (el fragmento se recorta con "…").
        libre = area.height - separacion - ALTO_HUECO_PRUEBA * huecos
        altos = [max(48, libre // max(1, len(evidencias)))] * len(evidencias) + [ALTO_HUECO_PRUEBA] * huecos
    y = area.top
    for indice in range(total):
        rect = pygame.Rect(area.left, y, area.width, altos[indice])
        if indice < len(evidencias):
            _captura(dibujado, pantalla, rect, evidencias[indice], tamanio)
        else:
            _hueco(dibujado, pantalla, rect)
        dibujado.importantes.append(("captura", rect))
        y = rect.bottom + SEPARACION_CAPTURAS


def _captura(dibujado, pantalla, rect, evidencia, tamanio):
    """Una prueba como captura de pantalla: franja con la fuente, título y fragmento."""
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_EVIDENCIA, rect, border_radius=8)
    franja = pygame.Rect(rect.left, rect.top, rect.width, 20)
    pygame.draw.rect(pantalla, assets.COLOR_BARRA_CAPTURA, franja, border_top_left_radius=8, border_top_right_radius=8)
    derecha = franja.right - 10
    if evidencia.get("pista"):
        pista = _linea(dibujado, pantalla, TEXTO_PISTA, pygame.Rect(franja.right - 84, franja.top, 74, franja.height),
                       assets.COLOR_PISTA, assets.TAMANIO_FUENTE_MINI, negrita=True, ancla="midright")
        derecha = pista.left - 8
    pygame.draw.circle(pantalla, assets.COLOR_FUENTE_EVIDENCIA, (franja.left + 12, franja.centery), 4)
    _linea(dibujado, pantalla, evidencia["fuente"], pygame.Rect(franja.left + 22, franja.top, derecha - franja.left - 22,
                                                                franja.height),
           assets.COLOR_FUENTE_EVIDENCIA, assets.TAMANIO_FUENTE_CELULAR - 1, negrita=True, ancla="midleft")
    interior = pygame.Rect(rect.left + 10, franja.bottom + 5, rect.width - 20, rect.bottom - franja.bottom - 13)
    alto_titulo = _alto_parrafo(evidencia["titulo"], interior.width, assets.TAMANIO_FUENTE_PEQUENA, True, 1)
    y = _parrafo(dibujado, pantalla, evidencia["titulo"], pygame.Rect(interior.left, interior.top, interior.width,
                                                                      min(alto_titulo, interior.height)),
                 assets.COLOR_TITULO_EVIDENCIA, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, interlineado=1)
    caja = pygame.Rect(interior.left, y + 3, interior.width, interior.bottom - y - 3)
    if caja.height > 0:
        _parrafo(dibujado, pantalla, evidencia["fragmento"], caja, assets.COLOR_TITULO_EVIDENCIA, tamanio, interlineado=1)


def _hueco(dibujado, pantalla, rect):
    """Prueba que no se encontró: borde punteado, candado y aviso."""
    color = assets.COLOR_BORDE_VIDRIO
    for inicio, fin in ((rect.topleft, rect.topright), (rect.bottomleft, rect.bottomright),
                        (rect.topleft, rect.bottomleft), (rect.topright, rect.bottomright)):
        dibujo.linea_punteada(pantalla, color, inicio, fin, largo=5, hueco=4, grosor=1)
    celular.dibujar_icono(pantalla, "candado", (rect.left + 20, rect.centery), 16, assets.COLOR_TEXTO_APAGADO)
    _linea(dibujado, pantalla, TEXTO_PRUEBA_NO_ENCONTRADA, pygame.Rect(rect.left + 38, rect.top, rect.width - 48, rect.height),
           assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_CELULAR, ancla="midleft")


# ----------------------------------------------------------------------
# Celular derecho: la publicación en el feed y los botones de la app
# ----------------------------------------------------------------------


def _medidas_feed(s, post):
    """Posiciones del feed. Si el texto es largo primero baja a 12 px y
    después se saca la fila de historias, antes que achicar la foto."""
    arriba = s.top + assets.ALTO_BARRA_ESTADO_CELULAR + assets.ALTO_BARRA_APP_CELULAR
    abajo = s.bottom - 12 - assets.ALTO_NAV_CELULAR - 22 - assets.ALTO_FILA_ACCIONES
    ancho_texto = s.width - 28
    texto = post.get("texto", "")
    minimo_foto, maximo_foto = assets.ALTO_FOTO_POST
    opciones = [(True, assets.TAMANIO_FUENTE_PEQUENA), (True, assets.TAMANIO_FUENTE_CELULAR),
                (False, assets.TAMANIO_FUENTE_PEQUENA), (False, assets.TAMANIO_FUENTE_CELULAR)]
    for historias, tamanio in opciones:
        autor_top = arriba + (assets.ALTO_HISTORIAS_CELULAR if historias else 0)
        alto_texto = _alto_parrafo(texto, ancho_texto, tamanio, interlineado=3)
        libre = abajo - (autor_top + 46 + alto_texto + 10)
        if libre >= minimo_foto:
            break
    alto_foto = max(80, min(maximo_foto, libre))
    if libre < 80:  # texto larguísimo: se le recorta la caja (último recurso)
        alto_texto -= 80 - libre
    autor = pygame.Rect(s.left, autor_top, s.width, 46)
    caja_texto = pygame.Rect(s.left + 14, autor.bottom, ancho_texto, alto_texto)
    foto = pygame.Rect(s.left, caja_texto.bottom + 10, s.width, alto_foto)
    acciones = pygame.Rect(s.left, foto.bottom, s.width, assets.ALTO_FILA_ACCIONES)
    datos = pygame.Rect(s.left + 14, acciones.bottom, s.width - 28, 20)
    nav = pygame.Rect(s.left, s.bottom - 12 - assets.ALTO_NAV_CELULAR, s.width, assets.ALTO_NAV_CELULAR)
    return {"historias": historias, "autor": autor, "texto": (caja_texto, tamanio), "foto": foto, "acciones": acciones,
            "datos": datos, "nav": nav}


def _dibujar_feed(dibujado, pantalla, terminal, post, zona, verificacion, tiempo):
    cuerpo = pygame.Rect(assets.RECT_CELULAR_FEED)
    s = celular.dibujar_celular(pantalla, cuerpo)
    dibujado.importantes.append(("celular_feed", cuerpo))
    _barra_estado(pantalla, s, terminal)
    y = s.top + assets.ALTO_BARRA_ESTADO_CELULAR

    # Barra de la app: publicar, el logo de Civitas (el mismo pixel art del menú) y avisos.
    barra = pygame.Rect(s.left, y, s.width, assets.ALTO_BARRA_APP_CELULAR)
    celular.dibujar_icono(pantalla, "mas", (s.left + 26, barra.centery), 20, assets.COLOR_TEXTO_HUD)
    logo = sprites.sprite(*sprites.palabra_titulo(assets.COLOR_TITULO, assets.COLOR_TITULO_LUZ), escala=3)
    pantalla.blit(logo, logo.get_rect(center=barra.center))
    celular.dibujar_icono(pantalla, "campana", (s.right - 26, barra.centery), 20, assets.COLOR_TEXTO_HUD)
    pygame.draw.circle(pantalla, assets.COLOR_CIVITAS, (s.right - 19, barra.centery - 8), 4)

    medidas = _medidas_feed(s, post)
    if medidas["historias"]:
        _dibujar_historias(dibujado, pantalla, pygame.Rect(s.left, barra.bottom, s.width, assets.ALTO_HISTORIAS_CELULAR), s)
    autor = medidas["autor"]
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (s.left, autor.top), (s.right - 1, autor.top))
    _dibujar_autor(dibujado, pantalla, autor, post)
    caja_texto, tamanio = medidas["texto"]
    _parrafo(dibujado, pantalla, post.get("texto", ""), caja_texto, assets.COLOR_TEXTO_HUD, tamanio, interlineado=3)
    _dibujar_foto(dibujado, pantalla, medidas["foto"], post, zona)

    raiz = terminal.arbol.raiz
    en_raiz = terminal.nodo_actual is raiz
    camino = terminal.camino()
    elegida = camino[1] if len(camino) > 1 else None
    hay_foco = en_raiz and terminal.resultado is None
    _dibujar_acciones(dibujado, pantalla, medidas["acciones"], opciones_visibles(raiz),
                      terminal.hijo_seleccionado if hay_foco else None, elegida, tiempo)
    datos = " · ".join(dato for dato in (post.get("compartidos", ""), post.get("comentarios", "")) if dato)
    if datos:
        _linea(dibujado, pantalla, datos, medidas["datos"], assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_CELULAR,
               ancla="midleft")
    _dibujar_nav(pantalla, medidas["nav"])
    celular.indicador_inicio(pantalla, s)
    if not en_raiz and terminal.nodo_actual.hijos:
        _dibujar_hoja(dibujado, pantalla, s, terminal, verificacion, tiempo)


def _dibujar_historias(dibujado, pantalla, fila, s):
    """Fila de historias con los retratos que ya existen; la última asoma cortada."""
    diametro = assets.DIAMETRO_HISTORIA_CELULAR
    paso = diametro + 22
    recorte_anterior = pantalla.get_clip()
    pantalla.set_clip(s.clip(recorte_anterior) if recorte_anterior else s)
    for i, (rol, nombre, recorte) in enumerate(assets.HISTORIAS_CELULAR):
        centro = (s.left + 14 + paso // 2 + i * paso - 8, fila.top + 6 + diametro // 2)
        if centro[0] - diametro // 2 > s.right:
            break
        pygame.draw.circle(pantalla, assets.COLOR_CIVITAS, centro, diametro // 2 + 4, 2)
        cara = celular.retrato_redondo(rol, diametro, recorte)
        if cara is not None:
            pantalla.blit(cara, cara.get_rect(center=centro))
        else:
            celular.avatar_iniciales(pantalla, centro, diametro // 2, nombre, anillo=False)
        columna = pygame.Rect(centro[0] - paso // 2 + 2, fila.top + diametro + 12, paso - 4, 16)
        if s.contains(columna):
            _linea(dibujado, pantalla, nombre, columna, assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI,
                   ancla="midtop")
    pantalla.set_clip(recorte_anterior)


def _dibujar_autor(dibujado, pantalla, fila, post):
    centro = (fila.left + 32, fila.centery)
    celular.avatar_iniciales(pantalla, centro, 15, post.get("usuario", ""))
    x = centro[0] + 26
    ancho = fila.right - 44 - x
    _linea(dibujado, pantalla, post.get("usuario", ""), pygame.Rect(x, fila.top + 4, ancho, 20), assets.COLOR_TEXTO_HUD,
           assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="midleft")
    _linea(dibujado, pantalla, post.get("hace", ""), pygame.Rect(x, fila.top + 23, ancho, 18), assets.COLOR_TEXTO_SECUNDARIO,
           assets.TAMANIO_FUENTE_CELULAR, ancla="midleft")
    celular.dibujar_icono(pantalla, "puntos", (fila.right - 24, fila.centery), 20, assets.COLOR_TEXTO_HUD)


def _dibujar_acciones(dibujado, pantalla, fila, opciones, seleccionada, elegida, tiempo):
    """La fila de botones de la app: un botón por opción, con icono y nombre.
    Foco violeta en la enfocada; la opción por la que se bajó queda marcada sin latido."""
    dibujado.fila_acciones = fila
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (fila.left, fila.bottom - 1), (fila.right - 1, fila.bottom - 1))
    for nodo, boton in zip(opciones, rects_acciones(fila, len(opciones))):
        enfocada = nodo is seleccionada
        if enfocada:
            _foco(pantalla, boton, tiempo)
        elif nodo is elegida:
            _foco(pantalla, boton, tiempo, latir=False)
        color = assets.COLOR_TEXTO_HUD if enfocada or nodo is elegida else assets.COLOR_TEXTO_SECUNDARIO
        celular.dibujar_icono(pantalla, celular.icono_para(nodo.etiqueta), (boton.centerx, boton.top + 19),
                              assets.TAMANIO_ICONO_ACCION, color)
        _linea(dibujado, pantalla, nodo.etiqueta, pygame.Rect(boton.left + 2, boton.bottom - 22, boton.width - 4, 18), color,
               assets.TAMANIO_FUENTE_CELULAR, negrita=enfocada, ancla="midtop", posicion=(boton.centerx, boton.bottom - 21))
        dibujado.acciones.append((nodo.etiqueta, boton))
        dibujado.importantes.append(("accion", boton))


def _dibujar_nav(pantalla, nav):
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (nav.left, nav.top), (nav.right - 1, nav.top))
    iconos = ("inicio", "lupa", "mas", "videos", "perfil")
    paso = nav.width / len(iconos)
    for i, nombre in enumerate(iconos):
        color = assets.COLOR_TEXTO_HUD if i == 0 else assets.COLOR_TEXTO_SECUNDARIO
        celular.dibujar_icono(pantalla, nombre, (round(nav.left + paso * (i + 0.5)), nav.centery), 20, color)


# ----------------------------------------------------------------------
# La foto de la publicación: la ilustración de la zona + lo que dice la descripción
# ----------------------------------------------------------------------


def _dibujar_foto(dibujado, pantalla, rect, post, zona):
    nombre = assets.FONDO_POR_ZONA.get(zona) if zona else None
    nombre = nombre or assets.FONDO_POST_GENERICO
    pantalla.blit(celular.foto_recortada(nombre, assets.RECORTE_FOTO_POST.get(nombre), rect.size), rect.topleft)
    recorte_anterior = pantalla.get_clip()
    pantalla.set_clip(rect.clip(recorte_anterior) if recorte_anterior else rect)
    tipo = tipo_de_imagen(post.get("imagen", ""))
    if tipo == "documento":
        _foto_documento(dibujado, pantalla, rect)
    elif tipo == "grafico":
        _foto_grafico(dibujado, pantalla, rect)
    elif tipo == "foto":
        _foto_con_hora(dibujado, pantalla, rect)
    pantalla.set_clip(recorte_anterior)
    etiqueta = post.get("etiqueta", "")
    if etiqueta:
        _chip_foto(dibujado, pantalla, rect, etiqueta)
    descripcion = post.get("imagen", "")
    if descripcion:
        banda = pygame.Rect(rect.left, rect.bottom - 22, rect.width, 22)
        dibujo.panel_alfa(pantalla, banda, assets.COLOR_LEYENDA_FOTO, radio=0)
        _linea(dibujado, pantalla, descripcion, banda.inflate(-16, 0), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_CELULAR,
               ancla="center")
    dibujado.importantes.append(("foto", rect))


def _chip_foto(dibujado, pantalla, foto, etiqueta):
    """Etiqueta de la plataforma sobre la foto (como las de "contexto" de las redes)."""
    tamanio, texto = _ajustar_linea(etiqueta, foto.width - 56, assets.TAMANIO_FUENTE_CELULAR, False,
                                    assets.TAMANIO_FUENTE_CELULAR_MINIMA)
    chip = pygame.Rect(foto.left + 8, foto.top + 8, fuente(tamanio).size(texto)[0] + 34, 22)
    dibujo.panel_alfa(pantalla, chip, assets.COLOR_LEYENDA_FOTO, radio=11)
    celular.dibujar_icono(pantalla, "info", (chip.left + 13, chip.centery), 13, assets.COLOR_TEXTO_HUD, 1)
    _linea(dibujado, pantalla, etiqueta, pygame.Rect(chip.left + 24, chip.top, chip.width - 28, chip.height),
           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_CELULAR, ancla="midleft")


def _foto_documento(dibujado, pantalla, foto):
    """Captura recortada de un comunicado: papel con membrete y renglones
    que se sale por abajo, con las marcas de recorte."""
    documento = pygame.Rect(0, 0, round(foto.width * 0.48), foto.height)
    documento.topleft = (foto.left + round(foto.width * 0.44), foto.top + 42)  # bajo la etiqueta de la foto
    dibujo.panel_alfa(pantalla, documento.move(4, 4), (0, 0, 0, 110), radio=3)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_EVIDENCIA, documento, border_radius=3)
    membrete = pygame.Rect(documento.left, documento.top, documento.width, 18)
    pygame.draw.rect(pantalla, assets.COLOR_MEMBRETE_DOCUMENTO, membrete, border_top_left_radius=3, border_top_right_radius=3)
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_EVIDENCIA, (membrete.left + 10, membrete.centery), 4)
    _linea(dibujado, pantalla, "COMUNICADO", pygame.Rect(membrete.left + 20, membrete.top, membrete.width - 24, membrete.height),
           assets.COLOR_FONDO_EVIDENCIA, assets.TAMANIO_FUENTE_MINI, negrita=True, ancla="midleft")
    anchos = (0.86, 0.62, 0.92, 0.88, 0.7, 0.9, 0.84, 0.6, 0.9, 0.78, 0.86, 0.66)
    for i, fraccion in enumerate(anchos):
        renglon = pygame.Rect(documento.left + 10, membrete.bottom + 8 + i * 10, round((documento.width - 20) * fraccion),
                              6 if i == 1 else 4)
        pygame.draw.rect(pantalla, assets.COLOR_TITULO_EVIDENCIA if i == 1 else assets.COLOR_LINEA_DOCUMENTO, renglon)
    dibujo.corchetes(pantalla, documento, assets.COLOR_TEXTO_HUD, 10, 2, margen=5)


def _foto_con_hora(dibujado, pantalla, foto):
    """Foto de cámara: visor en las esquinas y la hora impresa abajo a la derecha."""
    visor = pygame.Rect(foto.left + 14, foto.top + 38, foto.width - 28, foto.height - 38 - 30)
    dibujo.corchetes(pantalla, visor, assets.COLOR_TEXTO_HUD, 12, 2)
    posicion = (visor.right - 6, visor.bottom - 4)
    dibujo.texto(pantalla, assets.HORA_FOTO_POST, (posicion[0] + 1, posicion[1] + 1), assets.COLOR_NOCHE,
                 assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="bottomright")
    _linea(dibujado, pantalla, assets.HORA_FOTO_POST, pygame.Rect(visor.left, visor.top, visor.width - 6, visor.height - 4),
           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="bottomright", posicion=posicion)


def _foto_grafico(dibujado, pantalla, foto):
    """Gráfico de barras sin ficha técnica: una barra enorme con su porcentaje."""
    tarjeta = pygame.Rect(0, 0, round(foto.width * 0.58), round(foto.height * 0.66))
    tarjeta.center = (foto.centerx + 34, foto.centery + 4)
    dibujo.panel_alfa(pantalla, tarjeta, assets.COLOR_PANEL_GRAFICO, radio=6)
    pygame.draw.rect(pantalla, assets.COLOR_TEXTO_SECUNDARIO, (tarjeta.left + 10, tarjeta.top + 9, 12, 12), border_radius=3)
    pygame.draw.rect(pantalla, assets.COLOR_LINEA_DOCUMENTO, (tarjeta.left + 28, tarjeta.top + 12, tarjeta.width // 2, 5))
    base = tarjeta.bottom - 12
    alto_maximo = tarjeta.height - 56
    ancho_columna = (tarjeta.width - 30) // 4
    for i, (fraccion, color) in enumerate(zip((1.0, 0.42, 0.3, 0.2), assets.COLORES_CANDIDATOS)):
        alto = max(4, round(alto_maximo * fraccion))
        barra = pygame.Rect(tarjeta.left + 15 + i * ancho_columna + 6, base - alto, ancho_columna - 12, alto)
        pygame.draw.rect(pantalla, color, barra)
        if i == 0:
            _linea(dibujado, pantalla, "61 %", pygame.Rect(barra.left - 12, barra.top - 20, barra.width + 24, 18),
                   assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_CELULAR, negrita=True, ancla="midbottom",
                   posicion=(barra.centerx, barra.top - 3))
    pygame.draw.line(pantalla, assets.COLOR_TEXTO_SECUNDARIO, (tarjeta.left + 12, base), (tarjeta.right - 12, base))


# ----------------------------------------------------------------------
# Hoja inferior: el 2.º nivel del árbol (Verificar, Reportar...)
# ----------------------------------------------------------------------


def _dibujar_hoja(dibujado, pantalla, s, terminal, verificacion, tiempo):
    """Menú que sube desde abajo, como el de reportar de un celular: título,
    lo que encontró el jugador (en Verificar) o la pregunta, y una fila por opción."""
    nodo = terminal.nodo_actual
    opciones = opciones_visibles(nodo)
    celular.velo_pantalla(pantalla, s, assets.COLOR_VELO_OVERLAY)
    ancho_texto = s.width - 40
    es_verificacion = nodo.etiqueta == "Verificar" and bool(verificacion)
    if es_verificacion:
        texto = verificacion
    elif opciones:
        texto = PREGUNTAS.get(nodo.etiqueta, PREGUNTA_GENERICA)
    else:
        texto = PREGUNTA_CONFIRMAR
    # Sin opciones visibles (árbol fijo: solo queda la hoja de resultado) se confirma
    # con una fila genérica: el resultado no se escribe.
    filas = [(hijo, hijo.etiqueta) for hijo in opciones] or [(terminal.hijo_seleccionado, TEXTO_CONFIRMAR)]
    ancho_fila = s.width - 20
    altos_filas = [_alto_parrafo(etiqueta, ancho_fila - 48, assets.TAMANIO_FUENTE_PEQUENA, True) + 24 for _, etiqueta in filas]
    alto_texto = _alto_parrafo(texto, ancho_texto, assets.TAMANIO_FUENTE_PEQUENA, interlineado=3)
    alto = 46 + (22 if es_verificacion else 0) + alto_texto + 14 + sum(altos_filas) + 6 * len(filas) + 26
    alto = min(alto, s.height - 160)
    hoja = pygame.Rect(s.left, s.bottom - alto, s.width, alto)
    radio_abajo = assets.RADIO_CELULAR - assets.GROSOR_MARCO_CELULAR
    pygame.draw.rect(pantalla, assets.COLOR_HOJA_CELULAR, hoja, border_top_left_radius=18, border_top_right_radius=18,
                     border_bottom_left_radius=radio_abajo, border_bottom_right_radius=radio_abajo)
    pygame.draw.rect(pantalla, assets.COLOR_BORDE_VIDRIO, hoja, 1, border_top_left_radius=18, border_top_right_radius=18,
                     border_bottom_left_radius=radio_abajo, border_bottom_right_radius=radio_abajo)
    agarre = pygame.Rect(0, 0, 40, 4)
    agarre.midtop = (hoja.centerx, hoja.top + 8)
    pygame.draw.rect(pantalla, assets.COLOR_TEXTO_APAGADO, agarre, border_radius=2)
    dibujado.hoja = hoja
    dibujado.importantes.append(("hoja", hoja))

    # Título: el icono y el nombre de la opción por la que se bajó.
    titulo_y = hoja.top + 28
    f = fuente(assets.TAMANIO_FUENTE_NORMAL, True)
    ancho_titulo = min(f.size(nodo.etiqueta)[0], hoja.width - 80) + 24
    izquierda = hoja.centerx - ancho_titulo // 2
    celular.dibujar_icono(pantalla, celular.icono_para(nodo.etiqueta), (izquierda + 8, titulo_y), 16, assets.COLOR_TEXTO_HUD)
    _linea(dibujado, pantalla, nodo.etiqueta, pygame.Rect(izquierda + 24, titulo_y - 11, ancho_titulo - 24, 22),
           assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midleft")
    y = hoja.top + 46
    pygame.draw.line(pantalla, assets.COLOR_SEPARADOR_CELULAR, (hoja.left + 1, y - 4), (hoja.right - 2, y - 4))
    if es_verificacion:
        _rotulo(dibujado, pantalla, TEXTO_LO_QUE_ENCONTRASTE, pygame.Rect(hoja.left + 20, y + 2, ancho_texto, 18),
                assets.COLOR_VERIFICADO)
        y += 22
    y = _parrafo(dibujado, pantalla, texto, pygame.Rect(hoja.left + 20, y + 2, ancho_texto, min(alto_texto, hoja.bottom - y - 30)),
                 assets.COLOR_TEXTO_HUD if es_verificacion else assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                 interlineado=3) + 14

    seleccionado = terminal.hijo_seleccionado
    for (hijo, etiqueta), alto_fila in zip(filas, altos_filas):
        fila = pygame.Rect(hoja.left + 10, y, ancho_fila, alto_fila)
        if fila.bottom > hoja.bottom - 20:
            break
        enfocada = hijo is seleccionado and hijo is not None
        if enfocada:
            _foco(pantalla, fila, tiempo, radio=10)
        else:
            dibujo.panel(pantalla, fila, assets.COLOR_OPCION_FONDO, assets.COLOR_BORDE_VIDRIO, 1, radio=10)
        color = assets.COLOR_TEXTO_HUD if enfocada else assets.COLOR_TEXTO_SECUNDARIO
        _parrafo(dibujado, pantalla, etiqueta, pygame.Rect(fila.left + 14, fila.top + 12, fila.width - 48, fila.height - 24),
                 color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
        celular.dibujar_icono(pantalla, "chevron_derecha", (fila.right - 18, fila.centery), 16, color)
        dibujado.filas_hoja.append((etiqueta, fila))
        y = fila.bottom + 6
    celular.indicador_inicio(pantalla, s)
