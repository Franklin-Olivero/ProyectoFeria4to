"""Ciudad nocturna animada del menú principal (solo presentación).

Capas, de atrás hacia adelante:

    cielo (degradado + nubes, quieto)
    capa lejana   -> naves lejanas  -> bruma rosada del horizonte
    capa media    -> naves medias
    capa cercana (letreros holográficos que parpadean) -> naves cercanas
    azoteas en primer plano -> lluvia

Cada capa de edificios se genera una sola vez al crear el fondo, en
baja resolución (1 píxel = ESCALA_PIXEL_FONDO píxeles de pantalla) y se
escala sin suavizado, así se ve pixel art y cada frame es solo un par de
blits por capa. Las capas son "tileables": su ancho es el de la pantalla
y se dibujan dos veces seguidas, desplazadas a su propia velocidad
(parallax: lo cercano se mueve más rápido que lo lejano).

Con reducir_movimiento la ciudad queda quieta: sin desplazamiento, sin
naves, sin lluvia y sin parpadeo de letreros.
"""

import math
import random

import pygame

from src.core import assets
from src.ui import sprites
from src.ui.fuentes import fuente

_COLOR_TRANSPARENTE = (1, 2, 3)  # colorkey de las capas


class FondoCiudad:
    def __init__(self, tamanio, semilla=assets.SEMILLA_FONDO_CIUDAD):
        self.ancho, self.alto = tamanio
        self._rng = random.Random(semilla)
        self._cielo = _generar_cielo(tamanio, self._rng)
        self._bruma = _generar_bruma(tamanio)
        self._capas = [_Capa(tamanio, config, self._rng) for config in assets.CAPAS_FONDO_CIUDAD]
        self._naves = [_Nave(self, profundidad) for profundidad in assets.PROFUNDIDADES_NAVES]
        self._lluvia = [self._gota_nueva(al_azar=True) for _ in range(assets.CANTIDAD_GOTAS_LLUVIA)]
        self._parpadeo = None  # (capa, rect, segundos restantes)
        self._proximo_parpadeo = 1.0

    def actualizar(self, dt, reducir_movimiento):
        if reducir_movimiento:
            return
        for capa in self._capas:
            capa.actualizar(dt)
        for nave in self._naves:
            nave.actualizar(dt)
        for gota in self._lluvia:
            gota[1] += gota[2] * dt
            gota[0] += gota[2] * dt * assets.INCLINACION_LLUVIA
            if gota[1] > self.alto:
                gota[:] = self._gota_nueva()
        self._actualizar_parpadeo(dt)

    def dibujar(self, pantalla, reducir_movimiento):
        pantalla.blit(self._cielo, (0, 0))
        for indice, capa in enumerate(self._capas):
            capa.dibujar(pantalla)
            if self._parpadeo is not None and self._parpadeo[0] is capa and not reducir_movimiento:
                capa.apagar_letrero(pantalla, self._parpadeo[1])
            if not reducir_movimiento:
                for nave in self._naves:
                    if nave.profundidad["capa"] == indice:
                        nave.dibujar(pantalla)
            if indice == 0:
                pantalla.blit(self._bruma, (0, 0))
        if not reducir_movimiento:
            for x, y, velocidad, largo, color in self._lluvia:
                fin = (x + largo * assets.INCLINACION_LLUVIA, y + largo)
                pygame.draw.line(pantalla, color, (x, y), fin, 1)

    def _gota_nueva(self, al_azar=False):
        rng = self._rng
        y = rng.uniform(0, self.alto) if al_azar else rng.uniform(-60, -10)
        return [
            rng.uniform(-self.alto * assets.INCLINACION_LLUVIA, self.ancho), y,
            rng.uniform(*assets.VELOCIDAD_LLUVIA), rng.uniform(*assets.LARGO_GOTA_LLUVIA),
            rng.choice(assets.COLORES_LLUVIA),
        ]

    def _actualizar_parpadeo(self, dt):
        """Cada tanto un letrero holográfico se apaga un instante."""
        if self._parpadeo is not None:
            capa, rect, restante = self._parpadeo
            self._parpadeo = (capa, rect, restante - dt) if restante > dt else None
            return
        self._proximo_parpadeo -= dt
        if self._proximo_parpadeo > 0:
            return
        self._proximo_parpadeo = self._rng.uniform(*assets.INTERVALO_PARPADEO_LETRERO)
        con_letreros = [capa for capa in self._capas if capa.letreros]
        if con_letreros:
            capa = self._rng.choice(con_letreros)
            self._parpadeo = (capa, self._rng.choice(capa.letreros), assets.DURACION_PARPADEO_LETRERO)


class _Capa:
    """Una fila de edificios tileable que se desplaza a velocidad constante."""

    def __init__(self, tamanio, config, rng):
        self.config = config
        self.velocidad = config["velocidad"]
        self.desplazamiento = 0.0
        self.letreros = []  # rects (coordenadas de la capa) de los letreros
        self.superficie = self._generar(tamanio, rng)
        self.ancho = self.superficie.get_width()

    def actualizar(self, dt):
        self.desplazamiento = (self.desplazamiento + self.velocidad * dt) % self.ancho

    def dibujar(self, pantalla):
        x = -round(self.desplazamiento)
        pantalla.blit(self.superficie, (x, 0))
        pantalla.blit(self.superficie, (x + self.ancho, 0))

    def apagar_letrero(self, pantalla, rect):
        x = -round(self.desplazamiento)
        for desfase in (x, x + self.ancho):
            capa = pygame.Surface(rect.size, pygame.SRCALPHA)
            capa.fill(assets.COLOR_LETRERO_APAGADO)
            pantalla.blit(capa, (rect.x + desfase, rect.y))

    def _generar(self, tamanio, rng):
        escala = assets.ESCALA_PIXEL_FONDO
        ancho = math.ceil(tamanio[0] / escala)
        alto = math.ceil(tamanio[1] / escala)
        c = self.config
        baja = pygame.Surface((ancho, alto))
        baja.fill(_COLOR_TRANSPARENTE)
        edificios = []
        x = 0
        while x < ancho:
            w = rng.randint(*c["ancho"])
            h = rng.randint(*c["alto"])
            edificios.append(pygame.Rect(x, alto - h, w, h))
            x += w + rng.randint(*c["hueco"])
        con_letrero = []
        for edificio in edificios:
            # Cada edificio se dibuja también corrido un ancho a cada lado:
            # lo que sale por un borde entra por el otro (capa sin costuras).
            # Misma semilla en las tres copias: mismas ventanas.
            semilla = rng.random()
            for desfase in (-ancho, 0, ancho):
                _dibujar_edificio(baja, edificio.move(desfase, 0), c, random.Random(semilla))
            if rng.random() < c["prob_letrero"]:
                con_letrero.append(edificio)
        superficie = pygame.transform.scale(baja, (ancho * escala, alto * escala)).convert()
        superficie.set_colorkey(_COLOR_TRANSPARENTE)
        for edificio in con_letrero:
            self._letrero(superficie, edificio, escala, rng, ancho * escala)
        return superficie

    def _letrero(self, superficie, edificio, escala, rng, ancho_capa):
        """Letrero holográfico sobre la fachada: panel oscuro, borde neón
        y texto. Se dibuja en resolución completa para que el texto se lea."""
        texto = rng.choice(assets.TEXTOS_LETREROS)
        color = rng.choice(assets.COLORES_LETREROS)
        # Solo los textos cortos van en vertical, para no cortar palabras.
        corto = len(texto.replace(" ", "")) <= assets.LETRAS_MAXIMAS_LETRERO_VERTICAL
        vertical = corto and rng.random() < assets.PROB_LETRERO_VERTICAL and edificio.width * escala > 30
        f = fuente(assets.TAMANIO_FUENTE_LETRERO, True)
        if vertical:
            renders = [f.render(letra, False, color) for letra in texto.replace(" ", "")]
            ancho = max(r.get_width() for r in renders) + 10
            alto = sum(r.get_height() - 4 for r in renders) + 10
        else:
            render = f.render(texto, False, color)
            ancho, alto = render.get_width() + 14, render.get_height() + 6
        x = edificio.x * escala + max(4, (edificio.width * escala - ancho) // 2)
        y = edificio.y * escala + rng.randint(12, max(14, edificio.height * escala // 3))
        rect = pygame.Rect(x, y, ancho, alto)
        # Un letrero que se saldría por el borde derecho se omite: así la
        # capa sigue siendo tileable sin cortar ningún texto.
        if rect.right > ancho_capa or rect.bottom > superficie.get_height():
            return
        pygame.draw.rect(superficie, assets.COLOR_FONDO_LETRERO, rect)
        pygame.draw.rect(superficie, color, rect, 2)
        if vertical:
            cy = rect.top + 5
            for letra in renders:
                superficie.blit(letra, letra.get_rect(midtop=(rect.centerx, cy)))
                cy += letra.get_height() - 4
        else:
            superficie.blit(render, render.get_rect(center=rect.center))
        self.letreros.append(rect)


def _dibujar_edificio(baja, rect, c, rng):
    """Cuerpo, borde iluminado, cornisa, ventanas y antena (en baja resolución)."""
    pygame.draw.rect(baja, c["cuerpo"], rect)
    pygame.draw.line(baja, c["borde"], rect.topleft, (rect.left, rect.bottom), 1)
    if c.get("cornisa"):
        pygame.draw.line(baja, c["cornisa"], rect.topleft, (rect.right - 1, rect.top), 1)
    paso = c["paso_ventana"]
    for wy in range(rect.top + 3, rect.bottom - 2, paso):
        for wx in range(rect.left + 2, rect.right - 2, paso):
            if rng.random() < c["densidad_ventanas"]:
                baja.set_at((wx, wy), rng.choice(c["ventanas"]))
    if rng.random() < c["prob_antena"]:
        ax = rect.left + rect.width // 2
        largo = rng.randint(3, 9)
        pygame.draw.line(baja, c["borde"], (ax, rect.top - 1), (ax, rect.top - largo), 1)
        baja.set_at((ax, rect.top - largo - 1), assets.COLOR_LUZ_ANTENA)


class _Nave:
    """Nave que cruza la pantalla de un lado a otro; al salir vuelve a
    entrar tras una pausa, con otra altura, sentido y velocidad."""

    def __init__(self, fondo, profundidad):
        self.fondo = fondo
        self.profundidad = profundidad
        self._reiniciar(espera=fondo._rng.uniform(0, assets.ESPERA_MAXIMA_NAVE))

    def _reiniciar(self, espera):
        rng = self.fondo._rng
        p = self.profundidad
        self.espera = espera
        self.sentido = rng.choice((-1, 1))
        self.velocidad = rng.uniform(*p["velocidad"])
        self.y = rng.uniform(*p["altura"]) * self.fondo.alto
        imagen = sprites.sprite(sprites.NAVE, sprites.PALETA_NAVE, p["escala"])
        self.imagen = imagen if self.sentido > 0 else pygame.transform.flip(imagen, True, False)
        self.estela = _estela(p["largo_estela"], max(2, p["escala"] - 1), self.sentido)
        margen = self.imagen.get_width() + p["largo_estela"]
        self.x = -margen if self.sentido > 0 else self.fondo.ancho + margen

    def actualizar(self, dt):
        if self.espera > 0:
            self.espera -= dt
            return
        self.x += self.sentido * self.velocidad * dt
        margen = self.imagen.get_width() + self.profundidad["largo_estela"]
        if not (-margen * 1.5 <= self.x <= self.fondo.ancho + margen * 1.5):
            self._reiniciar(espera=self.fondo._rng.uniform(1.0, assets.ESPERA_MAXIMA_NAVE))

    def dibujar(self, pantalla):
        if self.espera > 0:
            return
        rect = self.imagen.get_rect(center=(round(self.x), round(self.y)))
        # La estela sale de la cola: a la izquierda si va hacia la derecha.
        if self.sentido > 0:
            pantalla.blit(self.estela, self.estela.get_rect(midright=(rect.left + 2, rect.centery + 1)))
        else:
            pantalla.blit(self.estela, self.estela.get_rect(midleft=(rect.right - 2, rect.centery + 1)))
        pantalla.blit(self.imagen, rect)


def _estela(largo, grosor, sentido):
    """Franja que se desvanece desde la nave hacia atrás."""
    superficie = pygame.Surface((largo, grosor), pygame.SRCALPHA)
    for i in range(largo):
        cerca_de_la_nave = i / largo if sentido > 0 else 1 - i / largo
        alfa = round(assets.ALFA_ESTELA_NAVE * cerca_de_la_nave ** 2)
        pygame.draw.line(superficie, (*assets.COLOR_ESTELA_NAVE, alfa), (i, 0), (i, grosor - 1))
    return superficie


def _generar_cielo(tamanio, rng):
    """Degradado vertical de noche a violeta en el horizonte, con nubes."""
    ancho, alto = tamanio
    cielo = pygame.Surface(tamanio)
    arriba, abajo = assets.COLOR_CIELO_ARRIBA, assets.COLOR_CIELO_HORIZONTE
    for y in range(alto):
        t = y / (alto - 1)
        pygame.draw.line(cielo, [round(a + (b - a) * t) for a, b in zip(arriba, abajo)], (0, y), (ancho, y))
    escala = assets.ESCALA_PIXEL_FONDO
    for _ in range(assets.CANTIDAD_NUBES):
        # Nube escalonada: franjas cada vez más angostas hacia arriba, con
        # el borde de abajo iluminado por la ciudad.
        w = rng.randint(40, 120) * escala
        x = rng.randint(-w // 2, ancho)
        y = rng.randint(4, alto // 3)
        for paso in range(rng.randint(2, 4)):
            franja_w = round(w * (1 - paso * 0.28))
            franja_x = x + rng.randint(0, max(0, w - franja_w))
            franja_y = y - paso * 3 * escala
            pygame.draw.rect(cielo, assets.COLOR_NUBE, (franja_x, franja_y, franja_w, 3 * escala))
        pygame.draw.rect(cielo, assets.COLOR_BORDE_NUBE, (x, y + 3 * escala - escala, w, escala))
    for _ in range(assets.CANTIDAD_ESTRELLAS):
        x = rng.randrange(0, ancho, escala)
        y = rng.randrange(0, alto // 2, escala)
        pygame.draw.rect(cielo, assets.COLOR_ESTRELLA, (x, y, escala, escala))
    return cielo.convert()


def _generar_bruma(tamanio):
    """Resplandor rosado que sube desde abajo (luz de la ciudad en la niebla)."""
    ancho, alto = tamanio
    bruma = pygame.Surface(tamanio, pygame.SRCALPHA)
    inicio = round(alto * assets.INICIO_BRUMA)
    for y in range(inicio, alto):
        t = (y - inicio) / max(1, alto - inicio)
        pygame.draw.line(bruma, (*assets.COLOR_BRUMA, round(assets.ALFA_BRUMA * t)), (0, y), (ancho, y))
    return bruma
