"""Audio del juego sobre pygame.mixer: música, efectos y sus volúmenes.

Es el único punto del juego que toca el mezclador. Hay dos grupos con su
propio volumen (src/core/preferencias.py):

    música  -> una pista en bucle por momento del juego, con fundido cruzado
    efectos -> cada pygame.mixer.Sound cargado aquí

Recursos: si existe el archivo de assets.RUTAS_SONIDOS / RUTAS_MUSICA se usa
ese (los compone tools/generar_audio.py, son propios). Si falta, el efecto se
sintetiza con un pitido y la música con un colchón de acordes: el juego nunca
depende de un archivo. Las pistas se cargan una vez y quedan en memoria, así
que cambiar de pista no bloquea un frame más que la primera vez (~35 ms).

Si el equipo no tiene salida de audio, pygame.mixer no inicia: todo
sigue funcionando y simplemente no suena nada.
"""

import array
import math
import os

import pygame

from src.core import assets


def a_volumen_mixer(porcentaje):
    """Porcentaje 0-100 de la interfaz -> volumen 0.0-1.0 de pygame.
    0% silencia; 100% es el máximo del mezclador, nunca más (sin amplificar)."""
    return max(0, min(100, porcentaje)) / 100


class Audio:
    def __init__(self, preferencias):
        self.disponible = _iniciar_mezclador()
        self.hay_musica = False
        self._efectos = {}  # nombre -> pygame.mixer.Sound
        if self.disponible:
            for nombre, (frecuencias, duracion) in assets.TONOS_SONIDOS.items():
                self._efectos[nombre] = _cargar_o_sintetizar(assets.RUTAS_SONIDOS.get(nombre), frecuencias, duracion)
            self._efectos = {nombre: sonido for nombre, sonido in self._efectos.items() if sonido is not None}
            self.hay_musica = any(os.path.exists(ruta) for ruta in assets.RUTAS_MUSICA.values())
        self._pistas = {}  # nombre -> Sound (archivo o colchón sintetizado)
        self._pista_actual = None
        self._canal_musica = None
        self._volumen_musica = 0.0
        self.aplicar(preferencias)

    def aplicar(self, preferencias):
        """Aplica los volúmenes al instante (se llama al mover un slider)."""
        if not self.disponible:
            return
        self._volumen_musica = a_volumen_mixer(preferencias.volumen_musica)
        if self._canal_musica is not None:
            self._canal_musica.set_volume(self._volumen_musica)
        volumen = a_volumen_mixer(preferencias.volumen_efectos)
        for sonido in self._efectos.values():
            sonido.set_volume(volumen)

    def musica(self, nombre):
        """Cambia la pista del momento con un fundido cruzado. Repetir la pista
        actual no la reinicia. None detiene la música."""
        if not self.disponible or nombre == self._pista_actual:
            return
        self._pista_actual = nombre
        if self._canal_musica is not None:
            self._canal_musica.fadeout(assets.FUNDIDO_MUSICA_MS)
            self._canal_musica = None
        if nombre is None:
            return
        pista = self._pista(nombre)
        if pista is None:
            return
        canal = pista.play(loops=-1, fade_ms=assets.FUNDIDO_MUSICA_MS)
        if canal is not None:
            canal.set_volume(self._volumen_musica)
        self._canal_musica = canal

    def _pista(self, nombre):
        if nombre not in self._pistas:
            ruta = assets.RUTAS_MUSICA.get(nombre)
            pista = None
            if ruta and os.path.exists(ruta):
                try:
                    pista = pygame.mixer.Sound(ruta)
                except pygame.error:
                    pista = None
            if pista is None and nombre in assets.ACORDES_MUSICA:
                pista = _sintetizar_colchon(assets.ACORDES_MUSICA[nombre])
            self._pistas[nombre] = pista
        return self._pistas[nombre]

    def reproducir(self, nombre):
        """Reproduce el efecto `nombre` (o nada si no existe). Lo corta si
        ya sonaba, para que navegar rápido no apile copias del mismo sonido."""
        sonido = self._efectos.get(nombre) if nombre else None
        if sonido is not None:
            sonido.stop()
            sonido.play()


def _iniciar_mezclador():
    if pygame.mixer.get_init() is not None:
        return True
    try:
        pygame.mixer.init()
    except pygame.error:
        return False
    return pygame.mixer.get_init() is not None


def _cargar_o_sintetizar(ruta, frecuencias, duracion):
    if ruta and os.path.exists(ruta):
        try:
            return pygame.mixer.Sound(ruta)
        except pygame.error:
            pass
    return _sintetizar(frecuencias, duracion)


def _sintetizar(frecuencias, duracion):
    """Pitido de onda cuadrada: una nota por frecuencia, seguidas, con
    caída lineal de volumen. None si el mezclador no usa muestras de 16 bits."""
    frecuencia_muestreo, formato, canales = pygame.mixer.get_init()
    if formato != -16:
        return None
    por_nota = int(frecuencia_muestreo * duracion / len(frecuencias))
    amplitud = int(32767 * assets.AMPLITUD_SONIDO_SINTETIZADO)
    muestras = array.array("h")
    for frecuencia in frecuencias:
        periodo = frecuencia_muestreo / frecuencia
        for i in range(por_nota):
            caida = 1 - i / por_nota
            valor = amplitud if (i % periodo) < periodo / 2 else -amplitud
            muestras.extend([int(valor * caida)] * canales)
    return pygame.mixer.Sound(buffer=muestras.tobytes())


def _sintetizar_colchon(acordes, segundos_por_acorde=assets.SEGUNDOS_POR_ACORDE):
    """Colchón ambiental: para cada acorde, la suma de sus senos con una
    envolvente que entra y sale suave (así el bucle no hace clic). Se
    calcula a la mitad de la frecuencia de muestreo y se duplica cada
    muestra: es un fondo grave y lento, no necesita más. None si el
    mezclador no usa 16 bits."""
    frecuencia_muestreo, formato, canales = pygame.mixer.get_init()
    if formato != -16:
        return None
    paso = 2
    por_acorde = int(frecuencia_muestreo * segundos_por_acorde) // paso
    amplitud = 32767 * assets.AMPLITUD_MUSICA_SINTETIZADA
    muestras = array.array("h")
    for acorde in acordes:
        fases = [2 * math.pi * f / (frecuencia_muestreo / paso) for f in acorde]
        for i in range(por_acorde):
            borde = min(1.0, i / (por_acorde * 0.15), (por_acorde - i) / (por_acorde * 0.15))
            valor = sum(math.sin(fase * i) * (1.0 if n == 0 else 0.6) for n, fase in enumerate(fases))
            valor += 0.25 * math.sin(fases[0] * i * 0.5)  # subgrave
            v = int(amplitud * borde * valor / (len(fases) + 0.25))
            muestras.extend([v] * (canales * paso))
    return pygame.mixer.Sound(buffer=muestras.tobytes())
