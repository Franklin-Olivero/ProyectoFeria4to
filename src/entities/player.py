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

Estadísticas: velocidad, cadencia, daño, vida y carga máxima salen de
STATS_POR_ROL[self.rol] (src/core/balance.py). Las clases de rol no
guardan números de balance propios.

Disparo sostenido: mientras se mantenga el botón, actualizar_disparo()
dispara un volley cada `intervalo_disparo()` segundos, medido con un
acumulador de tiempo (independiente del framerate). Cada kill propia
activa un buff temporal de cadencia.

Habilidad activa: no tiene cooldown por tiempo. Se carga matando
enemigos (registrar_kill) y se gasta completa al usarla.

Invulnerabilidad: tras un golpe, INVULNERABILIDAD_DURACION segundos sin
perder vida, con el sprite parpadeando.

Apuntado: los ataques salen siempre de `direccion_mirada`. Si el rol
tiene `apunta_con_mouse = True` (Ciudadano, Influencer, Periodista),
solo apuntar_a() la cambia, hacia el mouse; si es False (Candidato),
la cambia manejar_movimiento() con la dirección de caminata.
"""

import pygame

from src.core import assets
from src.core.apuntado import calcular_direccion_apuntado
from src.core.balance import (
    BUFF_KILL_DURACION,
    DANIO_BASE,
    STATS_POR_ROL,
    VELOCIDAD_BASE,
    VIDA_BASE,
    intervalo_disparo,
)
from src.entities.invulnerabilidad import Invulnerabilidad
from src.entities.projectile import Proyectil

ANGULO_ABANICO_GRADOS = 30


class JugadorBase:
    # Identidad del rol (no balance): cada rol sobreescribe estos 4.
    rol = None  # clave en STATS_POR_ROL
    COLOR = assets.COLOR_CIUDADANO
    NOMBRE = "Jugador"
    NOMBRE_HABILIDAD = ""
    # True: apunta con el mouse (apuntar_a). False: apunta hacia donde camina.
    apunta_con_mouse = True

    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, assets.TAMANIO_JUGADOR, assets.TAMANIO_JUGADOR)
        self.rect.center = (x, y)
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)

        self.stats = STATS_POR_ROL[self.rol]
        self.velocidad = VELOCIDAD_BASE * self.stats.velocidad_mult
        self.vida_maxima = VIDA_BASE * self.stats.vida_mult
        self.vida = self.vida_maxima
        self.invulnerabilidad = Invulnerabilidad()
        self.danio = DANIO_BASE * self.stats.danio_mult
        self.carga_maxima = self.stats.carga_maxima
        # Dirección hacia la que "mira" el jugador: de aquí salen los
        # ataques y la habilidad. La actualiza apuntar_a() (mouse) o
        # manejar_movimiento() según `apunta_con_mouse`.
        self.direccion_mirada = pygame.Vector2(0, -1)

        # Puede tener fracciones por la carga compartida del equipo.
        self.carga_habilidad = 0.0

        # Segundos que faltan para el próximo volley (<= 0: listo).
        self.tiempo_para_disparo = 0.0
        self.tiempo_buff_kill = 0.0

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
            if not self.apunta_con_mouse:
                self.direccion_mirada = direccion
            self.posicion += direccion * self.velocidad * dt
            self.rect.center = (round(self.posicion.x), round(self.posicion.y))
            self.rect.clamp_ip(limites)
            self.posicion.update(self.rect.center)

    def apuntar_a(self, punto_mouse):
        """Orienta `direccion_mirada` hacia `punto_mouse` (coordenadas del
        mundo). No hace nada si el rol no apunta con el mouse."""
        if not self.apunta_con_mouse:
            return
        previa = (self.direccion_mirada.x, self.direccion_mirada.y)
        nueva = calcular_direccion_apuntado(self.rect.center, punto_mouse, previa)
        self.direccion_mirada = pygame.Vector2(nueva)

    # ------------------------------------------------------------------
    # Disparo sostenido con cooldown
    # ------------------------------------------------------------------

    @property
    def buff_kill_activo(self):
        return self.tiempo_buff_kill > 0

    def intervalo_disparo(self):
        """Segundos entre volleys ahora mismo (1 / cadencia efectiva)."""
        return intervalo_disparo(self.stats.cadencia, self.buff_kill_activo)

    def actualizar_disparo(self, dt, disparando):
        """Avanza el cooldown y, si `disparando`, dispara los volleys que
        correspondan. Retorna la lista de proyectiles nuevos.

        El acumulador `tiempo_para_disparo` baja con dt y sube un
        intervalo por cada volley, así que la cadencia real es la misma
        a 30 o a 144 FPS (en un frame largo pueden salir 2 volleys).
        Sin disparar no se "ahorran" volleys: el acumulador no baja de 0.
        """
        self.tiempo_buff_kill = max(0.0, self.tiempo_buff_kill - dt)
        self.tiempo_para_disparo -= dt
        nuevos = []
        if disparando:
            while self.tiempo_para_disparo <= 0:
                nuevos.extend(self.ataque_basico())
                self.tiempo_para_disparo += self.intervalo_disparo()
        else:
            self.tiempo_para_disparo = max(self.tiempo_para_disparo, 0.0)
        return nuevos

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
        """Kill propia: 1 kill de carga y (re)inicia el buff de cadencia."""
        self.sumar_carga(1)
        self.tiempo_buff_kill = BUFF_KILL_DURACION

    def sumar_carga(self, cantidad):
        """Suma `cantidad` de kills (puede ser fracción) sin pasar del máximo."""
        self.carga_habilidad = min(self.carga_habilidad + cantidad, self.carga_maxima)

    def puede_usar_habilidad(self):
        return self.carga_habilidad >= self.carga_maxima

    def _gastar_carga(self):
        """Helper para usar_habilidad(): si la carga está completa la
        resetea a 0 y retorna True; si no, no toca nada y retorna False."""
        if not self.puede_usar_habilidad():
            return False
        self.carga_habilidad = 0.0
        return True

    def recibir_dano(self, danio, inicia_invulnerabilidad=True):
        """Resta vida salvo durante la invulnerabilidad (ver
        src/entities/invulnerabilidad.py). Los charcos pasan
        inicia_invulnerabilidad=False: respetan la ventana pero no la abren."""
        self.vida = self.invulnerabilidad.aplicar_golpe(
            self.vida, danio, inicia=inicia_invulnerabilidad
        )

    def actualizar_invulnerabilidad(self, dt):
        self.invulnerabilidad.actualizar(dt)

    def dibujar(self, pantalla):
        # Parpadeo durante la invulnerabilidad.
        if self.invulnerabilidad.visible:
            pygame.draw.rect(pantalla, self.COLOR, self.rect)


class Ciudadano(JugadorBase):
    """Ataque: abanico frontal de 3 proyectiles.
    Habilidad: Burbuja Comunitaria. Por ahora solo activa un flag con
    duración y radio; las colisiones del domo se conectan más adelante.
    """

    rol = "ciudadano"
    COLOR = assets.COLOR_CIUDADANO
    NOMBRE = "Ciudadano"
    NOMBRE_HABILIDAD = "Burbuja Comunitaria"

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
                    danio=self.danio,
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
