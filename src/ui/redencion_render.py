"""Pantallas de la crisis y de «Segunda oportunidad» (solo presentación).

    dibujar_eleccion: las dos salidas de la crisis, claras y sin reloj.
    dibujar_etapa: la etapa en curso de la MisionRedencion. Reconocer y
        Confianza navegan su árbol; Corregir muestra el grafo social real:
        quién recibió el rumor, quién ya tiene la corrección y quién falta.
    dibujar_final_derrota: «La confianza perdida» con lo que pasó y salidas.

Lee los objetos de src/story/redencion.py; no los modifica.
"""

import pygame

from src.core import assets
from src.core.balance import COBERTURA_REDENCION, OPORTUNIDADES_REDENCION
from src.story import redencion as red_mod
from src.ui import dibujo, kit, layout, red_social_render, sprites

_RECT_IZQ = pygame.Rect(48, 110, 420, 500)
_RECT_DER = pygame.Rect(488, 110, 744, 500)


def _fondo(pantalla, id_fondo, alfa=215):
    imagen = sprites.fondo_historia(id_fondo, pantalla.get_size())
    if imagen is not None:
        pantalla.blit(imagen, (0, 0))
    else:
        pantalla.fill(assets.COLOR_NOCHE)
    kit.velo(pantalla, alfa)


def dibujar_eleccion(pantalla, eleccion, datos, tiempo):
    _fondo(pantalla, assets.FONDO_REDENCION, 150)
    cx = pantalla.get_width() // 2
    kit.rotulo(pantalla, "Crisis de reputación", (cx, 96), assets.COLOR_GRAVE, ancla="midtop")
    caja = pygame.Rect(cx - 430, 122, 860, 110)
    layout.parrafo_en_caja(pantalla, datos["dialogo_mentora"], caja, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO,
                           interlineado=8, centrado=True)
    kit.rotulo(pantalla, f"{datos['mentora']['nombre']}  ·  {datos['mentora']['rol']}", (cx, 234), assets.COLOR_TEXTO_SECUNDARIO,
               ancla="midtop")
    for indice, (clave, titulo, detalle) in enumerate((
            (eleccion.ACEPTAR, datos["opcion_aceptar"], datos["detalle_aceptar"]),
            (eleccion.RECHAZAR, datos["opcion_rechazar"], datos["detalle_rechazar"]))):
        rect = pygame.Rect(cx - 500 + indice * 510, 300, 490, 170)
        acento = assets.COLOR_VERIFICADO if clave == eleccion.ACEPTAR else assets.COLOR_GRAVE
        seleccionada = eleccion.seleccion == clave
        kit.panel(pantalla, rect, acento if seleccionada else assets.COLOR_BORDE_VIDRIO, alfa=240, filo="todo" if seleccionada else "arriba")
        interior = rect.inflate(-48, -48)
        y = layout.parrafo_en_caja(pantalla, titulo, pygame.Rect(interior.left, interior.top, interior.width, 60),
                                   acento if seleccionada else assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True,
                                   interlineado=4, centrado=True)
        layout.parrafo_en_caja(pantalla, detalle, pygame.Rect(interior.left, y + 6, interior.width, interior.bottom - y - 6),
                               assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, interlineado=4, centrado=True)
    kit.tecla(pantalla, "← →", "elegir", (cx - 110, 520), ancla="center")
    kit.tecla(pantalla, "Enter", "confirmar", (cx + 100, 520), ancla="center")


def _encabezado_etapa(pantalla, mision, datos):
    kit.cabecera(pantalla, f"Misión · Segunda oportunidad · Etapa {mision.numero_etapa} de 3",
                 assets.TITULO_ETAPA_REDENCION.get(mision.etapa, ""), color_sobre=assets.COLOR_VERIFICADO, ancho=860)
    ancho = pantalla.get_width()
    kit.rotulo(pantalla, "Oportunidades", (ancho - 48 - 3 * 20 + 6, 30), assets.COLOR_TEXTO_SECUNDARIO, ancla="topright")
    kit.puntos_oportunidad(pantalla, (ancho - 48 - 3 * 20 + 16, 38), mision.oportunidades, OPORTUNIDADES_REDENCION)
    if mision.reintentos == 0:
        kit.rotulo(pantalla, "Último intento", (ancho - 48, 54), assets.COLOR_ALERTA, ancla="topright")


def _aviso(pantalla, mision, rect):
    """Explica el último error o lo que falta: nunca se falla sin saber por qué."""
    if not mision.aviso:
        return
    kit.panel(pantalla, rect, assets.COLOR_ALERTA, alfa=245)
    layout.parrafo_en_caja(pantalla, mision.aviso, rect.inflate(-28, -18), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL,
                           interlineado=4, alinear_arriba=False)


def _opciones_arbol(pantalla, arbol, rect, tiempo):
    kit.panel(pantalla, rect, assets.COLOR_CIVITAS)
    y = layout.parrafo_en_caja(pantalla, arbol.pregunta, pygame.Rect(rect.left + 24, rect.top + 20, rect.width - 48, 72),
                               assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, negrita=True, interlineado=5)
    y = max(y, rect.top + 96)
    opciones = arbol.opciones
    alto = min(92, (rect.bottom - y - 70 - 12 * (len(opciones) - 1)) // max(1, len(opciones)))
    for i, nodo in enumerate(opciones):
        fila = pygame.Rect(rect.left + 24, y + i * (alto + 12), rect.width - 48, alto)
        kit.opcion(pantalla, fila, nodo.etiqueta, i == arbol.indice, tiempo)
    kit.tecla(pantalla, "← →", "elegir", (rect.left + 90, rect.bottom - 24), ancla="center")
    kit.tecla(pantalla, "Enter", "responder", (rect.left + 240, rect.bottom - 24), ancla="center")


def _lista_pruebas(pantalla, mision, rect):
    kit.panel(pantalla, rect, assets.COLOR_VERIFICADO)
    kit.rotulo(pantalla, "Lo que muestran las pruebas", (rect.left + 20, rect.top + 18), assets.COLOR_VERIFICADO)
    y = rect.top + 46
    for prueba in mision.pruebas:
        dibujo.texto(pantalla, prueba["titulo"], (rect.left + 20, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
        y = layout.parrafo_en_caja(pantalla, prueba["fragmento"], pygame.Rect(rect.left + 20, y + 22, rect.width - 40, 96),
                                   assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, interlineado=3) + 12


def dibujar_etapa(pantalla, mision, datos, tiempo):
    _fondo(pantalla, assets.FONDO_REDENCION, 225)
    _encabezado_etapa(pantalla, mision, datos)
    if mision.etapa == red_mod.ETAPA_CORREGIR:
        _dibujar_corregir(pantalla, mision, datos, tiempo)
    elif mision.etapa == red_mod.ETAPA_RECONOCER:
        _lista_pruebas(pantalla, mision, _RECT_IZQ)
        _opciones_arbol(pantalla, mision.arbol_reconocer, _RECT_DER, tiempo)
        _aviso(pantalla, mision, pygame.Rect(_RECT_DER.left, 622, _RECT_DER.width, 62))
    elif mision.etapa == red_mod.ETAPA_CONFIANZA:
        retrato = sprites.retrato_rol(assets.ID_RETRATO_MENTORA, 340)
        kit.panel(pantalla, _RECT_IZQ, assets.COLOR_VERIFICADO)
        if retrato is not None:
            pantalla.blit(retrato, retrato.get_rect(midbottom=(_RECT_IZQ.centerx, _RECT_IZQ.bottom - 74)))
        kit.rotulo(pantalla, datos["mentora"]["nombre"], (_RECT_IZQ.centerx, _RECT_IZQ.bottom - 60), assets.COLOR_TEXTO_HUD, ancla="midtop")
        kit.rotulo(pantalla, "Te acompaña", (_RECT_IZQ.centerx, _RECT_IZQ.bottom - 38), assets.COLOR_TEXTO_SECUNDARIO, ancla="midtop")
        _opciones_arbol(pantalla, mision.arbol_confianza, _RECT_DER, tiempo)
        _aviso(pantalla, mision, pygame.Rect(_RECT_DER.left, 622, _RECT_DER.width, 62))
    kit.tecla(pantalla, "Esc", "pausar la misión", (pantalla.get_width() - 48, 700))


def _dibujar_corregir(pantalla, mision, datos, tiempo):
    """El grafo social real: posiciones del mismo dibujo que la propagación."""
    kit.panel(pantalla, _RECT_DER, assets.COLOR_CIVITAS)
    red = mision.red
    posiciones = red_social_render.posiciones_en(red, _RECT_DER.inflate(-80, -80))
    for a in red.ciudadanos():
        for b in red.grafo.vecinos(a):
            if a < b:
                pygame.draw.aaline(pantalla, assets.COLOR_ARISTA_RED, posiciones[a], posiciones[b])
    for correccion in mision.correcciones:
        for a, b in correccion.aristas:
            pygame.draw.line(pantalla, assets.COLOR_VERIFICADO, posiciones[a], posiciones[b], 2)
    elegido = mision.ciudadano_elegido
    for nodo in red.ciudadanos():
        x, y = posiciones[nodo]
        if nodo in mision.alcanzados:
            color = assets.COLOR_VERIFICADO
        elif nodo in mision.objetivo_correccion:
            color = assets.COLOR_NOVA
        else:
            color = assets.COLOR_NODO_NEUTRO
        pygame.draw.circle(pantalla, color, (x, y), 15)
        pygame.draw.circle(pantalla, assets.COLOR_NOCHE, (x, y), 15, 2)
        if nodo == elegido:
            pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, (x, y), 20, 2)
        dibujo.texto(pantalla, red.nombre(nodo).split()[0], (x, y + 20), assets.COLOR_TEXTO_HUD if nodo == elegido else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, negrita=nodo == elegido, ancla="midtop")

    kit.panel(pantalla, _RECT_IZQ, assets.COLOR_VERIFICADO)
    x = _RECT_IZQ.left + 22
    y = layout.parrafo_en_caja(pantalla, datos["instruccion_corregir"], pygame.Rect(x, _RECT_IZQ.top + 18, _RECT_IZQ.width - 44, 112),
                               assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, interlineado=5) + 8
    kit.rotulo(pantalla, "Cobertura de la corrección", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    cobertura = mision.cobertura()
    barra = pygame.Rect(x, y + 22, _RECT_IZQ.width - 44, 12)
    dibujo.barra(pantalla, barra, cobertura, assets.COLOR_VERIFICADO)
    marca = barra.left + round(barra.width * COBERTURA_REDENCION)
    pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (marca, barra.top - 4), (marca, barra.bottom + 3), 2)
    dibujo.texto(pantalla, f"{round(cobertura * 100)} %  (meta {round(COBERTURA_REDENCION * 100)} %)", (x, barra.bottom + 8),
                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    y = barra.bottom + 40
    kit.rotulo(pantalla, "Publicar desde", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, red.nombre(elegido), (x, y + 20), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, negrita=True)
    dibujo.texto(pantalla, f"{red.roles.get(elegido, '')} · {len(red.grafo.vecinos(elegido))} contactos", (x, y + 46),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    y += 76
    faltan = [red.nombre(n).split()[0] for n in mision.sin_corregir()]
    kit.rotulo(pantalla, "Aún creen la información falsa", (x, y), assets.COLOR_NOVA)
    layout.parrafo_en_caja(pantalla, ", ".join(faltan) if faltan else "Nadie: todos recibieron la corrección.",
                           pygame.Rect(x, y + 20, _RECT_IZQ.width - 44, 44), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL,
                           interlineado=3)
    kit.rotulo(pantalla, f"Publicaciones disponibles: {mision.publicaciones_restantes}", (x, _RECT_IZQ.bottom - 58), assets.COLOR_ALERTA)
    kit.tecla(pantalla, "← →", "ciudadano", (x + 68, _RECT_IZQ.bottom - 24), ancla="center")
    kit.tecla(pantalla, "Enter", "publicar", (x + 230, _RECT_IZQ.bottom - 24), ancla="center")
    _aviso(pantalla, mision, pygame.Rect(_RECT_DER.left, 622, _RECT_DER.width, 62))


class FinalDerrota:
    """Salidas del final «La confianza perdida». Nunca deja atrapado a nadie:
    siempre hay al menos reintentar o una campaña nueva. Sin pygame."""

    REINTENTAR = "reintentar"
    NUEVA = "nueva"
    SEGUIR = "seguir"
    TEXTOS = {REINTENTAR: "Volver al punto de control", NUEVA: "Comenzar una nueva campaña", SEGUIR: "Seguir con mi equipo, sin voz"}

    def __init__(self, indice, balance, puede_seguir=False, puede_reiniciar=True):
        self.indice_jugador = indice
        self.balance = balance
        self.opciones = []
        if balance["punto_control"]:
            self.opciones.append(self.REINTENTAR)
        if puede_seguir:
            self.opciones.append(self.SEGUIR)
        if puede_reiniciar or not self.opciones:
            self.opciones.append(self.NUEVA)
        self.indice = 0
        self.resultado = None
        self.tiempo = 0.0

    def actualizar(self, dt):
        self.tiempo += dt

    def navegar(self, direccion):
        if direccion == red_mod.CONFIRMAR:
            self.resultado = self.opciones[self.indice]
        else:
            paso = -1 if direccion == red_mod.IZQUIERDA else 1
            self.indice = (self.indice + paso) % len(self.opciones)


def dibujar_final_derrota(pantalla, final):
    datos = final.balance
    _fondo(pantalla, assets.FONDO_CONFIANZA_PERDIDA, 170)
    kit.cabecera(pantalla, "Final", datos["titulo"], color_sobre=assets.COLOR_GRAVE)
    layout.parrafo_en_caja(pantalla, datos["texto"], pygame.Rect(48, 96, 1184, 54), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, interlineado=5)
    izquierda = pygame.Rect(48, 160, 380, 340)
    kit.panel(pantalla, izquierda, assets.COLOR_GRAVE)
    x = izquierda.left + 22
    kit.rotulo(pantalla, "Reputación final", (x, izquierda.top + 18), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, f"{datos['reputacion']:+d}", (x, izquierda.top + 38), assets.color_reputacion(datos["reputacion"]),
                 assets.TAMANIO_FUENTE_ENORME, negrita=True)
    dibujo.texto(pantalla, datos["nivel"], (x, izquierda.top + 100), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    kit.barra_reputacion(pantalla, pygame.Rect(x, izquierda.top + 128, izquierda.width - 44, 10), datos["reputacion"])
    y = izquierda.top + 162
    kit.rotulo(pantalla, "Información difundida", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, f"{datos['expuestos']} de {datos['ciudadanos']} ciudadanos la recibieron", (x, y + 20), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
    dibujo.texto(pantalla, f"{datos['sin_corregir']} siguen sin corrección", (x, y + 42), assets.COLOR_NOVA, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    y += 82
    kit.rotulo(pantalla, "Estado de Ciudad Nova", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.barra(pantalla, pygame.Rect(x, y + 22, izquierda.width - 44, 10), datos["salud"] / 100, assets.color_reputacion(datos["salud"] * 2 - 100))
    dibujo.texto(pantalla, f"Salud general: {datos['salud']}/100", (x, y + 38), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
    derecha = pygame.Rect(444, 160, 788, 340)
    kit.panel(pantalla, derecha, assets.COLOR_GRAVE)
    x = derecha.left + 24
    kit.rotulo(pantalla, "Lo que tus decisiones provocaron", (x, derecha.top + 18), assets.COLOR_TEXTO_SECUNDARIO)
    y = derecha.top + 44
    for consecuencia in datos["consecuencias"] or ("Ninguna corrección llegó a tiempo.",):
        pygame.draw.circle(pantalla, assets.COLOR_GRAVE, (x + 4, y + 10), 3)
        y = layout.parrafo_en_caja(pantalla, consecuencia, pygame.Rect(x + 18, y, derecha.width - 66, 62), assets.COLOR_TEXTO_HUD,
                                   assets.TAMANIO_FUENTE_NORMAL, interlineado=4) + 8
    kit.rotulo(pantalla, "Para pensar", (x, derecha.bottom - 88), assets.COLOR_ALERTA)
    layout.parrafo_en_caja(pantalla, datos["mensaje"], pygame.Rect(x, derecha.bottom - 66, derecha.width - 48, 54), assets.COLOR_TEXTO_HUD,
                           assets.TAMANIO_FUENTE_NORMAL, interlineado=4)
    ancho = 370
    total = len(final.opciones) * (ancho + 16) - 16
    x0 = (pantalla.get_width() - total) // 2
    for i, clave in enumerate(final.opciones):
        kit.opcion(pantalla, (x0 + i * (ancho + 16), 520, ancho, 60), final.TEXTOS[clave], i == final.indice, final.tiempo)
    kit.tecla(pantalla, "← →", "elegir", (pantalla.get_width() // 2 - 80, 610), ancla="center")
    kit.tecla(pantalla, "Enter", "confirmar", (pantalla.get_width() // 2 + 80, 610), ancla="center")
