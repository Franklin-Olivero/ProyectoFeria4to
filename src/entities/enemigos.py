"""Los tres tipos de enemigo: Perseguidor, Tirador y Curandero.

Cada uno hereda de Enemigo (src/entities/enemy.py), así reutiliza vida,
empuje, escudo, agro_permanente, aggro forzado, la rama de congelado de
la gracia de entrada y la carga de habilidad por kill (que la da Main.py
a cualquier enemigo que muere). Solo cambia su behavior tree, armado con
las piezas de src/ai/behavior_tree.py y los nodos de
src/ai/nodos_combate.py:

    Perseguidor
    Selector
    ├── Sequence: ¿congelado? -> quieto
    ├── Sequence: (¿aggro forzado? | ¿detectado?) -> perseguir -> golpear por contacto
    └── quieto

    Tirador
    Selector
    ├── Sequence: ¿congelado? -> quieto
    ├── Sequence: (¿aggro forzado? | ¿detectado?) -> MantenerDistancia -> DispararApuntado
    └── quieto

    Curandero
    Selector
    ├── Sequence: ¿congelado? -> quieto
    ├── Sequence: ¿en pánico? -> perseguir           (6 s siendo el único vivo)
    ├── Sequence: (¿aggro forzado? | ¿detectado?) -> CurarAliado
    │             -> Selector( Sequence(DistanciaMenorQue(200) -> Huir) | ponerse detrás )
    └── quieto

Con agro_permanente (por defecto) "¿detectado?" siempre tiene éxito:
cada tipo hace lo suyo a cualquier distancia. Los números salen de
balance.py y los colores/tamaños de assets.py.
"""

import pygame

from src.ai.behavior_tree import EXITO, FALLO, Action, Selector, Sequence
from src.ai.nodos_combate import (
    CurarAliado,
    DispararApuntado,
    DistanciaMenorQue,
    Huir,
    MantenerDistancia,
    distancia,
    direccion,
    punto_detras,
)
from src.core import assets
from src.core.balance import (
    CADENCIA_TIRADOR_S,
    COOLDOWN_CONTACTO_PERSEGUIDOR,
    DANIO_CONTACTO_PERSEGUIDOR,
    DANIO_PROYECTIL_TIRADOR,
    DISTANCIA_HUIDA_CURANDERO,
    DURACION_EFECTO_CURA_S,
    FACTOR_ORBITA_TIRADOR,
    FRACCION_CURA,
    INTERVALO_CURA_S,
    MAX_CURAS_POR_ALIADO,
    PANICO_CURANDERO_S,
    RADIO_CURA,
    RANGO_PREFERIDO_TIRADOR,
    SEPARACION_DETRAS_CURANDERO,
    TELEGRAFIA_TIRADOR_S,
    TOLERANCIA_RANGO_TIRADOR,
    VELOCIDAD_PROYECTIL_TIRADOR,
)
from src.entities.enemy import Enemigo
from src.entities.projectile import Proyectil
from src.entities.tipos_enemigo import CONFIG_TIPO, TipoEnemigo

# Distancia (px) a la que el curandero considera que ya llegó a su escondite.
LLEGADA_ESCONDITE = 8


class EnemigoTipado(Enemigo):
    """Base común: stats del tipo (vida, velocidad, tamaño) y helpers del árbol."""

    def __init__(self, x, y, velocidad_base=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
        stats = CONFIG_TIPO[self.tipo]
        # Velocidad "normal" del tramo (sin el multiplicador del tipo).
        self.velocidad_base = velocidad_base
        super().__init__(
            x, y, velocidad_base * stats.velocidad_mult, agro_permanente,
            vida=stats.vida, tamanio=assets.TAMANIO_ENEMIGO_TIPO[self.tipo.value],
        )

    def _activo(self):
        """Selector "¿aggro forzado? o ¿jugador detectado?"."""
        return Selector([Action(self._aggro_forzado), Action(self._jugador_detectado)])

    def _marcar(self, *ruta):
        """Acción que solo registra la rama activa (globo de la tecla Tab)."""
        def marcar():
            self.nodo_activo = ruta
            return EXITO
        return Action(marcar)


class Perseguidor(EnemigoTipado):
    tipo = TipoEnemigo.PERSEGUIDOR

    def __init__(self, x, y, velocidad_base=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
        self.cooldown_contacto = 0.0
        super().__init__(x, y, velocidad_base, agro_permanente)

    def _construir_arbol(self):
        return Selector([
            self._rama_congelado(),
            Sequence([self._activo(), Action(self._perseguir_objetivo), Action(self._golpear_por_contacto)]),
            Action(self._quedarse_quieto),
        ])

    def _golpear_por_contacto(self):
        """Si toca a su objetivo y no está en cooldown, le resta vida (la
        invulnerabilidad del jugador se respeta en recibir_dano). Siempre EXITO."""
        self.cooldown_contacto = max(0.0, self.cooldown_contacto - self._dt)
        objetivo = self._objetivo()
        if self.cooldown_contacto == 0 and self.rect.colliderect(objetivo.rect):
            objetivo.recibir_dano(DANIO_CONTACTO_PERSEGUIDOR)
            self.cooldown_contacto = COOLDOWN_CONTACTO_PERSEGUIDOR
            self.nodo_activo = ("Selector", "Sequence", "Golpe por contacto")
        return EXITO


class Tirador(EnemigoTipado):
    tipo = TipoEnemigo.TIRADOR

    def __init__(self, x, y, velocidad_base=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
        self.recarga_disparo = 0.0  # s hasta empezar la próxima telegrafía
        self.telegrafia = 0.0  # s que faltan para disparar (> 0: resaltado)
        super().__init__(x, y, velocidad_base, agro_permanente)

    def _construir_arbol(self):
        return Selector([
            self._rama_congelado(),
            Sequence([
                self._activo(),
                self._marcar("Selector", "Sequence", "Mantener distancia"),
                MantenerDistancia(self, RANGO_PREFERIDO_TIRADOR, TOLERANCIA_RANGO_TIRADOR, FACTOR_ORBITA_TIRADOR),
                DispararApuntado(self, CADENCIA_TIRADOR_S, TELEGRAFIA_TIRADOR_S),
            ]),
            Action(self._quedarse_quieto),
        ])

    def disparar_hacia_objetivo(self):
        dx, dy = direccion(self.xy, self.objetivo_xy)
        if (dx, dy) == (0.0, 0.0):
            return
        self._proyectiles_salida.append(Proyectil(
            posicion=self.rect.center, direccion=pygame.Vector2(dx, dy),
            velocidad=VELOCIDAD_PROYECTIL_TIRADOR, danio=DANIO_PROYECTIL_TIRADOR,
            color=assets.COLOR_PROYECTIL_TIRADOR, tamanio=assets.TAMANIO_PROYECTIL_TIRADOR,
        ))
        self.nodo_activo = ("Selector", "Sequence", "Disparo apuntado")


class Curandero(EnemigoTipado):
    tipo = TipoEnemigo.CURANDERO

    def __init__(self, x, y, velocidad_base=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
        self.cooldown_cura = INTERVALO_CURA_S
        self.efecto_cura = None  # aliado curado hace poco (rayo verde)
        self.tiempo_efecto_cura = 0.0
        self.tiempo_solo = 0.0  # s seguidos siendo el único enemigo vivo
        self.en_panico = False
        super().__init__(x, y, velocidad_base, agro_permanente)

    def _construir_arbol(self):
        return Selector([
            self._rama_congelado(),
            Sequence([
                Action(self._revisar_panico),
                self._marcar("Selector", "Sequence", "Pánico"),
                Action(self._perseguir_objetivo),
            ]),
            Sequence([
                self._activo(),
                CurarAliado(self, INTERVALO_CURA_S, FRACCION_CURA, RADIO_CURA, MAX_CURAS_POR_ALIADO),
                Selector([
                    Sequence([
                        DistanciaMenorQue(self, DISTANCIA_HUIDA_CURANDERO),
                        self._marcar("Selector", "Sequence", "Huir"),
                        Huir(self),
                    ]),
                    Action(self._ponerse_detras),
                ]),
            ]),
            Action(self._quedarse_quieto),
        ])

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        self.tiempo_efecto_cura = max(0.0, self.tiempo_efecto_cura - dt)
        if self.tiempo_efecto_cura == 0:
            self.efecto_cura = None
        super().actualizar(dt, jugador, proyectiles_enemigos)

    def _otros_vivos(self):
        """Los demás enemigos vivos del cuarto (nada que no sea `curable`,
        como el jefe, cuenta como aliado para esconderse o para el pánico)."""
        return [aliado for aliado in self.aliados
                if aliado is not self and getattr(aliado, "curable", False) and aliado.vivo]

    def _revisar_panico(self):
        """Condición con memoria: cuenta cuánto lleva siendo el único vivo;
        a los PANICO_CURANDERO_S entra en pánico para siempre (persigue a
        velocidad normal y deja de curar), así nunca bloquea el cuarto."""
        if not self.en_panico:
            self.tiempo_solo = 0.0 if self._otros_vivos() else self.tiempo_solo + self._dt
            if self.tiempo_solo >= PANICO_CURANDERO_S:
                self.en_panico = True
                self.velocidad = self.velocidad_base
        return EXITO if self.en_panico else FALLO

    def _ponerse_detras(self):
        """Va al punto detrás de sus aliados (lejos del jugador); solo, huye."""
        punto = punto_detras([aliado.xy for aliado in self._otros_vivos()], self.objetivo_xy,
                             SEPARACION_DETRAS_CURANDERO)
        if punto is None:
            dx, dy = direccion(self.objetivo_xy, self.xy)
            self.mover(dx, dy)
            self.nodo_activo = ("Selector", "Sequence", "Huir (solo)")
            return EXITO
        if distancia(self.xy, punto) > LLEGADA_ESCONDITE:
            dx, dy = direccion(self.xy, punto)
            self.mover(dx, dy)
        self.nodo_activo = ("Selector", "Sequence", "Detrás de aliados")
        return EXITO

    def al_curar(self, aliado):
        self.efecto_cura = aliado
        self.tiempo_efecto_cura = DURACION_EFECTO_CURA_S


CLASE_POR_TIPO = {
    TipoEnemigo.PERSEGUIDOR: Perseguidor,
    TipoEnemigo.TIRADOR: Tirador,
    TipoEnemigo.CURANDERO: Curandero,
}


def crear_enemigo(tipo, x, y, velocidad_base=assets.VELOCIDAD_ENEMIGO, agro_permanente=True):
    """Fábrica: el enemigo del `tipo` dado en (x, y)."""
    return CLASE_POR_TIPO[tipo](x, y, velocidad_base, agro_permanente)

