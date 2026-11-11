"""Diagnóstico de red del modo Online: ping real, nombre del Wi-Fi y por
qué falló una conexión.

Sin pygame. Las funciones puras (`ssid_desde_netsh`,
`clasificar_error_conexion`, `formatear_ms`) están separadas de las que
tocan la red o llaman a `netsh`, para poder probarlas en aislado.
"""

import errno
import select
import socket
import subprocess
import sys
import threading
import time

from Online.codigo_sala import ip_local

# Cada cuánto el host y cada invitado se mandan PING por el socket de la sala.
INTERVALO_PING_S = 1.0
# Peso de la medición nueva en el promedio móvil (evita que el número salte).
SUAVIZADO_PING = 0.3

# Ping a internet = lo que tarda en abrirse una conexión TCP (SYN -> SYN/ACK
# es un viaje de ida y vuelta). No necesita permisos de administrador, a
# diferencia del ping ICMP.
DESTINOS_INTERNET = (("1.1.1.1", 443), ("8.8.8.8", 443))
INTERVALO_INTERNET_S = 2.0
TIMEOUT_INTERNET_S = 1.5

TIMEOUT_COMANDO_S = 5.0
LIMITE_ENVIO_S = 4.0  # Tolera fluctuaciones y jitter de Wi-Fi sin desconectar prematuramente

# Tipos de error al conectar
TIMEOUT = "timeout"
RECHAZADA = "rechazada"
SIN_RUTA = "sin_ruta"
DIRECCION = "direccion"
OTRO = "otro"

_WINERROR_SIN_RUTA = (10051, 10065)  # WSAENETUNREACH, WSAEHOSTUNREACH
_ERRNO_SIN_RUTA = (errno.ENETUNREACH, errno.EHOSTUNREACH)
_WINERROR_TIMEOUT = 10060            # WSAETIMEDOUT

CONSEJOS = {
    TIMEOUT: (
        "El Host no respondió: el Firewall de su PC o la red bloquean la entrada.",
        "1. En la PC del Host, dentro de la sala, presiona [F] y acepta el permiso de Windows.",
        "2. Ambas PCs en la MISMA red Wi-Fi (el Host la ve en ROOM SETTINGS).",
        "3. Redes de invitados o de universidad aíslan equipos: prueben el hotspot de un celular.",
    ),
    RECHAZADA: (
        "Esa PC respondió, pero no tiene una sala abierta.",
        "Revisa que el Host siga en la sala de espera y que el código sea el correcto.",
    ),
    SIN_RUTA: (
        "No hay camino de red hasta esa IP: las PCs están en redes distintas.",
        "Conecten ambas PCs al mismo Wi-Fi (o al hotspot de un celular).",
    ),
    DIRECCION: (
        "La dirección no es válida.",
        "Escribe el código de 4 caracteres que muestra el Host.",
    ),
    OTRO: (
        "Revisa que ambas PCs estén en la misma red y que el Host tenga la sala abierta.",
    ),
}


def ahora_ms():
    """Reloj monótono en ms. time.time() en Windows con Python < 3.13
    avanza de a ~16 ms y en una LAN mediría 0 ms."""
    return time.perf_counter() * 1000.0


def suavizar(anterior, nuevo):
    """Promedio móvil exponencial; con `anterior` None devuelve `nuevo`."""
    if anterior is None:
        return nuevo
    return anterior + SUAVIZADO_PING * (nuevo - anterior)


def formatear_ms(ms):
    if ms is None:
        return "—"
    if ms < 1:
        return "<1 ms"
    return f"{round(ms)} ms"


def clasificar_error_conexion(error):
    """Excepción de connect() -> TIMEOUT, RECHAZADA, SIN_RUTA, DIRECCION u OTRO."""
    if isinstance(error, ConnectionRefusedError):
        return RECHAZADA
    if isinstance(error, socket.gaierror):
        return DIRECCION
    if isinstance(error, (TimeoutError, socket.timeout)):
        return TIMEOUT
    winerror = getattr(error, "winerror", None)
    if winerror in _WINERROR_SIN_RUTA or getattr(error, "errno", None) in _ERRNO_SIN_RUTA:
        return SIN_RUTA
    if winerror == _WINERROR_TIMEOUT:
        return TIMEOUT
    return OTRO


def sin_retraso(sock):
    """Apaga el algoritmo de Nagle: los mensajes pequeños (input, ping)
    salen al instante en vez de esperar hasta ~200 ms para agruparse."""
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


def enviar_todo(sock, datos, limite_s=LIMITE_ENVIO_S):
    """sendall() para sockets no bloqueantes.

    sendall() en un socket no bloqueante lanza BlockingIOError si el búfer
    del sistema se llena y puede dejar un mensaje a medias, con lo que el
    otro lado ya no sabe dónde empieza el siguiente. Aquí se espera con
    select() a que haya espacio; si en `limite_s` no avanza, TimeoutError.
    """
    vista = memoryview(datos)
    fin = time.monotonic() + limite_s
    while vista:
        try:
            enviados = sock.send(vista)
        except (BlockingIOError, InterruptedError):
            restante = fin - time.monotonic()
            if restante <= 0:
                raise TimeoutError("el otro lado no está leyendo")
            select.select([], [sock], [], restante)
            continue
        vista = vista[enviados:]


def medir_rtt_tcp(destino, timeout=TIMEOUT_INTERNET_S):
    """Milisegundos que tarda en abrirse una conexión TCP a `destino`, o None."""
    inicio = ahora_ms()
    try:
        conexion = socket.create_connection(destino, timeout=timeout)
    except OSError:
        return None
    rtt = ahora_ms() - inicio
    conexion.close()
    return rtt


def ejecutar_comando(argumentos):
    """Corre un comando de consola de Windows sin abrir ventana.
    Retorna (código de salida, texto) o (None, "") si no se pudo correr."""
    try:
        resultado = subprocess.run(
            argumentos, capture_output=True, timeout=TIMEOUT_COMANDO_S,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    codificacion = "oem" if sys.platform == "win32" else "utf-8"
    return resultado.returncode, resultado.stdout.decode(codificacion, errors="replace")


def ssid_desde_netsh(texto):
    """Nombre del Wi-Fi en la salida de `netsh wlan show interfaces`, o None."""
    for linea in texto.splitlines():
        clave, separador, valor = linea.partition(":")
        if separador and clave.strip().upper() == "SSID" and valor.strip():
            return valor.strip()
    return None


def nombre_red_wifi():
    """Nombre del Wi-Fi al que está conectada esta PC, o None (cable, sin red u otro sistema)."""
    if sys.platform != "win32":
        return None
    codigo, texto = ejecutar_comando(["netsh", "wlan", "show", "interfaces"])
    return ssid_desde_netsh(texto) if codigo == 0 else None


class InfoRed:
    """IP y Wi-Fi de esta PC, leídos en un hilo (netsh tarda ~0.3 s)."""

    def __init__(self):
        self.ip = None
        self.wifi = None
        self.listo = False
        threading.Thread(target=self._leer, daemon=True).start()

    def _leer(self):
        self.ip = ip_local()
        self.wifi = nombre_red_wifi()
        self.listo = True

    def describir(self):
        if not self.listo:
            return "leyendo tu red..."
        red = f"Wi-Fi {self.wifi}" if self.wifi else "red por cable / sin Wi-Fi"
        return f"Tu PC: {self.ip} ({red})"


class MedidorInternet:
    """Hilo que mide el ping a internet cada INTERVALO_INTERNET_S segundos.

    ms     — último ping en ms (float) o None si no hay internet
    medido — True cuando terminó la primera medición
    """

    def __init__(self, destinos=DESTINOS_INTERNET, intervalo=INTERVALO_INTERNET_S):
        self.ms = None
        self.medido = False
        self._destinos = destinos
        self._intervalo = intervalo
        self._cancelar = threading.Event()

    def iniciar(self):
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def detener(self):
        self._cancelar.set()

    def _loop(self):
        while not self._cancelar.is_set():
            rtt = self._medir()
            self.ms = None if rtt is None else suavizar(self.ms, rtt)
            self.medido = True
            self._cancelar.wait(self._intervalo)

    def _medir(self):
        """El menor de los destinos: un pico en uno solo no infla el número."""
        medidas = [rtt for rtt in (medir_rtt_tcp(d) for d in self._destinos) if rtt is not None]
        return min(medidas) if medidas else None
