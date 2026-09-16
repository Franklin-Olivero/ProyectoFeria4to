"""Proyectil genérico, reutilizable tanto por el jugador como por los
enemigos.

Se mueve en línea recta a velocidad constante y se marca a sí mismo
como `vivo = False` cuando sale de los límites del cuarto. Quien lo
usa (el loop principal) decide cuándo marcarlo como no vivo por
impacto, usando `colisiona_con`.
"""

import pygame

from src.core import assets


class Proyectil:
    def __init__(self, posicion, direccion, velocidad, danio, color, tamanio=None):
        tamanio = tamanio or assets.TAMANIO_PROYECTIL
        self.rect = pygame.Rect(0, 0, tamanio, tamanio)
        self.rect.center = posicion
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)

        self.direccion = pygame.Vector2(direccion)
        if self.direccion.length_squared() > 0:
            self.direccion = self.direccion.normalize()

        self.velocidad = velocidad
        self.danio = danio
        self.color = color
        self.vivo = True

    def actualizar(self, dt, limites):
        """Avanza el proyectil y lo mata si quedó fuera de `limites`."""
        self.posicion += self.direccion * self.velocidad * dt
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))
        if not limites.colliderect(self.rect):
            self.vivo = False

    def colisiona_con(self, otro_rect):
        return self.vivo and self.rect.colliderect(otro_rect)

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, self.color, self.rect)
