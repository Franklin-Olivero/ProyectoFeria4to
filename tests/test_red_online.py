import base64
import errno
import socket
import threading
import time

import pytest

from Online import red_local
from Online.cliente import Cliente
from Online.firewall import comando_codificado, nombre_regla, script_permitir
from Online.protocolo import PING, PONG
from Online.red_local import (
    DIRECCION, OTRO, RECHAZADA, SIN_RUTA, TIMEOUT, clasificar_error_conexion,
    enviar_todo, formatear_ms, medir_rtt_tcp, ssid_desde_netsh, suavizar,
)
from Online.servidor import Servidor

SALIDA_NETSH = """
Hay 1 interfaz en el sistema:

    Nombre                 : Wi-Fi
    Descripción            : Intel(R) Wi-Fi 6 AX201
    Estado                 : conectado
    SSID                   : F.NAVARRO
    AP BSSID               : d8:32:14:e3:02:41
    Banda                  : 2,4 GHz
"""


def test_ssid_ignora_bssid():
    assert ssid_desde_netsh(SALIDA_NETSH) == "F.NAVARRO"


def test_ssid_con_dos_puntos_en_el_nombre():
    assert ssid_desde_netsh("    SSID                   : Casa:5G\n") == "Casa:5G"


def test_ssid_sin_wifi():
    assert ssid_desde_netsh("No hay ninguna interfaz inalámbrica en el sistema.") is None


@pytest.mark.parametrize("error, tipo", [
    (TimeoutError("timed out"), TIMEOUT),
    (socket.timeout("timed out"), TIMEOUT),
    (ConnectionRefusedError(10061, "rechazada"), RECHAZADA),
    (OSError(errno.EHOSTUNREACH, "sin ruta"), SIN_RUTA),
    (socket.gaierror(11001, "getaddrinfo failed"), DIRECCION),
    (OSError("otra cosa"), OTRO),
])
def test_clasificar_error_conexion(error, tipo):
    assert clasificar_error_conexion(error) == tipo


def test_formatear_ms():
    assert formatear_ms(None) == "—"
    assert formatear_ms(0.3) == "<1 ms"
    assert formatear_ms(12.6) == "13 ms"


def test_suavizar():
    assert suavizar(None, 40) == 40
    assert 40 < suavizar(40, 100) < 100


def test_medir_rtt_tcp_local():
    servidor = socket.create_server(("127.0.0.1", 0))
    try:
        rtt = medir_rtt_tcp(servidor.getsockname(), timeout=1.0)
    finally:
        servidor.close()
    assert rtt is not None and rtt >= 0


def test_medir_rtt_tcp_sin_servidor_da_none():
    libre = socket.socket()
    libre.bind(("127.0.0.1", 0))
    puerto = libre.getsockname()[1]
    libre.close()
    assert medir_rtt_tcp(("127.0.0.1", puerto), timeout=0.5) is None


def _par_con_buffers_chicos():
    a, b = socket.socketpair()
    a.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    b.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
    a.setblocking(False)
    return a, b


def test_enviar_todo_no_corta_mensajes_con_socket_no_bloqueante():
    a, b = _par_con_buffers_chicos()
    datos = bytes(range(256)) * 8000  # ~2 MB: llena el búfer varias veces
    recibido = bytearray()

    def leer():
        while len(recibido) < len(datos):
            trozo = b.recv(65536)
            if not trozo:
                break
            recibido.extend(trozo)

    lector = threading.Thread(target=leer)
    lector.start()
    try:
        enviar_todo(a, datos, limite_s=10)
        lector.join(10)
    finally:
        a.close()
        b.close()
    assert bytes(recibido) == datos


class _SocketLleno:
    """Socket cuyo búfer de envío nunca se vacía (el otro lado no lee)."""

    def send(self, datos):
        raise BlockingIOError


def test_enviar_todo_se_rinde_si_nadie_lee(monkeypatch):
    monkeypatch.setattr(red_local.select, "select", lambda r, w, x, t: (time.sleep(t), [], []))
    with pytest.raises(TimeoutError):
        enviar_todo(_SocketLleno(), b"x" * 100, limite_s=0.1)


def test_script_firewall_abre_solo_el_puerto_y_escapa_la_ruta():
    script = script_permitir(7777, r"C:\Users\O'Brien\python.exe")
    assert "-LocalPort 7777" in script
    assert "-Protocol TCP" in script
    assert nombre_regla(7777) in script
    assert r"$exe = 'C:\Users\O''Brien\python.exe'" in script
    assert base64.b64decode(comando_codificado(script)).decode("utf-16-le") == script


def _esperar(condicion, limite_s=3.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def test_host_e_invitado_miden_ping_real(monkeypatch):
    monkeypatch.setattr(red_local, "INTERVALO_PING_S", 0.05)
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.ping_medido and servidor.latencia_promedio() is not None)
        assert cliente._socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
        assert servidor.sala.grafo.existe_arista(0, 1)
        # PING/PONG se responden por dentro: no ensucian la cola del lobby.
        tipos = {msg.get("tipo") for msg in cliente.leer_mensajes()}
        assert not tipos & {PING, PONG}
    finally:
        cliente.detener()
        servidor.detener()


def test_desconexion_limpia_la_latencia(monkeypatch):
    monkeypatch.setattr(red_local, "INTERVALO_PING_S", 0.05)
    servidor = Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    cliente = Cliente()
    try:
        cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: servidor.latencia_promedio() is not None)
        cliente.desconectar()
        assert _esperar(lambda: servidor.latencia_promedio() is None)
        assert servidor.sala.cantidad() == 1
    finally:
        servidor.detener()
