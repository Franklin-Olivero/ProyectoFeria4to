"""Clasificador de reportes de toxicidad (lógica de fondo de la mazmorra).

Flujo:
    reportes (list[dict]) -> construir_arbol_reportes() -> ArbolDecision
    ArbolDecision -> calcular_nivel_toxicidad() -> float 0.0-100.0
    nivel -> nivel_a_dificultad() -> {"cantidad_enemigos", "multiplicador_velocidad"}

El jugador nunca ve el árbol: solo ve el resultado (más o menos
enemigos, más o menos rápidos). Este módulo no importa pygame, así que
se puede probar de forma aislada.
"""

from src.structures.tree import ArbolDecision

ID_RAIZ_ZONA = "zona"

GRAVEDAD_MINIMA = 1
GRAVEDAD_MAXIMA = 5

# Límites superiores (exclusivos) de los tramos bajo y medio; todo lo
# que esté en o por encima de LIMITE_TRAMO_MEDIO es tramo alto.
LIMITE_TRAMO_BAJO = 34.0
LIMITE_TRAMO_MEDIO = 67.0

DIFICULTAD_BAJA = {"cantidad_enemigos": 2, "multiplicador_velocidad": 0.8}
DIFICULTAD_MEDIA = {"cantidad_enemigos": 3, "multiplicador_velocidad": 1.0}
DIFICULTAD_ALTA = {"cantidad_enemigos": 5, "multiplicador_velocidad": 1.3}


def construir_arbol_reportes(reportes, nombre_zona="Zona"):
    """Arma un ArbolDecision a partir de una lista de reportes.

    Cada reporte es un dict {"id", "tipo", "gravedad"} con gravedad
    entera entre 1 y 5. La raíz (id ID_RAIZ_ZONA) representa la
    zona/edificio y cada reporte se inserta como hijo directo de la raíz;
    la etiqueta de cada nodo reporte es una copia del propio dict.

    Lanza ValueError si una gravedad está fuera de rango o si dos
    reportes comparten id (lo detecta ArbolDecision.insertar).

    Complejidad: O(r^2) con r reportes, porque cada insertar() hace una
    búsqueda O(n) en el árbol (n crece hasta r + 1). Para los pocos
    reportes de una zona esto es despreciable.
    """
    arbol = ArbolDecision(ID_RAIZ_ZONA, nombre_zona)
    for reporte in reportes:
        gravedad = reporte["gravedad"]
        if not GRAVEDAD_MINIMA <= gravedad <= GRAVEDAD_MAXIMA:
            raise ValueError(
                f"Gravedad {gravedad!r} fuera de rango "
                f"[{GRAVEDAD_MINIMA}, {GRAVEDAD_MAXIMA}] en reporte {reporte['id']!r}."
            )
        arbol.insertar(ID_RAIZ_ZONA, reporte["id"], dict(reporte))
    return arbol


def calcular_nivel_toxicidad(arbol):
    """Promedia la gravedad de todos los nodos reporte y la escala a 0-100.

    Usa el recorrido por niveles (BFS) del árbol: cada etiqueta que sea
    un dict es un reporte; la raíz (nombre de la zona) se ignora. El
    promedio de gravedad (1-5) se lleva linealmente a 0.0-100.0:
    gravedad promedio 1 -> 0.0, gravedad promedio 5 -> 100.0.
    Un árbol sin reportes (o vacío) devuelve 0.0.

    Complejidad: O(n), con n el número de nodos del árbol. El recorrido
    por niveles visita cada nodo exactamente una vez (O(n)) y luego se
    suman las gravedades en una sola pasada sobre esa lista (O(n)).
    Memoria extra: O(n) por la lista que devuelve el recorrido.
    """
    reportes = [etiqueta for etiqueta in arbol.por_niveles() if isinstance(etiqueta, dict)]
    if not reportes:
        return 0.0
    promedio = sum(reporte["gravedad"] for reporte in reportes) / len(reportes)
    return (promedio - GRAVEDAD_MINIMA) / (GRAVEDAD_MAXIMA - GRAVEDAD_MINIMA) * 100.0


def nivel_a_dificultad(nivel):
    """Traduce un nivel de toxicidad (0-100) a parámetros de spawn.

    Tramos:
        bajo  : nivel < 34       -> 2 enemigos, velocidad x0.8
        medio : 34 <= nivel < 67 -> 3 enemigos, velocidad x1.0
        alto  : nivel >= 67      -> 5 enemigos, velocidad x1.3

    Retorna un dict nuevo {"cantidad_enemigos", "multiplicador_velocidad"}.
    Complejidad: O(1).
    """
    if nivel < LIMITE_TRAMO_BAJO:
        return dict(DIFICULTAD_BAJA)
    if nivel < LIMITE_TRAMO_MEDIO:
        return dict(DIFICULTAD_MEDIA)
    return dict(DIFICULTAD_ALTA)


def enemigos_para_equipo(dificultad, nivel_toxicidad, cantidad_jugadores):
    """La dificultad de un cuarto con más enemigos si juegan varios (2 a 4,
    cooperativo u Online), en proporción a su toxicidad.

    Cada jugador además del primero suma round(fracción) enemigos, con la
    fracción de EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD (toxicidad 0) a
    EXTRA_ENEMIGOS_JUGADOR_TOXICIDAD_MAXIMA (toxicidad 100). Tope:
    MAX_ENEMIGOS_CUARTO (el cuarto no se satura). Un cuarto sin enemigos (la
    entrada) sigue sin enemigos y con 1 jugador nada cambia. Solo cambia la
    cantidad: la velocidad y los tipos siguen saliendo de la toxicidad.

        toxicidad   1 jugador  2   3   4
        baja (20)       2      3   3   4
        media (50)      3      4   4   5
        alta (90)       5      6   7   8

    Retorna un dict nuevo. O(1)."""
    from src.core.balance import (
        EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD, EXTRA_ENEMIGOS_JUGADOR_TOXICIDAD_MAXIMA, MAX_ENEMIGOS_CUARTO,
    )
    resultado = dict(dificultad)
    base = resultado.get("cantidad_enemigos", 0)
    otros = max(0, int(cantidad_jugadores) - 1)
    if base <= 0 or otros == 0:
        return resultado
    toxicidad = max(0.0, min(100.0, float(nivel_toxicidad)))
    fraccion = EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD + (
        EXTRA_ENEMIGOS_JUGADOR_TOXICIDAD_MAXIMA - EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD) * toxicidad / 100.0
    extra = int(otros * fraccion + 0.5)  # redondeo hacia arriba en .5 (round de Python redondea a par)
    resultado["cantidad_enemigos"] = max(base, min(base + extra, MAX_ENEMIGOS_CUARTO))
    return resultado


def vida_por_toxicidad(vida_base, nivel_toxicidad):
    """Vida de un enemigo que aparece en un cuarto con `nivel_toxicidad`:
    `vida_base` (la de su tipo o variante) por un multiplicador lineal de
    VIDA_ENEMIGO_MULT_SIN_TOXICIDAD (toxicidad 0) a
    VIDA_ENEMIGO_MULT_TOXICIDAD_MAXIMA (toxicidad 100), redondeado (.5 hacia
    arriba) y nunca menos que `vida_base`.

        vida base   tox 15   tox 50   tox 85   tox 100
            2          3        4        5        5
            3          5        6        7        8
            5          8       10       12       13

    O(1)."""
    from src.core.balance import VIDA_ENEMIGO_MULT_SIN_TOXICIDAD, VIDA_ENEMIGO_MULT_TOXICIDAD_MAXIMA
    toxicidad = max(0.0, min(100.0, float(nivel_toxicidad)))
    multiplicador = VIDA_ENEMIGO_MULT_SIN_TOXICIDAD + (
        VIDA_ENEMIGO_MULT_TOXICIDAD_MAXIMA - VIDA_ENEMIGO_MULT_SIN_TOXICIDAD) * toxicidad / 100.0
    return max(vida_base, int(vida_base * multiplicador + 0.5))


def reforzar_con_toxicidad(enemigo, nivel_toxicidad):
    """Le pone a `enemigo` (recién creado, con la vida de su tipo) la vida que
    le toca por la toxicidad. Devuelve el mismo enemigo."""
    enemigo.vida_maxima = vida_por_toxicidad(enemigo.vida_maxima, nivel_toxicidad)
    enemigo.vida = enemigo.vida_maxima
    return enemigo
