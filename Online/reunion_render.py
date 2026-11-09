"""Reunión de emergencia del modo Online: dibujo y ratón (solo presentación).

- El botón REPORTAR del HUD, abajo a la derecha: rojo cuando está listo,
  apagado y con los segundos que faltan mientras recarga.
- La reunión: una tarjeta por jugador que se puede votar (con la ropa que se
  puso en los vestidores), el botón Saltar, el chat y el reloj. Durante la
  votación solo se ve QUIÉN votó; a quién, recién en el resultado.
- El resultado: a quién expulsaron y si era el impostor, y quién votó a quién.

La regla está en Online/reunion.py y las constantes en src/core/assets.py.
"""

import math

import pygame

from Online.reunion import EXPULSADO, SALTAR
from src.core import assets
from src.core.balance import DURACION_RESULTADO_REUNION
from src.ui import dibujo, kit, layout, sprites


def nombre_jugador(indice, jugadores):
    """"J2 · Candidato" (o solo "J2" si no hay jugador con ese índice)."""
    jugador = jugadores[indice] if 0 <= indice < len(jugadores) else None
    nombre = getattr(jugador, "NOMBRE", "")
    return f"J{indice + 1} · {nombre}" if nombre else f"J{indice + 1}"


def _color_de(indice, jugadores):
    jugador = jugadores[indice] if 0 <= indice < len(jugadores) else None
    return getattr(jugador, "COLOR", assets.COLOR_TEXTO_HUD)


def _avatar(indice, jugadores, escala):
    jugador = jugadores[indice] if 0 <= indice < len(jugadores) else None
    if jugador is None:
        return None
    return sprites.sprite_jugador(getattr(jugador, "COLOR", assets.COLOR_TEXTO_HUD), escala=escala,
                                  rol=getattr(jugador, "rol", None), apariencia=getattr(jugador, "apariencia", None))


# ----------------------------------------------------------------------
# Rectángulos (también para el ratón)
# ----------------------------------------------------------------------

def rects_candidatos(cantidad):
    """Una tarjeta por candidato, en dos columnas dentro de RECT_CANDIDATOS_REUNION."""
    area = pygame.Rect(assets.RECT_CANDIDATOS_REUNION)
    sep = assets.SEPARACION_CANDIDATOS_REUNION
    filas = max(2, math.ceil(cantidad / 2))
    ancho = (area.width - sep) // 2
    alto = (area.height - sep * (filas - 1)) // filas
    return [pygame.Rect(area.left + (i % 2) * (ancho + sep), area.top + (i // 2) * (alto + sep), ancho, alto)
            for i in range(cantidad)]


def objetivo_en(posicion, candidatos):
    """Qué votaría un clic en `posicion`: el índice de un candidato, SALTAR o None."""
    for indice, rect in zip(candidatos, rects_candidatos(len(candidatos))):
        if rect.collidepoint(posicion):
            return indice
    if pygame.Rect(assets.RECT_SALTAR_REUNION).collidepoint(posicion):
        return SALTAR
    return None


def en_boton_reportar(posicion):
    return pygame.Rect(assets.RECT_BOTON_REPORTAR).collidepoint(posicion)


def opciones_de_voto(vista):
    """El orden en que las flechas recorren las opciones: candidatos y Saltar."""
    return list(vista.candidatos) + [SALTAR]


# ----------------------------------------------------------------------
# Botón REPORTAR (HUD)
# ----------------------------------------------------------------------

def _megafono(pantalla, centro, tamanio, color):
    """Megáfono con primitivas: boca, cuerpo, mango y dos ondas."""
    x, y = centro
    t = tamanio
    pygame.draw.polygon(pantalla, color, [(x - t * 0.55, y - t * 0.18), (x + t * 0.25, y - t * 0.5),
                                          (x + t * 0.25, y + t * 0.5), (x - t * 0.55, y + t * 0.18)])
    pygame.draw.rect(pantalla, color, pygame.Rect(round(x - t * 0.75), round(y - t * 0.2), round(t * 0.24), round(t * 0.4)),
                     border_radius=2)
    pygame.draw.line(pantalla, color, (round(x - t * 0.4), round(y + t * 0.2)), (round(x - t * 0.3), round(y + t * 0.55)), 3)
    for radio in (0.45, 0.75):
        caja = pygame.Rect(0, 0, round(t * radio * 2), round(t * radio * 2))
        caja.center = (round(x + t * 0.25), round(y))
        pygame.draw.arc(pantalla, color, caja, -0.7, 0.7, 2)


def dibujar_boton_reportar(pantalla, recarga, total, tiempo=0.0):
    """Listo (recarga <= 0): rojo, con pulso. Si no, apagado con los segundos."""
    rect = pygame.Rect(assets.RECT_BOTON_REPORTAR)
    listo = recarga <= 0.0
    if listo:
        pulso = 0.5 + 0.5 * math.sin(tiempo * 4.0)
        halo = rect.inflate(round(6 + 4 * pulso), round(6 + 4 * pulso))
        dibujo.panel_alfa(pantalla, halo, (*assets.COLOR_REPORTAR, round(60 + 60 * pulso)), radio=16)
        dibujo.panel(pantalla, rect, assets.COLOR_REPORTAR, assets.COLOR_TEXTO_HUD, 2, radio=14)
        _megafono(pantalla, (rect.centerx, rect.top + 34), 36, assets.COLOR_TEXTO_HUD)
        layout.texto_en_ancho(pantalla, assets.TEXTO_BOTON_REPORTAR, (rect.centerx, rect.bottom - 18), rect.width - 10,
                              assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="center", minimo=10)
    else:
        dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, assets.COLOR_REPORTAR_APAGADO, 2, radio=14)
        lleno = 1.0 - recarga / total if total > 0 else 1.0
        relleno = pygame.Rect(rect.left + 2, rect.bottom - 2 - round((rect.height - 4) * lleno), rect.width - 4,
                              round((rect.height - 4) * lleno))
        if relleno.height > 0:
            dibujo.panel_alfa(pantalla, relleno, (*assets.COLOR_REPORTAR_APAGADO, 110), radio=12)
        _megafono(pantalla, (rect.centerx, rect.top + 30), 30, assets.COLOR_REPORTAR_APAGADO)
        dibujo.texto(pantalla, f"{math.ceil(recarga)} s", (rect.centerx, rect.bottom - 30), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        layout.texto_en_ancho(pantalla, assets.TEXTO_BOTON_REPORTAR, (rect.centerx, rect.bottom - 11), rect.width - 10,
                              assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center", minimo=9)
    dibujo.chip(pantalla, "R", (rect.right - 6, rect.top + 6), ancla="topright")


def dibujar_aviso_red(pantalla, texto, color):
    """Chip sobre el botón: "Expulsado" o "Impostor descubierto"."""
    rect = pygame.Rect(assets.RECT_BOTON_REPORTAR)
    dibujo.chip(pantalla, texto, (rect.right, rect.bottom), color, assets.COLOR_FONDO_PANEL, color,
                assets.TAMANIO_FUENTE_PEQUENA, ancla="bottomright", alto=30, margen=10)


# ----------------------------------------------------------------------
# La reunión
# ----------------------------------------------------------------------

def _reloj(pantalla, vista, panel_rect):
    restante = vista.restante
    color = assets.COLOR_GRAVE if restante <= 10 else assets.COLOR_ALERTA if restante <= 20 else assets.COLOR_TEXTO_HUD
    x = panel_rect.right - 28
    minutos, segundos = divmod(math.ceil(restante), 60)
    kit.rotulo(pantalla, "Tiempo para hablar y votar", (x, panel_rect.top + 20), assets.COLOR_TEXTO_SECUNDARIO, ancla="topright")
    dibujo.texto(pantalla, f"{minutos}:{segundos:02d}", (x, panel_rect.top + 38), color, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="topright")
    barra = pygame.Rect(x - 260, panel_rect.top + 84, 260, 5)
    dibujo.barra(pantalla, barra, restante / vista.duracion if vista.duracion else 0.0, color, assets.COLOR_FONDO_BARRA, None)


def _tarjeta(pantalla, rect, indice, jugadores, vista, indice_local, enfocada, armada, mi_voto, tiempo):
    votó = indice in vista.votaron
    fondo = assets.COLOR_OPCION_FONDO
    borde = assets.COLOR_BORDE_VIDRIO
    if armada:
        borde = assets.COLOR_REPORTAR
    elif enfocada:
        borde = assets.COLOR_CIVITAS
    dibujo.panel(pantalla, rect, fondo, borde, 3 if (enfocada or armada) else 1, radio=10)
    if enfocada and not armada:
        pulso = 0.5 + 0.5 * math.sin(tiempo * 5.0)
        dibujo.panel_alfa(pantalla, rect.inflate(6, 6), (*assets.COLOR_CIVITAS, round(30 + 40 * pulso)), radio=12)
    avatar = _avatar(indice, jugadores, assets.ESCALA_AVATAR_REUNION)
    zona_avatar = pygame.Rect(rect.left + 12, rect.top + 12, min(rect.height - 24, 120), rect.height - 24)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, zona_avatar, border_radius=8)
    if avatar is not None:
        if avatar.get_height() > zona_avatar.height - 8:
            factor = (zona_avatar.height - 8) / avatar.get_height()
            avatar = pygame.transform.scale(avatar, (max(1, round(avatar.get_width() * factor)), zona_avatar.height - 8))
        sprites.dibujar_centrado(pantalla, avatar, zona_avatar.center)
    x = zona_avatar.right + 14
    ancho = rect.right - x - 12
    layout.texto_en_ancho(pantalla, f"J{indice + 1}", (x, rect.top + 14), ancho, _color_de(indice, jugadores),
                          assets.TAMANIO_FUENTE_TITULO, negrita=True)
    nombre = getattr(jugadores[indice], "NOMBRE", "") if 0 <= indice < len(jugadores) else ""
    layout.texto_en_ancho(pantalla, nombre, (x, rect.top + 44), ancho, assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)
    y_chips = rect.bottom - 40
    x_chip = x
    if indice == indice_local:
        x_chip = dibujo.chip(pantalla, "TÚ", (x_chip, y_chips), assets.COLOR_CIVITAS).right + 8
    if votó:
        x_chip = dibujo.chip(pantalla, "VOTÓ", (x_chip, y_chips), assets.COLOR_VERIFICADO).right + 8
    if mi_voto == indice:
        dibujo.chip(pantalla, "Tu voto", (x_chip, y_chips), assets.COLOR_REPORTAR)
    if armada:
        layout.texto_en_ancho(pantalla, "Otra vez para votar", (x, rect.top + 70), ancho, assets.COLOR_REPORTAR,
                              assets.TAMANIO_FUENTE_PEQUENA, negrita=True)


def _boton_saltar(pantalla, enfocado, armado, mi_voto, cuantos):
    rect = pygame.Rect(assets.RECT_SALTAR_REUNION)
    borde = assets.COLOR_REPORTAR if armado else assets.COLOR_CIVITAS if enfocado else assets.COLOR_BORDE_VIDRIO
    dibujo.panel(pantalla, rect, assets.COLOR_OPCION_FONDO, borde, 3 if (enfocado or armado) else 1, radio=10)
    texto = assets.TEXTO_SALTAR_REUNION + ("  ·  Enter o clic otra vez" if armado else "")
    if mi_voto == SALTAR:
        texto = "Saltaste la votación"
    dibujo.texto(pantalla, texto, (rect.left + 20, rect.centery), assets.COLOR_TEXTO_HUD if enfocado or armado else
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="midleft")
    dibujo.texto(pantalla, cuantos, (rect.right - 20, rect.centery), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="midright")


def _lineas_chat(chat, jugadores, ancho):
    """[(color o None, texto)] de abajo hacia arriba no: en orden, ya partidas."""
    lineas = []
    for autor, texto in chat:
        nombre = f"J{autor + 1}:"
        partes = dibujo.ajustar_texto(f"{nombre} {texto}", assets.TAMANIO_FUENTE_NORMAL, ancho)
        for numero, parte in enumerate(partes):
            lineas.append((autor if numero == 0 else None, parte))
    return lineas


def _chat(pantalla, vista, jugadores, texto_chat, puede_escribir, tiempo):
    rect = pygame.Rect(assets.RECT_CHAT_REUNION)
    kit.panel(pantalla, rect, assets.COLOR_CIVITAS)
    kit.rotulo(pantalla, "Chat", (rect.left + 18, rect.top + 14), assets.COLOR_CIVITAS)
    entrada = pygame.Rect(rect.left + 14, rect.bottom - 14 - assets.ALTO_ENTRADA_CHAT_REUNION, rect.width - 28,
                          assets.ALTO_ENTRADA_CHAT_REUNION)
    zona = pygame.Rect(rect.left + 18, rect.top + 40, rect.width - 36, entrada.top - rect.top - 50)
    alto_linea = assets.TAMANIO_FUENTE_NORMAL + 7
    lineas = _lineas_chat(vista.chat, jugadores, zona.width)
    visibles = lineas[-max(1, zona.height // alto_linea):]
    if not visibles:
        layout.parrafo_en_caja(pantalla, "Nadie escribió todavía. Cuenten qué vieron en la terminal.",
                               pygame.Rect(zona.left, zona.top, zona.width, 60), assets.COLOR_TEXTO_APAGADO,
                               assets.TAMANIO_FUENTE_NORMAL)
    for numero, (autor, texto) in enumerate(visibles):
        y = zona.top + numero * alto_linea
        if autor is not None:
            nombre = f"J{autor + 1}:"
            caja = dibujo.texto(pantalla, nombre, (zona.left, y), _color_de(autor, jugadores), assets.TAMANIO_FUENTE_NORMAL,
                                negrita=True)
            dibujo.texto(pantalla, texto[len(nombre):], (caja.right, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
        else:
            dibujo.texto(pantalla, texto, (zona.left, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
    dibujo.panel(pantalla, entrada, assets.COLOR_FONDO, assets.COLOR_CIVITAS if puede_escribir else assets.COLOR_BORDE_VIDRIO,
                 2 if puede_escribir else 1, radio=8)
    if not puede_escribir:
        dibujo.texto(pantalla, assets.TEXTO_EXPULSADO_PROPIO, (entrada.left + 12, entrada.centery), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        return
    if texto_chat:
        # Se ve el final de lo que se está escribiendo.
        fuente = dibujo.fuente(assets.TAMANIO_FUENTE_NORMAL, False)
        visible = texto_chat
        while visible and fuente.size(visible)[0] > entrada.width - 34:
            visible = visible[1:]
        caja = dibujo.texto(pantalla, visible, (entrada.left + 12, entrada.centery), assets.COLOR_TEXTO_HUD,
                            assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        cursor_x = caja.right + 2
    else:
        dibujo.texto(pantalla, assets.TEXTO_PISTA_CHAT_REUNION, (entrada.left + 12, entrada.centery), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        cursor_x = entrada.left + 10
    if int(tiempo * 2) % 2 == 0:
        pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (cursor_x, entrada.top + 11), (cursor_x, entrada.bottom - 11), 2)


def dibujar_reunion(pantalla, vista, jugadores, indice_local, seleccion=None, armado=None, mi_voto=None,
                    texto_chat="", tiempo=0.0):
    """La votación en curso. `seleccion`: opción enfocada (índice o SALTAR);
    `armado`: la que espera el segundo Enter/clic; `mi_voto`: lo que votó
    esta PC (o None); `texto_chat`: lo que se está escribiendo."""
    kit.velo(pantalla, assets.ALFA_VELO_REUNION)
    panel_rect = pygame.Rect(assets.RECT_PANEL_REUNION)
    kit.panel(pantalla, panel_rect, assets.COLOR_REPORTAR)
    dibujo.texto(pantalla, assets.TEXTO_TITULO_REUNION, (panel_rect.left + 28, panel_rect.top + 20), assets.COLOR_REPORTAR,
                 assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    convocante = f"Convocada por J{vista.convocante + 1}" if vista.convocante is not None else "Reunión"
    layout.texto_en_ancho(pantalla, f"{convocante}  ·  Hablen y voten: ¿quién es el impostor?",
                          (panel_rect.left + 28, panel_rect.top + 66), 760, assets.COLOR_TEXTO_SECUNDARIO,
                          assets.TAMANIO_FUENTE_NORMAL)
    _reloj(pantalla, vista, panel_rect)
    puede_votar = indice_local in vista.candidatos and indice_local not in vista.votaron and mi_voto is None
    for indice, rect in zip(vista.candidatos, rects_candidatos(len(vista.candidatos))):
        _tarjeta(pantalla, rect, indice, jugadores, vista, indice_local, puede_votar and seleccion == indice,
                 puede_votar and armado == indice, mi_voto, tiempo)
    votaron = f"Votaron {len(vista.votaron)} de {len(vista.candidatos)}"
    _boton_saltar(pantalla, puede_votar and seleccion == SALTAR, puede_votar and armado == SALTAR, mi_voto, votaron)
    _chat(pantalla, vista, jugadores, texto_chat, indice_local in vista.candidatos, tiempo)


def _texto_votos(vista, jugadores):
    """["J2 · Candidato: J1, J3", "Saltar: J4"] con los votos emitidos."""
    por_objetivo = {}
    for votante, objetivo in vista.votos:
        por_objetivo.setdefault(objetivo, []).append(f"J{votante + 1}")
    filas = []
    for objetivo, votantes in sorted(por_objetivo.items(), key=lambda par: (par[0] == SALTAR, str(par[0]))):
        nombre = "Saltar" if objetivo == SALTAR else nombre_jugador(objetivo, jugadores)
        filas.append(f"{nombre}: {', '.join(votantes)}  ({len(votantes)})")
    return filas or ["Nadie votó."]


def dibujar_resultado_reunion(pantalla, vista, jugadores, tiempo=0.0):
    """A quién expulsaron (y si era el impostor) o por qué no expulsaron a nadie."""
    kit.velo(pantalla, assets.ALFA_VELO_REUNION)
    panel_rect = pygame.Rect(assets.RECT_PANEL_REUNION)
    acento = assets.COLOR_IMPOSTOR if vista.era_impostor else assets.COLOR_TRIPULANTE if vista.expulsado is not None \
        else assets.COLOR_CIVITAS
    kit.panel(pantalla, panel_rect, acento)
    kit.rotulo(pantalla, "Resultado de la votación", (panel_rect.centerx, panel_rect.top + 26), assets.COLOR_TEXTO_SECUNDARIO,
               ancla="midtop")
    y = panel_rect.top + 64
    if vista.motivo == EXPULSADO and vista.expulsado is not None:
        avatar = _avatar(vista.expulsado, jugadores, assets.ESCALA_AVATAR_RESULTADO_REUNION)
        if avatar is not None:
            flota = round(math.sin(tiempo * 2.0) * 4)
            sprites.dibujar_centrado(pantalla, avatar, (panel_rect.centerx, y + 70 + flota))
        y += 160
        layout.texto_en_ancho(pantalla, f"{nombre_jugador(vista.expulsado, jugadores)} fue expulsado",
                              (panel_rect.centerx, y), panel_rect.width - 80, assets.COLOR_TEXTO_HUD,
                              assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="midtop")
        y += 52
        dibujo.texto(pantalla, assets.TEXTO_ERA_IMPOSTOR if vista.era_impostor else assets.TEXTO_NO_ERA_IMPOSTOR,
                     (panel_rect.centerx, y), acento, assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="midtop")
        y += 52
    else:
        y += 90
        layout.texto_en_ancho(pantalla, assets.TEXTOS_MOTIVO_REUNION.get(vista.motivo, "Nadie fue expulsado"),
                              (panel_rect.centerx, y), panel_rect.width - 80, assets.COLOR_TEXTO_HUD,
                              assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="midtop")
        y += 110
    kit.rotulo(pantalla, "Votos", (panel_rect.centerx, y), assets.COLOR_TEXTO_SECUNDARIO, ancla="midtop")
    y += 26
    for fila in _texto_votos(vista, jugadores)[:6]:
        dibujo.texto(pantalla, fila, (panel_rect.centerx, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, ancla="midtop")
        y += 24
    barra = pygame.Rect(panel_rect.centerx - 160, panel_rect.bottom - 28, 320, 4)
    dibujo.barra(pantalla, barra, vista.resultado_restante / DURACION_RESULTADO_REUNION, acento, assets.COLOR_FONDO_BARRA, None)
