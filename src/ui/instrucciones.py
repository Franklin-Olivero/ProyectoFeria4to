"""Pantalla de instrucciones antes de cada mazmorra (lógica pura, sin Pygame).

Al entrar a una mazmorra (o a la arena del jefe) el juego queda congelado
y se muestra una tarjeta por cada tipo de enemigo que puede aparecer
allí, más una de reglas. Qué tipos: los que composicion_cuarto puede
generar con el nivel de toxicidad de la zona (tipos_posibles); en el
jefe, sus súbditos y el jefe. Los textos están en src/core/textos_enemigos.py.

Enter, Espacio o clic comienzan, pero solo pasados RETARDO_INSTRUCCIONES
segundos (un Enter que venía de la puerta no la salta). Con más tarjetas
que TARJETAS_POR_PAGINA_INSTRUCCIONES, ← y → pasan de página.

La preferencia instrucciones_mazmorra decide si se muestran siempre o
solo cuando hay un tipo de enemigo que el jugador todavía no vio
(debe_mostrarse). El dibujo vive en src/ui/instrucciones_render.py.
"""

from dataclasses import dataclass

from src.core.balance import RETARDO_INSTRUCCIONES, TARJETAS_POR_PAGINA_INSTRUCCIONES
from src.core.preferencias import INSTRUCCIONES_PRIMERA_VEZ
from src.dungeon.clasificador_toxicidad import DIFICULTAD_ALTA, DIFICULTAD_BAJA, nivel_a_dificultad
from src.entities.tipos_enemigo import TIPOS_SUBDITOS, tipos_posibles
from src.ui.navegacion import CONFIRMAR, DERECHA, IZQUIERDA, SONIDO_CONFIRMAR, SONIDO_NAVEGAR

ENEMIGO = "enemigo"
JEFE = "jefe"
REGLAS_CUARTO = "reglas_cuarto"
REGLAS_JEFE = "reglas_jefe"
TIPO_JEFE = "jefe"  # clave de "visto" para el jefe


@dataclass(frozen=True)
class Tarjeta:
    clase: str  # ENEMIGO, JEFE, REGLAS_CUARTO o REGLAS_JEFE
    tipo: object = None  # TipoEnemigo en las de ENEMIGO


def nombre_dificultad(dificultad):
    if dificultad == DIFICULTAD_ALTA:
        return "Alta"
    if dificultad == DIFICULTAD_BAJA:
        return "Baja"
    return "Media"


def tipos_de_mazmorra(nivel_toxicidad):
    """Tipos que pueden aparecer en una mazmorra normal de ese nivel."""
    return tipos_posibles(nivel_a_dificultad(nivel_toxicidad))


def tarjetas_mazmorra(nivel_toxicidad):
    return [Tarjeta(ENEMIGO, tipo) for tipo in tipos_de_mazmorra(nivel_toxicidad)] + [Tarjeta(REGLAS_CUARTO)]


def tarjetas_jefe():
    subditos = [tipo for i, tipo in enumerate(TIPOS_SUBDITOS) if tipo not in TIPOS_SUBDITOS[:i]]
    return [Tarjeta(ENEMIGO, tipo) for tipo in subditos] + [Tarjeta(JEFE), Tarjeta(REGLAS_JEFE)]


def claves_vistas(tarjetas):
    """Lo que esta pantalla le enseña al jugador (tipos y jefe)."""
    claves = set()
    for tarjeta in tarjetas:
        if tarjeta.clase == ENEMIGO:
            claves.add(tarjeta.tipo)
        elif tarjeta.clase == JEFE:
            claves.add(TIPO_JEFE)
    return claves


def debe_mostrarse(preferencia, tarjetas, vistos):
    """Siempre, salvo con "solo primera vez": entonces solo si hay algo nuevo."""
    if preferencia != INSTRUCCIONES_PRIMERA_VEZ:
        return True
    return not claves_vistas(tarjetas) <= set(vistos)


class InstruccionesMazmorra:
    def __init__(self, titulo, nivel_toxicidad, dificultad, tarjetas, es_jefe=False,
                 por_pagina=TARJETAS_POR_PAGINA_INSTRUCCIONES, retardo=RETARDO_INSTRUCCIONES):
        self.titulo = titulo
        self.nivel_toxicidad = nivel_toxicidad
        self.dificultad = dificultad  # "Baja", "Media" o "Alta"
        self.tarjetas = list(tarjetas)
        self.es_jefe = es_jefe
        self.por_pagina = por_pagina
        self.retardo = retardo
        self.tiempo = 0.0
        self.pagina = 0
        self.comenzada = False

    @classmethod
    def para_mazmorra(cls, nombre_zona, nivel_toxicidad):
        dificultad = nombre_dificultad(nivel_a_dificultad(nivel_toxicidad))
        return cls(f"{nombre_zona} infectado", nivel_toxicidad, dificultad, tarjetas_mazmorra(nivel_toxicidad))

    @classmethod
    def para_jefe(cls, nivel_toxicidad):
        return cls("Alcaldía · Servidor Central", nivel_toxicidad, "Máxima", tarjetas_jefe(), es_jefe=True)

    @property
    def paginas(self):
        return max(1, -(-len(self.tarjetas) // self.por_pagina))

    def tarjetas_visibles(self):
        inicio = self.pagina * self.por_pagina
        return self.tarjetas[inicio:inicio + self.por_pagina]

    @property
    def puede_comenzar(self):
        return self.tiempo >= self.retardo

    def actualizar(self, dt):
        """Solo corre el retardo anti-salto: la mazmorra no avanza."""
        self.tiempo += dt

    def accion(self, accion):
        """CONFIRMAR comienza (pasado el retardo); ← → cambian de página.
        Retorna el sonido o None."""
        if accion == CONFIRMAR:
            if not self.puede_comenzar:
                return None
            self.comenzada = True
            return SONIDO_CONFIRMAR
        if accion in (IZQUIERDA, DERECHA) and self.paginas > 1:
            paso = -1 if accion == IZQUIERDA else 1
            nueva = max(0, min(self.paginas - 1, self.pagina + paso))
            if nueva != self.pagina:
                self.pagina = nueva
                return SONIDO_NAVEGAR
        return None
