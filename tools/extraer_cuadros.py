"""Convierte un MP4 en los cuadros JPG que reproduce src/ui/video_cuadros.py.

Solo se usa al producir el contenido, no al jugar (el juego no necesita ffmpeg):

    pip install imageio-ffmpeg          # en un entorno aparte
    python tools/extraer_cuadros.py intro.mp4 intro_ciudad --fps 12

Escribe assets/story/video/<id>/0001.jpg... y clip.json. Se usan 12 cuadros por
segundo a 1280×720: el pixel art se mueve con fluidez y cada clip de 5 s pesa ~5 MB.
"""

import argparse
import json
import os
import subprocess

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("id_clip")
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--calidad", type=int, default=4, help="2 = mejor, 31 = peor")
    args = parser.parse_args()
    import imageio_ffmpeg

    carpeta = os.path.join(RAIZ, "assets", "story", "video", args.id_clip)
    os.makedirs(carpeta, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", args.video,
                    "-vf", f"fps={args.fps},scale=1280:720:flags=lanczos", "-q:v", str(args.calidad),
                    os.path.join(carpeta, "%04d.jpg")], check=True)
    with open(os.path.join(carpeta, "clip.json"), "w", encoding="utf-8") as archivo:
        json.dump({"fps": args.fps, "origen": "Higgsfield (ver docs/ASSET_MANIFEST.md)"}, archivo)
    print(args.id_clip, len([n for n in os.listdir(carpeta) if n.endswith(".jpg")]), "cuadros")


if __name__ == "__main__":
    main()
