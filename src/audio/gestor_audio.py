"""Gestor de audio sobre pygame.mixer: música, efectos y sus volúmenes.

Es el único punto del juego que toca el mezclador. Todo se pide por ID
(assets.SONIDOS y assets.MUSICA) y se carga perezosamente: cada archivo
se lee la primera vez que suena y queda en una caché.

    reproducir(id)                 -> efecto (con anti-spam por ID)
    musica(id, bucle, fade_ms)     -> pista del momento, con fundido cruzado
    detener_musica(fade_ms)        -> silencio con fundido
    cambiar(campo, valor)          -> un ajuste de volumen: se aplica y se guarda
    alternar_silencio()            -> tecla N (se guarda)
    atenuar_musica(activo)         -> la pausa baja la música con fundido
    actualizar(dt)                 -> avanza ese fundido (una vez por frame)
    procesar_eventos()             -> lo que la lógica pidió con eventos_sonido.emitir

Volumen: SIEMPRE el efectivo de src/audio/ajustes_audio.py (general ×
música o efectos × mezcla de la categoría × ganancia del ID × atenuación,
0 en silencio), puesto en el Sound antes de cada play y re-aplicado a la
pista en curso cuando cambia un ajuste.

Por qué en el Sound y no en el canal: pygame.mixer hace el fundido de
entrada de una pista llevando el volumen del CANAL de 0 al que tenía
antes de empezar; un set_volume del canal hecho después del play se
pierde y la música terminaba sonando al 100 % (el bug de "el volumen
guardado no se aplica"). Por eso los canales quedan siempre en 1.0, el
volumen va en el Sound, y la música usa CANALES_MUSICA canales reservados
(A/B para el fundido cruzado) que ningún efecto puede ocupar.

Fallback silencioso: si falta un archivo, no carga o el equipo no tiene
salida de audio, ese ID no suena y el juego sigue igual.
"""

import threading
import time

import pygame

from src.audio import ajustes_audio, eventos_sonido
from src.audio.mezcla import LimitadorSonidos, a_fraccion, resolver_ruta, volumen_final
from src.core import assets
from src.core.balance import DURACION_ATENUACION_PAUSA, FACTOR_MUSICA_PAUSA

CANALES_MUSICA = 2


def a_volumen_mixer(porcentaje):
    """Porcentaje 0-100 de la interfaz -> volumen 0.0-1.0 de pygame.
    0% silencia; 100% es el máximo del mezclador, nunca más (sin amplificar)."""
    return a_fraccion(porcentaje)


class Audio:
    def __init__(self, ajustes, ruta_ajustes=None):
        """`ajustes`: AjustesAudio ya cargado (se carga ANTES de iniciar el
        mezclador); `ruta_ajustes`: dónde guardarlos al cambiar (None = la
        carpeta de datos de usuario)."""
        self.ajustes = ajustes
        self.ruta_ajustes = ruta_ajustes
        self.disponible = _iniciar_mezclador()
        self._canales_musica = []
        if self.disponible:
            pygame.mixer.set_reserved(CANALES_MUSICA)
            self._canales_musica = [pygame.mixer.Channel(i) for i in range(CANALES_MUSICA)]
        self._efectos = {}  # id -> pygame.mixer.Sound o None (no cargó)
        self._pistas = {}  # id -> pygame.mixer.Sound o None
        self._limitador = LimitadorSonidos()
        self._pista_actual = None
        self._canal_musica = None  # el reservado que suena ahora
        self._atenuacion = 1.0  # 1 = normal; FACTOR_MUSICA_PAUSA en pausa
        self._atenuacion_objetivo = 1.0
        self.hay_musica = self.disponible and any(resolver_ruta(i, assets.MUSICA) for i in assets.MUSICA)

    @property
    def silenciado(self):
        return self.ajustes.silencio

    # ------------------------------------------------------------------
    # Ajustes
    # ------------------------------------------------------------------

    def aplicar(self):
        """Re-aplica los ajustes a lo que ya suena: la pista en curso y los
        efectos cargados (así un silencio corta también lo que ya sonaba)."""
        if not self.disponible:
            return
        self._aplicar_volumen_musica()
        for id_sonido, sonido in self._efectos.items():
            if sonido is not None:
                sonido.set_volume(self._volumen_efecto(id_sonido))

    def cambiar(self, campo, valor):
        """Cambia un ajuste (validado y recortado), lo aplica al instante y lo
        guarda. True si cambió."""
        valor = ajustes_audio.valor_valido(campo, valor)
        if valor is None or getattr(self.ajustes, campo) == valor:
            return False
        setattr(self.ajustes, campo, valor)
        self.aplicar()
        self.guardar()
        return True

    def alternar_silencio(self):
        """Tecla N. Retorna el estado nuevo."""
        self.cambiar("silencio", not self.ajustes.silencio)
        return self.ajustes.silencio

    def guardar(self):
        return ajustes_audio.guardar(self.ajustes, self.ruta_ajustes)

    def _volumen_musica(self, id_pista):
        return volumen_final(id_pista, self.ajustes, es_musica=True, atenuacion=self._atenuacion)

    def _volumen_efecto(self, id_sonido):
        return volumen_final(id_sonido, self.ajustes)

    def volumen_musica_aplicado(self):
        """Volumen que tiene hoy la pista en curso (0 si no hay): para tests y QA."""
        pista = self._pistas.get(self._pista_actual)
        return pista.get_volume() if pista is not None else 0.0

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
        anterior = self._canal_musica
        self._soltar_canal(fade_ms)
        self._pista_actual = id_pista
        pista = self._pista(id_pista)
        if pista is None:
            return
        # El canal libre de los dos reservados (el otro hace el fundido de salida).
        canal = next((c for c in self._canales_musica if c is not anterior), self._canales_musica[0])
        canal.set_volume(1.0)
        pista.set_volume(self._volumen_musica(id_pista))
        canal.play(pista, loops=-1 if bucle else 0, fade_ms=fade_ms)
        self._canal_musica = canal

    def detener_musica(self, fade_ms=assets.FUNDIDO_MUSICA_MS):
        self._pista_actual = None
        self._soltar_canal(fade_ms)

    def atenuar_musica(self, activo):
        """La pausa baja la música a FACTOR_MUSICA_PAUSA (y la sube al
        reanudar) con un fundido de DURACION_ATENUACION_PAUSA (actualizar)."""
        self._atenuacion_objetivo = FACTOR_MUSICA_PAUSA if activo else 1.0

    def actualizar(self, dt):
        """Avanza el fundido de atenuación de la música. Un frame, O(1)."""
        if self._atenuacion == self._atenuacion_objetivo:
            return
        paso = (1.0 - FACTOR_MUSICA_PAUSA) * dt / DURACION_ATENUACION_PAUSA
        if self._atenuacion < self._atenuacion_objetivo:
            self._atenuacion = min(self._atenuacion_objetivo, self._atenuacion + paso)
        else:
            self._atenuacion = max(self._atenuacion_objetivo, self._atenuacion - paso)
        self._aplicar_volumen_musica()

    def _aplicar_volumen_musica(self):
        pista = self._pistas.get(self._pista_actual)
        if self.disponible and pista is not None:
            pista.set_volume(self._volumen_musica(self._pista_actual))

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
        if not self.disponible or self.ajustes.silencio or not id_sonido:
            return
        sonido = self._efecto(id_sonido)
        if sonido is None:
            return
        if assets.SONIDOS[id_sonido][1] == assets.CATEGORIA_UI:
            sonido.stop()
        elif not self._limitador.permitir(id_sonido, time.monotonic(), sonido.get_num_channels()):
            return
        sonido.set_volume(self._volumen_efecto(id_sonido))
        canal = sonido.play()
        if canal is not None:
            canal.set_volume(1.0)

    def procesar_eventos(self):
        """Reproduce lo que la lógica pidió este frame (src/audio/eventos_sonido.py)."""
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
