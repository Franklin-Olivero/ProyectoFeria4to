"""Ajustes de audio del jugador (lógica pura, sin Pygame).

Cuatro valores, guardados en ajustes_audio.json dentro de la carpeta de
datos de usuario (src/core/datos_usuario.py), cada vez que cambian:

    volumen_general  0-100  multiplica todo
    volumen_musica   0-100  pistas
    volumen_efectos  0-100  efectos y sonidos de interfaz
    silencio         bool   tecla N: todo a 0 sin perder los volúmenes

Al cargar se valida campo por campo: lo ausente, de otro tipo o corrupto
toma su valor predeterminado y los números se recortan a 0-100, así un
archivo viejo o editado a mano nunca impide arrancar. Si todavía no hay
archivo, se rescatan los volúmenes de un preferencias.json viejo.

volumen_efectivo es la cuenta que aplica el gestor (src/audio/gestor_audio.py)
a CADA sonido y a la música en curso:

    general × categoría (música o efectos) × mezcla de la categoría
    × ganancia del ID × atenuación (pausa) × (0 si silencio)
"""

import json
from dataclasses import asdict, dataclass, fields

from src.core import datos_usuario

VERSION = 1
NOMBRE_ARCHIVO = "ajustes_audio.json"
CAMPOS_VOLUMEN = ("volumen_general", "volumen_musica", "volumen_efectos")


@dataclass
class AjustesAudio:
    """Valores de una instalación sin ajustes guardados."""

    volumen_general: int = 100
    volumen_musica: int = 70
    volumen_efectos: int = 80
    silencio: bool = False

    def volumen_de(self, es_musica):
        """Volumen 0-100 del grupo: música o efectos (los de interfaz son efectos)."""
        return self.volumen_musica if es_musica else self.volumen_efectos


def acotar(valor):
    """Entero en 0-100 (redondea y recorta)."""
    return max(0, min(100, int(round(valor))))


def valor_valido(campo, valor):
    """`valor` ya validado para `campo`, o None si no sirve."""
    if campo in CAMPOS_VOLUMEN:
        # bool es subclase de int: True no es un volumen válido.
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor != valor:  # NaN
            return None
        return acotar(valor)
    if campo == "silencio":
        return valor if isinstance(valor, bool) else None
    return None


def desde_dict(datos):
    ajustes = AjustesAudio()
    if not isinstance(datos, dict):
        return ajustes
    for campo in fields(AjustesAudio):
        if campo.name in datos:
            valor = valor_valido(campo.name, datos[campo.name])
            if valor is not None:
                setattr(ajustes, campo.name, valor)
    return ajustes


def a_dict(ajustes):
    return {"version": VERSION, **asdict(ajustes)}


def ruta_predeterminada():
    return datos_usuario.ruta_datos(NOMBRE_ARCHIVO)


def _leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return None


def cargar(ruta=None, ruta_legado=None):
    """AjustesAudio del archivo. Si no existe o no es JSON válido:
    los volúmenes de `ruta_legado` (un preferencias.json viejo) si los
    tiene, y si no, los valores predeterminados."""
    datos = _leer_json(ruta or ruta_predeterminada())
    if datos is None and ruta_legado is not None:
        viejo = _leer_json(ruta_legado)
        if isinstance(viejo, dict):
            datos = {campo: viejo[campo] for campo in ("volumen_musica", "volumen_efectos") if campo in viejo}
    return desde_dict(datos)


def guardar(ajustes, ruta=None):
    """Guarda al instante (temporal + rename). False si no se pudo."""
    texto = json.dumps(a_dict(ajustes), ensure_ascii=False, indent=2)
    return datos_usuario.guardar_json_atomico(texto, ruta or ruta_predeterminada())


def volumen_efectivo(ajustes, es_musica, mezcla_categoria=1.0, ganancia=1.0, atenuacion=1.0, solo_general=False):
    """Volumen 0.0-1.0 con el que suena algo ahora mismo (nunca más de 1).
    `solo_general`: la banda sonora de una cinemática (voces + música + efectos
    ya mezclados) depende solo del volumen general, no del deslizador de música:
    si no, bajar la música dejaba los diálogos inaudibles."""
    if ajustes.silencio:
        return 0.0
    base = ajustes.volumen_general / 100 * (1.0 if solo_general else ajustes.volumen_de(es_musica) / 100)
    return max(0.0, min(1.0, base * mezcla_categoria * ganancia * atenuacion))
