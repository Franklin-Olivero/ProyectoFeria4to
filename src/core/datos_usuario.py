"""Dónde guarda el juego los datos del jugador (lógica pura, sin Pygame).

Los ajustes no van dentro del repositorio: viven en la carpeta de datos
de usuario del sistema operativo, así cada jugador conserva los suyos y
git nunca los ve.

    Windows : %APPDATA%\\Civitas
    macOS   : ~/Library/Application Support/Civitas
    Linux   : $XDG_DATA_HOME/civitas (o ~/.local/share/civitas)

CIVITAS_DATOS (variable de entorno) la reemplaza: la usan los tests y el
recorrido headless para no tocar los ajustes reales del jugador.
"""

import os
import sys

NOMBRE_APLICACION = "Civitas"
VARIABLE_CARPETA = "CIVITAS_DATOS"


def carpeta_datos(entorno=None, plataforma=None, inicio=None):
    """Carpeta de datos de usuario (no la crea). `entorno`, `plataforma`
    e `inicio` (la carpeta personal) se pueden inyectar en los tests."""
    entorno = os.environ if entorno is None else entorno
    plataforma = sys.platform if plataforma is None else plataforma
    inicio = os.path.expanduser("~") if inicio is None else inicio
    if entorno.get(VARIABLE_CARPETA):
        return entorno[VARIABLE_CARPETA]
    if plataforma.startswith("win"):
        return os.path.join(entorno.get("APPDATA") or os.path.join(inicio, "AppData", "Roaming"), NOMBRE_APLICACION)
    if plataforma == "darwin":
        return os.path.join(inicio, "Library", "Application Support", NOMBRE_APLICACION)
    base = entorno.get("XDG_DATA_HOME") or os.path.join(inicio, ".local", "share")
    return os.path.join(base, NOMBRE_APLICACION.lower())


def ruta_datos(nombre_archivo, **kwargs):
    """Ruta de `nombre_archivo` dentro de la carpeta de datos de usuario."""
    return os.path.join(carpeta_datos(**kwargs), nombre_archivo)


def guardar_json_atomico(datos_json, ruta):
    """Escribe el texto `datos_json` en `ruta` (crea la carpeta si falta)
    con un temporal + rename: un cierre a mitad no deja el archivo cortado.
    Retorna False si no se pudo escribir."""
    temporal = ruta + ".tmp"
    try:
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        with open(temporal, "w", encoding="utf-8") as archivo:
            archivo.write(datos_json)
        os.replace(temporal, ruta)
        return True
    except OSError:
        return False
