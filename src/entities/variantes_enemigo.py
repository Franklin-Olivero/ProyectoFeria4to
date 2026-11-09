"""Variantes de enemigo: un personaje de assets/sprites/enemigos/variantes por
cada una (lógica pura, sin Pygame).

Cada variante pertenece a un TipoEnemigo (su comportamiento: perseguidor,
tirador o curandero) y trae sus propios números (balance.
STATS_VARIANTE_ENEMIGO). `elegir_variantes` reparte las variantes de un
cuarto: dentro de la misma mazmorra siempre prefiere las menos usadas
hasta ahora, así cada cuarto trae caras distintas, y el azar desempata,
así cada mazmorra empieza con otras. El jefe (Flame Golem) no es una
variante: no aparece como enemigo común.
"""

from dataclasses import dataclass

from src.core.balance import (
    DURACION_CUADRO_ATAQUE_S,
    FRACCION_IMPACTO_ATAQUE,
    STATS_VARIANTE_ENEMIGO,
    StatsVariante,
)
from src.entities.tipos_enemigo import TipoEnemigo


@dataclass(frozen=True)
class VarianteEnemigo:
    nombre: str  # nombre exacto de la carpeta del arte (se muestra en el debug)
    tipo: TipoEnemigo
    stats: StatsVariante

    @property
    def duracion_ataque(self):
        """Segundos que dura su animación de ataque."""
        return self.stats.cuadros_ataque * DURACION_CUADRO_ATAQUE_S

    @property
    def tiempo_impacto(self):
        """Segundo de la animación en que cae el golpe o sale el disparo."""
        return self.duracion_ataque * FRACCION_IMPACTO_ATAQUE


VARIANTES = {
    nombre: VarianteEnemigo(nombre, TipoEnemigo(stats.tipo), stats)
    for nombre, stats in STATS_VARIANTE_ENEMIGO.items()
}


def variantes_de(tipo):
    """Variantes con el comportamiento `tipo`, en orden de la tabla."""
    return [v for v in VARIANTES.values() if v.tipo == tipo]


def elegir_variantes(tipos, rng, usos):
    """Una VarianteEnemigo por cada tipo de `tipos` (en el mismo orden).

    `usos` es un dict nombre -> veces elegida en la mazmorra; se actualiza
    aquí. Para cada tipo se toman las menos usadas y `rng` (random.Random)
    desempata. O(t * v), con t los tipos y v las variantes.
    """
    elegidas = []
    for tipo in tipos:
        candidatas = variantes_de(tipo)
        minimo = min(usos.get(v.nombre, 0) for v in candidatas)
        menos_usadas = [v for v in candidatas if usos.get(v.nombre, 0) == minimo]
        variante = rng.choice(menos_usadas)
        usos[variante.nombre] = usos.get(variante.nombre, 0) + 1
        elegidas.append(variante)
    return elegidas
