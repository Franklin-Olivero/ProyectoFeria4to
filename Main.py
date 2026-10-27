"""Punto de entrada del juego.

Antes de la partida va la pantalla de inicio (src/ui/menu_principal.py):

    MENÚ PRINCIPAL --JUGAR--> modo (1 o 2 jugadores) --> roles --> partida nueva
    MENÚ PRINCIPAL --CONTINUAR--> la partida en curso (si hay)
    partida, en la ciudad --(ESC)--> MENÚ PRINCIPAL (la partida queda en curso)

El flujo de la partida es una máquina de estados explícita (Escena,
src/core/escenas.py):

    CIUDAD --(E en una entrada)--> MAZMORRA --(cuarto final limpio)--> DECISION
    DECISION --(resultado)--> RESULTADO --(ENTER)--> CIUDAD (frente a esa puerta)
    CIUDAD --(E en la Alcaldía abierta)--> JEFE --(jefe muere)--> VICTORIA
    VICTORIA --(ENTER)--> CIUDAD           VICTORIA --(ESC)--> salir
    cualquiera --(colapso al 100%)--> DERROTA --(ENTER)--> partida nueva en la Plaza

En CIUDAD el jugador camina por Ciudad Nova (mapa de casillas,
src/dungeon/ciudad_mapa.py) con colisión contra casillas sólidas y
barricadas; G muestra la ruta sugerida (Dijkstra) al destino elegido
con TAB y M abre el mapa del mundo. Al entrar y salir de un edificio
hay un fundido corto.

El combate (MAZMORRA y JEFE) usa el mismo loop: la mazmorra de varios
cuartos y la arena del jefe exponen rect, enemigos, actualizar,
dibujar y manejar_evento. Solo el cuarto final de una mazmorra normal
tiene minijuego de decisión.

Cooperativo local: con "2 jugadores" el J2 elige rol con el control.
Cada jugador tiene su lector de input (src/core/entrada.py:
teclado+mouse para J1, control para J2) y su propia lista de
proyectiles, así cada kill se acredita a quien la hizo. Ambos comparten
cuarto, enemigos y colapso. En la ciudad camina el J1 y al entrar a un
edificio pasa todo el equipo.

Presentación: el HUD superior y la barra de controles (src/ui/hud.py)
se dibujan directo a la pantalla; el mundo se dibuja en un lienzo que
se copia con la sacudida del jefe. Los efectos de combate (cono de
apuntado, objetivo, números de daño, globo del behavior tree con Tab)
viven en src/ui/combate_render.py; el rastro del dash, en
src/ui/particulas.py. Cada frame termina en presentar(): aplica el
filtro de daltonismo de las preferencias (src/ui/filtro_color.py) a la
imagen final y hace el flip.
"""

import sys
from dataclasses import dataclass, replace

import pygame
from pygame._sdl2 import controller

from src.core import assets
from src.core.audio import Audio
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.core.entrada import TECLA_ARBOL, TECLA_MINIMAPA, EJE_MAXIMO, EntradaMando, EntradaTeclado
from src.core.preferencias import cargar as cargar_preferencias
from src.core.preferencias import guardar as guardar_preferencias
from src.core.equipo import jugadores_en_combate, registrar_kill_equipo, revivir_caidos
from src.core.escenas import ESCENAS_DE_COMBATE, Escena, escena_tras_colapso
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO
from src.core.balance import ALCANCE_AVISO_SELLADA
from src.dungeon import ciudad_mapa
from src.dungeon.grafo_ciudad import EDIFICIOS, ZONA_FINAL
from src.dungeon.mazmorra import Mazmorra
from src.dungeon.mazmorra_final import VICTORIA as MAZMORRA_FINAL_GANADA
from src.dungeon.mazmorra_jugable import MazmorraJugable
from src.dungeon.partida import Partida
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import ANGULO_ABANICO_GRADOS, Ciudadano
from src.ui import ciudad_render, combate_render, dibujo, hud, navegacion
from src.ui.combate_render import TextosFlotantes
from src.ui.filtro_color import FiltroColor
from src.ui.mapa_ciudad import SelectorZona
from src.ui.menu_principal import JUGAR, SALIR, MenuPrincipal
from src.ui.menu_principal_render import VistaMenu
from src.ui.mapa_ciudad_render import dibujar_mapa_mundo
from src.ui.mapa_render import dibujar_minimapa
from src.ui.pantalla_derrota import dibujar_derrota
from src.ui.pantalla_resultado import ResultadoMazmorra, dibujar_resultado
from src.ui.pantalla_victoria import dibujar_victoria
from src.ui.pantalla_modo import dibujar_modo
from src.ui.particulas import SistemaParticulas
from src.ui.seleccion import DOS_JUGADORES, UN_JUGADOR, ONLINE, SeleccionRoles, SelectorModo
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA
from src.ui.terminal_decision_render import dibujar_terminal

from Online.lobby import menu_online
from Online.sesion_red import AdaptadorOnlineHost, EntradaRed

TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE

# Tarjetas de la pantalla de selección, en orden (tecla 1 = la primera).
CLASES_ROL = [Ciudadano, Influencer, Periodista, Candidato]
TECLAS_ROL = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
TECLAS_MODO = {
    pygame.K_1: UN_JUGADOR,
    pygame.K_2: DOS_JUGADORES,
    pygame.K_3: ONLINE,
    pygame.K_KP1: UN_JUGADOR,
    pygame.K_KP2: DOS_JUGADORES,
    pygame.K_KP3: ONLINE,
}

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

VOLVER = "volver"  # Esc en modo o roles: un paso atrás
MENU = "menu"  # _jugar: Esc en el mapa, de vuelta al menú principal

# Menú principal y ajustes -> acciones de src/ui/navegacion.py.
TECLAS_MENU_PRINCIPAL = {
    pygame.K_UP: navegacion.ARRIBA, pygame.K_w: navegacion.ARRIBA,
    pygame.K_DOWN: navegacion.ABAJO, pygame.K_s: navegacion.ABAJO,
    pygame.K_LEFT: navegacion.IZQUIERDA, pygame.K_a: navegacion.IZQUIERDA,
    pygame.K_RIGHT: navegacion.DERECHA, pygame.K_d: navegacion.DERECHA,
    pygame.K_RETURN: navegacion.CONFIRMAR, pygame.K_KP_ENTER: navegacion.CONFIRMAR,
    pygame.K_SPACE: navegacion.CONFIRMAR,
    pygame.K_ESCAPE: navegacion.VOLVER, pygame.K_BACKSPACE: navegacion.VOLVER,
    pygame.K_q: navegacion.PESTANA_ANTERIOR, pygame.K_e: navegacion.PESTANA_SIGUIENTE,
}
BOTONES_MENU_PRINCIPAL = {
    pygame.CONTROLLER_BUTTON_DPAD_UP: navegacion.ARRIBA,
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: navegacion.ABAJO,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: navegacion.IZQUIERDA,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: navegacion.DERECHA,
    pygame.CONTROLLER_BUTTON_A: navegacion.CONFIRMAR,  # ✕
    pygame.CONTROLLER_BUTTON_B: navegacion.VOLVER,  # ○
    pygame.CONTROLLER_BUTTON_LEFTSHOULDER: navegacion.PESTANA_ANTERIOR,  # L1
    pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: navegacion.PESTANA_SIGUIENTE,  # R1
}

# Teclas de la terminal de decisión -> dirección de navegación.
TECLAS_TERMINAL = {
    pygame.K_LEFT: IZQUIERDA,
    pygame.K_RIGHT: DERECHA,
    pygame.K_RETURN: CONFIRMAR,
    pygame.K_KP_ENTER: CONFIRMAR,
}

# Teclas de la escena CIUDAD
TECLA_ENTRAR = pygame.K_e
TECLA_RUTA = pygame.K_g
TECLA_DESTINO = pygame.K_TAB
TECLA_MAPA_MUNDO = pygame.K_m


def main():
    pygame.init()
    controller.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    preferencias = cargar_preferencias()
    audio = Audio(preferencias)
    filtro = FiltroColor()

    def presentar():
        """Muestra el frame: filtro de daltonismo sobre la imagen final y flip."""
        filtro.aplicar(pantalla, preferencias.filtro_daltonismo)
        pygame.display.flip()

    # La vista del menú se conserva: al volver, la ciudad sigue donde iba.
    vista_menu = VistaMenu(pantalla.get_size())
    mando = _primer_mando()
    sesion = None  # partida en curso, para CONTINUAR
    while True:
        accion, mando = _menu_principal(pantalla, reloj, vista_menu, sesion is not None, preferencias, audio,
                                        presentar, mando)
        if accion == SALIR:
            break
        if accion == JUGAR:
            # Partida nueva: 1 o 2 jugadores, y luego cada uno elige su rol.
            eleccion = _menu_inicio(pantalla, reloj, mando, presentar)
            if eleccion is None:
                break
            if eleccion == VOLVER:
                continue
            clases, mando, entrada_extra = eleccion
            sesion = _nueva_sesion(clases, mando, entrada_extra)
            if hasattr(entrada_extra, "configurar_sesion"):
                sesion = entrada_extra.configurar_sesion(sesion)
        if _jugar(pantalla, reloj, sesion, preferencias, presentar) == SALIR:
            break
    guardar_preferencias(preferencias)
    pygame.quit()
    sys.exit()


@dataclass
class _Sesion:
    """Lo que sobrevive al volver al menú principal: la partida, los
    jugadores y sus lectores de input (mismo orden)."""

    partida: Partida
    jugadores: list
    entradas: list


def _nueva_sesion(clases, mando, entrada_extra=None):
    # J1 (jugadores[0]) es el del teclado: su HUD va arriba, maneja la
    # terminal de decisión y apunta con la mira del mouse.
    entradas = [EntradaTeclado()]
    if entrada_extra is not None:
        if isinstance(entrada_extra, list):
            entradas.extend(entrada_extra)
        else:
            entradas.append(entrada_extra)
    elif len(clases) > 1:
        entradas.append(EntradaMando(mando))
    return _Sesion(Partida(), [clase(0, 0) for clase in clases], entradas)


def _jugar(pantalla, reloj, sesion, preferencias, presentar):
    """La partida (máquina de escenas). Retorna SALIR si se cierra el
    juego, o MENU con Esc en el mapa (la sesión queda para CONTINUAR)."""
    partida = sesion.partida
    entradas = sesion.entradas
    jugadores = sesion.jugadores
    jugador = jugadores[0]
    if hasattr(sesion, "id_local") and sesion.id_local < len(jugadores):
        jugador = jugadores[sesion.id_local]
    for _idx_j, _j_extra in enumerate(jugadores):
        _j_extra.colocar_en((partida.posicion_aparicion()[0] + _idx_j * 28, partida.posicion_aparicion()[1]))
    # En la ciudad camina el J1; al entrar a un edificio pasa todo el equipo.
    # Al continuar una partida, se reaparece frente a la última puerta.
    jugador.colocar_en(partida.posicion_aparicion())
    # Destino de la ruta sugerida (TAB cicla entre los edificios).
    selector = SelectorZona(EDIFICIOS, EDIFICIOS[0])
    mostrar_ruta = False  # G
    mostrar_mapa_mundo = False  # M en la ciudad
    fundido = 0.0  # s que quedan del fundido al entrar/salir de un edificio
    tiempo = 0.0  # reloj de animaciones de la ciudad (auras, cintillo)

    escena = Escena.CIUDAD
    mazmorra = None  # MazmorraJugable de la zona que se está recorriendo
    arena = None
    mostrar_minimapa = True
    mostrar_arbol = False  # Tab: globo con el nodo activo del behavior tree
    resultado = None  # ResultadoMazmorra que muestra la escena RESULTADO
    # Mensaje central de la ciudad: (texto, color) del último resultado.
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

    while True:
        # tick_busy_loop y no tick: en Windows tick() duerme con poca
        # precisión y los frames salen de 16, 17 o 18 ms, lo que se ve
        # como tirones al moverse. busy_loop da frames regulares.
        dt = reloj.tick_busy_loop(FPS) / 1000
        tiempo += dt
        fundido = max(0.0, fundido - dt)
        tiempo_mensaje_mapa = max(0.0, tiempo_mensaje_mapa - dt)
        # Mouse: solo en combate y con un rol que apunta con él (no el
        # Candidato). Ahí se oculta el cursor del sistema y se dibuja la mira.
        pygame.mouse.set_visible(not _apunta_con_mouse(escena, jugador))

        # --- Input, según la escena ------------------------------------
        # El combate (mover, apuntar, disparar, habilidad, dash) no usa
        # eventos: cada frame se lee el estado del teclado/control (ver
        # _frame_de_combate). Aquí solo van menús y teclas de interfaz.
        for evento in pygame.event.get():
            if len(entradas) > 1 and getattr(entradas[1], "mando", None) is None:
                from Online.sesion_red import _MandoFicticio
                entradas[1].mando = _MandoFicticio()
            if len(entradas) > 1 and not entradas[1].mando.attached():
                # El control del J2 se desconectó: al volver a conectarlo, sigue jugando.
                entradas[1].mando = _actualizar_mando(evento, None) or entradas[1].mando
            if evento.type == pygame.QUIT:
                return SALIR
            elif evento.type != pygame.KEYDOWN:
                continue
            elif escena == Escena.CIUDAD:
                # La escena CIUDAD consume todas sus teclas (sin disparo ni F).
                if evento.key == TECLA_SALIR:
                    return MENU
                if evento.key == TECLA_MAPA_MUNDO:
                    mostrar_mapa_mundo = not mostrar_mapa_mundo
                elif evento.key == TECLA_DESTINO:
                    selector.mover(DERECHA)
                elif evento.key == TECLA_RUTA and not mostrar_mapa_mundo:
                    mostrar_ruta = not mostrar_ruta
                elif evento.key == TECLA_ENTRAR and not mostrar_mapa_mundo:
                    zona = ciudad_mapa.entrada_cercana(_posicion(jugador))
                    if zona is None or (zona == ZONA_FINAL and not partida.alcaldia_desbloqueada()):
                        continue
                    partida.entrar(zona)
                    limpiar_combate()
                    _curar(jugadores)
                    if zona == ZONA_FINAL:
                        arena = ArenaJefe(partida.colapso, jugadores)
                        escena = Escena.JEFE
                    else:
                        mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes(zona), zona))
                        mazmorra.colocar_en_entrada(jugadores)
                        escena = Escena.MAZMORRA
                    fundido = assets.DURACION_FUNDIDO
            elif escena == Escena.DECISION:
                if evento.key in TECLAS_TERMINAL:
                    mazmorra.cuarto.terminal.navegar(TECLAS_TERMINAL[evento.key])
            elif escena == Escena.RESULTADO:
                if evento.key in TECLAS_CONFIRMAR:
                    resultado = None
                    escena = _volver_a_la_ciudad(jugador, partida)
                    fundido = assets.DURACION_FUNDIDO
            elif escena in (Escena.VICTORIA, Escena.DERROTA):
                if evento.key in TECLAS_CONFIRMAR:
                    if escena == Escena.DERROTA:
                        # Partida completa nueva, con los mismos roles, en la
                        # Plaza y con las calles y barricadas restablecidas.
                        partida.reiniciar()
                        jugadores = [type(j)(0, 0) for j in jugadores]
                        sesion.jugadores = jugadores
                        jugador = jugadores[0]
                        selector = SelectorZona(EDIFICIOS, EDIFICIOS[0])
                        mostrar_ruta = mostrar_mapa_mundo = False
                        mensaje_mapa = None
                    arena = None
                    mazmorra = None
                    escena = _volver_a_la_ciudad(jugador, partida)
                    fundido = assets.DURACION_FUNDIDO
                    limpiar_combate()
                elif evento.key == TECLA_SALIR:
                    return SALIR
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

        if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None:
            escena, arena, mazmorra, fundido = sesion.adaptador_red.actualizar(
                escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador
            )

        if escena == Escena.CIUDAD and not mostrar_mapa_mundo:
            jugador.caminar_en_ciudad(pygame.key.get_pressed(), dt, partida.es_solida)
            if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None:
                sesion.adaptador_red.actualizar_ciudad(dt, partida, jugadores, jugador)
        elif escena in ESCENAS_DE_COMBATE:
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
        if escena in (Escena.CIUDAD, Escena.DERROTA):
            _dibujar_ciudad(pantalla, partida, jugador, selector.seleccionada, tiempo,
                            mostrar_ruta, mostrar_mapa_mundo and escena == Escena.CIUDAD)
            if tiempo_mensaje_mapa > 0 and mensaje_mapa is not None and escena == Escena.CIUDAD:
                _dibujar_mensaje(pantalla, mensaje_mapa[0], mensaje_mapa[1], assets.POSICION_MENSAJE_MAPA)
            if escena == Escena.DERROTA:
                dibujar_derrota(pantalla)
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL)
            elif mostrar_mapa_mundo:
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_MAPA_MUNDO)
            else:
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_CIUDAD)
            ciudad_render.dibujar_fundido(pantalla, fundido)
            presentar()
            sacudida = (0, 0)
            continue

        if escena == Escena.DECISION:
            dibujar_terminal(
                pantalla, mazmorra.cuarto.terminal,
                f"Cuarto final  ·  {mazmorra.mazmorra.nombre_zona}  ·  Mazmorra normal",
            )
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_TERMINAL)
            presentar()
            sacudida = (0, 0)
            continue

        if escena == Escena.RESULTADO:
            dibujar_resultado(pantalla, resultado)
            presentar()
            sacudida = (0, 0)
            continue

        escenario = _escenario_activo(escena, arena, mazmorra)
        en_combate = jugadores_en_combate(jugadores)  # los caídos no se dibujan
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        particulas.dibujar(lienzo)  # el rastro del dash queda detrás de los jugadores
        objetivo = None
        if escena in ESCENAS_DE_COMBATE:
            # Cono de apuntado de cada jugador que apunta (mouse o stick
            # derecho). Su visibilidad y opacidad son ajustes solo visuales.
            alfa_cono = combate_render.alfa_cono(preferencias.opacidad_cono) if preferencias.mostrar_cono else 0
            for j in en_combate:
                if j.apunta_con_mouse and alfa_cono > 0:
                    angulo = ANGULO_ABANICO_GRADOS if isinstance(j, Ciudadano) else assets.ANGULO_CONO_ESTRECHO
                    combate_render.dibujar_cono_apuntado(lienzo, j, angulo, alfa_cono)
            if jugador in en_combate and jugador.apunta_con_mouse:
                objetivo = combate_render.enemigo_apuntado(jugador, escenario.enemigos)
                if objetivo is not None:
                    combate_render.dibujar_objetivo(lienzo, jugador, objetivo)
        for j in en_combate:
            j.dibujar(lienzo)
            if escena in ESCENAS_DE_COMBATE and escenario.gracia.activa:
                combate_render.dibujar_gracia(lienzo, j, escenario.gracia.fraccion)
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
        # La sacudida es decorativa: reducir movimiento la quita.
        temblar = escena == Escena.JEFE and not preferencias.reducir_movimiento
        sacudida = arena.mazmorra.desplazamiento_sacudida() if temblar else (0, 0)
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
        ciudad_render.dibujar_fundido(pantalla, fundido)
        presentar()


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
        # Gracia de entrada al cuarto: el jugador solo puede moverse.
        jugador.armas_bloqueadas = escenario.gracia.activa
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
    la mazmorra normal (None en la ciudad)."""
    return arena if escena in (Escena.JEFE, Escena.VICTORIA) else mazmorra


def _enemigo_mas_cercano(jugador, enemigos):
    vivos = [enemigo for enemigo in enemigos if enemigo.vivo]
    if not vivos:
        return None
    centro = pygame.Vector2(jugador.rect.center)
    return min(vivos, key=lambda enemigo: centro.distance_squared_to(enemigo.rect.center))


def _posicion(jugador):
    return (jugador.posicion.x, jugador.posicion.y)


def _volver_a_la_ciudad(jugador, partida):
    """Pone al jugador frente a la puerta de la última zona (o en la
    Plaza tras un reinicio) y retorna la escena CIUDAD."""
    jugador.colocar_en(partida.posicion_aparicion())
    return Escena.CIUDAD


def _dibujar_ciudad(pantalla, partida, jugador, destino, tiempo, mostrar_ruta, mostrar_mapa_mundo):
    """Escena CIUDAD completa salvo la barra de controles: el mundo (o el
    mapa del mundo con M), el HUD, el cintillo y los avisos."""
    posicion = _posicion(jugador)
    ruta = partida.ruta_sugerida(posicion, destino) if mostrar_ruta or mostrar_mapa_mundo else None
    if mostrar_mapa_mundo:
        dibujar_mapa_mundo(pantalla, partida, destino, posicion)
        titulo = assets.TITULO_MAPA_MUNDO
    else:
        puntos = ciudad_mapa.polilinea_ruta(posicion, ruta[0]) if mostrar_ruta and ruta else None
        ciudad_render.dibujar_ciudad(pantalla, partida, jugador, tiempo, puntos)
        if hasattr(partida, "jugadores_online") and not mostrar_mapa_mundo:
            for _j_otro in partida.jugadores_online:
                if _j_otro is not jugador and getattr(_j_otro.invulnerabilidad, "visible", True):
                    from src.ui import sprites
                    _rect_v = ciudad_render.vista()
                    _cam = ciudad_render.camara_para((jugador.posicion.x, jugador.posicion.y))
                    _dx, _dy = _rect_v.x - _cam[0], _rect_v.y - _cam[1]
                    _img = sprites.sprite_jugador(_j_otro.COLOR, rol=_j_otro.rol, tiempo=tiempo,
                                                  caminando=getattr(_j_otro, "caminando_en_ciudad", False))
                    sprites.dibujar_centrado(pantalla, _img, (round(_j_otro.posicion.x + _dx), round(_j_otro.posicion.y + _dy - 6)))
        titulo = assets.TITULO_CIUDAD
    subtitulo = f"Destino: {destino}  ·  Calles bloqueadas: {len(partida.ciudad.bloqueadas)}"
    hud.dibujar_hud_superior(pantalla, jugador, None, titulo, subtitulo, partida.colapso)
    ciudad_render.dibujar_cintillo(pantalla, partida.titulares(), tiempo)
    if mostrar_mapa_mundo:
        return
    if mostrar_ruta:
        texto = (assets.TEXTO_RUTA_DESTINO.format(destino=destino, costo=ruta[1]) if ruta
                 else assets.TEXTO_SIN_RUTA)
        dibujo.chip(pantalla, texto, assets.POSICION_AVISO_RUTA, assets.COLOR_RUTA_CIUDAD, assets.COLOR_FONDO_PANEL,
                    assets.COLOR_RUTA_CIUDAD, assets.TAMANIO_FUENTE_NORMAL, ancla="topright", alto=30, margen=12)
    zona = ciudad_mapa.entrada_cercana(posicion)
    sellada = not partida.alcaldia_desbloqueada()
    if zona is not None and not (zona == ZONA_FINAL and sellada):
        ciudad_render.dibujar_aviso(
            pantalla, assets.TEXTO_AVISO_ENTRADA.format(zona=zona, nivel=partida.toxicidad(zona)),
            assets.COLOR_AVISO_ENTRADA,
        )
    elif sellada and ciudad_mapa.entrada_cercana(posicion, ALCANCE_AVISO_SELLADA) == ZONA_FINAL:
        ciudad_render.dibujar_aviso(pantalla, assets.TEXTO_ALCALDIA_SELLADA, assets.COLOR_AVISO_SELLADA)


def _curar(jugadores):
    """Cada mazmorra (normal o final) se empieza con la vida llena (y sin dash a medias)."""
    for jugador in jugadores:
        jugador.vida = jugador.vida_maxima
        jugador.invulnerabilidad.reiniciar()
        jugador.dash.reiniciar()
        jugador.detener()


def _menu_principal(pantalla, reloj, vista, hay_partida, preferencias, audio, presentar, mando):
    """Pantalla de inicio con la ciudad animada, el menú, EXTRAS, CRÉDITOS
    y el modal de ajustes. Teclado, control y ratón se traducen a
    acciones de src/ui/navegacion.py; el sonido sale de lo que retorna
    cada acción (un cambio real), así nunca se duplica. Retorna
    (JUGAR | CONTINUAR | SALIR, control)."""
    menu = MenuPrincipal(hay_partida, preferencias)
    sticks = (_StickMenu(),
              _StickMenu(pygame.CONTROLLER_AXIS_LEFTY, navegacion.ARRIBA, navegacion.ABAJO))
    guardadas = replace(preferencias)
    pygame.mouse.set_visible(True)
    while True:
        dt = reloj.tick_busy_loop(FPS) / 1000
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return SALIR, mando
            accion = _accion_menu(evento, sticks)
            sonido = menu.accion(accion) if accion is not None else vista.manejar_mouse(evento, menu)
            audio.reproducir(sonido)
        resultado = menu.actualizar(dt)
        # Los ajustes se aplican al instante y se guardan en disco al
        # cambiar (si se arrastra un slider, al soltarlo).
        if preferencias != guardadas:
            audio.aplicar(preferencias)
            if not vista.arrastrando:
                guardar_preferencias(preferencias)
                guardadas = replace(preferencias)
        if resultado is not None:
            return resultado, mando
        vista.actualizar(dt, menu, preferencias.reducir_movimiento)
        vista.dibujar(pantalla, menu, audio, preferencias.reducir_movimiento)
        presentar()


def _accion_menu(evento, sticks):
    """Acción de navegación de un evento de teclado o control, o None."""
    if evento.type == pygame.KEYDOWN:
        return TECLAS_MENU_PRINCIPAL.get(evento.key)
    if evento.type == pygame.CONTROLLERBUTTONDOWN:
        return BOTONES_MENU_PRINCIPAL.get(evento.button)
    for stick in sticks:
        direccion = stick.paso(evento)
        if direccion is not None:
            return direccion
    return None


def _menu_inicio(pantalla, reloj, mando, presentar):
    """Pantalla de modo y luego la de roles (Esc en roles vuelve al modo).
    Retorna (clases de rol en orden J1, J2..., control o None, entrada_extra), VOLVER
    con Esc en la pantalla de modo, o None si se cierra la ventana."""
    while True:
        modo = _elegir_modo(pantalla, reloj, mando, presentar)
        if modo is None or modo == VOLVER:
            return modo
        modo, mando = modo
        if modo == ONLINE:
            res = menu_online(pantalla, reloj, presentar, CLASES_ROL)
            if res is None:
                return None
            if res == "volver":
                continue
            clases, conexion, es_host = res
            from Online.sesion_red import preparar_sesion_online
            config_online = preparar_sesion_online(clases, mando, conexion, es_host)
            if config_online is not None:
                return config_online
            if es_host:
                adaptador = AdaptadorOnlineHost(conexion)
                entradas_red = [EntradaRed(adaptador, id_jugador=jid) for jid in range(1, len(clases))]
                return clases, mando, entradas_red
            else:
                return clases, mando, None
        clases = _elegir_roles(pantalla, reloj, modo, mando, presentar)
        if clases is None:
            return None
        if clases != VOLVER:
            return clases, mando, None


def _elegir_modo(pantalla, reloj, mando, presentar):
    """1 o 2 jugadores, con teclado o con el control. Dos jugadores exige
    un control: si no hay, se avisa y se espera a que se conecte uno.
    Retorna (modo, control), VOLVER con Esc u ○, o None si se cierra."""
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
                    return VOLVER
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
                elif evento.button == BOTON_CANCELAR:
                    return VOLVER
            elif (direccion := stick.paso(evento)) is not None:
                selector.mover(direccion)
        if confirmar:
            if selector.seleccionado == DOS_JUGADORES and mando is None:
                aviso = assets.DURACION_AVISO_MODO
            else:
                return selector.seleccionado, mando

        dibujar_modo(pantalla, selector, mando.name if mando is not None else None, aviso > 0)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_MODO)
        presentar()


def _elegir_roles(pantalla, reloj, modo, mando, presentar):
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
        presentar()
        if seleccion.lista:
            return [CLASES_ROL[indice] for indice in seleccion.indices()]
        reloj.tick(FPS)


class _StickMenu:
    """Un eje del stick izquierdo como flechas en los menús: un paso cada
    vez que se inclina más allá de UMBRAL_STICK_MENU; vuelve a contar al
    soltarlo. Por defecto el eje horizontal (izquierda / derecha)."""

    def __init__(self, eje=pygame.CONTROLLER_AXIS_LEFTX, negativo=IZQUIERDA, positivo=DERECHA):
        self._eje = eje
        self._negativo, self._positivo = negativo, positivo
        self._inclinado = False

    def paso(self, evento):
        if evento.type != pygame.CONTROLLERAXISMOTION or evento.axis != self._eje:
            return None
        valor = evento.value / EJE_MAXIMO
        if abs(valor) < UMBRAL_STICK_MENU:
            self._inclinado = False
            return None
        if self._inclinado:
            return None
        self._inclinado = True
        return self._positivo if valor > 0 else self._negativo


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
