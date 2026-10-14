"""Punto de entrada del juego.

El flujo de la partida es una máquina de estados explícita (Escena,
src/core/escenas.py):

    MAPA_CIUDAD --(ENTER en una zona)--> MAZMORRA --(cuarto final limpio)--> DECISION
    DECISION --(resultado)--> RESULTADO --(ENTER)--> MAPA_CIUDAD
    MAPA_CIUDAD --(ENTER en Alcaldía, si está desbloqueada)--> JEFE --(jefe muere)--> VICTORIA
    VICTORIA --(ENTER)--> MAPA_CIUDAD           VICTORIA --(ESC)--> salir
    cualquiera --(colapso al 100%)--> DERROTA --(ENTER)--> partida nueva en MAPA_CIUDAD

El combate (MAZMORRA y JEFE) usa el mismo loop: la mazmorra de varios
cuartos y la arena del jefe exponen rect, enemigos, actualizar,
dibujar y manejar_evento. Solo el cuarto final de una mazmorra normal
tiene minijuego de decisión.

Presentación: el HUD superior y la barra de controles (src/ui/hud.py)
se dibujan directo a la pantalla; el mundo se dibuja en un lienzo que
se copia con la sacudida del jefe. Los efectos de combate (cono de
apuntado, objetivo, números de daño, globo del behavior tree con Tab)
viven en src/ui/combate_render.py.
"""

import sys

import pygame

from src.core import assets
from src.core.balance import CLICK_DISPARA
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.core.equipo import registrar_kill_equipo
from src.core.escenas import ESCENAS_DE_COMBATE, Escena, escena_tras_colapso
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO
from src.dungeon.grafo_ciudad import ZONA_FINAL, ZONAS
from src.dungeon.mazmorra import Mazmorra
from src.dungeon.mazmorra_final import VICTORIA as MAZMORRA_FINAL_GANADA
from src.dungeon.mazmorra_jugable import MazmorraJugable
from src.dungeon.partida import Partida
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import ANGULO_ABANICO_GRADOS, Ciudadano
from src.ui import combate_render, dibujo, hud
from src.ui.combate_render import TextosFlotantes
from src.ui.mapa_ciudad import SelectorZona
from src.ui.mapa_ciudad_render import dibujar_mapa_ciudad
from src.ui.mapa_render import dibujar_minimapa
from src.ui.pantalla_derrota import dibujar_derrota
from src.ui.pantalla_resultado import ResultadoMazmorra, dibujar_resultado
from src.ui.pantalla_victoria import dibujar_victoria
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA
from src.ui.terminal_decision_render import dibujar_terminal

TECLA_DISPARAR = pygame.K_SPACE
TECLA_HABILIDAD = pygame.K_f
TECLA_MINIMAPA = pygame.K_m
TECLA_ARBOL = pygame.K_TAB
TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE

# Teclas de la pantalla de selección -> clase del rol a instanciar.
ROLES_POR_TECLA = {
    pygame.K_1: Ciudadano,
    pygame.K_2: Influencer,
    pygame.K_3: Periodista,
    pygame.K_4: Candidato,
}

# Teclas de la terminal de decisión -> dirección de navegación.
TECLAS_TERMINAL = {
    pygame.K_LEFT: IZQUIERDA,
    pygame.K_RIGHT: DERECHA,
    pygame.K_RETURN: CONFIRMAR,
    pygame.K_KP_ENTER: CONFIRMAR,
}

# Teclas del mapa de la ciudad -> dirección para cambiar de zona.
TECLAS_MAPA = {
    pygame.K_LEFT: IZQUIERDA,
    pygame.K_RIGHT: DERECHA,
}

TITULO_MAPA = "Mapa de la ciudad"


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    partida = Partida()
    clase_rol = _elegir_rol(pantalla, reloj)
    if clase_rol is None:
        pygame.quit()
        sys.exit()
    jugador = clase_rol(0, 0)
    # Todos los jugadores de la partida (por ahora solo uno); se usa para
    # repartir la carga compartida de equipo en cada kill.
    jugadores = [jugador]
    selector = _nuevo_selector(partida)

    escena = Escena.MAPA_CIUDAD
    mazmorra = None  # MazmorraJugable de la zona que se está recorriendo
    arena = None
    mostrar_minimapa = True
    mostrar_arbol = False  # Tab: globo con el nodo activo del behavior tree
    resultado = None  # ResultadoMazmorra que muestra la escena RESULTADO
    # Mensaje central del mapa: (texto, color) del último resultado o "Bloqueada".
    mensaje_mapa = None
    tiempo_mensaje_mapa = 0.0
    # Se dibuja el mundo aquí y se copia a la pantalla con la sacudida;
    # el HUD va directo a la pantalla para que no tiemble.
    # Profundidad 24 (sin canal alfa) a propósito: en macOS la ventana es
    # 32 bits con máscara alfa, y un lienzo que la herede deja alfa 0 en
    # cada píxel donde se blitea un sprite o piso con transparencia
    # (SRCALPHA); al copiarlo a la ventana esos píxeles se ven negros.
    lienzo = pygame.Surface(pantalla.get_size(), 0, 24)
    # Desplazamiento con el que se dibujó el mundo en el último frame: el
    # mouse está en coordenadas de pantalla y se le resta para apuntar.
    sacudida = (0, 0)
    textos = TextosFlotantes()

    proyectiles_jugador = []
    proyectiles_enemigos = []

    ejecutando = True
    while ejecutando:
        dt = reloj.tick(FPS) / 1000
        tiempo_mensaje_mapa = max(0.0, tiempo_mensaje_mapa - dt)
        # Mouse: solo en combate y con un rol que apunta con él (no el
        # Candidato). Ahí se oculta el cursor del sistema y se dibuja la mira.
        apuntando = _apunta_con_mouse(escena, jugador)
        pygame.mouse.set_visible(not apuntando)
        if apuntando:
            _apuntar_con_mouse(jugador, sacudida)  # la habilidad (F) sale hacia el mouse

        # --- Input, según la escena ------------------------------------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type != pygame.KEYDOWN:
                continue
            elif escena == Escena.MAPA_CIUDAD:
                if evento.key in TECLAS_MAPA:
                    selector.mover(TECLAS_MAPA[evento.key])
                elif evento.key in TECLAS_CONFIRMAR:
                    destino = selector.seleccionada
                    if destino == ZONA_FINAL and not partida.alcaldia_desbloqueada():
                        mensaje_mapa = (f"{ZONA_FINAL}: Bloqueada", assets.COLOR_MENSAJE_DERROTA)
                        tiempo_mensaje_mapa = assets.DURACION_MENSAJE_MAPA
                        continue
                    partida.viajar(destino)
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                    textos.limpiar()
                    _curar(jugador)
                    if destino == ZONA_FINAL:
                        arena = ArenaJefe(partida.colapso, jugador)
                        escena = Escena.JEFE
                    elif partida.ciudad.tiene_mazmorra_normal(destino):
                        mazmorra = MazmorraJugable(
                            Mazmorra(partida.ciudad.reportes(destino), destino)
                        )
                        mazmorra.colocar_en_entrada(jugador)
                        escena = Escena.MAZMORRA
                    # La Plaza no tiene mazmorra: solo se viaja hasta ella.
            elif escena == Escena.DECISION:
                if evento.key in TECLAS_TERMINAL:
                    mazmorra.cuarto.terminal.navegar(TECLAS_TERMINAL[evento.key])
            elif escena == Escena.RESULTADO:
                if evento.key in TECLAS_CONFIRMAR:
                    resultado = None
                    escena = Escena.MAPA_CIUDAD
            elif escena in (Escena.VICTORIA, Escena.DERROTA):
                if evento.key in TECLAS_CONFIRMAR:
                    if escena == Escena.DERROTA:
                        # Partida completa nueva, con el mismo rol.
                        partida.reiniciar()
                        jugador = type(jugador)(0, 0)
                        jugadores = [jugador]
                        selector = _nuevo_selector(partida)
                        mensaje_mapa = None
                    arena = None
                    mazmorra = None
                    escena = Escena.MAPA_CIUDAD
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                    textos.limpiar()
                elif evento.key == TECLA_SALIR:
                    ejecutando = False
            elif evento.key == TECLA_HABILIDAD:
                if jugador.puede_usar_habilidad():
                    escenario = _escenario_activo(escena, arena, mazmorra)
                    jugador.usar_habilidad(escenario.enemigos, proyectiles_jugador)
            elif evento.key == TECLA_MINIMAPA and escena == Escena.MAZMORRA:
                mostrar_minimapa = not mostrar_minimapa
            elif evento.key == TECLA_ARBOL and escena in ESCENAS_DE_COMBATE:
                mostrar_arbol = not mostrar_arbol
            else:
                _escenario_activo(escena, arena, mazmorra).manejar_evento(evento)

        # --- Actualización, según la escena ----------------------------
        escenario = _escenario_activo(escena, arena, mazmorra)
        jugador.actualizar_habilidad(dt)
        textos.actualizar(dt)

        if escena in ESCENAS_DE_COMBATE:
            _frame_de_combate(
                dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos,
                textos, sacudida,
            )
            if escena == Escena.MAZMORRA:
                if mazmorra.cambio_de_cuarto:
                    proyectiles_jugador.clear()
                    textos.limpiar()
                if mazmorra.cuarto.fase == FASE_DECISION:
                    escena = Escena.DECISION
            elif escena == Escena.JEFE and arena.mazmorra.estado == MAZMORRA_FINAL_GANADA:
                escena = Escena.VICTORIA
        elif escena == Escena.DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            proyectiles_jugador.clear()
            proyectiles_enemigos.clear()
            terminal = mazmorra.cuarto.terminal
            terminal.actualizar(dt)
            if terminal.resultado is not None:
                # Única vía para aplicar la decisión: una vez por mazmorra.
                colapso_antes = partida.colapso.valor
                partida.cerrar_mazmorra(mazmorra.mazmorra, terminal.resultado)
                mazmorra.cuarto.fase = FASE_RESUELTO
                resultado = ResultadoMazmorra(
                    terminal.resultado, terminal.opcion_elegida,
                    colapso_antes, partida.colapso.valor, mazmorra.mazmorra.nombre_zona,
                )
                mazmorra = None
                mensaje_mapa = (
                    f"{partida.ubicacion}: {terminal.resultado}",
                    assets.COLOR_TEAL if resultado.exito else assets.COLOR_MAGENTA,
                )
                tiempo_mensaje_mapa = assets.DURACION_MENSAJE_MAPA
                escena = Escena.RESULTADO
        # RESULTADO, VICTORIA y DERROTA: el mundo queda quieto hasta ENTER o ESC.

        # La pantalla de resultado se muestra completa antes de la derrota global.
        if escena not in (Escena.DERROTA, Escena.RESULTADO):
            escena = escena_tras_colapso(escena, partida.colapso)

        # --- Dibujo ----------------------------------------------------
        pantalla.fill(assets.COLOR_FONDO)
        if escena in (Escena.MAPA_CIUDAD, Escena.DERROTA):
            dibujar_mapa_ciudad(pantalla, partida, selector.seleccionada)
            hud.dibujar_hud_superior(
                pantalla, jugador, None, TITULO_MAPA,
                f"Ubicación: {partida.ubicacion}  ·  Mazmorras completadas: {partida.progreso.mazmorras_completadas}",
                partida.colapso,
            )
            if tiempo_mensaje_mapa > 0 and mensaje_mapa is not None and escena == Escena.MAPA_CIUDAD:
                _dibujar_mensaje(pantalla, mensaje_mapa[0], mensaje_mapa[1], assets.POSICION_MENSAJE_MAPA)
            if escena == Escena.DERROTA:
                dibujar_derrota(pantalla)
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL)
            else:
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_MAPA)
            pygame.display.flip()
            sacudida = (0, 0)
            continue

        if escena == Escena.DECISION:
            dibujar_terminal(
                pantalla, mazmorra.cuarto.terminal,
                f"Cuarto final  ·  {mazmorra.mazmorra.nombre_zona}  ·  Mazmorra normal",
            )
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_TERMINAL)
            pygame.display.flip()
            sacudida = (0, 0)
            continue

        if escena == Escena.RESULTADO:
            dibujar_resultado(pantalla, resultado)
            pygame.display.flip()
            sacudida = (0, 0)
            continue

        escenario = _escenario_activo(escena, arena, mazmorra)
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        objetivo = None
        if escena in ESCENAS_DE_COMBATE:
            angulo = ANGULO_ABANICO_GRADOS if isinstance(jugador, Ciudadano) else assets.ANGULO_CONO_ESTRECHO
            if jugador.apunta_con_mouse:
                combate_render.dibujar_cono_apuntado(lienzo, jugador, angulo)
                objetivo = combate_render.enemigo_apuntado(jugador, escenario.enemigos)
                if objetivo is not None:
                    combate_render.dibujar_objetivo(lienzo, jugador, objetivo)
        jugador.dibujar(lienzo)
        for proyectil in proyectiles_jugador:
            proyectil.dibujar(lienzo)
        for proyectil in proyectiles_enemigos:
            proyectil.dibujar(lienzo)
        textos.dibujar(lienzo)
        if mostrar_arbol and escena in ESCENAS_DE_COMBATE:
            enemigo_globo = objetivo or _enemigo_mas_cercano(jugador, escenario.enemigos)
            if enemigo_globo is not None:
                combate_render.dibujar_globo_arbol(lienzo, enemigo_globo)
        sacudida = arena.mazmorra.desplazamiento_sacudida() if escena == Escena.JEFE else (0, 0)
        pantalla.blit(lienzo, sacudida)

        if escena in (Escena.JEFE, Escena.VICTORIA):
            hud.dibujar_hud_superior(pantalla, jugador, len(escenario.enemigos), None, None, partida.colapso)
            arena.dibujar_hud(pantalla)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL if escena == Escena.VICTORIA else hud.CONTROLES_JEFE)
        else:
            titulo, subtitulo = _titulo_mazmorra(mazmorra)
            hud.dibujar_hud_superior(pantalla, jugador, len(escenario.enemigos), titulo, subtitulo, partida.colapso)
            if mazmorra.mensaje is not None:
                _dibujar_mensaje(pantalla, mazmorra.mensaje[0], assets.COLOR_MENSAJE_MAZMORRA,
                                 assets.POSICION_MENSAJE_MAZMORRA)
            if mostrar_minimapa:
                dibujar_minimapa(pantalla, mazmorra.mazmorra)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_COMBATE)
        if escena == Escena.VICTORIA:
            dibujar_victoria(pantalla)
        if _apunta_con_mouse(escena, jugador):
            combate_render.dibujar_mira(pantalla, jugador, sacudida)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _frame_de_combate(
    dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos, textos,
    sacudida=(0, 0),
):
    """Un frame de combate, igual en la mazmorra y en la arena."""
    jugador.actualizar_invulnerabilidad(dt)
    teclas = pygame.key.get_pressed()
    jugador.manejar_movimiento(teclas, dt, escenario.rect)
    # Se re-apunta tras moverse, para que el disparo salga desde la
    # posición nueva hacia el mouse.
    if jugador.apunta_con_mouse:
        _apuntar_con_mouse(jugador, sacudida)
    # Disparo sostenido: el jugador decide cuántos volleys salen según
    # su cooldown (cadencia del rol + buff por kill). SPACE o click izquierdo.
    disparando = teclas[TECLA_DISPARAR] or (CLICK_DISPARA and pygame.mouse.get_pressed()[0])
    proyectiles_jugador.extend(jugador.actualizar_disparo(dt, disparando))
    escenario.actualizar(dt, jugador, proyectiles_enemigos)

    _actualizar_proyectiles(proyectiles_jugador, dt, escenario.rect)
    _actualizar_proyectiles(proyectiles_enemigos, dt, escenario.rect)

    _resolver_colisiones_contra_enemigos(
        proyectiles_jugador, escenario.enemigos, jugador, jugadores, textos
    )
    _resolver_colision_contra_jugador(proyectiles_enemigos, jugador, textos)


def _apunta_con_mouse(escena, jugador):
    return escena in ESCENAS_DE_COMBATE and jugador.apunta_con_mouse


def _apuntar_con_mouse(jugador, sacudida):
    """Orienta al jugador hacia el mouse. El mundo se dibuja desplazado
    por la sacudida, así que el punto se pasa a coordenadas del mundo
    restándola. Sin foco de ventana se conserva la dirección anterior."""
    if not pygame.mouse.get_focused():
        return
    x, y = pygame.mouse.get_pos()
    jugador.apuntar_a((x - sacudida[0], y - sacudida[1]))


def _escenario_activo(escena, arena, mazmorra):
    """Lugar físico activo: la arena mientras dure la pelea final; si no,
    la mazmorra normal (None en el mapa)."""
    return arena if escena in (Escena.JEFE, Escena.VICTORIA) else mazmorra


def _enemigo_mas_cercano(jugador, enemigos):
    vivos = [enemigo for enemigo in enemigos if enemigo.vivo]
    if not vivos:
        return None
    centro = pygame.Vector2(jugador.rect.center)
    return min(vivos, key=lambda enemigo: centro.distance_squared_to(enemigo.rect.center))


def _nuevo_selector(partida):
    """Selector del mapa apuntando a la primera zona después de la ubicación."""
    selector = SelectorZona(ZONAS, partida.ubicacion)
    selector.mover(DERECHA)
    return selector


def _curar(jugador):
    """Cada mazmorra (normal o final) se empieza con la vida llena."""
    jugador.vida = jugador.vida_maxima
    jugador.invulnerabilidad.reiniciar()


def _elegir_rol(pantalla, reloj):
    """Pantalla previa al loop: espera 1-4 y retorna la clase elegida
    (None si se cierra la ventana)."""
    clases_rol = list(ROLES_POR_TECLA.values())
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN and evento.key in ROLES_POR_TECLA:
                return ROLES_POR_TECLA[evento.key]

        dibujar_seleccion(pantalla, clases_rol)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_SELECCION)
        pygame.display.flip()
        reloj.tick(FPS)


def _titulo_mazmorra(mazmorra):
    """Título y subtítulo del HUD en una mazmorra normal: la zona y en
    qué cuarto se está ("Cuarto 2 de 6 · Limpios 1/6")."""
    m = mazmorra.mazmorra
    cuartos = sorted(m.grafo.nodos())
    numero = cuartos.index(m.actual) + 1
    limpios, total = m.cuartos_limpios()
    subtitulo = f"Cuarto {numero} de {len(cuartos)}  ·  Limpios {limpios}/{total}"
    if m.actual == m.cuarto_final:
        subtitulo += "  ·  Cuarto final"
    return f"{m.nombre_zona} infectado", subtitulo


def _dibujar_mensaje(pantalla, cadena, color, centro):
    dibujo.chip(pantalla, cadena, centro, color, assets.COLOR_FONDO_PANEL, color,
                assets.TAMANIO_FUENTE_MEDIA, ancla="center", alto=36, margen=16)


def _actualizar_proyectiles(proyectiles, dt, limites):
    for proyectil in proyectiles:
        proyectil.actualizar(dt, limites)
    proyectiles[:] = [proyectil for proyectil in proyectiles if proyectil.vivo]


def _resolver_colisiones_contra_enemigos(proyectiles, enemigos, jugador, jugadores, textos):
    """Delega cada choque en `proyectil.al_impactar(enemigo)`, que cada
    tipo de proyectil del rol define (destruirse, perforar, empujar,
    área...). Cada enemigo que muere da la kill completa a `jugador` y
    carga compartida al resto de `jugadores` (ver src/core/equipo.py).
    Cada punto de daño que entra se muestra como número flotante."""
    for proyectil in proyectiles:
        for enemigo in enemigos:
            if not proyectil.vivo:
                break
            if enemigo.vivo and proyectil.colisiona_con(enemigo.rect):
                vida_antes = enemigo.vida
                proyectil.al_impactar(enemigo)
                if enemigo.vida < vida_antes:
                    textos.agregar(f"-{vida_antes - enemigo.vida:g}", (enemigo.rect.centerx, enemigo.rect.top - 12))
                if not enemigo.vivo:
                    registrar_kill_equipo(jugador, jugadores)


def _resolver_colision_contra_jugador(proyectiles, jugador, textos):
    """Un proyectil hostil que toca al jugador se consume siempre; si el
    jugador está invulnerable, recibir_dano() no le resta vida."""
    for proyectil in proyectiles:
        if proyectil.colisiona_con(jugador.rect):
            vida_antes = jugador.vida
            jugador.recibir_dano(proyectil.danio)
            proyectil.vivo = False
            if jugador.vida < vida_antes:
                textos.agregar(f"-{vida_antes - jugador.vida:g}", (jugador.rect.centerx, jugador.rect.top - 16),
                               assets.COLOR_MAGENTA)


if __name__ == "__main__":
    main()
