"""Dibujo y ratón del menú principal (solo presentación).

`VistaMenu` guarda solo estado visual (animaciones de realce, giro del
engranaje, apertura del modal y el slider que se arrastra con el ratón);
todo lo que el jugador elige vive en MenuPrincipal / ModalAjustes. El
layout se calcula en funciones que usan tanto el dibujo como el ratón,
así lo que se ve es exactamente lo que se puede cliquear.

Estados de cada opción (no solo por color):
    normal        -> texto claro
    seleccionada  -> "[ J U G A R ]" en violeta, con resplandor y entrada deslizante
    pulsada       -> fondo violeta lleno durante DURACION_PULSADO_MENU
    deshabilitada -> texto apagado y la razón debajo ("SIN PARTIDA EN CURSO")
"""

import math

import pygame

from src.core import assets
from src.ui import ajustes_render, dibujo, hud, sprites
from src.ui.fondo_ciudad import FondoCiudad
from src.ui.fuentes import fuente
from src.ui.menu_principal import (
    CONTINUAR,
    ENGRANAJE,
    LINEAS_CREDITOS,
    OPCIONES,
    TEXTO_EXTRAS,
    TEXTO_SIN_PARTIDA,
    VISTA_CREDITOS,
    VISTA_EXTRAS,
    VISTA_MENU,
)
from src.ui.navegacion import CONFIRMAR, SONIDO_NAVEGAR
from src.ui.titulo_civitas import TituloCivitas

SUBTITULO = "UNA CIUDAD AL BORDE DEL COLAPSO"
TITULOS_VISTA = {VISTA_EXTRAS: "EXTRAS", VISTA_CREDITOS: "CRÉDITOS"}
ETIQUETA_ENGRANAJE = "AJUSTES"
TEXTO_VOLVER = "VOLVER"
TEXTO_VER_INTRO = "VER INTRODUCCIÓN"


def espaciado(texto):
    """'JUGAR' -> '[ J U G A R ]' (opción seleccionada)."""
    return "[ " + " ".join(texto) + " ]"


def rects_menu(tamanio):
    """{opción o ENGRANAJE: Rect} en coordenadas de pantalla."""
    ancho, alto = tamanio
    rects = {}
    y = round(alto * assets.INICIO_OPCIONES_MENU)
    for opcion in OPCIONES:
        rects[opcion] = pygame.Rect(0, 0, assets.ANCHO_OPCION_MENU, assets.ALTO_OPCION_MENU)
        rects[opcion].center = (ancho // 2, y)
        y += assets.PASO_OPCIONES_MENU
    lado = assets.LADO_BOTON_ENGRANAJE
    margen = assets.MARGEN_BOTON_ENGRANAJE
    rects[ENGRANAJE] = pygame.Rect(ancho - margen - lado, margen, lado, lado)
    return rects


def rect_panel_vista(tamanio):
    """Panel de EXTRAS / CRÉDITOS."""
    rect = pygame.Rect(0, 0, *assets.TAMANIO_PANEL_VISTA)
    rect.center = (tamanio[0] // 2, round(tamanio[1] * assets.CENTRO_Y_PANEL_VISTA))
    return rect


def rect_boton_volver(tamanio):
    panel = rect_panel_vista(tamanio)
    rect = pygame.Rect(0, 0, assets.ANCHO_OPCION_MENU, assets.ALTO_OPCION_MENU)
    rect.midbottom = (panel.centerx, panel.bottom - 20)
    return rect


class VistaMenu:
    def __init__(self, tamanio, fondo=None):
        self.tamanio = tamanio
        self.fondo = fondo or FondoCiudad(tamanio)
        self.titulo = TituloCivitas()
        self.realce = {elemento: 0.0 for elemento in (*OPCIONES, ENGRANAJE)}
        self.angulo_engranaje = 0.0
        self.apertura = 0.0  # 0 = modal cerrado, 1 = abierto (transición)
        self._modal = None  # último modal abierto: se sigue dibujando mientras se cierra
        self.tiempo = 0.0
        self.ajustes = ajustes_render.VistaAjustes()

    @property
    def arrastrando(self):
        return self.ajustes.arrastre is not None

    def actualizar(self, dt, menu, reducir_movimiento):
        self.tiempo += dt
        self.fondo.actualizar(dt, reducir_movimiento)
        self.titulo.actualizar(dt, reducir_movimiento)
        for elemento in self.realce:
            objetivo = 1.0 if elemento == menu.foco else 0.0
            if reducir_movimiento:
                self.realce[elemento] = objetivo
            else:
                paso = dt / assets.DURACION_REALCE_MENU
                actual = self.realce[elemento]
                self.realce[elemento] = min(objetivo, actual + paso) if objetivo > actual else max(objetivo, actual - paso)
        if menu.foco == ENGRANAJE and menu.ajustes is None and not reducir_movimiento:
            self.angulo_engranaje = (self.angulo_engranaje + assets.GIRO_ENGRANAJE * dt) % 360
        elif menu.foco != ENGRANAJE:
            self.angulo_engranaje = 0.0  # sin foco, el pixel art queda derecho
        # Apertura del modal: sube al abrir, baja al cerrar.
        if menu.ajustes is not None:
            self._modal = menu.ajustes
        objetivo = 1.0 if menu.ajustes is not None else 0.0
        if reducir_movimiento:
            self.apertura = objetivo
        else:
            paso = dt / assets.DURACION_TRANSICION_MODAL
            self.apertura = min(objetivo, self.apertura + paso) if objetivo > self.apertura else max(objetivo, self.apertura - paso)
        if self.apertura == 0:
            self._modal = None
            self.ajustes.arrastre = None

    # --- Dibujo ----------------------------------------------------------

    def dibujar(self, pantalla, menu, audio, reducir_movimiento):
        self.fondo.dibujar(pantalla, reducir_movimiento)
        ancho, alto = self.tamanio
        centro_titulo = (ancho // 2, round(alto * assets.CENTRO_Y_TITULO))
        rect_titulo = self.titulo.dibujar(pantalla, centro_titulo)
        dibujo.texto(pantalla, SUBTITULO, (ancho // 2, rect_titulo.bottom + 18), assets.COLOR_CIAN_NEON,
                     assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="center")

        if menu.vista == VISTA_MENU:
            self._dibujar_opciones(pantalla, menu)
        else:
            self._dibujar_vista(pantalla, menu.vista)
        self._dibujar_engranaje(pantalla, menu)

        if self._modal is not None and self.apertura > 0:
            _difuminar_y_oscurecer(pantalla, self.apertura)
            suavizada = 1 - (1 - self.apertura) ** 3
            desfase = round((1 - suavizada) * assets.DESPLAZAMIENTO_ENTRADA_MODAL)
            self.ajustes.dibujar(pantalla, self._modal, audio, desfase, reducir_movimiento)
            controles = hud.CONTROLES_AJUSTES
        elif menu.vista != VISTA_MENU:
            controles = hud.CONTROLES_VISTA_MENU
        else:
            controles = hud.CONTROLES_MENU_PRINCIPAL
        hud.dibujar_barra_controles(pantalla, controles)

    def _dibujar_opciones(self, pantalla, menu):
        rects = rects_menu(self.tamanio)
        primero, ultimo = rects[OPCIONES[0]], rects[OPCIONES[-1]]
        fondo = pygame.Rect(primero.left - 40, primero.top - 22, primero.width + 80,
                            ultimo.bottom - primero.top + 44)
        dibujo.panel_alfa(pantalla, fondo, assets.COLOR_FONDO_MENU, radio=12)
        dibujo.panel(pantalla, fondo, None, assets.COLOR_BORDE_MENU, 1, radio=12)
        for opcion in OPCIONES:
            self._dibujar_opcion(pantalla, rects[opcion], opcion, menu)

    def _dibujar_opcion(self, pantalla, rect, opcion, menu):
        tamanio = assets.TAMANIO_FUENTE_MENU
        if not menu.habilitada(opcion):
            dibujo.texto(pantalla, opcion, (rect.centerx, rect.centery - 6), assets.COLOR_TEXTO_DESHABILITADO,
                         tamanio, negrita=True, ancla="center")
            dibujo.texto(pantalla, TEXTO_SIN_PARTIDA, (rect.centerx, rect.centery + 15),
                         assets.COLOR_TEXTO_DESHABILITADO, assets.TAMANIO_FUENTE_MINI, ancla="center")
            return
        if menu.pulsado == opcion:
            dibujo.panel(pantalla, rect, assets.COLOR_MENU_PULSADO, assets.COLOR_MENU_SELECCION, 2, radio=8)
            dibujo.texto(pantalla, espaciado(opcion), rect.center, assets.COLOR_TEXTO_PULSADO, tamanio,
                         negrita=True, ancla="center")
            return
        realce = self.realce[opcion]
        if realce > 0.02 and menu.foco == opcion:
            # Entra deslizándose desde la izquierda mientras sube el realce.
            x = rect.centerx - round((1 - realce) * assets.DESLIZAMIENTO_OPCION_MENU)
            texto = espaciado(opcion)
            brillo = _brillo_texto(texto, tamanio)
            pulso = 1.0 if menu.ajustes is not None else 0.85 + 0.15 * math.sin(self.tiempo * assets.PULSO_OPCION_MENU)
            brillo.set_alpha(round(255 * realce * pulso))
            pantalla.blit(brillo, brillo.get_rect(center=(x, rect.centery)))
            color = _mezclar(assets.COLOR_TEXTO_HUD, assets.COLOR_MENU_SELECCION, realce)
            dibujo.texto(pantalla, texto, (x, rect.centery), color, tamanio, negrita=True, ancla="center")
        else:
            dibujo.texto(pantalla, opcion, rect.center, assets.COLOR_TEXTO_HUD, tamanio, negrita=True, ancla="center")

    def _dibujar_engranaje(self, pantalla, menu):
        rect = rects_menu(self.tamanio)[ENGRANAJE]
        enfocado = menu.foco == ENGRANAJE and menu.vista == VISTA_MENU
        realce = self.realce[ENGRANAJE] if enfocado else 0.0
        if menu.pulsado == ENGRANAJE:
            color = assets.COLOR_TEXTO_PULSADO
            dibujo.panel(pantalla, rect, assets.COLOR_MENU_PULSADO, assets.COLOR_MENU_SELECCION, 2, radio=10)
        else:
            color = _mezclar(assets.COLOR_ENGRANAJE, assets.COLOR_MENU_SELECCION, realce)
            dibujo.panel_alfa(pantalla, rect, assets.COLOR_FONDO_MENU, radio=10)
            dibujo.panel(pantalla, rect, None, color if realce > 0.5 else assets.COLOR_BORDE_MENU,
                         2 if realce > 0.5 else 1, radio=10)
        if realce > 0.02:
            halo = _halo(rect.width // 2 + 8, assets.COLOR_MENU_SELECCION)
            halo.set_alpha(round(200 * realce))
            pantalla.blit(halo, halo.get_rect(center=rect.center))
        icono = sprites.sprite(sprites.ENGRANAJE, {"c": color}, assets.ESCALA_ENGRANAJE)
        if self.angulo_engranaje:
            icono = pygame.transform.rotate(icono, self.angulo_engranaje)
        pantalla.blit(icono, icono.get_rect(center=rect.center))
        # Etiqueta textual: el botón no depende solo del icono.
        if enfocado or menu.pulsado == ENGRANAJE:
            dibujo.texto(pantalla, ETIQUETA_ENGRANAJE, (rect.left - 12, rect.centery), assets.COLOR_MENU_SELECCION,
                         assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midright")

    def _dibujar_vista(self, pantalla, vista):
        panel = rect_panel_vista(self.tamanio)
        dibujo.panel_alfa(pantalla, panel, assets.COLOR_FONDO_MODAL_ALFA, radio=12)
        dibujo.panel(pantalla, panel, None, assets.COLOR_MENU_SELECCION, 2, radio=12)
        dibujo.texto(pantalla, TITULOS_VISTA[vista], (panel.centerx, panel.top + 34), assets.COLOR_MENU_SELECCION,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        y = panel.top + 82
        if vista == VISTA_EXTRAS:
            dibujo.texto(pantalla, "CINEMÁTICA DE INTRODUCCIÓN", (panel.centerx, y), assets.COLOR_CIAN_NEON,
                         assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
            y += 44
            for linea in TEXTO_EXTRAS:
                dibujo.texto(pantalla, linea, (panel.centerx, y), assets.COLOR_TEXTO_SECUNDARIO,
                             assets.TAMANIO_FUENTE_NORMAL, ancla="center")
                y += 28
        else:
            columna = panel.left + assets.COLUMNA_CREDITOS
            for etiqueta, valor in LINEAS_CREDITOS:
                if etiqueta:
                    dibujo.texto(pantalla, etiqueta.upper(), (columna - 16, y), assets.COLOR_CIAN_NEON,
                                 assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="midright")
                dibujo.texto(pantalla, valor, (columna, y), assets.COLOR_TEXTO_HUD,
                             assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
                y += 30
        boton = rect_boton_volver(self.tamanio)
        texto = espaciado(TEXTO_VER_INTRO if vista == VISTA_EXTRAS else TEXTO_VOLVER)
        brillo = _brillo_texto(texto, assets.TAMANIO_FUENTE_MENU)
        pantalla.blit(brillo, brillo.get_rect(center=boton.center))
        dibujo.texto(pantalla, texto, boton.center, assets.COLOR_MENU_SELECCION, assets.TAMANIO_FUENTE_MENU,
                     negrita=True, ancla="center")

    # --- Ratón -------------------------------------------------------------

    def manejar_mouse(self, evento, menu):
        """Hover enfoca, clic confirma. Retorna el sonido a reproducir."""
        if menu.ajustes is not None:
            sonido = self.ajustes.manejar_mouse(evento, menu.ajustes)
            if menu.ajustes.cerrado:  # clic en CERRAR
                menu.cerrar_ajustes()
            return sonido
        if evento.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button != 1:
            return None
        if menu.vista != VISTA_MENU:
            if evento.type == pygame.MOUSEBUTTONDOWN and rect_boton_volver(self.tamanio).collidepoint(evento.pos):
                return menu.accion(CONFIRMAR)
            return None
        elemento = self.elemento_en(evento.pos, menu)
        if elemento is None:
            return None
        if evento.type == pygame.MOUSEMOTION:
            return SONIDO_NAVEGAR if menu.enfocar(elemento) else None
        return menu.confirmar(elemento)

    def elemento_en(self, posicion, menu):
        for elemento, rect in rects_menu(self.tamanio).items():
            if rect.collidepoint(posicion) and (elemento != CONTINUAR or menu.habilitada(CONTINUAR)):
                return elemento
        return None


def _mezclar(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


_cache_brillos = {}


def _brillo_texto(texto, tamanio):
    """Halo violeta difuminado detrás de un texto (cacheado)."""
    clave = (texto, tamanio)
    if clave not in _cache_brillos:
        render = fuente(tamanio, True).render(texto, True, assets.COLOR_RESPLANDOR_MENU)
        radio = assets.RADIO_RESPLANDOR_MENU
        base = pygame.Surface((render.get_width() + radio * 4, render.get_height() + radio * 4), pygame.SRCALPHA)
        base.blit(render, (radio * 2, radio * 2))
        _cache_brillos[clave] = pygame.transform.gaussian_blur(base, radio)
    return _cache_brillos[clave].copy()


_cache_halos = {}


def _halo(radio, color):
    clave = (radio, color)
    if clave not in _cache_halos:
        lado = radio * 2 + 16
        base = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(base, (*color, 150), (lado // 2, lado // 2), radio, 4)
        _cache_halos[clave] = pygame.transform.gaussian_blur(base, 5)
    return _cache_halos[clave].copy()


def _difuminar_y_oscurecer(pantalla, intensidad):
    """Desenfoque barato (reducir y volver a ampliar) y velo negro al 60%.
    El velo es una multiplicación de color: no crea otra superficie."""
    ancho, alto = pantalla.get_size()
    factor = assets.REDUCCION_DESENFOQUE_MODAL
    pequena = pygame.transform.smoothscale(pantalla, (ancho // factor, alto // factor))
    difuminada = pygame.transform.smoothscale(pequena, (ancho, alto))
    if intensidad < 1:
        difuminada.set_alpha(round(255 * intensidad))  # solo durante la transición
    pantalla.blit(difuminada, (0, 0))
    brillo = 255 - round(assets.ALFA_VELO_MODAL * intensidad)
    pantalla.fill((brillo, brillo, brillo), special_flags=pygame.BLEND_MULT)
