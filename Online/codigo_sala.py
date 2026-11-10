"""Código de sala de 4 caracteres (estilo Among Us) en vez de escribir la IP.

El código guarda los últimos 20 bits de la IP del host en base 32
(4 caracteres x 5 bits). El invitado completa los 12 bits altos con su
propia IP: en una misma red LAN / Wi-Fi esos bits coinciden (p. ej. todo
10.20.x.x o 192.168.x.x). El puerto no viaja en el código: siempre es
PUERTO_DEFAULT.

Ejemplo: 10.20.54.107 -> "JPVM".

Sin dependencias de pygame; solo `ip_local()` toca la red.
"""

import socket

# 32 símbolos sin los que se confunden al leer en voz alta (I/1, O/0).
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 4
BITS_POR_CARACTER = 5
BITS_CODIGO = LARGO_CODIGO * BITS_POR_CARACTER  # 20
MASCARA_CODIGO = (1 << BITS_CODIGO) - 1


def ip_a_entero(ip):
    partes = ip.split(".")
    if len(partes) != 4:
        raise ValueError(f"IP inválida: {ip}")
    valor = 0
    for parte in partes:
        if not parte.isdigit() or not 0 <= int(parte) <= 255:
            raise ValueError(f"IP inválida: {ip}")
        valor = (valor << 8) | int(parte)
    return valor


def entero_a_ip(valor):
    return ".".join(str((valor >> desplazamiento) & 0xFF) for desplazamiento in (24, 16, 8, 0))


def generar_codigo(ip):
    """IP del host -> código de 4 caracteres."""
    n = ip_a_entero(ip) & MASCARA_CODIGO
    caracteres = []
    for i in range(LARGO_CODIGO):
        desplazamiento = BITS_POR_CARACTER * (LARGO_CODIGO - 1 - i)
        caracteres.append(ALFABETO[(n >> desplazamiento) & 0x1F])
    return "".join(caracteres)


def es_codigo(texto):
    texto = limpiar(texto)
    return len(texto) == LARGO_CODIGO and all(c in ALFABETO for c in texto)


def resolver_codigo(codigo, ip_propia):
    """Código + IP del invitado -> IP del host."""
    codigo = limpiar(codigo)
    if not es_codigo(codigo):
        raise ValueError(f"Código de sala inválido: {codigo}")
    n = 0
    for c in codigo:
        n = (n << BITS_POR_CARACTER) | ALFABETO.index(c)
    prefijo = ip_a_entero(ip_propia) & ~MASCARA_CODIGO & 0xFFFFFFFF
    return entero_a_ip(prefijo | n)


def limpiar(texto):
    return texto.strip().upper().replace(" ", "").replace("-", "")


def resolver_entrada(texto, ip_propia, puerto_default):
    """Lo que escribe el invitado -> (ip, puerto).

    Acepta un código de sala ("KMHB" o "KMHB:8080"), una IP ("10.20.54.107") o
    una IP con puerto ("10.20.54.107:8080"). Lanza ValueError si no es ninguno.
    """
    texto = limpiar(texto)
    texto = texto.replace(",", ".")  # punto del teclado numérico en algunos layouts

    base, sep, puerto_str = texto.partition(":")
    puerto = puerto_default
    if sep:
        if not puerto_str.isdigit() or not 0 < int(puerto_str) < 65536:
            raise ValueError(f"Puerto inválido: {puerto_str}")
        puerto = int(puerto_str)

    if es_codigo(base):
        return resolver_codigo(base, ip_propia), puerto

    ip_a_entero(base)
    return base, puerto


def ip_local():
    """IP de esta máquina en la red local (127.0.0.1 si no hay red)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
