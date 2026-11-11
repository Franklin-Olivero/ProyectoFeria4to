"""Textos de la pantalla de instrucciones de mazmorra (datos puros, sin Pygame).

Una ficha por TipoEnemigo y una para el jefe: nombre, qué hace (una
línea), cómo se comporta, amenaza (1 a 5) y un consejo. Los números
salen de balance.py, así el texto nunca contradice al juego. Si se
agrega un TipoEnemigo sin su ficha, tests/test_instrucciones.py falla.
Lo dibuja src/ui/instrucciones_render.py; aquí no hay nada de dibujo.
"""

from dataclasses import dataclass

from src.core.balance import (
    COOLDOWN_CONTACTO_PERSEGUIDOR,
    DISTANCIA_HUIDA_CURANDERO,
    FRACCION_CURA,
    GRACIA_ENTRADA_CUARTO_S,
    TIEMPO_LIMITE_JEFE,
    RANGO_PREFERIDO_TIRADOR,
)
from src.entities.tipos_enemigo import TipoEnemigo

AMENAZA_MAXIMA = 5


@dataclass(frozen=True)
class FichaEnemigo:
    nombre: str
    que_hace: str  # una línea
    comportamiento: str
    amenaza: int  # 1-5
    consejo: str


FICHAS = {
    TipoEnemigo.PERSEGUIDOR: FichaEnemigo(
        "Perseguidor",
        "Corre hacia ti sin parar.",
        f"Te persigue y te daña al tocarte (un golpe cada {COOLDOWN_CONTACTO_PERSEGUIDOR:g} s).",
        3,
        "Retrocede disparando y usa el dash si te alcanza.",
    ),
    TipoEnemigo.TIRADOR: FichaEnemigo(
        "Tirador",
        "Dispara desde lejos.",
        f"Mantiene unos {RANGO_PREFERIDO_TIRADOR:g} px de distancia y se ilumina justo antes de disparar.",
        4,
        "Cuando brille, muévete de lado; acércate para acorralarlo.",
    ),
    TipoEnemigo.CURANDERO: FichaEnemigo(
        "Curandero",
        "Cura a los demás enemigos.",
        f"Se esconde tras sus aliados, cura el {round(FRACCION_CURA * 100)} % de vida al más herido "
        f"y huye si estás a menos de {DISTANCIA_HUIDA_CURANDERO:g} px.",
        2,
        "Mátalo primero: mientras viva, los demás se recuperan.",
    ),
}

FICHA_JEFE = FichaEnemigo(
    "Servidor Central",
    "El jefe final: no hay decisión, solo combate.",
    "Tres fases: ráfagas con un hueco, espiral lenta y charcos tóxicos; en la fase 2 lo cubre un escudo.",
    AMENAZA_MAXIMA,
    "Busca el hueco de cada ráfaga; el Fact-Checking rompe el escudo de golpe.",
)

TITULO_REGLAS_CUARTO = "Reglas del cuarto"
REGLAS_CUARTO = (
    f"Al entrar a un cuarto tienes {GRACIA_ENTRADA_CUARTO_S:g} s de gracia: nadie ataca.",
    "El último cuarto se abre al limpiar todos; ahí te espera una decisión.",
    "Los muebles frenan las balas: cúbrete detrás, pero se rompen con los impactos.",
)
TITULO_REGLAS_JEFE = "Reglas del jefe"
REGLAS_JEFE = (
    f"{GRACIA_ENTRADA_CUARTO_S:g} s de gracia al empezar; tienes {TIEMPO_LIMITE_JEFE:g} s para vencerlo.",
    "Todos sus ataques dejan un hueco: muévete y busca la ventana para castigar.",
    "Columnas y muebles te cubren un rato: las balas los rompen y el jefe aplasta los que pisa.",
)


def ficha(tipo):
    """Ficha del TipoEnemigo (KeyError si falta: lo vigila un test)."""
    return FICHAS[tipo]
