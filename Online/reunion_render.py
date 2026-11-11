"""Reunión de emergencia del modo Online: dibujo y ratón (solo presentación).

- El botón REPORTAR del HUD, abajo a la derecha: rojo cuando está listo,
  apagado y con los segundos que faltan mientras recarga.
- La reunión: una tarjeta por jugador que se puede votar (con la ropa que se
  puso en los vestidores), el botón Saltar, el chat y el reloj. Durante la
  votación solo se ve QUIÉN votó; a quién, recién en el resultado.
- El resultado: a quién expulsaron y si era el impostor, y quién votó a quién.
- El fin de la partida: "¡Felicidades! Has descubierto al impostor" o "El
  impostor ha ganado", con el impostor a la vista.
- El botón SABOTEAR del impostor y los avisos de su publicación viral
  (la publicación misma se dibuja con la terminal tipo celular).

La regla está en Online/reunion.py y las constantes en src/core/assets.py.
"""

import math

import pygame

from Online.reunion import EXPULSADO, GANA_TRIPULACION, SALTAR
from src.ui.terminal_decision import PURIFICACION_EXITOSA
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


def en_boton_reportar(posicion, rect=None):
    return pygame.Rect(rect or assets.RECT_BOTON_REPORTAR).collidepoint(posicion)


def en_boton_sabotear(posicion):
    return pygame.Rect(assets.RECT_BOTON_SABOTEAR).collidepoint(posicion)


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


def _rayo(pantalla, centro, tamanio, color):
    """Rayo con primitivas: el sabotaje."""
    x, y = centro
    t = tamanio
    pygame.draw.polygon(pantalla, color, [(x + t * 0.12, y - t * 0.55), (x - t * 0.32, y + t * 0.06),
                                          (x - t * 0.02, y + t * 0.06), (x - t * 0.14, y + t * 0.55),
                                          (x + t * 0.32, y - t * 0.08), (x + t * 0.02, y - t * 0.08)])


def _dibujar_boton(pantalla, rect, texto, tecla, color, icono, recarga, total, tiempo):
    """Listo (recarga <= 0): de su color, con pulso. Si no, apagado y con los
    segundos que faltan. Bajo (< ALTO_MINIMO_BOTON_GRANDE): en una sola fila."""
    rect = pygame.Rect(rect)
    listo = recarga <= 0.0
    grande = rect.height >= assets.ALTO_MINIMO_BOTON_GRANDE
    if listo:
        pulso = 0.5 + 0.5 * math.sin(tiempo * 4.0)
        halo = rect.inflate(round(6 + 4 * pulso), round(6 + 4 * pulso))
        dibujo.panel_alfa(pantalla, halo, (*color, round(60 + 60 * pulso)), radio=16)
        dibujo.panel(pantalla, rect, color, assets.COLOR_TEXTO_HUD, 2, radio=14 if grande else 10)
        tinta, tinta_texto = assets.COLOR_TEXTO_HUD, assets.COLOR_TEXTO_HUD
    else:
        dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, assets.COLOR_REPORTAR_APAGADO, 2, radio=14 if grande else 10)
        lleno = 1.0 - recarga / total if total > 0 else 1.0
        relleno = pygame.Rect(rect.left + 2, rect.bottom - 2 - round((rect.height - 4) * lleno), rect.width - 4,
                              round((rect.height - 4) * lleno))
        if relleno.height > 0:
            dibujo.panel_alfa(pantalla, relleno, (*assets.COLOR_REPORTAR_APAGADO, 110), radio=12 if grande else 8)
        tinta, tinta_texto = assets.COLOR_REPORTAR_APAGADO, assets.COLOR_TEXTO_APAGADO
    if grande:
        icono(pantalla, (rect.centerx, rect.top + (34 if listo else 30)), 36 if listo else 30, tinta)
        if not listo:
            dibujo.texto(pantalla, f"{math.ceil(recarga)} s", (rect.centerx, rect.bottom - 30), assets.COLOR_TEXTO_SECUNDARIO,
                         assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        layout.texto_en_ancho(pantalla, texto, (rect.centerx, rect.bottom - (18 if listo else 11)), rect.width - 10,
                              tinta_texto, assets.TAMANIO_FUENTE_NORMAL if listo else assets.TAMANIO_FUENTE_PEQUENA,
                              negrita=True, ancla="center", minimo=9)
        dibujo.chip(pantalla, tecla, (rect.right - 6, rect.top + 6), ancla="topright")
        return
    # Compacto (en la barra de controles de la terminal): tecla, ícono, texto y segundos.
    chip = dibujo.chip(pantalla, tecla, (rect.left + 8, rect.centery), ancla="midleft")
    icono(pantalla, (chip.right + 24, rect.centery), 22, tinta)  # ocupa de x-16 a x+22
    etiqueta = texto if listo else f"{texto}  {math.ceil(recarga)} s"
    layout.texto_en_ancho(pantalla, etiqueta, (chip.right + 52, rect.centery), rect.right - chip.right - 58, tinta_texto,
                          assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midleft", minimo=9)


def dibujar_boton_reportar(pantalla, recarga, total, tiempo=0.0, rect=None):
    """REPORTAR: rojo cuando está listo (R o clic)."""
    _dibujar_boton(pantalla, rect or assets.RECT_BOTON_REPORTAR, assets.TEXTO_BOTON_REPORTAR, "R", assets.COLOR_REPORTAR,
                   _megafono, recarga, total, tiempo)


def dibujar_boton_sabotear(pantalla, recarga, total, tiempo=0.0):
    """SABOTEAR: solo el impostor lo ve (Q o clic)."""
    _dibujar_boton(pantalla, assets.RECT_BOTON_SABOTEAR, assets.TEXTO_BOTON_SABOTEAR, "Q", assets.COLOR_SABOTEAR,
                   _rayo, recarga, total, tiempo)


def dibujar_aviso_red(pantalla, texto, color, rect=None):
    """Chip en lugar del botón: "Expulsado" o "Impostor descubierto"."""
    rect = pygame.Rect(rect or assets.RECT_BOTON_REPORTAR)
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
    fondo = assets.COLOR_FONDO_TARJETA_REUNION
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
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_AVATAR_REUNION, zona_avatar, border_radius=8)
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
    dibujo.panel(pantalla, rect, assets.COLOR_FONDO_TARJETA_REUNION, borde, 3 if (enfocado or armado) else 1, radio=10)
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


# ----------------------------------------------------------------------
# Fin de la partida
# ----------------------------------------------------------------------

_CONFETI = [((numero * 97) % 1280, (numero * 53) % 720, 40 + (numero * 31) % 70, numero % 4) for numero in
            range(assets.CANTIDAD_CONFETI)]


def _confeti(pantalla, tiempo):
    """Papelitos que caen (posiciones fijas que se desplazan con el tiempo)."""
    colores = (assets.COLOR_VERIFICADO, assets.COLOR_CIVITAS, assets.COLOR_ALERTA, assets.COLOR_TRIPULANTE)
    alto = pantalla.get_height()
    for x, y, velocidad, color in _CONFETI:
        cae = (y + tiempo * velocidad) % alto
        vaiven = math.sin(tiempo * 2.0 + x) * 8
        pygame.draw.rect(pantalla, colores[color], (round(x + vaiven), round(cae), 6, 10), border_radius=2)


def textos_fin(fin, es_impostor_local):
    """(título, subtítulo, remate) de la pantalla final para esta PC."""
    return assets.TEXTOS_FIN_PARTIDA[(fin, bool(es_impostor_local))]


def dibujar_fin_partida(pantalla, vista, jugadores, indice_local, tiempo=0.0):
    """Pantalla final: ganó la tripulación (confeti) o el impostor (rojo), con
    el impostor a la vista. Los textos dependen de si esta PC es la del impostor."""
    gana_tripulacion = vista.fin == GANA_TRIPULACION
    acento = assets.COLOR_VERIFICADO if gana_tripulacion else assets.COLOR_IMPOSTOR
    kit.velo(pantalla, 235)
    if gana_tripulacion:
        _confeti(pantalla, tiempo)
    titulo, subtitulo, remate = textos_fin(vista.fin, indice_local == vista.impostor)
    centro_x = pantalla.get_width() // 2
    layout.texto_en_ancho(pantalla, titulo, (centro_x, 70), pantalla.get_width() - 120, acento,
                          assets.TAMANIO_FUENTE_ENORME, negrita=True, ancla="midtop")
    layout.texto_en_ancho(pantalla, subtitulo, (centro_x, 140), pantalla.get_width() - 160, assets.COLOR_TEXTO_HUD,
                          assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="midtop")
    if vista.impostor is not None:
        avatar = _avatar(vista.impostor, jugadores, assets.ESCALA_AVATAR_RESULTADO_REUNION)
        centro = (centro_x, 300 + round(math.sin(tiempo * 2.0) * 5))
        pulso = 0.5 + 0.5 * math.sin(tiempo * 3.0)
        halo = pygame.Rect(0, 0, 200, 200)
        halo.center = centro
        dibujo.panel_alfa(pantalla, halo, (*assets.COLOR_IMPOSTOR, round(40 + 50 * pulso)), radio=100)
        if avatar is not None:
            sprites.dibujar_centrado(pantalla, avatar, centro)
        dibujo.texto(pantalla, assets.TEXTO_FIN_ERA_IMPOSTOR.format(nombre=nombre_jugador(vista.impostor, jugadores)),
                     (centro_x, 418), assets.COLOR_IMPOSTOR, assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="midtop")
    layout.texto_en_ancho(pantalla, remate, (centro_x, 470), pantalla.get_width() - 160, assets.COLOR_CIVITAS if
                          gana_tripulacion else assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_GRANDE,
                          negrita=True, ancla="midtop")
    y = 540
    for fila in _texto_votos(vista, jugadores)[:3]:
        dibujo.texto(pantalla, fila, (centro_x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                     ancla="midtop")
        y += 20
    # "Enter: volver al menú" va en la barra de controles (Main), cuando ya se puede salir.


# ----------------------------------------------------------------------
# Publicación del botón SABOTEAR
# ----------------------------------------------------------------------

def dibujar_alerta_post(pantalla, tiempo=0.0):
    """Arriba al centro, para la tripulación (el impostor ve ahí su bloqueo)."""
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    kit.panel(pantalla, rect, assets.COLOR_REPORTAR)
    if int(tiempo * 3) % 2 == 0:
        pygame.draw.rect(pantalla, assets.COLOR_REPORTAR, rect, 2, border_radius=10)
    kit.rotulo(pantalla, "Alerta", (rect.left + 16, rect.top + 8), assets.COLOR_REPORTAR)
    layout.texto_en_ancho(pantalla, assets.TEXTO_ALERTA_POST_SABOTAJE, (rect.left + 16, rect.top + 28), rect.width - 32,
                          assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True, minimo=10)


def textos_resultado_post(vista):
    """(título, detalle, efecto) de cómo terminó la publicación del sabotaje."""
    frenado = vista.resultado == PURIFICACION_EXITOSA
    titulo = assets.TEXTO_POST_FRENADO if frenado else assets.TEXTO_POST_VIRAL
    detalle = assets.TEXTO_POST_ELIGIERON.format(opcion=vista.opcion) if vista.opcion else assets.TEXTO_POST_SIN_TIEMPO
    efecto = assets.TEXTO_POST_EFECTO_FRENADO if frenado else assets.TEXTO_POST_EFECTO_VIRAL
    return titulo, detalle, efecto


def dibujar_resultado_post(pantalla, vista):
    """Tarjeta con cómo terminó la publicación: frenada (cian) o viral (rojo)."""
    frenado = vista.resultado == PURIFICACION_EXITOSA
    acento = assets.COLOR_VERIFICADO if frenado else assets.COLOR_REPORTAR
    kit.velo(pantalla, 150)
    rect = pygame.Rect(assets.RECT_RESULTADO_POST_SABOTAJE)
    kit.panel(pantalla, rect, acento)
    titulo, detalle, efecto = textos_resultado_post(vista)
    layout.texto_en_ancho(pantalla, titulo, (rect.centerx, rect.top + 26), rect.width - 40, acento,
                          assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="midtop")
    layout.texto_en_ancho(pantalla, detalle, (rect.centerx, rect.top + 84), rect.width - 40, assets.COLOR_TEXTO_HUD,
                          assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="midtop")
    layout.texto_en_ancho(pantalla, efecto, (rect.centerx, rect.top + 124), rect.width - 40, assets.COLOR_TEXTO_SECUNDARIO,
                          assets.TAMANIO_FUENTE_NORMAL, ancla="midtop")
