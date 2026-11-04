"""Investigación del infiltrado, capítulo 3 (lógica pura, sin Pygame).

Tras resolver la terminal de la Empresa de Medios aparecen tres cuentas
(content/campaign.json, "sospechosos"): una coordinó la campaña de
NOVA_404, otra fue suplantada y otra compartió por error. El jugador
recorre las tarjetas con ← → y señala con Enter a la coordinadora. La
culpabilidad se deduce de las pistas (horarios automáticos, etiqueta
oculta, conexiones), nunca de la popularidad. Una elección correcta da
la pista final de la investigación; acusar a la víctima o al que se
equivocó tiene costo (conflictos, reputación).

En solitario y en cooperativo local decide el J1. En Online decide el
host (igual que la terminal): no se agregó protocolo de votación.
"""

from dataclasses import dataclass, field

from src.core.balance import (
    PUNTOS_INFILTRADO_CORRECTO,
    REPUTACION_INFILTRADO_CORRECTO,
    REPUTACION_INFILTRADO_ERRADO,
)

IZQUIERDA = "izquierda"
DERECHA = "derecha"
CONFIRMAR = "confirmar"

VEREDICTO_COORDINADOR = "coordinador"
VEREDICTO_VICTIMA = "victima"
VEREDICTO_ERROR = "error"

EFECTOS_POR_VEREDICTO = {
    VEREDICTO_COORDINADOR: {"informacion_verificada": 8, "confianza": 6, "desinformacion": -8},
    VEREDICTO_VICTIMA: {"conflictos": 10, "convivencia": -6, "confianza": -4},
    VEREDICTO_ERROR: {"conflictos": 6, "convivencia": -4},
}
TEXTOS_RESULTADO = {
    VEREDICTO_COORDINADOR: "Señalaste a la cuenta coordinadora. Las pruebas encajan: horarios automáticos, etiqueta oculta y raíz común.",
    VEREDICTO_VICTIMA: "Acusaste a una cuenta suplantada. Su dueña estaba en turno sin celular: la red se volvió contra una inocente.",
    VEREDICTO_ERROR: "Acusaste a quien compartió por error y ya se había disculpado. La coordinadora siguió operando.",
}


@dataclass
class ResultadoInvestigacion:
    cuenta: dict
    correcto: bool
    texto: str
    efectos: dict = field(default_factory=dict)
    reputacion: int = 0
    puntos: int = 0


class Investigacion:
    def __init__(self, datos):
        self.cuentas = list(datos["cuentas"])
        self.culpable = datos["culpable"]
        self.indice = 0
        self.resultado = None

    @property
    def seleccionada(self):
        return self.cuentas[self.indice]

    @property
    def terminada(self):
        return self.resultado is not None

    def navegar(self, direccion):
        """← → mueven el cursor (circular); Enter acusa a la seleccionada. O(1)."""
        if self.terminada:
            return
        cantidad = len(self.cuentas)
        if direccion == IZQUIERDA:
            self.indice = (self.indice - 1) % cantidad
        elif direccion == DERECHA:
            self.indice = (self.indice + 1) % cantidad
        elif direccion == CONFIRMAR:
            self.resultado = self.acusar(self.seleccionada["id"])

    def acusar(self, id_cuenta):
        cuenta = next(c for c in self.cuentas if c["id"] == id_cuenta)
        correcto = id_cuenta == self.culpable
        veredicto = cuenta["veredicto"]
        return ResultadoInvestigacion(
            cuenta=cuenta,
            correcto=correcto,
            texto=TEXTOS_RESULTADO[veredicto],
            efectos=dict(EFECTOS_POR_VEREDICTO[veredicto]),
            reputacion=REPUTACION_INFILTRADO_CORRECTO if correcto else REPUTACION_INFILTRADO_ERRADO,
            puntos=PUNTOS_INFILTRADO_CORRECTO if correcto else 0,
        )
