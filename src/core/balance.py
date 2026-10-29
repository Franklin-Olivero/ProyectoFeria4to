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

from src.core.assets import ESCALA_PIXEL

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
# Ciudad Nova: mapa de casillas (src/dungeon/ciudad_mapa.py) y red de
# calles como grafo (src/dungeon/grafo_ciudad.py)
# ----------------------------------------------------------------------
LADO_CASILLA_PIXEL_ART = 16  # píxeles de arte por lado de casilla
TAM_CASILLA = LADO_CASILLA_PIXEL_ART * ESCALA_PIXEL  # 48 px en pantalla
ENTRADA_ALCANCE = 60  # px del centro de la puerta para poder entrar con E
# La Alcaldía sellada queda detrás de sus barricadas: el aviso se
# muestra desde un poco más lejos que el alcance para entrar.
ALCANCE_AVISO_SELLADA = 110  # px

ZONA_PLAZA = "Plaza"
ZONA_COLEGIO = "Colegio"
ZONA_HOSPITAL = "Hospital"
ZONA_EMPRESA_MEDIOS = "Empresa de Medios"
ZONA_ALCALDIA = "Alcaldía"
CRUCE_NORTE = "Cruce Norte"
CRUCE_SUR = "Cruce Sur"
CRUCE_OESTE = "Cruce Oeste"
CRUCE_ESTE = "Cruce Este"

# Tramos de calle (nodo, nodo, saturación inicial). El trazado es una
# rueda: la Plaza al centro unida a 4 cruces y un anillo exterior que
# pasa frente a los 4 edificios. Ninguna arista es puente y cada
# edificio tiene dos rutas (una por cada lado del anillo).
# Ejemplo de Dijkstra: Plaza -> Empresa de Medios por el Cruce Este
# cuesta 4 + 2 = 6; por el Cruce Sur, 3 + 5 = 8.
PESOS_INICIALES_CIUDAD = [
    (ZONA_PLAZA, CRUCE_NORTE, 2),
    (ZONA_PLAZA, CRUCE_SUR, 3),
    (ZONA_PLAZA, CRUCE_OESTE, 2),
    (ZONA_PLAZA, CRUCE_ESTE, 4),
    (CRUCE_NORTE, ZONA_COLEGIO, 3),
    (ZONA_COLEGIO, CRUCE_OESTE, 2),
    (CRUCE_OESTE, ZONA_HOSPITAL, 3),
    (ZONA_HOSPITAL, CRUCE_SUR, 2),
    (CRUCE_SUR, ZONA_EMPRESA_MEDIOS, 5),
    (ZONA_EMPRESA_MEDIOS, CRUCE_ESTE, 2),
    (CRUCE_ESTE, ZONA_ALCALDIA, 3),
    (ZONA_ALCALDIA, CRUCE_NORTE, 4),
]
PESO_MINIMO_CIUDAD = 1
PESO_MAXIMO_CIUDAD = 10
# Pesos dinámicos al resolver una mazmorra, en las calles de su entrada.
AJUSTE_DETONACION = 3  # Detonación: +3
AJUSTE_PURIFICACION = 2  # Purificación Exitosa: -2
# Histéresis de las barricadas: una calle se bloquea al llegar a
# BLOQUEO_PESO y se desbloquea al bajar de DESBLOQUEO_PESO. Si
# bloquearla desconectaría la ciudad, queda abierta con PESO_MAXIMO_CIUDAD.
BLOQUEO_PESO = 8
DESBLOQUEO_PESO = 6

# Cintillo de noticias (src/dungeon/noticias.py)
COLAPSO_TITULAR_ALTO = 50.0  # desde este colapso hay titular de alarma

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

# ----------------------------------------------------------------------
# Gracia al entrar a un cuarto (src/dungeon/gracia_entrada.py)
# ----------------------------------------------------------------------
# Mientras dura, los enemigos quedan congelados (no persiguen, no
# disparan, no golpean) y el jugador solo puede moverse.
GRACIA_ENTRADA_CUARTO_S = 1.0
# Ningún enemigo aparece a menos de esto del punto donde entra el jugador.
DISTANCIA_MIN_SPAWN_ENEMIGO = 260  # px
SEPARACION_MIN_SPAWN_ENEMIGOS = 70  # px entre dos enemigos al aparecer
MARGEN_SPAWN_ENEMIGO = 60  # px libres hasta los muros del cuarto
PASO_GRILLA_SPAWN = (90, 80)  # px entre posiciones candidatas (x, y)

# ----------------------------------------------------------------------
# Tipos de enemigo (src/entities/tipos_enemigo.py, src/entities/enemigos.py)
# ----------------------------------------------------------------------
# La velocidad final = VELOCIDAD_ENEMIGO (assets) x multiplicador del
# tramo de toxicidad x velocidad_mult del tipo.


@dataclass(frozen=True)
class StatsTipoEnemigo:
    velocidad_mult: float
    vida: float


STATS_TIPO_ENEMIGO = {
    # Cuerpo a cuerpo: rápido, vida media, daño por contacto. No dispara.
    "perseguidor": StatsTipoEnemigo(velocidad_mult=1.15, vida=3),
    # A distancia: lento, frágil, dispara apuntado con telegrafía.
    "tirador": StatsTipoEnemigo(velocidad_mult=0.8, vida=2),
    # Apoyo: el más lento y frágil, no ataca; cura a sus aliados.
    "curandero": StatsTipoEnemigo(velocidad_mult=0.7, vida=2),
}

# Variantes: cada personaje de assets/sprites/enemigos 2.0 es un tipo de
# comportamiento (perseguidor / tirador / curandero) con sus propios
# números (ver src/entities/variantes_enemigo.py). `alcance` es el
# margen extra de golpe de los cuerpo a cuerpo y el rango preferido de
# los tiradores; `cooldown_s` es el tiempo entre golpes o entre disparos;
# `cuadros_ataque` son los cuadros de su tira de ataque. El golpe cae a
# FRACCION_IMPACTO_ATAQUE de la animación (así se ve venir) y el tirador
# usa ese mismo tiempo como telegrafía.
DURACION_CUADRO_ATAQUE_S = 0.07
FRACCION_IMPACTO_ATAQUE = 0.5


@dataclass(frozen=True)
class StatsVariante:
    tipo: str  # clave de STATS_TIPO_ENEMIGO
    velocidad_mult: float
    vida: float
    cuadros_ataque: int
    danio: float = 0
    cooldown_s: float = 0.0
    alcance: float = 0
    proyectiles: int = 1  # tiradores: balas por disparo (abanico)
    apertura_grados: float = 0  # ángulo entre balas del abanico
    velocidad_proyectil: float = 0
    tamanio_proyectil: int = 10


STATS_VARIANTE_ENEMIGO = {
    # Cuerpo a cuerpo
    "Hellhound": StatsVariante("perseguidor", 1.15, 3, 8, danio=1, cooldown_s=0.8, alcance=8),
    "Minotaur": StatsVariante("perseguidor", 0.8, 5, 8, danio=2, cooldown_s=1.6, alcance=14),
    "Blood Monster_A": StatsVariante("perseguidor", 1.0, 3, 8, danio=1, cooldown_s=0.9, alcance=8),
    "Blood Monster_B": StatsVariante("perseguidor", 1.3, 2, 8, danio=1, cooldown_s=0.7, alcance=6),
    "Hellbat": StatsVariante("perseguidor", 1.35, 2, 6, danio=1, cooldown_s=0.9, alcance=8),
    "Demon_A": StatsVariante("perseguidor", 1.05, 3, 7, danio=1, cooldown_s=0.9, alcance=10),
    "Demon_E": StatsVariante("perseguidor", 0.95, 4, 8, danio=1, cooldown_s=1.0, alcance=16),
    "Black Knight_A": StatsVariante("perseguidor", 0.85, 4, 16, danio=2, cooldown_s=1.8, alcance=12),
    "Black Knight_C": StatsVariante("perseguidor", 0.75, 6, 8, danio=2, cooldown_s=1.6, alcance=16),
    "Demoness_A": StatsVariante("perseguidor", 1.0, 3, 9, danio=1, cooldown_s=0.8, alcance=14),
    # A distancia
    "Warlock": StatsVariante("tirador", 0.8, 2, 7, danio=1, cooldown_s=1.8, alcance=320,
                             velocidad_proyectil=260, tamanio_proyectil=12),
    "Demon_B": StatsVariante("tirador", 0.9, 2, 9, danio=1, cooldown_s=1.5, alcance=340,
                             velocidad_proyectil=380, tamanio_proyectil=8),
    "Black Knight_B": StatsVariante("tirador", 0.7, 3, 7, danio=2, cooldown_s=2.6, alcance=300,
                                    velocidad_proyectil=200, tamanio_proyectil=12),
    "Eyeball Monster": StatsVariante("tirador", 0.9, 2, 8, danio=1, cooldown_s=1.6, alcance=300,
                                     velocidad_proyectil=320, tamanio_proyectil=8),
    "Lava Slime": StatsVariante("tirador", 0.7, 3, 6, danio=1, cooldown_s=2.2, alcance=260,
                                proyectiles=3, apertura_grados=30, velocidad_proyectil=220),
    "Demon_C": StatsVariante("tirador", 0.85, 2, 6, danio=1, cooldown_s=2.0, alcance=300,
                             proyectiles=2, apertura_grados=14, velocidad_proyectil=260),
    "Demon_D": StatsVariante("tirador", 0.8, 3, 11, danio=1, cooldown_s=2.4, alcance=300,
                             proyectiles=3, apertura_grados=24, velocidad_proyectil=240),
    # Apoyo (su "ataque" es el hechizo de cura)
    "Ghostfire": StatsVariante("curandero", 0.7, 2, 6),
    "Demoness_B": StatsVariante("curandero", 0.7, 2, 8),
}

# Perseguidor: golpe por contacto
DANIO_CONTACTO_PERSEGUIDOR = 1
COOLDOWN_CONTACTO_PERSEGUIDOR = 0.8  # s entre golpes

# Tirador: mantiene distancia y dispara apuntado
RANGO_PREFERIDO_TIRADOR = 320  # px al jugador
TOLERANCIA_RANGO_TIRADOR = 40  # px: dentro de [rango ± tolerancia] orbita
FACTOR_ORBITA_TIRADOR = 0.5  # fracción de su velocidad al orbitar
CADENCIA_TIRADOR_S = 1.8  # s entre disparos
TELEGRAFIA_TIRADOR_S = 0.25  # s resaltado antes de cada disparo
VELOCIDAD_PROYECTIL_TIRADOR = 260  # px/s: esquivable
DANIO_PROYECTIL_TIRADOR = 1

# Curandero: se esconde detrás de sus aliados y los cura
DISTANCIA_HUIDA_CURANDERO = 200  # px: más cerca que esto, huye
SEPARACION_DETRAS_CURANDERO = 120  # px detrás del centro de sus aliados
INTERVALO_CURA_S = 3.0
FRACCION_CURA = 0.34  # de la vida máxima del aliado por cura
RADIO_CURA = 280  # px
MAX_CURAS_POR_ALIADO = 2  # por aliado y por cuarto: nadie es inmatable
DURACION_EFECTO_CURA_S = 0.4  # s que se ve el rayo de cura
PANICO_CURANDERO_S = 6.0  # s siendo el único vivo antes de entrar en pánico

# Composición de cada cuarto según el tramo de toxicidad
# (composicion_cuarto en src/entities/tipos_enemigo.py). Los totales
# salen de DIFICULTAD_BAJA/MEDIA/ALTA del clasificador (2 / 3 / 5).
PROB_TIRADOR_FINAL_BAJA = 0.5  # el cuarto final BAJA puede traer 1 tirador
PROPORCION_TIRADORES_MEDIA = 0.4  # ~60 % perseguidores / ~40 % tiradores
PROB_CURANDERO_MEDIA = 0.25
MAX_CURANDEROS_MEDIA = 1
PROPORCION_TIRADORES_ALTA = 0.4
PROPORCION_CURANDEROS_ALTA = 0.2
PROB_CURANDERO_EXTRA_ALTA = 0.3  # chance de un segundo curandero
MAX_CURANDEROS_ALTA = 2
MIN_CURANDEROS_FINAL_ALTA = 1
MIN_TIRADORES_FINAL_ALTA = 2
