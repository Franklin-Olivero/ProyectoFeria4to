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
    3. Cada jugador puede moverse en la sala de espera, elegir su rol y
       su apariencia (vestidores).
    4. El host inicia la partida cuando hay al menos 2 jugadores listos:
       sortea al impostor entre los conectados y lo difunde en INICIAR.
    5. Durante la partida: los inputs de los clientes se envían al host,
       y los estados del juego se difunden a todos los clientes.
"""

import random
import socket
import threading
import time

from Online import red_local
from Online.protocolo import (
    BIENVENIDA, DESCONEXION, ELEGIR_APARIENCIA, ELEGIR_ROL, ESTADO, HOLA, INICIAR, INPUT,
    LOBBY, PING, PONG, POSICION_LOBBY, ENTRAR_MAZMORRA, CAMBIO_ESCENA,
    CAMBIO_CUARTO, DECISION_NAV, HISTORIA, REUNION, SABOTAJE, GrafoSala, deserializar_buffer, msg_bienvenida,
    msg_desconexion, msg_lobby, msg_ping, msg_pong, msg_posicion_lobby,
    msg_entrar_mazmorra, msg_cambio_escena, msg_cambio_cuarto, msg_iniciar,
    serializar, crear_mensaje,
)
from Online.red_local import ahora_ms, enviar_todo, sin_retraso, suavizar

# Puertos más propensos a estar abiertos en redes WiFi universitarias o públicas:
# 8080 (HTTP alternativo), 8443 (HTTPS alternativo), 8000 (dev web), 5000, 9000, 25565, 7777, 8888.
PUERTO_DEFAULT = 8080
PUERTOS_CANDIDATOS = (8080, 8443, 8000, 5000, 9000, 25565, 7777, 8888)
MAX_JUGADORES = 4
BACKLOG = 5
BUFFER_SIZE = 4096
TIMEOUT_ACEPTAR = 0.05  # polling rápido para no bloquear


class Servidor:
    """Servidor TCP que gestiona una sala de hasta 4 jugadores."""

    def __init__(self):
        self.sala = GrafoSala()
        self.iniciado = False
        self.id_impostor = None  # id de red del jugador sorteado al iniciar
        self.estado_partida = {"escena": "CIUDAD", "zona": None, "cuarto_idx": 0}
        self.ultimo_snapshot_estado = None
        self.error = None
        self.corriendo = False
        self.mensajes_host = []  # mensajes que el host debe procesar
        self._socket = None
        self._clientes = {}      # id_jugador (1..3) -> socket
        self._buffers = {}       # id_jugador -> bytes acumulados
        self.posiciones_lobby = {}  # id_jugador -> (x, y)
        self.latencias = {}         # id_jugador -> ping medido con PING/PONG (ms)
        self._hilo = None
        self._cancelar = threading.Event()
        self._lock = threading.RLock()
        self._proximo_ping = 0.0

    def sortear_impostor(self):
        """Elige al impostor al azar entre los vértices del grafo de sala:
        1 de 2, 1 de 3 o 1 de 4. Solo el host decide y una sola vez por
        partida; los invitados lo reciben en INICIAR. O(V log V) por el
        sorted de sala.jugadores(); random.choice es O(1)."""
        if self.id_impostor is None:
            jugadores = self.sala.jugadores()
            if jugadores:
                self.id_impostor = random.choice(jugadores)
        return self.id_impostor

    def marcar_iniciado(self, estado_partida=None):
        """Marca que la partida ha iniciado y guarda el estado actual. El
        sorteo va antes que `iniciado`: quien se una desde ese instante ya
        lo recibe en su BIENVENIDA."""
        with self._lock:
            self.sortear_impostor()
            self.iniciado = True
            if estado_partida:
                self.estado_partida.update(estado_partida)

    def actualizar_estado_partida(self, escena=None, zona=None, cuarto_idx=None):
        """Actualiza el estado actual de la partida (escena, zona o cuarto)."""
        if escena is not None:
            self.estado_partida["escena"] = escena
        if zona is not None:
            self.estado_partida["zona"] = zona
        if cuarto_idx is not None:
            self.estado_partida["cuarto_idx"] = cuarto_idx

    # ------------------------------------------------------------------
    # API pública (llamada desde Pygame)
    # ------------------------------------------------------------------

    def iniciar(self, puerto=PUERTO_DEFAULT, interfaz="0.0.0.0"):
        """Arranca el servidor en un hilo aparte. Retorna la IP local.
        `interfaz` = "127.0.0.1" solo acepta conexiones de esta PC (tests).
        Si el puerto pedido está ocupado o bloqueado (y no es 0), prueba
        automáticamente los demás puertos de PUERTOS_CANDIDATOS."""
        if puerto == 0:
            candidatos = [0]
        elif puerto is None:
            candidatos = list(PUERTOS_CANDIDATOS)
        else:
            candidatos = [puerto] + [p for p in PUERTOS_CANDIDATOS if p != puerto]

        ultimo_error = None
        for p in candidatos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((interfaz, p))
                self._socket = sock
                break
            except OSError as e:
                ultimo_error = e
                sock.close()
        else:
            self.error = f"No se pudo abrir ningún puerto en {candidatos}: {ultimo_error}"
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
                    enviar_todo(sock, datos_bytes)
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
                    enviar_todo(sock, datos_bytes)
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

    def latencia_promedio(self):
        """Ping promedio (ms) con los invitados conectados, o None si
        ninguno ha respondido aún (o no hay invitados)."""
        with self._lock:
            valores = [self.latencias[jid] for jid in self._clientes if jid in self.latencias]
        return sum(valores) / len(valores) if valores else None

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

    def _quizas_enviar_pings(self):
        """Cada INTERVALO_PING_S manda PING a todos; cada invitado lo devuelve como PONG."""
        ahora = time.perf_counter()
        if ahora >= self._proximo_ping:
            self._proximo_ping = ahora + red_local.INTERVALO_PING_S
            self.enviar_a_todos(msg_ping(ahora_ms()))

    def _loop(self):
        while not self._cancelar.is_set():
            self._quizas_enviar_pings()
            # 1. Aceptar nuevos clientes si hay cupo disponible.
            if len(self._clientes) < MAX_JUGADORES - 1:
                try:
                    conn, _ = self._socket.accept()
                    conn.setblocking(False)
                    sin_retraso(conn)
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
            bienvenida = msg_bienvenida(
                nuevo_id, self.sala.a_dict(),
                iniciado=self.iniciado,
                estado_partida=self.estado_partida if self.iniciado else None,
                id_impostor=self.id_impostor if self.iniciado else None,
            )
            try:
                enviar_todo(sock, bienvenida)
            except OSError:
                self._desconectar_cliente_interno(nuevo_id)
                return

            if self.iniciado:
                # La partida ya arrancó: notificar al cliente de inmediato para que salte a juego
                try:
                    enviar_todo(sock, msg_iniciar(self.estado_partida, id_impostor=self.id_impostor))
                    if self.ultimo_snapshot_estado is not None:
                        enviar_todo(sock, self.ultimo_snapshot_estado)
                except OSError:
                    self._desconectar_cliente_interno(nuevo_id)
                    return
                self.mensajes_host.append({"tipo": "RECONEXION", "id": nuevo_id})

            # Broadcast del lobby actualizado a todos.
            lobby_bytes = msg_lobby(self.sala.a_dict())
            for cid, s in self._clientes.items():
                if cid != nuevo_id:
                    try:
                        enviar_todo(s, lobby_bytes)
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

        elif tipo == ELEGIR_APARIENCIA:
            # Igual que el rol: es otro atributo del nodo `jid` (el id de la
            # conexión, no el del mensaje: nadie viste a otro jugador).
            self.sala.elegir_apariencia(jid, msg.get("apariencia"))
            self.enviar_a_todos(msg_lobby(self.sala.a_dict()))
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

        elif tipo in (DECISION_NAV, HISTORIA, REUNION, SABOTAJE):
            msg["id"] = jid  # el id de la conexión: nadie decide (ni vota) por otro
            with self._lock:
                self.mensajes_host.append(msg)

        elif tipo == ENTRAR_MAZMORRA:
            zona = msg.get("zona")
            self.actualizar_estado_partida(escena="MAZMORRA", zona=zona, cuarto_idx=0)
            datos_bytes = msg_entrar_mazmorra(zona, id_jugador=jid)
            self.enviar_a_todos(datos_bytes, excluir_id=jid)
            with self._lock:
                self.mensajes_host.append({"tipo": ENTRAR_MAZMORRA, "zona": zona, "id": jid})

        elif tipo == CAMBIO_ESCENA:
            esc = msg.get("escena")
            zona = msg.get("zona")
            cuarto = msg.get("cuarto", 0)
            self.actualizar_estado_partida(escena=esc, zona=zona, cuarto_idx=cuarto)
            datos_bytes = msg_cambio_escena(esc, zona=zona, cuarto_idx=cuarto)
            self.enviar_a_todos(datos_bytes, excluir_id=jid)
            with self._lock:
                self.mensajes_host.append({"tipo": CAMBIO_ESCENA, "escena": esc, "zona": zona, "cuarto": cuarto, "id": jid})

        elif tipo == CAMBIO_CUARTO:
            cuarto = msg.get("cuarto", 0)
            self.actualizar_estado_partida(cuarto_idx=cuarto)
            datos_bytes = msg_cambio_cuarto(cuarto)
            self.enviar_a_todos(datos_bytes, excluir_id=jid)
            with self._lock:
                self.mensajes_host.append({"tipo": CAMBIO_CUARTO, "cuarto": cuarto, "id": jid})

        elif tipo == PING:
            pong = msg_pong(msg.get("t", 0))
            self.enviar_a_cliente(jid, pong)

        elif tipo == PONG:
            # `t` es la hora (reloj de ESTA PC) en que se mandó el PING: el
            # invitado lo devuelve igual, así no importa que su reloj sea otro.
            rtt = max(0.0, ahora_ms() - msg.get("t", 0))
            with self._lock:
                if jid not in self._clientes:
                    return
                self.latencias[jid] = suavizar(self.latencias.get(jid), rtt)
                self.sala.actualizar_latencia(0, jid, round(self.latencias[jid]))

    def _desconectar_cliente(self, jid):
        with self._lock:
            self._desconectar_cliente_interno(jid)

    def _desconectar_cliente_interno(self, jid):
        sock = self._clientes.pop(jid, None)
        self._buffers.pop(jid, None)
        self.posiciones_lobby.pop(jid, None)
        self.latencias.pop(jid, None)
        if sock:
            try:
                sock.close()
            except OSError:
                pass
        self.sala.desconectar(jid)
        lobby_bytes = msg_lobby(self.sala.a_dict())
        for s in self._clientes.values():
            try:
                enviar_todo(s, lobby_bytes)
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
