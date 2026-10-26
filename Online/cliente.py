"""Cliente TCP para el multijugador en red de Civitas.

Se conecta al servidor (host) por IP y puerto. Envía el input del
jugador local y recibe el estado del juego. La comunicación usa el
mismo protocolo basado en JSON con header de longitud de 4 bytes
(Online/protocolo.py).

Flujo:
    1. conectar(ip, puerto) → abre socket TCP al servidor.
    2. Envía HOLA → recibe BIENVENIDA con su id y el lobby.
    3. Elige rol (ELEGIR_ROL) → recibe LOBBY actualizado.
    4. Recibe INICIAR → la partida empieza.
    5. Cada frame envía INPUT y recibe ESTADO.

La lectura del socket es no bloqueante para no pausar el loop de Pygame.
"""

import socket
import threading
import time

from Online.protocolo import (
    BIENVENIDA, DESCONEXION, ESTADO, GrafoSala, INICIAR, LOBBY, PONG,
    POSICION_LOBBY, deserializar_buffer, msg_elegir_rol, msg_hola,
    msg_input, msg_ping, msg_posicion_lobby,
)

BUFFER_SIZE = 4096


class Cliente:
    """Cliente TCP que se conecta a una sala existente.

    Atributos públicos (leídos desde el hilo de Pygame):
        id_jugador  — número asignado por el servidor (0=host, 1=invitado)
        sala        — GrafoSala reconstruido del último LOBBY recibido
        iniciado    — True cuando recibe INICIAR
        conectado   — True mientras el socket está abierto
        error       — str con el último error, o None
        mensajes    — cola de mensajes recibidos (list)
        latencia_ms — última latencia medida (ms)
    """

    def __init__(self):
        self.id_jugador = None
        self.sala = GrafoSala()
        self.iniciado = False
        self.conectado = False
        self.error = None
        self.mensajes = []
        self.latencia_ms = 0
        self.posiciones_lobby = {}  # id -> (x, y)
        self._socket = None
        self._hilo = None
        self._cancelar = threading.Event()
        self._lock = threading.Lock()
        self._buffer = b""

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def conectar(self, ip, puerto):
        """Se conecta al servidor. Retorna True si tuvo éxito."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((ip, puerto))
            self._socket.setblocking(False)
            self.conectado = True
        except (OSError, ConnectionRefusedError) as e:
            self.error = f"No se pudo conectar a {ip}:{puerto} — {e}"
            return False

        # Enviar saludo.
        self._enviar(msg_hola("Invitado"))

        # Iniciar hilo de lectura.
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()
        return True

    def desconectar(self):
        """Cierra la conexión."""
        self._cancelar.set()
        self.conectado = False
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

    def enviar_rol(self, rol):
        """Notifica al servidor la elección de rol."""
        self._enviar(msg_elegir_rol(self.id_jugador if self.id_jugador is not None else 1, rol))

    def enviar_posicion_lobby(self, x, y):
        """Envía la posición del jugador en la sala de espera."""
        if self.id_jugador is not None:
            self._enviar(msg_posicion_lobby(self.id_jugador, x, y))

    def enviar_input(self, datos_input):
        """Envía el input de este frame al servidor."""
        self._enviar(msg_input(self.id_jugador if self.id_jugador is not None else 1, datos_input))

    def enviar_ping(self):
        """Envía un ping para medir latencia."""
        self._enviar(msg_ping(time.time() * 1000))

    def leer_mensajes(self):
        """Retorna y vacía la cola de mensajes recibidos."""
        with self._lock:
            msgs = list(self.mensajes)
            self.mensajes.clear()
        return msgs

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _enviar(self, datos_bytes):
        if self._socket and self.conectado:
            try:
                self._socket.sendall(datos_bytes)
            except OSError:
                self.conectado = False

    def _loop(self):
        """Lee mensajes del servidor en un hilo aparte."""
        while not self._cancelar.is_set():
            try:
                datos = self._socket.recv(BUFFER_SIZE)
            except BlockingIOError:
                time.sleep(0.005)
                continue
            except OSError:
                break

            if not datos:
                break

            self._buffer += datos
            mensajes, self._buffer = deserializar_buffer(self._buffer)
            for msg in mensajes:
                self._procesar(msg)

        self.conectado = False

    def _procesar(self, msg):
        tipo = msg.get("tipo")

        if tipo == BIENVENIDA:
            self.id_jugador = msg.get("id", 1)
            self.sala = GrafoSala.de_dict(msg.get("sala", {}))

        elif tipo == LOBBY:
            self.sala = GrafoSala.de_dict(msg.get("sala", {}))

        elif tipo == INICIAR:
            self.iniciado = True

        elif tipo == PONG:
            t_envio = msg.get("t", 0)
            self.latencia_ms = int((time.time() * 1000) - t_envio)

        elif tipo == POSICION_LOBBY:
            jid = msg.get("id")
            if jid is not None and jid != self.id_jugador:
                self.posiciones_lobby[jid] = (msg.get("x", 0), msg.get("y", 0))

        elif tipo == DESCONEXION:
            self.conectado = False

        # Todos los mensajes (incluido ESTADO) van a la cola.
        with self._lock:
            self.mensajes.append(msg)
