"""Prueba headless de los ajustes de audio y la pausa con el juego REAL (Main.main).

1. Escribe unos ajustes de audio distintos a los de fábrica en una carpeta de
   datos temporal (CIVITAS_DATOS) y arranca el juego: comprueba que el volumen
   que de verdad tiene la música es el efectivo de esos ajustes.
2. Entra al Colegio y pausa con Esc: en 2 s simulados no avanzan el reloj del
   juego, la gracia de entrada ni los enemigos, y la música baja.
3. P reanuda y el mundo sigue.
4. Abre Ajustes en la pausa, sube el volumen general y verifica que se aplica a
   la pista en curso y se guarda en el archivo al instante.

    python tools/prueba_pausa_audio.py [--capturas carpeta]

La usa tests/test_pausa_audio_en_partida.py.
"""

import argparse
import json
import os
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools"))
os.chdir(RAIZ)

AJUSTES_GUARDADOS = {"version": 1, "volumen_general": 40, "volumen_musica": 50, "volumen_efectos": 30, "silencio": False}


def guion(c, _opciones):
    from src.audio.ajustes_audio import AjustesAudio
    from src.audio.mezcla import volumen_final
    from src.core.balance import FACTOR_MUSICA_PAUSA
    from src.dungeon import ciudad_mapa

    pg = c.pygame
    enter = pg.K_RETURN

    def L():
        return c.locales()

    def cerrar_dialogos():
        for _ in range(4000):
            loc = L()
            if loc["dialogo"] is None and loc["indicador_rep"] is None:
                return
            c.tecla(enter)
            yield 8

    yield 30
    c.tecla(enter)  # JUGAR
    yield 20
    c.tecla(pg.K_1)
    yield 20
    c.tecla(enter)  # Ciudadano
    while L() is None:
        yield 1
    yield from cerrar_dialogos()
    yield 30

    # 1. Volumen aplicado = el de los ajustes guardados.
    audio = L()["audio"]
    assert audio.ajustes == AjustesAudio(40, 50, 30, False), audio.ajustes
    if audio.disponible:
        esperado = volumen_final(audio._pista_actual, audio.ajustes, es_musica=True)
        aplicado = audio.volumen_musica_aplicado()
        assert abs(aplicado - esperado) < 0.01, (aplicado, esperado)
        c.log(f"volumen de la música aplicado {aplicado:.3f} = efectivo {esperado:.3f}")

    # 2. Pausa en una mazmorra.
    col, fila = ciudad_mapa.ENTRADAS["Colegio"]
    x, y = ciudad_mapa.centro_casilla(col, fila)
    L()["jugador"].colocar_en((x, y + 8))
    yield 3
    c.tecla(pg.K_e)
    yield 6
    yield from cerrar_dialogos()
    assert L()["escena"].name == "MAZMORRA", L()["escena"]
    yield 40  # instrucciones de mazmorra: pasado el retardo, Enter comienza
    assert L()["instrucciones"] is not None
    c.tecla(enter)
    yield 2
    assert L()["instrucciones"] is None
    mazmorra = L()["mazmorra"]
    mazmorra.gracia.iniciar()  # una gracia recién empezada: su reloj debe quedar quieto
    yield 1
    c.tecla(pg.K_ESCAPE)
    yield 2
    pausa = L()["pausa"]
    assert pausa.abierta and pausa.congelada
    antes = (L()["tiempo"], mazmorra.gracia.restante,
             [tuple(e.rect.center) for e in mazmorra.cuarto.enemigos], mazmorra.mazmorra.tiempo_propagacion
             if hasattr(mazmorra.mazmorra, "tiempo_propagacion") else None)
    yield 120  # 2 s simulados en pausa
    despues = (L()["tiempo"], mazmorra.gracia.restante,
               [tuple(e.rect.center) for e in mazmorra.cuarto.enemigos], mazmorra.mazmorra.tiempo_propagacion
               if hasattr(mazmorra.mazmorra, "tiempo_propagacion") else None)
    assert antes == despues, (antes, despues)
    c.log("en pausa no avanzó nada en 2 s")
    if audio.disponible:
        atenuado = volumen_final(audio._pista_actual, audio.ajustes, es_musica=True, atenuacion=FACTOR_MUSICA_PAUSA)
        assert abs(audio.volumen_musica_aplicado() - atenuado) < 0.01
        c.log("la música bajó con la pausa")
    c.captura("pausa_menu")

    # 3. P reanuda.
    c.tecla(pg.K_p)
    yield 30
    assert not L()["pausa"].abierta
    assert L()["tiempo"] > antes[0] and mazmorra.gracia.restante < antes[1]
    c.log("P reanudó y el mundo siguió")

    # 4. Ajustes dentro de la pausa: se aplican y se guardan al instante.
    c.tecla(pg.K_ESCAPE)
    yield 2
    c.tecla(pg.K_DOWN, enter)  # Ajustes
    yield 3
    assert L()["pausa"].ajustes is not None
    c.captura("pausa_ajustes")
    c.tecla(pg.K_DOWN, pg.K_RIGHT, pg.K_RIGHT)  # volumen general 40 -> 50
    yield 3
    assert audio.ajustes.volumen_general == 50
    with open(os.path.join(os.environ["CIVITAS_DATOS"], "ajustes_audio.json"), encoding="utf-8") as archivo:
        assert json.load(archivo)["volumen_general"] == 50
    if audio.disponible:
        yield 40  # la música termina de subir al cerrar la pausa
    c.tecla(pg.K_ESCAPE, pg.K_ESCAPE)  # cierra el modal y la pausa
    yield 40
    assert not L()["pausa"].abierta
    if audio.disponible:
        esperado = volumen_final(audio._pista_actual, audio.ajustes, es_musica=True)
        assert abs(audio.volumen_musica_aplicado() - esperado) < 0.01
    c.log("ajuste de la pausa aplicado y guardado")
    from recorrido_campania import FinDelGuion
    raise FinDelGuion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capturas", default=None)
    args = parser.parse_args()
    carpeta = tempfile.mkdtemp(prefix="civitas_prueba_pausa_")
    os.environ["CIVITAS_DATOS"] = carpeta
    with open(os.path.join(carpeta, "ajustes_audio.json"), "w", encoding="utf-8") as archivo:
        json.dump(AJUSTES_GUARDADOS, archivo)
    import recorrido_campania

    resultado = recorrido_campania.ejecutar(guion=guion, carpeta=args.capturas, verboso=True)
    print(f"OK pausa y audio: {resultado.frames} frames")


if __name__ == "__main__":
    main()
