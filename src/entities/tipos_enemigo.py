"""Tipos de enemigo y composición de cada cuarto (lógica pura, sin Pygame).

    PERSEGUIDOR  cuerpo a cuerpo, rápido, daño por contacto, no dispara.
    TIRADOR      mantiene ~320 px de distancia y dispara apuntado, con
                 una telegrafía corta antes de cada disparo.
    CURANDERO    no ataca: se esconde detrás de sus aliados, huye si el
                 jugador se acerca y cada pocos segundos cura a un herido.

Los números de cada tipo viven en balance.py (STATS_TIPO_ENEMIGO y las
constantes de cada comportamiento); los colores, tamaños y el id de su
sprite, en assets.py. Las clases con el behavior tree de cada tipo
están en src/entities/enemigos.py.

composicion_cuarto() decide qué tipos aparecen en un cuarto según su
tramo de toxicidad (el dict de nivel_a_dificultad del clasificador):

    BAJA  (2)  todos perseguidores; el cuarto final puede traer 1 tirador.
    MEDIA (3)  ~60 % perseguidores / ~40 % tiradores; a veces 1 curandero
               (25 %, nunca en los cuartos iniciales).
    ALTA  (5)  ~40 % perseguidores / ~40 % tiradores / ~20 % curanderos
               (máx. 2 y nunca más que los demás); el final garantiza
               al menos 1 curandero y 2 tiradores.
Siempre queda al menos un enemigo que no es curandero.
"""

from enum import Enum

from src.core.balance import (
    MAX_CURANDEROS_ALTA,
    MAX_CURANDEROS_MEDIA,
    MIN_CURANDEROS_FINAL_ALTA,
    MIN_TIRADORES_FINAL_ALTA,
    PROB_CURANDERO_EXTRA_ALTA,
    PROB_CURANDERO_MEDIA,
    PROB_TIRADOR_FINAL_BAJA,
    PROPORCION_CURANDEROS_ALTA,
    PROPORCION_TIRADORES_ALTA,
    PROPORCION_TIRADORES_MEDIA,
    STATS_TIPO_ENEMIGO,
)
from src.dungeon.clasificador_toxicidad import DIFICULTAD_ALTA, DIFICULTAD_MEDIA


class TipoEnemigo(Enum):
    PERSEGUIDOR = "perseguidor"
    TIRADOR = "tirador"
    CURANDERO = "curandero"


# Stats de cada tipo (velocidad_mult, vida), leídos de balance.py.
CONFIG_TIPO = {tipo: STATS_TIPO_ENEMIGO[tipo.value] for tipo in TipoEnemigo}

TRAMO_BAJO = "baja"
TRAMO_MEDIO = "media"
TRAMO_ALTO = "alta"


def tramo_de(dificultad):
    """Tramo de toxicidad de un dict de nivel_a_dificultad, por su
    cantidad de enemigos (2 baja, 3 media, 5 alta)."""
    cantidad = dificultad["cantidad_enemigos"]
    if cantidad >= DIFICULTAD_ALTA["cantidad_enemigos"]:
        return TRAMO_ALTO
    if cantidad >= DIFICULTAD_MEDIA["cantidad_enemigos"]:
        return TRAMO_MEDIO
    return TRAMO_BAJO


def composicion_cuarto(nivel_dificultad, es_cuarto_final, rng, es_cuarto_inicial=False):
    """Lista de TipoEnemigo para un cuarto: perseguidores, luego
    tiradores, luego curanderos (así quien reparte las posiciones puede
    dejar a los curanderos más lejos de la entrada).

    `nivel_dificultad` es el dict de nivel_a_dificultad; su
    "cantidad_enemigos" es el total. `rng` (random.Random) decide las
    partes al azar, así los tests son deterministas. Un cuarto inicial
    (la entrada y sus vecinos: las primeras peleas) nunca trae curanderos.
    O(n), con n la cantidad de enemigos.
    """
    total = nivel_dificultad["cantidad_enemigos"]
    if total <= 0:
        return []
    tramo = tramo_de(nivel_dificultad)
    curanderos = tiradores = 0

    if tramo == TRAMO_BAJO:
        if es_cuarto_final and rng.random() < PROB_TIRADOR_FINAL_BAJA:
            tiradores = 1
    elif tramo == TRAMO_MEDIO:
        if not es_cuarto_inicial and rng.random() < PROB_CURANDERO_MEDIA:
            curanderos = MAX_CURANDEROS_MEDIA
        tiradores = round((total - curanderos) * PROPORCION_TIRADORES_MEDIA)
    else:
        if not es_cuarto_inicial:
            curanderos = round(total * PROPORCION_CURANDEROS_ALTA)
            if rng.random() < PROB_CURANDERO_EXTRA_ALTA:
                curanderos += 1
            if es_cuarto_final:
                curanderos = max(curanderos, MIN_CURANDEROS_FINAL_ALTA)
            # Máximo de curanderos y nunca más que los que sí atacan.
            curanderos = min(curanderos, MAX_CURANDEROS_ALTA, total // 2)
        tiradores = round(total * PROPORCION_TIRADORES_ALTA)
        if es_cuarto_final:
            tiradores = max(tiradores, MIN_TIRADORES_FINAL_ALTA)

    # Garantía: al menos un enemigo que no sea curandero.
    curanderos = min(curanderos, total - 1)
    tiradores = min(tiradores, total - curanderos)
    perseguidores = total - curanderos - tiradores
    return (
        [TipoEnemigo.PERSEGUIDOR] * perseguidores
        + [TipoEnemigo.TIRADOR] * tiradores
        + [TipoEnemigo.CURANDERO] * curanderos
    )
