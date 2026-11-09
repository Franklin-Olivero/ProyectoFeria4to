"""Preferencias del jugador: audio, accesibilidad y controles (lógica pura, sin Pygame).

Se guardan en un JSON pequeño (RUTA_PREFERENCIAS, junto a Main.py) cada
vez que el jugador cambia un ajuste. Al cargar se valida campo por campo:
lo que falte, tenga otro tipo o esté fuera de rango toma su valor
predeterminado, así un archivo viejo, editado a mano o corrupto nunca
impide arrancar el juego.

Quién usa cada preferencia:
    volumen_musica / volumen_efectos -> src/core/audio.py (pygame.mixer)
    filtro_daltonismo                -> src/ui/filtro_color.py (toda la pantalla)
    reducir_movimiento               -> fondo y título del menú, transición del
                                        modal y sacudida de cámara del jefe
    mostrar_cono / opacidad_cono     -> cono de apuntado (src/ui/combate_render.py)
    esquema_controles                -> vista elegida en la guía de controles
    subtitulos                       -> se guarda; el juego no tiene audio hablado.
                                        Los diálogos y eventos del modo historia
                                        ya son texto en pantalla.
    alto_contraste                   -> src/ui/filtro_color.py (toda la pantalla)
    avance_cinematicas               -> manual (el jugador avanza) o automatico
                                        (respeta el tiempo de lectura)
    velocidad_texto                  -> caracteres por segundo de diálogos y cinemáticas
"""

import json
import os
from dataclasses import asdict, dataclass, fields

VERSION = 1
RUTA_PREFERENCIAS = "preferencias.json"

FILTRO_NINGUNO = "Ninguno"
FILTROS_DALTONISMO = (FILTRO_NINGUNO, "Protanopia", "Deuteranopia", "Tritanopia")

ESQUEMA_TECLADO = "teclado"
ESQUEMA_MANDO = "mando"
ESQUEMAS_CONTROLES = (ESQUEMA_TECLADO, ESQUEMA_MANDO)

AVANCE_MANUAL = "manual"
AVANCE_AUTOMATICO = "automatico"
AVANCES_CINEMATICA = (AVANCE_MANUAL, AVANCE_AUTOMATICO)
VELOCIDADES_TEXTO = ("lenta", "normal", "rapida")
CARACTERES_POR_SEGUNDO = {"lenta": 18.0, "normal": 28.0, "rapida": 45.0}

# Opciones válidas de los campos de texto (los demás se validan por tipo).
OPCIONES_TEXTO = {
    "filtro_daltonismo": FILTROS_DALTONISMO,
    "esquema_controles": ESQUEMAS_CONTROLES,
    "avance_cinematicas": AVANCES_CINEMATICA,
    "velocidad_texto": VELOCIDADES_TEXTO,
}
# Campos enteros que son un porcentaje 0-100.
CAMPOS_PORCENTAJE = ("volumen_musica", "volumen_efectos", "opacidad_cono")


@dataclass
class Preferencias:
    """Valores predeterminados de una instalación sin preferencias guardadas."""

    volumen_musica: int = 70
    volumen_efectos: int = 80
    subtitulos: bool = False
    filtro_daltonismo: str = FILTRO_NINGUNO
    reducir_movimiento: bool = False
    # Modo historia: realza el contraste de toda la imagen (src/ui/filtro_color.py).
    alto_contraste: bool = False
    # Modo historia: el texto espera al jugador salvo que elija avance automático.
    avance_cinematicas: str = AVANCE_MANUAL
    velocidad_texto: str = "normal"
    esquema_controles: str = ESQUEMA_TECLADO
    mostrar_cono: bool = True
    # 40% de assets.ALFA_MAXIMO_CONO = el cono que el juego tenía antes de este ajuste.
    opacidad_cono: int = 40


def acotar_porcentaje(valor):
    """Entero en 0-100 (redondea y recorta)."""
    return max(0, min(100, int(round(valor))))


def valor_valido(campo, valor):
    """`valor` ya validado para `campo`, o None si no sirve."""
    if campo in CAMPOS_PORCENTAJE:
        # bool es subclase de int: True no es un volumen válido.
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
        return acotar_porcentaje(valor)
    if campo in OPCIONES_TEXTO:
        return valor if valor in OPCIONES_TEXTO[campo] else None
    return valor if isinstance(valor, bool) else None


def desde_dict(datos):
    """Preferencias a partir de un dict leído del disco. Cada campo
    ausente o inválido conserva su valor predeterminado."""
    preferencias = Preferencias()
    if not isinstance(datos, dict):
        return preferencias
    for campo in fields(Preferencias):
        if campo.name in datos:
            valor = valor_valido(campo.name, datos[campo.name])
            if valor is not None:
                setattr(preferencias, campo.name, valor)
    return preferencias


def a_dict(preferencias):
    return {"version": VERSION, **asdict(preferencias)}


def cargar(ruta=RUTA_PREFERENCIAS):
    """Lee el archivo; si no existe o no es JSON válido, valores predeterminados."""
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return desde_dict(json.load(archivo))
    except (OSError, ValueError):
        return Preferencias()


def guardar(preferencias, ruta=RUTA_PREFERENCIAS):
    """Escribe primero un archivo temporal y luego lo renombra, así un
    cierre a mitad de escritura no deja el JSON cortado. Retorna False si
    no se pudo escribir (el juego sigue con los valores en memoria)."""
    temporal = ruta + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(a_dict(preferencias), archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
        return True
    except OSError:
        return False
