"""Gestor de audio sobre pygame.mixer: música, efectos y sus volúmenes.

Es el único punto del juego que toca el mezclador. Todo se pide por ID
(assets.SONIDOS y assets.MUSICA) y se carga perezosamente: cada archivo
se lee la primera vez que suena y queda en una caché.

    reproducir(id)                 -> efecto (con anti-spam por ID)
    musica(id, bucle, fade_ms)     -> pista del momento, con fundido cruzado
    detener_musica(fade_ms)        -> silencio con fundido
    alternar_silencio()            -> tecla N: silencia todo / vuelve a sonar
    procesar_eventos()             -> lo que la lógica pidió con eventos_sonido.emitir

Volumen de cada sonido: preferencias del jugador (música / efectos) por
la categoría y la ganancia de su ID (src/core/mezcla_audio.py, números
en balance.py). Fallback silencioso: si falta un archivo, no carga o el
equipo no tiene salida de audio, ese ID no suena y el juego sigue igual.
"""

import threading
import time

import pygame

from src.core import assets, eventos_sonido
from src.core.mezcla_audio import LimitadorSonidos, a_fraccion, resolver_ruta, volumen_final


def a_volumen_mixer(porcentaje):
    """Porcentaje 0-100 de la interfaz -> volumen 0.0-1.0 de pygame.
    0% silencia; 100% es el máximo del mezclador, nunca más (sin amplificar)."""
    return a_fraccion(porcentaje)


class Audio:
    def __init__(self, preferencias):
        self.disponible = _iniciar_mezclador()
        self.silenciado = False
        self._preferencias = preferencias
        self._efectos = {}  # id -> pygame.mixer.Sound o None (no cargó)
        self._pistas = {}  # id -> pygame.mixer.Sound o None
        self._limitador = LimitadorSonidos()
        self._pista_actual = None
        self._canal_musica = None
        self.hay_musica = self.disponible and any(resolver_ruta(i, assets.MUSICA) for i in assets.MUSICA)

    # ------------------------------------------------------------------
    # Volúmenes
    # ------------------------------------------------------------------

    def aplicar(self, preferencias):
        """Aplica los volúmenes al instante (se llama al mover un slider)."""
        self._preferencias = preferencias
        if not self.disponible:
            return
        if self._canal_musica is not None and self._pista_actual is not None:
            self._canal_musica.set_volume(self._volumen_musica(self._pista_actual))

    def alternar_silencio(self):
        """Silencia o devuelve el sonido (música y efectos). Retorna el estado nuevo."""
        self.silenciado = not self.silenciado
        if self.disponible:
            if self.silenciado:
                pygame.mixer.stop()
                if self._canal_musica is not None:
                    self._canal_musica.set_volume(0.0)
            else:
                self.aplicar(self._preferencias)
                if self._pista_actual is not None and (self._canal_musica is None or not self._canal_musica.get_busy()):
                    # pygame.mixer.stop() cortó la pista: vuelve a entrar con fundido.
                    pista, self._pista_actual = self._pista_actual, None
                    self.musica(pista)
        return self.silenciado

    def _volumen_musica(self, id_pista):
        return volumen_final(id_pista, self._preferencias.volumen_musica, self.silenciado, es_musica=True)

    def _volumen_efecto(self, id_sonido):
        return volumen_final(id_sonido, self._preferencias.volumen_efectos, self.silenciado)

    # ------------------------------------------------------------------
    # Música
    # ------------------------------------------------------------------

    def musica(self, id_pista, bucle=True, fade_ms=assets.FUNDIDO_MUSICA_MS):
        """Cambia la pista del momento con un fundido cruzado. Repetir la pista
        actual no la reinicia. None detiene la música."""
        if not self.disponible or id_pista == self._pista_actual:
            return
        if id_pista is None:
            self.detener_musica(fade_ms)
            return
        self._soltar_canal(fade_ms)
        self._pista_actual = id_pista
        pista = self._pista(id_pista)
        if pista is None:
            return
        canal = pista.play(loops=-1 if bucle else 0, fade_ms=fade_ms)
        if canal is not None:
            canal.set_volume(self._volumen_musica(id_pista))
        self._canal_musica = canal

    def detener_musica(self, fade_ms=assets.FUNDIDO_MUSICA_MS):
        self._pista_actual = None
        self._soltar_canal(fade_ms)

    def _soltar_canal(self, fade_ms):
        if self._canal_musica is not None:
            self._canal_musica.fadeout(fade_ms)
            self._canal_musica = None

    def _pista(self, id_pista):
        if id_pista not in self._pistas:
            self._pistas[id_pista] = _cargar(resolver_ruta(id_pista, assets.MUSICA))
        return self._pistas[id_pista]

    def precargar_musica(self):
        """Decodifica las pistas en un hilo aparte, para que el primer cambio
        de pista no congele un frame. Si algo falla, se cargará al usarla."""
        if not self.disponible:
            return

        def cargar_todas():
            for id_pista in assets.MUSICA:
                try:
                    self._pista(id_pista)
                except Exception:  # noqa: BLE001 - nunca debe tumbar el juego
                    return

        threading.Thread(target=cargar_todas, name="precarga-musica", daemon=True).start()

    # ------------------------------------------------------------------
    # Efectos
    # ------------------------------------------------------------------

    def reproducir(self, id_sonido):
        """Reproduce el efecto `id_sonido` (o nada si no existe, no cargó,
        está en silencio o el anti-spam lo frena). Los de interfaz se
        cortan y vuelven a empezar, para que navegar rápido no apile copias."""
        if not self.disponible or self.silenciado or not id_sonido:
            return
        sonido = self._efecto(id_sonido)
        if sonido is None:
            return
        if assets.SONIDOS[id_sonido][1] == assets.CATEGORIA_UI:
            sonido.stop()
        elif not self._limitador.permitir(id_sonido, time.monotonic(), sonido.get_num_channels()):
            return
        canal = sonido.play()
        if canal is not None:
            canal.set_volume(self._volumen_efecto(id_sonido))

    def procesar_eventos(self):
        """Reproduce lo que la lógica pidió este frame (src/core/eventos_sonido.py)."""
        for id_sonido in eventos_sonido.drenar():
            self.reproducir(id_sonido)

    def _efecto(self, id_sonido):
        if id_sonido not in self._efectos:
            self._efectos[id_sonido] = _cargar(resolver_ruta(id_sonido))
        return self._efectos[id_sonido]


def _iniciar_mezclador():
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
        if pygame.mixer.get_init() is None:
            return False
        pygame.mixer.set_num_channels(assets.CANALES_MEZCLADOR)
    except pygame.error:
        return False
    return True


def _cargar(ruta):
    """pygame.mixer.Sound del archivo, o None si no hay ruta o no carga."""
    if ruta is None:
        return None
    try:
        return pygame.mixer.Sound(ruta)
    except (pygame.error, FileNotFoundError):
        return None
