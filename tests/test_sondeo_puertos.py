import socket
import pytest

from Online.servidor import Servidor, PUERTOS_CANDIDATOS
from Online.codigo_sala import generar_codigo, resolver_entrada
from Online.sondeo_puertos import probar_puerto


def test_resolver_entrada_con_puerto_personalizado():
    cod = generar_codigo("10.20.54.107")
    ip, puerto = resolver_entrada(f"{cod}:8080", "10.20.54.1", 7777)
    assert ip == "10.20.54.107"
    assert puerto == 8080


def test_resolver_entrada_ip_con_puerto():
    ip, puerto = resolver_entrada("192.168.1.50:9000", "192.168.1.1", 7777)
    assert ip == "192.168.1.50"
    assert puerto == 9000


def test_resolver_entrada_sin_puerto_usa_default():
    cod = generar_codigo("10.20.54.107")
    ip, puerto = resolver_entrada(cod, "10.20.54.1", 8080)
    assert ip == "10.20.54.107"
    assert puerto == 8080


def test_probar_puerto_detecta_puerto_cerrado():
    ok, ms, detalle = probar_puerto("127.0.0.1", 59999, timeout=0.2)
    assert ok is False


def test_servidor_fallback_cuando_puerto_ocupado():
    puerto_ocupado = PUERTOS_CANDIDATOS[0]
    sock_ocupado = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock_ocupado.bind(("127.0.0.1", puerto_ocupado))
        sock_ocupado.listen(1)

        servidor = Servidor()
        ip = servidor.iniciar(puerto=puerto_ocupado, interfaz="127.0.0.1")
        assert ip is not None
        assert servidor.puerto != puerto_ocupado
        assert servidor.puerto in PUERTOS_CANDIDATOS
        servidor.detener()
    except OSError:
        pass
    finally:
        sock_ocupado.close()
