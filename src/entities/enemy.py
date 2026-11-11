"""Enemigo controlado por un árbol de comportamiento (ver
src/ai/behavior_tree.py).

Cada frame, `actualizar` guarda el contexto del frame (jugador, dt,
lista de salida de proyectiles) y hace tick() al árbol raíz, que es:

    Selector
    ├── Sequence: "¿congelado?" -> "quieto (gracia)"
    ├── Sequence: "¿aggro forzado?" -> "perseguir" -> "disparar"
    ├── Sequence: "¿jugador detectado?" -> "perseguir" -> "disparar"
    └── Action: "quedarse quieto" (siempre EXITO)

La primera rama es la gracia de entrada al cuarto
(src/dungeon/gracia_entrada.py): mientras `congelado` sea True el
enemigo no hace nada más, con prioridad sobre agro_permanente. Después,
si alguien le forzó el aggro (Live Stream Viral del
Influencer), persigue y dispara a ese objetivo sin importar la
distancia; si no, y el jugador está detectado, lo persigue y le
dispara; si no, se queda quieto.

Regla de diseño: agresividad absoluta. Con `agro_permanente` (True por
defecto, en los cuartos normales y en los súbditos del jefe) el nodo de
detección siempre tiene éxito: el enemigo persigue y dispara sin
importar la distancia y nunca llega a "quedarse quieto". Con
agro_permanente = False vuelve a usar RANGO_DISPARO_ENEMIGO (se
conserva para poder desactivarlo en un enemigo concreto).

Esta clase es también la base de los tipos de enemigo
(src/entities/enemigos.py): cada tipo sobreescribe `_construir_arbol`
y reutiliza vida, empuje, escudo, agro, la rama de congelado y la
"interfaz de agente" que piden los nodos de src/ai/nodos_combate.py
(xy, objetivo_xy, dt, mover).
"""

import pygame

from src.ai.behavior_tree import EXITO, FALLO, Action, Selector, Sequence
from src.audio import eventos_sonido
from src.core import assets
from src.entities.projectile import Proyectil


class Enemigo:
    # Tipo (TipoEnemigo) para el sprite y la composición; None = el
    # enemigo genérico original (persigue y dispara).
    tipo = None
    # Un curandero puede curarlo (el jefe no tiene este atributo).
    curable = True

    def __init__(self, x, y, velocidad=assets.VELOCIDAD_ENEMIGO, agro_permanente=True,
                 vida=assets.VIDA_ENEMIGO, tamanio=assets.TAMANIO_ENEMIGO):
        self.rect = pygame.Rect(0, 0, tamanio, tamanio)
        self.rect.center = (x, y)
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)
        self.vida = vida
        self.vida_maxima = vida
        # Veces que un curandero lo curó en este cuarto (tope por aliado).
        self.curaciones_recibidas = 0
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
        # Gracia de entrada: lo pone el cuarto/arena cada frame.
        self.congelado = False
        # Enemigos del mismo cuarto (los curanderos los leen).
        self.aliados = []
        # Grafo de celdas del cuarto (src/dungeon/navegacion_cuarto.py): lo
        # pone el cuarto cada frame. Con él, perseguir rodea las coberturas
        # por el camino más corto (BFS); sin él (None) va en línea recta.
        self.navegacion = None
        # Segundos vividos: solo para animaciones (parpadeo de la gracia).
        self.reloj = 0.0

        # Contexto del frame actual; lo llena `actualizar` antes del
        # tick para que las acciones del árbol (sin argumentos, por
        # diseño de Action) puedan leerlo.
        self._jugador = None
        self._dt = 0.0
        self._proyectiles_salida = None

        self.arbol = self._construir_arbol()

    def _rama_congelado(self):
        """Primera rama de todo árbol de enemigo: la gracia de entrada."""
        return Sequence([Action(self._esta_congelado), Action(self._quieto_congelado)])

    def _construir_arbol(self):
        return Selector(
            [
                self._rama_congelado(),
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

    # ------------------------------------------------------------------
    # Interfaz de agente (la usan los nodos de src/ai/nodos_combate.py)
    # ------------------------------------------------------------------

    @property
    def xy(self):
        return (self.posicion.x, self.posicion.y)

    @property
    def objetivo_xy(self):
        centro = self._objetivo().rect.center
        return (centro[0], centro[1])

    @property
    def dt(self):
        return self._dt

    def rumbo_hacia(self, destino):
        """Dirección unitaria (dx, dy) para llegar a `destino`: con muebles
        en el cuarto, la que da su grafo de celdas (rodea por el camino más
        corto, BFS); sin ellos, la línea recta."""
        if self.navegacion is not None:
            return self.navegacion.direccion(self.xy, destino, max(self.rect.size) / 2 + 1)
        direccion = pygame.Vector2(destino) - self.posicion
        if direccion.length_squared() == 0:
            return (0.0, 0.0)
        direccion = direccion.normalize()
        return (direccion.x, direccion.y)

    def mover(self, dx, dy, factor=1.0):
        """Avanza en la dirección unitaria (dx, dy) a `factor` veces su velocidad."""
        self.posicion += pygame.Vector2(dx, dy) * self.velocidad * factor * self._dt
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        """Ejecuta un tick del árbol de comportamiento para este frame."""
        self._jugador = jugador
        self._dt = dt
        self._proyectiles_salida = proyectiles_enemigos
        self.reloj += dt

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

    def _esta_congelado(self):
        return EXITO if self.congelado else FALLO

    def _quieto_congelado(self):
        self.nodo_activo = ("Selector", "Congelado (gracia)")
        return EXITO

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
        dx, dy = self.rumbo_hacia(self._objetivo().rect.center)
        self.mover(dx, dy)
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
        vivo_antes = self.vivo
        self.vida -= danio
        eventos_sonido.emitir("impacto_enemigo")
        if vivo_antes and not self.vivo:
            tipo = self.tipo.value if self.tipo is not None else "perseguidor"
            eventos_sonido.emitir(f"muerte_{tipo}")

    def empujar(self, impulso):
        """Desplaza al enemigo `impulso` (Vector2, en píxeles) de golpe."""
        self.posicion += impulso
        self.rect.center = (round(self.posicion.x), round(self.posicion.y))

    def mantener_dentro(self, limites):
        """Evita que un empujón lo saque del cuarto."""
        self.rect.clamp_ip(limites)
        self.posicion.update(self.rect.center)

    def dibujar(self, pantalla):
        from src.ui import enemigo_render

        enemigo_render.dibujar_enemigo(pantalla, self)
