"""Paquete de multijugador en red para Civitas.

Arquitectura cliente-servidor sobre sockets TCP (librería estándar de
Python, sin dependencias externas). El host corre el servidor y un
cliente local; el invitado se conecta con la IP del host.

Módulos:
    protocolo   — formato de mensajes y serialización (grafo de red)
    servidor    — acepta conexiones, retransmite estado
    cliente     — se conecta al servidor, envía input, recibe estado
    lobby       — pantalla de lobby (host/join) con Pygame
    sesion_red  — adaptador que conecta el juego existente con la red
"""
