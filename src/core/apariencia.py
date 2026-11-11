"""Apariencia de un jugador del modo Online: piel, cabeza, traje y colores.

Es lo que se elige en los vestidores del lobby (estilo Among Us). Lógica
pura (sin pygame), para probarse en aislado. Cada campo en None significa
"lo de su rol": quien nunca pasó por un vestidor se ve exactamente como
la hoja de su rol (assets/sprites/jugadores/<rol>.png).

    piel      índice en assets.TONOS_PIEL; None = la piel original de la
              cabeza que lleva puesta (pestaña COLOR).
    cabeza    rol (assets.ROLES_APARIENCIA) del que sale la cabeza (HAT).
    traje     rol del que salen el torso y las piernas (SKIN).
    pelo      índice en assets.TONOS_PELO: color del pelo (HAIR).
    ropa      índice en assets.COLORES_ROPA: color de la camisa (SHIRT).
    pantalon  índice en assets.COLORES_PANTALON (PANTS).
              Los tres últimos recolorean el arte de las recetas
              (src/ui/receta_jugador.py); None = el color original.

Es inmutable (frozen): cambiar un campo crea otra Apariencia, y por eso
sirve de clave para cachear el sprite armado (src/ui/sprites.py).

Viaja por red como dict (a_dict / de_dict) dentro de cada nodo del
GrafoSala (Online/protocolo.py). de_dict valida campo por campo: un dato
roto o de otra versión del juego nunca tumba el lobby, solo deja ese
campo en None. Todas las operaciones son O(1).
"""

from dataclasses import dataclass, replace

from src.core import assets


@dataclass(frozen=True)
class Apariencia:
    piel: int | None = None
    cabeza: str | None = None
    traje: str | None = None
    pelo: int | None = None
    ropa: int | None = None
    pantalon: int | None = None

    def es_predeterminada(self):
        """True si no cambia nada respecto a la hoja del rol."""
        return self == PREDETERMINADA

    def con(self, campo, valor):
        """Copia con `campo` ("piel", "cabeza", "traje", "pelo", "ropa" o
        "pantalon") cambiado a `valor`."""
        return replace(self, **{campo: valor})

    def cabeza_para(self, rol):
        """Rol del que sale la cabeza de un jugador de rol `rol`."""
        return self.cabeza or rol

    def traje_para(self, rol):
        """Rol del que sale el traje de un jugador de rol `rol`."""
        return self.traje or rol

    def a_dict(self):
        """Para mandarla por red (JSON)."""
        return {"piel": self.piel, "cabeza": self.cabeza, "traje": self.traje,
                "pelo": self.pelo, "ropa": self.ropa, "pantalon": self.pantalon}

    @classmethod
    def de_dict(cls, datos):
        """Apariencia recibida por red; lo que no sea válido (o no venga,
        como en una versión vieja del juego) queda en None."""
        if not isinstance(datos, dict):
            return PREDETERMINADA
        return cls(
            piel=_piel_valida(datos.get("piel")),
            cabeza=_rol_valido(datos.get("cabeza")),
            traje=_rol_valido(datos.get("traje")),
            pelo=_indice_valido(datos.get("pelo"), assets.TONOS_PELO),
            ropa=_indice_valido(datos.get("ropa"), assets.COLORES_ROPA),
            pantalon=_indice_valido(datos.get("pantalon"), assets.COLORES_PANTALON),
        )


PREDETERMINADA = Apariencia()


def _piel_valida(valor):
    return _indice_valido(valor, assets.TONOS_PIEL)


def _indice_valido(valor, paleta):
    # bool es subclase de int, pero True/False no son un color.
    if isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor < len(paleta):
        return valor
    return None


def _rol_valido(valor):
    return valor if isinstance(valor, str) and valor in assets.ROLES_APARIENCIA else None
