"""Regla del Firewall de Windows para que otras PCs puedan entrar a la sala.

Windows bloquea las conexiones entrantes en las redes "Públicas" (así
marca casi cualquier Wi-Fi nuevo) salvo que una regla las permita, y una
regla de BLOQUEO para un programa gana sobre cualquier regla que permita.
Por eso el invitado veía "timed out": sus paquetes llegaban y Windows los
descartaba sin responder.

El Host lo arregla una sola vez con [F] en la sala: aparece el permiso de
administrador de Windows y un PowerShell oculto
    1. crea la regla "Civitas-Online-TCP-<puerto>" (entrante, solo TCP en
       ese puerto, en todos los tipos de red) y
    2. desactiva los bloqueos entrantes de ESTE python.exe (Windows los
       crea cuando alguien cierra su aviso del Firewall con "Cancelar").
No abre otros puertos ni cambia el tipo de red.
"""

import base64
import ctypes
import os
import sys
import threading
import time

from Online.red_local import ejecutar_comando

NOMBRE_REGLA = "Civitas-Online-TCP-{puerto}"
ESPERA_REGLA_S = 45  # tras aceptar el permiso, cuánto se espera a que aparezca la regla

# Estados que dibuja la sala
NO_APLICA = "no_aplica"   # no es Windows
REVISANDO = "revisando"
FALTA = "falta"
ESPERANDO = "esperando"   # se pidió el permiso de administrador
PERMITIDO = "permitido"
DENEGADO = "denegado"     # se canceló el permiso o no se creó la regla


def es_windows():
    return sys.platform == "win32"


def nombre_regla(puerto):
    return NOMBRE_REGLA.format(puerto=int(puerto))


def ejecutable_actual():
    """Ruta del python.exe que corre este proceso, la que ve el Firewall
    (en un venv de Windows sys.executable es solo el lanzador)."""
    if es_windows():
        try:
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.QueryFullProcessImageNameW.argtypes = (
                wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
            kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
            buffer = ctypes.create_unicode_buffer(32768)
            largo = wintypes.DWORD(len(buffer))
            if kernel32.QueryFullProcessImageNameW(kernel32.GetCurrentProcess(), 0, buffer,
                                                   ctypes.byref(largo)):
                return buffer.value
        except (OSError, AttributeError):
            pass
    return getattr(sys, "_base_executable", None) or sys.executable


def script_permitir(puerto, ejecutable):
    """Script de PowerShell que corre con permisos de administrador."""
    exe = ejecutable.replace("'", "''")  # comilla simple escapada para PowerShell
    return (
        "$ErrorActionPreference = 'SilentlyContinue'\n"
        f"$nombre = '{nombre_regla(puerto)}'\n"
        f"$exe = '{exe}'\n"
        "Get-NetFirewallRule -DisplayName $nombre | Remove-NetFirewallRule\n"
        "New-NetFirewallRule -DisplayName $nombre -Description 'Civitas: sala del modo Online' "
        f"-Direction Inbound -Action Allow -Protocol TCP -LocalPort {int(puerto)} -Profile Any | Out-Null\n"
        "Get-NetFirewallRule -Direction Inbound -Action Block -Enabled True | Where-Object {\n"
        "    $programa = ($_ | Get-NetFirewallApplicationFilter).Program\n"
        "    $programa -and ([Environment]::ExpandEnvironmentVariables($programa) -eq $exe)\n"
        "} | Disable-NetFirewallRule\n"
    )


def comando_codificado(script):
    """-EncodedCommand de PowerShell: Base64 del script en UTF-16LE (sin problemas de comillas)."""
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def ruta_powershell():
    """Ruta fija de System32: no se eleva un powershell.exe cualquiera del PATH."""
    raiz = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(raiz, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def regla_existe(puerto):
    """True si ya existe la regla de Civitas (netsh sale con 0 si la encuentra)."""
    codigo, _ = ejecutar_comando(
        ["netsh", "advfirewall", "firewall", "show", "rule", f"name={nombre_regla(puerto)}"])
    return codigo == 0


def pedir_permiso(puerto):
    """Abre el permiso de administrador de Windows y, si se acepta, corre el
    script oculto. Bloquea hasta que el usuario responde. True si se aceptó."""
    if not es_windows():
        return False
    parametros = ("-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand "
                  + comando_codificado(script_permitir(puerto, ejecutable_actual())))
    try:
        from ctypes import wintypes
        shell32 = ctypes.WinDLL("shell32")
        shell32.ShellExecuteW.argtypes = (
            wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
            wintypes.LPCWSTR, ctypes.c_int)
        shell32.ShellExecuteW.restype = ctypes.c_void_p
        resultado = shell32.ShellExecuteW(None, "runas", ruta_powershell(), parametros, None, 0)
    except (OSError, AttributeError):
        return False
    # ShellExecuteW devuelve un valor > 32 si lanzó el proceso.
    return (resultado or 0) > 32


class EstadoFirewall:
    """Estado de la regla para la sala del Host; las consultas a Windows
    corren en hilos para no congelar la pantalla."""

    def __init__(self, puerto):
        self.puerto = puerto
        self.estado = REVISANDO if es_windows() else NO_APLICA
        if es_windows():
            threading.Thread(target=self._revisar, daemon=True).start()

    def permitir(self):
        """Tecla F: pide el permiso de administrador (otra vez si ya estaba)."""
        if self.estado in (NO_APLICA, ESPERANDO):
            return
        self.estado = ESPERANDO
        threading.Thread(target=self._permitir, daemon=True).start()

    def _revisar(self):
        existe = regla_existe(self.puerto)
        if self.estado == REVISANDO:
            self.estado = PERMITIDO if existe else FALTA

    def _permitir(self):
        if not pedir_permiso(self.puerto):
            self.estado = DENEGADO
            return
        limite = time.monotonic() + ESPERA_REGLA_S
        while time.monotonic() < limite:
            if regla_existe(self.puerto):
                self.estado = PERMITIDO
                return
            time.sleep(1.0)
        self.estado = DENEGADO
