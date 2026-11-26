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
    ("Carga", "carga_maxima"),
]
# En estas, menos es mejor (menos kills para llenar la habilidad): su
# barra es el mínimo entre los roles dividido por el valor del rol.
ESTADISTICAS_INVERSAS = ("carga_maxima",)
# Escala de la tarjeta del lobby: cada estadística se muestra de 1 a 10
# (src/core/puntajes_roles.py) entre el mínimo y el máximo de los 4 roles,
# así se aprovecha toda la escala. Los valores reales de STATS_POR_ROL no
# cambian: es solo cómo se muestran.
PUNTAJE_MINIMO, PUNTAJE_MAXIMO = 1, 10
RANGOS_STATS = {
    atributo: (min(getattr(s, atributo) for s in STATS_POR_ROL.values()),
               max(getattr(s, atributo) for s in STATS_POR_ROL.values()))
    for _, atributo in ESTADISTICAS_VISIBLES
}


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
    def fraccion(stats, atributo):
        valores = [getattr(otro, atributo) for otro in STATS_POR_ROL.values()]
        if atributo in ESTADISTICAS_INVERSAS:
            return min(valores) / getattr(stats, atributo)
        return getattr(stats, atributo) / max(valores)

    return {
        rol: {atributo: fraccion(stats, atributo) for _, atributo in ESTADISTICAS_VISIBLES}
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

# Peso base de cada calle = su largo real. Las calles son los tramos de
# src/dungeon/ciudad_mapa.py (la rueda: la Plaza al centro unida a 4
# cruces y un anillo exterior frente a los 4 edificios; ninguna arista es
# puente y cada edificio tiene dos rutas). Cada casilla mide
# METROS_POR_CASILLA y cada METROS_POR_PUNTO_DE_PESO metros suman 1 de
# peso, redondeando al entero más cercano: una calle de 12 casillas
# (60 m) pesa 3 y una de 23 casillas (115 m) pesa 6. Sobre ese peso base
# actúan la saturación (+3 / -2) y las barricadas (8 / 6).
# Ejemplo de Dijkstra: Plaza -> Colegio por el Cruce Norte cuesta 3 + 3 = 6;
# por el Cruce Oeste, 6 + 6 = 12 (es el doble de largo).
METROS_POR_CASILLA = 5
METROS_POR_PUNTO_DE_PESO = 20
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
# mazmorra final y no usa reportes). Los capítulos van del más fácil al
# más difícil. Gravedad promedio -> nivel:
#   Cap. 1 Colegio 1.6 -> 15.0 (tramo bajo), Cap. 2 Hospital 3.0 -> 50.0 (medio),
#   Cap. 3 Empresa de Medios 4.4 -> 85.0 (alto), Cap. 4 Alcaldía: 100 (NIVEL_TOXICIDAD_FINAL).
REPORTES_POR_ZONA = {
    ZONA_COLEGIO: [
        {"id": 1, "tipo": "comentario", "gravedad": 1},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 2},
        {"id": 3, "tipo": "comentario", "gravedad": 1},
        {"id": 4, "tipo": "denuncia", "gravedad": 2},
        {"id": 5, "tipo": "comentario", "gravedad": 2},
    ],
    ZONA_HOSPITAL: [
        {"id": 1, "tipo": "comentario", "gravedad": 2},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 4},
        {"id": 3, "tipo": "denuncia", "gravedad": 3},
        {"id": 4, "tipo": "comentario", "gravedad": 3},
    ],
    ZONA_EMPRESA_MEDIOS: [
        {"id": 1, "tipo": "comentario", "gravedad": 4},
        {"id": 2, "tipo": "publicacion_viral", "gravedad": 5},
        {"id": 3, "tipo": "denuncia", "gravedad": 5},
        {"id": 4, "tipo": "comentario", "gravedad": 3},
        {"id": 5, "tipo": "publicacion_viral", "gravedad": 5},
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

# Variantes: cada personaje de assets/sprites/enemigos/variantes es un tipo de
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

# Más jugadores, más enemigos (cooperativo local y Online, de 2 a 4):
# cada jugador además del primero suma a cada cuarto con enemigos una fracción
# de enemigo que crece con la toxicidad del cuarto (0.4 a toxicidad 0, 1.0 a
# toxicidad 100), redondeado. Ningún cuarto pasa de MAX_ENEMIGOS_CUARTO: caben
# 10 bien separados (src/dungeon/spawn.py), así que no se satura.
# (enemigos_para_equipo en src/dungeon/clasificador_toxicidad.py)
EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD = 0.4
EXTRA_ENEMIGOS_JUGADOR_TOXICIDAD_MAXIMA = 1.0
MAX_ENEMIGOS_CUARTO = 8

# Vida de los enemigos según la toxicidad del cuarto donde aparecen
# (vida_por_toxicidad en src/dungeon/clasificador_toxicidad.py): la vida
# del tipo/variante por un multiplicador que va de x1.5 (toxicidad 0) a
# x2.5 (toxicidad 100), redondeado. Vale para los cuartos de las mazmorras
# y los súbditos del jefe (toxicidad 100). El jefe no cambia (VIDA_JEFE).
VIDA_ENEMIGO_MULT_SIN_TOXICIDAD = 1.5
VIDA_ENEMIGO_MULT_TOXICIDAD_MAXIMA = 2.5

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

# ----------------------------------------------------------------------
# Modo historia "Código Nova" (src/story/)
# ----------------------------------------------------------------------
# Indicadores de Ciudad Nova (enteros 0-100). Los cuatro primeros y
# participacion_responsable son "buenos"; desinformacion y conflictos
# son "malos". El Colapso Electoral sigue siendo la barra de derrota:
# cada Detonación suma colapso y además mueve estos indicadores según
# la consecuencia elegida (content/campaign.json); nunca al revés.
INDICADORES_INICIALES = {
    "informacion_verificada": 40,
    "confianza": 50,
    "convivencia": 55,
    "bienestar_digital": 50,
    "participacion_responsable": 45,
    "desinformacion": 45,
    "conflictos": 30,
}
INDICADOR_MINIMO = 0
INDICADOR_MAXIMO = 100
# Reputación individual (src/story/reputacion.py): de -100 a +100, por jugador.
REPUTACION_INICIAL = 0
REPUTACION_MINIMA = -100
REPUTACION_MAXIMA = 100
# (id, nombre visible, valor mínimo del tramo), de mayor a menor.
NIVELES_REPUTACION = (
    ("referente", "Referente de Ciudad Nova", 60),
    ("confiable", "Ciudadano confiable", 20),
    ("neutral", "Reputación neutral", -19),
    ("cuestionada", "Reputación cuestionada", -59),
    ("crisis", "Crisis de reputación", -100),
)
UMBRAL_CRISIS_REPUTACION = -60  # a este valor o menos se activa la crisis
UMBRAL_DESCONFIANZA = -20  # las pruebas parciales ya no bastan: la ciudad pide más
UMBRAL_CONFIANZA = 20  # un ciudadano aporta una prueba al entrar a cada zona
UMBRAL_REFERENTE = 60  # más alcance de las correcciones y más tiempo en la terminal
TIEMPO_EXTRA_TERMINAL_REFERENTE = 10.0  # s
# Saltos de una corrección publicada según la reputación de quien la publica
# (la credibilidad decide hasta dónde llega por el grafo social).
SALTOS_CORRECCION_REFERENTE = 4
SALTOS_CORRECCION_CUESTIONADA = 2
SALTOS_CORRECCION_CRISIS = 1
# Valoración de cada acción: (sin saber, con indicios, sabiéndolo) según la
# veracidad REAL de la publicación. Los valores dependen de lo que el
# jugador podía saber: equivocarse no pesa igual que manipular.
VALORACION_ACCIONES = {
    # Compartir la publicación tal cual.
    "compartir": {"enganosa": (-12, -20, -30), "veraz": (4, 8, 15)},
    # Dar "me gusta": el algoritmo la muestra a más gente, como un compartir más
    # suave (la mitad de su peso, en los dos sentidos). Ante una engañosa resta
    # más que ignorarla: aunque no la reenvíes, la amplificas.
    "me_gusta": {"enganosa": (-6, -10, -15), "veraz": (2, 4, 8)},
    # Publicar información comprobada (aclaración o dato verificado).
    "publicar_verificado": {"enganosa": (-4, 8, 20), "veraz": (-2, 6, 15)},
    # Reportar la publicación como falsa o engañosa.
    "reportar": {"enganosa": (-2, 8, 25), "veraz": (-10, -15, -20)},
    # Denunciar a quienes atacan una publicación verdadera.
    "denunciar_ataque": {"enganosa": (-6, -8, -10), "veraz": (-2, 10, 20)},
    # Linchamiento: reportes en masa, bloqueos, acusar sin pruebas.
    "linchar": {"enganosa": (-10, -12, -15), "veraz": (-15, -20, -25)},
    # Afirmar de más: "es 100 % falso" o creer sin comprobar.
    "afirmar_sin_matiz": {"enganosa": (-8, -10, -12), "veraz": (-10, -14, -18)},
    # Seguir difundiendo después de revisarla.
    "insistir": {"enganosa": (-15, -22, -35), "veraz": (-2, -2, -2)},
    # No actuar: no siempre es malo (no amplificar lo que no se pudo comprobar).
    "ignorar": {"enganosa": (0, -3, -8), "veraz": (-2, -5, -10)},
    # Se acabó el reloj.
    "no_decidir": {"enganosa": (-3, -4, -6), "veraz": (-3, -5, -8)},
}
# La gravedad del daño posible escala solo las penalizaciones.
MULTIPLICADOR_GRAVEDAD = {"baja": 0.75, "media": 1.0, "alta": 1.25}
# El alcance real en el grafo social ajusta el cambio (BFS, no un número fijo).
PENALIZACION_POR_AFECTADO = 1
PENALIZACION_MAXIMA_ALCANCE = 5
AFECTADOS_POR_PUNTO_BONO = 3
BONO_MAXIMO_ALCANCE = 3
# Redención (src/story/redencion.py)
RECUPERACION_REDENCION = 45  # reputación que devuelve la misión completa
TOPE_REPUTACION_TRAS_REDENCION = 59  # la huella queda: no se vuelve a ser "referente"
EFECTOS_REDENCION = {"desinformacion": -10, "confianza": 8, "informacion_verificada": 5, "convivencia": 4}
EFECTOS_RECHAZO_REDENCION = {"confianza": -12, "desinformacion": 8, "conflictos": 6}
OPORTUNIDADES_REDENCION = 3  # errores permitidos por intento de la misión
REINTENTOS_REDENCION = 1  # veces que la misión se puede reintentar antes de fallar
PUBLICACIONES_REDENCION = 2  # correcciones que se pueden publicar en la etapa 2
COBERTURA_REDENCION = 0.75  # fracción de los expuestos que debe recibir la corrección
SALTOS_CORRECCION_REDENCION = 2
REPUTACION_MIN_FINAL_POSITIVO = -19  # "renace" y "arquitecto" exigen no estar cuestionado
# Terminal de decisión: hay que leer la publicación y las pruebas, así que el
# reloj presiona sin impedir la lectura.
DURACION_TERMINAL_HISTORIA = 45.0  # s
# Modo Online: al abrirse la terminal, el impostor queda bloqueado un tiempo
# que el host sortea entre estos dos valores (cada terminal el suyo). Mientras
# tanto el resto busca la respuesta correcta; después el impostor elige
# normal, sin límite de movimientos. Con los dos iguales, el bloqueo es fijo.
COOLDOWN_SABOTAJE_MIN = 10.0  # s
COOLDOWN_SABOTAJE_MAX = 15.0  # s
# Modo Online: reunión de emergencia (Online/reunion.py). El botón REPORTAR
# se puede usar cada COOLDOWN_REUNION segundos (cuenta desde que arranca la
# partida y desde que termina cada reunión). En la reunión el equipo tiene
# DURACION_REUNION segundos para hablar y votar; solo cuentan los votos emitidos.
COOLDOWN_REUNION = 60.0  # s
DURACION_REUNION = 60.0  # s
DURACION_RESULTADO_REUNION = 6.0  # s que todos ven a quién expulsaron
MAX_MENSAJES_REUNION = 14  # mensajes del chat que guarda el host (y manda en el ESTADO)
MAX_LARGO_MENSAJE_REUNION = 80  # caracteres por mensaje
# Fin de la partida Online por votación: expulsar al impostor la gana la
# tripulación; si expulsan inocentes hasta que quedan solo el impostor y uno
# más (con 2 jugadores: solo el impostor), gana el impostor.
JUGADORES_MINIMOS_VICTORIA_IMPOSTOR = 2
# Modo Online: botón SABOTEAR del impostor (Online/post_sabotaje.py). A todos
# les salta una publicación falsa y tienen poco tiempo para frenarla
# (Verificar o Reportar); el impostor puede elegir recién tras su bloqueo.
COOLDOWN_POST_SABOTAJE = 75.0  # s entre sabotajes (también al empezar la partida)
DURACION_POST_SABOTAJE = 20.0  # s para elegir
BLOQUEO_POST_SABOTAJE = 5.0  # s en que el impostor todavía no puede elegir
DURACION_RESULTADO_POST_SABOTAJE = 4.0  # s que todos ven cómo terminó
EFECTOS_POST_SABOTAJE_VIRAL = {"desinformacion": 6, "confianza": -3}  # y la barra de colapso, como una incursión fallida
EFECTOS_POST_SABOTAJE_FRENADO = {"informacion_verificada": 2, "desinformacion": -2}
# Evidencia por zona: con esta fracción de las pruebas reveladas el
# estado pasa de "sin pruebas" a "parcial"; con todas, a "verificado" o
# "desmentido" según el veredicto real de la publicación.
# Finales (src/story/eleccion.py). Umbrales sobre los indicadores
# finales; el final "arquitecto" exige además las 3 pistas, haber rastreado
# el origen de la señal en el capítulo 3 y el jefe derrotado.
FINAL_RENACE_VERIFICADA_MIN = 55
FINAL_RENACE_CONFIANZA_MIN = 50
FINAL_RENACE_DESINFORMACION_MAX = 45
PISTAS_PARA_FINAL_SECRETO = 3
# Elecciones simuladas: cuánto pesa cada indicador afín en el apoyo de
# un candidato (ver content/campaign.json, "afin").
PESO_INDICADOR_AFIN_ELECCION = 0.5
PESO_REPUTACION_ELECCION = 0.1  # sobre la reputación colectiva (-100 a +100)
# Grafo social (src/story/red_social.py)
SALTOS_MAXIMOS_PROPAGACION = 3
PROBABILIDAD_REBOTE_BASE = 0.7  # chance de que un contacto reenvíe una publicación
PROBABILIDAD_REBOTE_CORREGIDA = 0.25  # tras una corrección publicada
# Matices narrativos por rol (un solo modificador pequeño por rol; el
# combate no cambia):
#   influencer: amplifica más al compartir (rebote extra en la propagación);
#   ciudadano: cada éxito refuerza la confianza vecinal;
#   periodista: identifica una fuente extra al entrar a una zona;
#   candidato: mayor cuidado reputacional (las penalizaciones pesan ×1.5).
REBOTE_EXTRA_INFLUENCER = 0.15
CONFIANZA_EXTRA_CIUDADANO = 2
EVIDENCIA_INICIAL_PERIODISTA = 1
MULTIPLICADOR_PENALIZACION_CANDIDATO = 1.5
# Efecto del alcance de una publicación sobre los indicadores: cada
# ciudadano que recibe un rumor sin corrección suma desinformación; cada
# dos que reciben la corrección suman información verificada.
DESINFORMACION_POR_ALCANZADO = 1
BIENESTAR_POR_ALCANZADO = -0.5
VERIFICADA_POR_CORREGIDO = 0.5
EVENTOS_RECIENTES_CINTILLO = 2  # titulares de eventos aleatorios que quedan en el cintillo
# Investigación del origen de la señal, capítulo 3 (src/story/investigacion.py):
# reputación y puntos según a qué tipo de cuenta se señale.
PUNTOS_ORIGEN_RASTREADO = 150
REPUTACION_POR_TIPO_CUENTA = {"origen": 15, "amplificador": 0, "error": -10, "victima": -20}
# Jefe derrotado / derrotas en la arena (efectos narrativos, una vez)
EFECTOS_JEFE_DERROTADO = {"desinformacion": -10, "confianza": 6, "bienestar_digital": 6}
PUNTOS_JEFE_DERROTADO = 200

# ----------------------------------------------------------------------
# Mezcla de audio (src/audio/gestor_audio.py). Volumen final de un sonido =
# preferencia del jugador (música o efectos) * VOLUMEN_CATEGORIA *
# GANANCIA_SONIDO[id] (o GANANCIA_MUSICA[id]). Las ganancias igualan
# el volumen percibido sin editar los archivos: se calcularon para dejar
# cada efecto cerca de -19 dB RMS y cada pista cerca de -18 dB RMS (el
# pack Bitcade viene normalizado a -1 dBFS y suena ~6 dB más fuerte que
# el audio propio). Nunca pasan de 1.0: nada se amplifica ni satura.
# Los sonidos que se repiten mucho (disparos e impactos) van 40 % más
# bajos para no tapar la música.
# ----------------------------------------------------------------------
VOLUMEN_CATEGORIA = {"musica": 0.85, "sfx": 1.0, "ui": 0.8, "cinematica": 1.0}
GANANCIA_SONIDO = {
    "disparo_ciudadano": 0.45,
    "disparo_influencer": 0.26,
    "disparo_periodista": 0.29,
    "disparo_candidato": 0.23,
    "habilidad_ciudadano": 0.59,
    "habilidad_influencer": 0.67,
    "habilidad_periodista": 0.44,
    "habilidad_candidato": 0.28,
    "habilidad_lista": 0.50,
    "dash": 0.43,
    "jugador_herido": 0.46,
    "impacto_enemigo": 0.27,
    "muerte_perseguidor": 0.40,
    "muerte_tirador": 0.59,
    "muerte_curandero": 0.40,
    "disparo_tirador": 0.49,
    "curacion": 0.67,
    "jefe_rafaga": 0.50,
    "jefe_fase": 0.63,
    "jefe_escudo_roto": 0.58,
    "jefe_derrotado": 0.63,
    "puerta": 0.37,
    "impacto_cobertura": 0.20,
    "cobertura_rota": 0.50,
    "puerta_sellada": 0.32,
    "cuarto_liberado": 0.53,
    "cuarto_final_desbloqueado": 0.42,
    "gracia_entrada": 0.48,
    "transicion": 0.79,
    "barricada": 0.37,
    "ruta": 0.48,
    "noticia": 1.00,
    "tick": 0.27,
    "decision_buena": 0.54,
    "decision_mala": 0.63,
    "error_decision": 0.32,
    "navegar": 0.27,
    "confirmar": 0.48,
    "volver": 0.26,
    "notificacion": 1.00,
    "evidencia": 0.50,
    "mision": 0.53,
    "reputacion_sube": 0.64,
    "reputacion_baja": 0.81,
    "victoria": 0.54,
    "derrota": 0.35,
    "crisis": 0.71,
    "redencion": 0.86,
    "glitch": 0.70,
    "viral": 0.84,
}
GANANCIA_MUSICA = {
    "menu": 0.68,
    "lobby": 0.62,
    "ciudad": 1.00,
    "combate": 0.88,
    "jefe": 1.00,
    "misterio": 0.75,
    "decision": 0.61,
    "crisis": 0.92,
    "redencion": 0.76,
    "victoria": 0.91,
    "derrota": 0.89,
    "prologo_umbral": 1.00,  # ya mezclada (~-22 dB RMS con voces): no se atenúa
}
# Anti-spam: un mismo sonido suena a lo sumo MAX_SIMULTANEOS_SONIDO
# veces a la vez y nunca dos veces en menos de INTERVALO_MINIMO_SONIDO s
# (p. ej. los 3 proyectiles del abanico del Ciudadano o 5 enemigos que
# mueren en el mismo frame suenan una vez).
MAX_SIMULTANEOS_SONIDO = 3
INTERVALO_MINIMO_SONIDO = 0.05
# Duración máxima esperada de un efecto (tests/test_audio.py). Los IDs
# de LARGOS_PERMITIDOS (habilidades, jefe, jingles, transiciones de la
# historia) pueden durar más; ningún efecto pasa de DURACION_MAXIMA_LARGO.
DURACION_MAXIMA_SFX = 1.5
DURACION_MAXIMA_LARGO = 3.2
LARGOS_PERMITIDOS = (
    "habilidad_ciudadano", "habilidad_influencer", "jefe_fase", "jefe_derrotado", "cuarto_liberado",
    "decision_buena", "decision_mala", "victoria", "derrota", "crisis", "redencion",
)
# Últimos segundos de la terminal de decisión en que suena el tic de reloj.
SEGUNDOS_TIC_TERMINAL = 5
# Paso de las teclas - / + para el volumen general en el lobby (porcentaje).
PASO_VOLUMEN_LOBBY = 10

# ----------------------------------------------------------------------
# Pausa (src/core/pausa.py). En partida individual el mundo se congela
# de verdad; con 2+ jugadores (locales u online) el menú se abre pero el
# juego sigue, para no detener a los demás. Si algún día se quiere que
# la pausa congele también en multijugador, basta poner esto en True.
# ----------------------------------------------------------------------
PUEDE_PAUSAR_MULTIJUGADOR = False
FACTOR_MUSICA_PAUSA = 0.35  # la música baja a este factor mientras dura la pausa
DURACION_ATENUACION_PAUSA = 0.4  # s del fundido de la música al pausar / reanudar

# ----------------------------------------------------------------------
# Decoración de Ciudad Nova (src/dungeon/layout_decoracion.py). Todo se
# coloca por reglas sobre el mapa, con una semilla fija: la ciudad es
# siempre la misma y se puede probar.
# ----------------------------------------------------------------------
ESPACIADO_FAROLAS = 6  # casillas entre dos farolas seguidas de una misma acera
MARGEN_FAROLAS_CRUCE = 3  # casillas desde el inicio de un tramo hasta su primera farola
ESPACIADO_ARBOLES_AVENIDA = 3  # casillas entre árboles de la hilera del camellón de la Avenida Nova
ESPACIADO_MOBILIARIO_ACERA = 12  # casillas entre papeleras, canteros, buzones o hidrantes
ARBOLES_PARQUE = 10  # árboles agrupados en el césped de cada parque
# Jardines ('J'): árboles en grupos naturales. Centros de grupo a
# SEPARACION_GRUPOS_ARBOLES casillas o más entre sí; en cada grupo, de
# ARBOLES_POR_GRUPO[0] a [1] árboles a RADIO_GRUPO_ARBOLES del centro y a
# SEPARACION_ARBOLES_JARDIN o más entre ellos. Arbustos en el borde de los
# canteros cada ESPACIADO_ARBUSTOS casillas.
SEPARACION_GRUPOS_ARBOLES = 5
RADIO_GRUPO_ARBOLES = 2
ARBOLES_POR_GRUPO = (2, 4)
SEPARACION_ARBOLES_JARDIN = 2
ESPACIADO_ARBUSTOS = 3
ALTO_COPA_CASILLAS = 3  # casillas que sube la copa: un árbol nunca va tan cerca bajo una fachada
SEPARACION_ARBOLES_PARQUE = 2  # casillas mínimas entre dos árboles del parque (Chebyshev)
SEMILLA_DECORACION = 404
# Paleta de Ciudad Nova (src/core/medicion_paleta.py, tools/medir_paleta_ciudad.py):
# la ciudad es sobria; el neón saturado queda para carteles, puertas,
# ventanas puntuales y la línea amarilla de la calzada.
UMBRAL_SATURACION_ALTA = 0.50  # saturación (0-1) desde la que un píxel cuenta como neón...
UMBRAL_BRILLO_SATURADO = 0.35  # ...si además es así de brillante
UMBRAL_SATURACION_COLOR = 0.22  # bajo esto el píxel es neutro (grises y azul-gris nocturno)
FRACCION_FAMILIA_DOMINANTE = 0.04  # una familia de color domina si pasa este % de píxeles
MAX_FRACCION_SATURADA_CIUDAD = 0.08  # tope de neón en la panorámica
MAX_FAMILIAS_DOMINANTES_CIUDAD = 4  # neutro + verde + pocas más
# Verde: al menos esta fracción del área no vial (sin calles ni edificios) es vegetación.
MIN_FRACCION_VERDE_CIUDAD = 0.45
# Cámara de la ciudad: encuadra un poco más arriba del jugador (las
# fachadas miran al sur: frente a una puerta se ve el edificio entero).
ADELANTO_CAMARA_CIUDAD = 72  # px

# ----------------------------------------------------------------------
# Instrucciones antes de cada mazmorra (src/ui/instrucciones.py)
# ----------------------------------------------------------------------
RETARDO_INSTRUCCIONES = 0.4  # s antes de aceptar "comenzar" (un Enter de más no la salta)
TARJETAS_POR_PAGINA_INSTRUCCIONES = 4  # con más, ← → pasan de página


# ----------------------------------------------------------------------
# Coberturas rompibles (src/dungeon/coberturas.py, navegacion_cuarto.py)
# ----------------------------------------------------------------------
# Los muebles de una mazmorra son sólidos: frenan a jugadores, enemigos y
# balas (de cualquiera), y cada bala que reciben les quita vida hasta que
# se rompen. Así cubrirse sirve, pero no para siempre.
# La hitbox es la base del objeto (vista 3/4): la parte de arriba de la
# imagen es altura, y un personaje puede pasar por detrás de ella.
FRACCION_HITBOX_COBERTURA = 0.6  # de la altura de la imagen, desde abajo
MARGEN_LATERAL_HITBOX_COBERTURA = 4  # px que se recortan a cada lado
# Un mueble cuya base queda a menos de esto del muro de arriba está contra
# la pared: su hitbox sube hasta el muro (nadie cabe detrás de un estante).
MARGEN_MURO_COBERTURA = 72  # = PASO_MINIMO_COBERTURA: detrás no cabría un enemigo
# Vida por clase de objeto (en puntos de daño: una bala enemiga quita 1).
VIDA_COBERTURA = {"fragil": 4, "media": 8, "resistente": 14}
CLASE_COBERTURA_PREDETERMINADA = "media"
CLASE_COBERTURA = {
    # Livianos: sillas, plantas, trípodes.
    "globo": "fragil", "esqueleto": "fragil", "suero": "fragil", "microfono": "fragil",
    "aro_luz": "fragil", "softbox": "fragil", "camara": "fragil", "cordon": "fragil",
    "bandera": "fragil", "lampara": "fragil", "planta": "fragil", "ficus": "fragil",
    "palmera": "fragil", "pack:silla": "fragil", "silla_oficina": "fragil",
    "silla_ruedas": "fragil", "oxigeno": "fragil", "dispensador": "fragil",
    "monitor": "fragil", "pizarra_movil": "fragil", "biombo": "fragil", "urna": "fragil",
    "pack:pupitre": "fragil",
    # Macizos: estanterías, gabinetes, racks, piedra.
    "estanteria": "resistente", "gabinete": "resistente", "rack": "resistente",
    "columna": "resistente", "bloque_glitch": "resistente", "archivador": "resistente",
    "pack:casillero": "resistente", "pack:estante": "resistente", "maletas": "resistente",
    "busto": "resistente", "mesa_consejo": "resistente", "mesa_noticias": "resistente",
}
# Objetos chicos del piso que siguen siendo solo decoración (sin hitbox).
OBJETOS_SIN_HITBOX = ("libros", "cables", "pack:mochila", "pack:maceta")
# Etapas de daño: por debajo de cada fracción de vida el objeto se ve más roto.
FRACCIONES_ETAPA_COBERTURA = (2 / 3, 1 / 3)
DURACION_GOLPE_COBERTURA = 0.18  # s que tiembla y destella tras un impacto
# Entre dos coberturas del centro del cuarto (y entre ellas y lo demás)
# queda al menos este paso: cabe el enemigo más ancho (64 px).
PASO_MINIMO_COBERTURA = 72
# Y ningún hueco queda "a medias": o es más angosto que esto (no entra ni
# el jugador, de 36 px) o mide PASO_MINIMO_COBERTURA o más (entran todos).
# Así no existe un rincón donde el jugador quepa y los enemigos no.
HUECO_CERRADO_COBERTURA = 30
# Navegación de los enemigos: el piso se cuadricula en celdas y cada celda
# libre es un nodo del grafo; BFS desde el jugador da el rodeo más corto.
ESQUINA_COBERTURA = 16  # px: un enemigo enganchado menos que esto en un canto se corre y pasa
NAV_CELDA = 24  # px por celda
NAV_HOLGURA = 22  # px que se le suma a cada cobertura (medio enemigo típico)
NAV_PASOS_VISTA = 6  # celdas del camino que se intentan saltar en línea recta
NAV_MAX_RUTAS = 12  # BFS guardados (uno por celda de jugador reciente)

# Burbuja Comunitaria del Ciudadano (src/entities/burbuja.py): frena los
# proyectiles enemigos que entran al domo y cura a los aliados de adentro.
CURACION_BURBUJA_POR_S = 0.5  # vida por segundo (en 4 s de burbuja: 2 de vida)
