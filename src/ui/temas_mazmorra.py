"""Escenarios por lugar: Colegio, Hospital, Medios y Servidor Central (presentación).

Cada cuarto se pinta una vez en baja resolución (1 píxel = 3 px en pantalla,
la misma densidad que los personajes) y se cachea: cada frame es un solo blit.
Nada de esto toca colisiones, puertas ni tamaños.

Composición común de un cuarto:
    - exterior: lo que se ve más allá de los muros, en los márgenes laterales;
    - cara del muro: una banda de 36 px dentro del borde superior. Es tan alta
      como el cuerpo de un personaje, así que los pies nunca pasan por encima:
      con la misma colisión de siempre el cuarto se lee en perspectiva 3/4;
    - piso y mobiliario bajo: oscuros y desaturados para que personajes y balas
      se distingan siempre (nada es sólido, y debe parecer parte del fondo);
    - luz: viñeta y charcos de luz horneados.

`dibujar_animado` añade lo poco que se mueve (pantallas, LEDs, energía); son
unos cuantos rectángulos por frame.
"""

import math
import random

import pygame

from src.core import assets
from src.ui import arte_colegio, decor_mazmorra

P = 3  # px de pantalla por píxel del cuadro
ALTO_CARA_MURO = 12  # en píxeles del cuadro (36 px en pantalla)
_cache = {}
_focos_actuales = {}  # tema -> focos del último cuarto pedido (None = sin arte generado)


def _caja(s, color, x, y, w, h, borde=None):
    pygame.draw.rect(s, color, (x, y, w, h))
    if borde is not None:
        pygame.draw.rect(s, borde, (x, y, w, h), 1)


def _aclarar(color, d):
    return tuple(max(0, min(255, c + d)) for c in color)


class _Cuadro:
    """Lienzo de baja resolución y dónde queda el cuarto dentro de él."""

    def __init__(self, rect, direcciones, rng, toxicidad, arte=False):
        self.ancho, self.alto = 1280 // P, (assets.ALTO_MUNDO_TEMA) // P
        self.s = pygame.Surface((self.ancho, self.alto))
        self.origen_y = assets.Y_MUNDO_TEMA
        g = assets.GROSOR_MURO // P
        self.x = rect.left // P
        self.y = (rect.top - self.origen_y) // P
        self.w = rect.width // P
        self.h = rect.height // P
        self.g = g
        self.rng = rng
        self.direcciones = set(direcciones)
        self.toxicidad = toxicidad
        self.arte = arte  # hay arte generado: el decorador pone piso, muro y muebles
        # Piso útil, sin la cara del muro.
        self.piso = pygame.Rect(self.x, self.y + ALTO_CARA_MURO, self.w, self.h - ALTO_CARA_MURO)
        self.cara = pygame.Rect(self.x, self.y, self.w, ALTO_CARA_MURO)
        self.libres = [self._zona_puerta(d) for d in self.direcciones] + [self._zona_central()]

    def _zona_puerta(self, direccion):
        ancho = assets.ANCHO_PUERTA // P + 10
        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        if direccion == "N":
            return pygame.Rect(cx - ancho // 2, self.y, ancho, ALTO_CARA_MURO + 22)
        if direccion == "S":
            return pygame.Rect(cx - ancho // 2, self.y + self.h - 22, ancho, 22)
        if direccion == "E":
            return pygame.Rect(self.x + self.w - 30, cy - ancho // 2, 30, ancho)
        return pygame.Rect(self.x, cy - ancho // 2, 30, ancho)

    def _zona_central(self):
        return pygame.Rect(self.x + self.w // 2 - 34, self.y + self.h // 2 - 34, 68, 62)

    def libre(self, rect):
        return not any(pygame.Rect(rect).colliderect(zona) for zona in self.libres)

    def colocar(self, ancho, alto, intentos=24, zona=None):
        """Busca un lugar donde no estorbe a puertas, centro ni otro mueble."""
        zona = zona or self.piso.inflate(-6, -6)
        for _ in range(intentos):
            x = self.rng.randint(zona.left, max(zona.left, zona.right - ancho))
            y = self.rng.randint(zona.top, max(zona.top, zona.bottom - alto))
            rect = pygame.Rect(x, y, ancho, alto)
            if self.libre(rect.inflate(4, 4)):
                self.libres.append(rect)
                return rect
        return None


# ----------------------------------------------------------------------
# Piezas comunes
# ----------------------------------------------------------------------


def _muros(c, color_borde, color_tapa):
    """Los muros de siempre (franja de GROSOR_MURO) sobre el exterior."""
    ext = pygame.Rect(c.x - c.g, c.y - c.g, c.w + 2 * c.g, c.h + 2 * c.g)
    pygame.draw.rect(c.s, color_tapa, ext)
    pygame.draw.rect(c.s, color_borde, ext, 1)
    pygame.draw.line(c.s, _aclarar(color_tapa, 14), (ext.left + 1, ext.top + 1), (ext.right - 2, ext.top + 1))


def _hueco_puertas(c, oscuro, marco):
    """Vano de la puerta norte en la cara del muro: la puerta llega hasta el piso."""
    if "N" in c.direcciones:
        ancho = assets.ANCHO_PUERTA // P + 2
        x = c.x + c.w // 2 - ancho // 2
        _caja(c.s, marco, x - 2, c.y, ancho + 4, ALTO_CARA_MURO)
        _caja(c.s, oscuro, x, c.y, ancho, ALTO_CARA_MURO)
        pygame.draw.line(c.s, _aclarar(oscuro, 18), (x, c.y + ALTO_CARA_MURO - 1), (x + ancho - 1, c.y + ALTO_CARA_MURO - 1))


def _sombra_cara(c):
    """Línea de sombra donde el muro toca el piso."""
    capa = pygame.Surface((c.w, 4), pygame.SRCALPHA)
    for i in range(4):
        pygame.draw.line(capa, (0, 0, 16, 110 - i * 28), (0, i), (c.w, i))
    c.s.blit(capa, (c.x, c.y + ALTO_CARA_MURO))


def _luz(c, cx, cy, radio, color, fuerza=60, aplastada=1.0):
    """Charco de luz aditivo (se hornea una vez)."""
    capa = pygame.Surface((radio * 2, radio * 2))
    for r in range(radio, 0, -3):
        t = 1 - r / radio
        valor = tuple(round(k * fuerza / 255 * t * t) for k in color)
        pygame.draw.circle(capa, valor, (radio, radio), r)
    if aplastada != 1.0:
        capa = pygame.transform.scale(capa, (radio * 2, round(radio * 2 * aplastada)))
    c.s.blit(capa, capa.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)


def _vineta(c, fuerza=70):
    """Oscurece el cuarto hacia sus bordes: el centro de la acción se lee mejor."""
    ancho = 40
    capa = pygame.Surface((c.ancho, c.alto), pygame.SRCALPHA)
    for i in range(ancho):
        alfa = round(fuerza * (1 - i / ancho) ** 2)
        pygame.draw.rect(capa, (4, 5, 20, alfa), (c.x - c.g + i, c.y - c.g + i, c.w + 2 * c.g - 2 * i, c.h + 2 * c.g - 2 * i), 1)
    c.s.blit(capa, (0, 0))


def _exterior_oscuro(c, color):
    """Los márgenes fuera del cuarto quedan atrás: más oscuros y sin detalle fino."""
    capa = pygame.Surface((c.ancho, c.alto), pygame.SRCALPHA)
    capa.fill((*color, 150))
    c.s.blit(capa, (0, 0))


def _huella_nova(c):
    """A más toxicidad, más grietas magenta de NOVA_404: se nota lo infectado."""
    cantidad = int(c.toxicidad // 18)
    for _ in range(cantidad):
        x = c.rng.randint(c.piso.left + 8, c.piso.right - 24)
        y = c.rng.randint(c.piso.top + 8, c.piso.bottom - 12)
        px = x
        for _ in range(c.rng.randint(4, 9)):
            ancho = c.rng.randint(2, 7)
            color = assets.COLOR_TEMA_NOVA_OSCURO if c.rng.random() < 0.7 else assets.COLOR_MAGENTA_OSCURO
            pygame.draw.line(c.s, color, (px, y), (px + ancho, y))
            px += ancho
            y += c.rng.choice((-1, 0, 1))


def _base_con_arte(c, tema, oscuro, marco):
    """Piso y cara lisos para que el decorador multiplique la textura y ponga
    el muro generado; se conservan el vano norte, la sombra y las grietas."""
    pygame.draw.rect(c.s, assets.BASE_PISO_TEMA[tema], c.piso)
    pygame.draw.rect(c.s, oscuro, c.cara)
    _hueco_puertas(c, oscuro, marco)
    _sombra_cara(c)
    _huella_nova(c)


# ----------------------------------------------------------------------
# Colegio
# ----------------------------------------------------------------------


def _pintar_colegio(c):
    """Con el pack del Colegio (src/ui/arte_colegio.py) el piso queda en un
    gris neutro sobre el que se multiplican los tablones reales, y la
    pizarra, el tablero y los pupitres los pone el pack; sin él, todo se
    pinta aquí como siempre."""
    arte = arte_colegio.disponible()
    piso_a, piso_b, linea = (72, 56, 56), (80, 62, 60), (56, 42, 46)
    # Exterior: pasillo con casilleros.
    c.s.fill((30, 26, 52))
    for lado in (range(0, c.x - c.g), range(c.x + c.w + c.g, c.ancho)):
        for x in lado:
            if x % 12 == 0:
                _caja(c.s, (40, 58, 88), x, 0, 11, c.alto, (26, 38, 62))
                pygame.draw.rect(c.s, (66, 84, 118), (x + 8, c.alto // 2, 2, 5))
                for y in range(8, c.alto, 60):
                    pygame.draw.line(c.s, (30, 44, 70), (x + 2, y), (x + 8, y))
    _exterior_oscuro(c, (18, 14, 40))
    _muros(c, (24, 22, 52), (72, 62, 82))
    # Piso: tablones de madera oscura.
    pygame.draw.rect(c.s, assets.COLOR_BASE_PISO_COLEGIO if arte else piso_a, c.piso)
    for fila, y in enumerate(range(c.piso.top, c.piso.bottom, 8) if not arte else ()):
        pygame.draw.line(c.s, linea, (c.piso.left, y), (c.piso.right - 1, y))
        for x in range(c.piso.left + (fila * 13) % 34, c.piso.right, 34):
            pygame.draw.line(c.s, linea, (x, y), (x, y + 7))
        if fila % 3 == 1:
            pygame.draw.rect(c.s, piso_b, (c.piso.left, y + 1, c.piso.width, 7))
            for x in range(c.piso.left + (fila * 13) % 34, c.piso.right, 34):
                pygame.draw.line(c.s, linea, (x, y), (x, y + 7))
    # Cara del muro: friso verde escolar y pared crema.
    pygame.draw.rect(c.s, (92, 80, 92), c.cara)
    pygame.draw.rect(c.s, (46, 86, 82), (c.cara.left, c.cara.bottom - 4, c.cara.width, 4))
    pygame.draw.line(c.s, (66, 112, 104), (c.cara.left, c.cara.bottom - 5), (c.cara.right - 1, c.cara.bottom - 5))
    # Pizarra con tiza y tablero de avisos.
    if arte:
        _cierre_colegio(c)
        return
    x = c.x + 26
    _caja(c.s, (84, 62, 44), x - 1, c.y + 1, 72, 9)
    _caja(c.s, (28, 62, 54), x, c.y + 2, 70, 7)
    for i in range(5):
        pygame.draw.line(c.s, (190, 214, 196), (x + 4 + i * 13, c.y + 4 + i % 2), (x + 13 + i * 13, c.y + 4 + i % 2))
    pygame.draw.line(c.s, (214, 200, 150), (x + 8, c.y + 7), (x + 28, c.y + 7))
    tablero = c.x + c.w - 90
    _caja(c.s, (128, 96, 62), tablero, c.y + 1, 60, 9, (84, 62, 44))
    for i, color in enumerate(((226, 214, 170), (130, 190, 220), (236, 150, 160), (240, 210, 120), (170, 226, 170))):
        pygame.draw.rect(c.s, color, (tablero + 3 + i * 11, c.y + 2 + (i % 2), 8, 6))
    # Reloj y pantalla informativa.
    reloj = (c.x + c.w // 2 + 56, c.y + 5)
    pygame.draw.circle(c.s, (226, 220, 200), reloj, 3)
    pygame.draw.line(c.s, (40, 36, 50), reloj, (reloj[0], reloj[1] - 2))
    _caja(c.s, (18, 20, 44), c.x + c.w // 2 - 92, c.y + 2, 26, 7, (70, 66, 88))
    # Tapete central apagado para la zona de acción.
    # Pupitres en filas a los costados, de madera y sillas.
    for columna in range(3):
        for fila in range(5):
            for lado in (c.piso.left + 18 + columna * 28, c.piso.right - 34 - columna * 28):
                rect = pygame.Rect(lado, c.piso.top + 14 + fila * 28, 16, 8)
                if c.rng.random() < 0.12 or not c.libre(rect.inflate(2, 4)):
                    continue
                _caja(c.s, (84, 62, 56), rect.x, rect.y, rect.w, rect.h, (58, 42, 44))
                pygame.draw.line(c.s, (100, 76, 66), (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1))
                _caja(c.s, (50, 62, 92), rect.x + 5, rect.bottom + 2, 6, 4, (36, 44, 72))
                if c.rng.random() < 0.3:
                    pygame.draw.rect(c.s, (210, 204, 186), (rect.x + 3, rect.y + 2, 5, 3))
    # Hojas y cuadernos tirados: el aula se quedó a medias.
    for _ in range(14):
        rect = c.colocar(4, 3)
        if rect:
            pygame.draw.rect(c.s, c.rng.choice(((190, 186, 172), (150, 170, 196), (214, 170, 170))), rect)
    _cierre_colegio(c)


def _cierre_colegio(c):
    """Puertas, sombra, grietas de NOVA y la luz cálida de las ventanas."""
    _hueco_puertas(c, (24, 20, 40), (84, 62, 44))
    _sombra_cara(c)
    _huella_nova(c)
    _luz(c, c.x + 90, c.y + 70, 80, (255, 216, 150), 46, 0.7)
    _luz(c, c.x + c.w // 2, c.y + c.h // 2, 120, (255, 224, 180), 26)
    _vineta(c)


# ----------------------------------------------------------------------
# Hospital
# ----------------------------------------------------------------------


def _pintar_hospital(c):
    c.s.fill((16, 32, 44))
    # Exterior: pasillo clínico con franjas.
    for lado in (pygame.Rect(0, 0, c.x - c.g, c.alto), pygame.Rect(c.x + c.w + c.g, 0, c.ancho - c.x - c.w - c.g, c.alto)):
        pygame.draw.rect(c.s, (28, 56, 68), lado)
        for y in range(0, c.alto, 24):
            pygame.draw.line(c.s, (22, 44, 56), (lado.left, y), (lado.right, y))
        pygame.draw.rect(c.s, (40, 118, 110), (lado.centerx - 2, 0, 4, c.alto))
    _exterior_oscuro(c, (6, 16, 28))
    _muros(c, (12, 28, 40), (88, 118, 128))
    # Piso: baldosa clínica fría y guías de color que llevan a urgencias.
    if c.arte:
        _base_con_arte(c, "hospital", (16, 40, 52), (80, 104, 116))
        for x in (c.x + c.w // 4, c.x + 3 * c.w // 4):
            _luz(c, x, c.y + c.h // 2, 110, (150, 230, 255), 40, 0.8)
        _vineta(c, 80)
        return
    pygame.draw.rect(c.s, (54, 80, 92), c.piso)
    for x in range(c.piso.left, c.piso.right, 16):
        pygame.draw.line(c.s, (46, 70, 82), (x, c.piso.top), (x, c.piso.bottom - 1))
    for y in range(c.piso.top, c.piso.bottom, 16):
        pygame.draw.line(c.s, (46, 70, 82), (c.piso.left, y), (c.piso.right - 1, y))
    for x0 in range(c.piso.left, c.piso.right, 32):
        for y0 in range(c.piso.top, c.piso.bottom, 32):
            pygame.draw.rect(c.s, (58, 86, 98), (x0 + 1, y0 + 1, 15, 15))
    medio_y = c.y + c.h // 2
    pygame.draw.rect(c.s, (150, 60, 72), (c.piso.left, medio_y + 44, c.piso.width, 2))
    pygame.draw.rect(c.s, (46, 130, 136), (c.piso.left, medio_y + 48, c.piso.width, 2))
    # Cara del muro: azulejo pálido, franja de seguridad.
    pygame.draw.rect(c.s, (134, 164, 168), c.cara)
    for x in range(c.cara.left, c.cara.right, 6):
        pygame.draw.line(c.s, (120, 150, 156), (x, c.cara.top), (x, c.cara.bottom - 1))
    pygame.draw.rect(c.s, (64, 150, 148), (c.cara.left, c.cara.bottom - 4, c.cara.width, 3))
    # Monitores de signos vitales y señales.
    for x in (c.x + 24, c.x + 56, c.x + c.w - 78):
        _caja(c.s, (14, 26, 34), x, c.y + 2, 24, 7, (50, 70, 80))
    _caja(c.s, (160, 30, 44), c.x + c.w // 2 - 84, c.y + 2, 26, 7)
    _caja(c.s, (236, 236, 240), c.x + c.w // 2 - 74, c.y + 3, 6, 5)
    pygame.draw.rect(c.s, (160, 30, 44), (c.x + c.w // 2 - 72, c.y + 3, 2, 5))
    pygame.draw.rect(c.s, (160, 30, 44), (c.x + c.w // 2 - 74, c.y + 5, 6, 1))
    _caja(c.s, (20, 110, 72), c.x + c.w // 2 + 58, c.y + 2, 22, 7)
    pygame.draw.line(c.s, (170, 250, 190), (c.x + c.w // 2 + 62, c.y + 5), (c.x + c.w // 2 + 75, c.y + 5))
    _caja(c.s, (172, 192, 196), c.x + c.w - 38, c.y + 1, 20, 10, (110, 130, 140))
    # Camillas con sábana, soporte de suero y biombos a los costados.
    for lado in (c.piso.left + 8, c.piso.right - 56):
        for fila in range(3):
            rect = pygame.Rect(lado, c.piso.top + 14 + fila * 48, 46, 18)
            if not c.libre(rect.inflate(2, 2)):
                continue
            c.libres.append(rect)
            _caja(c.s, (76, 92, 104), rect.x, rect.y + 3, rect.w, rect.h - 4, (44, 58, 70))
            _caja(c.s, (152, 176, 182), rect.x + 2, rect.y + 2, rect.w - 4, rect.h - 7, (112, 134, 146))
            _caja(c.s, (196, 212, 214), rect.x + 2, rect.y + 3, 9, rect.h - 9)
            soporte = (rect.right + 3, rect.y - 2)
            pygame.draw.line(c.s, (112, 130, 140), soporte, (soporte[0], soporte[1] + 16))
            _caja(c.s, (170, 214, 226), soporte[0] - 2, soporte[1] - 1, 5, 5)
    # Biombos de tela y carros de curación.
    for _ in range(4):
        rect = c.colocar(26, 4)
        if rect:
            _caja(c.s, (84, 136, 140), rect.x, rect.y, rect.w, 3, (56, 104, 110))
            for x in range(rect.x, rect.right, 4):
                pygame.draw.line(c.s, (60, 110, 116), (x, rect.y), (x, rect.y + 2))
    for _ in range(4):
        rect = c.colocar(11, 8)
        if rect:
            _caja(c.s, (120, 138, 148), rect.x, rect.y, rect.w, rect.h, (72, 90, 102))
            pygame.draw.rect(c.s, (176, 66, 76), (rect.x + 4, rect.y + 2, 3, 3))
    _hueco_puertas(c, (16, 40, 52), (80, 104, 116))
    _sombra_cara(c)
    _huella_nova(c)
    # Tubos fluorescentes fríos.
    for x in (c.x + c.w // 4, c.x + 3 * c.w // 4):
        _luz(c, x, c.y + c.h // 2, 110, (150, 230, 255), 40, 0.8)
    _vineta(c, 80)


# ----------------------------------------------------------------------
# Empresa de Medios
# ----------------------------------------------------------------------


def _pintar_medios(c):
    c.s.fill((10, 10, 28))
    # Exterior: pasillos de servidores.
    for lado in (pygame.Rect(0, 0, c.x - c.g, c.alto), pygame.Rect(c.x + c.w + c.g, 0, c.ancho - c.x - c.w - c.g, c.alto)):
        for y in range(0, c.alto, 22):
            _caja(c.s, (22, 24, 48), lado.left + 3, y + 2, lado.width - 6, 19, (36, 40, 76))
            for i in range(lado.left + 6, lado.right - 6, 4):
                pygame.draw.rect(c.s, c.rng.choice(((62, 230, 196), (255, 190, 60), (40, 46, 90), (40, 46, 90))), (i, y + 6, 1, 1))
            pygame.draw.line(c.s, (44, 48, 90), (lado.left + 5, y + 12), (lado.right - 6, y + 12))
    _exterior_oscuro(c, (6, 6, 20))
    _muros(c, (14, 14, 36), (40, 42, 78))
    # Piso: alfombra técnica oscura y placas de piso elevado.
    if c.arte:
        _base_con_arte(c, "medios", (6, 6, 20), (64, 66, 110))
        _luz(c, c.x + c.w // 2, c.y + c.h // 2 + 10, 120, (120, 150, 255), 34, 0.8)
        _luz(c, c.x + c.w // 4, c.y + 14, 60, (255, 90, 140), 36, 0.8)
        _luz(c, c.x + 3 * c.w // 4, c.y + 14, 60, (70, 220, 240), 36, 0.8)
        _vineta(c, 90)
        return
    pygame.draw.rect(c.s, (30, 32, 60), c.piso)
    for x in range(c.piso.left, c.piso.right, 20):
        for y in range(c.piso.top, c.piso.bottom, 20):
            pygame.draw.rect(c.s, (34, 37, 68), (x + 1, y + 1, 18, 18))
            pygame.draw.rect(c.s, (24, 26, 52), (x + 1, y + 18, 18, 1))
    # Cara del muro: paneles acústicos, pantallas de noticias y letrero AL AIRE.
    pygame.draw.rect(c.s, (34, 34, 64), c.cara)
    for x in range(c.cara.left, c.cara.right, 10):
        pygame.draw.line(c.s, (26, 26, 52), (x, c.cara.top), (x, c.cara.bottom - 1))
    for x in list(range(c.x + 12, c.x + c.w // 2 - 54, 34)) + list(range(c.x + c.w // 2 + 54, c.x + c.w - 30, 34)):
        _caja(c.s, (10, 14, 34), x, c.y + 1, 30, 9, (70, 74, 120))
        pygame.draw.rect(c.s, (160, 40, 70), (x + 2, c.y + 7, 26, 2))
    # Cables, escritorios de redacción, cámaras y bastidores.
    for _ in range(5):
        x = c.rng.randint(c.piso.left + 6, c.piso.right - 60)
        y = c.rng.randint(c.piso.top + 6, c.piso.bottom - 10)
        puntos = [(x, y)]
        for _ in range(c.rng.randint(4, 8)):
            x += c.rng.randint(6, 18)
            y += c.rng.randint(-5, 5)
            puntos.append((x, max(c.piso.top + 3, min(c.piso.bottom - 3, y))))
        pygame.draw.lines(c.s, (16, 16, 34), False, [(a, b + 1) for a, b in puntos])
        pygame.draw.lines(c.s, c.rng.choice(((52, 52, 92), (70, 40, 92), (36, 78, 88))), False, puntos)
    for lado in (c.piso.left + 8, c.piso.right - 44):
        for fila in range(3):
            rect = pygame.Rect(lado, c.piso.top + 12 + fila * 50, 36, 15)
            if not c.libre(rect.inflate(2, 2)):
                continue
            c.libres.append(rect)
            _caja(c.s, (58, 50, 62), rect.x, rect.y + 4, rect.w, rect.h - 4, (36, 32, 48))
            for mx in (rect.x + 2, rect.x + 19):
                _caja(c.s, (12, 14, 34), mx, rect.y, 15, 8, (84, 88, 128))
                pygame.draw.rect(c.s, (34, 110, 120), (mx + 2, rect.y + 2, 11, 2))
    for _ in range(3):  # cámaras de estudio con trípode
        rect = c.colocar(14, 14)
        if rect:
            cx, cy = rect.center
            for dx, dy in ((-6, 6), (6, 6), (0, -6)):
                pygame.draw.line(c.s, (20, 20, 40), (cx, cy), (cx + dx, cy + dy))
            _caja(c.s, (70, 72, 104), cx - 4, cy - 3, 8, 5, (34, 36, 66))
    for _ in range(3):  # bastidor bajo
        rect = c.colocar(14, 22)
        if rect:
            _caja(c.s, (24, 26, 52), rect.x, rect.y, rect.w, rect.h, (58, 62, 104))
            for y in range(rect.y + 3, rect.bottom - 2, 4):
                pygame.draw.line(c.s, (44, 48, 86), (rect.x + 2, y), (rect.right - 3, y))
    _hueco_puertas(c, (6, 6, 20), (64, 66, 110))
    _sombra_cara(c)
    _huella_nova(c)
    # Focos de estudio y pantallas que iluminan la sala.
    _luz(c, c.x + c.w // 2, c.y + c.h // 2 + 10, 120, (120, 150, 255), 34, 0.8)
    _luz(c, c.x + c.w // 4, c.y + 14, 60, (255, 90, 140), 36, 0.8)
    _luz(c, c.x + 3 * c.w // 4, c.y + 14, 60, (70, 220, 240), 36, 0.8)
    _vineta(c, 90)


# ----------------------------------------------------------------------
# Servidor Central
# ----------------------------------------------------------------------


def _pintar_servidor(c):
    c.s.fill((6, 4, 18))
    for lado in (pygame.Rect(0, 0, c.x - c.g, c.alto), pygame.Rect(c.x + c.w + c.g, 0, c.ancho - c.x - c.w - c.g, c.alto)):
        for x in range(lado.left + 2, lado.right - 6, 11):
            _caja(c.s, (18, 12, 40), x, 0, 9, c.alto, (42, 26, 70))
            for y in range(4, c.alto, 7):
                if c.rng.random() < 0.55:
                    pygame.draw.rect(c.s, c.rng.choice(((255, 56, 120), (164, 110, 255), (60, 40, 110))), (x + 2, y, 5, 1))
    _exterior_oscuro(c, (6, 2, 18))
    _muros(c, (42, 18, 64), (26, 16, 50))
    # Piso: placas negras con circuitos que convergen al núcleo. Con arte, el
    # mármol de la Alcaldía se multiplica encima: los circuitos quedan como
    # la corrupción de NOVA que se mete bajo el piso del poder.
    if c.arte:
        pygame.draw.rect(c.s, assets.BASE_PISO_TEMA["servidor"], c.piso)
    else:
        pygame.draw.rect(c.s, (16, 12, 34), c.piso)
        for x in range(c.piso.left, c.piso.right, 24):
            pygame.draw.line(c.s, (24, 18, 48), (x, c.piso.top), (x, c.piso.bottom - 1))
        for y in range(c.piso.top, c.piso.bottom, 24):
            pygame.draw.line(c.s, (24, 18, 48), (c.piso.left, y), (c.piso.right - 1, y))
    centro = (c.x + c.w // 2, c.y + c.h // 2 + 4)
    rng = c.rng
    for _ in range(26):
        angulo = rng.uniform(0, 2 * math.pi)
        x = centro[0] + math.cos(angulo) * c.w * 0.52
        y = centro[1] + math.sin(angulo) * c.h * 0.52
        x = max(c.piso.left + 2, min(c.piso.right - 2, x))
        y = max(c.piso.top + 2, min(c.piso.bottom - 2, y))
        px, py = round(x), round(y)
        color = (86, 26, 92) if rng.random() < 0.7 else (120, 28, 84)
        # Traza en escuadra hacia el centro, como una placa de circuito.
        medio = (px, centro[1] + round((py - centro[1]) * 0.35))
        pygame.draw.line(c.s, color, (px, py), medio)
        pygame.draw.line(c.s, color, medio, (centro[0] + round((px - centro[0]) * 0.2), medio[1]))
        pygame.draw.line(c.s, color, (centro[0] + round((px - centro[0]) * 0.2), medio[1]), centro)
        pygame.draw.rect(c.s, (190, 60, 150), (px - 1, py - 1, 2, 2))
    # Núcleo en el piso.
    for radio, color in ((34, (44, 16, 64)), (26, (66, 20, 84)), (18, (30, 12, 50))):
        pygame.draw.circle(c.s, color, centro, radio, 2 if radio != 18 else 0)
    if c.arte:
        _huella_nova(c)
        _sombra_cara(c)
        _luz(c, centro[0], centro[1], 100, (255, 60, 170), 60, 0.9)
        _luz(c, c.x + c.w // 2, c.y + 30, 150, (255, 210, 150), 22, 0.6)
        _vineta(c, 100)
        return
    # Cara del muro: torres de servidores y pantallas corruptas con la marca de NOVA.
    pygame.draw.rect(c.s, (24, 14, 46), c.cara)
    for x in range(c.cara.left + 2, c.cara.right - 10, 16):
        _caja(c.s, (14, 10, 34), x, c.y + 1, 14, 10, (60, 34, 94))
        for y in range(c.y + 3, c.y + 10, 2):
            if rng.random() < 0.7:
                pygame.draw.line(c.s, rng.choice(((255, 56, 120), (120, 60, 180), (62, 230, 196))), (x + 2, y), (x + rng.randint(4, 11), y))
    # Cables gruesos que bajan del techo.
    for x in range(c.x + 40, c.x + c.w - 30, 62):
        y = c.piso.top
        px = x
        for _ in range(9):
            nx = px + rng.randint(-5, 5)
            ny = y + 7
            pygame.draw.line(c.s, (8, 6, 20), (px, y), (nx, ny), 3)
            pygame.draw.line(c.s, (54, 30, 84), (px, y), (nx, ny))
            px, y = nx, ny
    _huella_nova(c)
    _sombra_cara(c)
    _luz(c, centro[0], centro[1], 100, (255, 60, 170), 60, 0.9)
    _luz(c, c.x + 30, c.y + 10, 70, (160, 80, 255), 40)
    _luz(c, c.x + c.w - 30, c.y + 10, 70, (160, 80, 255), 40)
    _vineta(c, 110)


_PINTORES = {
    "colegio": _pintar_colegio,
    "hospital": _pintar_hospital,
    "medios": _pintar_medios,
    "servidor": _pintar_servidor,
}


def fondo(rect, tema, semilla, direcciones=(), toxicidad=0):
    """Superficie de todo el mundo del cuarto (ancho de pantalla). Se dibuja
    en (0, assets.Y_MUNDO_TEMA). Cacheada: se pinta una vez por cuarto."""
    clave = (tema, rect.size, rect.topleft, semilla, tuple(sorted(direcciones)), int(toxicidad // 18))
    if clave not in _cache:
        if len(_cache) > 24:
            _cache.clear()
        arte = decor_mazmorra.disponible(tema)
        cuadro = _Cuadro(rect, direcciones, random.Random(f"{tema}-{semilla}"), toxicidad, arte)
        _PINTORES[tema](cuadro)
        final = pygame.transform.scale(cuadro.s, (cuadro.ancho * P, cuadro.alto * P))
        focos = None
        if arte:
            libres = [pygame.Rect(r.x * P, r.y * P, r.w * P, r.h * P) for r in cuadro.libres]
            if tema == "colegio" and decor_mazmorra.variante(tema, semilla) == "aula":
                arte_colegio.vestir_aula(final, rect, cuadro.origen_y, semilla, libres)
            cuarto = pygame.Rect(cuadro.x * P, cuadro.y * P, cuadro.w * P, cuadro.h * P)
            banda = assets.BANDA_DECOR_ARENA if tema == "servidor" else assets.BANDA_DECOR_MAZMORRA
            focos = decor_mazmorra.vestir(final, cuarto, tema, semilla, libres, direcciones, banda)
        final = final.convert() if pygame.display.get_surface() is not None else final
        _cache[clave] = (final, focos)
    final, _focos_actuales[tema] = _cache[clave]
    return final


# ----------------------------------------------------------------------
# Lo poco que se mueve
# ----------------------------------------------------------------------


def _pantallas_medios(pantalla, rect, tiempo):
    y = rect.top + 1 * P
    for i, x in enumerate(list(range(rect.left + 12 * P, rect.left + rect.width // 2 - 54 * P, 34 * P))
                          + list(range(rect.left + rect.width // 2 + 54 * P, rect.right - 30 * P, 34 * P))):
        fase = int(tiempo * 5 + i * 3) % 10
        color = assets.COLOR_TEMA_PANTALLA[(i + int(tiempo / 3)) % len(assets.COLOR_TEMA_PANTALLA)]
        pygame.draw.rect(pantalla, color, (x + 2 * P, y + 1 * P, 26 * P, 4 * P))
        ancho_noticia = (8 + fase) * P
        pygame.draw.rect(pantalla, assets.COLOR_TEXTO_HUD, (x + 3 * P, y + 2 * P, ancho_noticia, 1 * P))
    # Letrero AL AIRE que respira.
    if math.sin(tiempo * 2.2) > -0.5:
        pygame.draw.rect(pantalla, assets.COLOR_GRAVE, (rect.centerx - 42 * P, rect.top + 3 * P, 8 * P, 5 * P))


def _monitores_hospital(pantalla, rect, tiempo):
    for k, x0 in enumerate((rect.left + 24 * P, rect.left + 56 * P, rect.right - 78 * P)):
        y = rect.top + 5 * P
        anterior = None
        for i in range(0, 22):
            t = (i / 22 + tiempo * 0.5 + k * 0.3) % 1.0
            pico = -3 * math.exp(-((t - 0.5) ** 2) / 0.002) + 1.5 * math.exp(-((t - 0.56) ** 2) / 0.002)
            punto = (x0 + (i + 1) * P, y + round(pico) * P)
            if anterior is not None:
                pygame.draw.line(pantalla, assets.COLOR_TEMA_ECG, anterior, punto, 2)
            anterior = punto
    # Señal de emergencia: pulso rojo suave.
    if math.sin(tiempo * 3) > 0:
        pygame.draw.rect(pantalla, assets.COLOR_GRAVE, (rect.centerx - 84 * P, rect.top - 3, 26 * P, 3))


def _pantalla_colegio(pantalla, rect, tiempo):
    x, y = rect.centerx - 92 * P, rect.top + 2 * P
    pygame.draw.rect(pantalla, assets.COLOR_TEMA_INFO, (x + 2 * P, y + 1 * P, 22 * P, 2 * P))
    for i in range(3):
        if int(tiempo * 1.5 + i) % 4 != 3:
            pygame.draw.rect(pantalla, assets.COLOR_TEXTO_HUD, (x + (3 + i * 7) * P, y + 4 * P, 5 * P, 1 * P))


def _energia_servidor(pantalla, rect, tiempo):
    """El núcleo late y la señal corre por las torres: la presencia de NOVA_404."""
    _pulso_nucleo(pantalla, rect, tiempo)
    for i in range(0, rect.width // (16 * P)):
        if (i * 7 + int(tiempo * 8)) % 13 == 0:
            x = rect.left + (2 + i * 16) * P
            pygame.draw.rect(pantalla, assets.COLOR_NOVA, (x + 2 * P, rect.top + 3 * P, 10 * P, 2 * P))


def _pulso_nucleo(pantalla, rect, tiempo):
    centro = (rect.centerx, rect.centery + 4 * P)
    fase = (tiempo * 0.7) % 1.0
    radio = round(40 + fase * 110)
    capa = pygame.Surface((radio * 2 + 6, radio * 2 + 6), pygame.SRCALPHA)
    pygame.draw.circle(capa, (*assets.COLOR_NOVA, round(70 * (1 - fase))), (radio + 3, radio + 3), radio, 3)
    pantalla.blit(capa, capa.get_rect(center=centro))


_ANIMADORES = {
    "colegio": _pantalla_colegio,
    "hospital": _monitores_hospital,
    "medios": _pantallas_medios,
    "servidor": _energia_servidor,
}


def dibujar_animado(pantalla, rect, tema, tiempo):
    """Capa viva del cuarto. Con reducir movimiento se puede omitir sin perder nada.

    Con arte generado lo que late son los objetos que brillan del cuarto (sus
    pantallas y LEDs, donde de verdad están); sin él, los de siempre."""
    focos = _focos_actuales.get(tema)
    if focos is not None:
        decor_mazmorra.dibujar_focos(pantalla, focos, tiempo, assets.Y_MUNDO_TEMA)
        if tema == "servidor":
            _pulso_nucleo(pantalla, rect, tiempo)
        return
    animador = _ANIMADORES.get(tema)
    if animador is not None:
        animador(pantalla, rect, tiempo)
