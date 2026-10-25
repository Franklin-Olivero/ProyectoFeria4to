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

Gracia de entrada: mientras `armas_bloqueadas` sea True (Main.py lo
pone durante el segundo de gracia al entrar a un cuarto) el jugador
puede moverse pero no dispara ni usa la habilidad.

Apuntado: los ataques salen siempre de `direccion_mirada`. Si el rol
tiene `apunta_con_mouse = True` (Ciudadano, Influencer, Periodista),
solo apuntar_a() la cambia, hacia el mouse o el stick derecho; si es
False (Candidato), la cambia mover() con la dirección de caminata.

Input: manejar_input() aplica un InputJugador (src/core/entrada.py), así
el mismo código sirve para el teclado+mouse del J1 y el control del J2.

Dash (src/entities/dash.py): desplazamiento corto en la dirección de
movimiento (o de mirada si está quieto), invulnerable, sin disparar.
"""

import math
from collections import deque

import pygame

from src.core import assets
from src.core.apuntado import calcular_direccion_apuntado
from src.core.balance import (
    ACELERACION_MOVIMIENTO,
    BUFF_KILL_DURACION,
    DANIO_BASE,
    FRENADO_MOVIMIENTO,
    VELOCIDAD_MINIMA_MOVIMIENTO,
    STATS_POR_ROL,
    VELOCIDAD_BASE,
    VIDA_BASE,
    intervalo_disparo,
)
from src.core.entrada import DISTANCIA_PUNTO_STICK, direccion_teclado
from src.dungeon.ciudad_mapa import mover_con_colision
from src.entities.dash import Dash
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
        # Dirección de caminata del último frame ((0, 0) quieto): el dash sale hacia acá.
        self.direccion_movimiento = pygame.Vector2(0, 0)
        # Velocidad real (px/s): sigue a la pedida con inercia (ver mover).
        self.velocidad_actual = pygame.Vector2(0, 0)

        # Puede tener fracciones por la carga compartida del equipo.
        self.carga_habilidad = 0.0

        # Segundos que faltan para el próximo volley (<= 0: listo).
        self.tiempo_para_disparo = 0.0
        self.tiempo_buff_kill = 0.0
        # Gracia de entrada al cuarto: sin disparo ni habilidad.
        self.armas_bloqueadas = False

        self.dash = Dash()
        # Posiciones recientes durante el dash: ahí se dibujan las imágenes fantasma.
        self.rastro_dash = deque(maxlen=assets.DASH_AFTERIMAGES)

    @property
    def vivo(self):
        return self.vida > 0

    def manejar_input(self, entrada, dt, limites):
        """Aplica un InputJugador: mueve, apunta y arranca el dash.

        Disparo y habilidad no van aquí porque producen proyectiles (ver
        actualizar_disparo e intentar_habilidad)."""
        self.mover(entrada.movimiento, dt, limites)
        if entrada.punto_apuntado is not None:
            self.apuntar_a(entrada.punto_apuntado)
        elif entrada.direccion_apuntado is not None:
            # El stick da una dirección: se apunta a un punto lejano en ella.
            dx, dy = entrada.direccion_apuntado
            self.apuntar_a((self.rect.centerx + dx * DISTANCIA_PUNTO_STICK,
                            self.rect.centery + dy * DISTANCIA_PUNTO_STICK))
        if entrada.dash:
            self.iniciar_dash()

    def manejar_movimiento(self, teclas, dt, limites):
        """Mueve al jugador según WASD/flechas (ver mover)."""
        self.mover(direccion_teclado(teclas), dt, limites)

    def mover(self, direccion, dt, limites):
        """Un frame de movimiento hacia `direccion` (x, y) y clamp a `limites`.

        Inercia: la velocidad real no salta a la pedida, se le acerca
        exponencialmente, v(t) = pedida + (v0 - pedida) * e^(-k*t), con
        k = ACELERACION_MOVIMIENTO al caminar y FRENADO_MOVIMIENTO al
        soltar. El avance del frame es la integral exacta de v(t) en dt,
        así el recorrido es el mismo a 30 o a 144 FPS. O(1).

        Durante el dash se ignora el input: se avanza en la dirección
        fijada al iniciarlo, DASH_VELOCIDAD_MULT veces más rápido (y sin
        atravesar muros, por el mismo clamp). Al terminar, esa velocidad
        se va frenando con la misma inercia, en vez de cortarse en seco.
        """
        direccion = pygame.Vector2(direccion)
        if direccion.length_squared() > 0:
            direccion = direccion.normalize()
        self.direccion_movimiento = pygame.Vector2(direccion)

        if self.dash.activo:
            self.rastro_dash.append(self.rect.center)
            self.velocidad_actual = (pygame.Vector2(self.dash.direccion)
                                     * self.velocidad * self.dash.velocidad_multiplicador)
            desplazamiento = self.velocidad_actual * dt
        else:
            if direccion.length_squared() > 0 and not self.apunta_con_mouse:
                self.direccion_mirada = direccion
            pedida = direccion * self.velocidad
            tasa = ACELERACION_MOVIMIENTO if direccion.length_squared() > 0 else FRENADO_MOVIMIENTO
            restante = math.exp(-tasa * dt)  # fracción de la diferencia que queda tras dt
            diferencia = self.velocidad_actual - pedida
            # Integral de v(t) entre 0 y dt: pedida*dt + diferencia*(1 - e^(-k*dt))/k.
            desplazamiento = pedida * dt + diferencia * ((1 - restante) / tasa)
            self.velocidad_actual = pedida + diferencia * restante
            if pedida.length_squared() == 0 and self.velocidad_actual.length() < VELOCIDAD_MINIMA_MOVIMIENTO:
                self.velocidad_actual.update(0, 0)

        if desplazamiento.length_squared() == 0:
            return
        self.posicion += desplazamiento
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))
        antes = self.rect.center
        self.rect.clamp_ip(limites)
        # Contra un muro se pierde la velocidad en ese eje (no queda "empujando").
        if self.rect.centerx != antes[0]:
            self.velocidad_actual.x = 0
        if self.rect.centery != antes[1]:
            self.velocidad_actual.y = 0
        if self.rect.center != antes:
            self.posicion.update(self.rect.center)

    def detener(self):
        """Sin inercia pendiente (al aparecer en un cuarto o al curarse)."""
        self.velocidad_actual.update(0, 0)

    def iniciar_dash(self):
        """Dash hacia donde camina; quieto, hacia donde mira. True si arrancó."""
        direccion = self.direccion_movimiento
        if direccion.length_squared() == 0:
            direccion = self.direccion_mirada
        return self.dash.iniciar((direccion.x, direccion.y))

    def actualizar_dash(self, dt):
        self.dash.actualizar(dt)
        if not self.dash.activo:
            self.rastro_dash.clear()

    def caminar_en_ciudad(self, teclas, dt, es_solida):
        """Movimiento en Ciudad Nova: misma velocidad del rol, pero contra
        las casillas sólidas del mapa (mover_con_colision, por ejes
        separados) en vez de contra los muros de un cuarto."""
        direccion = pygame.Vector2(direccion_teclado(teclas))
        if direccion.length_squared() == 0:
            return
        delta = direccion * self.velocidad * dt
        x, y = mover_con_colision(
            (self.posicion.x, self.posicion.y), (delta.x, delta.y), self.rect.size, es_solida
        )
        self.colocar_en((x, y))

    def colocar_en(self, posicion):
        """Pone el centro del jugador en `posicion` (px), sin inercia pendiente."""
        self.posicion.update(posicion)
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))
        self.detener()

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
        Durante el dash no se dispara y el acumulador queda en pausa.
        """
        self.tiempo_buff_kill = max(0.0, self.tiempo_buff_kill - dt)
        if not self.dash.puede_disparar:
            return []
        self.tiempo_para_disparo -= dt
        if self.armas_bloqueadas:
            disparando = False
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

    def intentar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Lo que llama el loop al apretar la tecla/botón de habilidad:
        durante el dash no se puede; si no, usar_habilidad() decide por la carga."""
        if not self.dash.puede_disparar:
            return False
        return self.usar_habilidad(enemigos, proyectiles_salida)

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

    def habilidad_cargada(self):
        """La barra está llena (aunque las armas estén bloqueadas)."""
        return self.carga_habilidad >= self.carga_maxima

    def puede_usar_habilidad(self):
        return self.habilidad_cargada() and not self.armas_bloqueadas

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
        inicia_invulnerabilidad=False: respetan la ventana pero no la abren.
        Durante el dash (DASH_INVULNERABLE) ningún golpe entra ni abre la
        ventana; si ya estaba abierta, sigue corriendo igual."""
        if self.dash.invulnerable:
            return
        self.vida = self.invulnerabilidad.aplicar_golpe(
            self.vida, danio, inicia=inicia_invulnerabilidad
        )

    def actualizar_invulnerabilidad(self, dt):
        self.invulnerabilidad.actualizar(dt)

    def dibujar(self, pantalla):
        # Parpadeo durante la invulnerabilidad. El sprite (pixel art, ver
        # src/ui/sprites.py) se apoya en el borde inferior del rect de
        # colisión y sobresale un poco por arriba, como en un top-down.
        from src.ui import sprites

        imagen = sprites.sprite_jugador(self.COLOR)
        # Imágenes fantasma del dash: la más nueva (última del rastro) es la más opaca.
        for alfa, centro in zip(assets.DASH_AFTERIMAGE_ALFA, reversed(self.rastro_dash)):
            fantasma = imagen.copy()
            fantasma.set_alpha(alfa)
            pantalla.blit(fantasma, fantasma.get_rect(midbottom=(centro[0], centro[1] + self.rect.height // 2 + 4)))
        if self.invulnerabilidad.visible:
            pantalla.blit(imagen, imagen.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 4)))


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
            diametro = self.radio_burbuja * 2
            capa = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
            pygame.draw.circle(capa, (*assets.COLOR_BURBUJA, 40), (self.radio_burbuja,) * 2, self.radio_burbuja)
            pantalla.blit(capa, capa.get_rect(center=self.rect.center))
            pygame.draw.circle(
                pantalla,
                assets.COLOR_BURBUJA,
                self.rect.center,
                self.radio_burbuja,
                assets.GROSOR_BURBUJA,
            )
