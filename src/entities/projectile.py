"""Proyectil genérico, reutilizable tanto por el jugador como por los
enemigos.

Se mueve en línea recta a velocidad constante y se marca a sí mismo
como `vivo = False` cuando sale de los límites del cuarto. El loop
principal detecta el choque con `colisiona_con` y delega el efecto en
`al_impactar(enemigo)`: por defecto daña y se destruye, y cada rol
define subclases que lo sobreescriben (empujar, perforar, área...).
"""

from collections import deque

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

    def al_impactar(self, enemigo):
        """Efecto al chocar con un enemigo: lo daña y se destruye."""
        enemigo.recibir_dano(self.danio)
        self.vivo = False

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, self.color, self.rect)


class ProyectilConEstela(Proyectil):
    """Proyectil redondo que deja una estela corta (lo usa el jefe).

    Guarda las últimas posiciones separadas al menos `espaciado` px (no
    una por frame: con proyectiles lentos se superpondrían) y las dibuja
    con transparencia decreciente según `alfas`.
    """

    def __init__(self, posicion, direccion, velocidad, danio, color, tamanio, alfas, espaciado):
        super().__init__(posicion, direccion, velocidad, danio, color, tamanio)
        self.alfas = alfas
        self.espaciado = espaciado
        self.estela = deque(maxlen=len(alfas))  # la más reciente primero

    def actualizar(self, dt, limites):
        ultima = self.estela[0] if self.estela else None
        if ultima is None or self.posicion.distance_to(ultima) >= self.espaciado:
            self.estela.appendleft(pygame.Vector2(self.posicion))
        super().actualizar(dt, limites)

    def dibujar(self, pantalla):
        radio = self.rect.width // 2
        for centro, alfa in zip(self.estela, self.alfas):
            superficie = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.circle(superficie, (*self.color, alfa), (radio, radio), radio)
            pantalla.blit(superficie, superficie.get_rect(center=(round(centro.x), round(centro.y))))
        pygame.draw.circle(pantalla, self.color, self.rect.center, radio)
