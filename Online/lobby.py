"""Pantalla de Lobby Interactivo del modo Online (estilo sala de espera Among Us).

Características:
    1. Sala física interactiva para hasta 4 jugadores simultáneos.
    2. Los jugadores se mueven libremente por la sala con WASD o flechas.
    3. Laptop central interactiva y atajos [1-4] para seleccionar personaje.
    4. Panel lateral con la IP de la sala, capacidad (X/4) y latencia.
    5. Radar en tiempo real con el Grafo de Sala (GrafoSala de Estructura de Datos 2).
    6. Botón central de inicio: requiere mínimo 2 jugadores y solo el Host puede iniciar.
"""

import math
import time
import pygame

from src.core import assets
from src.core.config import FPS
from src.ui import dibujo, hud, sprites

from Online.servidor import Servidor, PUERTO_DEFAULT, MAX_JUGADORES
from Online.cliente import Cliente
from Online.protocolo import (
    ROLES, GrafoSala, ELEGIR_ROL, INICIAR, LOBBY, ESTADO, POSICION_LOBBY,
    msg_elegir_rol, msg_iniciar, msg_lobby, msg_posicion_lobby,
)

# Colores de la sala y estética retrofuturista
COLOR_ONLINE = (100, 200, 255)
COLOR_ESPERANDO = (150, 150, 185)
COLOR_CONECTADO = assets.COLOR_TEAL
COLOR_IP = assets.COLOR_AMARILLO
COLOR_PISO_A = (18, 16, 36)
COLOR_PISO_B = (24, 22, 46)
COLOR_REJILLA = (36, 32, 64)
COLOR_MURO_LOBBY = (32, 28, 56)
COLOR_BORDE_NEON = (70, 190, 240)
COLOR_CAJA = (44, 40, 72)
COLOR_CAJA_BORDE = (90, 84, 140)

# Mapeo de nombres de rol a sus identificadores de sprite y colores
ROLES_INFO = {
    "Ciudadano": {"color": assets.COLOR_CIUDADANO, "rol": "ciudadano", "desc": "Disparo en abanico"},
    "Influencer": {"color": assets.COLOR_INFLUENCER, "rol": "influencer", "desc": "Ondas sónicas y empuje"},
    "Periodista": {"color": assets.COLOR_PERIODISTA, "rol": "periodista", "desc": "Rayo láser perforante"},
    "Candidato": {"color": assets.COLOR_CANDIDATO, "rol": "candidato", "desc": "Aura protectora"},
}

# Límites de la sala de espera
SALA_RECT = pygame.Rect(70, 50, 870, 590)

# Obstáculos en la sala (colisión para los jugadores)
OBSTACULOS = [
    pygame.Rect(455, 230, 100, 70),   # Laptop Central
    pygame.Rect(140, 140, 90, 70),    # Caja superior izquierda
    pygame.Rect(760, 140, 90, 70),    # Caja superior derecha
    pygame.Rect(140, 480, 90, 70),    # Caja inferior izquierda
    pygame.Rect(760, 480, 90, 70),    # Caja inferior derecha
]

# Puntos de aparición por jugador (0=Host, 1, 2, 3)
SPAWNS = [
    (505, 360),
    (610, 360),
    (430, 430),
    (680, 430),
]


def pantalla_elegir_modo_online(pantalla, reloj, presentar):
    """Sub-pantalla donde se elige HOST (Crear sala) o JOIN (Unirse)."""
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

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, "Modo Online", (640, 50), COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, "¿Cómo quieres jugar hoy?", (640, 90),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        # Tarjeta HOST
        rect_host = pygame.Rect(250, 160, 320, 370)
        sel_h = indice == 0
        color_h = COLOR_ONLINE if sel_h else assets.COLOR_BORDE_CHIP
        dibujo.panel(pantalla, rect_host, assets.COLOR_FONDO_PANEL, color_h,
                     assets.GROSOR_TARJETA_RESALTADA if sel_h else 1, radio=12)
        dibujo.chip(pantalla, "1", (rect_host.left + 20, rect_host.top + 18), color_h,
                    assets.COLOR_FONDO, color_h, assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        img = sprites.sprite_jugador(COLOR_ONLINE, escala=5, rol="ciudadano")
        pantalla.blit(img, img.get_rect(midtop=(rect_host.centerx, rect_host.top + 60)))
        dibujo.texto(pantalla, "Crear sala (Host)", (rect_host.centerx, rect_host.top + 200),
                     assets.COLOR_TEXTO_HUD if sel_h else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Tú eres el anfitrión", (rect_host.centerx, rect_host.top + 236),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Hasta 4 jugadores (2 mín)", (rect_host.centerx, rect_host.top + 264),
                     assets.COLOR_TEAL, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Inicia la partida cuando estén listos", (rect_host.centerx, rect_host.top + 292),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

        # Tarjeta JOIN
        rect_join = pygame.Rect(710, 160, 320, 370)
        sel_j = indice == 1
        color_j = COLOR_ONLINE if sel_j else assets.COLOR_BORDE_CHIP
        dibujo.panel(pantalla, rect_join, assets.COLOR_FONDO_PANEL, color_j,
                     assets.GROSOR_TARJETA_RESALTADA if sel_j else 1, radio=12)
        dibujo.chip(pantalla, "2", (rect_join.left + 20, rect_join.top + 18), color_j,
                    assets.COLOR_FONDO, color_j, assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        img2 = sprites.sprite_jugador(assets.COLOR_INFLUENCER, escala=5, rol="influencer")
        pantalla.blit(img2, img2.get_rect(midtop=(rect_join.centerx, rect_join.top + 60)))
        dibujo.texto(pantalla, "Unirse a sala (Join)", (rect_join.centerx, rect_join.top + 200),
                     assets.COLOR_TEXTO_HUD if sel_j else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Ingresa la IP del Host", (rect_join.centerx, rect_join.top + 236),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Misma red Wi-Fi o 127.0.0.1", (rect_join.centerx, rect_join.top + 264),
                     assets.COLOR_TEAL, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Espera a que el anfitrión inicie", (rect_join.centerx, rect_join.top + 292),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

        hud.dibujar_barra_controles(pantalla,
                                    [("← →", "elegir"), ("1-2", "directo"),
                                     ("Enter", "confirmar"), ("Esc", "volver")])
        presentar()
        reloj.tick(FPS)


def _pantalla_ingresar_ip(pantalla, reloj, presentar):
    """Pantalla para ingresar la IP del Host."""
    ip_texto = ""
    cursor_visible = True
    cursor_timer = 0.0
    while True:
        dt = reloj.tick(FPS) / 1000
        cursor_timer += dt
        if cursor_timer >= 0.45:
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
                    if char and (char.isdigit() or char == "." or char == ":"):
                        ip_texto += char

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, "Modo Online", (640, 70), COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Ingresa la IP de la sala del Host:", (640, 240),
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, ancla="center")

        rect_input = pygame.Rect(400, 310, 480, 56)
        dibujo.panel(pantalla, rect_input, assets.COLOR_FONDO_PANEL, COLOR_ONLINE, 2, radio=8)
        mostrar = (ip_texto if ip_texto else "Ej: 192.168.1.15 o 127.0.0.1")
        color_texto = assets.COLOR_TEXTO_HUD if ip_texto else assets.COLOR_TEXTO_APAGADO
        cursor = "|" if (cursor_visible and ip_texto) else ""
        dibujo.texto(pantalla, ip_texto + cursor if ip_texto else mostrar,
                     (rect_input.left + 18, rect_input.centery),
                     color_texto, assets.TAMANIO_FUENTE_TITULO, ancla="midleft")

        dibujo.texto(pantalla, "Si juegas en la misma PC usa: 127.0.0.1", (640, 400),
                     assets.COLOR_TEAL, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Presiona Enter para conectar", (640, 434),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

        hud.dibujar_barra_controles(pantalla,
                                    [("0-9 y .", "escribir IP"), ("Enter", "conectar"), ("Esc", "volver")])
        presentar()


def _pantalla_error(pantalla, reloj, presentar, mensaje):
    """Muestra un modal de error y retorna 'volver'."""
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    return "volver"

        pantalla.fill(assets.COLOR_FONDO)
        dibujo.texto(pantalla, "Error de Conexión", (640, 280), assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, str(mensaje), (640, 340), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        dibujo.texto(pantalla, "Presiona Enter o Esc para volver", (640, 420),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        presentar()
        reloj.tick(FPS)


# =========================================================================
# Sala de Espera Interactiva (Estilo Among Us)
# =========================================================================

def pantalla_sala_espera(pantalla, reloj, presentar, clases_rol, es_host, conexion, ip):
    """Lobby interactivo tipo Among Us para hasta 4 jugadores simultáneos.

    Retorna (clases_elegidas, conexion, es_host) o 'volver' o None.
    """
    id_local = 0 if es_host else (conexion.id_jugador if conexion.id_jugador is not None else 1)
    spawn = SPAWNS[id_local % len(SPAWNS)]
    pos_x, pos_y = float(spawn[0]), float(spawn[1])

    anim_tiempo = 0.0
    caminando = False
    rol_local = "Ciudadano"  # Por defecto el primer rol
    modal_roles_abierto = False
    indice_rol_selector = 0

    # Registrar el rol inicial
    if es_host:
        conexion.sala.elegir_rol(0, rol_local)
        conexion.posiciones_lobby[0] = (pos_x, pos_y)
    else:
        conexion.enviar_rol(rol_local)
        conexion.enviar_posicion_lobby(pos_x, pos_y)

    timer_pos_red = 0.0
    aviso_temporal = ""
    aviso_timer = 0.0

    while True:
        dt = reloj.tick(FPS) / 1000
        anim_tiempo += dt
        timer_pos_red += dt
        aviso_timer = max(0.0, aviso_timer - dt)

        # 1. Procesar mensajes de red
        if es_host:
            for msg in conexion.leer_mensajes():
                pass  # El servidor ya actualiza su sala y posiciones internamente
            sala = conexion.sala
            posiciones = dict(conexion.posiciones_lobby)
            posiciones[0] = (pos_x, pos_y)
            latencia = 0
        else:
            for msg in conexion.leer_mensajes():
                tipo = msg.get("tipo")
                if tipo == INICIAR:
                    # El host inició la partida!
                    conexion.iniciado = True
                    clases = _armar_clases_partida(conexion.sala, clases_rol)
                    return clases, conexion, False
            sala = conexion.sala
            id_local = conexion.id_jugador if conexion.id_jugador is not None else 1
            posiciones = dict(conexion.posiciones_lobby)
            posiciones[id_local] = (pos_x, pos_y)
            latencia = conexion.latencia_ms

        jugadores_conectados = sala.jugadores()
        cantidad_conectados = len(jugadores_conectados)

        # 2. Manejo de Eventos
        mouse_pos = pygame.mouse.get_pos()
        rect_boton_inicio = pygame.Rect(320, 576, 370, 50)
        rect_laptop = OBSTACULOS[0]
        cerca_laptop = math.hypot(pos_x - rect_laptop.centerx, pos_y - rect_laptop.centery) < 95

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                conexion.detener()
                return None

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                # Clic en botón de inicio
                if rect_boton_inicio.collidepoint(mouse_pos) and es_host:
                    if cantidad_conectados < 2:
                        aviso_temporal = "¡Se necesitan al menos 2 jugadores para iniciar!"
                        aviso_timer = 2.5
                    elif not sala.todos_listos():
                        aviso_temporal = "¡Todos los jugadores deben elegir su rol!"
                        aviso_timer = 2.5
                    else:
                        # Iniciar partida
                        conexion.enviar_a_todos(msg_iniciar())
                        clases = _armar_clases_partida(sala, clases_rol)
                        return clases, conexion, True

                # Clic en la laptop central
                if rect_laptop.collidepoint(mouse_pos) or cerca_laptop:
                    modal_roles_abierto = not modal_roles_abierto

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    if modal_roles_abierto:
                        modal_roles_abierto = False
                    else:
                        conexion.detener()
                        return "volver"

                # Abrir / cerrar modal de roles
                elif evento.key == pygame.K_e:
                    modal_roles_abierto = not modal_roles_abierto

                # Atajos 1-4 para cambio rápido de personaje
                elif evento.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    idx = evento.key - pygame.K_1
                    if idx < len(ROLES):
                        rol_local = ROLES[idx]
                        indice_rol_selector = idx
                        if es_host:
                            conexion.sala.elegir_rol(0, rol_local)
                            conexion.enviar_a_todos(msg_lobby(conexion.sala.a_dict()))
                        else:
                            conexion.enviar_rol(rol_local)

                # Enter para Iniciar partida (solo Host)
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if modal_roles_abierto:
                        modal_roles_abierto = False
                    elif es_host:
                        if cantidad_conectados < 2:
                            aviso_temporal = "¡Se necesitan al menos 2 jugadores para iniciar!"
                            aviso_timer = 2.5
                        elif not sala.todos_listos():
                            aviso_temporal = "¡Todos los jugadores deben elegir su rol!"
                            aviso_timer = 2.5
                        else:
                            conexion.enviar_a_todos(msg_iniciar())
                            clases = _armar_clases_partida(sala, clases_rol)
                            return clases, conexion, True

                # Navegar modal de roles con flechas si está abierto
                if modal_roles_abierto:
                    if evento.key in (pygame.K_LEFT, pygame.K_a):
                        indice_rol_selector = (indice_rol_selector - 1) % len(ROLES)
                        rol_local = ROLES[indice_rol_selector]
                        _actualizar_rol(es_host, conexion, id_local, rol_local)
                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                        indice_rol_selector = (indice_rol_selector + 1) % len(ROLES)
                        rol_local = ROLES[indice_rol_selector]
                        _actualizar_rol(es_host, conexion, id_local, rol_local)

        # 3. Movimiento del jugador local
        if not modal_roles_abierto:
            teclas = pygame.key.get_pressed()
            dx, dy = 0.0, 0.0
            if teclas[pygame.K_w] or teclas[pygame.K_UP]:
                dy -= 1.0
            if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
                dy += 1.0
            if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
                dx -= 1.0
            if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
                dx += 1.0

            if dx != 0 or dy != 0:
                dist = math.hypot(dx, dy)
                dx, dy = dx / dist, dy / dist
                velocidad = 230 * dt
                nx = pos_x + dx * velocidad
                ny = pos_y + dy * velocidad

                # Colisión con límites de la sala
                rect_jugador = pygame.Rect(nx - 16, ny - 16, 32, 32)
                colisiona = False
                if not SALA_RECT.inflate(-40, -40).contains(rect_jugador):
                    colisiona = True
                for obs in OBSTACULOS:
                    if obs.colliderect(rect_jugador):
                        colisiona = True
                        break

                if not colisiona:
                    pos_x, pos_y = nx, ny
                caminando = True
            else:
                caminando = False
        else:
            caminando = False

        # Transmisión periódica de posición en el lobby (~25 Hz)
        if timer_pos_red >= 0.04:
            timer_pos_red = 0.0
            if es_host:
                conexion.posiciones_lobby[0] = (pos_x, pos_y)
                conexion.enviar_a_todos(msg_posicion_lobby(0, pos_x, pos_y))
            else:
                conexion.enviar_posicion_lobby(pos_x, pos_y)

        # 4. Renderizado Completo
        pantalla.fill(assets.COLOR_FONDO)

        # Dibujar la Sala de Espera (Búnker / Nave estilo Among Us)
        _dibujar_escenario_lobby(pantalla, anim_tiempo, cerca_laptop)

        # Dibujar a los jugadores presentes en la sala
        _dibujar_jugadores_lobby(pantalla, sala, posiciones, id_local,
                                anim_tiempo, caminando, rol_local, pos_x, pos_y)

        # Dibujar el Botón de Inicio Central (Among Us Style)
        _dibujar_boton_inicio(pantalla, rect_boton_inicio, es_host, cantidad_conectados,
                              sala.todos_listos(), aviso_temporal if aviso_timer > 0 else "")

        # Dibujar el Panel Lateral de Información de Sala
        _dibujar_panel_sala(pantalla, ip, conexion.puerto if es_host else PUERTO_DEFAULT,
                            cantidad_conectados, es_host, latencia)

        # Dibujar el Radar del Grafo de Sala (Estructuras de Datos 2)
        _dibujar_radar_grafo(pantalla, sala)

        # Modal de Selección de Rol (si está abierto)
        if modal_roles_abierto:
            _dibujar_modal_roles(pantalla, indice_rol_selector, rol_local)

        # Barra de Controles inferior
        hud.dibujar_barra_controles(pantalla, [
            ("WASD / Flechas", "caminar"),
            ("E / 1-4", "personalizar rol"),
            ("Enter", "iniciar partida" if es_host else "esperar"),
            ("Esc", "salir"),
        ])

        presentar()


def _actualizar_rol(es_host, conexion, id_local, nuevo_rol):
    """Actualiza y sincroniza el rol seleccionado."""
    if es_host:
        conexion.sala.elegir_rol(0, nuevo_rol)
        conexion.enviar_a_todos(msg_lobby(conexion.sala.a_dict()))
    else:
        conexion.enviar_rol(nuevo_rol)


def _armar_clases_partida(sala, clases_rol):
    """Retorna la lista de clases en orden de ID de los jugadores conectados."""
    clases = []
    for jid in sala.jugadores():
        rol_nom = sala.rol_de(jid)
        idx = ROLES.index(rol_nom) if (rol_nom and rol_nom in ROLES) else 0
        clases.append(clases_rol[idx])
    return clases


# =========================================================================
# Renderizado del Escenario de Espera (Estilo Among Us)
# =========================================================================

def _dibujar_escenario_lobby(pantalla, tiempo, cerca_laptop):
    """Dibuja la habitación de la nave/búnker con piso texturizado y props."""
    # Piso metálico con cuadrícula
    dibujo.panel(pantalla, SALA_RECT, COLOR_PISO_A, COLOR_MURO_LOBBY, grosor=8, radio=16)

    # Baldosas interiores
    tile_size = 50
    for x in range(SALA_RECT.left + 15, SALA_RECT.right - 15, tile_size):
        for y in range(SALA_RECT.top + 15, SALA_RECT.bottom - 15, tile_size):
            paridad = ((x // tile_size) + (y // tile_size)) % 2 == 0
            color_baldosa = COLOR_PISO_B if paridad else COLOR_PISO_A
            pygame.draw.rect(pantalla, color_baldosa, (x, y, tile_size - 2, tile_size - 2))

    # Borde de neón cian en las paredes (estilo futurista)
    pygame.draw.rect(pantalla, COLOR_BORDE_NEON, SALA_RECT.inflate(-8, -8), 2, border_radius=14)

    # Compuerta superior (airlock como en Among Us)
    puerta_rect = pygame.Rect(435, SALA_RECT.top - 4, 140, 24)
    dibujo.panel(pantalla, puerta_rect, (60, 54, 90), COLOR_BORDE_NEON, grosor=2, radio=4)
    # Luces rojas/verdes de la compuerta
    luz_color = assets.COLOR_TEAL if math.sin(tiempo * 4) > 0 else (20, 100, 100)
    pygame.draw.circle(pantalla, luz_color, (puerta_rect.centerx - 25, puerta_rect.centery), 4)
    pygame.draw.circle(pantalla, luz_color, (puerta_rect.centerx + 25, puerta_rect.centery), 4)
    dibujo.texto(pantalla, "AIRLOCK 01", (puerta_rect.centerx, puerta_rect.centery + 12),
                 assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MINI, ancla="center")

    # Cajas metálicas de carga
    for i, caja in enumerate(OBSTACULOS[1:]):
        dibujo.panel(pantalla, caja, COLOR_CAJA, COLOR_CAJA_BORDE, grosor=2, radio=6)
        # Línea de detalle militar
        pygame.draw.line(pantalla, COLOR_CAJA_BORDE, (caja.left + 10, caja.centery), (caja.right - 10, caja.centery), 2)
        dibujo.texto(pantalla, f"CARGO-0{i+1}", (caja.centerx, caja.centery - 12),
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MINI, ancla="center")

    # Laptop Central (Estación de Personalización de Rol)
    laptop_rect = OBSTACULOS[0]
    # Aura pulsante si estás cerca
    if cerca_laptop:
        pulso = int(25 + 15 * math.sin(tiempo * 8))
        dibujo.panel_alfa(pantalla, laptop_rect.inflate(20, 20), COLOR_ONLINE + (pulso,), radio=12)

    dibujo.panel(pantalla, laptop_rect, (28, 24, 52),
                 COLOR_ONLINE if cerca_laptop else assets.COLOR_BORDE_CHIP,
                 grosor=3 if cerca_laptop else 1, radio=8)

    # Pantalla brillante de la laptop
    pantalla_lap = pygame.Rect(laptop_rect.left + 16, laptop_rect.top + 12, 68, 44)
    color_pantalla = (50, 160, 230) if math.sin(tiempo * 5) > -0.7 else (30, 90, 140)
    pygame.draw.rect(pantalla, color_pantalla, pantalla_lap, border_radius=4)
    dibujo.texto(pantalla, "CUSTOMIZE", (pantalla_lap.centerx, pantalla_lap.centery),
                 (255, 255, 255), assets.TAMANIO_FUENTE_MINI, negrita=True, ancla="center")

    # Badge flotante si estás cerca
    if cerca_laptop:
        y_flotante = laptop_rect.top - 24 + math.sin(tiempo * 6) * 3
        dibujo.chip(pantalla, "Presiona [E] o Click: Elegir Rol",
                    (laptop_rect.centerx, y_flotante), assets.COLOR_TEXTO_HUD,
                    (20, 40, 60), COLOR_ONLINE, assets.TAMANIO_FUENTE_PEQUENA, ancla="center", alto=26)


def _dibujar_jugadores_lobby(pantalla, sala, posiciones, id_local,
                             tiempo, caminando, rol_local, local_x, local_y):
    """Dibuja los avatares de todos los jugadores conectados caminando en la sala."""
    jugadores = sala.jugadores()
    for jid in jugadores:
        if jid == id_local:
            px, py = local_x, local_y
            rol = rol_local
            anim_cam = caminando
        else:
            px, py = posiciones.get(jid, SPAWNS[jid % len(SPAWNS)])
            rol = sala.rol_de(jid) or "Ciudadano"
            anim_cam = False

        info = ROLES_INFO.get(rol, ROLES_INFO["Ciudadano"])
        color_rol = info["color"]
        rol_clave = info["rol"]

        # Sombra en los pies
        sombra_rect = pygame.Rect(0, 0, 44, 14)
        sombra_rect.center = (int(px), int(py + 26))
        dibujo.panel_alfa(pantalla, sombra_rect, (0, 0, 0, 110), radio=7)

        # Muñeco animado
        img = sprites.sprite_jugador(color_rol, escala=4, rol=rol_clave,
                                     tiempo=tiempo, caminando=anim_cam)
        img_rect = img.get_rect(center=(int(px), int(py)))
        pantalla.blit(img, img_rect)

        # Indicador para el jugador local (flechita / etiqueta tú)
        es_yo = (jid == id_local)
        es_host_j = (jid == 0)

        # Etiqueta de Nombre
        if es_host_j:
            nombre = f"HOST (J1)" + (" (Tú)" if es_yo else "")
            color_tag = COLOR_ONLINE
        else:
            nombre = f"J{jid + 1}" + (" (Tú)" if es_yo else "")
            color_tag = assets.COLOR_AMARILLO if es_yo else assets.COLOR_TEXTO_HUD

        dibujo.texto(pantalla, nombre, (int(px), int(py - 38)), color_tag,
                     assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")

        # Chip del Rol
        dibujo.chip(pantalla, rol, (int(px), int(py - 22)),
                    color_rol, (16, 14, 30), color_rol,
                    assets.TAMANIO_FUENTE_MINI, ancla="center", alto=18, margen=6)


def _dibujar_boton_inicio(pantalla, rect, es_host, cantidad, todos_listos, aviso):
    """Dibuja el botón/panel de inicio estilo Among Us."""
    if cantidad < 2:
        # Menos de 2 jugadores: Esperando jugadores
        dibujo.panel(pantalla, rect, (26, 24, 44), (70, 66, 100), grosor=1, radio=8)
        dibujo.texto(pantalla, f"WAITING FOR PLAYERS ({cantidad}/4)",
                     (rect.centerx, rect.centery - 6), COLOR_ESPERANDO,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Se necesitan mínimo 2 jugadores para iniciar",
                     (rect.centerx, rect.centery + 12), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_MINI, ancla="center")
    elif es_host:
        if todos_listos:
            # Listo para arrancar (Host)
            dibujo.panel(pantalla, rect, (16, 60, 48), COLOR_CONECTADO, grosor=2, radio=8)
            dibujo.texto(pantalla, "▶ START / INICIAR PARTIDA (Enter)",
                         (rect.centerx, rect.centery - 6), (255, 255, 255),
                         assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
            dibujo.texto(pantalla, "Todos listos. Presiona Enter o haz click aquí",
                         (rect.centerx, rect.centery + 14), COLOR_CONECTADO,
                         assets.TAMANIO_FUENTE_MINI, ancla="center")
        else:
            dibujo.panel(pantalla, rect, (48, 40, 20), assets.COLOR_AMARILLO, grosor=1, radio=8)
            dibujo.texto(pantalla, "ESPERANDO QUE ELIJAN ROL...",
                         (rect.centerx, rect.centery - 6), assets.COLOR_AMARILLO,
                         assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
            dibujo.texto(pantalla, "Todos deben seleccionar personaje",
                         (rect.centerx, rect.centery + 12), assets.COLOR_TEXTO_APAGADO,
                         assets.TAMANIO_FUENTE_MINI, ancla="center")
    else:
        # Invitado
        dibujo.panel(pantalla, rect, (24, 30, 60), COLOR_ONLINE, grosor=1, radio=8)
        dibujo.texto(pantalla, "ESPERANDO A QUE EL HOST INICIE...",
                     (rect.centerx, rect.centery - 6), COLOR_ONLINE,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Estás listo. El anfitrión iniciará la partida",
                     (rect.centerx, rect.centery + 12), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_MINI, ancla="center")

    if aviso:
        dibujo.texto(pantalla, aviso, (rect.centerx, rect.bottom + 14),
                     assets.COLOR_MAGENTA, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")


def _dibujar_panel_sala(pantalla, ip, puerto, cantidad, es_host, latencia):
    """Panel lateral derecho estilo Among Us con los ajustes de la sala."""
    rect = pygame.Rect(960, 50, 260, 275)
    dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, COLOR_ONLINE, grosor=2, radio=12)

    dibujo.texto(pantalla, "ROOM SETTINGS", (rect.centerx, rect.top + 16),
                 COLOR_ONLINE, assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")

    # IP / Room code
    y = rect.top + 45
    dibujo.texto(pantalla, "IP DE LA SALA:", (rect.left + 16, y),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI)
    y += 18
    ip_rect = pygame.Rect(rect.left + 14, y, rect.width - 28, 38)
    dibujo.panel(pantalla, ip_rect, (14, 20, 36), COLOR_IP, grosor=1, radio=6)
    dibujo.texto(pantalla, f"{ip}:{puerto}", (ip_rect.centerx, ip_rect.centery),
                 COLOR_IP, assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")

    # Capacidad (X/4)
    y += 48
    dibujo.texto(pantalla, "CAPACIDAD:", (rect.left + 16, y),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, f"👤 {cantidad} / 4", (rect.right - 16, y),
                 COLOR_CONECTADO if cantidad >= 2 else assets.COLOR_MAGENTA,
                 assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="topright")

    # Slots visuales
    y += 28
    slot_w = 48
    for i in range(4):
        sx = rect.left + 18 + i * (slot_w + 10)
        activo = i < cantidad
        c_slot = COLOR_CONECTADO if activo else (36, 34, 56)
        pygame.draw.rect(pantalla, c_slot, (sx, y, slot_w, 8), border_radius=3)

    # Red y Host
    y += 20
    dibujo.texto(pantalla, "RED: LAN / Wi-Fi Privada", (rect.left + 16, y),
                 assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MINI)
    y += 18
    dibujo.texto(pantalla, f"ROL: {'HOST (Creador)' if es_host else 'INVITADO'}", (rect.left + 16, y),
                 COLOR_ONLINE, assets.TAMANIO_FUENTE_MINI, negrita=True)
    y += 18
    dibujo.texto(pantalla, f"PING: {latencia} ms", (rect.left + 16, y),
                 COLOR_CONECTADO, assets.TAMANIO_FUENTE_MINI)


def _dibujar_radar_grafo(pantalla, sala):
    """Panel lateral inferior con la visualización del Grafo de Sala (ED2)."""
    rect = pygame.Rect(960, 340, 260, 300)
    dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_CHIP, grosor=1, radio=12)

    dibujo.texto(pantalla, "ESTRUCTURA DE DATOS", (rect.centerx, rect.top + 14),
                 assets.COLOR_AMARILLO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
    dibujo.texto(pantalla, "Grafo de Sala (GrafoSala)", (rect.centerx, rect.top + 32),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI, ancla="center")

    # Dibujo del Grafo en el radar
    centro_grafo = (rect.centerx, rect.top + 130)
    radio = 55
    jugadores = sala.jugadores()
    n = len(jugadores)

    # Coordenadas de los vértices
    pos_nodos = {}
    if n == 1:
        pos_nodos[jugadores[0]] = centro_grafo
    else:
        for i, jid in enumerate(jugadores):
            ang = 2 * math.pi * i / n - math.pi / 2
            pos_nodos[jid] = (int(centro_grafo[0] + radio * math.cos(ang)),
                              int(centro_grafo[1] + radio * math.sin(ang)))

    # Dibujar Aristas entre todos los pares conectados
    for i, a in enumerate(jugadores):
        for b in jugadores[i + 1:]:
            p1 = pos_nodos[a]
            p2 = pos_nodos[b]
            pygame.draw.line(pantalla, COLOR_ONLINE, p1, p2, 2)

    # Dibujar Nodos (Vértices)
    for jid, pos in pos_nodos.items():
        rol_nom = sala.rol_de(jid) or "Ciudadano"
        color_vertice = ROLES_INFO.get(rol_nom, ROLES_INFO["Ciudadano"])["color"]
        pygame.draw.circle(pantalla, (20, 18, 36), pos, 14)
        pygame.draw.circle(pantalla, color_vertice, pos, 12)
        dibujo.texto(pantalla, f"J{jid+1}", pos, (255, 255, 255),
                     assets.TAMANIO_FUENTE_MINI, negrita=True, ancla="center")

    # Métricas del Grafo
    aristas = n * (n - 1) // 2
    y = rect.top + 215
    dibujo.texto(pantalla, f"Vértices (Jugadores): {n}", (rect.left + 16, y),
                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MINI)
    y += 18
    dibujo.texto(pantalla, f"Aristas (Canales TCP): {aristas}", (rect.left + 16, y),
                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MINI)
    y += 18
    dibujo.texto(pantalla, f"Topología: Grafo Completo K_{n}", (rect.left + 16, y),
                 COLOR_ONLINE, assets.TAMANIO_FUENTE_MINI)


def _dibujar_modal_roles(pantalla, indice_sel, rol_actual):
    """Modal emergente para personalizar el rol al usar la laptop."""
    # Fondo oscurecido
    dibujo.panel_alfa(pantalla, (0, 0, 1280, 720), (10, 8, 20, 190), radio=0)

    rect_modal = pygame.Rect(180, 130, 920, 460)
    dibujo.panel(pantalla, rect_modal, assets.COLOR_FONDO_PANEL, COLOR_ONLINE, grosor=3, radio=16)

    dibujo.texto(pantalla, "PERSONALIZAR PERSONAJE", (rect_modal.centerx, rect_modal.top + 22),
                 COLOR_ONLINE, assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
    dibujo.texto(pantalla, "Selecciona tu clase con las teclas 1-4, flechas o clic:",
                 (rect_modal.centerx, rect_modal.top + 56), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    w_card = 195
    h_card = 310
    inicio_x = rect_modal.left + 35

    for i, nombre_rol in enumerate(ROLES):
        rx = inicio_x + i * (w_card + 18)
        rc = pygame.Rect(rx, rect_modal.top + 95, w_card, h_card)

        es_elegido = (nombre_rol == rol_actual)
        info = ROLES_INFO[nombre_rol]
        color = info["color"]

        dibujo.panel(pantalla, rc, assets.COLOR_FONDO, color if es_elegido else assets.COLOR_BORDE_CHIP,
                     grosor=3 if es_elegido else 1, radio=10)

        # Número de atajo
        dibujo.chip(pantalla, str(i + 1), (rc.left + 10, rc.top + 10),
                    color, assets.COLOR_FONDO, color, assets.TAMANIO_FUENTE_PEQUENA, alto=24, margen=8)

        # Sprite del personaje
        img = sprites.sprite_jugador(color, escala=4, rol=info["rol"])
        pantalla.blit(img, img.get_rect(midtop=(rc.centerx, rc.top + 45)))

        # Nombre y descripción
        dibujo.texto(pantalla, nombre_rol, (rc.centerx, rc.top + 175),
                     color if es_elegido else assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        dibujo.texto(pantalla, info["desc"], (rc.centerx, rc.top + 215),
                     assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI, ancla="center")

        # Botón / estado
        if es_elegido:
            dibujo.chip(pantalla, "SELECCIONADO", (rc.centerx, rc.bottom - 22),
                        assets.COLOR_FONDO, color, color,
                        assets.TAMANIO_FUENTE_PEQUENA, ancla="center", alto=26, margen=10)
        else:
            dibujo.chip(pantalla, f"Tecla [{i+1}]", (rc.centerx, rc.bottom - 22),
                        assets.COLOR_TEXTO_APAGADO, assets.COLOR_FONDO_CHIP, assets.COLOR_BORDE_CHIP,
                        assets.TAMANIO_FUENTE_PEQUENA, ancla="center", alto=26, margen=10)

    dibujo.texto(pantalla, "Presiona [E] o [Esc] para cerrar", (rect_modal.centerx, rect_modal.bottom - 20),
                 assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")


# =========================================================================
# Flujo Principal Integrador
# =========================================================================

def menu_online(pantalla, reloj, presentar, clases_rol):
    """Flujo completo del modo Online:
    1. Elige entre Crear Sala (Host) o Unirse (Join).
    2. Entra a la Sala de Espera interactiva tipo Among Us.
    Retorna (clases, conexion, es_host) o 'volver' o None.
    """
    while True:
        opcion = pantalla_elegir_modo_online(pantalla, reloj, presentar)
        if opcion is None or opcion == "volver":
            return opcion

        if opcion == "host":
            servidor = Servidor()
            ip = servidor.iniciar(PUERTO_DEFAULT)
            if ip is None:
                _pantalla_error(pantalla, reloj, presentar, servidor.error)
                continue

            res = pantalla_sala_espera(pantalla, reloj, presentar, clases_rol,
                                       es_host=True, conexion=servidor, ip=ip)
            if res is None:
                servidor.detener()
                return None
            if res == "volver":
                servidor.detener()
                continue
            return res

        elif opcion == "join":
            ip = _pantalla_ingresar_ip(pantalla, reloj, presentar)
            if ip is None:
                return None
            if ip == "volver":
                continue

            cliente = Cliente()
            if not cliente.conectar(ip, PUERTO_DEFAULT):
                _pantalla_error(pantalla, reloj, presentar, cliente.error)
                continue

            # Esperar bienvenida inicial
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
                dibujo.texto(pantalla, "Conectando a la sala...", (640, 360), COLOR_ONLINE,
                             assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
                presentar()

            if esperando:
                cliente.desconectar()
                _pantalla_error(pantalla, reloj, presentar, "Tiempo de espera de conexión agotado")
                continue

            res = pantalla_sala_espera(pantalla, reloj, presentar, clases_rol,
                                       es_host=False, conexion=cliente, ip=ip)
            if res is None:
                cliente.desconectar()
                return None
            if res == "volver":
                cliente.desconectar()
                continue
            return res
