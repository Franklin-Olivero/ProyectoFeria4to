"""Lógica y dibujo de un cuarto de mazmorra: puertas y enemigos placeholder.

Todavía no hay IA de enemigos, movimiento de jugador ni ataques. El
único comportamiento real es: mientras existan enemigos en el cuarto,
las 4 puertas (N, S, E, W) permanecen bloqueadas; cuando la lista de
enemigos queda vacía, las puertas se abren.
"""

import pygame

ANCHO_CUARTO = 500
ALTO_CUARTO = 400

GROSOR_MURO = 4
COLOR_MURO = (200, 200, 210)

ANCHO_PUERTA = 80
GROSOR_PUERTA = 20
COLOR_PUERTA_BLOQUEADA = (200, 30, 30)
COLOR_PUERTA_ABIERTA = (30, 180, 60)

TAMANIO_ENEMIGO = 40
COLOR_ENEMIGO = (230, 160, 20)

TECLA_DEBUG_ELIMINAR_ENEMIGO = pygame.K_k


class Puerta:
    """Una puerta del cuarto: su rectángulo y si está bloqueada o abierta."""

    def __init__(self, direccion, rect):
        self.direccion = direccion
        self.rect = rect
        self.bloqueada = True

    def color(self):
        return COLOR_PUERTA_BLOQUEADA if self.bloqueada else COLOR_PUERTA_ABIERTA


class Enemigo:
    """Enemigo placeholder: solo un cuadrado en una posición fija."""

    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, TAMANIO_ENEMIGO, TAMANIO_ENEMIGO)
        self.rect.center = (x, y)


class Cuarto:
    """Un cuarto con 4 puertas y una lista de enemigos.

    Las puertas están bloqueadas mientras `enemigos` no esté vacía, y se
    abren automáticamente en cuanto se vacía.
    """

    def __init__(self):
        ancho_ventana = pygame.display.get_surface().get_width()
        alto_ventana = pygame.display.get_surface().get_height()

        self.rect = pygame.Rect(0, 0, ANCHO_CUARTO, ALTO_CUARTO)
        self.rect.center = (ancho_ventana // 2, alto_ventana // 2)

        self.puertas = self._crear_puertas()
        self.enemigos = self._crear_enemigos_iniciales()
        self._actualizar_estado_puertas()

    def _crear_puertas(self):
        r = self.rect

        rect_n = pygame.Rect(0, 0, ANCHO_PUERTA, GROSOR_PUERTA)
        rect_n.center = (r.centerx, r.top)

        rect_s = pygame.Rect(0, 0, ANCHO_PUERTA, GROSOR_PUERTA)
        rect_s.center = (r.centerx, r.bottom)

        rect_e = pygame.Rect(0, 0, GROSOR_PUERTA, ANCHO_PUERTA)
        rect_e.center = (r.right, r.centery)

        rect_w = pygame.Rect(0, 0, GROSOR_PUERTA, ANCHO_PUERTA)
        rect_w.center = (r.left, r.centery)

        return {
            "N": Puerta("N", rect_n),
            "S": Puerta("S", rect_s),
            "E": Puerta("E", rect_e),
            "W": Puerta("W", rect_w),
        }

    def _crear_enemigos_iniciales(self):
        r = self.rect
        return [
            Enemigo(r.centerx - 120, r.centery),
            Enemigo(r.centerx, r.centery - 60),
            Enemigo(r.centerx + 120, r.centery),
        ]

    def _actualizar_estado_puertas(self):
        bloqueadas = len(self.enemigos) > 0
        for puerta in self.puertas.values():
            puerta.bloqueada = bloqueadas

    def eliminar_un_enemigo(self):
        """Debug: quita un enemigo de la lista y refresca el estado de las puertas."""
        if self.enemigos:
            self.enemigos.pop()
            self._actualizar_estado_puertas()

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == TECLA_DEBUG_ELIMINAR_ENEMIGO:
            self.eliminar_un_enemigo()

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, COLOR_MURO, self.rect, GROSOR_MURO)

        for puerta in self.puertas.values():
            pygame.draw.rect(pantalla, puerta.color(), puerta.rect)

        for enemigo in self.enemigos:
            pygame.draw.rect(pantalla, COLOR_ENEMIGO, enemigo.rect)
