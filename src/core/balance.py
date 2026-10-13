"""Balance de los 4 roles jugables (sin Pygame).

Único lugar donde se ajustan las estadísticas de los roles: las clases
de rol (src/entities/) solo leen STATS_POR_ROL[self.rol], nunca guardan
números de balance propios. Cada rol tiene una fortaleza y una
debilidad clara, y ninguno domina a otro en todas las estadísticas
(ver tests/test_balance.py).

Los multiplicadores son relativos a los valores base (1.0 = como se
sentía el Ciudadano antes de balancear).
"""

from dataclasses import dataclass

# Valores base (multiplicador 1.0)
VELOCIDAD_BASE = 220  # píxeles por segundo
VIDA_BASE = 5
DANIO_BASE = 1

# Invulnerabilidad tras recibir un golpe (todos los roles, cuarto y
# arena). Un golpe dentro de la ventana no resta vida ni la reinicia.
INVULNERABILIDAD_DURACION = 0.6  # segundos

# Límites de la cadencia efectiva (con o sin buff)
CADENCIA_MINIMA_INTERVALO = 0.08  # segundos: piso del tiempo entre disparos
CADENCIA_MAXIMA = 12  # volleys por segundo: tope

# Buff por kill: cada kill propia acelera la cadencia un rato. Matar
# otra vez mientras está activo reinicia la duración, no acumula.
BUFF_KILL_DURACION = 2.0  # segundos
BUFF_KILL_MULTIPLICADOR = 1.25

# Sinergia de equipo: fracción de una kill que recibe cada aliado
# cuando otro jugador mata a un enemigo (ver src/core/equipo.py).
CARGA_COMPARTIDA = 0.25


@dataclass(frozen=True)
class StatsRol:
    velocidad_mult: float
    cadencia: float  # volleys por segundo
    danio_mult: float
    vida_mult: float
    carga_maxima: int  # kills para llenar la habilidad
    proyectiles_nominales: float  # proyectiles que impactan a un objetivo por volley


STATS_POR_ROL = {
    # Fortaleza: el que más aguanta y dispara más seguido. Debilidad: el más lento y el de menor daño por proyectil.
    "ciudadano": StatsRol(0.85, 2.4, 0.6, 1.40, 6, 1.5),
    # Fortaleza: el más rápido, ideal para atraer y reposicionar. Debilidad: el más frágil.
    "influencer": StatsRol(1.25, 2.0, 1.0, 0.85, 5, 1.0),
    # Fortaleza: alto daño por rayo y buena movilidad. Debilidad: cadencia baja y poca vida.
    "periodista": StatsRol(1.05, 1.4, 1.6, 0.90, 5, 1.0),
    # Fortaleza: el mayor daño por golpe y la habilidad más barata. Debilidad: la cadencia más lenta.
    "candidato": StatsRol(0.95, 0.9, 3.0, 1.15, 4, 1.0),
}

# Estadísticas que se muestran en la pantalla de selección, en orden:
# (etiqueta, atributo de StatsRol).
ESTADISTICAS_VISIBLES = [
    ("Velocidad", "velocidad_mult"),
    ("Cadencia", "cadencia"),
    ("Daño", "danio_mult"),
    ("Vida", "vida_mult"),
]


def intervalo_disparo(cadencia, buff_activo=False):
    """Segundos entre volleys para una cadencia (volleys/s).

    Con el buff por kill la cadencia se multiplica por
    BUFF_KILL_MULTIPLICADOR. El resultado se acota: la cadencia nunca
    pasa de CADENCIA_MAXIMA y el intervalo nunca baja de
    CADENCIA_MINIMA_INTERVALO.
    """
    cadencia_efectiva = cadencia * (BUFF_KILL_MULTIPLICADOR if buff_activo else 1.0)
    cadencia_efectiva = min(cadencia_efectiva, CADENCIA_MAXIMA)
    return max(1 / cadencia_efectiva, CADENCIA_MINIMA_INTERVALO)


def dps_nominal(stats):
    """Daño por segundo teórico sobre un solo objetivo, en unidades de DANIO_BASE."""
    return stats.cadencia * stats.danio_mult * stats.proyectiles_nominales


def stats_normalizadas():
    """{rol: {atributo: fracción 0..1}}, cada estadística visible
    dividida por el máximo de esa estadística entre los 4 roles.
    Es lo que dibujan las barras de la pantalla de selección."""
    maximos = {
        atributo: max(getattr(stats, atributo) for stats in STATS_POR_ROL.values())
        for _, atributo in ESTADISTICAS_VISIBLES
    }
    return {
        rol: {
            atributo: getattr(stats, atributo) / maximos[atributo]
            for _, atributo in ESTADISTICAS_VISIBLES
        }
        for rol, stats in STATS_POR_ROL.items()
    }


# ----------------------------------------------------------------------
# Jefe final: "Servidor Central" (src/entities/jefe.py)
# ----------------------------------------------------------------------
# Patrones legibles: muchos proyectiles LENTOS, nunca rápidos e
# inesquivables. Todo intervalo está en segundos.

VIDA_JEFE = 120
VELOCIDAD_MOVIMIENTO_JEFE = 40  # px/s, solo en fase 3 ("se mueve lento")
# Perilla principal de dificultad de la pelea: con los i-frames de
# 0.6 s, 0.5 deja aguantar unos 10 golpes. Si la pelea queda muy fácil
# súbelo (p. ej. 0.75 o 1.0); si queda muy difícil bájalo.
DANIO_PROYECTIL_JEFE = 0.5

# Fase según la fracción de vida restante: > 60% fase 1, > 30% fase 2,
# el resto fase 3. Justo en 60% ya es fase 2 y justo en 30% ya es fase 3.
UMBRAL_FASE_2 = 0.60
UMBRAL_FASE_3 = 0.30
PAUSA_CAMBIO_FASE = 0.8  # sin atacar, parpadeando, al cambiar de fase
DURACION_DESTELLO_DANIO = 0.08

# Fase 1: ráfaga radial + invocar súbditos
RAFAGA_INTERVALO = 2.0
RAFAGA_CANTIDAD = 16  # proyectiles por círculo
RAFAGA_VELOCIDAD = 130
INVOCACION_INTERVALO = 8.0
INVOCACION_CANTIDAD = 2

# Fase 2: escudo de anonimato + espiral continua + disparo dirigido
ESCUDO_VIDA = 15  # impactos para romperlo (el daño no importa)
ESPIRAL_INTERVALO = 0.15
ESPIRAL_BRAZOS = 2  # brazos opuestos de la espiral
ESPIRAL_PASO_GRADOS = 13  # giro de la espiral entre disparos
ESPIRAL_VELOCIDAD = 120
DIRIGIDO_INTERVALO = 1.5
DIRIGIDO_VELOCIDAD = 190

# Fase 3: ráfaga + espiral con intervalos 30% más cortos + charcos
FACTOR_INTERVALO_FASE_3 = 0.7
CHARCO_INTERVALO = 4.0

# Charcos tóxicos (src/dungeon/charco.py)
CHARCO_AVISO = 1.0  # solo contorno, sin daño
CHARCO_DURACION = 5.0  # fase activa, con daño
CHARCO_RADIO = 45  # px
CHARCO_DANIO_POR_SEGUNDO = 1.0

# Mazmorra final (src/dungeon/mazmorra_final.py)
TIEMPO_LIMITE_JEFE = 180.0
NIVEL_TOXICIDAD_FINAL = 100.0  # siempre el máximo
COLAPSO_DESBLOQUEO = 80.0  # colapso > esto desbloquea la mazmorra final
MAZMORRAS_PARA_DESBLOQUEO = 1
