"""Pantalla de lobby del modo Online (presentación con Pygame).

Dos sub-pantallas:
    1. Elegir rol: HOST (crear sala) o JOIN (unirse).
    2. Lobby: muestra los jugadores conectados (grafo de sala),
       elección de rol y botón de iniciar.

Usa las mismas primitivas de dibujo del juego (src/ui/dibujo.py) y los
colores/fuentes de src/core/assets.py para que se vea consistente con
el resto de las pantallas.
"""

import pygame
import time

from src.core import assets
from src.core.config import FPS
from src.ui import dibujo, hud, sprites

from Online.servidor import Servidor, PUERTO_DEFAULT
from Online.cliente import Cliente
from Online.protocolo import (
    ROLES, GrafoSala, ELEGIR_ROL, INICIAR, LOBBY, ESTADO,
    msg_elegir_rol, msg_iniciar, msg_lobby, msg_estado,
)

# Constantes de layout del lobby.
TITULO_ONLINE = "Modo Online"
SUBTITULO_HOST = "Crear sala (Host)"
SUBTITULO_JOIN = "Unirse (Join)"
ANCHO_TARJETA_LOBBY = 280
ALTO_TARJETA_LOBBY = 340

# Colores específicos del lobby.
COLOR_ONLINE = (100, 200, 255)  # azul claro para el modo online
COLOR_ESPERANDO = (150, 150, 182)
COLOR_CONECTADO = assets.COLOR_TEAL
COLOR_IP = assets.COLOR_AMARILLO

# Posiciones.
POS_TITULO = (640, 50)
POS_SUBTITULO = (640, 84)
POS_IP_DISPLAY = (640, 340)
POS_ESTADO = (640, 400)
POS_ROLES = (640, 460)
POS_INICIAR = (640, 560)
POS_INPUT_IP = (640, 360)
POS_AVISO = (640, 590)

# Resultado del lobby.
LOBBY_INICIAR = "iniciar"
LOBBY_VOLVER = "volver"
LOBBY_SALIR = None


def pantalla_elegir_modo_online(pantalla, reloj, presentar):
    """Pantalla donde se elige HOST o JOIN.
    Retorna 'host', 'join', 'volver' o None (cerrar ventana)."""
    opciones = ["host", "join"]
    indice = 0
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return "volver"
                elif evento.key in (pygame.K_LEFT, pygame.K_a):
                    indice = (indice - 1) % 2
                elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                    indice = (indice + 1) % 2
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return opciones[indice]
                elif evento.key == pygame.K_1:
                    return "host"
                elif evento.key == pygame.K_2:
                    return "join"

        # Dibujo.
        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, TITULO_ONLINE, POS_TITULO, COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, "¿Cómo quieres conectarte?", (640, 90),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        # Tarjeta HOST.
        rect_host = pygame.Rect(250, 160, ANCHO_TARJETA_LOBBY, ALTO_TARJETA_LOBBY)
        elegido_host = indice == 0
        color_h = COLOR_ONLINE if elegido_host else assets.COLOR_BORDE_CHIP
        dibujo.panel(pantalla, rect_host, assets.COLOR_FONDO_PANEL, color_h,
                     assets.GROSOR_TARJETA_RESALTADA if elegido_host else 1, radio=12)
        dibujo.chip(pantalla, "1", (rect_host.left + 20, rect_host.top + 18), color_h,
                    assets.COLOR_FONDO, color_h, assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        # Icono: muñeco con corona (host).
        img = sprites.sprite_jugador(COLOR_ONLINE, escala=5)
        pantalla.blit(img, img.get_rect(midtop=(rect_host.centerx, rect_host.top + 60)))
        dibujo.texto(pantalla, "Crear sala", (rect_host.centerx, rect_host.top + 200),
                     assets.COLOR_TEXTO_HUD if elegido_host else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Tú eres el Host", (rect_host.centerx, rect_host.top + 232),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Otros se unen con tu IP", (rect_host.centerx, rect_host.top + 258),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        # Tarjeta JOIN.
        rect_join = pygame.Rect(750, 160, ANCHO_TARJETA_LOBBY, ALTO_TARJETA_LOBBY)
        elegido_join = indice == 1
        color_j = COLOR_ONLINE if elegido_join else assets.COLOR_BORDE_CHIP
        dibujo.panel(pantalla, rect_join, assets.COLOR_FONDO_PANEL, color_j,
                     assets.GROSOR_TARJETA_RESALTADA if elegido_join else 1, radio=12)
        dibujo.chip(pantalla, "2", (rect_join.left + 20, rect_join.top + 18), color_j,
                    assets.COLOR_FONDO, color_j, assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        img2 = sprites.sprite_jugador(assets.COLOR_AMARILLO, escala=5)
        pantalla.blit(img2, img2.get_rect(midtop=(rect_join.centerx, rect_join.top + 60)))
        dibujo.texto(pantalla, "Unirse", (rect_join.centerx, rect_join.top + 200),
                     assets.COLOR_TEXTO_HUD if elegido_join else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Ingresa la IP del Host", (rect_join.centerx, rect_join.top + 232),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Misma red Wi-Fi / LAN", (rect_join.centerx, rect_join.top + 258),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        hud.dibujar_barra_controles(pantalla,
                                    [("← →", "elegir"), ("1-2", "directo"),
                                     ("Enter", "confirmar"), ("Esc", "volver")])
        presentar()
        reloj.tick(FPS)


def pantalla_lobby_host(pantalla, reloj, presentar, clases_rol):
    """Lobby del host: muestra la IP, espera al invitado, ambos eligen
    rol y el host inicia la partida.

    Retorna (lista_de_clases, Servidor) o 'volver' o None.
    `clases_rol` es la lista [Ciudadano, Influencer, Periodista, Candidato].
    """
    servidor = Servidor()
    ip = servidor.iniciar(PUERTO_DEFAULT)
    if ip is None:
        return _pantalla_error(pantalla, reloj, presentar, servidor.error)

    indice_rol = 0  # cursor del host sobre los roles
    rol_confirmado = False
    aviso = ""
    aviso_timer = 0.0

    while True:
        dt = reloj.tick(FPS) / 1000
        aviso_timer = max(0.0, aviso_timer - dt)

        # Procesar mensajes del servidor (en el hilo principal).
        for msg in servidor.leer_mensajes():
            tipo = msg.get("tipo")
            if tipo == LOBBY:
                pass  # el grafo de sala ya se actualizó en el servidor
            elif tipo == ELEGIR_ROL:
                pass  # ya procesado por el servidor

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                servidor.detener()
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    servidor.detener()
                    return "volver"
                if not rol_confirmado:
                    if evento.key in (pygame.K_LEFT, pygame.K_a):
                        indice_rol = (indice_rol - 1) % len(clases_rol)
                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                        indice_rol = (indice_rol + 1) % len(clases_rol)
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        rol_confirmado = True
                        nombre_rol = ROLES[indice_rol]
                        servidor.sala.elegir_rol(0, nombre_rol)
                        # Notificar al invitado.
                        servidor.enviar_a_invitado(msg_lobby(servidor.sala.a_dict()))
                    elif evento.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        indice_rol = evento.key - pygame.K_1
                        if indice_rol < len(clases_rol):
                            rol_confirmado = True
                            nombre_rol = ROLES[indice_rol]
                            servidor.sala.elegir_rol(0, nombre_rol)
                            servidor.enviar_a_invitado(msg_lobby(servidor.sala.a_dict()))
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    # Intentar iniciar la partida.
                    if servidor.sala.todos_listos():
                        servidor.enviar_a_invitado(msg_iniciar())
                        servidor.iniciado = True
                        # Devolver las clases elegidas.
                        clases = []
                        for jid in servidor.sala.jugadores():
                            nombre = servidor.sala.rol_de(jid)
                            idx = ROLES.index(nombre) if nombre in ROLES else 0
                            clases.append(clases_rol[idx])
                        return clases, servidor
                    else:
                        aviso = "Esperando a que todos elijan rol..."
                        aviso_timer = 2.0
                elif evento.key == pygame.K_BACKSPACE:
                    rol_confirmado = False
                    servidor.sala.elegir_rol(0, None)
                    servidor.enviar_a_invitado(msg_lobby(servidor.sala.a_dict()))

        # Dibujo.
        _dibujar_lobby(pantalla, "HOST", ip, servidor.puerto, servidor.sala,
                       clases_rol, indice_rol, rol_confirmado, 0,
                       aviso if aviso_timer > 0 else "")
        hud.dibujar_barra_controles(pantalla,
                                    [("← →", "elegir rol"), ("Enter", "confirmar"),
                                     ("Retroceso", "cambiar"), ("Esc", "volver")])
        presentar()


def pantalla_lobby_join(pantalla, reloj, presentar, clases_rol):
    """Lobby del invitado: ingresa la IP del host, se conecta, elige rol
    y espera a que el host inicie.

    Retorna (lista_de_clases, Cliente) o 'volver' o None.
    """
    # Fase 1: ingresar IP.
    ip = _pantalla_ingresar_ip(pantalla, reloj, presentar)
    if ip is None:
        return None
    if ip == "volver":
        return "volver"

    # Fase 2: conectar.
    cliente = Cliente()
    if not cliente.conectar(ip, PUERTO_DEFAULT):
        return _pantalla_error(pantalla, reloj, presentar, cliente.error)

    # Esperar BIENVENIDA.
    esperando = True
    timeout = 5.0
    while esperando and timeout > 0:
        dt = reloj.tick(FPS) / 1000
        timeout -= dt
        for msg in cliente.leer_mensajes():
            if msg.get("tipo") == "BIENVENIDA":
                esperando = False
                break
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                cliente.desconectar()
                return None

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, "Conectando...", (640, 360), COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        presentar()

    if esperando:
        cliente.desconectar()
        return _pantalla_error(pantalla, reloj, presentar, "Tiempo de conexión agotado")

    # Fase 3: lobby — elegir rol y esperar INICIAR.
    indice_rol = 0
    rol_confirmado = False
    aviso = ""
    aviso_timer = 0.0

    while True:
        dt = reloj.tick(FPS) / 1000
        aviso_timer = max(0.0, aviso_timer - dt)

        for msg in cliente.leer_mensajes():
            tipo = msg.get("tipo")
            if tipo == LOBBY:
                cliente.sala = GrafoSala.de_dict(msg.get("sala", {}))
            elif tipo == INICIAR:
                cliente.iniciado = True
                # Armar lista de clases.
                clases = []
                for jid in cliente.sala.jugadores():
                    nombre = cliente.sala.rol_de(jid)
                    idx = ROLES.index(nombre) if nombre in ROLES else 0
                    clases.append(clases_rol[idx])
                return clases, cliente

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                cliente.desconectar()
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    cliente.desconectar()
                    return "volver"
                if not rol_confirmado:
                    if evento.key in (pygame.K_LEFT, pygame.K_a):
                        indice_rol = (indice_rol - 1) % len(clases_rol)
                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                        indice_rol = (indice_rol + 1) % len(clases_rol)
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        rol_confirmado = True
                        cliente.enviar_rol(ROLES[indice_rol])
                    elif evento.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        idx = evento.key - pygame.K_1
                        if idx < len(clases_rol):
                            indice_rol = idx
                            rol_confirmado = True
                            cliente.enviar_rol(ROLES[indice_rol])
                elif evento.key == pygame.K_BACKSPACE:
                    rol_confirmado = False
                    cliente.enviar_rol(None)

        id_local = cliente.id_jugador or 1
        _dibujar_lobby(pantalla, "JOIN", ip, PUERTO_DEFAULT, cliente.sala,
                       clases_rol, indice_rol, rol_confirmado, id_local,
                       aviso if aviso_timer > 0 else "")
        hud.dibujar_barra_controles(pantalla,
                                    [("← →", "elegir rol"), ("Enter", "confirmar"),
                                     ("Retroceso", "cambiar"), ("Esc", "volver")])
        presentar()


# =========================================================================
# Pantallas auxiliares
# =========================================================================

def _pantalla_ingresar_ip(pantalla, reloj, presentar):
    """Campo de texto para ingresar la IP del host.
    Retorna la IP como str, 'volver' con Esc, o None si se cierra."""
    ip_texto = ""
    cursor_visible = True
    cursor_timer = 0.0
    while True:
        dt = reloj.tick(FPS) / 1000
        cursor_timer += dt
        if cursor_timer >= 0.5:
            cursor_visible = not cursor_visible
            cursor_timer = 0.0

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return "volver"
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if ip_texto.strip():
                        return ip_texto.strip()
                elif evento.key == pygame.K_BACKSPACE:
                    ip_texto = ip_texto[:-1]
                else:
                    char = evento.unicode
                    if char and (char.isdigit() or char == "."):
                        ip_texto += char

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, TITULO_ONLINE, POS_TITULO, COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Ingresa la IP del Host:", (640, 280),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_TITULO, ancla="center")

        # Campo de texto con borde.
        rect_input = pygame.Rect(380, 330, 520, 50)
        dibujo.panel(pantalla, rect_input, assets.COLOR_FONDO_PANEL, COLOR_ONLINE, 2, radio=8)
        mostrar = ip_texto + ("|" if cursor_visible else " ")
        dibujo.texto(pantalla, mostrar, (rect_input.left + 16, rect_input.centery),
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, ancla="midleft")

        dibujo.texto(pantalla, "Ejemplo: 192.168.1.20", (640, 410),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        hud.dibujar_barra_controles(pantalla,
                                    [("0-9 y .", "escribir"), ("Enter", "conectar"), ("Esc", "volver")])
        presentar()


def _pantalla_error(pantalla, reloj, presentar, mensaje):
    """Muestra un error y espera Enter o Esc."""
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    return "volver"

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, "Error de conexión", (640, 280), assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, str(mensaje), (640, 340), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Presiona Enter o Esc para volver", (640, 420),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        presentar()
        reloj.tick(FPS)


def _dibujar_lobby(pantalla, modo, ip, puerto, sala, clases_rol,
                   indice_rol, rol_confirmado, id_local, aviso):
    """Dibuja la pantalla del lobby (común a host y join)."""
    pantalla.fill(assets.COLOR_FONDO)

    # Título.
    etiqueta = "SALA — HOST" if modo == "HOST" else "SALA — INVITADO"
    dibujo.texto(pantalla, etiqueta, POS_TITULO, COLOR_ONLINE,
                 assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")

    # IP y puerto.
    if ip:
        dibujo.texto(pantalla, f"IP: {ip}:{puerto}", (640, 90), COLOR_IP,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")

    # Tarjetas de jugadores conectados.
    jugadores = sala.jugadores()
    n = max(len(jugadores), 2)
    ancho_t = 240
    sep = 40
    inicio_x = 640 - ((n - 1) * (ancho_t + sep)) / 2

    for i in range(n):
        x = int(inicio_x + i * (ancho_t + sep))
        rect = pygame.Rect(x - ancho_t // 2, 130, ancho_t, 200)
        conectado = i < len(jugadores)
        es_local = conectado and jugadores[i] == id_local
        color_borde = COLOR_ONLINE if es_local else (COLOR_CONECTADO if conectado else assets.COLOR_BORDE_CHIP)
        dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, color_borde,
                     3 if es_local else 1, radio=10)

        if conectado:
            jid = jugadores[i]
            rol_nombre = sala.rol_de(jid)
            etq = f"J{jid + 1}" + (" (tú)" if es_local else "")
            dibujo.texto(pantalla, etq, (rect.centerx, rect.top + 14),
                         color_borde, assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
            # Muñeco.
            if rol_nombre and rol_nombre in ROLES:
                idx = ROLES.index(rol_nombre)
                color_sprite = [assets.COLOR_CIUDADANO, assets.COLOR_INFLUENCER,
                                assets.COLOR_PERIODISTA, assets.COLOR_CANDIDATO][idx]
            else:
                color_sprite = assets.COLOR_TEXTO_APAGADO
            img = sprites.sprite_jugador(color_sprite, escala=4)
            pantalla.blit(img, img.get_rect(midtop=(rect.centerx, rect.top + 50)))
            estado = rol_nombre if rol_nombre else "Eligiendo..."
            dibujo.texto(pantalla, estado, (rect.centerx, rect.top + 165),
                         assets.COLOR_TEXTO_HUD if rol_nombre else COLOR_ESPERANDO,
                         assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        else:
            dibujo.texto(pantalla, "Esperando...", (rect.centerx, rect.centery),
                         COLOR_ESPERANDO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    # Selector de rol del jugador local (si no ha confirmado).
    y_roles = 370
    dibujo.texto(pantalla, "Elige tu rol:", (640, y_roles - 30),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    for i, nombre_rol in enumerate(ROLES):
        x = 280 + i * 190
        elegido = i == indice_rol
        confirmado_este = elegido and rol_confirmado
        color_r = [assets.COLOR_CIUDADANO, assets.COLOR_INFLUENCER,
                   assets.COLOR_PERIODISTA, assets.COLOR_CANDIDATO][i]
        color_borde = color_r if elegido else assets.COLOR_BORDE_CHIP
        rect_r = pygame.Rect(x - 70, y_roles, 140, 100)
        dibujo.panel(pantalla, rect_r, assets.COLOR_FONDO_PANEL, color_borde,
                     3 if elegido else 1, radio=8)
        if confirmado_este:
            dibujo.panel_alfa(pantalla, rect_r, color_r + (36,), radio=8)
        dibujo.chip(pantalla, str(i + 1), (rect_r.left + 8, rect_r.top + 8), color_borde,
                    assets.COLOR_FONDO, color_borde, assets.TAMANIO_FUENTE_PEQUENA, alto=22, margen=6)
        img_r = sprites.sprite_jugador(color_r, escala=3)
        pantalla.blit(img_r, img_r.get_rect(midtop=(rect_r.centerx, rect_r.top + 18)))
        dibujo.texto(pantalla, nombre_rol, (rect_r.centerx, rect_r.bottom - 18),
                     assets.COLOR_TEXTO_HUD if elegido else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

    # Estado.
    if rol_confirmado and modo == "HOST":
        if sala.todos_listos():
            dibujo.texto(pantalla, "¡Todos listos! Presiona Enter para iniciar", POS_INICIAR,
                         COLOR_CONECTADO, assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        else:
            dibujo.texto(pantalla, "Esperando a que el otro jugador elija rol...", POS_INICIAR,
                         COLOR_ESPERANDO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
    elif rol_confirmado and modo == "JOIN":
        dibujo.texto(pantalla, "Rol confirmado. Esperando que el Host inicie...", POS_INICIAR,
                     COLOR_ESPERANDO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    # Grafo de sala (mini visualización de la estructura de datos).
    _dibujar_grafo_sala(pantalla, sala, 640, 540)

    if aviso:
        dibujo.texto(pantalla, aviso, POS_AVISO, assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="center")


def _dibujar_grafo_sala(pantalla, sala, cx, cy):
    """Dibuja una mini-visualización del grafo de sala: nodos = jugadores,
    aristas = conexiones. Puramente decorativo pero muestra la ED en uso."""
    jugadores = sala.jugadores()
    if len(jugadores) < 2:
        # Solo un nodo.
        if jugadores:
            pygame.draw.circle(pantalla, COLOR_ONLINE, (cx, cy), 8)
            dibujo.texto(pantalla, f"J{jugadores[0]+1}", (cx, cy + 16),
                         assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        dibujo.texto(pantalla, "Grafo de sala: 1 nodo, 0 aristas", (cx, cy + 36),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        return

    # Dos nodos con una arista.
    sep = 100
    p1 = (cx - sep // 2, cy)
    p2 = (cx + sep // 2, cy)
    pygame.draw.line(pantalla, assets.COLOR_BORDE_PANEL, p1, p2, 2)
    pygame.draw.circle(pantalla, COLOR_ONLINE, p1, 8)
    pygame.draw.circle(pantalla, assets.COLOR_AMARILLO, p2, 8)
    for i, (px, py) in enumerate((p1, p2)):
        jid = jugadores[i] if i < len(jugadores) else i
        dibujo.texto(pantalla, f"J{jid+1}", (px, py + 16),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

    dibujo.texto(pantalla, f"Grafo de sala: {len(jugadores)} nodos, "
                 f"{len(jugadores) * (len(jugadores)-1) // 2} aristas",
                 (cx, cy + 36), assets.COLOR_TEXTO_APAGADO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="center")


def menu_online(pantalla, reloj, presentar, clases_rol):
    """Flujo completo del modo Online:
    1. Elige entre Crear Sala (Host) o Unirse (Join).
    2. Entra al lobby correspondiente (selección de rol y conexión).
    Retorna (clases, conexion, es_host) o 'volver' o None si se cierra.
    """
    while True:
        opcion = pantalla_elegir_modo_online(pantalla, reloj, presentar)
        if opcion is None or opcion == "volver":
            return opcion
        if opcion == "host":
            res = pantalla_lobby_host(pantalla, reloj, presentar, clases_rol)
            if res is None:
                return None
            if res == "volver":
                continue
            clases, servidor = res
            return clases, servidor, True
        elif opcion == "join":
            res = pantalla_lobby_join(pantalla, reloj, presentar, clases_rol)
            if res is None:
                return None
            if res == "volver":
                continue
            clases, cliente = res
            return clases, cliente, False

