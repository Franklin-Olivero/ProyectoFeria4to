"""Servidor TCP para el multijugador en red de Civitas (hasta 4 jugadores).

El host ejecuta este servidor en un hilo aparte. Acepta hasta 3 invitados
(4 jugadores en total con el host) y retransmite mensajes entre todos.
El estado del lobby se modela con un GrafoSala (Online/protocolo.py),
un grafo no dirigido donde cada nodo = jugador y cada arista = conexión
activa entre ellos.

Flujo:
    1. El host llama a iniciar(puerto) → abre socket, escucha.
    2. Los invitados se conectan (IDs 1, 2, 3) → el servidor les envía
       BIENVENIDA y sincroniza el lobby con todos.
    3. Cada jugador puede moverse en la sala de espera y elegir su rol.
    4. El host inicia la partida cuando hay al menos 2 jugadores listos.
    5. Durante la partida: los inputs de los clientes se envían al host,
       y los estados del juego se difunden a todos los clientes.
"""

import socket
import threading
import time

from Online.protocolo import (
    BIENVENIDA, DESCONEXION, ELEGIR_ROL, ESTADO, HOLA, INICIAR, INPUT,
    LOBBY, PING, PONG, POSICION_LOBBY, GrafoSala, deserializar_buffer,
    msg_bienvenida, msg_desconexion, msg_lobby, msg_pong,
    msg_posicion_lobby, serializar, crear_mensaje,
)

PUERTO_DEFAULT = 7777
MAX_JUGADORES = 4
BACKLOG = 5
BUFFER_SIZE = 4096
TIMEOUT_ACEPTAR = 0.05  # polling rápido para no bloquear


class Servidor:
    """Servidor TCP que gestiona una sala de hasta 4 jugadores."""

    def __init__(self):
        self.sala = GrafoSala()
        self.iniciado = False
        self.error = None
        self.corriendo = False
        self.mensajes_host = []  # mensajes que el host debe procesar
        self._socket = None
        self._clientes = {}      # id_jugador (1..3) -> socket
        self._buffers = {}       # id_jugador -> bytes acumulados
        self.posiciones_lobby = {}  # id_jugador -> (x, y)
        self._hilo = None
        self._cancelar = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # API pública (llamada desde Pygame)
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
        self._socket.setblocking(False)
        self.corriendo = True

        # El host es el jugador 0.
        self.sala.conectar(0)

        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()

        return _ip_local()

    def detener(self):
        """Cierra todos los sockets y detiene el servidor."""
        self._cancelar.set()
        self.corriendo = False
        with self._lock:
            for sock in list(self._clientes.values()):
                try:
                    sock.close()
                except OSError:
                    pass
            self._clientes.clear()
            self._buffers.clear()
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

    def enviar_a_todos(self, datos_bytes, excluir_id=None):
        """Envía bytes a todos los clientes conectados (excepto excluir_id)."""
        with self._lock:
            desconectados = []
            for jid, sock in self._clientes.items():
                if jid == excluir_id:
                    continue
                try:
                    sock.sendall(datos_bytes)
                except OSError:
                    desconectados.append(jid)
            for jid in desconectados:
                self._desconectar_cliente_interno(jid)

    def enviar_a_invitado(self, datos_bytes):
        """Compatibilidad con código anterior: difunde a todos los clientes."""
        self.enviar_a_todos(datos_bytes)

    def enviar_a_cliente(self, id_jugador, datos_bytes):
        """Envía bytes a un cliente específico."""
        with self._lock:
            sock = self._clientes.get(id_jugador)
            if sock:
                try:
                    sock.sendall(datos_bytes)
                except OSError:
                    self._desconectar_cliente_interno(id_jugador)

    def hay_invitados(self):
        with self._lock:
            return len(self._clientes) > 0

    def hay_invitado(self):
        return self.hay_invitados()

    def cantidad_jugadores(self):
        return self.sala.cantidad()

    def leer_mensajes(self):
        """Retorna y vacía la cola de mensajes para el host."""
        with self._lock:
            msgs = list(self.mensajes_host)
            self.mensajes_host.clear()
        return msgs

    @property
    def puerto(self):
        if self._socket:
            try:
                return self._socket.getsockname()[1]
            except OSError:
                pass
        return PUERTO_DEFAULT

    # ------------------------------------------------------------------
    # Loop interno (hilo en segundo plano)
    # ------------------------------------------------------------------

    def _loop(self):
        while not self._cancelar.is_set():
            # 1. Aceptar nuevos clientes si hay cupo disponible.
            if len(self._clientes) < MAX_JUGADORES - 1:
                try:
                    conn, _ = self._socket.accept()
                    conn.setblocking(False)
                    self._registrar_nuevo_cliente(conn)
                except BlockingIOError:
                    pass
                except OSError:
                    break

            # 2. Leer datos de los clientes conectados.
            with self._lock:
                clientes_activos = list(self._clientes.items())

            for jid, sock in clientes_activos:
                try:
                    datos = sock.recv(BUFFER_SIZE)
                except BlockingIOError:
                    continue
                except OSError:
                    self._desconectar_cliente(jid)
                    continue

                if not datos:
                    self._desconectar_cliente(jid)
                    continue

                self._buffers[jid] = self._buffers.get(jid, b"") + datos
                mensajes, self._buffers[jid] = deserializar_buffer(self._buffers[jid])
                for msg in mensajes:
                    self._procesar(jid, msg)

            time.sleep(0.004)  # ~250 Hz

    def _registrar_nuevo_cliente(self, sock):
        with self._lock:
            # Asignar el primer id disponible entre 1 y 3.
            usados = set(self._clientes.keys())
            nuevo_id = None
            for candidato in range(1, MAX_JUGADORES):
                if candidato not in usados:
                    nuevo_id = candidato
                    break
            if nuevo_id is None:
                try:
                    sock.close()
                except OSError:
                    pass
                return

            self._clientes[nuevo_id] = sock
            self._buffers[nuevo_id] = b""
            self.sala.conectar(nuevo_id)

            # Enviar bienvenida al recién conectado.
            bienvenida = msg_bienvenida(nuevo_id, self.sala.a_dict())
            try:
                sock.sendall(bienvenida)
            except OSError:
                self._desconectar_cliente_interno(nuevo_id)
                return

            # Broadcast del lobby actualizado a todos.
            lobby_bytes = msg_lobby(self.sala.a_dict())
            for cid, s in self._clientes.items():
                if cid != nuevo_id:
                    try:
                        s.sendall(lobby_bytes)
                    except OSError:
                        pass

            self.mensajes_host.append({"tipo": LOBBY, "sala": self.sala.a_dict()})

    def _procesar(self, jid, msg):
        tipo = msg.get("tipo")

        if tipo == HOLA:
            # Ya se envió bienvenida al aceptar conexión.
            pass

        elif tipo == ELEGIR_ROL:
            rol = msg.get("rol")
            self.sala.elegir_rol(jid, rol)
            lobby = msg_lobby(self.sala.a_dict())
            self.enviar_a_todos(lobby)
            with self._lock:
                self.mensajes_host.append({"tipo": LOBBY, "sala": self.sala.a_dict()})

        elif tipo == POSICION_LOBBY:
            x, y = msg.get("x", 0), msg.get("y", 0)
            self.posiciones_lobby[jid] = (x, y)
            # Retransmitir a los otros clientes y al host.
            pos_bytes = msg_posicion_lobby(jid, x, y)
            self.enviar_a_todos(pos_bytes, excluir_id=jid)
            with self._lock:
                self.mensajes_host.append({"tipo": POSICION_LOBBY, "id": jid, "x": x, "y": y})

        elif tipo == INPUT:
            msg["id"] = jid
            with self._lock:
                self.mensajes_host.append(msg)

        elif tipo == PING:
            pong = msg_pong(msg.get("t", 0))
            self.enviar_a_cliente(jid, pong)

        elif tipo == PONG:
            t_envio = msg.get("t", 0)
            latencia = int((time.time() * 1000) - t_envio)
            self.sala.actualizar_latencia(0, jid, latencia)

    def _desconectar_cliente(self, jid):
        with self._lock:
            self._desconectar_cliente_interno(jid)

    def _desconectar_cliente_interno(self, jid):
        sock = self._clientes.pop(jid, None)
        self._buffers.pop(jid, None)
        self.posiciones_lobby.pop(jid, None)
        if sock:
            try:
                sock.close()
            except OSError:
                pass
        self.sala.desconectar(jid)
        lobby_bytes = msg_lobby(self.sala.a_dict())
        for s in self._clientes.values():
            try:
                s.sendall(lobby_bytes)
            except OSError:
                pass
        self.mensajes_host.append({"tipo": DESCONEXION, "id": jid})
        self.mensajes_host.append({"tipo": LOBBY, "sala": self.sala.a_dict()})


def _ip_local():
    """Obtiene la IP local de la máquina."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
