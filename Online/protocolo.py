"""Protocolo de mensajes para el multijugador en red de Civitas.

Cada mensaje es un dict serializado a JSON + un delimitador de línea
('\\n'). El grafo de conexiones entre jugadores (quién está en el lobby,
quién confirmó rol) se mantiene como un Grafo (src/structures/graph.py)
donde cada nodo es un id de jugador y las aristas representan que están
en la misma sala.

Tipos de mensaje (campo "tipo"):
    HOLA          — el cliente se presenta al servidor
    BIENVENIDA    — el servidor acepta y asigna número de jugador
    LOBBY         — estado del lobby (jugadores conectados, roles, apariencias)
    ELEGIR_ROL    — un jugador confirma su clase
    ELEGIR_APARIENCIA — un jugador cambia piel, cabeza o traje en un vestidor
    INICIAR       — el host arranca la partida (lleva quién es el impostor)
    INPUT         — input de un frame (dirección, disparando, etc.)
    ESTADO        — snapshot del estado del juego (posiciones, vidas...)
    DESCONEXION   — un jugador se fue
    PING / PONG   — latencia
    CELULAR       — celular: chat de la sala y semilla + reloj del feed en vivo (Online/chat_celular.py)

La estructura de datos clave aquí es el **grafo de sala**: un grafo no
dirigido donde cada nodo es un jugador conectado y cada arista indica
que comparten la misma sesión. Esto permite, en futuras ampliaciones,
manejar múltiples salas o topologías de red más complejas. Para la demo
actual (2 jugadores, 1 sala) el grafo tiene 2 nodos y 1 arista.

Complejidad:
    - Serializar/deserializar: O(n) donde n = tamaño del mensaje
    - Buscar jugador en el grafo de sala: O(1) promedio (dict interno)
    - Verificar conexión entre jugadores: O(1) promedio
"""

import json
import struct

from src.core.apariencia import PREDETERMINADA, Apariencia
from src.structures.graph import Grafo

# Delimitador de fin de mensaje (cada mensaje JSON ocupa una línea).
DELIMITADOR = b"\\n"
ENCODING = "utf-8"

# --- Tipos de mensaje ---------------------------------------------------

HOLA = "HOLA"
BIENVENIDA = "BIENVENIDA"
LOBBY = "LOBBY"
ELEGIR_ROL = "ELEGIR_ROL"
ELEGIR_APARIENCIA = "ELEGIR_APARIENCIA"
INICIAR = "INICIAR"
INPUT = "INPUT"
ESTADO = "ESTADO"
DESCONEXION = "DESCONEXION"
POSICION_LOBBY = "POSICION_LOBBY"
PING = "PING"
PONG = "PONG"
ENTRAR_MAZMORRA = "ENTRAR_MAZMORRA"
CAMBIO_ESCENA = "CAMBIO_ESCENA"
CAMBIO_CUARTO = "CAMBIO_CUARTO"
DECISION_NAV = "DECISION_NAV"
HISTORIA = "HISTORIA"  # un invitado decide en su crisis: el host fija la reputación
REUNION = "REUNION"  # reunión de emergencia: convocar, votar o escribir en el chat (Online/reunion.py)
SABOTAJE = "SABOTAJE"  # el impostor aprieta SABOTEAR: publicación viral para todos (Online/post_sabotaje.py)
CELULAR = "CELULAR"  # celular: "sync" al conectarse y "chat" de la sala (Online/chat_celular.py)

# --- Roles (mismos nombres que las clases del juego) ---------------------

ROLES = ("Ciudadano", "Influencer", "Periodista", "Candidato")


# =========================================================================
# Grafo de sala: estructura de datos que modela las conexiones del lobby
# =========================================================================

class GrafoSala:
    """Grafo no dirigido que modela los jugadores conectados a una sala.

    Cada nodo es un id de jugador (entero, 0 = host, 1 = invitado).
    Una arista entre dos nodos significa que comparten sesión.
    El peso de la arista guarda la latencia (ms) entre ellos.

    Además del rol, cada nodo guarda la apariencia que su jugador eligió
    en los vestidores del lobby (src/core/apariencia.py).

    Operaciones:
        conectar(id)        — agrega jugador al grafo       O(V)
        desconectar(id)     — quita jugador y sus aristas   O(V)
        jugadores()         — lista de ids conectados        O(V)
        estan_conectados()  — hay arista entre host e invitado O(1)
        latencia(a, b)      — peso de la arista              O(1)
        elegir_apariencia() / apariencia_de() — atributo del nodo O(1)
    """

    def __init__(self):
        self.grafo = Grafo()
        self._roles = {}  # id -> nombre de rol (o None si no eligió)
        self._apariencias = {}  # id -> Apariencia (piel, cabeza y traje del vestidor)

    def conectar(self, id_jugador):
        """Agrega un jugador al grafo y lo conecta con todos los demás
        (sala única: todos están conectados entre sí)."""
        existentes = self.grafo.nodos()
        self.grafo.agregar_nodo(id_jugador)
        for otro in existentes:
            self.grafo.agregar_arista(id_jugador, otro, peso=0)
        self._roles[id_jugador] = None
        self._apariencias[id_jugador] = PREDETERMINADA

    def desconectar(self, id_jugador):
        """Quita al jugador y todas sus aristas."""
        if id_jugador in self.grafo.nodos():
            self.grafo.eliminar_nodo(id_jugador)
        self._roles.pop(id_jugador, None)
        self._apariencias.pop(id_jugador, None)

    def jugadores(self):
        """Lista de ids de jugadores conectados."""
        return sorted(self.grafo.nodos())

    def cantidad(self):
        return len(self.grafo.nodos())

    def elegir_rol(self, id_jugador, rol):
        """Registra la elección de rol de un jugador."""
        self._roles[id_jugador] = rol

    def rol_de(self, id_jugador):
        return self._roles.get(id_jugador)

    def elegir_apariencia(self, id_jugador, apariencia):
        """Registra la apariencia de un jugador: una Apariencia o el dict
        recibido por red (se valida con Apariencia.de_dict)."""
        if not isinstance(apariencia, Apariencia):
            apariencia = Apariencia.de_dict(apariencia)
        self._apariencias[id_jugador] = apariencia

    def apariencia_de(self, id_jugador):
        """Apariencia del jugador (la predeterminada si nunca eligió)."""
        return self._apariencias.get(id_jugador, PREDETERMINADA)

    def todos_listos(self):
        """True si todos eligieron rol."""
        return len(self._roles) >= 2 and all(
            r is not None for r in self._roles.values()
        )

    def estan_conectados(self, a, b):
        """True si hay arista directa entre a y b."""
        return self.grafo.existe_arista(a, b)

    def actualizar_latencia(self, a, b, ms):
        """Actualiza el peso (latencia) de la arista entre a y b."""
        if self.grafo.existe_arista(a, b):
            self.grafo.agregar_arista(a, b, peso=ms)

    def a_dict(self):
        """Serializa el estado del lobby para enviarlo por red."""
        return {
            "jugadores": [
                {"id": jid, "rol": self._roles.get(jid),
                 "apariencia": self.apariencia_de(jid).a_dict()}
                for jid in self.jugadores()
            ],
        }

    @classmethod
    def de_dict(cls, datos):
        """Reconstruye el grafo de sala desde un dict recibido por red."""
        sala = cls()
        for info in datos.get("jugadores", []):
            jid = info["id"]
            sala.conectar(jid)
            if info.get("rol"):
                sala.elegir_rol(jid, info["rol"])
            # Un host de una versión sin vestidores no la manda: queda la predeterminada.
            if "apariencia" in info:
                sala.elegir_apariencia(jid, info["apariencia"])
        return sala


# =========================================================================
# Serialización de mensajes
# =========================================================================

def crear_mensaje(tipo, **campos):
    """Crea un mensaje como dict con el tipo y los campos dados."""
    return {"tipo": tipo, **campos}


def serializar(mensaje):
    """Dict -> bytes listos para enviar por socket (JSON + delimitador).

    Se antepone la longitud como entero de 4 bytes (big-endian) para
    poder leer mensajes completos sin depender del delimitador dentro
    del JSON. Formato: [4 bytes longitud][JSON en UTF-8]
    """
    datos = json.dumps(mensaje, ensure_ascii=False).encode(ENCODING)
    return struct.pack("!I", len(datos)) + datos


def deserializar_buffer(buffer):
    """Extrae todos los mensajes completos de un buffer de bytes.

    Retorna (lista_de_mensajes, buffer_restante).
    Cada mensaje tiene un header de 4 bytes con su longitud.
    """
    mensajes = []
    while len(buffer) >= 4:
        longitud = struct.unpack("!I", buffer[:4])[0]
        if len(buffer) < 4 + longitud:
            break  # mensaje incompleto, esperar más datos
        datos = buffer[4:4 + longitud]
        buffer = buffer[4 + longitud:]
        try:
            mensajes.append(json.loads(datos.decode(ENCODING)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # mensaje corrupto, se descarta
    return mensajes, buffer


# =========================================================================
# Mensajes predefinidos
# =========================================================================

def msg_hola(nombre="Jugador"):
    return serializar(crear_mensaje(HOLA, nombre=nombre))


def msg_bienvenida(id_jugador, sala_dict, iniciado=False, estado_partida=None, id_impostor=None):
    return serializar(crear_mensaje(BIENVENIDA, id=id_jugador, sala=sala_dict, iniciado=iniciado,
                                    estado_partida=estado_partida, id_impostor=id_impostor))


def msg_lobby(sala_dict):
    return serializar(crear_mensaje(LOBBY, sala=sala_dict))


def msg_elegir_rol(id_jugador, rol):
    return serializar(crear_mensaje(ELEGIR_ROL, id=id_jugador, rol=rol))


def msg_elegir_apariencia(id_jugador, apariencia_dict):
    return serializar(crear_mensaje(ELEGIR_APARIENCIA, id=id_jugador, apariencia=apariencia_dict))


def msg_iniciar(estado_partida=None, id_impostor=None):
    return serializar(crear_mensaje(INICIAR, estado_partida=estado_partida, id_impostor=id_impostor))


def msg_input(id_jugador, datos_input):
    return serializar(crear_mensaje(INPUT, id=id_jugador, input=datos_input))


def msg_estado(datos_estado):
    return serializar(crear_mensaje(ESTADO, estado=datos_estado))


def msg_desconexion(id_jugador):
    return serializar(crear_mensaje(DESCONEXION, id=id_jugador))


def msg_ping(timestamp):
    return serializar(crear_mensaje(PING, t=timestamp))


def msg_pong(timestamp):
    return serializar(crear_mensaje(PONG, t=timestamp))


def msg_posicion_lobby(id_jugador, x, y):
    return serializar(crear_mensaje(POSICION_LOBBY, id=id_jugador, x=round(x, 1), y=round(y, 1)))


def msg_entrar_mazmorra(zona, id_jugador=0):
    return serializar(crear_mensaje(ENTRAR_MAZMORRA, zona=zona, id=id_jugador))


def msg_cambio_escena(escena, zona=None, cuarto_idx=0):
    return serializar(crear_mensaje(CAMBIO_ESCENA, escena=escena, zona=zona, cuarto=cuarto_idx))


def msg_cambio_cuarto(cuarto_idx):
    return serializar(crear_mensaje(CAMBIO_CUARTO, cuarto=cuarto_idx))


def msg_decision_nav(direccion, id_jugador=None):
    return serializar(crear_mensaje(DECISION_NAV, dir=direccion, id=id_jugador))


def msg_historia(evento, id_jugador=None, **datos):
    return serializar(crear_mensaje(HISTORIA, evento=evento, id=id_jugador, **datos))


def msg_reunion(evento, id_jugador=None, **datos):
    return serializar(crear_mensaje(REUNION, evento=evento, id=id_jugador, **datos))


def msg_sabotaje(id_jugador=None):
    return serializar(crear_mensaje(SABOTAJE, id=id_jugador))


def msg_celular(evento, **datos):
    """Celular: `evento` EVENTO_SYNC (host -> invitado: semilla, t, chat) o
    EVENTO_CHAT (invitado -> host: texto; host -> todos: m)."""
    return serializar(crear_mensaje(CELULAR, evento=evento, **datos))


