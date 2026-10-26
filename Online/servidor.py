"""Servidor TCP para el multijugador en red de Civitas.

El host ejecuta este servidor en un hilo aparte. Acepta exactamente 1
conexión (el invitado) y retransmite mensajes entre ambos. El estado
del lobby se modela con un GrafoSala (Online/protocolo.py), que es un
grafo no dirigido donde cada nodo = jugador y cada arista = conexión
activa en la sala.

Flujo:
    1. El host llama a iniciar(puerto) → abre socket, escucha.
    2. El invitado se conecta → el servidor le envía BIENVENIDA con su
       id y el estado del lobby.
    3. Ambos eligen rol (ELEGIR_ROL) → el servidor actualiza el grafo
       y reenvía LOBBY a todos.
    4. El host envía INICIAR → el servidor lo reenvía al invitado.
    5. Durante la partida: cada INPUT del invitado se reenvía al host,
       cada ESTADO del host se reenvía al invitado.

Complejidad:
    - Aceptar conexión: O(1)
    - Procesar mensaje: O(n) donde n = tamaño del mensaje
    - Broadcast a k clientes: O(k × n) — con k=1 es O(n)
"""

import socket
import threading
import time

from Online.protocolo import (
    BIENVENIDA, DESCONEXION, ELEGIR_ROL, ESTADO, HOLA, INICIAR, INPUT,
    LOBBY, PING, PONG, GrafoSala, deserializar_buffer, msg_bienvenida,
    msg_desconexion, msg_lobby, msg_pong, serializar, crear_mensaje,
)

# Puerto por defecto para la sala.
PUERTO_DEFAULT = 7777
BACKLOG = 1  # solo 1 invitado en esta versión
BUFFER_SIZE = 4096
TIMEOUT_ACEPTAR = 0.5  # segundos entre checks de cancelación


class Servidor:
    """Servidor TCP que gestiona una sala de 2 jugadores.

    Atributos públicos (leídos desde el hilo principal / Pygame):
        sala        — GrafoSala con los jugadores conectados
        iniciado    — True cuando el host envió INICIAR
        error       — str con el último error, o None
        corriendo   — True mientras el servidor acepta conexiones
        mensajes_host — cola de mensajes dirigidos al host (list)
    """

    def __init__(self):
        self.sala = GrafoSala()
        self.iniciado = False
        self.error = None
        self.corriendo = False
        self.mensajes_host = []  # mensajes que el host debe procesar
        self._socket = None
        self._cliente = None  # socket del invitado
        self._hilo = None
        self._cancelar = threading.Event()
        self._lock = threading.Lock()
        self._buffer_cliente = b""

    # ------------------------------------------------------------------
    # API pública (llamada desde el hilo de Pygame)
    # ------------------------------------------------------------------

    def iniciar(self, puerto=PUERTO_DEFAULT):
        """Arranca el servidor en un hilo aparte. Retorna la IP local."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._socket.bind(("0.0.0.0", puerto))
        except OSError as e:
            self.error = f"No se pudo abrir el puerto {puerto}: {e}"
            return None
        self._socket.listen(BACKLOG)
        self._socket.settimeout(TIMEOUT_ACEPTAR)
        self.corriendo = True

        # El host es el jugador 0.
        self.sala.conectar(0)

        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()

        return _ip_local()

    def detener(self):
        """Cierra todo limpiamente."""
        self._cancelar.set()
        self.corriendo = False
        if self._cliente:
            try:
                self._cliente.close()
            except OSError:
                pass
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

    def enviar_a_invitado(self, datos_bytes):
        """Envía bytes crudos al invitado (llamado desde el hilo de Pygame)."""
        if self._cliente:
            try:
                self._cliente.sendall(datos_bytes)
            except OSError:
                self._desconectar_invitado()

    def hay_invitado(self):
        return self._cliente is not None

    def leer_mensajes(self):
        """Retorna y vacía la cola de mensajes para el host."""
        with self._lock:
            msgs = list(self.mensajes_host)
            self.mensajes_host.clear()
        return msgs

    @property
    def puerto(self):
        if self._socket:
            return self._socket.getsockname()[1]
        return None

    # ------------------------------------------------------------------
    # Loop interno (hilo aparte)
    # ------------------------------------------------------------------

    def _loop(self):
        """Espera la conexión del invitado y luego procesa sus mensajes."""
        # Fase 1: esperar al invitado.
        while not self._cancelar.is_set():
            try:
                conn, addr = self._socket.accept()
                conn.setblocking(False)
                self._cliente = conn
                break
            except socket.timeout:
                continue
            except OSError:
                return

        if self._cancelar.is_set():
            return

        # Fase 2: leer mensajes del invitado.
        while not self._cancelar.is_set():
            try:
                datos = self._cliente.recv(BUFFER_SIZE)
            except BlockingIOError:
                time.sleep(0.005)  # ~200 Hz de polling
                continue
            except OSError:
                self._desconectar_invitado()
                break

            if not datos:
                self._desconectar_invitado()
                break

            self._buffer_cliente += datos
            mensajes, self._buffer_cliente = deserializar_buffer(self._buffer_cliente)
            for msg in mensajes:
                self._procesar(msg)

    def _procesar(self, msg):
        """Procesa un mensaje del invitado."""
        tipo = msg.get("tipo")

        if tipo == HOLA:
            # Registrar al invitado (jugador 1) en el grafo de sala.
            self.sala.conectar(1)
            bienvenida = msg_bienvenida(1, self.sala.a_dict())
            self.enviar_a_invitado(bienvenida)
            # Notificar al host del estado del lobby.
            with self._lock:
                self.mensajes_host.append({"tipo": LOBBY, "sala": self.sala.a_dict()})

        elif tipo == ELEGIR_ROL:
            id_j = msg.get("id", 1)
            rol = msg.get("rol")
            self.sala.elegir_rol(id_j, rol)
            # Broadcast del lobby actualizado.
            lobby = msg_lobby(self.sala.a_dict())
            self.enviar_a_invitado(lobby)
            with self._lock:
                self.mensajes_host.append({"tipo": LOBBY, "sala": self.sala.a_dict()})

        elif tipo == INPUT:
            # Reenviar el input del invitado al host.
            with self._lock:
                self.mensajes_host.append(msg)

        elif tipo == PING:
            pong = msg_pong(msg.get("t", 0))
            self.enviar_a_invitado(pong)

        elif tipo == PONG:
            # Calcular latencia y actualizar el grafo.
            t_envio = msg.get("t", 0)
            latencia = int((time.time() * 1000) - t_envio)
            self.sala.actualizar_latencia(0, 1, latencia)

    def _desconectar_invitado(self):
        """Limpia la conexión del invitado."""
        if self._cliente:
            try:
                self._cliente.close()
            except OSError:
                pass
            self._cliente = None
        self.sala.desconectar(1)
        with self._lock:
            self.mensajes_host.append({"tipo": DESCONEXION, "id": 1})


def _ip_local():
    """Obtiene la IP local de la máquina (la que otros en la LAN ven)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
