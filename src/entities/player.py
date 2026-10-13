"""Jugadores: clase base común y el rol Ciudadano.

`JugadorBase` concentra todo lo que comparten los 4 roles: movimiento,
vida, dirección de mirada, carga de habilidad por kills y dibujo
básico. Cada rol hereda de ella y solo sobreescribe:

    ataque_basico()      -> lista de proyectiles/efectos nuevos
    usar_habilidad(...)  -> True si se usó, False si faltaba carga

Gracias a esa interfaz común, el loop principal (Main.py) trata a
cualquier rol igual: agrega lo que devuelve ataque_basico() a sus
proyectiles y resuelve colisiones con `proyectil.al_impactar(enemigo)`,
que cada tipo de proyectil define a su manera.

Habilidad activa: no tiene cooldown por tiempo. Se carga matando
enemigos (registrar_kill) y se gasta completa al usarla.
"""

import pygame

from src.core import assets
from src.entities.projectile import Proyectil

ANGULO_ABANICO_GRADOS = 30


class JugadorBase:
    CARGA_MAXIMA_HABILIDAD = 5  # kills necesarios para usar la habilidad
    COLOR = assets.COLOR_CIUDADANO  # cada rol lo sobreescribe
    NOMBRE = "Jugador"

    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
        self.rect.center = (x, y)
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)
        self.vida = assets.VIDA_JUGADOR
        # Dirección hacia la que "mira" el jugador: se usa para apuntar
        # los ataques. El proyecto es 100% teclado (sin mouse en ningún
        # otro sistema), así que se define como la última dirección de
        # movimiento en vez de apuntar al mouse, para mantener
        # consistencia con el resto de la mecánica.
        self.direccion_mirada = pygame.Vector2(0, -1)

        self.carga_habilidad = 0

    @property
    def vivo(self):
        return self.vida > 0

    def manejar_movimiento(self, teclas, dt, limites):
        """Mueve al jugador según WASD/flechas y lo mantiene dentro de `limites`."""
        direccion = pygame.Vector2(0, 0)
        if teclas[pygame.K_w] or teclas[pygame.K_UP]:
            direccion.y -= 1
        if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
            direccion.y += 1
        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
            direccion.x -= 1
        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
            direccion.x += 1

        if direccion.length_squared() > 0:
            direccion = direccion.normalize()
            self.direccion_mirada = direccion
            self.posicion += direccion * assets.VELOCIDAD_JUGADOR * dt
            self.rect.center = (round(self.posicion.x), round(self.posicion.y))
            self.rect.clamp_ip(limites)
            self.posicion.update(self.rect.center)

    # ------------------------------------------------------------------
    # Interfaz que cada rol sobreescribe
    # ------------------------------------------------------------------

    def ataque_basico(self):
        """Retorna la lista de proyectiles/efectos que crea el ataque.

        Quien llama es responsable de agregarlos a los proyectiles activos.
        """
        raise NotImplementedError

    def usar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Activa la habilidad del rol si la carga está completa.

        `enemigos` son los enemigos vivos del cuarto (para habilidades
        que los afectan directamente) y `proyectiles_salida` la lista
        donde se agregan los proyectiles que la habilidad dispare.
        Retorna True si se usó, False si faltaba carga.
        """
        raise NotImplementedError

    def actualizar_habilidad(self, dt):
        """Avanza los efectos con duración de la habilidad (si los hay)."""

    # ------------------------------------------------------------------
    # Carga de habilidad por kills
    # ------------------------------------------------------------------

    def registrar_kill(self):
        """Suma 1 a la carga de la habilidad, sin pasar del máximo."""
        self.carga_habilidad = min(self.carga_habilidad + 1, self.CARGA_MAXIMA_HABILIDAD)

    def puede_usar_habilidad(self):
        return self.carga_habilidad >= self.CARGA_MAXIMA_HABILIDAD

    def _gastar_carga(self):
        """Helper para usar_habilidad(): si la carga está completa la
        resetea a 0 y retorna True; si no, no toca nada y retorna False."""
        if not self.puede_usar_habilidad():
            return False
        self.carga_habilidad = 0
        return True

    def recibir_dano(self, danio):
        self.vida -= danio

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, self.COLOR, self.rect)


class Ciudadano(JugadorBase):
    """Ataque: abanico frontal de 3 proyectiles.
    Habilidad: Burbuja Comunitaria. Por ahora solo activa un flag con
    duración y radio; las colisiones del domo se conectan más adelante.
    """

    COLOR = assets.COLOR_CIUDADANO
    NOMBRE = "Ciudadano"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.burbuja_activa = False
        self.tiempo_burbuja = 0.0
        self.radio_burbuja = assets.RADIO_BURBUJA

    def ataque_basico(self):
        """Dispara 3 proyectiles en abanico (~30° entre ellos) en la
        dirección hacia la que mira el jugador."""
        angulos = [-ANGULO_ABANICO_GRADOS, 0, ANGULO_ABANICO_GRADOS]
        proyectiles = []
        for angulo in angulos:
            direccion = self.direccion_mirada.rotate(angulo)
            proyectiles.append(
                Proyectil(
                    posicion=self.rect.center,
                    direccion=direccion,
                    velocidad=assets.VELOCIDAD_PROYECTIL,
                    danio=assets.DANIO_PROYECTIL_JUGADOR,
                    color=assets.COLOR_PROYECTIL_JUGADOR,
                )
            )
        return proyectiles

    def usar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Gasta toda la carga y activa la Burbuja Comunitaria."""
        if not self._gastar_carga():
            return False
        self.burbuja_activa = True
        self.tiempo_burbuja = assets.DURACION_BURBUJA
        return True

    def actualizar_habilidad(self, dt):
        """Descuenta la duración de la burbuja y la apaga al llegar a 0."""
        if not self.burbuja_activa:
            return
        self.tiempo_burbuja -= dt
        if self.tiempo_burbuja <= 0:
            self.tiempo_burbuja = 0.0
            self.burbuja_activa = False

    def dibujar(self, pantalla):
        super().dibujar(pantalla)
        if self.burbuja_activa:
            pygame.draw.circle(
                pantalla,
                assets.COLOR_BURBUJA,
                self.rect.center,
                self.radio_burbuja,
                assets.GROSOR_BURBUJA,
            )
