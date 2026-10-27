import pytest

from Online.codigo_sala import (
    ALFABETO, LARGO_CODIGO, es_codigo, generar_codigo, resolver_codigo, resolver_entrada,
)


@pytest.mark.parametrize("ip", ["10.20.54.107", "192.168.1.15", "192.168.0.255", "172.16.5.4"])
def test_ida_y_vuelta_en_la_misma_red(ip):
    codigo = generar_codigo(ip)
    assert len(codigo) == LARGO_CODIGO
    assert all(c in ALFABETO for c in codigo)
    ip_invitado = ip.rsplit(".", 1)[0] + ".200"
    assert resolver_codigo(codigo, ip_invitado) == ip


def test_invitado_en_otra_subred_del_mismo_bloque():
    codigo = generar_codigo("10.20.54.107")
    assert resolver_codigo(codigo, "10.20.99.3") == "10.20.54.107"


def test_misma_pc():
    assert resolver_codigo(generar_codigo("127.0.0.1"), "127.0.0.1") == "127.0.0.1"


def test_entrada_acepta_codigo_en_minusculas_y_con_espacios():
    codigo = generar_codigo("10.20.54.107")
    texto = " ".join(codigo.lower())
    assert resolver_entrada(texto, "10.20.54.1", 7777) == ("10.20.54.107", 7777)


def test_entrada_acepta_ip_y_puerto():
    assert resolver_entrada("10.20.54.107", "10.20.54.1", 7777) == ("10.20.54.107", 7777)
    assert resolver_entrada("10.20.54.107:7000", "10.20.54.1", 7777) == ("10.20.54.107", 7000)


@pytest.mark.parametrize("texto", ["1020541077777:7777", "ABC", "AB0O", "10.20.54", "10.20.54.107:abc"])
def test_entrada_invalida(texto):
    with pytest.raises(ValueError):
        resolver_entrada(texto, "10.20.54.1", 7777)


def test_es_codigo_rechaza_caracteres_confusos():
    assert not es_codigo("IO01")
