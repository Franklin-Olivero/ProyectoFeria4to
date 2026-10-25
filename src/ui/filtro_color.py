"""Filtro de daltonismo sobre toda la pantalla (solo presentación).

Qué hace: aplica a cada píxel de la imagen final (justo antes de
pygame.display.flip) una matriz 3x3 de corrección ("daltonización"):

    salida = M · (R, G, B)        M = I + E · (I - S)

S simula cómo ve el color una persona con ese tipo de daltonismo
(matrices de Machado, Oliveira y Fernandes, 2009, severidad máxima); I - S
es la información de color que esa persona pierde, y E la redistribuye
en los canales que sí distingue (rojo-verde -> verde y azul en protanopia
y deuteranopia; azul-amarillo -> rojo y verde en tritanopia). Es una
aproximación hecha en sRGB: ayuda a separar los colores del juego, pero
no reemplaza las pruebas con jugadores daltónicos.

Cómo, sin numpy: pygame no multiplica matrices de color, pero sí sabe
(1) multiplicar cada canal por una constante (fill con BLEND_MULT),
(2) sumar y restar imágenes (blit con BLEND_ADD / BLEND_SUB) y
(3) leer los mismos bytes de una imagen con otro orden de canales
(pygame.image.frombuffer con otro formato, sin copiar). Con (3) se
obtienen "vistas" donde el canal rojo de salida trae, por ejemplo, el
verde de entrada. Las 9 entradas de M se reparten en 4 vistas:

    IDENTIDAD: R<-R  G<-G  B<-B      CRUZ_A: R<-G  G<-B  (B en 0)
    CRUZ_B:    G<-R  B<-G  (R en 0)  CRUZ_S: R<-B  B<-R  (G en 0)

y cada vista se multiplica por sus coeficientes y se suma (o resta, si
el coeficiente es negativo). Un coeficiente mayor que 1 se reparte en
varias pasadas, porque BLEND_MULT solo multiplica por 0..1.
"""

import math

import pygame

from src.core.preferencias import FILTRO_NINGUNO

IDENTIDAD, CRUZ_A, CRUZ_B, CRUZ_S = "identidad", "cruz_a", "cruz_b", "cruz_s"
UMBRAL_COEFICIENTE = 0.01  # coeficientes menores se ignoran (invisibles en 8 bits)

# Simulación del daltonismo (Machado et al. 2009, severidad 1.0).
SIMULACION = {
    "Protanopia": ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.786281, 0.099216),
                   (-0.003882, -0.048116, 1.051998)),
    "Deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042940, 0.968881)),
    "Tritanopia": ((1.255528, -0.076749, -0.178779),
                   (-0.078411, 0.930809, 0.147602),
                   (0.004733, 0.691367, 0.303900)),
}
# Redistribución del error: a qué canales visibles se pasa lo que se pierde.
_ERROR_ROJO_VERDE = ((0, 0, 0), (0.7, 1, 0), (0.7, 0, 1))
_ERROR_AZUL_AMARILLO = ((1, 0, 0.7), (0, 1, 0.7), (0, 0, 0))
REDISTRIBUCION = {
    "Protanopia": _ERROR_ROJO_VERDE,
    "Deuteranopia": _ERROR_ROJO_VERDE,
    "Tritanopia": _ERROR_AZUL_AMARILLO,
}
_I = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def _multiplicar(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def matriz_correccion(filtro):
    """M = I + E·(I - S) para `filtro`, o None con "Ninguno"."""
    if filtro not in SIMULACION:
        return None
    perdida = tuple(tuple(_I[i][j] - SIMULACION[filtro][i][j] for j in range(3)) for i in range(3))
    redistribuida = _multiplicar(REDISTRIBUCION[filtro], perdida)
    return tuple(tuple(_I[i][j] + redistribuida[i][j] for j in range(3)) for i in range(3))


def coeficientes_por_vista(m):
    """Las 9 entradas de M repartidas en las 4 vistas: {vista: (r, g, b)}.
    m[salida][entrada]; cada entrada de M aparece en exactamente una vista."""
    return {
        IDENTIDAD: (m[0][0], m[1][1], m[2][2]),
        CRUZ_A: (m[0][1], m[1][2], 0.0),
        CRUZ_B: (0.0, m[1][0], m[2][1]),
        CRUZ_S: (m[0][2], 0.0, m[2][0]),
    }


def factor_escala(m):
    """Cuántas veces se reduce M antes de aplicarla: la suma de los
    coeficientes positivos de una fila puede pasar de 1 (blanco -> más de
    255) y BLEND_ADD satura en 255 antes de que lleguen las restas. Con
    M/k ninguna suma parcial se satura; al final se multiplica por k."""
    mayor = max(sum(c for c in fila if c > 0) for fila in m)
    return max(1, math.ceil(mayor - 1e-9))


def descomponer(m):
    """(pasadas, k): lista de pasadas (vista, color 0-255, signo) cuya suma
    reproduce M/k, y el factor k (ver factor_escala). Cada pasada es
    "vista × color/255", sumada (+1) o restada (-1). Primero todas las
    sumas (la identidad la primera) y después las restas, para que la
    resta saturada en 0 no se coma valores que una suma posterior repondría."""
    k = factor_escala(m)
    sumas, restas = [], []
    for vista, coeficientes in coeficientes_por_vista(m).items():
        for signo, destino in ((1, sumas), (-1, restas)):
            resto = [max(0.0, signo * c / k) if abs(c) >= UMBRAL_COEFICIENTE else 0.0 for c in coeficientes]
            while any(r > 0 for r in resto):
                tramo = [min(1.0, r) for r in resto]
                destino.append((vista, tuple(round(t * 255) for t in tramo), signo))
                resto = [max(0.0, r - t) for r, t in zip(resto, tramo)]
    return sumas + restas, k


class FiltroColor:
    """Aplica el filtro elegido a la superficie de la pantalla. Guarda las
    superficies de trabajo para no crearlas cada frame."""

    def __init__(self):
        self._descomposiciones = {}  # filtro -> (pasadas, k)
        self._tamanio = None

    def descomposicion(self, filtro):
        if filtro not in self._descomposiciones:
            m = matriz_correccion(filtro)
            self._descomposiciones[filtro] = descomponer(m) if m is not None else ([], 1)
        return self._descomposiciones[filtro]

    def aplicar(self, pantalla, filtro):
        """Reemplaza el contenido de `pantalla` por su versión filtrada."""
        if filtro == FILTRO_NINGUNO:
            return
        pasadas, k = self.descomposicion(filtro)
        if not pasadas:
            return
        self._preparar(pantalla.get_size())
        vistas = self._vistas(pantalla, {vista for vista, _, _ in pasadas})

        # La pantalla hace de acumulador. La primera pasada de la identidad
        # se multiplica directo sobre ella (es la imagen original); si no
        # hay, arranca en negro.
        usos = {}
        for vista, _, _ in pasadas:
            usos[vista] = usos.get(vista, 0) + 1
        inicio = 0
        if pasadas[0][0] == IDENTIDAD and pasadas[0][2] > 0:
            pantalla.fill(pasadas[0][1], special_flags=pygame.BLEND_MULT)
            usos[IDENTIDAD] -= 1
            inicio = 1
        else:
            pantalla.fill((0, 0, 0))
        for vista, color, signo in pasadas[inicio:]:
            usos[vista] -= 1
            # Última vez que se usa la vista: se multiplica en su lugar y
            # se ahorra la copia al temporal.
            fuente = vistas[vista]
            if usos[vista] > 0:
                self._temporal.blit(fuente, (0, 0))
                fuente = self._temporal
            fuente.fill(color, special_flags=pygame.BLEND_MULT)
            pantalla.blit(fuente, (0, 0), special_flags=pygame.BLEND_ADD if signo > 0 else pygame.BLEND_SUB)

        if k > 1:  # se calculó M/k: se multiplica por k sumando la imagen k-1 veces
            self._temporal.blit(pantalla, (0, 0))
            for _ in range(k - 1):
                pantalla.blit(self._temporal, (0, 0), special_flags=pygame.BLEND_ADD)

    def _preparar(self, tamanio):
        if tamanio == self._tamanio:
            return
        self._tamanio = tamanio
        # Formatos de almacenamiento conocidos (bytes de cada píxel, de menor a mayor):
        #   XRGB: B G R X   XBGR: R G B X   BGRX: X R G B
        self._xrgb = pygame.Surface(tamanio, 0, 32, masks=(0xFF0000, 0x00FF00, 0x0000FF, 0))
        self._xbgr = pygame.Surface(tamanio, 0, 32, masks=(0x0000FF, 0x00FF00, 0xFF0000, 0))
        self._bgrx = pygame.Surface(tamanio, 0, 32, masks=(0x0000FF00, 0x00FF0000, 0xFF000000, 0))
        self._cruces = {vista: pygame.Surface(tamanio, 0, 32) for vista in (CRUZ_A, CRUZ_B, CRUZ_S)}
        self._temporal = pygame.Surface(tamanio, 0, 32)

    def _vistas(self, pantalla, necesarias):
        """{vista: Surface opaca}. La identidad es una copia de la pantalla
        en XRGB; las cruzadas leen esos bytes con otro formato (sin copiar)
        y el blit a una superficie normal los deja como colores comunes,
        listos para multiplicarlos."""
        tamanio = pantalla.get_size()
        self._xrgb.blit(pantalla, (0, 0))
        vistas = {IDENTIDAD: self._xrgb}
        if CRUZ_S in necesarias:
            # XRGB leído como RGBX: R<-B, G<-G, B<-R (el G se anula con su coeficiente 0).
            vistas[CRUZ_S] = self._cruces[CRUZ_S]
            vistas[CRUZ_S].blit(pygame.image.frombuffer(self._xrgb.get_buffer(), tamanio, "RGBX"), (0, 0))
        if CRUZ_A in necesarias:
            # XBGR leído como ARGB: R<-G, G<-B, B<-X (=0). ARGB trae alfa
            # (el byte X, en 0): se desactiva para copiar los colores tal cual.
            self._xbgr.blit(self._xrgb, (0, 0))
            vista = pygame.image.frombuffer(self._xbgr.get_buffer(), tamanio, "ARGB")
            vista.set_alpha(None)
            vistas[CRUZ_A] = self._cruces[CRUZ_A]
            vistas[CRUZ_A].blit(vista, (0, 0))
            del vista  # suelta el bloqueo de _xbgr
        if CRUZ_B in necesarias:
            # BGRX leído como RGBX: R<-X (=0), G<-R, B<-G.
            self._bgrx.blit(self._xrgb, (0, 0))
            vistas[CRUZ_B] = self._cruces[CRUZ_B]
            vistas[CRUZ_B].blit(pygame.image.frombuffer(self._bgrx.get_buffer(), tamanio, "RGBX"), (0, 0))
        return vistas
