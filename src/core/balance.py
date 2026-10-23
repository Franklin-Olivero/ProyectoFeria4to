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

# Movimiento con inercia: la velocidad real se acerca a la pedida con un
# suavizado exponencial (independiente del framerate). Con 16/s llega
# al 95% de la velocidad del rol en ~0.19 s; con 22/s frena en ~0.14 s.
ACELERACION_MOVIMIENTO = 16.0  # 1/s: qué tan rápido arranca o cambia de dirección
FRENADO_MOVIMIENTO = 22.0  # 1/s: qué tan rápido se detiene al soltar
VELOCIDAD_MINIMA_MOVIMIENTO = 4.0  # px/s: por debajo se considera quieto

# Dash (src/entities/dash.py): igual para los 4 roles; la diferencia
# natural sale de la velocidad de cada rol, que se multiplica.
DASH_VELOCIDAD_MULT = 4.0  # multiplicador sobre la velocidad del rol
DASH_DURACION = 0.12  # segundos que dura el desplazamiento
DASH_COOLDOWN = 5.0  # segundos entre el inicio de un dash y el siguiente
DASH_INVULNERABLE = True  # durante el dash ningún golpe resta vida

# Controles: apuntado con mouse (src/core/apuntado.py) y gatillos
ZONA_MUERTA_APUNTADO = 6  # px: con el mouse más cerca se conserva la dirección previa
MOSTRAR_LINEA_APUNTADO = True  # línea tenue del jugador a la mira
CLICK_DISPARA = True  # click izquierdo mantenido dispara igual que SPACE

# Control de PS4 del J2 (src/core/entrada.py): sticks y gatillo en -1..1 / 0..1.
ZONA_MUERTA_STICK = 0.15  # inclinación menor que esto cuenta como stick suelto
UMBRAL_GATILLO = 0.5  # R2 hundido más que esto = disparando

# Cooperativo: un jugador caído revive al cruzar al siguiente cuarto.
VIDA_AL_REVIVIR = 1

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

# Regla de diseño: TODO patrón del jefe, en las 3 fases, deja un pasillo
# esquivable (ver tests/test_jefe_esquivable.py).
MAX_PROYECTILES_JEFE = 40  # balas del jefe vivas a la vez; con el tope lleno omite emitir

# Fase 1: ráfaga radial con hueco + invocar súbditos
RAFAGA_INTERVALO = 2.0
JEFE_RADIAL_BALAS = 16  # posiciones del círculo (separadas 22.5°)
JEFE_RADIAL_HUECO = 3  # balas consecutivas que faltan: el pasillo de escape
JEFE_RADIAL_SEPARACION_HUECO = 60  # grados mínimos entre el hueco nuevo y el anterior
JEFE_HUECO_DISTANCIA_MURO = 250  # px libres hasta el muro en la dirección del hueco (si se puede)
RAFAGA_VELOCIDAD = 130
INVOCACION_INTERVALO = 8.0
INVOCACION_CANTIDAD = 2

# Fase 2: escudo de anonimato + espiral continua + disparo dirigido
ESCUDO_VIDA = 15  # impactos para romperlo (el daño no importa)
ESPIRAL_INTERVALO = 0.15
JEFE_ESPIRAL_BRAZOS = 2  # brazos opuestos de la espiral (máximo 2 para que se lea)
JEFE_ESPIRAL_VEL_ANGULAR = 50  # grados por segundo que gira la espiral (lento)
ESPIRAL_VELOCIDAD = RAFAGA_VELOCIDAD  # misma velocidad de bala que la fase 1, en todas las fases
DIRIGIDO_INTERVALO = 1.5
DIRIGIDO_VELOCIDAD = 190

# Fase 3: ciclo de FASE3_CICLO s con descanso, en vez de todo a la vez:
#   0.0 y 1.2 s ráfagas con hueco | 4.0-6.5 s espiral | 6.5-8.0 s descanso
FASE3_CICLO = 8.0  # duración de un ciclo completo
FASE3_RAFAGAS = (0.0, 1.2)  # segundos del ciclo en que sale cada ráfaga radial
FASE3_ESPIRAL_INICIO = 4.0  # la espiral empieza cuando los anillos ya salieron de la arena
FASE3_ESPIRAL_DURACION = 2.5  # segundos de espiral por ciclo
FASE3_DESCANSO = 1.5  # sin ninguna emisión al final del ciclo: ventana para castigar
DIRIGIDO_MARGEN_RAFAGA = 0.8  # s tras una ráfaga sin disparo dirigido (no alcanza ni tapa el hueco)
CHARCO_INTERVALO = 6.0  # un charco nuevo cada 6 s en fase 3
CHARCO_MAXIMO_ACTIVOS = 2  # charcos vivos a la vez como máximo
CHARCO_DISTANCIA_MIN_JUGADOR = 90  # px mínimos entre el borde del charco nuevo y el jugador

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

# ----------------------------------------------------------------------
# Mazmorra multi-cuarto (src/dungeon/mazmorra.py)
# ----------------------------------------------------------------------
CANTIDAD_CUARTOS_MAZMORRA = 6
LADO_CUADRICULA_MAZMORRA = 3  # la mazmorra se genera sobre una cuadrícula 3x3
# El cuarto de entrada empieza vacío: sin enemigos.
DIFICULTAD_ENTRADA = {"cantidad_enemigos": 0, "multiplicador_velocidad": 1.0}

# Propagación de toxicidad: cada PROPAGACION_INTERVALO segundos que el
# jugador pasa en un cuarto con enemigos vivos, los cuartos aún no
# generados a distancia d (BFS) suben PROPAGACION_INCREMENTO / d.
PROPAGACION_INTERVALO = 15.0  # segundos
PROPAGACION_INCREMENTO = 10.0  # puntos de toxicidad a distancia 1
TOXICIDAD_MAXIMA_CUARTO = 100.0

# ----------------------------------------------------------------------
# Mapa de la ciudad (src/dungeon/grafo_ciudad.py)
# ----------------------------------------------------------------------
ZONA_PLAZA = "Plaza"
ZONA_COLEGIO = "Colegio"
ZONA_HOSPITAL = "Hospital"
ZONA_EMPRESA_MEDIOS = "Empresa de Medios"
ZONA_ALCALDIA = "Alcaldía"

# Calles (zona, zona, saturación). Ruta corta y peligrosa: Plaza ->
# Empresa de Medios directo (1 calle, peso 6). Ruta larga y segura:
# Plaza -> Hospital -> Empresa de Medios (2 calles, peso 3 + 2 = 5).
PESOS_INICIALES_CIUDAD = [
    (ZONA_PLAZA, ZONA_COLEGIO, 2),
    (ZONA_PLAZA, ZONA_HOSPITAL, 3),
    (ZONA_PLAZA, ZONA_EMPRESA_MEDIOS, 6),
    (ZONA_COLEGIO, ZONA_HOSPITAL, 4),
    (ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS, 2),
    (ZONA_COLEGIO, ZONA_ALCALDIA, 5),
    (ZONA_EMPRESA_MEDIOS, ZONA_ALCALDIA, 3),
]
PESO_MINIMO_CIUDAD = 1
PESO_MAXIMO_CIUDAD = 10
AJUSTE_PESO_CIUDAD = 1  # Purificación Exitosa baja, Detonación sube
COSTO_VIAJE_COLAPSO = 0.02  # puntos de colapso por unidad de costo de la ruta

# Reportes de toxicidad de cada zona con mazmorra (la Alcaldía es la
# mazmorra final y no usa reportes). Gravedad promedio -> nivel:
#   Colegio 4.4 -> 85.0 (tramo alto), Hospital 3.0 -> 50.0 (medio),
#   Empresa de Medios 1.6 -> 15.0 (bajo).
REPORTES_POR_ZONA = {
    ZONA_COLEGIO: [
        {"id": 1, "tipo": "comentario", "gravedad": 4},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 5},
        {"id": 3, "tipo": "denuncia", "gravedad": 5},
        {"id": 4, "tipo": "comentario", "gravedad": 3},
        {"id": 5, "tipo": "publicacion_viral", "gravedad": 5},
    ],
    ZONA_HOSPITAL: [
        {"id": 1, "tipo": "comentario", "gravedad": 2},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 4},
        {"id": 3, "tipo": "denuncia", "gravedad": 3},
        {"id": 4, "tipo": "comentario", "gravedad": 3},
    ],
    ZONA_EMPRESA_MEDIOS: [
        {"id": 1, "tipo": "comentario", "gravedad": 1},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 2},
        {"id": 3, "tipo": "comentario", "gravedad": 1},
        {"id": 4, "tipo": "denuncia", "gravedad": 2},
        {"id": 5, "tipo": "comentario", "gravedad": 2},
    ],
}
