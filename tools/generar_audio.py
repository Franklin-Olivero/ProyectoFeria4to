"""Compone la música y los efectos del juego (síntesis propia, sin muestras ajenas).

    python tools/generar_audio.py            # reescribe su audio dentro de assets/audio/
    python tools/generar_audio.py --revisar  # además, informa nivel y continuidad del bucle

Solo se ejecuta para regenerar el audio: el juego carga los archivos resultantes
y no depende de este script. Todo es matemática sobre la biblioteca estándar, así
que no hay licencias de terceros. Cada pista se escribe en un búfer circular: las
colas de las notas y el eco dan la vuelta al final y entran por el principio,
por lo que el bucle no tiene costura.
"""

import array
import glob
import math
import os
import random
import sys
import wave

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TASA = 22050
DOS_PI = 2 * math.pi

NOTAS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
         "A": 9, "A#": 10, "Bb": 10, "B": 11}
ACORDES = {"m": (0, 3, 7), "M": (0, 4, 7), "m7": (0, 3, 7, 10), "M7": (0, 4, 7, 11), "7": (0, 4, 7, 10), "m9": (0, 3, 7, 10, 14),
           "M9": (0, 4, 7, 11, 14), "sus2": (0, 2, 7), "dim": (0, 3, 6), "add9": (0, 4, 7, 14)}


def frecuencia(nombre, octava):
    return 440.0 * 2 ** ((NOTAS[nombre] + 12 * (octava + 1) - 69) / 12)


class Pista:
    def __init__(self, compases, tempo, pulsos=4):
        self.negra = 60.0 / tempo
        self.segundos = compases * pulsos * self.negra
        self.n = int(self.segundos * TASA)
        self.b = [0.0] * self.n

    def t(self, compas, pulso=0.0, pulsos=4):
        return (compas * pulsos + pulso) * self.negra

    def nota(self, inicio, duracion, f, ganancia, forma="seno", ataque=0.01, caida=None, vibrato=0.0):
        """Suma una nota con envolvente suave. El índice da la vuelta: bucle sin costura."""
        n = int(duracion * TASA)
        i0 = int(inicio * TASA)
        n_ataque = max(1, int(ataque * TASA))
        decaimiento = caida if caida is not None else duracion * 0.45
        fase = 0.0
        paso = DOS_PI * f / TASA
        b, total = self.b, self.n
        for i in range(n):
            t = i / TASA
            env = min(1.0, i / n_ataque) * math.exp(-t / decaimiento) * min(1.0, (n - i) / (0.02 * TASA + 1))
            if vibrato:
                fase += paso * (1 + vibrato * math.sin(DOS_PI * 5 * t))
            else:
                fase += paso
            if forma == "seno":
                v = math.sin(fase)
            elif forma == "pluck":
                v = math.sin(fase) + 0.35 * math.sin(2 * fase) * math.exp(-t * 6) + 0.18 * math.sin(3 * fase) * math.exp(-t * 10)
            elif forma == "piano":
                v = math.sin(fase) + 0.45 * math.sin(2 * fase) * math.exp(-t * 2.5) + 0.2 * math.sin(3 * fase) * math.exp(-t * 4) \
                    + 0.08 * math.sin(4 * fase) * math.exp(-t * 7)
            elif forma == "tri":
                v = 2 / math.pi * math.asin(math.sin(fase))
            elif forma == "saw":  # sierra suave de 5 armónicos
                v = sum(math.sin(k * fase) / k for k in range(1, 6)) * 0.6
            elif forma == "sub":
                v = math.sin(fase) + 0.25 * math.sin(2 * fase)
            else:
                v = math.sin(fase)
            b[(i0 + i) % total] += v * env * ganancia

    def pad(self, inicio, duracion, frecuencias, ganancia, oscilacion=0.25):
        """Colchón: senos desafinados que entran y salen despacio (paso de 2 muestras)."""
        n = int(duracion * TASA)
        i0 = int(inicio * TASA)
        borde = max(1, int(min(duracion * 0.3, 1.2) * TASA))
        por_voz = ganancia / max(1, len(frecuencias))
        b, total = self.b, self.n
        for f in frecuencias:
            for desafine in (0.998, 1.002):
                paso = DOS_PI * f * desafine / TASA
                fase = random.random() * DOS_PI
                for i in range(n):
                    fase += paso
                    env = min(1.0, i / borde, (n - i) / borde)
                    lfo = 1 + oscilacion * math.sin(DOS_PI * 0.13 * i / TASA + f)
                    v = math.sin(fase) + 0.25 * math.sin(2 * fase)
                    b[(i0 + i) % total] += v * env * por_voz * lfo * 0.5

    def bombo(self, inicio, ganancia=0.5):
        n = int(0.22 * TASA)
        i0 = int(inicio * TASA)
        fase = 0.0
        for i in range(n):
            t = i / TASA
            fase += DOS_PI * (46 + 110 * math.exp(-t * 34)) / TASA
            self.b[(i0 + i) % self.n] += math.sin(fase) * math.exp(-t * 15) * ganancia

    def ruido(self, inicio, duracion, ganancia, brillo=0.5, rng=random):
        """Ruido filtrado: platillos (brillo alto) o caja (brillo bajo)."""
        n = int(duracion * TASA)
        i0 = int(inicio * TASA)
        anterior = 0.0
        for i in range(n):
            blanco = rng.uniform(-1, 1)
            anterior += brillo * (blanco - anterior)
            salida = blanco - anterior if brillo < 0.6 else anterior
            self.b[(i0 + i) % self.n] += salida * math.exp(-i / TASA / (duracion * 0.3)) * ganancia

    def eco(self, retardo, cantidad):
        """Eco circular: la cola también da la vuelta."""
        d = int(retardo * TASA)
        copia = list(self.b)
        for i in range(self.n):
            self.b[(i + d) % self.n] += copia[i] * cantidad

    def suavizar(self, cantidad=0.6):
        """Filtro paso bajo de un polo: quita el brillo digital."""
        anterior = self.b[-1]
        for i in range(self.n):
            anterior += cantidad * (self.b[i] - anterior)
            self.b[i] = anterior

    def normalizar(self, pico=0.72):
        maximo = max(abs(v) for v in self.b) or 1.0
        factor = pico / maximo
        # Compresión suave para que las pistas tengan un volumen parecido.
        self.b = [math.tanh(v * factor * 1.25) * 0.8 for v in self.b]


def escribir(ruta, muestras):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    datos = array.array("h", (max(-32767, min(32767, int(v * 32767))) for v in muestras))
    with wave.open(ruta, "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(TASA)
        archivo.writeframes(datos.tobytes())


def acorde(raiz, tipo, octava):
    base = frecuencia(raiz, octava)
    return [base * 2 ** (s / 12) for s in ACORDES[tipo]]


def arpegio(pista, compas, frecuencias, ganancia, patron, forma="pluck", division=0.5, caida=0.35):
    for paso, indice in enumerate(patron):
        if indice is None:
            continue
        f = frecuencias[indice % len(frecuencias)] * (2 if indice >= len(frecuencias) else 1)
        pista.nota(pista.t(compas, paso * division), caida * 2, f, ganancia, forma, caida=caida)


# ----------------------------------------------------------------------
# Pistas
# ----------------------------------------------------------------------


def menu():
    """Atmosférica: ciudad de noche. Colchón amplio y pocas notas."""
    p = Pista(16, 72)
    prog = [("A", "m9"), ("F", "M7"), ("C", "M7"), ("G", "add9")]
    for c in range(16):
        raiz, tipo = prog[(c // 2) % 4]
        if c % 2 == 0:
            p.pad(p.t(c), p.t(2) * 1.05, acorde(raiz, tipo, 3), 0.42)
            p.nota(p.t(c), p.t(2), frecuencia(raiz, 2), 0.20, "sub", 0.4, 3.0)
        if c % 4 in (1, 3):
            arpegio(p, c, acorde(raiz, tipo, 5), 0.075, [0, None, 2, None, 3, None, 1, None], "pluck", 0.5, 0.7)
    p.eco(p.negra * 1.5, 0.32)
    p.suavizar(0.55)
    return p


def ciudad():
    """Exploración: arpegio que empuja a caminar, sin cansar."""
    p = Pista(16, 92)
    prog = [("D", "m7"), ("Bb", "M7"), ("F", "M7"), ("C", "add9")]
    for c in range(16):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, tipo, 3), 0.26)
        p.nota(p.t(c), p.negra * 1.8, frecuencia(raiz, 2), 0.28, "sub", 0.02, 0.9)
        p.nota(p.t(c, 2.5), p.negra, frecuencia(raiz, 2), 0.18, "sub", 0.02, 0.4)
        arpegio(p, c, acorde(raiz, tipo, 4), 0.09, [0, 2, 1, 3, 2, 1, 3, 2], "pluck", 0.5, 0.26)
        for pulso in range(8):
            if c >= 4:
                p.ruido(p.t(c, pulso * 0.5), 0.05, 0.022 + (0.012 if pulso % 2 else 0), 0.85)
    p.eco(p.negra * 0.75, 0.2)
    p.suavizar(0.7)
    return p


def combate():
    """Mazmorra: bajo en corcheas y batería firme, tensión sin estridencia."""
    p = Pista(16, 128)
    prog = [("E", "m"), ("C", "M"), ("A", "m"), ("B", "m")]
    rng = random.Random(4)
    for c in range(16):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.02, acorde(raiz, tipo, 3), 0.17)
        for pulso in range(8):
            p.nota(p.t(c, pulso * 0.5), p.negra * 0.45, frecuencia(raiz, 2), 0.25, "saw", 0.005, 0.1)
        p.bombo(p.t(c, 0))
        p.bombo(p.t(c, 2))
        if c % 2 == 1:
            p.bombo(p.t(c, 2.5), 0.3)
        p.ruido(p.t(c, 1), 0.14, 0.18, 0.3, rng)
        p.ruido(p.t(c, 3), 0.14, 0.18, 0.3, rng)
        for pulso in range(8):
            p.ruido(p.t(c, pulso * 0.5), 0.04, 0.035, 0.85, rng)
        if c >= 8:
            arpegio(p, c, acorde(raiz, tipo, 4), 0.07, [0, None, 2, 1, None, 2, 0, None], "pluck", 0.5, 0.16)
    p.suavizar(0.8)
    return p


def jefe():
    """Frenética: semicorcheas, doble bombo y motivo insistente de NOVA_404."""
    p = Pista(16, 150)
    prog = [("C", "m"), ("Ab", "M"), ("F", "m"), ("G", "M")]
    motivo = [(0, 7), (0.75, 10), (1.5, 8), (2.5, 7), (3, 3)]
    rng = random.Random(9)
    for c in range(16):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.02, acorde(raiz, tipo, 3), 0.15)
        for pulso in range(16):
            p.nota(p.t(c, pulso * 0.25), p.negra * 0.25, frecuencia(raiz, 2), 0.2, "saw", 0.003, 0.06)
        for pulso in range(4):
            p.bombo(p.t(c, pulso), 0.42)
        p.ruido(p.t(c, 1), 0.13, 0.2, 0.3, rng)
        p.ruido(p.t(c, 3), 0.13, 0.2, 0.3, rng)
        for pulso in range(8):
            p.ruido(p.t(c, pulso * 0.5 + 0.25), 0.04, 0.04, 0.85, rng)
        if c >= 4:
            base = frecuencia("C", 4)
            for pulso, semitonos in motivo:
                p.nota(p.t(c, pulso), p.negra * 0.8, base * 2 ** (semitonos / 12), 0.11, "saw", 0.01, 0.2, 0.004)
    p.suavizar(0.85)
    return p


def misterio():
    """Investigación y cinemáticas: dron y campanas lejanas."""
    p = Pista(12, 60)
    rng = random.Random(21)
    prog = [("C", "m"), ("Ab", "M7"), ("Eb", "M7"), ("G", "sus2")]
    for c in range(0, 12, 2):
        raiz, tipo = prog[(c // 2) % 4]
        p.pad(p.t(c), p.t(2) * 1.05, acorde(raiz, tipo, 3), 0.38)
        p.nota(p.t(c), p.t(2), frecuencia(raiz, 1), 0.22, "sub", 0.8, 4.0)
    escala = [0, 3, 5, 7, 10, 12, 15]
    for _ in range(14):
        c = rng.randrange(12)
        p.nota(p.t(c, rng.randrange(4)), 2.4, frecuencia("C", 5) * 2 ** (rng.choice(escala) / 12), 0.06, "piano", 0.02, 1.0)
    p.eco(p.negra * 1.5, 0.38)
    p.suavizar(0.5)
    return p


def decision():
    """Terminal: un pulso como reloj que no deja de sonar, armonía sin resolver."""
    p = Pista(8, 104)
    prog = [("F", "m"), ("Db", "M7"), ("F", "m"), ("C", "dim")]
    rng = random.Random(3)
    for c in range(8):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, tipo, 3), 0.28)
        p.nota(p.t(c), p.negra * 1.4, frecuencia(raiz, 1), 0.3, "sub", 0.02, 0.7)
        for pulso in range(4):
            p.ruido(p.t(c, pulso), 0.03, 0.09, 0.9, rng)  # tic
            p.nota(p.t(c, pulso + 0.5), 0.08, 1760, 0.018, "seno", 0.002, 0.02)  # tac
        if c % 2 == 1:
            p.nota(p.t(c, 2), p.negra * 2, frecuencia(raiz, 5), 0.05, "piano", 0.02, 0.8)
    p.eco(p.negra * 0.75, 0.15)
    p.suavizar(0.65)
    return p


def crisis():
    """Crisis de reputación: latido grave y disonancia que aprieta."""
    p = Pista(8, 66)
    for c in range(8):
        raiz = ("B", "Bb", "B", "F#")[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, "dim", 3), 0.36, 0.5)
        for pulso in (0, 0.45):
            p.bombo(p.t(c, pulso), 0.34 if pulso == 0 else 0.22)
        for pulso in (2, 2.45):
            p.bombo(p.t(c, pulso), 0.26 if pulso == 2 else 0.17)
        p.nota(p.t(c), p.t(1), frecuencia(raiz, 1), 0.2, "sub", 0.2, 2.0)
        if c % 2 == 1:
            p.nota(p.t(c, 3), 1.8, frecuencia(raiz, 5) * 2 ** (1 / 12), 0.045, "tri", 0.3, 1.0, 0.01)
    p.eco(p.negra, 0.22)
    p.suavizar(0.5)
    return p


def redencion():
    """Redención: piano sencillo y colchón cálido, esperanza contenida."""
    p = Pista(16, 74)
    prog = [("C", "M"), ("G", "M"), ("A", "m7"), ("F", "M7")]
    melodia = [(0, 16), (1, 19), (2, 21), (3, 19), (4, 16), (5, 14), (6, 12), (7, 14)]
    for c in range(16):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, tipo, 3), 0.27)
        p.nota(p.t(c), p.t(1), frecuencia(raiz, 2), 0.2, "sub", 0.2, 1.8)
        arpegio(p, c, acorde(raiz, tipo, 4), 0.1, [0, 1, 2, 1, 3, 1, 2, 1] if tipo != "M" else [0, 1, 2, 1, 2, 1, 0, 1], "piano", 0.5, 0.9)
        if c >= 8:
            pulso, semitonos = melodia[(c - 8) % len(melodia)]
            del pulso
            p.nota(p.t(c, 0), p.negra * 3, frecuencia("C", 4) * 2 ** (semitonos / 12), 0.1, "piano", 0.01, 1.6)
    p.eco(p.negra * 1.5, 0.26)
    p.suavizar(0.55)
    return p


def victoria():
    """Tema de victoria: luminoso, sin fanfarria militar."""
    p = Pista(8, 104)
    prog = [("C", "M9"), ("F", "M7"), ("A", "m7"), ("G", "add9")]
    melodia = (24, 28, 31, 33, 31, 28, 26, 24)
    for c in range(8):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, tipo, 3), 0.28)
        p.nota(p.t(c), p.negra * 2, frecuencia(raiz, 2), 0.26, "sub", 0.02, 1.0)
        arpegio(p, c, acorde(raiz, tipo, 4), 0.09, [0, 1, 2, 3, 2, 3, 1, 2], "pluck", 0.5, 0.25)
        p.nota(p.t(c, 0), p.negra * 2.5, frecuencia("C", 3) * 2 ** (melodia[c] / 12), 0.12, "piano", 0.01, 1.0)
        p.bombo(p.t(c, 0), 0.22)
        p.bombo(p.t(c, 2), 0.22)
    p.eco(p.negra * 0.75, 0.2)
    p.suavizar(0.7)
    return p


def derrota():
    """Derrota: piano escaso y mucho aire. Pesa sin castigar."""
    p = Pista(8, 56)
    prog = [("A", "m"), ("F", "M7"), ("D", "m7"), ("E", "m")]
    for c in range(8):
        raiz, tipo = prog[c % 4]
        p.pad(p.t(c), p.t(1) * 1.05, acorde(raiz, tipo, 3), 0.25)
        for pulso, indice in ((0, 0), (1.5, 2), (2, 1), (3, 2)):
            f = acorde(raiz, tipo, 4)[indice % len(acorde(raiz, tipo, 4))]
            p.nota(p.t(c, pulso), 2.2, f, 0.11, "piano", 0.015, 1.1)
    p.eco(p.negra * 1.5, 0.35)
    p.suavizar(0.45)
    return p


PISTAS = {"menu": menu, "ciudad": ciudad, "combate": combate, "jefe": jefe, "misterio": misterio, "decision": decision,
          "crisis": crisis, "redencion": redencion, "victoria": victoria, "derrota": derrota}


# ----------------------------------------------------------------------
# Efectos
# ----------------------------------------------------------------------


def _efecto(duracion, capas, pico=0.7):
    n = int(duracion * TASA)
    b = [0.0] * n
    for inicio, dur, f, gan, forma, caida in capas:
        i0 = int(inicio * TASA)
        fase = 0.0
        for i in range(min(int(dur * TASA), n - i0)):
            t = i / TASA
            fase += DOS_PI * (f(t) if callable(f) else f) / TASA
            if forma == "seno":
                v = math.sin(fase)
            elif forma == "campana":
                v = math.sin(fase) + 0.5 * math.sin(2.01 * fase) * math.exp(-t * 7) + 0.25 * math.sin(3.02 * fase) * math.exp(-t * 11)
            else:
                v = math.sin(fase) + 0.3 * math.sin(2 * fase)
            b[i0 + i] += v * math.exp(-t / caida) * min(1.0, t / 0.004) * gan
    maximo = max(abs(v) for v in b) or 1.0
    salida = [v / maximo * pico for v in b]
    fundido = int(0.01 * TASA)
    for i in range(fundido):
        salida[-1 - i] *= i / fundido
    return salida


def _nota(s, o=5):
    return frecuencia(s, o)


EFECTOS = {
    "reputacion_sube": lambda: _efecto(0.9, [(0, .7, _nota("E"), .5, "campana", .3), (.1, .7, _nota("G"), .45, "campana", .3), (.2, .7, _nota("C", 6), .45, "campana", .35)], 0.55),
    "reputacion_baja": lambda: _efecto(1.1, [(0, 1, lambda t: 220 * 2 ** (-t * 0.9), .6, "cuerpo", .5), (.05, 1, lambda t: 233 * 2 ** (-t * 0.9), .4, "cuerpo", .45), (0, .3, 60, .6, "seno", .2)], 0.6),
    "crisis": lambda: _efecto(2.2, [(0, 2.2, 49, .9, "seno", .9), (0, 2.2, 58.3, .6, "seno", .8), (.1, 2, 311, .14, "cuerpo", .9), (.1, 2, 329.6, .14, "cuerpo", .9)], 0.72),
    "redencion": lambda: _efecto(2.4, [(0, 2.4, _nota("C", 4), .4, "campana", 1.0), (.2, 2.2, _nota("E", 4), .36, "campana", 1.0), (.4, 2, _nota("G", 4), .34, "campana", 1.0), (.7, 1.7, _nota("C"), .3, "campana", .9)], 0.55),
    "decision_buena": lambda: _efecto(1.0, [(0, 1, _nota("G", 4), .4, "campana", .5), (.12, 1, _nota("D"), .4, "campana", .5)], 0.5),
    "decision_mala": lambda: _efecto(1.1, [(0, 1, _nota("D", 4), .45, "cuerpo", .4), (0, 1, _nota("Eb", 4), .4, "cuerpo", .4), (0, .4, 55, .7, "seno", .25)], 0.6),
    "error_decision": lambda: _efecto(.32, [(0, .3, _nota("A", 3), .5, "cuerpo", .12), (.09, .22, _nota("F", 3), .5, "cuerpo", .1)], 0.45),
    "notificacion": lambda: _efecto(.32, [(0, .3, _nota("E", 6), .4, "campana", .1), (.07, .24, _nota("B", 6), .3, "campana", .09)], 0.3),
    "evidencia": lambda: _efecto(.7, [(0, .6, _nota("G"), .4, "campana", .22), (.08, .6, _nota("B"), .4, "campana", .22), (.17, .5, _nota("E", 6), .4, "campana", .25)], 0.45),
    "mision": lambda: _efecto(.9, [(0, .7, _nota("E"), .4, "campana", .28), (.12, .7, _nota("A"), .4, "campana", .3), (.24, .65, _nota("B"), .4, "campana", .3)], 0.45),
    "transicion": lambda: _efecto(.8, [(0, .8, lambda t: 120 + 240 * t, .6, "seno", .4)], 0.4),
    "glitch": lambda: _efecto(.45, [(0, .08, 1760, .4, "cuerpo", .05), (.08, .08, 110, .6, "cuerpo", .05), (.17, .08, 1480, .4, "cuerpo", .05), (.28, .15, 92, .6, "cuerpo", .08)], 0.5),
    "viral": lambda: _efecto(.55, [(i * .07, .09, 440 + (i % 2) * 220, .35, "cuerpo", .05) for i in range(7)], 0.4),
    "victoria": lambda: _efecto(1.8, [(i * .13, 1.2, _nota(n, o), .4, "campana", .6) for i, (n, o) in enumerate((("C", 5), ("E", 5), ("G", 5), ("C", 6)))], 0.55),
    "derrota": lambda: _efecto(1.8, [(i * .24, 1.2, _nota(n, 4), .42, "cuerpo", .55) for i, n in enumerate(("G", "Eb", "C"))], 0.5),
}


def revisar(nombre, muestras):
    rms = math.sqrt(sum(v * v for v in muestras) / len(muestras))
    pico = max(abs(v) for v in muestras)
    salto = abs(muestras[0] - muestras[-1])
    print(f"{nombre:18s} {len(muestras) / TASA:5.1f} s  pico {pico:.2f}  RMS {20 * math.log10(max(rms, 1e-6)):6.1f} dBFS  costura {salto:.3f}")


def destino(nombre, es_musica):
    """Dónde vive hoy cada archivo propio (assets/audio/, ver assets.SONIDOS):
    la pista o el efecto que el juego usa, o su copia en sin_conectar/ si un
    sonido del pack Bitcade lo reemplazó para ese evento."""
    audio = os.path.join(RAIZ, "assets", "audio")
    if es_musica:
        candidatos = [os.path.join(audio, "musica", f"{nombre}.wav")]
        respaldo = os.path.join(audio, "sin_conectar", f"musica_{nombre}.wav")
    else:
        candidatos = sorted(glob.glob(os.path.join(audio, "sfx", "*", f"{nombre}.wav")))
        respaldo = os.path.join(audio, "sin_conectar", f"sfx_{nombre}.wav")
    return next((ruta for ruta in candidatos if os.path.exists(ruta)), respaldo)


def main():
    random.seed(404)
    ver = "--revisar" in sys.argv
    for nombre, componer in PISTAS.items():
        pista = componer()
        pista.normalizar()
        escribir(destino(nombre, es_musica=True), pista.b)
        if ver:
            revisar(nombre, pista.b)
    for nombre, crear in EFECTOS.items():
        muestras = crear()
        escribir(destino(nombre, es_musica=False), muestras)
        if ver:
            revisar(nombre, muestras)


if __name__ == "__main__":
    main()
