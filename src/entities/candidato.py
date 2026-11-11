"""Candidato: el rol que remata.

Ataque: onda expansiva radial. No es direccional: un círculo centrado
donde estaba el Candidato que crece hasta RADIO_MAXIMO_ONDA y daña una
vez a cada enemigo que toque.
Habilidad: Debate Rebotante, dispara 3 proyectiles que rebotan en los
bordes del cuarto (invierten su componente x o y) hasta agotar sus
rebotes o su tiempo de vida.
"""

import pygame

from src.core import assets
from src.entities.player import JugadorBase
from src.entities.projectile import Proyectil


class OndaExpansiva:
    """Efecto de área con la misma interfaz que Proyectil (actualizar,
    colisiona_con, al_impactar, dibujar, vivo), para que el loop
    principal lo trate igual que a cualquier proyectil."""

    def __init__(self, centro, danio):
        self.centro = pygame.Vector2(centro)
        self.radio = 0.0
        self.tiempo = 0.0
        self.danio = danio
        self.vivo = True
        self.golpeados = []

    def actualizar(self, dt, limites):
        """Crece linealmente hasta el radio máximo y luego desaparece.
        No usa `limites`: un área no "sale" del cuarto."""
        self.tiempo += dt
        progreso = min(self.tiempo / assets.DURACION_ONDA, 1.0)
        self.radio = assets.RADIO_MAXIMO_ONDA * progreso
        if progreso >= 1.0:
            self.vivo = False

    def colisiona_con(self, otro_rect):
        """Círculo vs rectángulo: el punto del rect más cercano al centro
        está a menos de `radio`."""
        if not self.vivo:
            return False
        cercano_x = max(otro_rect.left, min(self.centro.x, otro_rect.right))
        cercano_y = max(otro_rect.top, min(self.centro.y, otro_rect.bottom))
        return self.centro.distance_to((cercano_x, cercano_y)) <= self.radio

    def al_impactar(self, enemigo):
        if enemigo in self.golpeados:
            return
        self.golpeados.append(enemigo)
        enemigo.recibir_dano(self.danio)

    def al_chocar_cobertura(self, cobertura):
        """La onda es un área: daña una vez cada mueble que alcanza y sigue."""
        if cobertura in self.golpeados:
            return
        self.golpeados.append(cobertura)
        cobertura.recibir_impacto(self.danio)

    def dibujar(self, pantalla):
        if self.radio >= 1:
            pygame.draw.circle(
                pantalla, assets.COLOR_ONDA_CANDIDATO, self.centro, self.radio, assets.GROSOR_ONDA
            )


class ProyectilRebotante(Proyectil):
    """Proyectil que rebota en los bordes en vez de destruirse."""

    def __init__(self, posicion, direccion, danio):
        super().__init__(
            posicion=posicion,
            direccion=direccion,
            velocidad=assets.VELOCIDAD_PROYECTIL,
            danio=danio,
            color=assets.COLOR_PROYECTIL_REBOTANTE,
        )
        self.rebotes = 0
        self.tiempo_vida = assets.TIEMPO_VIDA_REBOTANTE

    def actualizar(self, dt, limites):
        self.posicion += self.direccion * self.velocidad * dt
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))

        # Toca un borde vertical -> invierte velocidad_x; uno horizontal
        # -> invierte velocidad_y. Se reubica dentro para no rebotar dos
        # veces seguidas contra el mismo borde.
        if self.rect.left < limites.left or self.rect.right > limites.right:
            self.direccion.x *= -1
            self.rebotes += 1
        if self.rect.top < limites.top or self.rect.bottom > limites.bottom:
            self.direccion.y *= -1
            self.rebotes += 1
        self.rect.clamp_ip(limites)
        self.posicion.update(self.rect.center)

        self.tiempo_vida -= dt
        if self.rebotes > assets.MAXIMO_REBOTES or self.tiempo_vida <= 0:
            self.vivo = False

    def al_chocar_cobertura(self, cobertura):
        """Daña el mueble y rebota en él como en una pared: se invierte el
        eje por el que menos se metió (esa es la cara que tocó)."""
        cobertura.recibir_impacto(self.danio)
        x, y, ancho, alto = cobertura.hitbox
        entra_x = min(self.rect.right - x, x + ancho - self.rect.left)
        entra_y = min(self.rect.bottom - y, y + alto - self.rect.top)
        if entra_x <= entra_y:
            self.direccion.x *= -1
            self.rect.centerx += entra_x if self.rect.centerx > x + ancho / 2 else -entra_x
        else:
            self.direccion.y *= -1
            self.rect.centery += entra_y if self.rect.centery > y + alto / 2 else -entra_y
        self.posicion.update(self.rect.center)
        self.rebotes += 1
        if self.rebotes > assets.MAXIMO_REBOTES:
            self.vivo = False


class Candidato(JugadorBase):
    rol = "candidato"
    COLOR = assets.COLOR_CANDIDATO
    NOMBRE = "Candidato"
    NOMBRE_HABILIDAD = "Debate Rebotante"
    # Ataque radial (no necesita apuntar) y Debate Rebotante hacia donde
    # camina: la dirección la sigue fijando manejar_movimiento().
    apunta_con_mouse = False

    def ataque_basico(self):
        return [OndaExpansiva(self.rect.center, self.danio)]

    def usar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Debate Rebotante: 3 proyectiles rebotantes en abanico."""
        if not self._gastar_carga():
            return False
        if proyectiles_salida is not None:
            for angulo in assets.ANGULOS_DEBATE_REBOTANTE:
                direccion = self.direccion_mirada.rotate(angulo)
                proyectiles_salida.append(ProyectilRebotante(self.rect.center, direccion, self.danio))
        return True
