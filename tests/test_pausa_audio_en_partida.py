"""Ajustes de audio guardados y pausa con el loop real de Main.py, sin ventana
(ver tools/prueba_pausa_audio.py): el volumen aplicado coincide con el
guardado, la pausa congela la mazmorra, P reanuda y un ajuste cambiado en
la pausa se aplica y se guarda.

Corre en un proceso aparte: el juego llama a pygame.quit() al salir.
"""

import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_ajustes_guardados_y_pausa_en_partida():
    entorno = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "PYTHONIOENCODING": "utf-8"}
    entorno.pop("CIVITAS_DATOS", None)  # la prueba crea su propia carpeta temporal
    salida = subprocess.run([sys.executable, os.path.join("tools", "prueba_pausa_audio.py")], cwd=RAIZ, env=entorno,
                            capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert salida.returncode == 0, salida.stdout[-1500:] + salida.stderr[-3000:]
    for marca in ("en pausa no avanzó nada", "P reanudó", "ajuste de la pausa aplicado y guardado", "OK pausa y audio"):
        assert marca in salida.stdout, marca
