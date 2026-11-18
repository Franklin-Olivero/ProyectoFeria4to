"""Reproducción de clips cinematográficos sin dependencias (solo presentación).

pygame no decodifica video, y el juego debe arrancar sin ffmpeg ni internet.
Por eso cada clip se guarda como cuadros JPG ya extraídos:

    assets/story/video/<id>/0001.jpg, 0002.jpg, ...
    assets/story/video/<id>/clip.json   {"fps": 12}

(los genera tools/extraer_cuadros.py a partir del MP4). Un hilo lector prepara
por adelantado los cuadros que vienen, así decodificar un JPG nunca frena un
frame del juego. `cuadro` retorna la imagen que toca, o None si el clip no
existe: quien la pide cae a la ilustración con paneo (el fallback).

El jugador puede leer todo el tiempo que quiera: el clip va y vuelve despacio
(vaivén) en vez de congelarse, así la escena sigue viva sin un corte visible.

Un clip con `"lineal": true` en su clip.json (la película del prólogo) se
reproduce una sola vez, sincronizado con su banda sonora: el cuadro es
int(tiempo · fps) y al final se queda en el último. Sus cuadros pueden estar a
menor resolución (960×540) y se escalan en el hilo lector, nunca en el frame.

Si falta un clip se avisa una sola vez por consola y se usa el fallback.
"""

import json
import os
import sys
import threading

import pygame

from src.core import assets

RUTA_VIDEOS = assets.RUTA_VIDEOS_HISTORIA
CUADROS_ADELANTADOS = 8  # cuadros que el hilo mantiene listos


class _Clip:
    lineal = False  # vaivén por omisión (los clips de ambiente)

    def __init__(self, carpeta, nombres, fps, tamanio, lineal=False):
        self.carpeta = carpeta
        self.nombres = nombres
        self.fps = fps
        self.tamanio = tamanio
        self.lineal = lineal
        self.listos = {}  # índice -> Surface
        self.objetivo = 0
        self._candado = threading.Lock()
        self._evento = threading.Event()
        self._vivo = True
        self._hilo = threading.Thread(target=self._trabajar, daemon=True)
        self._hilo.start()

    def _trabajar(self):
        while self._vivo:
            self._evento.wait(0.2)
            self._evento.clear()
            with self._candado:
                objetivo = self.objetivo
            ventana = range(max(0, objetivo - CUADROS_ADELANTADOS // 2), min(objetivo + CUADROS_ADELANTADOS, len(self.nombres)))
            for indice in sorted(ventana, key=lambda i: abs(i - objetivo)):
                with self._candado:
                    if indice in self.listos:
                        continue
                imagen = self._cargar(indice)
                with self._candado:
                    self.listos[indice] = imagen
                    # Solo un puñado en memoria: 720p sin comprimir pesa ~3 MB por cuadro.
                    for viejo in [i for i in self.listos if abs(i - objetivo) > CUADROS_ADELANTADOS]:
                        del self.listos[viejo]

    def _cargar(self, indice):
        try:
            imagen = pygame.image.load(os.path.join(self.carpeta, self.nombres[indice]))
        except (pygame.error, OSError):
            return pygame.Surface(self.tamanio)  # un cuadro dañado se ve negro, no tumba el juego
        if imagen.get_size() != self.tamanio:
            imagen = pygame.transform.smoothscale(imagen, self.tamanio)
        return imagen

    def indice_en(self, tiempo):
        """Cuadro que toca en el segundo `tiempo`. Puro, O(1)."""
        ultimo = len(self.nombres) - 1
        if self.lineal:
            return max(0, min(ultimo, int(tiempo * self.fps)))
        posicion = int(tiempo * self.fps) % (2 * ultimo) if ultimo > 0 else 0
        return posicion if posicion <= ultimo else 2 * ultimo - posicion

    def en(self, tiempo):
        indice = self.indice_en(tiempo)
        with self._candado:
            self.objetivo = indice
            imagen = self.listos.get(indice)
            if imagen is None and self.listos:
                # Aún no llega este cuadro: el más cercano evita un parpadeo.
                imagen = self.listos[min(self.listos, key=lambda i: abs(i - indice))]
        self._evento.set()
        return imagen


_clips = {}
_avisados = set()


def disponible(id_clip):
    return os.path.isfile(os.path.join(RUTA_VIDEOS, id_clip, "clip.json"))


def _avisar(id_clip, motivo):
    if id_clip not in _avisados:
        _avisados.add(id_clip)
        print(f"[video] {id_clip}: {motivo}; se usa la ilustración de respaldo.", file=sys.stderr)


def _abrir(id_clip, tamanio):
    carpeta = os.path.join(RUTA_VIDEOS, id_clip)
    try:
        with open(os.path.join(carpeta, "clip.json"), encoding="utf-8") as archivo:
            datos = json.load(archivo)
        fps = float(datos.get("fps", 12))
        lineal = bool(datos.get("lineal", False))
        nombres = sorted(n for n in os.listdir(carpeta) if n.endswith(".jpg"))
    except (OSError, ValueError, AttributeError) as error:
        _avisar(id_clip, f"no se pudo abrir ({error.__class__.__name__})")
        return None
    if not nombres or fps <= 0:
        _avisar(id_clip, "la carpeta no tiene cuadros")
        return None
    return _Clip(carpeta, nombres, fps, tamanio, lineal)


def duracion(id_clip):
    """Segundos que dura un clip según su clip.json y sus cuadros, o None."""
    carpeta = os.path.join(RUTA_VIDEOS, id_clip)
    try:
        with open(os.path.join(carpeta, "clip.json"), encoding="utf-8") as archivo:
            fps = float(json.load(archivo).get("fps", 12))
        cuadros = len([n for n in os.listdir(carpeta) if n.endswith(".jpg")])
    except (OSError, ValueError, AttributeError):
        return None
    return cuadros / fps if fps > 0 and cuadros else None


def cuadro(id_clip, tiempo, tamanio):
    """Superficie del clip en el segundo `tiempo`, o None si no hay clip."""
    clave = (id_clip, tamanio)
    if clave not in _clips:
        _clips[clave] = _abrir(id_clip, tamanio)
    clip = _clips[clave]
    return clip.en(tiempo) if clip is not None else None
