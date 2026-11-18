"""Exporta el prólogo tal como lo dibuja el juego (video + rótulos + audio) a MP4.

Sirve para revisar el corto fuera del juego y entregarlo (QA, sustentación).
Usa el render real (src/ui/cinematica_render.py) sin ventana:

    pip install imageio-ffmpeg          # en un entorno aparte
    python tools/exportar_prologo.py [--capturas]

Salida: _packs/prologo_umbral/prologo_umbral_final.mp4 (fuera de git) y, con
--capturas, docs/capturas/prologo/<segundo>.png de los momentos clave.
"""

import argparse
import os
import subprocess
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story import cinematica as cine  # noqa: E402
from src.ui import cinematica_render, video_cuadros  # noqa: E402

FPS = 15
MOMENTOS = (1.5, 4.5, 6.6, 9.8, 13.0, 15.0, 18.5, 21.0, 23.0, 27.5, 31.0, 35.0, 38.0, 42.0, 45.5, 48.5, 52.5, 56.0, 61.0, 63.5, 65.8)


def _esperar_cuadro(id_clip, tiempo, tamanio):
    """El lector va en otro hilo: para exportar se espera el cuadro exacto."""
    for _ in range(400):
        video_cuadros.cuadro(id_clip, tiempo, tamanio)
        clip = video_cuadros._clips.get((id_clip, tamanio))
        if clip is None or clip.indice_en(tiempo) in clip.listos:
            return
        time.sleep(0.005)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capturas", action="store_true")
    args = parser.parse_args()
    import imageio_ffmpeg

    pygame.init()
    pantalla = pygame.Surface((1280, 720))
    guion = cine.guion_intro(Partida().campania.contenido, "periodista", "Periodista")
    toma = guion.actual
    salida = os.path.join(RAIZ, "_packs", "prologo_umbral", "prologo_umbral_final.mp4")
    audio = os.path.join(RAIZ, assets.MUSICA[toma.pista])
    proceso = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", "1280x720", "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-crf", "18",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", salida],
                               stdin=subprocess.PIPE)
    carpeta_capturas = os.path.join(RAIZ, "docs", "capturas", "prologo")
    if args.capturas:
        os.makedirs(carpeta_capturas, exist_ok=True)
    pendientes = list(MOMENTOS)
    guion.tomar_pista()
    guion.reiniciar_reloj()
    cuadro = 0
    while guion.actual is toma:
        _esperar_cuadro(toma.video, guion.tiempo, pantalla.get_size())
        cinematica_render.dibujar_cinematica(pantalla, guion, 1 / FPS)
        proceso.stdin.write(pygame.image.tobytes(pantalla, "RGB"))
        if pendientes and guion.tiempo >= pendientes[0]:
            pygame.image.save(pantalla, os.path.join(carpeta_capturas, f"{pendientes.pop(0):05.1f}.png")) \
                if args.capturas else pendientes.pop(0)
        cuadro += 1
        guion.actualizar(1 / FPS)
    proceso.stdin.close()
    proceso.wait()
    print(f"{cuadro} cuadros ({cuadro / FPS:.1f} s) -> {os.path.relpath(salida, RAIZ)}")


if __name__ == "__main__":
    main()
