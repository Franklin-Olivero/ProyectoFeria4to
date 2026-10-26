"""Adaptador de sesión para el modo Online de Civitas.

Conecta el juego existente (Main.py, que ya maneja la partida local)
con la red (Online/servidor.py y Online/cliente.py). En cada frame:

    - El host lee el input del invitado desde el servidor y lo inyecta
      como si fuera el input de un segundo jugador local.
    - El host serializa las posiciones, vidas y estado de todos los
      objetos y lo envía al invitado.
    - El invitado recibe ese snapshot y actualiza su vista.

Para la demo de la feria, el host es autoritativo: toda la lógica
corre en su máquina y el invitado solo ve el resultado. Esto simplifica
enormemente la sincronización (no hay conflictos de estado).

Estructura de datos en uso: el estado del juego se transmite como un
dict serializable que incluye las posiciones de los jugadores, enemigos,
proyectiles y el valor del colapso. El grafo de sala (GrafoSala) se
usa durante el lobby para manejar las conexiones.
"""

import time
import math

from Online.protocolo import (
    INPUT, ESTADO, DESCONEXION, crear_mensaje, serializar,
    deserializar_buffer, msg_estado, msg_input, ROLES,
)


def serializar_input(pedido):
    """Convierte un InputJugador en un dict serializable para enviar por red.

    Campos: dirección de movimiento (dx, dy), si está disparando,
    punto de apuntado (px, py), si pidió habilidad y si pidió dash.
    """
    return {
        "dx": round(pedido.direccion.x, 3) if pedido.direccion else 0,
        "dy": round(pedido.direccion.y, 3) if pedido.direccion else 0,
        "disparando": pedido.disparando,
        "px": round(pedido.punto.x, 1) if pedido.punto else None,
        "py": round(pedido.punto.y, 1) if pedido.punto else None,
        "habilidad": pedido.habilidad,
        "dash": pedido.dash,
    }


def deserializar_input(datos):
    """Reconstruye un InputJugador (namedtuple-like) desde un dict de red.

    En lugar de importar el dataclass real (que trae dependencias de Pygame),
    retorna un objeto simple con los mismos atributos que InputJugador.
    """
    return _InputRed(
        dx=datos.get("dx", 0),
        dy=datos.get("dy", 0),
        disparando=datos.get("disparando", False),
        px=datos.get("px"),
        py=datos.get("py"),
        habilidad=datos.get("habilidad", False),
        dash=datos.get("dash", False),
    )


class _InputRed:
    """Sustituto ligero de InputJugador para datos que llegan por red."""

    def __init__(self, dx=0, dy=0, disparando=False, px=None, py=None,
                 habilidad=False, dash=False):
        from pygame import Vector2
        self.direccion = Vector2(dx, dy) if (dx or dy) else None
        self.disparando = disparando
        self.punto = Vector2(px, py) if px is not None else None
        self.habilidad = habilidad
        self.dash = dash


def serializar_estado(jugadores, escenario, colapso):
    """Crea un snapshot del estado del juego para enviar al invitado.

    Incluye: posición y vida de cada jugador, posición y vida de cada
    enemigo, y el valor actual del colapso. Los proyectiles se omiten
    por ahora (cada cliente los calcula localmente).
    """
    estado = {
        "t": time.time(),
        "jugadores": [
            {
                "x": round(j.posicion.x, 1),
                "y": round(j.posicion.y, 1),
                "vida": j.vida,
                "vida_max": j.vida_maxima,
            }
            for j in jugadores
        ],
        "colapso": round(colapso.valor, 2),
    }
    if escenario is not None and hasattr(escenario, "enemigos"):
        estado["enemigos"] = [
            {
                "x": e.rect.centerx,
                "y": e.rect.centery,
                "vida": e.vida,
                "vivo": e.vivo,
            }
            for e in escenario.enemigos
        ]
    return estado


def aplicar_estado_remoto(estado, jugadores):
    """Aplica un snapshot recibido por red a los jugadores locales.

    Solo actualiza posiciones y vida; la lógica de combate la maneja
    el host. El invitado solo refleja lo que ve.
    """
    datos_jugadores = estado.get("jugadores", [])
    for i, datos in enumerate(datos_jugadores):
        if i < len(jugadores):
            jugadores[i].posicion.x = datos["x"]
            jugadores[i].posicion.y = datos["y"]
            jugadores[i].vida = datos["vida"]


class AdaptadorOnlineHost:
    """El host usa este adaptador para enviar estado y recibir input de hasta 3 invitados.

    Cada frame:
        1. Llama a recibir_input(id_jugador) → obtiene el input de ese cliente.
        2. Ejecuta la lógica de juego normalmente.
        3. Llama a enviar_estado() → serializa y envía a todos los clientes.
    """

    def __init__(self, servidor):
        self.servidor = servidor
        self._ultimos_inputs = {}  # id_jugador -> InputRed
        self._contador_frames = 0
        self._intervalo_estado = 2  # enviar estado cada N frames

    def recibir_input(self, id_jugador=1):
        """Retorna el último InputRed de un jugador remoto específico."""
        for msg in self.servidor.leer_mensajes():
            if msg.get("tipo") == INPUT:
                jid = msg.get("id", 1)
                self._ultimos_inputs[jid] = deserializar_input(msg.get("input", {}))
            elif msg.get("tipo") == DESCONEXION:
                jid = msg.get("id", 1)
                self._ultimos_inputs.pop(jid, None)
        return self._ultimos_inputs.get(id_jugador)

    def enviar_estado(self, jugadores, escenario, colapso):
        """Serializa y envía el estado actual a todos los invitados."""
        self._contador_frames += 1
        if self._contador_frames % self._intervalo_estado != 0:
            return
        estado = serializar_estado(jugadores, escenario, colapso)
        self.servidor.enviar_a_todos(msg_estado(estado))

    def detener(self):
        self.servidor.detener()


class AdaptadorOnlineJoin:
    """El invitado usa este adaptador para enviar input y recibir estado."""

    def __init__(self, cliente):
        self.cliente = cliente
        self._ultimo_estado = None

    def enviar_input(self, pedido):
        """Serializa el input local y lo envía al host."""
        datos = serializar_input(pedido)
        self.cliente.enviar_input(datos)

    def recibir_estado(self):
        """Retorna el último estado recibido del host, o None."""
        for msg in self.cliente.leer_mensajes():
            if msg.get("tipo") == ESTADO:
                self._ultimo_estado = msg.get("estado")
        return self._ultimo_estado

    def detener(self):
        self.cliente.desconectar()


class _MandoFicticio:
    """Simula un mando siempre conectado para que el bucle de Main.py no falle."""
    def attached(self):
        return True


class EntradaRed:
    """Entrada que lee el input de un jugador remoto recibido a través del socket."""

    def __init__(self, adaptador, id_jugador=1):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()

    def leer(self):
        from src.core.entrada import InputJugador
        inp = self.adaptador.recibir_input(self.id_jugador)
        if inp is None:
            return InputJugador()
        return InputJugador(
            movimiento=(inp.direccion.x, inp.direccion.y) if inp.direccion else (0.0, 0.0),
            punto_apuntado=inp.punto,
            disparando=inp.disparando,
            habilidad=inp.habilidad,
            dash=inp.dash,
        )

