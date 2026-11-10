"""Prueba de humo de Ciudad Nova con el Main real (sin ventana).

    python tools/humo_ciudad.py                      # headless (SDL dummy)
    python tools/humo_ciudad.py --capturas carpeta   # además guarda capturas

Lobby -> roles -> ciudad; camina por cada zona (el render de la ciudad
corre cada frame y se mide su costo); entra con E a cada edificio (la
Alcaldía, sellada al empezar, no debe dejar entrar), vuelve a la ciudad
desde la pausa y termina dentro de una mazmorra. Cualquier excepción del
juego hace fallar el script. Reporta el tiempo medio por frame del dibujo
de la ciudad (debe caber en 16,6 ms para 60 FPS).
"""

import argparse
import os
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools"))
os.chdir(RAIZ)

import recorrido_campania as rc  # noqa: E402

# Una casilla transitable de cada zona (la cámara la encuadra al pararse ahí).
PUNTOS_ZONA = {
    "plaza": (30, 27), "parque": (44, 15), "comercial": (32, 34), "escolar": (15, 15),
    "hospitalaria": (12, 37), "civica": (42, 6), "medios": (46, 41), "residencial": (59, 18),
    "avenida": (12, 24), "liminal": (25, 43),
}
resultado = {"ms_ciudad": [], "zonas": [], "edificios": {}}


def guion(c, _opciones):
    pg = c.pygame
    ENTER, ESC, ABAJO, IZQ, E = pg.K_RETURN, pg.K_ESCAPE, pg.K_DOWN, pg.K_LEFT, pg.K_e
    from src.dungeon import ciudad_mapa

    def L():
        return c.locales()

    def cerrar_overlays(limite=3000):
        for _ in range(limite):
            loc = L()
            if loc is None or (loc["dialogo"] is None and loc["indicador_rep"] is None):
                return
            c.tecla(ENTER)
            yield 10

    def escena():
        return L()["escena"].name

    def medir(frames):
        for _ in range(frames):
            inicio = time.perf_counter()
            yield 1
            if escena() == "CIUDAD":
                resultado["ms_ciudad"].append((time.perf_counter() - inicio) * 1000)

    # Menú -> 1 jugador -> rol -> partida.
    yield 30
    c.tecla(ENTER)
    yield 30
    c.tecla(pg.K_1)
    yield 30
    c.tecla(pg.K_RIGHT)
    yield 5
    c.tecla(ENTER)
    while L() is None:
        yield 1
    yield 20
    yield from cerrar_overlays()
    assert escena() == "CIUDAD", escena()
    c.captura("humo_ciudad")

    # Caminar por cada zona.
    for nombre, casilla in PUNTOS_ZONA.items():
        assert not ciudad_mapa.es_solida(*casilla), (nombre, casilla)
        L()["jugador"].colocar_en(ciudad_mapa.centro_casilla(*casilla))
        c.tecla(pg.K_RIGHT)
        yield from medir(30)
        resultado["zonas"].append(nombre)
        c.captura(f"humo_zona_{nombre}")

    # Entrar a cada edificio con E.
    for zona in ("Colegio", "Hospital", "Alcaldía", "Empresa de Medios"):
        col, fila = ciudad_mapa.ENTRADAS[zona]
        x, y = ciudad_mapa.centro_casilla(col, fila)
        L()["jugador"].colocar_en((x, y + 8))
        yield 3
        assert ciudad_mapa.entrada_cercana((x, y + 8)) == zona
        c.tecla(E)
        yield 8
        yield from cerrar_overlays()
        resultado["edificios"][zona] = escena()
        c.captura(f"humo_entrada_{zona.split()[0].lower()}")
        if escena() == "CIUDAD":
            continue  # la Alcaldía sellada
        if L()["instrucciones"] is not None:
            yield 40
            c.tecla(ENTER)
            yield 30
        if zona == "Empresa de Medios":
            break  # se termina dentro de la mazmorra
        c.tecla(ESC)  # pausa -> Volver a la ciudad -> Sí
        yield 6
        c.tecla(ABAJO, ABAJO, ABAJO)
        yield 4
        c.tecla(ENTER)
        yield 4
        c.tecla(IZQ)
        yield 4
        c.tecla(ENTER)
        for _ in range(240):
            yield 1
            if escena() == "CIUDAD":
                break
        yield from cerrar_overlays()
        assert escena() == "CIUDAD", (zona, escena())
    yield 30
    raise rc.FinDelGuion


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capturas", default=None)
    args = parser.parse_args()
    rc.ejecutar(guion=guion, carpeta=args.capturas)
    ms = resultado["ms_ciudad"]
    print("zonas recorridas:", ", ".join(resultado["zonas"]))
    for zona, escena in resultado["edificios"].items():
        print(f"  E en {zona:18s} -> {escena}")
    if ms:
        ms_ordenados = sorted(ms)
        print(f"frame de la ciudad: media {sum(ms) / len(ms):.2f} ms, p95 {ms_ordenados[int(len(ms) * 0.95)]:.2f} ms"
              f" ({len(ms)} frames; 60 FPS = 16.67 ms)")
    esperado = {"Colegio": "MAZMORRA", "Hospital": "MAZMORRA", "Empresa de Medios": "MAZMORRA", "Alcaldía": "CIUDAD"}
    assert resultado["edificios"] == esperado, resultado["edificios"]
    assert len(resultado["zonas"]) == len(PUNTOS_ZONA)
    print("OK")


if __name__ == "__main__":
    main()
