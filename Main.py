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

Cooperativo local: si al empezar hay un control conectado, el J2 elige
rol con él (o Enter para jugar solo). Cada jugador tiene su lector de
input (src/core/entrada.py: teclado+mouse para J1, control para J2) y
su propia lista de proyectiles, así cada kill se acredita a quien la
hizo. Ambos comparten cuarto, enemigos y colapso.

Presentación: el HUD superior y la barra de controles (src/ui/hud.py)
se dibujan directo a la pantalla; el mundo se dibuja en un lienzo que
se copia con la sacudida del jefe. Los efectos de combate (cono de
apuntado, objetivo, números de daño, globo del behavior tree con Tab)
viven en src/ui/combate_render.py; el rastro del dash, en
src/ui/particulas.py.
"""

import sys

import pygame
from pygame._sdl2 import controller

from src.core import assets
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.core.entrada import EJE_MAXIMO, EntradaMando, EntradaTeclado
from src.core.equipo import jugadores_en_combate, registrar_kill_equipo, revivir_caidos
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
from src.ui.pantalla_modo import dibujar_modo
from src.ui.particulas import SistemaParticulas
from src.ui.seleccion import DOS_JUGADORES, UN_JUGADOR, SeleccionRoles, SelectorModo
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA
from src.ui.terminal_decision_render import dibujar_terminal

TECLA_MINIMAPA = pygame.K_m
TECLA_ARBOL = pygame.K_TAB
TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE

# Tarjetas de la pantalla de selección, en orden (tecla 1 = la primera).
CLASES_ROL = [Ciudadano, Influencer, Periodista, Candidato]
TECLAS_ROL = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
TECLAS_MODO = {pygame.K_1: UN_JUGADOR, pygame.K_2: DOS_JUGADORES}

# Menús: J1 con flechas o A/D, Enter o Espacio confirma, Retroceso se arrepiente.
TECLAS_MENU_J1 = {
    pygame.K_LEFT: IZQUIERDA, pygame.K_a: IZQUIERDA,
    pygame.K_RIGHT: DERECHA, pygame.K_d: DERECHA,
}
TECLAS_CONFIRMAR_MENU = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
TECLA_CANCELAR = pygame.K_BACKSPACE
# Menús: J2 con la cruceta (o el stick izquierdo), ✕ confirma, ○ se arrepiente.
BOTONES_MENU_J2 = {
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: IZQUIERDA,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: DERECHA,
}
BOTON_CONFIRMAR = pygame.CONTROLLER_BUTTON_A  # ✕
BOTON_CANCELAR = pygame.CONTROLLER_BUTTON_B  # ○
UMBRAL_STICK_MENU = 0.6  # fracción del eje: más inclinado = un paso en el menú

VOLVER = "volver"  # _elegir_roles: Esc, de vuelta a la pantalla de modo

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
    controller.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    partida = Partida()
    # Menú de inicio: 1 o 2 jugadores, y luego cada uno elige su rol.
    eleccion = _menu_inicio(pantalla, reloj, _primer_mando())
    if eleccion is None:
        pygame.quit()
        sys.exit()
    clases, mando = eleccion
    entradas = [EntradaTeclado()]
    if len(clases) > 1:
        entradas.append(EntradaMando(mando))
    # Todos los jugadores de la partida, en el mismo orden que `entradas`.
    # J1 (jugadores[0]) es el del teclado: su HUD va arriba, maneja la
    # terminal de decisión y apunta con la mira del mouse.
    jugadores = [clase(0, 0) for clase in clases]
    jugador = jugadores[0]
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
    particulas = SistemaParticulas()

    # Una lista de proyectiles por jugador (mismo orden que `jugadores`):
    # así cada kill se acredita a quien disparó.
    proyectiles_por_jugador = [[] for _ in jugadores]
    proyectiles_enemigos = []

    def limpiar_combate():
        """Descarta proyectiles, números flotantes y partículas en vuelo."""
        for proyectiles in proyectiles_por_jugador:
            proyectiles.clear()
        proyectiles_enemigos.clear()
        textos.limpiar()
        particulas.limpiar()

    ejecutando = True
    while ejecutando:
        # tick_busy_loop y no tick: en Windows tick() duerme con poca
        # precisión y los frames salen de 16, 17 o 18 ms, lo que se ve
        # como tirones al moverse. busy_loop da frames regulares.
        dt = reloj.tick_busy_loop(FPS) / 1000
        tiempo_mensaje_mapa = max(0.0, tiempo_mensaje_mapa - dt)
        # Mouse: solo en combate y con un rol que apunta con él (no el
        # Candidato). Ahí se oculta el cursor del sistema y se dibuja la mira.
        pygame.mouse.set_visible(not _apunta_con_mouse(escena, jugador))

        # --- Input, según la escena ------------------------------------
        # El combate (mover, apuntar, disparar, habilidad, dash) no usa
        # eventos: cada frame se lee el estado del teclado/control (ver
        # _frame_de_combate). Aquí solo van menús y teclas de interfaz.
        for evento in pygame.event.get():
            if len(entradas) > 1 and not entradas[1].mando.attached():
                # El control del J2 se desconectó: al volver a conectarlo, sigue jugando.
                entradas[1].mando = _actualizar_mando(evento, None) or entradas[1].mando
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
                    limpiar_combate()
                    _curar(jugadores)
                    if destino == ZONA_FINAL:
                        arena = ArenaJefe(partida.colapso, jugadores)
                        escena = Escena.JEFE
                    elif partida.ciudad.tiene_mazmorra_normal(destino):
                        mazmorra = MazmorraJugable(
                            Mazmorra(partida.ciudad.reportes(destino), destino)
                        )
                        mazmorra.colocar_en_entrada(jugadores)
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
                        # Partida completa nueva, con los mismos roles.
                        partida.reiniciar()
                        jugadores = [type(j)(0, 0) for j in jugadores]
                        jugador = jugadores[0]
                        selector = _nuevo_selector(partida)
                        mensaje_mapa = None
                    arena = None
                    mazmorra = None
                    escena = Escena.MAPA_CIUDAD
                    limpiar_combate()
                elif evento.key == TECLA_SALIR:
                    ejecutando = False
            elif evento.key == TECLA_MINIMAPA and escena == Escena.MAZMORRA:
                mostrar_minimapa = not mostrar_minimapa
            elif evento.key == TECLA_ARBOL and escena in ESCENAS_DE_COMBATE:
                mostrar_arbol = not mostrar_arbol
            else:
                _escenario_activo(escena, arena, mazmorra).manejar_evento(evento)

        # --- Actualización, según la escena ----------------------------
        escenario = _escenario_activo(escena, arena, mazmorra)
        for j in jugadores:
            j.actualizar_habilidad(dt)
        textos.actualizar(dt)
        particulas.actualizar(dt)

        if escena in ESCENAS_DE_COMBATE:
            _frame_de_combate(
                dt, jugadores, entradas, escenario, proyectiles_por_jugador, proyectiles_enemigos,
                textos, particulas, sacudida,
            )
            if escena == Escena.MAZMORRA:
                if mazmorra.cambio_de_cuarto:
                    limpiar_combate()
                    revivir_caidos(jugadores)  # cooperativo: el caído vuelve en el cuarto nuevo
                    for j in jugadores:
                        j.detener()  # se aparece quieto junto a la puerta
                if mazmorra.cuarto.fase == FASE_DECISION:
                    escena = Escena.DECISION
            elif escena == Escena.JEFE and arena.mazmorra.estado == MAZMORRA_FINAL_GANADA:
                escena = Escena.VICTORIA
        elif escena == Escena.DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            limpiar_combate()
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
        en_combate = jugadores_en_combate(jugadores)  # los caídos no se dibujan
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        particulas.dibujar(lienzo)  # el rastro del dash queda detrás de los jugadores
        objetivo = None
        if escena in ESCENAS_DE_COMBATE and jugador in en_combate:
            angulo = ANGULO_ABANICO_GRADOS if isinstance(jugador, Ciudadano) else assets.ANGULO_CONO_ESTRECHO
            if jugador.apunta_con_mouse:
                combate_render.dibujar_cono_apuntado(lienzo, jugador, angulo)
                objetivo = combate_render.enemigo_apuntado(jugador, escenario.enemigos)
                if objetivo is not None:
                    combate_render.dibujar_objetivo(lienzo, jugador, objetivo)
        for j in en_combate:
            j.dibujar(lienzo)
            if j is not jugador and j.apunta_con_mouse:
                combate_render.dibujar_indicador_apuntado(lienzo, j)  # J2 no tiene mira
        for proyectiles in proyectiles_por_jugador:
            for proyectil in proyectiles:
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

        # Solitario: el J1 va en el HUD superior. Cooperativo: arriba solo
        # el lugar, los enemigos y el colapso; cada jugador en su panel lateral.
        coop = len(jugadores) > 1
        jugador_hud, etiqueta_hud = (None, None) if coop else (jugador, "J1")
        if escena in (Escena.JEFE, Escena.VICTORIA):
            hud.dibujar_hud_superior(pantalla, jugador_hud, len(escenario.enemigos), None, None, partida.colapso,
                                     etiqueta_hud)
            arena.dibujar_hud(pantalla)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL if escena == Escena.VICTORIA else hud.CONTROLES_JEFE)
        else:
            titulo, subtitulo = _titulo_mazmorra(mazmorra)
            hud.dibujar_hud_superior(pantalla, jugador_hud, len(escenario.enemigos), titulo, subtitulo,
                                     partida.colapso, etiqueta_hud)
            if mazmorra.mensaje is not None:
                _dibujar_mensaje(pantalla, mazmorra.mensaje[0], assets.COLOR_MENSAJE_MAZMORRA,
                                 assets.POSICION_MENSAJE_MAZMORRA)
            if mostrar_minimapa:
                dibujar_minimapa(pantalla, mazmorra.mazmorra)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_COMBATE)
        if coop:
            for numero, j in enumerate(jugadores):
                hud.dibujar_panel_jugador(pantalla, j, numero)
        if escena == Escena.VICTORIA:
            dibujar_victoria(pantalla)
        if _apunta_con_mouse(escena, jugador) and jugador in en_combate:
            combate_render.dibujar_mira(pantalla, jugador, sacudida)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _frame_de_combate(
    dt, jugadores, entradas, escenario, proyectiles_por_jugador, proyectiles_enemigos, textos,
    particulas, sacudida=(0, 0),
):
    """Un frame de combate, igual en la mazmorra y en la arena, para 1 o 2 jugadores."""
    teclas = pygame.key.get_pressed()
    en_combate = jugadores_en_combate(jugadores)
    for jugador, entrada, proyectiles in zip(jugadores, entradas, proyectiles_por_jugador):
        jugador.actualizar_invulnerabilidad(dt)
        jugador.actualizar_dash(dt)
        # Se lee aunque esté caído, para que un botón mantenido no cuente
        # como "recién apretado" al revivir.
        pedido = _leer_entrada(entrada, teclas, sacudida)
        if jugador not in en_combate:
            continue
        # Mueve, apunta (mouse o stick) y arranca el dash si se pidió.
        jugador.manejar_input(pedido, dt, escenario.rect)
        if jugador.dash.activo:
            particulas.emitir(jugador.rect.center, jugador.COLOR)
        if pedido.habilidad:
            jugador.intentar_habilidad(escenario.enemigos, proyectiles)
        # Disparo sostenido: el jugador decide cuántos volleys salen según
        # su cooldown (cadencia del rol + buff por kill); nada durante el dash.
        proyectiles.extend(jugador.actualizar_disparo(dt, pedido.disparando))
    escenario.actualizar(dt, jugadores, proyectiles_enemigos)

    for proyectiles in proyectiles_por_jugador:
        _actualizar_proyectiles(proyectiles, dt, escenario.rect)
    _actualizar_proyectiles(proyectiles_enemigos, dt, escenario.rect)

    for jugador, proyectiles in zip(jugadores, proyectiles_por_jugador):
        _resolver_colisiones_contra_enemigos(proyectiles, escenario.enemigos, jugador, jugadores, textos)
    for jugador in en_combate:
        _resolver_colision_contra_jugador(proyectiles_enemigos, jugador, textos)


def _leer_entrada(entrada, teclas, sacudida):
    """InputJugador de este frame: teclado+mouse (J1) o control (J2)."""
    if isinstance(entrada, EntradaTeclado):
        return entrada.leer(teclas, pygame.mouse.get_pressed(), _punto_mouse(sacudida))
    return entrada.leer()


def _apunta_con_mouse(escena, jugador):
    return escena in ESCENAS_DE_COMBATE and jugador.apunta_con_mouse


def _punto_mouse(sacudida):
    """Punto del mouse en coordenadas del mundo: el mundo se dibuja
    desplazado por la sacudida, así que se le resta. Sin foco de ventana,
    None (se conserva la dirección anterior)."""
    if not pygame.mouse.get_focused():
        return None
    x, y = pygame.mouse.get_pos()
    return (x - sacudida[0], y - sacudida[1])


def _primer_mando():
    """El primer control reconocido por SDL como "GameController" (un
    DualShock 4 lo es), abierto; None si no hay ninguno."""
    for indice in range(controller.get_count()):
        if controller.is_controller(indice):
            return controller.Controller(indice)
    return None


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


def _curar(jugadores):
    """Cada mazmorra (normal o final) se empieza con la vida llena (y sin dash a medias)."""
    for jugador in jugadores:
        jugador.vida = jugador.vida_maxima
        jugador.invulnerabilidad.reiniciar()
        jugador.dash.reiniciar()
        jugador.detener()


def _menu_inicio(pantalla, reloj, mando):
    """Pantalla de modo y luego la de roles (Esc en roles vuelve al modo).
    Retorna (clases de rol en orden J1, J2..., control o None), o None
    si se cierra la ventana."""
    while True:
        modo = _elegir_modo(pantalla, reloj, mando)
        if modo is None:
            return None
        modo, mando = modo
        clases = _elegir_roles(pantalla, reloj, modo, mando)
        if clases is None:
            return None
        if clases != VOLVER:
            return clases, mando


def _elegir_modo(pantalla, reloj, mando):
    """1 o 2 jugadores, con teclado o con el control. Dos jugadores exige
    un control: si no hay, se avisa y se espera a que se conecte uno.
    Retorna (modo, control) o None si se cierra o se pulsa Esc."""
    selector = SelectorModo()
    stick = _StickMenu()
    aviso = 0.0  # segundos que le quedan al aviso "Conecta un control"
    while True:
        dt = reloj.tick(FPS) / 1000
        aviso = max(0.0, aviso - dt)
        confirmar = False
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_SALIR:
                    return None
                if evento.key in TECLAS_MENU_J1:
                    selector.mover(TECLAS_MENU_J1[evento.key])
                elif evento.key in TECLAS_MODO:
                    selector.elegir(TECLAS_MODO[evento.key])
                    confirmar = True
                elif evento.key in TECLAS_CONFIRMAR_MENU:
                    confirmar = True
            elif evento.type == pygame.CONTROLLERBUTTONDOWN:
                if evento.button in BOTONES_MENU_J2:
                    selector.mover(BOTONES_MENU_J2[evento.button])
                elif evento.button == BOTON_CONFIRMAR:
                    confirmar = True
            elif (direccion := stick.paso(evento)) is not None:
                selector.mover(direccion)
        if confirmar:
            if selector.seleccionado == DOS_JUGADORES and mando is None:
                aviso = assets.DURACION_AVISO_MODO
            else:
                return selector.seleccionado, mando

        dibujar_modo(pantalla, selector, mando.name if mando is not None else None, aviso > 0)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_MODO)
        pygame.display.flip()


def _elegir_roles(pantalla, reloj, modo, mando):
    """Cada jugador mueve su cursor sobre las tarjetas y confirma; la
    partida empieza cuando todos confirmaron. J1: flechas o A/D, Enter
    o Espacio, 1-4 directo, Retroceso para cambiar. J2: cruceta o stick,
    ✕ confirma, ○ para cambiar. Retorna la lista de clases elegidas,
    VOLVER con Esc, o None si se cierra la ventana."""
    cantidad = 1 if modo == UN_JUGADOR else 2
    seleccion = SeleccionRoles(cantidad, len(CLASES_ROL))
    j1 = seleccion.cursores[0]
    j2 = seleccion.cursores[1] if cantidad > 1 else None
    stick = _StickMenu()
    while True:
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_SALIR:
                    return VOLVER
                if evento.key in TECLAS_MENU_J1:
                    j1.mover(TECLAS_MENU_J1[evento.key])
                elif evento.key in TECLAS_ROL:
                    j1.elegir(TECLAS_ROL[evento.key])
                elif evento.key in TECLAS_CONFIRMAR_MENU:
                    j1.confirmar()
                elif evento.key == TECLA_CANCELAR:
                    j1.cancelar()
            elif j2 is not None and evento.type == pygame.CONTROLLERBUTTONDOWN:
                if evento.button in BOTONES_MENU_J2:
                    j2.mover(BOTONES_MENU_J2[evento.button])
                elif evento.button == BOTON_CONFIRMAR:
                    j2.confirmar()
                elif evento.button == BOTON_CANCELAR:
                    j2.cancelar()
            elif j2 is not None and (direccion := stick.paso(evento)) is not None:
                j2.mover(direccion)

        dibujar_seleccion(pantalla, CLASES_ROL, seleccion)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_SELECCION_DOS if j2 else hud.CONTROLES_SELECCION)
        pygame.display.flip()
        if seleccion.lista:
            return [CLASES_ROL[indice] for indice in seleccion.indices()]
        reloj.tick(FPS)


class _StickMenu:
    """Stick izquierdo como flechas en los menús: un paso cada vez que se
    inclina más allá de UMBRAL_STICK_MENU; vuelve a contar al soltarlo."""

    def __init__(self):
        self._inclinado = False

    def paso(self, evento):
        if evento.type != pygame.CONTROLLERAXISMOTION or evento.axis != pygame.CONTROLLER_AXIS_LEFTX:
            return None
        valor = evento.value / EJE_MAXIMO
        if abs(valor) < UMBRAL_STICK_MENU:
            self._inclinado = False
            return None
        if self._inclinado:
            return None
        self._inclinado = True
        return DERECHA if valor > 0 else IZQUIERDA


def _actualizar_mando(evento, mando):
    """Conexión en caliente: abre el control que se conecta si no había
    uno, y lo olvida si se desconecta."""
    if evento.type == pygame.CONTROLLERDEVICEADDED and mando is None:
        if controller.is_controller(evento.device_index):
            return controller.Controller(evento.device_index)
    elif evento.type == pygame.CONTROLLERDEVICEREMOVED and mando is not None and not mando.attached():
        return None
    return mando


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
