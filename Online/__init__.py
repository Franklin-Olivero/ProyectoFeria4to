"""Paquete de multijugador en red para Civitas.

Arquitectura cliente-servidor sobre sockets TCP (librería estándar de
Python, sin dependencias externas). El host corre el servidor y un
cliente local; el invitado se conecta con la IP del host.

Módulos:
    protocolo   — formato de mensajes y serialización (grafo de red)
    servidor    — acepta conexiones, retransmite estado
    cliente     — se conecta al servidor, envía input, recibe estado
    lobby       — pantalla de lobby (host/join) con Pygame
    personalizacion — vestidor del lobby: pestañas COLOR / HAT / SKIN / HAIR / SHIRT / PANTS (puro)
    sala_hotel  — la sala de espera como salón del hotel Backrooms (puro: disposición)
    sala_hotel_render — dibujo del salón con la escena del lobby del hotel
    disposicion_hud — dónde van los botones REPORTAR y SABOTEAR (a la izquierda, puro)
    personalizacion_render — dibujo y ratón del vestidor
    pantalla_rol — revelación de rol al iniciar (impostor o tripulante)
    sabotaje    — bloqueo del sabotaje del impostor en la terminal (puro)
    sabotaje_render — indicador del sabotaje que solo ve el impostor
    reunion     — reunión de emergencia: botón REPORTAR, chat y votación (puro)
    reunion_render — dibujo y ratón de la reunión, los botones REPORTAR y SABOTEAR y el fin de partida
    post_sabotaje — botón SABOTEAR del impostor: publicación viral para todos (puro)
    sesion_red  — adaptador que conecta el juego existente con la red
"""
