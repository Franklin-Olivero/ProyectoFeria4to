"""Audio del juego sobre pygame.mixer: música, efectos y sus volúmenes.

Es el único punto del juego que toca el mezclador. Hay dos grupos con su
propio volumen (src/core/preferencias.py):

    música  -> pygame.mixer.music (una pista en bucle, si existe el archivo)
    efectos -> cada pygame.mixer.Sound cargado aquí (interfaz y, a futuro, combate)

Recursos: si existe el archivo de assets.RUTAS_SONIDOS / RUTA_MUSICA_MENU
se usa ese. Aún no hay archivos de audio en el repositorio, así que los
efectos de interfaz se generan en código (un pitido de onda cuadrada de
8 bits), igual que los sprites se dibujan en código mientras llega el
arte real; la música queda en silencio hasta que se agregue la pista.

Si el equipo no tiene salida de audio, pygame.mixer no inicia: todo
sigue funcionando y simplemente no suena nada.
"""

import array
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
            self.hay_musica = _iniciar_musica(assets.RUTA_MUSICA_MENU)
        self.aplicar(preferencias)

    def aplicar(self, preferencias):
        """Aplica los volúmenes al instante (se llama al mover un slider)."""
        if not self.disponible:
            return
        pygame.mixer.music.set_volume(a_volumen_mixer(preferencias.volumen_musica))
        volumen = a_volumen_mixer(preferencias.volumen_efectos)
        for sonido in self._efectos.values():
            sonido.set_volume(volumen)

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


def _iniciar_musica(ruta):
    if not ruta or not os.path.exists(ruta):
        return False
    try:
        pygame.mixer.music.load(ruta)
        pygame.mixer.music.play(-1)
    except pygame.error:
        return False
    return True


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
