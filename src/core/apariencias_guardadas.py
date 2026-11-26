"""Lo que cada jugador eligió en el vestidor, guardado entre partidas (lógica pura).

Se guarda en apariencias.json dentro de la carpeta de datos de usuario
(src/core/datos_usuario.py, nunca en el repositorio), una Apariencia por
puesto: J1 (teclado) y J2 (control). La usan:

    - la selección de roles local (Main._elegir_roles): V / △ abren el
      vestidor y al cerrarlo se guarda; al empezar, cada jugador sale
      vestido con lo suyo (en la ciudad, las mazmorras y el jefe);
    - el lobby Online (Online/lobby.py): J1 entra con lo que eligió la
      última vez y lo que cambie en los vestidores también se guarda.

Al cargar se valida con Apariencia.de_dict: un archivo viejo, editado a
mano o corrupto nunca impide arrancar, solo deja en AUTO lo que no sirva.
"""

import json

from src.core import datos_usuario
from src.core.apariencia import PREDETERMINADA, Apariencia

VERSION = 1
NOMBRE_ARCHIVO = "apariencias.json"
PUESTOS = 2  # J1 y J2
_en_memoria = None  # lo último guardado, por si el disco falla (solo con la ruta predeterminada)


def ruta_predeterminada():
    return datos_usuario.ruta_datos(NOMBRE_ARCHIVO)


def desde_dict(datos):
    """[Apariencia de J1, Apariencia de J2] desde lo leído del archivo."""
    lista = datos.get("jugadores") if isinstance(datos, dict) else None
    lista = lista if isinstance(lista, list) else []
    apariencias = [Apariencia.de_dict(item) for item in lista[:PUESTOS]]
    return apariencias + [PREDETERMINADA] * (PUESTOS - len(apariencias))


def a_dict(apariencias):
    lista = list(apariencias)[:PUESTOS]
    lista += [PREDETERMINADA] * (PUESTOS - len(lista))
    return {"version": VERSION, "jugadores": [(a or PREDETERMINADA).a_dict() for a in lista]}


def cargar(ruta=None):
    """Las apariencias guardadas, o todas en AUTO si no hay archivo válido
    (o lo último que se intentó guardar en esta sesión, si el disco falló)."""
    try:
        with open(ruta or ruta_predeterminada(), encoding="utf-8") as archivo:
            return desde_dict(json.load(archivo))
    except (OSError, ValueError):
        if ruta is None and _en_memoria is not None:
            return list(_en_memoria)
        return [PREDETERMINADA] * PUESTOS


def guardar(apariencias, ruta=None):
    """Escritura atómica. Retorna False si no se pudo escribir (el juego
    sigue con lo que tiene en memoria)."""
    global _en_memoria
    datos = a_dict(apariencias)
    if ruta is None:
        _en_memoria = desde_dict(datos)
    return datos_usuario.guardar_json_atomico(json.dumps(datos, ensure_ascii=False, indent=2),
                                              ruta or ruta_predeterminada())


def guardar_puesto(puesto, apariencia, ruta=None):
    """Cambia solo la apariencia del puesto `puesto` (0 = J1) y guarda."""
    apariencias = cargar(ruta)
    if 0 <= puesto < PUESTOS:
        apariencias[puesto] = apariencia or PREDETERMINADA
    return guardar(apariencias, ruta)


def para_jugador(apariencia):
    """Lo que se le asigna a un jugador: None si está toda en AUTO (así
    usa directamente la hoja de su rol), o la Apariencia."""
    return None if apariencia is None or apariencia.es_predeterminada() else apariencia
