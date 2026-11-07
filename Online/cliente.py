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

from Online import red_local
from Online.protocolo import (
    BIENVENIDA, DESCONEXION, ESTADO, GrafoSala, INICIAR, LOBBY, PING, PONG,
    POSICION_LOBBY, ENTRAR_MAZMORRA, CAMBIO_ESCENA, CAMBIO_CUARTO,
    deserializar_buffer, msg_elegir_apariencia, msg_elegir_rol, msg_hola, msg_input, msg_ping,
    msg_pong, msg_posicion_lobby, msg_entrar_mazmorra, msg_decision_nav, msg_historia,
)
from Online.red_local import (
    ahora_ms, clasificar_error_conexion, enviar_todo, sin_retraso, suavizar,
)

BUFFER_SIZE = 4096


class Cliente:
    """Cliente TCP que se conecta a una sala existente.

    Atributos públicos (leídos desde el hilo de Pygame):
        id_jugador  — número asignado por el servidor (0=host, 1=invitado)
        sala        — GrafoSala reconstruido del último LOBBY recibido
        iniciado    — True cuando recibe INICIAR
        id_impostor — id del jugador que sorteó el host (None hasta iniciar)
        unido_en_curso — True si al conectarse la partida ya había iniciado
        conectado   — True mientras el socket está abierto
        error       — str con el último error, o None
        tipo_error  — por qué falló conectar (red_local.TIMEOUT, RECHAZADA...)
        mensajes    — cola de mensajes recibidos (list)
        latencia_ms — ping con el host (ms, promedio móvil)
        ping_medido — True desde que llegó el primer PONG
    """

    def __init__(self):
        self.id_jugador = None
        self.sala = GrafoSala()
        self.iniciado = False
        self.id_impostor = None
        self.unido_en_curso = False
        self.estado_partida = {"escena": "CIUDAD", "zona": None, "cuarto_idx": 0}
        self.conectado = False
        self.error = None
        self.tipo_error = None
        self.mensajes = []
        self.latencia_ms = 0
        self.ping_medido = False
        self.posiciones_lobby = {}  # id -> (x, y)
        self._socket = None
        self._hilo = None
        self._cancelar = threading.Event()
        self._lock = threading.RLock()
        self._lock_envio = threading.Lock()  # el hilo lector también envía (ping)
        self._buffer = b""
        self._rtt = None
        self._proximo_ping = 0.0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def conectar(self, ip, puerto):
        """Se conecta al servidor. Retorna True si tuvo éxito."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((ip, puerto))
            sin_retraso(self._socket)
            self._socket.setblocking(False)
            self.conectado = True
        except (OSError, ConnectionRefusedError) as e:
            self.error = f"No se pudo conectar a {ip}:{puerto} — {e}"
            self.tipo_error = clasificar_error_conexion(e)
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

    def detener(self):
        """Mismo nombre que Servidor.detener(): la sala de espera llama
        conexion.detener() sin saber si es host o invitado."""
        self.desconectar()

    def enviar_rol(self, rol):
        """Notifica al servidor la elección de rol."""
        self._enviar(msg_elegir_rol(self.id_jugador if self.id_jugador is not None else 1, rol))

    def enviar_apariencia(self, apariencia):
        """Notifica al servidor la Apariencia elegida en un vestidor."""
        self._enviar(msg_elegir_apariencia(self.id_jugador if self.id_jugador is not None else 1,
                                           apariencia.a_dict()))

    def enviar_posicion_lobby(self, x, y):
        """Envía la posición del jugador en la sala de espera."""
        if self.id_jugador is not None:
            self._enviar(msg_posicion_lobby(self.id_jugador, x, y))

    def enviar_input(self, datos_input):
        """Envía el input de este frame al servidor."""
        self._enviar(msg_input(self.id_jugador if self.id_jugador is not None else 1, datos_input))

    def enviar_decision_nav(self, direccion):
        """Envía la selección o confirmación de la terminal de decisión al host."""
        self._enviar(msg_decision_nav(direccion, self.id_jugador if self.id_jugador is not None else 1))

    def enviar_historia(self, evento, **datos):
        """Avisa al host de una decisión de la crisis o de la misión de redención."""
        self._enviar(msg_historia(evento, self.id_jugador if self.id_jugador is not None else 1, **datos))

    def enviar_ping(self):
        """Envía un ping para medir latencia (el host lo devuelve como PONG)."""
        self._enviar(msg_ping(ahora_ms()))

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
                with self._lock_envio:
                    enviar_todo(self._socket, datos_bytes)
            except OSError:
                self.conectado = False

    def _quizas_enviar_ping(self):
        ahora = time.perf_counter()
        if ahora >= self._proximo_ping:
            self._proximo_ping = ahora + red_local.INTERVALO_PING_S
            self.enviar_ping()

    def _registrar_rtt(self, t_envio):
        self._rtt = suavizar(self._rtt, max(0.0, ahora_ms() - t_envio))
        self.latencia_ms = round(self._rtt)
        self.ping_medido = True
        self._pesar_arista_propia()

    def _pesar_arista_propia(self):
        """El peso de la arista host-yo en el grafo de sala es el ping medido."""
        if self.ping_medido and self.id_jugador is not None:
            self.sala.actualizar_latencia(0, self.id_jugador, self.latencia_ms)

    def _loop(self):
        """Lee mensajes del servidor en un hilo aparte."""
        while not self._cancelar.is_set():
            self._quizas_enviar_ping()
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

    def enviar_entrar_mazmorra(self, zona):
        """Notifica al servidor que este jugador pide entrar a una mazmorra."""
        self._enviar(msg_entrar_mazmorra(zona, id_jugador=self.id_jugador if self.id_jugador is not None else 1))

    def _procesar(self, msg):
        tipo = msg.get("tipo")

        if tipo == BIENVENIDA:
            self.id_jugador = msg.get("id", 1)
            self.sala = GrafoSala.de_dict(msg.get("sala", {}))
            self._pesar_arista_propia()
            if msg.get("iniciado"):
                self.id_impostor = msg.get("id_impostor")
                self.unido_en_curso = True
                self.iniciado = True
                if msg.get("estado_partida"):
                    self.estado_partida.update(msg.get("estado_partida"))

        elif tipo == LOBBY:
            self.sala = GrafoSala.de_dict(msg.get("sala", {}))
            self._pesar_arista_propia()

        elif tipo == INICIAR:
            # Primero el impostor: el lobby sale de la sala al ver `iniciado`,
            # desde otro hilo, y ahí mismo pregunta quién es.
            self.id_impostor = msg.get("id_impostor")
            self.iniciado = True
            if msg.get("estado_partida"):
                self.estado_partida.update(msg.get("estado_partida"))

        elif tipo == ENTRAR_MAZMORRA:
            self.estado_partida["escena"] = "MAZMORRA"
            self.estado_partida["zona"] = msg.get("zona")
            self.estado_partida["cuarto_idx"] = 0

        elif tipo == CAMBIO_ESCENA:
            self.estado_partida["escena"] = msg.get("escena")
            self.estado_partida["zona"] = msg.get("zona")
            self.estado_partida["cuarto_idx"] = msg.get("cuarto", 0)

        elif tipo == CAMBIO_CUARTO:
            self.estado_partida["cuarto_idx"] = msg.get("cuarto", 0)

        elif tipo == PING:
            # El host mide su ping con este invitado: se le devuelve tal cual.
            self._enviar(msg_pong(msg.get("t", 0)))
            return

        elif tipo == PONG:
            self._registrar_rtt(msg.get("t", 0))
            return

        elif tipo == POSICION_LOBBY:
            jid = msg.get("id")
            if jid is not None and jid != self.id_jugador:
                self.posiciones_lobby[jid] = (msg.get("x", 0), msg.get("y", 0))

        elif tipo == DESCONEXION:
            self.conectado = False

        # Todos los mensajes (incluido ESTADO, ENTRAR_MAZMORRA, CAMBIO_ESCENA) van a la cola.
        with self._lock:
            self.mensajes.append(msg)

