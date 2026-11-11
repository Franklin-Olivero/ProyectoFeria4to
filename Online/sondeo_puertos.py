"""Herramienta de diagnóstico y sondeo de puertos para Civitas Online.

Especialmente útil en redes universitarias o públicas donde algunos puertos
están bloqueados por firewall o existe aislamiento de clientes (AP Isolation).

Uso desde terminal (en la carpeta del proyecto):
    Laptop 1 (Host):     python -m Online.sondeo_puertos host
    Laptop 2 (Invitado): python -m Online.sondeo_puertos test <IP_DEL_HOST>
"""

import socket
import subprocess
import sys
import time

from Online.codigo_sala import ip_local
from Online.servidor import PUERTOS_CANDIDATOS

TIMEOUT_SONDEO = 1.8
SALUDO_PRUEBA = b"CIVITAS_PING\n"
RESPUESTA_PRUEBA = b"CIVITAS_OK\n"


def probar_ping(ip):
    """Prueba si la IP responde a ICMP ping."""
    param = "-n" if sys.platform == "win32" else "-c"
    try:
        resultado = subprocess.run(
            ["ping", param, "1", "-w", "1500", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2.5,
        )
        return resultado.returncode == 0
    except Exception:
        return False


def probar_puerto(ip, puerto, timeout=TIMEOUT_SONDEO):
    """Intenta conectar a ip:puerto y mide latencia en ms.
    Retorna (True, ms, "OK") o (False, None, razon)."""
    t0 = time.perf_counter()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, puerto))
        try:
            s.sendall(SALUDO_PRUEBA)
            s.settimeout(1.0)
            s.recv(64)
        except OSError:
            pass
        ms = round((time.perf_counter() - t0) * 1000, 1)
        s.close()
        return True, ms, "Abierto y respondiendo"
    except socket.timeout:
        s.close()
        return False, None, "Timeout (bloqueado por firewall o red)"
    except ConnectionRefusedError:
        s.close()
        return False, None, "Conexión rechazada (puerto libre pero sin servidor)"
    except OSError as e:
        s.close()
        return False, None, f"Error: {e}"


def ejecutar_host(puerto_especifico=None):
    """Abre servidores de prueba en los puertos candidatos para escuchar sondas."""
    puertos = [puerto_especifico] if puerto_especifico else list(PUERTOS_CANDIDATOS)
    ip = ip_local()

    sockets_abiertos = []
    puertos_listos = []

    print("\n" + "=" * 65)
    print("   CIVITAS ONLINE - DIAGNÓSTICO DE PUERTOS (MODO HOST)")
    print("=" * 65)
    print(f"[*] Tu IP local en la red: {ip}")
    print("[*] Abriendo listeners de prueba...")

    for p in puertos:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", p))
            sock.listen(5)
            sock.setblocking(False)
            sockets_abiertos.append((sock, p))
            puertos_listos.append(p)
        except OSError as e:
            print(f"    [-] Puerto {p}: No se pudo abrir ({e})")

    if not sockets_abiertos:
        print("\n[!] ERROR: No se pudo abrir ningún puerto candidato.")
        return

    print(f"[+] Escuchando en {len(puertos_listos)} puertos: {puertos_listos}")
    print("\n--> AHORA EN LA OTRA LAPTOP EJECUTA:")
    print(f"    python -m Online.sondeo_puertos test {ip}\n")
    print("Esperando conexiones de prueba... (Presiona Ctrl+C para finalizar)")

    try:
        while True:
            for sock, p in sockets_abiertos:
                try:
                    cliente, addr = sock.accept()
                    print(f"\n[!] ¡SONDA RECIBIDA! Cliente conectado desde {addr[0]}:{addr[1]} al puerto {p} [OK]")
                    try:
                        cliente.sendall(RESPUESTA_PRUEBA)
                    except OSError:
                        pass
                    cliente.close()
                except BlockingIOError:
                    pass
                except OSError:
                    pass
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[*] Cerrando servidores de prueba. ¡Listo!")
    finally:
        for sock, _ in sockets_abiertos:
            try:
                sock.close()
            except OSError:
                pass


def ejecutar_test(ip_host):
    """Prueba conectividad contra el host."""
    print("\n" + "=" * 65)
    print(f"   CIVITAS ONLINE - PROBANDO CONEXIÓN A {ip_host}")
    print("=" * 65)

    print("[*] Probando ping ICMP...")
    ping_ok = probar_ping(ip_host)
    if ping_ok:
        print("    [+] Ping respondió correctamente.")
    else:
        print("    [-] Ping no respondió (puede estar bloqueado por la red o firewall).")

    print("\n[*] Probando puertos candidatos...")
    print(f"{'PUERTO':<10} {'ESTADO':<15} {'LATENCIA':<12} {'DETALLE'}")
    print("-" * 65)

    puertos_abiertos = []
    for p in PUERTOS_CANDIDATOS:
        ok, ms, detalle = probar_puerto(ip_host, p)
        if ok:
            estado = "ABIERTO [OK]"
            lat = f"{ms} ms"
            puertos_abiertos.append(p)
        else:
            estado = "BLOQUEADO"
            lat = "-"
        print(f"{p:<10} {estado:<15} {lat:<12} {detalle}")

    print("-" * 65)
    if puertos_abiertos:
        print(f"\n[+] ¡ÉXITO! Puertos disponibles encontrados: {puertos_abiertos}")
        print(f"    Te recomendamos usar el puerto: {puertos_abiertos[0]}")
        print(f"    El juego conectará automáticamente, o puedes escribir: {ip_host}:{puertos_abiertos[0]}")
    else:
        print("\n[!] ALERTA CRÍTICA: NINGÚN PUERTO RESPONDIÓ.")
        print("    Diagnóstico:")
        if not ping_ok:
            print("    1. La red WiFi de la universidad tiene Aislamiento de Clientes (AP Isolation).")
            print("       Los routers no permiten que dos computadoras se comuniquen directamente.")
        else:
            print("    1. El Firewall de Windows en la laptop Host está bloqueando las conexiones entrantes.")
            print("       En la sala de espera del Host, presiona la tecla [F] para autorizar el Firewall.")
        print("\n    SOLUCIÓN INMEDIATA PARA JUGAR EN LA UNIVERSIDAD:")
        print("    * Activa la 'Zona con cobertura inalámbrica' (Hotspot / Compartir Internet) en tu celular.")
        print("    * Conecta AMBAS laptops a ese Wi-Fi del celular.")
        print("    * Como la partida es en red local LAN, ¡NO consume tus datos móviles!")
        print("=" * 65 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python -m Online.sondeo_puertos host [puerto]")
        print("  python -m Online.sondeo_puertos test <IP_DEL_HOST>")
        return

    comando = sys.argv[1].lower()
    if comando == "host":
        puerto = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        ejecutar_host(puerto)
    elif comando in ("test", "invitado", "join"):
        if len(sys.argv) < 3:
            print("Error: Debes indicar la IP del host. Ej: python -m Online.sondeo_puertos test 10.20.54.107")
            return
        ejecutar_test(sys.argv[2])
    else:
        print(f"Comando desconocido: {comando}")


if __name__ == "__main__":
    main()

