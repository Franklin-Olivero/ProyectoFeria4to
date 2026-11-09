"""Dibujo y ratón del modal de ajustes (solo presentación).

El estado (pestaña, foco, valores) es de ModalAjustes (src/ui/ajustes.py);
aquí solo se calcula el layout, se dibuja y se traduce el ratón a
llamadas del modal. `_layout()` lo usan el dibujo y el ratón, así cada
zona cliqueable coincide con lo que se ve.

Widgets:
    slider       -> barra de segmentos (violeta = activo), marca del valor y "70%"
    interruptor  -> píldora con perilla y el texto ACTIVADO / DESACTIVADO
    selector     -> ◄ valor ► con puntos que indican la posición
    segmentado   -> dos opciones visibles (TECLADO / RATÓN | MANDO)
"""

from types import SimpleNamespace

import pygame

from src.core import assets
from src.core.preferencias import ESQUEMA_MANDO, ESQUEMA_TECLADO, OPCIONES_TEXTO
from src.ui import combate_render, dibujo, guia_controles, sprites
from src.ui.ajustes import (
    BARRA_PESTANAS,
    CERRAR,
    INTERRUPTORES,
    PESTANA_ACCESIBILIDAD,
    PESTANA_AUDIO,
    PESTANA_CONTROLES,
    PESTANA_PARTIDA,
    SELECTORES,
    SLIDERS,
)
from src.ui.navegacion import CONFIRMAR, DERECHA, IZQUIERDA, SONIDO_CONFIRMAR, SONIDO_NAVEGAR

TITULO = "AJUSTES"
TEXTO_CERRAR = "CERRAR"
ETIQUETAS = {
    "volumen_general": "VOLUMEN GENERAL",
    "silencio": "SILENCIO (N)",
    "hud_detallado": "HUD DETALLADO",
    "instrucciones_mazmorra": "INSTRUCCIONES",
    "volumen_musica": "MÚSICA",
    "volumen_efectos": "EFECTOS DE SONIDO",
    "subtitulos": "SUBTÍTULOS",
    "filtro_daltonismo": "FILTRO DE DALTONISMO",
    "reducir_movimiento": "REDUCIR MOVIMIENTO",
    "alto_contraste": "ALTO CONTRASTE",
    "avance_cinematicas": "AVANCE DE ESCENAS",
    "velocidad_texto": "VELOCIDAD DEL TEXTO",
    "esquema_controles": "ESQUEMA",
    "mostrar_cono": "CONO DE DISPARO",
    "opacidad_cono": "OPACIDAD",
}
DESCRIPCIONES = {
    "subtitulos": "Las escenas ya se leen en pantalla; la opción queda guardada para futuras voces.",
    "avance_cinematicas": "Manual: tú decides cuándo seguir. Automático: respeta el tiempo de lectura.",
    "filtro_daltonismo": "Corrige el color de toda la pantalla. Es una aproximación: no reemplaza pruebas con jugadores.",
    "reducir_movimiento": "Detiene parallax, naves, lluvia, glitch del título, transiciones y sacudida de cámara.",
    "alto_contraste": "Realza el contraste de toda la imagen: fondos más oscuros y texto más brillante.",
}
# Cómo se lee en pantalla el valor guardado de un selector.
NOMBRES_OPCION = {"siempre": "Siempre", "primera_vez": "Solo tipos nuevos"}
NOMBRES_ESQUEMA = {ESQUEMA_TECLADO: "TECLADO / RATÓN", ESQUEMA_MANDO: "MANDO"}
MUESTRAS_COLOR = (
    ("Jugador", assets.COLOR_TEAL),
    ("Enemigo", assets.COLOR_MAGENTA),
    ("Colapso", assets.COLOR_AMARILLO),
    ("Jefe", assets.COLOR_MORADO),
)
NOTA_CONO = "Solo visual: no cambia la puntería, el alcance ni el daño."


class VistaAjustes:
    def __init__(self):
        self.arrastre = None  # campo del slider que se arrastra con el ratón
        self._layout = None  # el del último frame dibujado (lo usa el ratón)

    # --- Dibujo ----------------------------------------------------------

    def dibujar(self, pantalla, modal, audio, desfase, reducir_movimiento):
        layout = _layout(modal, pantalla.get_size(), desfase)
        self._layout = layout
        m = layout.modal
        dibujo.panel(pantalla, m, assets.COLOR_FONDO_MODAL, assets.COLOR_MENU_SELECCION, 2, radio=12)
        dibujo.panel(pantalla, m.inflate(-10, -10), None, assets.COLOR_BORDE_MODAL_INTERIOR, 1, radio=9)
        dibujo.corchetes(pantalla, m, assets.COLOR_CIAN_NEON, 16, 2, margen=-6)
        dibujo.texto(pantalla, TITULO, (m.left + 30, m.top + 36), assets.COLOR_MENU_SELECCION,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="midleft")
        self._dibujar_cerrar(pantalla, layout, modal.foco == CERRAR)
        self._dibujar_pestanas(pantalla, layout, modal)

        for campo, fila in layout.filas.items():
            self._dibujar_fila(pantalla, layout, modal, campo, fila)
        if modal.pestana in (PESTANA_AUDIO, PESTANA_PARTIDA):
            self._notas_audio(pantalla, layout, audio)
        elif modal.pestana == PESTANA_ACCESIBILIDAD:
            self._muestras_color(pantalla, layout.zonas["muestras"])
        elif modal.preferencias.esquema_controles == ESQUEMA_MANDO:
            _dibujar_mando(pantalla, layout.zonas["mando"])
            self._vista_previa_cono(pantalla, layout.zonas["vista_previa"], modal.preferencias)
        else:
            _dibujar_guia_teclado(pantalla, layout.zonas["guia"])

    def _dibujar_cerrar(self, pantalla, layout, enfocado):
        r = layout.cerrar
        borde = assets.COLOR_MENU_SELECCION if enfocado else assets.COLOR_BORDE_MENU
        dibujo.panel(pantalla, r, assets.COLOR_FILA_ENFOCADA if enfocado else assets.COLOR_FONDO_MODAL, borde,
                     2 if enfocado else 1, radio=6)
        texto = TEXTO_CERRAR if not enfocado else "[ " + TEXTO_CERRAR + " ]"
        dibujo.texto(pantalla, texto, (r.centerx - 14, r.centery), assets.COLOR_TEXTO_HUD if not enfocado
                     else assets.COLOR_MENU_SELECCION, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
        cx, cy = r.right - 18, r.centery
        for dx in (-5, 5):
            pygame.draw.line(pantalla, borde, (cx - 5, cy - dx), (cx + 5, cy + dx), 2)

    def _dibujar_pestanas(self, pantalla, layout, modal):
        enfocada = modal.foco == BARRA_PESTANAS
        for nombre, r in layout.pestanas.items():
            activa = nombre == modal.pestana
            if activa:
                dibujo.panel(pantalla, r, assets.COLOR_PESTANA_ACTIVA, None, radio=6)
                pygame.draw.rect(pantalla, assets.COLOR_MENU_SELECCION, (r.left, r.bottom - 3, r.width, 3))
                if enfocada:
                    dibujo.panel(pantalla, r.inflate(6, 6), None, assets.COLOR_MENU_SELECCION, 2, radio=8)
            color = assets.COLOR_TEXTO_HUD if activa else assets.COLOR_TEXTO_SECUNDARIO
            texto = f"[ {nombre} ]" if activa and enfocada else nombre
            dibujo.texto(pantalla, texto, r.center, color, assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="center")
        y = layout.contenido.top - 10
        pygame.draw.line(pantalla, assets.COLOR_BORDE_MENU, (layout.modal.left + 24, y), (layout.modal.right - 24, y))

    def _dibujar_fila(self, pantalla, layout, modal, campo, fila):
        enfocado = modal.foco == campo
        descripcion = DESCRIPCIONES.get(campo)
        y_etiqueta = fila.top + 18 if descripcion else fila.centery
        if enfocado:
            dibujo.panel(pantalla, fila, assets.COLOR_FILA_ENFOCADA, assets.COLOR_MENU_SELECCION, 2, radio=8)
            x, y = fila.left + 10, y_etiqueta
            pygame.draw.polygon(pantalla, assets.COLOR_MENU_SELECCION, [(x, y - 6), (x + 7, y), (x, y + 6)])
        dibujo.texto(pantalla, ETIQUETAS[campo], (fila.left + 26, y_etiqueta),
                     assets.COLOR_TEXTO_HUD if enfocado else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midleft")
        if descripcion:
            dibujo.texto(pantalla, descripcion, (fila.left + 26, fila.top + 46), assets.COLOR_TEXTO_APAGADO,
                         assets.TAMANIO_FUENTE_MINI, ancla="midleft")
        valor = modal.valor(campo)
        if campo in SLIDERS:
            _slider(pantalla, layout.pistas[campo], valor, enfocado, self.arrastre == campo)
        elif campo in INTERRUPTORES:
            _interruptor(pantalla, layout.interruptores[campo], valor, enfocado)
        elif campo == "esquema_controles":
            _segmentado(pantalla, {v: r for (c, v), r in layout.segmentos.items() if c == campo}, valor, enfocado)
        elif campo in SELECTORES:
            _selector(pantalla, layout.flechas[(campo, -1)], layout.flechas[(campo, 1)], valor,
                      OPCIONES_TEXTO[campo], enfocado)

    def _notas_audio(self, pantalla, layout, audio):
        zona = layout.zonas["notas"]
        notas = []
        if not audio.disponible:
            notas.append("No se detectó salida de audio: los volúmenes se guardan igual.")
        notas.append("Los cambios suenan al instante y se guardan solos. N silencia en cualquier momento.")
        y = zona.top
        for nota in notas:
            y = dibujo.parrafo(pantalla, nota, (zona.left + 26, y), zona.width - 52, assets.COLOR_TEXTO_APAGADO,
                               assets.TAMANIO_FUENTE_PEQUENA) + 6

    def _muestras_color(self, pantalla, zona):
        dibujo.texto(pantalla, "VISTA PREVIA DE COLORES DEL JUEGO", (zona.left + 26, zona.top),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
        ancho = (zona.width - 52 - 3 * 14) // len(MUESTRAS_COLOR)
        x = zona.left + 26
        for nombre, color in MUESTRAS_COLOR:
            muestra = pygame.Rect(x, zona.top + 24, ancho, 26)
            dibujo.panel(pantalla, muestra, color, assets.COLOR_TEXTO_HUD, 1, radio=4)
            dibujo.texto(pantalla, nombre, (muestra.centerx, muestra.bottom + 14), assets.COLOR_TEXTO_HUD,
                         assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
            x += ancho + 14

    def _vista_previa_cono(self, pantalla, zona, preferencias):
        dibujo.panel(pantalla, zona, assets.COLOR_FONDO_VISTA_PREVIA, assets.COLOR_BORDE_MENU, 1, radio=6)
        imagen = sprites.sprite_jugador(assets.COLOR_CIUDADANO, 2)
        centro = (zona.left + 34, zona.centery - 8)
        jugador = SimpleNamespace(rect=imagen.get_rect(center=centro), direccion_mirada=(1, 0))
        alfa = combate_render.alfa_cono(preferencias.opacidad_cono)
        if preferencias.mostrar_cono and alfa > 0:
            combate_render.dibujar_cono_apuntado(pantalla, jugador, assets.ANGULO_CONO_VISTA_PREVIA, alfa,
                                                 largo=zona.width - 60)
        else:
            dibujo.texto(pantalla, "CONO OCULTO", (zona.centerx + 20, zona.centery - 8),
                         assets.COLOR_TEXTO_DESHABILITADO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
        pantalla.blit(imagen, jugador.rect)
        dibujo.texto(pantalla, NOTA_CONO, (zona.centerx, zona.bottom - 14), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_MINI, ancla="center")

    # --- Ratón -------------------------------------------------------------

    def manejar_mouse(self, evento, modal):
        """Hover enfoca filas; clic en pestañas, CERRAR, sliders (y arrastre),
        flechas, opciones e interruptores. Retorna el sonido o None."""
        layout = self._layout
        if layout is None:
            return None
        if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            self.arrastre = None
            return None
        if evento.type == pygame.MOUSEMOTION:
            if self.arrastre in layout.pistas:
                modal.fijar(self.arrastre, _valor_en(layout.pistas[self.arrastre], evento.pos[0]))
                return None
            elemento = _elemento_en(layout, evento.pos)
            return SONIDO_NAVEGAR if elemento is not None and modal.enfocar(elemento) else None
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return None
        posicion = evento.pos
        if layout.cerrar.collidepoint(posicion):
            modal.enfocar(CERRAR)
            return modal.accion(CONFIRMAR)
        for nombre, r in layout.pestanas.items():
            if r.collidepoint(posicion):
                return SONIDO_NAVEGAR if modal.elegir_pestana(nombre) else None
        for campo, r in layout.pistas.items():
            if r.inflate(0, 16).collidepoint(posicion):
                modal.enfocar(campo)
                self.arrastre = campo
                modal.fijar(campo, _valor_en(r, posicion[0]))
                return SONIDO_NAVEGAR
        for (campo, paso), r in layout.flechas.items():
            if r.collidepoint(posicion):
                modal.enfocar(campo)
                return modal.accion(IZQUIERDA if paso < 0 else DERECHA)
        for (campo, valor), r in layout.segmentos.items():
            if r.collidepoint(posicion):
                modal.enfocar(campo)
                return SONIDO_CONFIRMAR if modal.fijar(campo, valor) else None
        elemento = _elemento_en(layout, posicion)
        if elemento in INTERRUPTORES or elemento in SELECTORES:
            modal.enfocar(elemento)
            return modal.accion(CONFIRMAR)
        return None


# --- Layout -------------------------------------------------------------------


def _layout(modal, tamanio, desfase=0):
    ancho, alto = tamanio
    # El modal crece si su pestaña tiene más filas de las que caben, sin
    # pisar la barra de controles de abajo.
    alto_modal = assets.TAMANIO_MODAL_AJUSTES[1]
    if modal.pestana != PESTANA_CONTROLES:
        filas = sum(assets.ALTO_FILA_AJUSTES + (10 if campo in DESCRIPCIONES else 0) + 8 for campo in modal.controles())
        alto_modal = max(alto_modal, 132 + filas + 10 + assets.ALTO_ZONA_INFERIOR_AJUSTES + 24)
    m = pygame.Rect(0, 0, assets.TAMANIO_MODAL_AJUSTES[0], alto_modal)
    m.center = (ancho // 2, round(alto * assets.CENTRO_Y_MODAL_AJUSTES) + desfase)
    limite = alto - assets.ALTO_BARRA_CONTROLES - 4 + desfase
    if m.bottom > limite:
        m.bottom = limite
    m.top = max(m.top, 4 + desfase)
    layout = SimpleNamespace(
        modal=m, filas={}, pistas={}, interruptores={}, flechas={}, segmentos={}, zonas={},
        cerrar=pygame.Rect(m.right - 24 - assets.ANCHO_BOTON_CERRAR, m.top + 18, assets.ANCHO_BOTON_CERRAR, 36),
        pestanas={},
    )
    x = m.left + 28
    for nombre in modal.pestanas:
        layout.pestanas[nombre] = pygame.Rect(x, m.top + 70, assets.ANCHO_PESTANA, 40)
        x += assets.ANCHO_PESTANA + 8
    contenido = pygame.Rect(m.left + 28, m.top + 132, m.width - 56, m.height - 132 - 24)
    layout.contenido = contenido

    paso = assets.ALTO_FILA_AJUSTES + 8
    if modal.pestana == PESTANA_CONTROLES:
        fila = pygame.Rect(contenido.left, contenido.top, contenido.width, assets.ALTO_FILA_AJUSTES)
        _registrar(layout, "esquema_controles", fila, assets.ANCHO_ETIQUETA_AJUSTES)
        resto = pygame.Rect(contenido.left, fila.bottom + 14, contenido.width, contenido.bottom - fila.bottom - 14)
        if modal.preferencias.esquema_controles == ESQUEMA_MANDO:
            layout.zonas["mando"] = pygame.Rect(resto.left, resto.top, assets.ANCHO_ZONA_MANDO, resto.height)
            columna = pygame.Rect(resto.left + assets.ANCHO_ZONA_MANDO + 16, resto.top,
                                  resto.width - assets.ANCHO_ZONA_MANDO - 16, resto.height)
            y = columna.top
            for campo in ("mostrar_cono", "opacidad_cono"):
                fila = pygame.Rect(columna.left, y, columna.width, assets.ALTO_FILA_AJUSTES)
                _registrar(layout, campo, fila, assets.ANCHO_ETIQUETA_COLUMNA)
                y += paso
            layout.zonas["vista_previa"] = pygame.Rect(columna.left, y + 4, columna.width, columna.bottom - y - 4)
        else:
            layout.zonas["guia"] = resto
        return layout

    y = contenido.top
    for campo in modal.controles():
        alto_fila = assets.ALTO_FILA_AJUSTES + (10 if campo in DESCRIPCIONES else 0)
        fila = pygame.Rect(contenido.left, y, contenido.width, alto_fila)
        _registrar(layout, campo, fila, assets.ANCHO_ETIQUETA_AJUSTES)
        y += alto_fila + 8
    resto = pygame.Rect(contenido.left, y + 10, contenido.width, contenido.bottom - y - 10)
    layout.zonas["notas" if modal.pestana in (PESTANA_AUDIO, PESTANA_PARTIDA) else "muestras"] = resto
    return layout


def _registrar(layout, campo, fila, ancho_etiqueta):
    """Guarda la fila y las zonas cliqueables de su widget. En las filas
    con descripción el widget va en la línea de la etiqueta y la
    descripción ocupa todo el ancho de abajo."""
    layout.filas[campo] = fila
    zona = pygame.Rect(fila.left + ancho_etiqueta, fila.top, fila.width - ancho_etiqueta - 16, fila.height)
    cy = fila.top + 18 if campo in DESCRIPCIONES else fila.centery
    if campo in SLIDERS:
        layout.pistas[campo] = pygame.Rect(zona.left, cy - 10, zona.width - 70, 20)
    elif campo in INTERRUPTORES:
        layout.interruptores[campo] = pygame.Rect(zona.left, cy - 14, 60, 28)
    elif campo == "esquema_controles":
        mitad = (zona.width - 10) // 2
        for i, valor in enumerate(OPCIONES_TEXTO[campo]):
            layout.segmentos[(campo, valor)] = pygame.Rect(zona.left + i * (mitad + 10), cy - 16, mitad, 32)
    elif campo in SELECTORES:
        layout.flechas[(campo, -1)] = pygame.Rect(zona.left, cy - 14, 28, 28)
        layout.flechas[(campo, 1)] = pygame.Rect(zona.right - 28, cy - 14, 28, 28)


def _elemento_en(layout, posicion):
    for campo, fila in layout.filas.items():
        if fila.collidepoint(posicion):
            return campo
    if layout.cerrar.collidepoint(posicion):
        return CERRAR
    return None


def _valor_en(pista, x):
    return (x - pista.left) / max(1, pista.width) * 100


# --- Widgets ----------------------------------------------------------------------


def _slider(pantalla, pista, valor, enfocado, arrastrando):
    segmentos = max(10, min(assets.SEGMENTOS_SLIDER, pista.width // 14))
    hueco = 3
    ancho = (pista.width - hueco * (segmentos - 1)) / segmentos
    activos = round(valor / 100 * segmentos)
    for i in range(segmentos):
        r = pygame.Rect(round(pista.left + i * (ancho + hueco)), pista.top, max(1, round(ancho)), pista.height)
        if i < activos:
            pygame.draw.rect(pantalla, assets.COLOR_SEGMENTO_ACTIVO, r)
            pygame.draw.rect(pantalla, assets.COLOR_SEGMENTO_LUZ, (r.left, r.top, r.width, r.height // 3))
        else:
            pygame.draw.rect(pantalla, assets.COLOR_SEGMENTO_INACTIVO, r)
    if enfocado:
        dibujo.panel(pantalla, pista.inflate(8, 8), None, assets.COLOR_CIAN_NEON, 1, radio=3)
    marca_x = pista.left + round(valor / 100 * pista.width)
    color_marca = assets.COLOR_CIAN_NEON if arrastrando else assets.COLOR_TEXTO_HUD
    grosor = 6 if arrastrando else 4
    pygame.draw.rect(pantalla, color_marca, (marca_x - grosor // 2, pista.top - 5, grosor, pista.height + 10))
    dibujo.texto(pantalla, f"{valor}%", (pista.right + 62, pista.centery), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="midright")


def _interruptor(pantalla, r, activo, enfocado):
    fondo = assets.COLOR_SEGMENTO_ACTIVO if activo else assets.COLOR_SEGMENTO_INACTIVO
    dibujo.panel(pantalla, r, fondo, assets.COLOR_CIAN_NEON if enfocado else assets.COLOR_BORDE_MENU, 1,
                 radio=r.height // 2)
    radio = r.height // 2 - 4
    cx = r.right - radio - 4 if activo else r.left + radio + 4
    pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, (cx, r.centery), radio)
    texto, color = ("ACTIVADO", assets.COLOR_MENU_SELECCION) if activo else ("DESACTIVADO", assets.COLOR_TEXTO_APAGADO)
    dibujo.texto(pantalla, texto, (r.right + 14, r.centery), color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True,
                 ancla="midleft")


def _selector(pantalla, izquierda, derecha, valor, opciones, enfocado):
    color = assets.COLOR_MENU_SELECCION if enfocado else assets.COLOR_TEXTO_SECUNDARIO
    for r, sentido in ((izquierda, -1), (derecha, 1)):
        cx, cy = r.center
        # La punta mira hacia afuera: ◄ a la izquierda, ► a la derecha.
        pygame.draw.polygon(pantalla, color, [(cx + 6 * sentido, cy), (cx - 5 * sentido, cy - 8),
                                              (cx - 5 * sentido, cy + 8)])
    centro_x = (izquierda.right + derecha.left) // 2
    dibujo.texto(pantalla, NOMBRES_OPCION.get(valor, valor), (centro_x, izquierda.centery - 4), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
    indice = opciones.index(valor)
    inicio = centro_x - (len(opciones) - 1) * 6
    for i in range(len(opciones)):
        punto = pygame.Rect(0, 0, 6, 6)
        punto.center = (inicio + i * 12, izquierda.centery + 14)
        pygame.draw.rect(pantalla, assets.COLOR_MENU_SELECCION if i == indice else assets.COLOR_SEGMENTO_INACTIVO,
                         punto)


def _segmentado(pantalla, rects, actual, enfocado):
    for valor, r in rects.items():
        elegido = valor == actual
        borde = assets.COLOR_CIAN_NEON if enfocado and elegido else assets.COLOR_BORDE_MENU
        dibujo.panel(pantalla, r, assets.COLOR_PESTANA_ACTIVA if elegido else assets.COLOR_FONDO_MODAL, borde,
                     2 if elegido else 1, radio=6)
        dibujo.texto(pantalla, NOMBRES_ESQUEMA[valor], r.center,
                     assets.COLOR_TEXTO_HUD if elegido else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")


# --- Guía de controles ---------------------------------------------------------


def _dibujar_guia_teclado(pantalla, zona):
    acciones = guia_controles.acciones_teclado()
    por_columna = (len(acciones) + 1) // 2
    ancho_columna = zona.width // 2
    for i, (accion, teclas, nota) in enumerate(acciones):
        columna, fila = divmod(i, por_columna)
        x = zona.left + 26 + columna * ancho_columna
        y = zona.top + 14 + fila * 36
        dibujo.texto(pantalla, accion, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                     ancla="midleft")
        x_tecla = x + 128
        for tecla in teclas:
            rect = dibujo.chip(pantalla, tecla, (x_tecla, y), ancla="midleft", alto=24)
            x_tecla = rect.right + 4
        if nota:
            dibujo.texto(pantalla, nota, (x_tecla + 4, y), assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MINI,
                         ancla="midleft")
    dibujo.texto(pantalla, guia_controles.NOTA_TECLADO, (zona.left + 26, zona.bottom - 12),
                 assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft")


def _dibujar_mando(pantalla, zona):
    """DualShock 4 estilizado con un rótulo por acción asignada."""
    cuerpo = pygame.Rect(0, 0, 232, 124)
    cuerpo.midtop = (zona.centerx, zona.top + 34)
    color, borde = assets.COLOR_CUERPO_MANDO, assets.COLOR_BORDE_MANDO
    # Gatillos y hombros (detrás del cuerpo).
    piezas = {
        "gatillo_izq": pygame.Rect(cuerpo.left + 24, cuerpo.top - 26, 46, 14),
        "hombro_izq": pygame.Rect(cuerpo.left + 18, cuerpo.top - 12, 56, 14),
        "gatillo_der": pygame.Rect(cuerpo.right - 70, cuerpo.top - 26, 46, 14),
        "hombro_der": pygame.Rect(cuerpo.right - 74, cuerpo.top - 12, 56, 14),
    }
    for r in piezas.values():
        dibujo.panel(pantalla, r, color, borde, 1, radio=5)
    for cx in (cuerpo.left + 34, cuerpo.right - 34):
        pygame.draw.circle(pantalla, color, (cx, cuerpo.bottom + 4), 32)
        pygame.draw.circle(pantalla, borde, (cx, cuerpo.bottom + 4), 32, 1)
    dibujo.panel(pantalla, cuerpo, color, borde, 1, radio=30)
    dibujo.panel(pantalla, (cuerpo.centerx - 38, cuerpo.top + 10, 76, 40), assets.COLOR_FONDO_MODAL, borde, 1, radio=5)

    puntos = {}
    cruceta = (cuerpo.left + 46, cuerpo.top + 50)
    for w, h in ((10, 30), (30, 10)):
        r = pygame.Rect(0, 0, w, h)
        r.center = cruceta
        pygame.draw.rect(pantalla, assets.COLOR_FONDO_MODAL, r)
    puntos["cruceta"] = cruceta
    centro_botones = (cuerpo.right - 46, cuerpo.top + 50)
    for simbolo, (dx, dy) in (("△", (0, -16)), ("○", (16, 0)), ("✕", (0, 16)), ("□", (-16, 0))):
        centro = (centro_botones[0] + dx, centro_botones[1] + dy)
        pygame.draw.circle(pantalla, assets.COLOR_FONDO_MODAL, centro, 8)
        _simbolo_ps(pantalla, simbolo, centro)
        if simbolo == "✕":
            puntos["cruz"] = centro
    for nombre, cx in (("stick_izq", cuerpo.centerx - 36), ("stick_der", cuerpo.centerx + 36)):
        centro = (cx, cuerpo.top + 92)
        pygame.draw.circle(pantalla, assets.COLOR_FONDO_MODAL, centro, 15)
        pygame.draw.circle(pantalla, borde, centro, 15, 1)
        puntos[nombre] = centro
    puntos["hombro_izq"] = piezas["hombro_izq"].midleft
    puntos["gatillo_der"] = piezas["gatillo_der"].midright

    # Rótulos: los del lado izquierdo del control a la izquierda y viceversa.
    lado_izquierdo = ("hombro_izq", "cruceta", "stick_izq")
    for elemento, (rotulo, accion) in guia_controles.acciones_mando().items():
        punto = puntos[elemento]
        izquierda = elemento in lado_izquierdo
        y = punto[1] if elemento not in ("stick_izq", "stick_der") else cuerpo.bottom + 18
        x = zona.left + 4 if izquierda else zona.right - 4
        ancla_linea = (x + 78, y) if izquierda else (x - 78, y)
        pygame.draw.line(pantalla, assets.COLOR_LINEA_GUIA_MANDO, punto, ancla_linea, 1)
        pygame.draw.circle(pantalla, assets.COLOR_CIAN_NEON, punto, 2)
        ancla = "topleft" if izquierda else "topright"
        dibujo.texto(pantalla, rotulo, (x, y - 14), assets.COLOR_CIAN_NEON, assets.TAMANIO_FUENTE_PEQUENA,
                     negrita=True, ancla=ancla)
        dibujo.texto(pantalla, accion, (x, y + 1), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, ancla=ancla)

    y = cuerpo.bottom + 52
    for nota in (guia_controles.NOTA_MANDO, guia_controles.NOTA_MENUS_MANDO):
        y = dibujo.parrafo(pantalla, nota, (zona.left + 4, y), zona.width - 8, assets.COLOR_TEXTO_APAGADO,
                           assets.TAMANIO_FUENTE_MINI) + 4


def _simbolo_ps(pantalla, simbolo, centro):
    """Símbolos de los botones frontales dibujados (no dependen de la fuente)."""
    x, y = centro
    color = assets.COLORES_BOTONES_PS[simbolo]
    if simbolo == "✕":
        pygame.draw.line(pantalla, color, (x - 4, y - 4), (x + 4, y + 4), 2)
        pygame.draw.line(pantalla, color, (x - 4, y + 4), (x + 4, y - 4), 2)
    elif simbolo == "○":
        pygame.draw.circle(pantalla, color, centro, 4, 2)
    elif simbolo == "□":
        pygame.draw.rect(pantalla, color, (x - 4, y - 4, 8, 8), 2)
    else:
        pygame.draw.polygon(pantalla, color, [(x, y - 5), (x + 5, y + 4), (x - 5, y + 4)], 2)
