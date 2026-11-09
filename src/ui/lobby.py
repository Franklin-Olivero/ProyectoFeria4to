"""Contenido del lobby: habilidades, sinergias y resumen (lógica pura, sin Pygame).

Lo dibuja src/ui/seleccion_rol.py. La sinergia sale del diseño de los
roles: el Influencer agrupa, el Periodista expone, el Candidato remata
y el Ciudadano sostiene. Cada par de roles distintos tiene una razón
para jugar junto; repetir rol funciona, pero no se complementa.
"""

from src.core.balance import STATS_POR_ROL

DESCRIPCION_HABILIDAD = {
    "ciudadano": "Levanta un domo comunitario durante 4 s.",
    "influencer": "Atrae a todos los enemigos del cuarto durante 3 s.",
    "periodista": "Rayo que quita el escudo de anonimato.",
    "candidato": "3 proyectiles que rebotan en las paredes.",
}
PAPEL = {"influencer": "agrupa", "periodista": "expone", "candidato": "remata", "ciudadano": "sostiene"}

# Por qué combina cada par de roles distintos (clave sin orden).
SINERGIAS = {
    frozenset(("influencer", "candidato")): "El Influencer junta a los enemigos y el Candidato los barre.",
    frozenset(("influencer", "periodista")): "Enemigos agrupados en la línea del rayo perforante.",
    frozenset(("periodista", "candidato")): "El Periodista quita escudos y el Candidato remata.",
    frozenset(("ciudadano", "influencer")): "El Ciudadano aguanta mientras el Influencer atrae.",
    frozenset(("ciudadano", "periodista")): "El Ciudadano cubre los disparos lentos del Periodista.",
    frozenset(("ciudadano", "candidato")): "El Ciudadano sostiene mientras el Candidato carga su golpe.",
}
# Mejores compañeros de cada rol (para el lobby de 1 jugador).
COMPANEROS = {
    "ciudadano": ("candidato", "periodista"),
    "influencer": ("candidato", "periodista"),
    "periodista": ("candidato", "influencer"),
    "candidato": ("influencer", "periodista"),
}
MAXIMO_ESTRELLAS = 3

RESUMEN_PARTIDA = "Colapso inicial 0 %  ·  Purifica las mazmorras de Ciudad Nova y derrota al Servidor Central"
LINEA_CONTROLES = ("WASD mover  ·  Ratón apuntar  ·  Espacio / clic disparar  ·  F habilidad  ·  "
                   "Shift dash  ·  M minimapa  ·  N silencio  ·  - + volumen")


def sinergia(roles):
    """(estrellas 0-3, texto) del equipo `roles` (claves de STATS_POR_ROL).

    Un solo jugador: 0 estrellas y con quién combina su rol. Dos o más:
    1 estrella por cada par de roles distintos que tiene sinergia (hasta
    3) y la razón del primero; si todos repiten rol, 1 estrella."""
    roles = list(roles)
    if not roles:
        return 0, ""
    if len(roles) == 1:
        a, b = COMPANEROS[roles[0]]
        return 0, f"Combina con {nombre(a)} y {nombre(b)}"
    pares = []
    for i, rol in enumerate(roles):
        for otro in roles[i + 1:]:
            clave = frozenset((rol, otro))
            if clave in SINERGIAS and clave not in pares:
                pares.append(clave)
    if not pares:
        return 1, "Mismo rol: funciona, pero prueben roles que se complementen"
    return min(MAXIMO_ESTRELLAS, len(pares) + 1), SINERGIAS[pares[0]]


def nombre(rol):
    return rol.capitalize()


def valor_estadistica(rol, atributo):
    """Texto del valor real de una estadística, para el lado de su barra."""
    valor = getattr(STATS_POR_ROL[rol], atributo)
    if atributo == "cadencia":
        return f"{valor:g}/s"
    if atributo == "carga_maxima":
        return f"{valor} kills"
    return f"×{valor:g}"
