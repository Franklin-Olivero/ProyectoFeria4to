"""Chat de la sala y reloj compartido del CELULAR del modo Online (lógica pura, sin pygame).

El celular (botón CELULAR, tecla C) tiene dos apps: el feed en vivo de la
red social Civitas (Online/feed_celular.py) y un chat de texto con los
jugadores de la sala. Este módulo es todo lo que el celular comparte por la
red (mensaje CELULAR de Online/protocolo.py): los mensajes del chat y la
semilla + el reloj del feed.

Quién manda: el HOST, igual que en la reunión de emergencia
(Online/reunion.py). Cuando alguien escribe, el host limpia el texto, le
pone como autor el id de la CONEXIÓN por la que llegó (nadie escribe por
otro), aplica el anti-spam y los silenciados (los expulsados por votación),
le da el número siguiente (1, 2, 3...) y lo difunde a todos. Cada invitado
solo inserta lo que llega, por número y sin duplicar: el mismo mensaje puede
llegar dos veces (en el SYNC al conectarse y en la difusión de justo
después).

El feed es igual en todas las PCs sin mandarlo por la red: es una
simulación determinista de (semilla, instante). El host sortea la semilla y
cuenta los segundos desde que abrió la sala; al conectarse, cada invitado
recibe los dos (SYNC) y desde ahí suma su propio reloj. Así todas las PCs le
piden al feed el mismo instante.

Estructuras de datos (para la exposición):
    HistorialChat — cola acotada (collections.deque) con los últimos
        MAX_MENSAJES_CELULAR mensajes ordenados por número, más un conjunto
        (set) con los números que tiene: "¿ya lo tengo?" es O(1) en vez de
        recorrer la cola. publicar O(1); recibir O(1) si llega en orden (lo
        normal: TCP) y O(n) si llega desordenado; no_leidos O(k) con k = no
        leídos; reemplazar O(m log m) por ordenar.
    CanalCelular.silenciados — conjunto de ids de red: ¿puede escribir? en O(1).
    Anti-spam — diccionario autor -> instante de su último mensaje: O(1).

Thread-safe: el hilo de red (Servidor o Cliente) y el de pygame usan el
mismo CanalCelular; todo pasa bajo su propio lock.
"""

import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass

MAX_LARGO_MENSAJE_CELULAR = 80
MAX_MENSAJES_CELULAR = 60
INTERVALO_MINIMO_CHAT_S = 0.3  # anti-spam por autor: lo aplica el host

# Tipos de mensaje del chat.
JUGADOR = "jugador"  # lo escribió un jugador
SISTEMA_ENTRO = "entro"  # "J3 entró a la sala" (autor = quien entró)
SISTEMA_SALIO = "salio"  # "J3 salió de la sala" (autor = quien salió)
TIPOS_MENSAJE = (JUGADOR, SISTEMA_ENTRO, SISTEMA_SALIO)

# Eventos del mensaje CELULAR (campo "evento").
EVENTO_SYNC = "sync"  # host -> invitado al conectarse: semilla, reloj e historial
EVENTO_CHAT = "chat"  # invitado -> host: {"texto"}; host -> todos: {"m": dict del mensaje}

LIMITE_ID_RED = 16  # ids de red válidos: 0..15 (la sala usa 0..3; mismo margen que Online/reunion.py)
# Un SYNC con un reloj mayor (más de un día de sala abierta) es basura: el
# feed tendría que simular todo ese tiempo de golpe. Se ignora.
MAX_RELOJ_SYNC_S = 24 * 3600.0


def limpiar_texto(texto):
    """Un renglón de a lo sumo MAX_LARGO_MENSAJE_CELULAR caracteres
    imprimibles con los espacios colapsados, o "" si no queda nada (o no es
    un str). Lo aplican el host al publicar y el invitado al recibir: lo que
    llega por la red nunca se dibuja sin limpiar. Igual que limpiar_mensaje de
    Online/reunion.py, con el largo del celular. O(n) en el largo del texto."""
    if not isinstance(texto, str):
        return ""
    texto = "".join(c if c.isprintable() else " " for c in texto)
    return " ".join(texto.split())[:MAX_LARGO_MENSAJE_CELULAR].rstrip()


def _es_entero(valor):
    """int de verdad: en Python True/False también son int y no cuentan."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_numero_finito(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    try:
        return math.isfinite(valor)
    except OverflowError:  # un int enorme no cabe en un float
        return False


@dataclass(frozen=True)
class MensajeChat:
    """Un mensaje del chat tal como lo publicó el host. Inmutable: los hilos
    se lo pasan sin copiarlo y nadie lo cambia por el camino."""

    numero: int  # lo asigna el host: 1, 2, 3... (creciente)
    autor: int  # id de RED (0 = host, 1..3 invitados); en los del sistema, a quién se refiere
    texto: str  # limpio ("" en los del sistema)
    segundos: float  # reloj del celular (CanalCelular.segundos()) cuando el host lo publicó
    tipo: str = JUGADOR

    def a_dict(self):
        """Lo que viaja por la red (claves cortas, como el ESTADO)."""
        return {"n": self.numero, "a": self.autor, "t": self.texto, "s": round(self.segundos, 2), "k": self.tipo}

    @staticmethod
    def de_dict(datos):
        """MensajeChat a partir de `a_dict()` (lo que llega por la red), o None
        si no tiene la forma: nunca se confía en sus tipos y el texto se vuelve
        a limpiar."""
        if not isinstance(datos, dict):
            return None
        return _crear_mensaje(datos.get("n"), datos.get("a"), datos.get("t"), datos.get("s"), datos.get("k"))


def _crear_mensaje(numero, autor, texto, segundos, tipo):
    """El MensajeChat validado, o None. Un solo lugar con las reglas: lo usan
    el host al publicar y el invitado al recibir, así lo que publica uno el
    otro siempre lo acepta."""
    if not _es_entero(numero) or numero < 1:
        return None
    if not _es_entero(autor) or not 0 <= autor < LIMITE_ID_RED:
        return None
    if not _es_numero_finito(segundos) or tipo not in TIPOS_MENSAJE:
        return None
    texto = limpiar_texto(texto) if tipo == JUGADOR else ""
    if tipo == JUGADOR and not texto:
        return None
    return MensajeChat(numero, autor, texto, float(segundos), tipo)


class HistorialChat:
    """Cola acotada de los últimos MAX_MENSAJES_CELULAR mensajes, ordenada por número.

    Dos estructuras que cambian siempre juntas:
        _cola    — deque de MensajeChat, del más viejo (izquierda) al más nuevo
                   (derecha). Al pasarse del tope se descarta el más viejo por
                   la izquierda en O(1) (en una lista sería O(n): corre todo).
        _numeros — set con los números que hay en la cola: saber si un
                   mensaje ya llegó es O(1).
    Sin lock propio: lo protege el CanalCelular que lo contiene.
    """

    def __init__(self, maximo=MAX_MENSAJES_CELULAR):
        self.maximo = max(1, int(maximo))
        self._cola = deque()
        self._numeros = set()

    def publicar(self, autor, texto, segundos, tipo=JUGADOR):
        """Host: agrega un mensaje con el número siguiente al último. O(1).
        None si no es válido (texto vacío, autor o tipo raros): no gasta número."""
        mensaje = _crear_mensaje(self.ultimo_numero() + 1, autor, texto, segundos, tipo)
        if mensaje is not None:
            self._cola.append(mensaje)
            self._numeros.add(mensaje.numero)
            self._recortar()
        return mensaje

    def recibir(self, mensaje):
        """Invitado: inserta un mensaje del host en su lugar (por número), sin
        duplicar y respetando el tope. True si quedó guardado.

        Lo normal (TCP entrega en orden) es que sea el más nuevo: va al final
        en O(1). Si llega desordenado se busca su lugar desde el final, como
        en la inserción de insertion sort: O(n) con n <= maximo."""
        if not isinstance(mensaje, MensajeChat) or mensaje.numero in self._numeros:
            return False
        posicion = len(self._cola)
        for anterior in reversed(self._cola):
            if anterior.numero < mensaje.numero:
                break
            posicion -= 1
        self._cola.insert(posicion, mensaje)
        self._numeros.add(mensaje.numero)
        self._recortar()
        # Más viejo que todo lo guardado con la cola llena: el tope lo sacó.
        return mensaje.numero in self._numeros

    def reemplazar(self, mensajes):
        """Sync: deja exactamente estos mensajes, ordenados por número, sin
        duplicados (gana el primero) y solo los últimos `maximo`. Lo que no es
        un MensajeChat se ignora. O(m log m) por el ordenamiento."""
        unicos = {}  # número -> mensaje
        for mensaje in mensajes or ():
            if isinstance(mensaje, MensajeChat) and mensaje.numero not in unicos:
                unicos[mensaje.numero] = mensaje
        ordenados = sorted(unicos.values(), key=lambda m: m.numero)[-self.maximo:]
        self._cola = deque(ordenados)
        self._numeros = {m.numero for m in ordenados}

    def mensajes(self):
        """Tupla del más viejo al más nuevo (una copia: se puede recorrer
        mientras otro hilo agrega)."""
        return tuple(self._cola)

    def ultimo_numero(self):
        """Número del mensaje más nuevo, o 0 si está vacío."""
        return self._cola[-1].numero if self._cola else 0

    def no_leidos(self, leido_hasta, id_local):
        """Mensajes de JUGADOR de OTROS autores con número > leido_hasta (la
        insignia roja del botón; los del sistema y los propios no cuentan).
        Recorre desde el más nuevo y para en el primero ya leído: O(k)."""
        if isinstance(leido_hasta, bool) or not isinstance(leido_hasta, (int, float)):
            leido_hasta = 0
        cuenta = 0
        for mensaje in reversed(self._cola):
            if mensaje.numero <= leido_hasta:
                break
            if mensaje.tipo == JUGADOR and mensaje.autor != id_local:
                cuenta += 1
        return cuenta

    def a_lista(self):
        """[a_dict(), ...] del más viejo al más nuevo: el historial del SYNC."""
        return [mensaje.a_dict() for mensaje in self._cola]

    def __len__(self):
        return len(self._cola)

    def _recortar(self):
        """Tope: descarta los más viejos por la izquierda, O(1) cada uno."""
        while len(self._cola) > self.maximo:
            self._numeros.discard(self._cola.popleft().numero)


class CanalCelular:
    """Lo que el celular comparte por la red de la sala: el chat y la semilla + el reloj del feed.
    Lo tienen el Servidor (host) y el Cliente (invitado). Thread-safe: el hilo de red y el de pygame lo usan.

    El reloj se guarda como dos números: `_base` (segundos del celular en un
    instante) y `_origen` (ese instante en el reloj de ESTA PC). El host
    arranca en (0, ahora); el invitado, al sincronizarse, pasa a (segundos
    del host, ahora). segundos() = _base + lo que corrió el reloj local desde
    _origen: nunca hace falta volver a preguntarle la hora al host."""

    def __init__(self, semilla=None, sincronizado=True, reloj=time.perf_counter):
        self._lock = threading.RLock()
        self._reloj = reloj  # inyectable: los tests le pasan uno que mueven a mano
        self._origen = reloj()
        self._base = 0.0
        self._semilla = semilla if semilla is not None else random.randrange(1, 2**31)
        self.sincronizado = sincronizado  # host True; invitado False hasta el primer SYNC completo
        self.leido_hasta = 0  # último número de chat que esta PC ya vio (lo mueve la interfaz)
        self.silenciados = set()  # ids de red que no pueden escribir (host: los expulsados)
        self._historial = HistorialChat()
        self._ultimo_por_autor = {}  # anti-spam: autor -> segundos() de su último mensaje publicado

    @property
    def semilla(self):
        """Semilla del feed: la sortea el host; el invitado la copia en el SYNC."""
        return self._semilla

    def segundos(self):
        """Reloj del celular. Host: segundos desde que se creó (al abrir la
        sala). Invitado: los segundos del host al llegar el SYNC + lo que pasó
        desde entonces en su propio reloj (la diferencia con el host es la
        latencia de ese mensaje: milisegundos)."""
        with self._lock:
            return self._segundos()

    def _segundos(self):
        return max(0.0, self._base + (self._reloj() - self._origen))

    def sincronizar(self, semilla, segundos, mensajes_dicts):
        """Invitado, al llegar el SYNC del host: copia su semilla, su reloj y
        su historial. Tolera basura: un dato inválido se ignora (queda el
        propio) y los mensajes rotos se descartan uno por uno. Queda
        `sincronizado` cuando llegan una semilla y un reloj válidos."""
        with self._lock:
            semilla_valida = _es_entero(semilla)
            reloj_valido = _es_numero_finito(segundos) and 0 <= segundos <= MAX_RELOJ_SYNC_S
            if semilla_valida:
                self._semilla = semilla
            if reloj_valido:
                self._base = float(segundos)
                self._origen = self._reloj()
            if isinstance(mensajes_dicts, list):
                self._historial.reemplazar(
                    mensaje for mensaje in map(MensajeChat.de_dict, mensajes_dicts) if mensaje is not None)
            if semilla_valida and reloj_valido:
                self.sincronizado = True

    def publicar(self, autor, texto, tipo=JUGADOR):
        """Host: publica un mensaje en el chat de la sala. Limpia el texto,
        aplica el anti-spam por autor (INTERVALO_MINIMO_CHAT_S, no a los del
        sistema), rechaza a los silenciados (solo JUGADOR), lo sella con
        segundos() y le da el número siguiente. Todo bajo el lock: dos hilos
        que publican a la vez nunca se llevan el mismo número.
        Retorna el MensajeChat publicado, o None si no salió."""
        if not _es_entero(autor):
            return None
        with self._lock:
            ahora = self._segundos()
            if tipo == JUGADOR:
                if autor in self.silenciados:
                    return None
                ultimo = self._ultimo_por_autor.get(autor)
                if ultimo is not None and ahora - ultimo < INTERVALO_MINIMO_CHAT_S:
                    return None
            mensaje = self._historial.publicar(autor, texto, ahora, tipo)
            if mensaje is not None and tipo == JUGADOR:
                self._ultimo_por_autor[autor] = ahora  # un mensaje rechazado no reinicia la espera
            return mensaje

    def recibir(self, datos):
        """Invitado: un mensaje que difundió el host (su a_dict()). Retorna el
        MensajeChat si es nuevo y quedó guardado; None si es basura, ya estaba
        (llegó también en el SYNC) o es más viejo que todo el historial lleno."""
        mensaje = MensajeChat.de_dict(datos)
        if mensaje is None:
            return None
        with self._lock:
            return mensaje if self._historial.recibir(mensaje) else None

    def mensajes(self):
        """Copia (tupla) del historial, del más viejo al más nuevo."""
        with self._lock:
            return self._historial.mensajes()

    def ultimo_numero(self):
        with self._lock:
            return self._historial.ultimo_numero()

    def no_leidos(self, id_local):
        """Mensajes de otros jugadores que esta PC todavía no vio."""
        with self._lock:
            return self._historial.no_leidos(self.leido_hasta, id_local)

    def marcar_leidos(self):
        """La interfaz muestra el chat: todo lo que hay ya se vio."""
        with self._lock:
            self.leido_hasta = self._historial.ultimo_numero()

    def a_sync(self):
        """Lo que el host le manda a un invitado al conectarse (evento SYNC)."""
        with self._lock:
            return {"semilla": self._semilla, "t": self._segundos(), "chat": self._historial.a_lista()}
