"""Registro de errores del modo Online (sin Pygame).

Regla del modo Online: un error de la sincronización NUNCA cierra el
juego. Quien lo atrapa llama a registrar(); aquí se anota el traceback
completo en Online/errores_online.log (para arreglarlo después) y se
avisa una sola vez por consola, y la partida sigue con el frame
siguiente.

    try:
        ...
    except Exception:
        registro_errores.registrar("AdaptadorOnlineHost.actualizar")

Cada error distinto (mismo contexto + misma excepción) se escribe la
primera vez y luego cada REPETICIONES_ENTRE_AVISOS veces, así un error
que se repite en cada frame (60 por segundo) no llena el disco.
"""

import sys
import time
import traceback
from pathlib import Path

RUTA_LOG = Path(__file__).with_name("errores_online.log")
TAMANIO_MAXIMO_LOG = 1_000_000  # bytes: al pasarlo, el archivo empieza de cero
REPETICIONES_ENTRE_AVISOS = 600  # ~10 s de un error que se repite en cada frame

_vistos = {}  # firma del error -> veces que ocurrió


def registrar(contexto, error=None):
    """Anota la excepción que se está manejando (o `error`) con su
    traceback. Nunca lanza: si no se puede escribir el archivo, solo
    queda el aviso por consola."""
    try:
        if error is None:
            error = sys.exc_info()[1]
        detalle = "".join(traceback.format_exception(type(error), error, error.__traceback__)) if error else ""
        firma = (contexto, type(error).__name__, str(error))
        veces = _vistos.get(firma, 0) + 1
        _vistos[firma] = veces
        if veces != 1 and veces % REPETICIONES_ENTRE_AVISOS != 0:
            return
        encabezado = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {contexto} (vez {veces})"
        print(f"[Online] Error atrapado en {contexto}: {type(error).__name__}: {error} "
              f"(el juego sigue; detalle en {RUTA_LOG.name})", file=sys.stderr)
        _escribir(f"{encabezado}\n{detalle}\n")
    except Exception:  # noqa: BLE001 - el registro jamás debe tumbar el juego
        pass


def _escribir(texto):
    try:
        if RUTA_LOG.exists() and RUTA_LOG.stat().st_size > TAMANIO_MAXIMO_LOG:
            RUTA_LOG.write_text("", encoding="utf-8")
        with RUTA_LOG.open("a", encoding="utf-8") as archivo:
            archivo.write(texto)
    except OSError:
        pass
