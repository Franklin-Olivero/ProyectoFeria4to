"""Apariencia de un jugador: tono de piel y colores de su personaje.

Es lo que se elige en los vestidores (estilo Among Us). Lógica pura (sin
pygame), para probarse en aislado. Cada campo en None significa "lo del
dibujo": quien nunca pasó por un vestidor se ve exactamente como el
personaje de Higgsfield de su rol (assets/sprites/jugadores/<rol>.png).

    piel      índice en assets.TONOS_PIEL (pestaña COLOR).
    pelo      índice en assets.TONOS_PELO: color del cabello (HAIR).
    ropa      índice en assets.COLORES_ROPA: color de la camisa (SHIRT).
    pantalon  índice en assets.COLORES_PANTALON (PANTS).
    zapatos   índice en assets.COLORES_ZAPATOS (SHOES).
              Cada uno tiñe esa parte del dibujo (src/ui/tinte_jugador.py).
    cabeza    rol del que salía la cabeza en el vestidor viejo (HAT) y
    traje     rol del que salía el traje (SKIN). Se conservan para leer
              apariencias de versiones viejas por red, pero el arte de
              Higgsfield no se mezcla entre personajes: no cambian el dibujo.

Es inmutable (frozen): cambiar un campo crea otra Apariencia, y por eso
sirve de clave para cachear el sprite teñido (src/ui/sprites.py).

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
    zapatos: int | None = None

    def es_predeterminada(self):
        """True si no cambia nada respecto a la hoja del rol."""
        return self == PREDETERMINADA

    def con(self, campo, valor):
        """Copia con `campo` ("piel", "cabeza", "traje", "pelo", "ropa" o
        "pantalon" o "zapatos") cambiado a `valor`."""
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
                "pelo": self.pelo, "ropa": self.ropa, "pantalon": self.pantalon,
                "zapatos": self.zapatos}

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
            zapatos=_indice_valido(datos.get("zapatos"), assets.COLORES_ZAPATOS),
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
