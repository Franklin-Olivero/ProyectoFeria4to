"""Enemigo controlado por un árbol de comportamiento (ver
src/ai/behavior_tree.py).

Cada frame, `actualizar` guarda el contexto del frame (jugador, dt,
lista de salida de proyectiles) y hace tick() al árbol raíz, que es:

    Selector
    ├── Sequence: "¿aggro forzado?" -> "perseguir" -> "disparar"
    ├── Sequence: "¿jugador detectado?" -> "perseguir" -> "disparar"
    └── Action: "quedarse quieto" (siempre EXITO)

Es decir: si alguien le forzó el aggro (Live Stream Viral del
Influencer), persigue y dispara a ese objetivo sin importar la
distancia; si no, y el jugador está detectado, lo persigue y le
dispara; si no, se queda quieto.

Regla de diseño: agresividad absoluta. Con `agro_permanente` (True por
defecto, en los cuartos normales y en los súbditos del jefe) el nodo de
detección siempre tiene éxito: el enemigo persigue y dispara sin
importar la distancia y nunca llega a "quedarse quieto". Con
agro_permanente = False vuelve a usar RANGO_DISPARO_ENEMIGO (se
conserva para poder desactivarlo en un enemigo concreto).
"""

import pygame

from src.ai.behavior_tree import EXITO, FALLO, Action, Selector, Sequence
from src.core import assets
from src.entities.projectile import Proyectil


class Enemigo:
    def __init__(self, x, y, velocidad=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
        self.rect = pygame.Rect(0, 0, assets.TAMANIO_ENEMIGO, assets.TAMANIO_ENEMIGO)
        self.rect.center = (x, y)
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)
        self.vida = assets.VIDA_ENEMIGO
        # Píxeles por segundo; el cuarto la ajusta según la toxicidad de
        # la zona (ver src/dungeon/clasificador_toxicidad.py).
        self.velocidad = velocidad
        self.cooldown_disparo = 0.0
        # Escudo de anonimato: mientras esté activo el enemigo ignora
        # el daño. Lo quita el Fact-Checking del Periodista. Ningún
        # enemigo lo trae activo todavía.
        self.escudo_anonimato = False
        # Aggro forzado (Live Stream Viral): objetivo con `.rect` que el
        # árbol persigue mientras `tiempo_objetivo_forzado` sea > 0.
        self.objetivo_forzado = None
        self.tiempo_objetivo_forzado = 0.0
        # True: detecta al jugador a cualquier distancia (agresividad absoluta).
        self.agro_permanente = agro_permanente
        # Ruta de nodos que ejecutó el árbol en el último tick, solo para
        # mostrarla en pantalla (tecla Tab). Ej.: ("Selector", "Sequence",
        # "Perseguir"). No influye en la IA.
        self.nodo_activo = ()
        # Alterna el color del sprite para que no todos se vean iguales.
        self.variante = (round(x) + round(y)) // 40 % 2

        # Contexto del frame actual; lo llena `actualizar` antes del
        # tick para que las acciones del árbol (sin argumentos, por
        # diseño de Action) puedan leerlo.
        self._jugador = None
        self._dt = 0.0
        self._proyectiles_salida = None

        self.arbol = Selector(
            [
                Sequence(
                    [
                        Action(self._aggro_forzado),
                        Action(self._perseguir_objetivo),
                        Action(self._disparar_a_objetivo),
                    ]
                ),
                Sequence(
                    [
                        Action(self._jugador_detectado),
                        Action(self._perseguir_objetivo),
                        Action(self._disparar_a_objetivo),
                    ]
                ),
                Action(self._quedarse_quieto),
            ]
        )

    @property
    def vivo(self):
        return self.vida > 0

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        """Ejecuta un tick del árbol de comportamiento para este frame."""
        self._jugador = jugador
        self._dt = dt
        self._proyectiles_salida = proyectiles_enemigos

        if self.cooldown_disparo > 0:
            self.cooldown_disparo -= dt

        if self.tiempo_objetivo_forzado > 0:
            self.tiempo_objetivo_forzado -= dt
            if self.tiempo_objetivo_forzado <= 0:
                self.objetivo_forzado = None

        self.arbol.tick()

    def forzar_objetivo(self, objetivo, duracion):
        """Fija el aggro hacia `objetivo` (cualquier cosa con `.rect`)
        durante `duracion` segundos, ignorando el rango de disparo."""
        self.objetivo_forzado = objetivo
        self.tiempo_objetivo_forzado = duracion

    def _objetivo(self):
        """A quién persigue/dispara este frame: el objetivo forzado si
        está activo, si no el jugador."""
        if self.objetivo_forzado is not None:
            return self.objetivo_forzado
        return self._jugador

    def _aggro_forzado(self):
        return EXITO if self.objetivo_forzado is not None else FALLO

    def _jugador_detectado(self):
        """Con agro_permanente, siempre; si no, solo dentro del rango."""
        if self.agro_permanente:
            return EXITO
        distancia = pygame.Vector2(self.rect.center).distance_to(self._jugador.rect.center)
        return EXITO if distancia <= assets.RANGO_DISPARO_ENEMIGO else FALLO

    def _perseguir_objetivo(self):
        self.nodo_activo = ("Selector", "Sequence", "Perseguir")
        direccion = pygame.Vector2(self._objetivo().rect.center) - self.posicion
        if direccion.length_squared() > 0:
            direccion = direccion.normalize()
            self.posicion += direccion * self.velocidad * self._dt
            self.rect.center = (round(self.posicion.x), round(self.posicion.y))
        return EXITO

    def _disparar_a_objetivo(self):
        # Este nodo siempre retorna EXITO, incluso en cooldown: el
        # cooldown solo bloquea la creación del proyectil, no el
        # resultado del nodo. Si retornara FALLO durante el cooldown,
        # la Sequence completa fallaría y el Selector caería a
        # "quedarse quieto", interrumpiendo la persecución cada vez que
        # el enemigo no puede disparar. Así, perseguir nunca se
        # interrumpe por el cooldown de disparo.
        if self.cooldown_disparo <= 0:
            direccion = pygame.Vector2(self._objetivo().rect.center) - pygame.Vector2(
                self.rect.center
            )
            if direccion.length_squared() > 0:
                proyectil = Proyectil(
                    posicion=self.rect.center,
                    direccion=direccion,
                    velocidad=assets.VELOCIDAD_PROYECTIL,
                    danio=assets.DANIO_PROYECTIL_ENEMIGO,
                    color=assets.COLOR_PROYECTIL_ENEMIGO,
                )
                self._proyectiles_salida.append(proyectil)
                self.cooldown_disparo = assets.COOLDOWN_DISPARO_ENEMIGO
                self.nodo_activo = ("Selector", "Sequence", "Disparar")
        return EXITO

    def _quedarse_quieto(self):
        self.nodo_activo = ("Selector", "Quedarse quieto")
        return EXITO

    def recibir_dano(self, danio):
        if self.escudo_anonimato:
            return
        self.vida -= danio

    def empujar(self, impulso):
        """Desplaza al enemigo `impulso` (Vector2, en píxeles) de golpe."""
        self.posicion += impulso
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))

    def mantener_dentro(self, limites):
        """Evita que un empujón lo saque del cuarto."""
        self.rect.clamp_ip(limites)
        self.posicion.update(self.rect.center)

    def dibujar(self, pantalla):
        from src.ui import sprites

        paleta = sprites.PALETA_ENEMIGO if self.variante == 0 else sprites.PALETA_ENEMIGO_MORADO
        imagen = sprites.sprite(sprites.ENEMIGO, paleta)
        pantalla.blit(imagen, imagen.get_rect(center=self.rect.center))
        if self.escudo_anonimato:
            pygame.draw.rect(pantalla, assets.COLOR_ESCUDO_JEFE, self.rect.inflate(8, 8), 2, border_radius=4)
