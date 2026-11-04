"""Integración del modo historia con la mazmorra jugable (pygame.Rect, sin ventana).

Recorre el flujo del Colegio como lo hace Main.py: entrar, limpiar los
cuartos (una evidencia por cuarto), abrir la terminal del cuarto final
con el árbol del escenario y cerrar la mazmorra una sola vez con la
consecuencia aplicada. También comprueba que el árbol fijo original
sigue siendo el de un cuarto sin fábrica (compatibilidad).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import DURACION_TERMINAL_HISTORIA, REPORTES_POR_ZONA, ZONA_COLEGIO  # noqa: E402
from src.dungeon.cuarto import FASE_DECISION, Cuarto  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.mazmorra_jugable import MazmorraJugable  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.story.escenarios import DESMENTIDO  # noqa: E402
from src.ui.pantalla_resultado import ResultadoMazmorra  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR, PURIFICACION_EXITOSA  # noqa: E402


def _entrar_al_colegio(partida, semilla=3):
    mazmorra = MazmorraJugable(
        Mazmorra(REPORTES_POR_ZONA[ZONA_COLEGIO], ZONA_COLEGIO, semilla=semilla),
        fabrica_arbol=partida.fabrica_arbol(ZONA_COLEGIO),
        duracion_terminal=DURACION_TERMINAL_HISTORIA,
    )
    jugador = Ciudadano(0, 0)
    mazmorra.colocar_en_entrada([jugador])
    return mazmorra, jugador


def _limpiar_cuarto_actual(mazmorra, jugador):
    """Mata a todos los enemigos del cuarto actual y corre un frame."""
    mazmorra.gracia.restante = 0.0
    while mazmorra.cuarto.enemigos:
        mazmorra.cuarto.eliminar_un_enemigo()
    mazmorra.actualizar(1 / 60, [jugador], [])


def _ir_a(mazmorra, jugador, destino):
    """Mueve por el grafo hasta `destino` tocando puertas abiertas (sin
    pasar por el cuarto final sellado, que nunca es punto de corte)."""
    m = mazmorra.mazmorra
    grafo = m.grafo
    if destino != m.cuarto_final:
        grafo = grafo.copia()
        grafo.eliminar_nodo(m.cuarto_final)
    camino = grafo.bfs(m.actual)[2]
    ruta = grafo.camino(camino, m.actual, destino)
    for siguiente in ruta[1:]:
        _limpiar_cuarto_actual(mazmorra, jugador)
        direccion = next(d for d, v in mazmorra.mazmorra.puertas(mazmorra.mazmorra.actual).items() if v == siguiente)
        puerta = mazmorra.cuarto.puertas[direccion]
        jugador.rect.center = puerta.rect.center
        jugador.posicion.update(jugador.rect.center)
        mazmorra.actualizar(1 / 60, [jugador], [])
        assert mazmorra.mazmorra.actual == siguiente, f"no cruzó a {siguiente}"


def test_flujo_del_colegio_revela_evidencia_y_cierra_una_vez():
    partida = Partida()
    campania = partida.campania
    mazmorra, jugador = _entrar_al_colegio(partida)
    m = mazmorra.mazmorra
    limpios_vistos = len(m.limpiados)

    # Como Main.py: cada cuarto limpio nuevo revela una evidencia.
    def revisar_evidencia():
        nonlocal limpios_vistos
        if len(m.limpiados) > limpios_vistos:
            limpios_vistos = len(m.limpiados)
            return campania.revelar_evidencia(ZONA_COLEGIO)
        return None

    reveladas = []
    for cuarto in m.grafo.nodos():
        if cuarto in (m.entrada, m.cuarto_final):
            continue
        _ir_a(mazmorra, jugador, cuarto)
        _limpiar_cuarto_actual(mazmorra, jugador)
        evidencia = revisar_evidencia()
        if evidencia is not None:
            reveladas.append(evidencia["id"])
    assert reveladas == ["col_e1", "col_e2", "col_e3"]  # 4 cuartos intermedios, 3 pruebas
    assert campania.pistas == ["col_e3"]
    assert campania.estado_evidencia(ZONA_COLEGIO) == DESMENTIDO
    assert m.final_desbloqueado()

    _ir_a(mazmorra, jugador, m.cuarto_final)
    _limpiar_cuarto_actual(mazmorra, jugador)
    assert mazmorra.cuarto.fase == FASE_DECISION
    terminal = mazmorra.cuarto.terminal
    assert terminal.duracion == DURACION_TERMINAL_HISTORIA
    assert terminal.arbol.raiz.etiqueta == "¿Cierran todos los colegios?"
    assert campania.zona_activa == ZONA_COLEGIO and campania.escenario_activo.estado == DESMENTIDO

    for _ in range(3):
        terminal.navegar(CONFIRMAR)  # Verificar -> Publicar aclaración -> hoja
    assert terminal.resultado == PURIFICACION_EXITOSA
    colapso_antes = partida.colapso.valor
    assert partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    resultado = ResultadoMazmorra(terminal.resultado, terminal.opcion_elegida, colapso_antes, partida.colapso.valor,
                                  ZONA_COLEGIO, campania.ultima_consecuencia, dict(campania.ultimos_deltas))
    assert resultado.exito and "comunicado" in resultado.explicacion
    assert resultado.deltas["informacion_verificada"] == 12
    assert partida.progreso.mazmorras_completadas == 1
    assert campania.puntos == 120
    # Segundo cierre (p. ej. un frame repetido): nada se aplica dos veces.
    assert not partida.cerrar_mazmorra(m, terminal.resultado, terminal)
    assert campania.puntos == 120 and partida.progreso.mazmorras_completadas == 1


def test_cuarto_sin_fabrica_usa_el_arbol_original():
    cuarto = Cuarto(direcciones_puertas=("N",), nivel_toxicidad=10.0, es_final=True)
    while cuarto.enemigos:
        cuarto.eliminar_un_enemigo()
    cuarto.actualizar(1 / 60, [Ciudadano(0, 0)], [])
    assert cuarto.fase == FASE_DECISION
    assert cuarto.terminal.arbol.raiz.etiqueta == "Publicación Viral"
    assert cuarto.terminal.duracion == 10.0
