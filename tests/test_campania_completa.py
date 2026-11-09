"""Recorre la campaña con el loop real de Main.py, sin ventana (ver tools/recorrido_campania.py).

Pasa por: menú, intro que espera a Enter, capítulos, combate, pruebas en el suelo,
terminal, indicador de reputación, investigación por DFS, crisis, rechazo, final de
derrota, punto de control, misión de redención, jefe, elecciones y final.

Corre en un proceso aparte: el juego llama a pygame.quit() al salir y no debe
afectar a los demás tests.
"""

import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_campania_completa_de_principio_a_fin():
    entorno = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    salida = subprocess.run([sys.executable, os.path.join("tools", "recorrido_campania.py")], cwd=RAIZ, env=entorno,
                            capture_output=True, text=True, timeout=300)
    assert salida.returncode == 0, salida.stdout[-1500:] + salida.stderr[-3000:]
    assert "campaña completa" in salida.stdout and "la intro esperó" in salida.stdout
