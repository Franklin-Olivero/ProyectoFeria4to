"""Influencer: el rol que agrupa.

Ataque: cono de sonido expansivo, simplificado a un proyectil ancho
que, al golpear, daña y empuja al enemigo en la dirección del disparo.
Habilidad: Live Stream Viral, fija el aggro de todos los enemigos vivos
del cuarto hacia el Influencer durante unos segundos (ver
Enemigo.forzar_objetivo y la primera rama del behavior tree).
"""

from src.core import assets
from src.entities.player import JugadorBase
from src.entities.projectile import Proyectil


class ProyectilEmpuje(Proyectil):
    """Proyectil ancho que, además de dañar, hace retroceder al enemigo."""

    def __init__(self, posicion, direccion, danio):
        super().__init__(
            posicion=posicion,
            direccion=direccion,
            velocidad=assets.VELOCIDAD_PROYECTIL_INFLUENCER,
            danio=danio,
            color=assets.COLOR_PROYECTIL_INFLUENCER,
            tamanio=assets.TAMANIO_PROYECTIL_INFLUENCER,
        )

    def al_impactar(self, enemigo):
        enemigo.empujar(self.direccion * assets.IMPULSO_EMPUJE_INFLUENCER)
        super().al_impactar(enemigo)


class Influencer(JugadorBase):
    rol = "influencer"
    COLOR = assets.COLOR_INFLUENCER
    NOMBRE = "Influencer"
    NOMBRE_HABILIDAD = "Live Stream Viral"

    def ataque_basico(self):
        return [ProyectilEmpuje(self.rect.center, self.direccion_mirada, self.danio)]

    def usar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Live Stream Viral: todos los enemigos vivos persiguen y le
        disparan al Influencer, sin importar la distancia, por
        DURACION_LIVE_STREAM segundos."""
        if not self._gastar_carga():
            return False
        for enemigo in enemigos:
            if enemigo.vivo:
                enemigo.forzar_objetivo(self, assets.DURACION_LIVE_STREAM)
        return True
