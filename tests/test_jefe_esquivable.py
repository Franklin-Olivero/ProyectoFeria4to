"""Regla de diseño: todo patrón del jefe es esquivable (sin pygame).

Se simulan las balas del jefe como datos (x, y, dx, dy, velocidad),
igual que las mueve la arena, con el jefe fijo en el centro de la arena
real. Cada 0.1 s se mira qué balas cruzan bandas de radio 120, 180 y
240 px (±12 px) y se calcula el pasillo libre más ancho de cada banda.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    CHARCO_DISTANCIA_MIN_JUGADOR,
    CHARCO_MAXIMO_ACTIVOS,
    CHARCO_RADIO,
    FASE3_CICLO,
    FASE3_DESCANSO,
    JEFE_ESPIRAL_BRAZOS,
    JEFE_RADIAL_BALAS,
    JEFE_RADIAL_HUECO,
    JEFE_RADIAL_SEPARACION_HUECO,
    MAX_PROYECTILES_JEFE,
    PAUSA_CAMBIO_FASE,
)
from src.entities.jefe import Jefe, SalidaJefe, distancia_angular  # noqa: E402

# Arena real: rect de ANCHO_ARENA x ALTO_ARENA centrado en CENTRO_ARENA.
CX, CY = assets.CENTRO_ARENA
LIMITES = (
    CX - assets.ANCHO_ARENA / 2,
    CY - assets.ALTO_ARENA / 2,
    CX + assets.ANCHO_ARENA / 2,
    CY + assets.ALTO_ARENA / 2,
)
DT = 1 / 60
MUESTREO = 6  # frames: cada 0.1 s
BANDAS = (120, 180, 240)
TOLERANCIA_BANDA = 12
ANCHO_JUGADOR = assets.TAMANIO_JUGADOR
ANCHO_BALA = assets.TAMANIO_PROYECTIL_JEFE
PASILLO_MINIMO = 3 * ANCHO_JUGADOR
VIDA_POR_FASE = {1: 1.0, 2: 0.5, 3: 0.25}
PASO_RADIAL = 360 / JEFE_RADIAL_BALAS


def jefe_en_fase(fase, semilla=0):
    jefe = Jefe(CX, CY, LIMITES, random.Random(semilla))
    jefe.vida = jefe.vida_maxima * VIDA_POR_FASE[fase]
    return jefe


def simular(fase, segundos, objetivo=lambda t: (CX, LIMITES[3] - 40), semilla=0,
            al_muestrear=None, al_frame=None):
    """Corre el jefe `segundos` en `fase` con la arena real. Retorna el
    máximo de balas vivas a la vez."""
    jefe = jefe_en_fase(fase, semilla)
    balas = []
    maximo = 0
    for frame in range(int(segundos / DT)):
        t = frame * DT
        salida = SalidaJefe()
        jefe.actualizar(DT, objetivo(t), salida, len(balas))
        jefe.x, jefe.y = CX, CY  # fijo en el centro
        for d in salida.disparos:
            balas.append([d.x, d.y, d.dx, d.dy, d.velocidad])
        maximo = max(maximo, len(balas))
        for bala in balas:
            bala[0] += bala[2] * bala[4] * DT
            bala[1] += bala[3] * bala[4] * DT
        izquierda, arriba, derecha, abajo = LIMITES
        balas = [b for b in balas if izquierda <= b[0] <= derecha and arriba <= b[1] <= abajo]
        if al_frame is not None:
            al_frame(jefe, salida, t)
        if al_muestrear is not None and frame % MUESTREO == 0:
            al_muestrear(balas, t)
    return maximo


def mayor_pasillo(balas, radio):
    """Arco libre más largo (en px) sobre la circunferencia de `radio`.

    Cada bala de la banda ocupa (ancho bala + ancho jugador) de arco
    centrado en su ángulo; las zonas del círculo donde el jugador no
    cabe dentro de la arena (muros) también cuentan como ocupadas.
    """
    ocupados = []
    medio = (ANCHO_BALA + ANCHO_JUGADOR) / 2 / radio
    for x, y, *_ in balas:
        if abs(math.hypot(x - CX, y - CY) - radio) <= TOLERANCIA_BANDA:
            angulo = math.atan2(y - CY, x - CX)
            ocupados.append((angulo - medio, angulo + medio))
    medio_alto = (LIMITES[3] - LIMITES[1]) / 2 - ANCHO_JUGADOR / 2
    medio_ancho = (LIMITES[2] - LIMITES[0]) / 2 - ANCHO_JUGADOR / 2
    if radio > medio_alto:  # muros de arriba y abajo
        h = math.acos(medio_alto / radio)
        ocupados += [(math.pi / 2 - h, math.pi / 2 + h), (-math.pi / 2 - h, -math.pi / 2 + h)]
    if radio > medio_ancho:  # muros laterales
        h = math.acos(medio_ancho / radio)
        ocupados += [(-h, h), (math.pi - h, math.pi + h)]
    if not ocupados:
        return 2 * math.pi * radio

    # Normalizar a [0, 2π), partiendo los que cruzan el 0, y unir.
    tramos = []
    for a, b in ocupados:
        a, b = a % (2 * math.pi), a % (2 * math.pi) + (b - a)
        if b > 2 * math.pi:
            tramos += [(a, 2 * math.pi), (0.0, b - 2 * math.pi)]
        else:
            tramos.append((a, b))
    tramos.sort()
    unidos = [list(tramos[0])]
    for a, b in tramos[1:]:
        if a <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], b)
        else:
            unidos.append([a, b])
    huecos = [unidos[i + 1][0] - unidos[i][1] for i in range(len(unidos) - 1)]
    huecos.append(2 * math.pi - unidos[-1][1] + unidos[0][0])  # el que da la vuelta
    return max(huecos) * radio


# ----------------------------------------------------------------------
# Ráfaga radial con hueco
# ----------------------------------------------------------------------


def indices_de(disparos):
    return {round(math.degrees(math.atan2(d.dy, d.dx)) / PASO_RADIAL) % JEFE_RADIAL_BALAS
            for d in disparos}


def test_rafaga_tiene_hueco_consecutivo_que_salta_mas_de_60_grados():
    rafagas = []

    def registrar(jefe, salida, t):
        if len(salida.disparos) == JEFE_RADIAL_BALAS - JEFE_RADIAL_HUECO:
            rafagas.append((indices_de(salida.disparos), jefe.ultimo_hueco))

    total = 0
    for semilla in range(5):
        rafagas.clear()
        simular(1, 60, semilla=semilla, al_frame=registrar)
        total += len(rafagas)
        revisar_rafagas(rafagas)
    assert total > 100


def revisar_rafagas(rafagas):
    anterior = None
    for indices, centro_hueco in rafagas:
        faltantes = set(range(JEFE_RADIAL_BALAS)) - indices
        assert len(faltantes) == JEFE_RADIAL_HUECO
        # Consecutivas (circular): existe un inicio i con i, i+1, i+2 faltantes.
        assert any(
            {(i + k) % JEFE_RADIAL_BALAS for k in range(JEFE_RADIAL_HUECO)} == faltantes
            for i in faltantes
        )
        if anterior is not None:
            assert distancia_angular(anterior, centro_hueco) > JEFE_RADIAL_SEPARACION_HUECO
        anterior = centro_hueco


def test_hueco_nuevo_siempre_lejos_del_anterior():
    jefe = jefe_en_fase(1)
    for _ in range(500):
        previo = jefe.ultimo_hueco
        jefe.ultimo_hueco = jefe._centro_hueco(jefe.elegir_hueco())
        if previo is not None:
            assert distancia_angular(previo, jefe.ultimo_hueco) > JEFE_RADIAL_SEPARACION_HUECO


# ----------------------------------------------------------------------
# Pasillo esquivable en las 3 fases
# ----------------------------------------------------------------------


@pytest.mark.parametrize("fase", [1, 2, 3])
def test_siempre_hay_pasillo_de_tres_jugadores(fase):
    peores = {radio: math.inf for radio in BANDAS}

    def medir(balas, t):
        for radio in BANDAS:
            peores[radio] = min(peores[radio], mayor_pasillo(balas, radio))

    # El objetivo da vueltas: el disparo dirigido sale en todas direcciones.
    def objetivo(t):
        return (CX + 300 * math.cos(t), CY + 200 * math.sin(t))

    for semilla in range(3):
        simular(fase, 60, objetivo=objetivo, semilla=semilla, al_muestrear=medir)
    for radio, peor in peores.items():
        assert peor >= PASILLO_MINIMO, f"fase {fase}, radio {radio}: pasillo de {peor:.0f} px"


def test_mayor_pasillo_detecta_un_anillo_cerrado():
    """Control del propio test: un círculo completo de 16 balas no deja pasillo."""
    balas = [[CX + 120 * math.cos(math.radians(i * PASO_RADIAL)),
              CY + 120 * math.sin(math.radians(i * PASO_RADIAL)), 0, 0, 0]
             for i in range(JEFE_RADIAL_BALAS)]
    assert mayor_pasillo(balas, 120) < PASILLO_MINIMO


# ----------------------------------------------------------------------
# Tope de balas, espiral y descanso
# ----------------------------------------------------------------------


@pytest.mark.parametrize("fase", [1, 2, 3])
def test_nunca_mas_de_max_proyectiles(fase):
    assert simular(fase, 60) <= MAX_PROYECTILES_JEFE


def test_tope_lleno_omite_emitir():
    jefe = jefe_en_fase(2)
    jefe.actualizar(PAUSA_CAMBIO_FASE + DT, (CX, 500), SalidaJefe(), 0)
    salida = SalidaJefe()
    for _ in range(120):
        jefe.actualizar(DT, (CX, 500), salida, MAX_PROYECTILES_JEFE)
    assert salida.disparos == []


def test_espiral_maximo_dos_brazos_y_misma_velocidad_que_fase_1():
    velocidades = set()

    def registrar(jefe, salida, t):
        for d in salida.disparos:
            velocidades.add(d.velocidad)
        assert len(salida.disparos) <= JEFE_RADIAL_BALAS

    simular(1, 10, al_frame=registrar)
    rafaga = set(velocidades)
    velocidades.clear()
    simular(3, 20, objetivo=lambda t: (CX, CY), al_frame=registrar)  # sin dirigidos
    assert velocidades == rafaga  # la fase 3 no acelera balas
    assert JEFE_ESPIRAL_BRAZOS <= 2


def test_fase_3_tiene_descanso_sin_emisiones_en_cada_ciclo():
    emisiones = []

    def registrar(jefe, salida, t):
        if salida.disparos or salida.charcos:
            emisiones.append(t)

    simular(3, 60, al_frame=registrar)
    huecos = [b - a for a, b in zip(emisiones, emisiones[1:])]
    ciclos_completos = int((60 - PAUSA_CAMBIO_FASE) / FASE3_CICLO) - 1
    assert sum(h >= FASE3_DESCANSO - DT for h in huecos) >= ciclos_completos


def test_rafagas_y_dirigido_nunca_en_el_mismo_instante():
    def registrar(jefe, salida, t):
        velocidades = {d.velocidad for d in salida.disparos}
        assert len(velocidades) <= 1  # o anillo, o espiral, o dirigido

    simular(3, 60, objetivo=lambda t: (CX + 200, CY + 150), al_frame=registrar)


# ----------------------------------------------------------------------
# Charcos
# ----------------------------------------------------------------------


def test_charcos_lejos_del_jugador_fuera_del_jefe_y_maximo_dos():
    vivos = []

    def objetivo(t):
        return (CX + 330 * math.cos(t * 0.7), CY + 190 * math.sin(t * 1.3))

    def registrar(jefe, salida, t):
        for charco in vivos:
            charco.actualizar(DT)
        vivos[:] = [c for c in vivos if c.vivo]
        for charco in salida.charcos:
            jugador = objetivo(t)
            borde_al_jugador = math.dist((charco.x, charco.y), jugador) - CHARCO_RADIO
            assert borde_al_jugador >= CHARCO_DISTANCIA_MIN_JUGADOR
            assert math.dist((charco.x, charco.y), (CX, CY)) > CHARCO_RADIO + assets.TAMANIO_JEFE / 2
            vivos.append(charco)
        assert len(vivos) <= CHARCO_MAXIMO_ACTIVOS
        nacidos.extend(salida.charcos)

    nacidos = []
    for semilla in range(5):
        simular(3, 120, objetivo=objetivo, semilla=semilla, al_frame=registrar)
    assert len(nacidos) > 50
