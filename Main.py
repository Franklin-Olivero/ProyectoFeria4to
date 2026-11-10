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
from src.audio.gestor_audio import Audio
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.audio import eventos_sonido
from src.core.entrada import (
    TECLA_ARBOL, TECLA_MINIMAPA, TECLA_SILENCIO, TECLAS_VOLUMEN, EJE_MAXIMO, EntradaMando, EntradaTeclado,
)
from src.audio import ajustes_audio
from src.core.preferencias import RUTA_LEGADO as RUTA_PREFERENCIAS_LEGADO
from src.core.preferencias import cargar as cargar_preferencias
from src.core.preferencias import guardar as guardar_preferencias
from src.core.equipo import jugadores_en_combate, registrar_kill_equipo, revivir_caidos, todos_caidos
from src.core.escenas import ESCENAS_DE_COMBATE, Escena, escena_tras_colapso
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO
from src.core.balance import (
    ALCANCE_AVISO_SELLADA, BLOQUEO_POST_SABOTAJE, COOLDOWN_POST_SABOTAJE, COOLDOWN_REUNION, DURACION_TERMINAL_HISTORIA,
    MAX_LARGO_MENSAJE_REUNION, PASO_VOLUMEN_LOBBY,
)
from src.dungeon import ciudad_mapa, registro_mazmorras
from src.dungeon.grafo_ciudad import EDIFICIOS, ZONA_FINAL, ZONA_INICIO
from src.dungeon.mazmorra import Mazmorra
from src.dungeon.mazmorra_final import VICTORIA as MAZMORRA_FINAL_GANADA
from src.dungeon.mazmorra_jugable import MazmorraJugable
from src.dungeon.partida import Partida
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import ANGULO_ABANICO_GRADOS, Ciudadano
from src.ui import ciudad_render, combate_render, dialogo_render, dibujo, hud, indicadores_render, navegacion
from src.ui import ayuda_render, elecciones_render, investigacion_render, red_social_render, tarjetas_render
from src.ui import escena_lobby_render
from src.ui import cinematica_render, feed_render, layout, mision_render, redencion_render, reputacion_render
from src.core.preferencias import CARACTERES_POR_SEGUNDO
from src.story.cinematica import Cinematica, guion_caida_servidor, guion_derrota_global, guion_final, guion_intro
from src.story.redencion import CONFIRMAR as NAV_CONFIRMAR, DERECHA as NAV_DERECHA, ETAPA_CONFIANZA, ETAPA_CORREGIR
from src.story.redencion import IZQUIERDA as NAV_IZQUIERDA, EleccionCrisis
from src.story.eleccion import resumen_final
from src.story.misiones import RastreadorMisiones, mision_actual
from src.ui.combate_render import TextosFlotantes
from src.ui.filtro_color import FiltroColor, aplicar_alto_contraste
from src.ui.mapa_ciudad import SelectorZona
from src.ui.menu_principal import JUGAR, SALIR, VER_INTRO, MenuPrincipal
from src.ui.menu_principal_render import VistaMenu
from src.ui.mapa_ciudad_render import dibujar_mapa_mundo
from src.ui.mapa_render import dibujar_minimapa
from src.ui.pantalla_derrota import dibujar_derrota
from src.ui.pantalla_resultado import ResultadoMazmorra, dibujar_resultado
from src.ui.pantalla_victoria import dibujar_victoria
from src.ui.pantalla_modo import dibujar_modo
from src.ui.particulas import SistemaParticulas
from src.ui.seleccion import DOS_JUGADORES, UN_JUGADOR, ONLINE, SeleccionRoles, SelectorModo
from src.ui.seleccion_rol import VistaSeleccion
from src.ui.ajustes import ModalAjustes, PESTANAS_PAUSA
from src.ui import pausa as menu_pausa
from src.ui.pausa_render import VistaPausa
from src.ui import hud_partida, hud_visibilidad
from src.core.balance import NIVEL_TOXICIDAD_FINAL
from src.ui.instrucciones import InstruccionesMazmorra, claves_vistas, debe_mostrarse
from src.ui.instrucciones_render import dibujar_instrucciones
from src.ui.terminal_decision import CONFIRMAR, DERECHA, DETONACION, IZQUIERDA, PURIFICACION_EXITOSA
from src.ui.terminal_decision_render import dibujar_terminal

from Online import disposicion_hud, reunion_render, sabotaje_render
from Online.lobby import menu_online
from Online.sesion_red import AdaptadorOnlineHost, EntradaRed
from Online.sesion_red import cerrar_red_de_sesion, compartir_combate_con_sesion, normalizar_escena, proteger_partida_online

TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE
TECLAS_PAUSA = (pygame.K_ESCAPE, pygame.K_p)  # abren el menú de pausa en la partida

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
TECLA_ESTADO_CIUDAD = pygame.K_i  # panel de indicadores del modo historia
TECLA_AYUDA = pygame.K_h
TECLA_REPORTAR = pygame.K_r  # Online: reunión de emergencia (botón REPORTAR)
TECLA_SABOTEAR = pygame.K_q  # Online: el impostor lanza una publicación viral (botón SABOTEAR)
# Dónde el impostor ve el botón SABOTEAR (en la terminal ya hay una decisión).
ESCENAS_BOTON_SABOTEAR = (Escena.CIUDAD, Escena.MAZMORRA, Escena.JEFE)
TECLAS_SALIR_FIN_PARTIDA = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE)
# Dónde se ve el botón REPORTAR: con el mundo en marcha (Online/sesion_red.ESCENAS_REUNION).
ESCENAS_BOTON_REPORTAR = (Escena.CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE)
# Diálogos del modo historia (overlay sobre cualquier escena).
TECLAS_DIALOGO_AVANZAR = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
TECLAS_DIALOGO_SALTAR = (pygame.K_ESCAPE, pygame.K_TAB)
# Pantallas de la crisis y de la redención (flechas, A/D o W/S y Enter).
TECLAS_NAV_HISTORIA = {
    pygame.K_LEFT: NAV_IZQUIERDA, pygame.K_a: NAV_IZQUIERDA, pygame.K_UP: NAV_IZQUIERDA, pygame.K_w: NAV_IZQUIERDA,
    pygame.K_RIGHT: NAV_DERECHA, pygame.K_d: NAV_DERECHA, pygame.K_DOWN: NAV_DERECHA, pygame.K_s: NAV_DERECHA,
    pygame.K_RETURN: NAV_CONFIRMAR, pygame.K_KP_ENTER: NAV_CONFIRMAR, pygame.K_SPACE: NAV_CONFIRMAR,
}
BOTONES_NAV_HISTORIA = {
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: NAV_IZQUIERDA, pygame.CONTROLLER_BUTTON_DPAD_UP: NAV_IZQUIERDA,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: NAV_DERECHA, pygame.CONTROLLER_BUTTON_DPAD_DOWN: NAV_DERECHA,
    pygame.CONTROLLER_BUTTON_A: NAV_CONFIRMAR,
}


def cargar_ajustes_audio():
    """Ajustes de audio guardados (o los volúmenes de un preferencias.json viejo)."""
    return ajustes_audio.cargar(ruta_legado=RUTA_PREFERENCIAS_LEGADO)


def main():
    # Orden de arranque: primero los ajustes guardados, después el
    # mezclador (pygame.init), y el gestor los aplica a todo lo que suene.
    preferencias = cargar_preferencias()
    ajustes = cargar_ajustes_audio()
    pygame.init()
    controller.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    audio = Audio(ajustes)
    audio.precargar_musica()
    filtro = FiltroColor()

    def presentar():
        """Muestra el frame: filtro de daltonismo (y alto contraste) sobre
        la imagen final y flip."""
        filtro.aplicar(pantalla, preferencias.filtro_daltonismo)
        if preferencias.alto_contraste:
            aplicar_alto_contraste(pantalla)
        pygame.display.flip()

    # La vista del menú se conserva: al volver, la ciudad sigue donde iba.
    vista_menu = VistaMenu(pantalla.get_size())
    mando = _primer_mando()
    sesion = None  # partida en curso, para CONTINUAR
    while True:
        audio.musica("menu")
        accion, mando = _menu_principal(pantalla, reloj, vista_menu, sesion is not None, preferencias, audio,
                                        presentar, mando)
        if accion == SALIR:
            break
        if accion == VER_INTRO:
            # EXTRAS: volver a ver la introducción (no toca ninguna partida).
            if _reproducir_cinematica(pantalla, reloj, guion_intro(Partida().campania.contenido),
                                      preferencias, audio, presentar) == SALIR:
                break
            continue
        if accion == JUGAR:
            # Partida nueva: la de antes suelta su red (si era Online, el puerto
            # 7777 queda libre para volver a crear una sala).
            cerrar_red_de_sesion(sesion)
            # 1 o 2 jugadores, y luego cada uno elige su rol.
            eleccion = _menu_inicio(pantalla, reloj, mando, presentar, audio, preferencias)
            if eleccion is None:
                break
            if eleccion == VOLVER:
                continue
            clases, mando, entrada_extra = eleccion
            sesion = _nueva_sesion(clases, mando, entrada_extra)
            if hasattr(entrada_extra, "configurar_sesion"):
                sesion = entrada_extra.configurar_sesion(sesion)
            sesion.audio = audio
        if _jugar(pantalla, reloj, sesion, preferencias, presentar) == SALIR:
            break
        if getattr(sesion, "partida_online_terminada", False):
            # Alguien ganó por votación (Online/reunion.py): no hay nada que continuar.
            cerrar_red_de_sesion(sesion)
            sesion = None
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
    audio: object = None  # src/audio/gestor_audio.Audio (música y efectos de la historia)
    id_impostor: object = None  # modo Online: id de red del jugador que sorteó el host


def _reproducir_cinematica(pantalla, reloj, cinematica, preferencias, audio, presentar):
    """Reproduce una Cinematica sola (EXTRAS → ver la introducción).
    Enter avanza, Esc salta. Retorna SALIR si se cierra la ventana."""
    audio.musica("misterio")
    pygame.mouse.set_visible(True)
    cinematica.configurar_lectura(CARACTERES_POR_SEGUNDO[preferencias.velocidad_texto], preferencias.avance_cinematicas)
    while not cinematica.terminada:
        dt = reloj.tick_busy_loop(FPS) / 1000
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return SALIR
            if evento.type == pygame.KEYDOWN:
                if evento.key in TECLAS_DIALOGO_AVANZAR:
                    cinematica.avanzar()
                elif evento.key in TECLAS_DIALOGO_SALTAR:
                    cinematica.saltar()
            elif evento.type == pygame.CONTROLLERBUTTONDOWN:
                if evento.button == BOTON_CONFIRMAR:
                    cinematica.avanzar()
                elif evento.button == BOTON_CANCELAR:
                    cinematica.saltar()
        cinematica.actualizar(dt)
        audio.reproducir(cinematica.tomar_sonido())
        if cinematica.terminada:
            break
        cinematica_render.dibujar_cinematica(pantalla, cinematica, dt, preferencias.reducir_movimiento)
        presentar()
    return None


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
    escena_previa = escena  # para el sonido del titular al volver a la ciudad
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

    # Online: los adaptadores de red usan estas listas (Online/sesion_red.py).
    compartir_combate_con_sesion(sesion, limpiar_combate, proyectiles_enemigos, textos)

    # --- Modo historia (src/story/): overlays sobre la escena -----------
    campania = partida.campania
    adaptador_red = getattr(sesion, "adaptador_red", None)
    # Quién juega en ESTA pantalla: en red, un jugador; en local, todos.
    indice_local = getattr(sesion, "id_local", 0) if adaptador_red is not None else 0
    indices_locales = [indice_local] if adaptador_red is not None else list(range(len(jugadores)))
    campania.espejo = hasattr(adaptador_red, "enviar_decision_nav")  # invitado: el host manda
    partida.indice_decisor = indice_local
    for _i_j, _j_rol in enumerate(jugadores):
        campania.establecer_rol(_j_rol.rol, _i_j)
        campania.rep(_i_j)
    audio = getattr(sesion, "audio", None)
    eventos_sonido.drenar()  # lo pedido en menús o antes de empezar ya no aplica

    def sonar(nombre):
        if audio is not None and nombre:
            audio.reproducir(nombre)

    def musica(nombre):
        if audio is not None:
            audio.musica(nombre)

    # Overlay narrativo activo (pausa el mundo): una Cinematica o una
    # DialogoSecuencia. Los que esperan turno van en `cola_historia`
    # (p. ej. la tarjeta del capítulo y luego su diálogo).
    cola_historia = []
    velocidad_texto = CARACTERES_POR_SEGUNDO[preferencias.velocidad_texto]
    dialogo = campania.cinematica_intro(jugador.rol, jugador.NOMBRE)
    if dialogo is not None:
        dialogo.configurar_lectura(velocidad_texto, preferencias.avance_cinematicas)
    tiempo_overlay = 0.0  # s desde que se abrió el overlay/panel actual (animación de entrada)

    def encolar_historia(*items):
        nonlocal dialogo, tiempo_overlay
        for item in items:
            if item is None:
                continue
            item.configurar_lectura(velocidad_texto, modo=preferencias.avance_cinematicas)
            if dialogo is None:
                dialogo = item
                tiempo_overlay = 0.0
            else:
                cola_historia.append(item)

    def siguiente_historia():
        nonlocal dialogo, tiempo_overlay
        dialogo = cola_historia.pop(0) if cola_historia else None
        tiempo_overlay = 0.0

    def al_entrar_a_zona(zona):
        """Entrar a un edificio, con la E de esta PC o porque la red trajo al
        equipo (Online: entró el host o lo pidió un invitado). En cada PC, la
        presentación del capítulo una vez por zona; donde se decide la
        historia (host o partida local), además los matices de entrada."""
        nonlocal mostrar_estado, tarjeta_evidencia, limpios_vistos
        if zona != ZONA_FINAL and getattr(mazmorra, "mazmorra", None) is not None:
            campania.evidencias_sueltas.pop(zona, None)
            limpios_vistos = len(mazmorra.mazmorra.limpiados)
        mostrar_estado = False
        tarjeta_evidencia = None
        campania.evidencias_nuevas.clear()
        sonar("transicion")
        # Presentación del capítulo (una vez por zona): tarjeta de título y
        # luego el diálogo; el mundo espera (en red, a todo el equipo).
        encolar_historia(*campania.presentacion_zona(zona, jugador.rol, jugador.NOMBRE, indice_local))
        if not campania.espejo:
            # Matices de entrada: la fuente del Periodista y la ayuda de
            # los ciudadanos a quien se ganó su confianza.
            for _i_j in range(len(jugadores)):
                campania.al_entrar_zona(zona, _i_j)
                aporte = campania.aporte_ciudadano(zona, _i_j)
                if aporte is not None:
                    toasts.append([campania.contenido["aportes_ciudadanos"].format(nombre=aporte[0]),
                                   assets.DURACION_TOAST_MISION + 1, "Ayuda ciudadana"])

    # Crisis y redención (por jugador de esta pantalla).
    crisis_en_curso = None  # índice del jugador cuya crisis se está presentando
    eleccion_crisis = None  # EleccionCrisis abierta
    etapa_abierta = None  # índice del jugador cuya etapa de la misión está en pantalla
    final_derrota = None  # redencion_render.FinalDerrota abierto
    final_pendiente = None  # índice: el final se abre al terminar su cinemática
    indicador_rep = None  # reputacion_render.IndicadorReputacion en pantalla
    tiempo_historia = 0.0
    feed_ciudad = None  # (texto, nivel, segundos restantes): comentario de un ciudadano
    reloj_reaccion = assets.PERIODO_REACCION_CIUDAD / 2

    def accion_historia(evento, indice, **datos):
        """Una decisión de la crisis. El host (o el juego local) la aplica; el
        invitado la aplica en su copia para seguir jugando y avisa al host,
        que es quien fija la reputación de todos."""
        if campania.espejo and adaptador_red is not None and hasattr(adaptador_red, "enviar_historia"):
            adaptador_red.enviar_historia(evento, **datos)
            campania.esperar_host(indice)
        if evento == "aceptar":
            return campania.aceptar_redencion(indice)
        if evento == "completar":
            return campania.completar_redencion(indice)
        if evento == "rechazar":
            return campania.rechazar_redencion(indice)
        if evento == "fallar":
            return campania.fallar_redencion(indice)
        if evento == "reintentar":
            return campania.volver_a_punto_control(indice)
        return None

    def reiniciar_partida():
        """Partida completa nueva, con los mismos roles, en la Plaza y con
        las calles y barricadas restablecidas."""
        nonlocal jugadores, jugador, selector, mostrar_ruta, mostrar_mapa_mundo, mensaje_mapa
        partida.reiniciar()
        jugadores = _jugadores_nuevos(jugadores)
        sesion.jugadores = jugadores
        jugador = jugadores[indice_local] if indice_local < len(jugadores) else jugadores[0]
        selector = SelectorZona(EDIFICIOS, EDIFICIOS[0])
        mostrar_ruta = mostrar_mapa_mundo = False
        mensaje_mapa = None
        for _i, _j in enumerate(jugadores):
            campania.establecer_rol(_j.rol, _i)
            campania.rep(_i)

    tarjeta_evidencia = None  # (evidencia, segundos restantes) en combate
    mostrar_estado = False  # tecla I en la ciudad
    mostrar_ayuda = False  # tecla H en la ciudad
    limpios_vistos = 0  # cuartos limpios ya contados (una evidencia por cuarto)
    # Tras el resultado de una zona que propagó por la red social: la
    # pantalla del grafo (Enter la abre, Enter la cierra).
    propagacion_pendiente = False
    mostrar_propagacion = False
    tiempo_propagacion = 0.0
    investigacion = None  # capítulo 3: Investigacion activa (tras el resultado)
    mostrar_elecciones = False  # tras la victoria: pantalla de elecciones y epílogo
    tiempo_elecciones = 0.0  # s en la pantalla de elecciones (las barras se llenan)
    final_presentado = False  # ya se mostró la cinemática del final
    victoria_presentada = False  # ya se mostró la caída del servidor
    derrota_presentada = False
    # Misiones: se derivan del estado cada frame; el rastreador detecta
    # objetivos recién cumplidos para el aviso y su sonido.
    rastreador = RastreadorMisiones()
    mision = None
    toasts = []  # [texto, segundos restantes, título]
    escena_avisos = escena
    aviso_sabotaje = 0.0  # s que el indicador del impostor marca "aún no" (tecla durante su bloqueo)
    # Online: otros jugadores que siguen leyendo una escena (en combate, el mundo los espera).
    lectores_red = []
    espera_equipo = False
    presentar_externo = presentar  # el `presentar` de main(): filtro de color y flip
    pausa = menu_pausa.Pausa()
    vista_pausa = VistaPausa()
    sticks_pausa = (_StickMenu(pygame.CONTROLLER_AXIS_LEFTY, navegacion.ARRIBA, navegacion.ABAJO),)
    fondo_pausa = None  # último frame antes de congelar: se redibuja tal cual
    instrucciones = None  # InstruccionesMazmorra abierta (el mundo espera) o None
    instrucciones_vistas = set()  # tipos de enemigo ya presentados en esta partida

    def presentar_frame():
        """Muestra el frame; con la pausa abierta, su menú encima."""
        nonlocal fondo_pausa
        if pausa.abierta:
            if fondo_pausa is None:
                fondo_pausa = pantalla.copy()
            vista_pausa.dibujar(pantalla, pausa, audio, preferencias.reducir_movimiento)
        presentar_externo()

    estado_hud = {"controles": assets.DURACION_CONTROLES_AYUDA, "mision": 0.0, "rect_mision": None, "escena": None}

    def mision_abierta():
        """La misión completa se abre con el mouse sobre su línea o unos
        segundos tras cambiar de destino con Tab."""
        rect = estado_hud["rect_mision"]
        return estado_hud["mision"] > 0 or (rect is not None and rect.collidepoint(pygame.mouse.get_pos()))

    def bloques_hud(escena_actual, mapa_mundo=False):
        return hud_visibilidad.bloques_visibles(
            escena_actual, preferencias.hud_detallado, estado_hud["controles"] > 0, mostrar_minimapa,
            len(jugadores) > 1, mapa_mundo, mision_abierta())

    def abrir_pausa():
        if pausa.abrir(escena, len(jugadores), adaptador_red is not None):
            if audio is not None:
                audio.atenuar_musica(True)
            sonar(navegacion.SONIDO_CONFIRMAR)
            return True
        return False

    def cerrar_pausa():
        nonlocal fondo_pausa
        pausa.cerrar()
        fondo_pausa = None
        if audio is not None:
            audio.atenuar_musica(instrucciones is not None)  # bajo las instrucciones sigue baja

    def entrar_a_zona(zona):
        """Entra (o vuelve a entrar) al edificio `zona` con todo el equipo:
        la Alcaldía abre la arena del jefe; los demás, una mazmorra nueva."""
        nonlocal arena, mazmorra, escena, fundido
        partida.entrar(zona)
        limpiar_combate()
        _curar(jugadores)
        if zona == ZONA_FINAL:
            arena = ArenaJefe(partida.colapso, jugadores)
            escena = Escena.JEFE
        else:
            mazmorra = MazmorraJugable(
                Mazmorra(partida.ciudad.reportes(zona), zona),
                fabrica_arbol=partida.fabrica_arbol(zona),
                duracion_terminal=DURACION_TERMINAL_HISTORIA + campania.duracion_extra_terminal(indice_local),
            )
            mazmorra.colocar_en_entrada(jugadores)
            escena = Escena.MAZMORRA
        fundido = assets.DURACION_FUNDIDO
        al_entrar_a_zona(zona)
        abrir_instrucciones(zona)

    def abrir_instrucciones(zona):
        """Antes del primer cuarto (o del jefe): una tarjeta por enemigo que
        puede aparecer. El mundo queda congelado hasta comenzar. Online no se
        muestra: el mundo no se congela para un solo jugador."""
        nonlocal instrucciones
        instrucciones = None
        if adaptador_red is not None:
            return
        if zona == ZONA_FINAL:
            nuevas = InstruccionesMazmorra.para_jefe(NIVEL_TOXICIDAD_FINAL)
        else:
            nuevas = InstruccionesMazmorra.para_mazmorra(zona, mazmorra.mazmorra.nivel_zona)
        if debe_mostrarse(preferencias.instrucciones_mazmorra, nuevas.tarjetas, instrucciones_vistas):
            instrucciones = nuevas
            if audio is not None:
                audio.atenuar_musica(True)

    def comenzar_instrucciones():
        """Cierra las instrucciones: vuelve la música y arranca la gracia del
        primer cuarto (o de la arena)."""
        nonlocal instrucciones
        instrucciones_vistas.update(claves_vistas(instrucciones.tarjetas))
        instrucciones = None
        if audio is not None:
            audio.atenuar_musica(False)
        combate = arena if escena == Escena.JEFE else mazmorra
        if combate is not None:
            combate.gracia.iniciar()

    def atender_instrucciones(dt):
        """Un frame con las instrucciones abiertas: solo corre su retardo
        anti-salto; Enter, Espacio o clic comienzan, ← → pasan de página y
        Esc abre la pausa encima. Retorna SALIR si se cierra la ventana."""
        instrucciones.actualizar(dt)
        pygame.mouse.set_visible(True)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return SALIR
            if evento.type == pygame.KEYDOWN and evento.key == TECLA_SILENCIO:
                if audio is not None:
                    audio.alternar_silencio()
                continue
            if evento.type == pygame.KEYDOWN and evento.key in TECLAS_PAUSA:
                abrir_pausa()
                break
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                accion = navegacion.CONFIRMAR
            else:
                accion = _accion_menu(evento, sticks_pausa)
            if accion == navegacion.VOLVER:  # ○ del control: la pausa
                abrir_pausa()
                break
            if accion in (navegacion.CONFIRMAR, navegacion.IZQUIERDA, navegacion.DERECHA):
                sonar(instrucciones.accion(accion))
            if instrucciones.comenzada:
                comenzar_instrucciones()
                return None
        dibujar_instrucciones(pantalla, instrucciones, instrucciones.tiempo, preferencias.reducir_movimiento)
        presentar_frame()
        return None

    def atender_pausa():
        """Un frame con la pausa abierta: solo su menú recibe el teclado, el
        ratón y el control. Los ajustes se aplican y guardan al cambiar.
        Retorna SALIR o MENU si hay que dejar la partida; si no, None."""
        nonlocal mazmorra, arena, escena, fundido, instrucciones
        audio_antes = replace(audio.ajustes) if audio is not None else None
        hud_antes = preferencias.hud_detallado
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return SALIR
            if evento.type == pygame.KEYDOWN and evento.key == TECLA_SILENCIO:
                if audio is not None:
                    audio.alternar_silencio()
                continue
            if (evento.type == pygame.KEYDOWN and evento.key == pygame.K_p
                    and pausa.ajustes is None and pausa.confirmando is None):
                sonar(pausa.elegir(menu_pausa.CONTINUAR))
                continue
            accion = _accion_menu(evento, sticks_pausa)
            sonar(pausa.accion(accion) if accion is not None else vista_pausa.manejar_mouse(evento, pausa))
        arrastrando = vista_pausa.ajustes.arrastre is not None
        if audio is not None and audio.ajustes != audio_antes and not arrastrando:
            audio.aplicar()
            audio.guardar()
        if preferencias.hud_detallado != hud_antes:
            guardar_preferencias(preferencias)

        eleccion = pausa.tomar_accion()
        if eleccion == menu_pausa.AJUSTES:
            ajustes = audio.ajustes if audio is not None else ajustes_audio.AjustesAudio()
            pausa.abrir_ajustes(ModalAjustes(preferencias, ajustes, PESTANAS_PAUSA))
        elif eleccion == menu_pausa.CONTINUAR:
            cerrar_pausa()
        elif eleccion == menu_pausa.REINICIAR:
            cerrar_pausa()
            entrar_a_zona(ZONA_FINAL if escena == Escena.JEFE else mazmorra.mazmorra.nombre_zona)
        elif eleccion == menu_pausa.VOLVER_CIUDAD:
            instrucciones = None
            cerrar_pausa()
            mazmorra = None
            arena = None
            limpiar_combate()
            escena = _volver_a_la_ciudad(jugador, partida)
            fundido = assets.DURACION_FUNDIDO
        elif eleccion == menu_pausa.SALIR_MENU:
            instrucciones = None
            cerrar_pausa()
            return MENU
        return None

    def navegar_terminal(actor, direccion):
        """Única vía para mover o confirmar la terminal de decisión desde esta
        PC, con teclado o con control. Online: el impostor no mueve ni
        confirma hasta que termine su bloqueo (Online/sabotaje.py), y el
        invitado manda la tecla al host. False si no se movió nada."""
        nonlocal aviso_sabotaje
        cuarto = getattr(mazmorra, "cuarto", None) if mazmorra is not None else None
        terminal = getattr(cuarto, "terminal", None)
        if terminal is None or not campania.puede_decidir(actor):
            return False
        # Con la terminal: el bloqueo corre desde que se ve, no desde el
        # próximo actualizar del adaptador.
        if hasattr(adaptador_red, "puede_navegar") and not adaptador_red.puede_navegar(actor, terminal):
            aviso_sabotaje = assets.DURACION_AVISO_SABOTAJE
            return False
        if direccion == CONFIRMAR:
            campania.registrar_actor(actor)
        if hasattr(adaptador_red, "enviar_decision_nav"):
            adaptador_red.enviar_decision_nav(direccion)
        terminal.navegar(direccion)
        return True

    # --- Online: reunión de emergencia (Online/reunion.py) -----------------
    # El host lleva la votación; esta PC solo guarda lo que escribe, qué
    # opción enfoca, cuál espera el segundo Enter/clic y qué votó.
    texto_chat = ""
    seleccion_voto = None
    voto_armado = None
    voto_local = None  # (número de reunión, objetivo) que votó esta PC
    numero_reunion = 0  # la última reunión que vio esta PC
    resultado_sonado = 0  # la última votación cuyo resultado ya sonó
    en_reunion = False  # reunión, publicación del sabotaje o fin: el mundo espera
    tiempo_fin = 0.0  # s desde que terminó la partida Online (Enter vuelve al menú)
    numero_sabotaje = 0  # la última publicación del sabotaje que vio esta PC
    resultado_sabotaje_sonado = 0

    def vista_reunion():
        return adaptador_red.estado_reunion() if hasattr(adaptador_red, "estado_reunion") else None

    def mi_voto(vista):
        return voto_local[1] if voto_local is not None and voto_local[0] == vista.numero else None

    def vista_sabotaje():
        return adaptador_red.estado_sabotaje() if hasattr(adaptador_red, "estado_sabotaje") else None

    def evento_red_en_curso():
        """Reunión, publicación del sabotaje, sus resultados o el fin de la partida."""
        return bool(hasattr(adaptador_red, "evento_red_en_curso") and adaptador_red.evento_red_en_curso())

    def rects_botones():
        """(REPORTAR, SABOTEAR) a la izquierda, según la escena (Online/disposicion_hud.py)."""
        return disposicion_hud.rects_botones(escena, len(jugadores), getattr(preferencias, "hud_detallado", False))

    def boton_reportar_visible(vista):
        """Online con impostor en juego, el mundo en marcha, sin modal y sin
        haber sido expulsado ni descubierto ya al impostor."""
        return (vista is not None and len(jugadores) >= 2 and any(getattr(j, "es_impostor", False) for j in jugadores)
                and escena in ESCENAS_BOTON_REPORTAR and not evento_red_en_curso() and dialogo is None
                and not pantalla_historia_abierta() and indicador_rep is None
                and indice_local not in vista.expulsados and not vista.impostor_descubierto)

    def boton_sabotear_visible(vista):
        """Solo para el impostor (no expulsado), con el mundo en marcha."""
        return (boton_reportar_visible(vista) and escena in ESCENAS_BOTON_SABOTEAR
                and getattr(jugador, "es_impostor", False) and vista_sabotaje() is not None)

    def reportar():
        """REPORTAR desde esta PC (tecla R o clic). True si la tecla era suya."""
        vista = vista_reunion()
        if not boton_reportar_visible(vista):
            return False
        if vista.recarga <= 0.0:
            adaptador_red.convocar_reunion(indice_local)
        return True

    def sabotear():
        """SABOTEAR desde esta PC (tecla Q o clic): solo el impostor."""
        if not boton_sabotear_visible(vista_reunion()):
            return False
        if vista_sabotaje().recarga <= 0.0:
            adaptador_red.sabotear(indice_local)
        return True

    def navegar_post(direccion):
        """Tecla en la publicación del sabotaje (la decide el host)."""
        nonlocal aviso_sabotaje
        if not adaptador_red.navegar_sabotaje(indice_local, direccion) and getattr(jugador, "es_impostor", False):
            aviso_sabotaje = assets.DURACION_AVISO_SABOTAJE

    def votar(vista, objetivo):
        nonlocal voto_local, voto_armado
        if adaptador_red.votar_reunion(indice_local, objetivo):
            voto_local = (vista.numero, objetivo)
        voto_armado = None

    def manejar_evento_reunion(evento, vista):
        """Con la reunión abierta, esta PC solo chatea y vota: las teclas no
        llegan al juego. Elegir y confirmar: Enter (o clic) dos veces."""
        nonlocal texto_chat, seleccion_voto, voto_armado
        if not vista.activa:
            return  # se está mostrando el resultado
        escribe = indice_local in vista.candidatos
        puede_votar = escribe and indice_local not in vista.votaron and mi_voto(vista) is None
        opciones = reunion_render.opciones_de_voto(vista)
        if evento.type == pygame.TEXTINPUT:
            if escribe:
                texto_chat = (texto_chat + evento.text)[:MAX_LARGO_MENSAJE_REUNION]
            return
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            objetivo = reunion_render.objetivo_en(evento.pos, vista.candidatos)
            if objetivo is not None and puede_votar:
                if voto_armado == objetivo:
                    votar(vista, objetivo)
                else:
                    seleccion_voto = voto_armado = objetivo
            return
        direccion = None
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_BACKSPACE:
                texto_chat = texto_chat[:-1]
                return
            if evento.key == TECLA_SALIR:
                voto_armado = None
                return
            if evento.key in TECLAS_CONFIRMAR:
                if texto_chat.strip():
                    adaptador_red.escribir_reunion(indice_local, texto_chat)
                    texto_chat = ""
                    return
                direccion = CONFIRMAR
            elif evento.key in (pygame.K_LEFT, pygame.K_UP):
                direccion = IZQUIERDA
            elif evento.key in (pygame.K_RIGHT, pygame.K_DOWN):
                direccion = DERECHA
        elif evento.type == pygame.CONTROLLERBUTTONDOWN:
            if evento.button == BOTON_CANCELAR:
                voto_armado = None
                return
            direccion = BOTONES_NAV_HISTORIA.get(evento.button)
        if direccion is None or not puede_votar:
            return
        if seleccion_voto not in opciones:
            seleccion_voto = opciones[0]
        if direccion in (IZQUIERDA, DERECHA):
            paso = -1 if direccion == IZQUIERDA else 1
            seleccion_voto = opciones[(opciones.index(seleccion_voto) + paso) % len(opciones)]
            voto_armado = None
        elif direccion == CONFIRMAR:
            if voto_armado == seleccion_voto:
                votar(vista, seleccion_voto)
            else:
                voto_armado = seleccion_voto

    def _dibujar_capa_reunion(modal):
        """Encima de todo: el fin de la partida, la reunión, la publicación del
        sabotaje, sus resultados o los botones REPORTAR y SABOTEAR."""
        vista = vista_reunion()
        if vista is None:
            return
        vista_sab = vista_sabotaje()
        if vista.fin is not None:
            puede_salir = tiempo_fin >= assets.ESPERA_SALIR_FIN_PARTIDA
            reunion_render.dibujar_fin_partida(pantalla, vista, jugadores, indice_local, tiempo_fin)
            if puede_salir:
                hud.dibujar_barra_controles(pantalla, assets.CONTROLES_FIN_PARTIDA)
            return
        if vista_sab is not None and vista_sab.activo:
            _dibujar_post_sabotaje(vista_sab)
            return
        if vista_sab is not None and vista_sab.mostrando_resultado:
            reunion_render.dibujar_resultado_post(pantalla, vista_sab)
            return
        if vista.activa:
            reunion_render.dibujar_reunion(pantalla, vista, jugadores, indice_local, seleccion_voto, voto_armado,
                                           mi_voto(vista), texto_chat, tiempo_overlay)
            hud.dibujar_barra_controles(pantalla, assets.CONTROLES_REUNION)
        elif vista.mostrando_resultado:
            reunion_render.dibujar_resultado_reunion(pantalla, vista, jugadores, tiempo_overlay)
        elif modal is None and boton_reportar_visible(vista):
            rect_reportar, rect_sabotear = rects_botones()
            reunion_render.dibujar_boton_reportar(pantalla, vista.recarga, COOLDOWN_REUNION, tiempo_overlay, rect_reportar)
            if boton_sabotear_visible(vista) and rect_sabotear is not None:
                reunion_render.dibujar_boton_sabotear(pantalla, vista_sab.recarga, COOLDOWN_POST_SABOTAJE, tiempo_overlay,
                                                      rect_sabotear)
        elif modal is None and escena in ESCENAS_BOTON_REPORTAR and dialogo is None \
                and any(getattr(j, "es_impostor", False) for j in jugadores):
            if indice_local in vista.expulsados:
                reunion_render.dibujar_aviso_red(pantalla, assets.TEXTO_AVISO_FANTASMA, assets.COLOR_GRAVE,
                                                 rects_botones()[0])
            elif vista.impostor_descubierto:
                reunion_render.dibujar_aviso_red(pantalla, assets.TEXTO_IMPOSTOR_DESCUBIERTO, assets.COLOR_IMPOSTOR,
                                                 rects_botones()[0])
        aviso = adaptador_red.aviso_version() if hasattr(adaptador_red, "aviso_version") else None
        if aviso and modal is None:
            dibujo.chip(pantalla, aviso, assets.POSICION_AVISO_VERSION, assets.COLOR_ALERTA, assets.COLOR_FONDO_PANEL,
                        assets.COLOR_ALERTA, assets.TAMANIO_FUENTE_PEQUENA, ancla="center", alto=30, margen=12)

    def _dibujar_post_sabotaje(vista_sab):
        """La publicación viral con la terminal tipo celular (pantalla completa)."""
        terminal = adaptador_red.terminal_sabotaje()
        post = adaptador_red.post_sabotaje(vista_sab.indice_post)
        if terminal is None or post is None:
            return
        expulsado_local = indice_local in vista_reunion().expulsados
        dibujar_terminal(pantalla, terminal, assets.TEXTO_SUBTITULO_POST_SABOTAJE, post=post, evidencias=[],
                         total_evidencias=0, tiempo=tiempo_overlay, zona=post.get("zona"),
                         nota_decisor=assets.TEXTO_AVISO_FANTASMA if expulsado_local else "")
        if getattr(jugador, "es_impostor", False) and not expulsado_local:
            sabotaje_render.dibujar_sabotaje(pantalla, vista_sab.bloqueo, aviso_sabotaje, BLOQUEO_POST_SABOTAJE)
            hud.dibujar_barra_controles(pantalla, sabotaje_render.CONTROLES_IMPOSTOR)
        else:
            reunion_render.dibujar_alerta_post(pantalla, tiempo_overlay)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_TERMINAL)

    def presentar():
        """Overlays de la historia encima de lo que dibujó la escena, en
        orden de capas (src/ui/layout.py): paneles, un único modal, avisos."""
        # Capa de paneles (no modales).
        if tarjeta_evidencia is not None and escena in ESCENAS_DE_COMBATE and dialogo is None:
            tarjetas_render.dibujar_tarjeta_evidencia(pantalla, assets.RECT_TARJETA_EVIDENCIA, tarjeta_evidencia[0])
        if pantalla_historia_abierta():
            _dibujar_pantalla_historia()
            _dibujar_capa_reunion("historia")
            presentar_frame()
            return
        # Un único modal a la vez.
        activos = {
            "cinematica": isinstance(dialogo, Cinematica),
            "dialogo": dialogo is not None and not isinstance(dialogo, Cinematica),
            "ayuda": mostrar_ayuda and escena == Escena.CIUDAD,
            "estado": mostrar_estado and escena == Escena.CIUDAD,
        }
        modal = layout.modal_prioritario({nombre for nombre, activo in activos.items() if activo})
        if modal == "cinematica":
            cinematica_render.dibujar_cinematica(pantalla, dialogo, 0.0, preferencias.reducir_movimiento)
        elif modal == "dialogo":
            dialogo_render.dibujar_dialogo(pantalla, dialogo, tiempo, tiempo_overlay)
            hud.dibujar_barra_controles(pantalla, hud.CONTROLES_DIALOGO)
        elif modal == "ayuda":
            ayuda_render.dibujar_ayuda(pantalla, tiempo_overlay)
        elif modal == "estado":
            indicadores_render.dibujar_panel_estado(pantalla, campania, transcurrido=tiempo_overlay)
        if espera_equipo and modal is None:
            dibujo.chip(pantalla, _texto_espera_lectura(lectores_red), assets.POSICION_AVISO_ESPERA_LECTURA,
                        assets.COLOR_TEXTO_HUD, assets.COLOR_FONDO_PANEL, assets.COLOR_CIVITAS,
                        assets.TAMANIO_FUENTE_NORMAL, ancla="center", alto=32, margen=14)
        # Avisos encima de todo (solo el más reciente, para no apilar).
        if toasts and modal != "cinematica" and (escena == Escena.CIUDAD or escena in ESCENAS_DE_COMBATE):
            texto_toast, restante_toast, titulo_toast = toasts[0]
            mision_render.dibujar_toast_objetivo(pantalla, texto_toast, restante_toast, titulo=titulo_toast)
        if feed_ciudad is not None and modal is None and escena == Escena.CIUDAD and not mostrar_mapa_mundo:
            feed_render.dibujar_feed(pantalla, feed_ciudad[0], feed_ciudad[1], feed_ciudad[2])
        if indicador_rep is not None:
            reputacion_render.dibujar_indicador(pantalla, indicador_rep)
        _dibujar_capa_reunion(modal)
        presentar_frame()

    def pantalla_historia_abierta():
        return eleccion_crisis is not None or etapa_abierta is not None or final_derrota is not None

    def _dibujar_pantalla_historia():
        datos = campania.contenido["redencion"]
        if final_derrota is not None:
            redencion_render.dibujar_final_derrota(pantalla, final_derrota)
        elif eleccion_crisis is not None:
            redencion_render.dibujar_eleccion(pantalla, eleccion_crisis, datos, tiempo_historia)
        else:
            mision_abierta = campania.mision_de(etapa_abierta)
            if mision_abierta is not None:
                redencion_render.dibujar_etapa(pantalla, mision_abierta, datos, tiempo_historia)

    def navegar_historia(direccion):
        """Enter y flechas en las pantallas de crisis, misión y final."""
        nonlocal eleccion_crisis, etapa_abierta, final_derrota, crisis_en_curso, final_pendiente, escena, fundido, tiempo_historia
        # Un Enter de más al salir de una cinemática no debe decidir por el jugador.
        if tiempo_historia < assets.PAUSA_ANTES_DE_DECIDIR:
            return
        if final_derrota is not None:
            final_derrota.navegar(direccion)
            if final_derrota.resultado is None:
                return
            indice, eleccion = final_derrota.indice_jugador, final_derrota.resultado
            final_derrota = None
            if eleccion == redencion_render.FinalDerrota.REINTENTAR:
                accion_historia("reintentar", indice)
                crisis_en_curso = indice
                eleccion_crisis = EleccionCrisis()
                tiempo_historia = 0.0
            elif eleccion == redencion_render.FinalDerrota.NUEVA:
                reiniciar_partida()
                escena = _volver_a_la_ciudad(jugador, partida)
                fundido = assets.DURACION_FUNDIDO
            sonar("mision")
            return
        if eleccion_crisis is not None:
            eleccion_crisis.navegar(direccion)
            if eleccion_crisis.resultado is None:
                sonar(navegacion.SONIDO_NAVEGAR)
                return
            indice = crisis_en_curso
            aceptada = eleccion_crisis.resultado == EleccionCrisis.ACEPTAR
            eleccion_crisis = None
            crisis_en_curso = None
            if aceptada:
                accion_historia("aceptar", indice)
                etapa_abierta = indice
                tiempo_historia = 0.0
                sonar("redencion")
            else:
                accion_historia("rechazar", indice)
                encolar_historia(campania.guion_de_rechazo())
                final_pendiente = indice
            return
        mision_abierta = campania.mision_de(etapa_abierta) if etapa_abierta is not None else None
        if mision_abierta is None:
            etapa_abierta = None
            return
        etapa_antes, errores_antes = mision_abierta.etapa, mision_abierta.errores
        mision_abierta.navegar(direccion)
        if mision_abierta.errores > errores_antes:
            sonar("error_decision")
        elif mision_abierta.etapa != etapa_antes:
            sonar("mision")
        if mision_abierta.completada:
            indice = etapa_abierta
            etapa_abierta = None
            origenes = [c.origen for c in mision_abierta.correcciones]
            accion_historia("completar", indice, origenes=origenes)
            encolar_historia(campania.guion_recuperacion(campania.roles.get(indice), jugadores[indice].NOMBRE))
        elif mision_abierta.fallida:
            indice = etapa_abierta
            etapa_abierta = None
            accion_historia("fallar", indice)
            encolar_historia(campania.guion_de_rechazo())
            final_pendiente = indice
        elif mision_abierta.etapa in (ETAPA_CORREGIR, ETAPA_CONFIANZA) and mision_abierta.etapa != etapa_antes:
            # Las siguientes etapas se abren en su lugar de la ciudad.
            etapa_abierta = None
            toasts.append(["Sigue la baliza en la ciudad", assets.DURACION_TOAST_MISION, "Misión actualizada"])

    while True:
        # tick_busy_loop y no tick: en Windows tick() duerme con poca
        # precisión y los frames salen de 16, 17 o 18 ms, lo que se ve
        # como tirones al moverse. busy_loop da frames regulares.
        dt = reloj.tick_busy_loop(FPS) / 1000
        if audio is not None:
            audio.actualizar(dt)
        if pausa.abierta:
            salida_pausa = atender_pausa()
            if salida_pausa is not None:
                return salida_pausa
            if pausa.abierta and pausa.congelada:
                # Congelada: el bucle no llama a ningún actualizar (enemigos,
                # proyectiles, gracia, terminal, colapso, propagación, cintillo):
                # solo se redibuja el último frame con el menú encima.
                if fondo_pausa is not None:
                    pantalla.blit(fondo_pausa, (0, 0))
                presentar_frame()
                continue
        if instrucciones is not None and dialogo is None and indicador_rep is None and not pausa.abierta:
            # Instrucciones de mazmorra: el mundo espera (ni gracia, ni fundido, ni enemigos).
            if atender_instrucciones(dt) == SALIR:
                return SALIR
            continue
        tiempo += dt
        fundido = max(0.0, fundido - dt)
        if estado_hud["escena"] != escena:
            estado_hud["escena"] = escena
            estado_hud["controles"] = assets.DURACION_CONTROLES_AYUDA  # unos segundos al entrar a cada escena
        estado_hud["controles"] = max(0.0, estado_hud["controles"] - dt)
        estado_hud["mision"] = max(0.0, estado_hud["mision"] - dt)
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
            vista_actual = vista_reunion()
            if vista_actual is not None and vista_actual.fin is not None:
                # Terminó la partida: tras unos segundos, Enter vuelve al menú.
                if tiempo_fin >= assets.ESPERA_SALIR_FIN_PARTIDA and (
                        (evento.type == pygame.KEYDOWN and evento.key in TECLAS_SALIR_FIN_PARTIDA)
                        or (evento.type == pygame.CONTROLLERBUTTONDOWN and evento.button in (BOTON_CONFIRMAR, BOTON_CANCELAR))):
                    sesion.partida_online_terminada = True
                    return MENU
                continue
            vista_sab = vista_sabotaje()
            if vista_sab is not None and vista_sab.en_curso:
                # Publicación viral del sabotaje: solo se elige (o se espera su resultado).
                if vista_sab.activo:
                    if evento.type == pygame.KEYDOWN and evento.key in TECLAS_TERMINAL:
                        navegar_post(TECLAS_TERMINAL[evento.key])
                    elif evento.type == pygame.CONTROLLERBUTTONDOWN and BOTONES_NAV_HISTORIA.get(evento.button):
                        navegar_post(BOTONES_NAV_HISTORIA[evento.button])
                continue
            if vista_actual is not None and vista_actual.en_curso:
                # Reunión de emergencia: se lleva el teclado, el ratón y el control.
                manejar_evento_reunion(evento, vista_actual)
                continue
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 \
                    and reunion_render.en_boton(evento.pos, rects_botones()[0]) and reportar():
                continue
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 \
                    and reunion_render.en_boton(evento.pos, rects_botones()[1]) and sabotear():
                continue
            if evento.type == pygame.CONTROLLERBUTTONDOWN:
                # El control también navega la historia y la terminal (J2 en cooperativo).
                direccion_mando = BOTONES_NAV_HISTORIA.get(evento.button)
                if indicador_rep is not None:
                    if direccion_mando == NAV_CONFIRMAR:
                        indicador_rep.avanzar()
                elif pantalla_historia_abierta():
                    if direccion_mando is not None:
                        navegar_historia(direccion_mando)
                elif dialogo is not None:
                    if evento.button == BOTON_CONFIRMAR:
                        dialogo.avanzar()
                    elif evento.button == BOTON_CANCELAR:
                        dialogo.saltar()
                    if _overlay_terminado(dialogo):
                        siguiente_historia()
                elif escena == Escena.DECISION and direccion_mando is not None:
                    # El mismo camino que el teclado: bloqueo del impostor y envío al host.
                    navegar_terminal(1 if len(jugadores) > 1 and adaptador_red is None else indice_local, direccion_mando)
                continue
            if evento.type != pygame.KEYDOWN:
                continue
            if evento.key == TECLA_SILENCIO:
                if audio is not None:
                    audio.alternar_silencio()
                continue
            if evento.key == TECLA_AYUDA:
                estado_hud["controles"] = assets.DURACION_CONTROLES_AYUDA  # H: los controles, 3 s
            if indicador_rep is not None:
                # El indicador de reputación se lleva Enter hasta cerrarse.
                if evento.key in TECLAS_DIALOGO_AVANZAR:
                    indicador_rep.avanzar()
                continue
            if pantalla_historia_abierta():
                if evento.key == TECLA_SALIR and etapa_abierta is not None:
                    etapa_abierta = None  # la misión queda en pausa
                elif evento.key in TECLAS_NAV_HISTORIA:
                    navegar_historia(TECLAS_NAV_HISTORIA[evento.key])
                continue
            if evento.key == TECLA_REPORTAR and dialogo is None and reportar():
                continue
            if evento.key == TECLA_SABOTEAR and dialogo is None and sabotear():
                continue
            if (evento.key in TECLAS_PAUSA and dialogo is None
                    and not (escena == Escena.CIUDAD and (mostrar_estado or mostrar_ayuda))
                    and abrir_pausa()):
                continue
            if dialogo is not None:
                # Un diálogo o cinemática abiertos se quedan con todas las teclas.
                if evento.key in TECLAS_DIALOGO_AVANZAR:
                    dialogo.avanzar()
                elif evento.key in TECLAS_DIALOGO_SALTAR:
                    dialogo.saltar()
                if _overlay_terminado(dialogo):
                    siguiente_historia()
            elif escena == Escena.CIUDAD:
                # La escena CIUDAD consume todas sus teclas (sin disparo ni F).
                if evento.key == TECLA_ENTRAR and getattr(jugador, "expulsado", False):
                    toasts.append([assets.TEXTO_AVISO_FANTASMA, 2.0, "Expulsado"])
                    continue
                if evento.key == TECLA_ENTRAR and not mostrar_mapa_mundo:
                    # Una etapa de la misión de redención tiene prioridad sobre la puerta.
                    baliza = _baliza_cercana(campania, indices_locales, jugador)
                    if baliza is not None:
                        etapa_abierta = baliza
                        tiempo_historia = 0.0
                        sonar("transicion")
                        continue
                if evento.key == TECLA_SALIR:
                    # Con Estado o Ayuda abiertos, Esc los cierra (si no, abrió la pausa).
                    mostrar_estado = mostrar_ayuda = False
                    continue
                if evento.key == TECLA_ESTADO_CIUDAD:
                    mostrar_estado = not mostrar_estado
                    mostrar_ayuda = False
                    tiempo_overlay = 0.0
                elif evento.key == TECLA_AYUDA:
                    mostrar_ayuda = not mostrar_ayuda
                    mostrar_estado = False
                    tiempo_overlay = 0.0
                elif evento.key == TECLA_MAPA_MUNDO:
                    mostrar_mapa_mundo = not mostrar_mapa_mundo
                elif evento.key == TECLA_DESTINO:
                    selector.mover(DERECHA)
                    estado_hud["mision"] = assets.DURACION_MISION_ABIERTA
                elif evento.key == TECLA_RUTA and not mostrar_mapa_mundo:
                    mostrar_ruta = not mostrar_ruta
                    sonar("ruta")
                elif evento.key == TECLA_ENTRAR and not mostrar_mapa_mundo:
                    zona = ciudad_mapa.entrada_cercana(_posicion(jugador))
                    if zona is None or (zona == ZONA_FINAL and not partida.alcaldia_desbloqueada()):
                        continue
                    entrar_a_zona(zona)
            elif escena == Escena.DECISION:
                if evento.key in TECLAS_TERMINAL:
                    navegar_terminal(indice_local, TECLAS_TERMINAL[evento.key])
            elif escena == Escena.RESULTADO:
                if investigacion is not None and not investigacion.terminada:
                    if evento.key in TECLAS_TERMINAL and not (hasattr(adaptador_red, "expulsado")
                                                              and adaptador_red.expulsado(indice_local)):
                        direccion = TECLAS_TERMINAL[evento.key]
                        adaptador = getattr(sesion, "adaptador_red", None)
                        if adaptador is not None and hasattr(adaptador, "enviar_decision_nav"):
                            adaptador.enviar_decision_nav(direccion)  # invitado: vota en el host
                        else:
                            investigacion.navegar(direccion)
                        if investigacion.terminada and not campania.espejo:
                            campania.registrar_investigacion(investigacion.resultado, indice_local)
                    continue
                if evento.key in TECLAS_CONFIRMAR:
                    if propagacion_pendiente:
                        # Primero cómo viajó la publicación por la red social.
                        propagacion_pendiente = False
                        mostrar_propagacion = True
                        tiempo_propagacion = 0.0
                        sonar("viral")
                        continue
                    mostrar_propagacion = False
                    if investigacion is None and resultado is not None \
                            and campania.investigacion_pendiente(resultado.zona):
                        # Capítulo 3: ¿de dónde sale la señal?
                        investigacion = campania.nueva_investigacion()
                        sesion.investigacion_activa = investigacion
                        continue
                    sesion.investigacion_activa = None
                    investigacion = None
                    resultado = None
                    escena = _volver_a_la_ciudad(jugador, partida)
                    fundido = assets.DURACION_FUNDIDO
                    # Al volver, la ciudad sigue viva: un evento al azar
                    # (su titular entra al cintillo de noticias).
                    if not campania.espejo:
                        campania.sortear_evento()
                    reloj_reaccion = 1.5  # enseguida alguien comenta lo ocurrido
            elif escena in (Escena.VICTORIA, Escena.DERROTA):
                if evento.key in TECLAS_CONFIRMAR:
                    if escena == Escena.VICTORIA and not mostrar_elecciones:
                        # Epílogo: elecciones simuladas (las barras se llenan).
                        mostrar_elecciones = True
                        tiempo_elecciones = 0.0
                        sonar("mision")
                        continue
                    if escena == Escena.VICTORIA and not final_presentado:
                        # Revelación del final según los datos reales de la partida.
                        final_presentado = True
                        resumen = resumen_final(campania)
                        encolar_historia(guion_final(resumen["clave"], resumen["titulo"], resumen["texto"], resumen["epilogo"]))
                        continue
                    mostrar_elecciones = False
                    final_presentado = victoria_presentada = False
                    if escena == Escena.DERROTA:
                        reiniciar_partida()
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
                escenario_evento = _escenario_activo(escena, arena, mazmorra)
                if escenario_evento is not None and hasattr(escenario_evento, "manejar_evento"):
                    escenario_evento.manejar_evento(evento)

        # --- Actualización, según la escena ----------------------------
        escenario = _escenario_activo(escena, arena, mazmorra)
        for j in jugadores:
            j.actualizar_habilidad(dt)
        textos.actualizar(dt)
        particulas.actualizar(dt)

        if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None:
            escena_antes_red = escena
            escena, arena, mazmorra, fundido = sesion.adaptador_red.actualizar(
                escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador
            )
            if getattr(sesion.adaptador_red, "resultado_remoto", None) is not None:
                resultado = sesion.adaptador_red.resultado_remoto
                sesion.adaptador_red.resultado_remoto = None
            # El adaptador pudo llevar al jugador a otra escena (p. ej. a la
            # mazmorra donde entró el otro): el escenario se vuelve a calcular,
            # si no, el combate corría sobre el de la ciudad (None) y se cerraba.
            escena = normalizar_escena(escena, arena, mazmorra, resultado, jugador, partida)
            escenario = _escenario_activo(escena, arena, mazmorra)
            # La red trajo al equipo a un edificio (entró otro jugador): la
            # misma presentación que con la E propia, también en esta PC.
            if escena_antes_red == Escena.CIUDAD and escena in ESCENAS_DE_COMBATE:
                al_entrar_a_zona(partida.ubicacion)
            vista_actual = vista_reunion()
            if vista_actual is not None and vista_actual.numero != numero_reunion:
                # Empezó otra reunión: chat, foco y voto de esta PC desde cero
                # (también se va la "r" que la convocó, si llegó como texto).
                numero_reunion = vista_actual.numero
                texto_chat, seleccion_voto, voto_armado = "", None, None
                sonar("crisis")
            if vista_actual is not None and vista_actual.mostrando_resultado and resultado_sonado != vista_actual.numero:
                resultado_sonado = vista_actual.numero
                sonar("decision_buena" if vista_actual.era_impostor else
                      "decision_mala" if vista_actual.expulsado is not None else "notificacion")
            if vista_actual is not None:
                # El expulsado es un fantasma en todas las PCs (src/core/equipo.py).
                for _i_fantasma, _j_fantasma in enumerate(jugadores):
                    _j_fantasma.expulsado = _i_fantasma in vista_actual.expulsados
                if vista_actual.fin is not None:
                    if tiempo_fin == 0.0:
                        gano_esta_pc = (vista_actual.fin == "tripulacion") != (indice_local == vista_actual.impostor)
                        sonar("victoria" if gano_esta_pc else "derrota")
                    tiempo_fin += dt
            vista_sab = vista_sabotaje()
            if vista_sab is not None and vista_sab.numero != numero_sabotaje:
                numero_sabotaje = vista_sab.numero
                sonar("viral")
            if vista_sab is not None and vista_sab.mostrando_resultado and resultado_sabotaje_sonado != vista_sab.numero:
                resultado_sabotaje_sonado = vista_sab.numero
                sonar("decision_buena" if vista_sab.resultado == PURIFICACION_EXITOSA else "decision_mala")

        # Con un diálogo o cinemática abiertos el mundo queda quieto (ni
        # caminar ni combate) y la tarjeta de evidencia espera a que termine.
        tiempo_overlay += dt
        tiempo_historia += dt
        aviso_sabotaje = max(0.0, aviso_sabotaje - dt)
        if escena != escena_avisos:
            # Un aviso de la mazmorra no debe aparecer ya de vuelta en la ciudad.
            escena_avisos = escena
            toasts.clear()
        if dialogo is not None:
            dialogo.actualizar(dt)
        if isinstance(dialogo, Cinematica):
            sonar(dialogo.tomar_sonido())
            if dialogo.terminada:
                siguiente_historia()
        if final_derrota is not None:
            final_derrota.actualizar(dt)
        if indicador_rep is not None:
            indicador_rep.actualizar(dt)
            if indicador_rep.cerrado:
                indicador_rep = None
        # El equipo se fue a una mazmorra (Online): la crisis espera a volver.
        if escena != Escena.CIUDAD and (crisis_en_curso is not None or etapa_abierta is not None):
            crisis_en_curso = etapa_abierta = eleccion_crisis = None
        sesion.historia_ocupada = dialogo is not None or pantalla_historia_abierta() or indicador_rep is not None
        en_dialogo = sesion.historia_ocupada
        # Online: en la reunión de emergencia (y su resultado) el mundo espera en todas las PCs.
        en_reunion = evento_red_en_curso()
        # Online, en combate: el mundo también espera a quien siga leyendo en
        # otra PC (la tarjeta del capítulo, la cinemática del jefe...), así a
        # nadie lo atacan mientras lee.
        lectores_red = adaptador_red.esperando_lectura() if hasattr(adaptador_red, "esperando_lectura") else []
        espera_equipo = escena in ESCENAS_DE_COMBATE and bool(lectores_red) and not en_dialogo
        # Cada cambio de reputación se presenta en una pausa segura (nunca en combate).
        if indicador_rep is None and dialogo is None and not pantalla_historia_abierta() \
                and escena in (Escena.CIUDAD, Escena.RESULTADO):
            for _i in indices_locales:
                cambio = campania.rep(_i).tomar_pendiente()
                if cambio is not None:
                    indicador_rep = reputacion_render.IndicadorReputacion(cambio)
                    sonar("reputacion_sube" if cambio.delta > 0 else "reputacion_baja" if cambio.delta < 0 else "notificacion")
                    break
        # Crisis: se presenta al volver a la ciudad, nunca en plena acción.
        if escena == Escena.CIUDAD and not en_dialogo and indicador_rep is None and crisis_en_curso is None:
            en_crisis = campania.jugador_en_crisis(indices_locales)
            if en_crisis is not None:
                crisis_en_curso = en_crisis
                encolar_historia(campania.guion_de_crisis(en_crisis, jugadores[en_crisis].NOMBRE, campania.roles.get(en_crisis)))
                en_dialogo = True
        if dialogo is None and crisis_en_curso is not None and eleccion_crisis is None:
            eleccion_crisis = EleccionCrisis()
            tiempo_historia = 0.0
            sonar("crisis")
        if dialogo is None and final_pendiente is not None and final_derrota is None:
            hay_equipo = not campania.todos_sin_voz()
            final_derrota = redencion_render.FinalDerrota(final_pendiente, campania.balance_final_individual(final_pendiente),
                                                          puede_seguir=hay_equipo, puede_reiniciar=not campania.espejo)
            final_pendiente = None
            tiempo_historia = 0.0
        # Comentarios de los ciudadanos según la reputación.
        if feed_ciudad is not None:
            feed_ciudad = (feed_ciudad[0], feed_ciudad[1], feed_ciudad[2] - dt)
            if feed_ciudad[2] <= 0:
                feed_ciudad = None
        if escena == Escena.CIUDAD and not en_dialogo:
            reloj_reaccion -= dt
            if reloj_reaccion <= 0:
                reloj_reaccion = assets.PERIODO_REACCION_CIUDAD
                texto_feed, nivel_feed = campania.reaccion_ciudadana(indice_local)
                feed_ciudad = (texto_feed, nivel_feed, assets.DURACION_FEED_CIVITAS)
                sonar("notificacion")
        if tarjeta_evidencia is None:
            evidencia_nueva = campania.tomar_evidencia_nueva()
            if evidencia_nueva is not None:
                tarjeta_evidencia = (evidencia_nueva, assets.DURACION_TARJETA_EVIDENCIA)
                sonar("evidencia")
        if tarjeta_evidencia is not None and not en_dialogo:
            restante = tarjeta_evidencia[1] - dt
            tarjeta_evidencia = (tarjeta_evidencia[0], restante) if restante > 0 else None
        if toasts:
            toasts[0][1] -= dt
            if toasts[0][1] <= 0:
                toasts.pop(0)
        if audio is not None:
            audio.procesar_eventos()
        else:
            eventos_sonido.drenar()
        if escena == Escena.CIUDAD and escena_previa != Escena.CIUDAD and tiempo_mensaje_mapa > 0:
            sonar("noticia")  # vuelve a la ciudad con un titular nuevo
        escena_previa = escena
        toma_actual = dialogo.actual if isinstance(dialogo, Cinematica) else None
        musica(_pista_para(escena, toma_actual is not None, crisis_en_curso is not None,
                           campania.mision_de(indice_local) is not None or (toma_actual is not None and toma_actual.id.startswith("redencion")),
                           final_derrota is not None or final_pendiente is not None))

        if escena == Escena.CIUDAD and not mostrar_mapa_mundo and not en_dialogo and not mostrar_estado and not mostrar_ayuda \
                and not en_reunion:
            jugador.caminar_en_ciudad(pygame.key.get_pressed(), dt, partida.es_solida)
            if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None:
                sesion.adaptador_red.actualizar_ciudad(dt, partida, jugadores, jugador)
        elif escena in ESCENAS_DE_COMBATE and not en_dialogo and not espera_equipo and not en_reunion:
            _frame_de_combate(
                dt, jugadores, entradas, escenario, proyectiles_por_jugador, proyectiles_enemigos,
                textos, particulas, sacudida,
            )
            if escena == Escena.MAZMORRA:
                if mazmorra is not None and mazmorra.cambio_de_cuarto:
                    limpiar_combate()
                    revivir_caidos(jugadores)  # cooperativo: el caído vuelve en el cuarto nuevo
                    for j in jugadores:
                        j.detener()  # se aparece quieto junto a la puerta
                if mazmorra is not None and getattr(mazmorra, "mazmorra", None) is not None and not campania.espejo:
                    # Modo historia: cada cuarto limpio deja una prueba en el suelo;
                    # hay que ir a recogerla (el host decide, en red).
                    m_actual = mazmorra.mazmorra
                    limpios = len(m_actual.limpiados)
                    if limpios > limpios_vistos:
                        limpios_vistos = limpios
                        if campania.soltar_evidencia(m_actual.nombre_zona, m_actual.actual):
                            toasts.append(["Recógela antes de salir del cuarto", 2.4, "Prueba disponible"])
                            sonar("notificacion")
                    if campania.hay_evidencia_suelta(m_actual.nombre_zona, m_actual.actual):
                        punto = _punto_evidencia(mazmorra)
                        if any(pygame.Vector2(j.rect.center).distance_to(punto) < assets.RADIO_RECOGER_EVIDENCIA
                               for j in jugadores_en_combate(jugadores)):
                            campania.recoger_evidencia(m_actual.nombre_zona, m_actual.actual)
                if mazmorra is not None and getattr(mazmorra, "cuarto", None) is not None and mazmorra.cuarto.fase == FASE_DECISION:
                    escena = Escena.DECISION
                elif mazmorra is not None and todos_caidos(jugadores):
                    colapso_antes = partida.colapso.valor
                    partida.registrar_decision(mazmorra.mazmorra.nombre_zona, DETONACION)
                    colapso_despues = partida.colapso.valor
                    resultado = ResultadoMazmorra(
                        DETONACION, "Derrota", colapso_antes, colapso_despues, mazmorra.mazmorra.nombre_zona
                    )
                    zona_nombre = mazmorra.mazmorra.nombre_zona
                    if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None and hasattr(sesion.adaptador_red, "notificar_resultado"):
                        sesion.adaptador_red.notificar_resultado(resultado)
                    mazmorra = None
                    mensaje_mapa = (
                        f"{zona_nombre}: {DETONACION}",
                        assets.COLOR_MAGENTA,
                    )
                    tiempo_mensaje_mapa = assets.DURACION_MENSAJE_MAPA
                    escena = Escena.RESULTADO
                    limpiar_combate()
            elif escena == Escena.JEFE and arena is not None and arena.mazmorra.estado == MAZMORRA_FINAL_GANADA:
                escena = Escena.VICTORIA
                if not victoria_presentada:
                    # Cinemática de la caída del servidor; el jefe cuenta una sola vez.
                    victoria_presentada = True
                    campania.registrar_jefe_derrotado()
                    limpiar_combate()
                    encolar_historia(guion_caida_servidor())
        elif escena == Escena.DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            limpiar_combate()
            if mazmorra is not None and getattr(mazmorra, "cuarto", None) is not None and mazmorra.cuarto.terminal is not None:
                terminal = mazmorra.cuarto.terminal
                if not en_reunion:
                    terminal.actualizar(dt)  # en la reunión el reloj de la terminal se detiene
                if terminal.resultado is not None:
                    # Única vía para aplicar la decisión: una vez por mazmorra.
                    colapso_antes = partida.colapso.valor
                    if not campania.espejo:
                        partida.cerrar_mazmorra(mazmorra.mazmorra, terminal.resultado, terminal)
                    mazmorra.cuarto.fase = FASE_RESUELTO
                    resultado = ResultadoMazmorra(
                        terminal.resultado, terminal.opcion_elegida,
                        colapso_antes, partida.colapso.valor, mazmorra.mazmorra.nombre_zona,
                        campania.ultima_consecuencia, dict(campania.ultimos_deltas),
                    )
                    tarjeta_evidencia = None
                    propagacion_pendiente = campania.ultima_propagacion is not None
                    sonar("decision_buena" if resultado.exito else "decision_mala")
                    if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None and hasattr(sesion.adaptador_red, "notificar_resultado"):
                        sesion.adaptador_red.notificar_resultado(resultado)
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
            if escena == Escena.DERROTA and not derrota_presentada:
                derrota_presentada = True
                encolar_historia(guion_derrota_global())
        # Misión visible: se deriva del estado; un objetivo recién cumplido avisa.
        mision = mision_actual(escena.value, campania, partida,
                               mazmorra.mazmorra if mazmorra is not None and getattr(mazmorra, "mazmorra", None) else None,
                               arena.mazmorra if arena is not None else None,
                               campania.mision_de(indice_local))
        for objetivo in rastreador.novedades(mision):
            toasts.append([objetivo.texto, assets.DURACION_TOAST_MISION,
                           mision_render.TEXTO_TOAST_MISION if mision.completada else mision_render.TEXTO_TOAST])
            sonar("mision")
        if escena == Escena.CIUDAD and derrota_presentada:
            derrota_presentada = False  # partida nueva: la próxima derrota vuelve a presentarse

        # --- Dibujo ----------------------------------------------------
        pantalla.fill(assets.COLOR_FONDO)
        if escena in (Escena.CIUDAD, Escena.DERROTA):
            mapa_abierto = mostrar_mapa_mundo and escena == Escena.CIUDAD
            bloques = bloques_hud(Escena.CIUDAD, mapa_abierto) if escena == Escena.CIUDAD and dialogo is None \
                else hud_visibilidad.bloques_visibles(Escena.CIUDAD, mapa_mundo=mapa_abierto) - {hud_visibilidad.CONTROLES}
            estado_hud["rect_mision"] = _dibujar_ciudad(
                pantalla, partida, jugador, selector.seleccionada, tiempo, mostrar_ruta, mapa_abierto, indice_local,
                bloques=bloques, mision=mision if not (mostrar_estado or mostrar_ayuda) else None,
                transcurrido_mision=tiempo_overlay)
            if escena == Escena.CIUDAD and not mostrar_mapa_mundo and not en_dialogo:
                _dibujar_baliza_mision(pantalla, campania, indices_locales, jugador, tiempo)
            if tiempo_mensaje_mapa > 0 and mensaje_mapa is not None and escena == Escena.CIUDAD:
                _dibujar_mensaje(pantalla, mensaje_mapa[0], mensaje_mapa[1], assets.POSICION_MENSAJE_MAPA)
            if escena == Escena.DERROTA:
                dibujar_derrota(pantalla)
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL)
            ciudad_render.dibujar_fundido(pantalla, fundido)
            presentar()
            sacudida = (0, 0)
            continue

        if escena == Escena.DECISION:
            if mazmorra is not None and getattr(mazmorra, "cuarto", None) is not None and mazmorra.cuarto.terminal is not None:
                zona_terminal = mazmorra.mazmorra.nombre_zona
                escenario_historia = campania.escenario_activo if campania.zona_activa == zona_terminal else None
                expulsado_local = bool(hasattr(adaptador_red, "expulsado") and adaptador_red.expulsado(indice_local))
                dibujar_terminal(
                    pantalla, mazmorra.cuarto.terminal,
                    f"{zona_terminal}  ·  {campania.titulo_capitulo(zona_terminal)}",
                    post=escenario_historia.post if escenario_historia is not None else None,
                    estado_evidencia=escenario_historia.estado if escenario_historia is not None else None,
                    evidencias=campania.evidencias_reveladas_de(zona_terminal),
                    total_evidencias=len(campania.evidencias_de(zona_terminal)),
                    verificacion=escenario_historia.resultado_verificacion if escenario_historia is not None else "",
                    exige_mas_pruebas=campania.exige_mas_pruebas,
                    tiempo=tiempo,
                    zona=zona_terminal,
                    nota_decisor="Expulsado: tu equipo decide por ti" if expulsado_local else
                    "" if campania.puede_decidir(indice_local) else "Sin voz: tu equipo decide por ti",
                )
                # Online: solo el impostor ve su sabotaje (Online/sabotaje_render.py).
                restante_sabotaje = adaptador_red.restante_sabotaje() if hasattr(adaptador_red, "restante_sabotaje") else None
                if jugador.es_impostor and restante_sabotaje is not None and not expulsado_local:
                    espera_sabotaje = adaptador_red.espera_sabotaje() if hasattr(adaptador_red, "espera_sabotaje") else None
                    sabotaje_render.dibujar_sabotaje(pantalla, restante_sabotaje, aviso_sabotaje, espera_sabotaje)
                    hud.dibujar_barra_controles(pantalla, sabotaje_render.CONTROLES_IMPOSTOR)
                else:
                    hud.dibujar_barra_controles(pantalla, hud.CONTROLES_TERMINAL)
            presentar()
            sacudida = (0, 0)
            continue

        if escena == Escena.RESULTADO:
            # Invitado: ve el mismo rastreo que el host (su navegación va al host).
            espejo_investigacion = getattr(adaptador_red, "investigacion_espejo", None)
            if campania.espejo and isinstance(espejo_investigacion, dict):
                if investigacion is None:
                    investigacion = campania.nueva_investigacion()
                investigacion.copiar_de(espejo_investigacion)
            if investigacion is not None:
                # Online (host): las navegaciones de los invitados también cuentan.
                adaptador = getattr(sesion, "adaptador_red", None)
                if adaptador is not None and hasattr(adaptador, "tomar_solicitudes_decision") \
                        and not investigacion.terminada:
                    for direccion in adaptador.tomar_solicitudes_decision():
                        investigacion.navegar(direccion)
                    if investigacion.terminada:
                        campania.registrar_investigacion(investigacion.resultado, getattr(adaptador, "ultimo_actor", 0))
                investigacion_render.dibujar_investigacion(pantalla, investigacion, tiempo)
            elif mostrar_propagacion:
                tiempo_propagacion += dt
                red_social_render.dibujar_pantalla_propagacion(pantalla, campania, tiempo_propagacion)
            else:
                dibujar_resultado(pantalla, resultado)
            presentar()
            sacudida = (0, 0)
            continue

        if escena == Escena.VICTORIA and mostrar_elecciones:
            tiempo_elecciones += dt
            elecciones_render.dibujar_elecciones(pantalla, resumen_final(campania), tiempo_elecciones,
                                                 mostrar_final=final_presentado)
            presentar()
            sacudida = (0, 0)
            continue

        escenario = _escenario_activo(escena, arena, mazmorra)
        if escenario is None:
            ciudad_render.dibujar_fundido(pantalla, fundido)
            presentar()
            sacudida = (0, 0)
            continue

        en_combate = jugadores_en_combate(jugadores)  # los caídos no se dibujan
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        if escena == Escena.MAZMORRA and mazmorra is not None and getattr(mazmorra, "mazmorra", None) is not None \
                and campania.hay_evidencia_suelta(mazmorra.mazmorra.nombre_zona, mazmorra.mazmorra.actual):
            feed_render.dibujar_prueba_suelta(lienzo, _punto_evidencia(mazmorra), tiempo)
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
        if getattr(jugador, "expulsado", False):
            _dibujar_fantasma(lienzo, jugador, tiempo)  # los demás no lo ven; él sí
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
        sacudida = arena.mazmorra.desplazamiento_sacudida() if (temblar and arena is not None) else (0, 0)
        pantalla.blit(lienzo, sacudida)

        # Solitario: el J1 va en el HUD superior. Cooperativo: arriba solo
        # el lugar, los enemigos y el colapso; cada jugador en su panel lateral.
        coop = len(jugadores) > 1
        jugador_hud, etiqueta_hud = (None, None) if coop else (jugador, "J1")
        enemigos_cant = len(escenario.enemigos) if escenario is not None else 0
        if escena in (Escena.JEFE, Escena.VICTORIA):
            ctx = hud_partida.ContextoHud(jugador=jugador_hud, etiqueta_jugador=etiqueta_hud, colapso=partida.colapso,
                                          enemigos=enemigos_cant, arena=arena, titulo="Alcaldía · mazmorra final",
                                          controles=hud.CONTROLES_JEFE, tiempo=tiempo)
            hud_partida.dibujar_hud(pantalla, bloques_hud(Escena.JEFE), ctx)
            if escena == Escena.VICTORIA:
                hud.dibujar_barra_controles(pantalla, hud.CONTROLES_FINAL)
        else:
            titulo, subtitulo = _titulo_mazmorra(mazmorra)
            grafo = getattr(mazmorra, "mazmorra", None) if mazmorra is not None else None
            aviso = None
            if mazmorra is not None and mazmorra.mensaje is not None:
                aviso = (mazmorra.mensaje[0], assets.COLOR_MENSAJE_MAZMORRA, assets.POSICION_MENSAJE_MAZMORRA)
            ctx = hud_partida.ContextoHud(
                jugador=jugador_hud, etiqueta_jugador=etiqueta_hud, colapso=partida.colapso, enemigos=enemigos_cant,
                cuartos=grafo.cuartos_limpios() if grafo is not None else None, mazmorra=grafo, titulo=titulo,
                subtitulo=subtitulo, mision=mision if dialogo is None else None, transcurrido_mision=tiempo_overlay,
                controles=hud.CONTROLES_COMBATE, aviso=aviso, tiempo=tiempo)
            hud_partida.dibujar_hud(pantalla, bloques_hud(Escena.MAZMORRA), ctx)
        if coop:
            for numero, j in enumerate(jugadores):
                if getattr(j, "expulsado", False) and j is not jugador:
                    continue  # el fantasma de otro no se ve
                hud.dibujar_panel_jugador(pantalla, j, numero)
        if escena == Escena.VICTORIA:
            dibujar_victoria(pantalla)
        if _apunta_con_mouse(escena, jugador) and jugador in en_combate:
            combate_render.dibujar_mira(pantalla, jugador, sacudida)
        ciudad_render.dibujar_fundido(pantalla, fundido)
        presentar()


# Online: si algo falla en una partida en red, se anota en
# Online/errores_online.log y se vuelve al menú (CONTINUAR la retoma) en
# vez de cerrar el juego. Una partida local se comporta igual que antes.
_jugar = proteger_partida_online(_jugar)


def _frame_de_combate(
    dt, jugadores, entradas, escenario, proyectiles_por_jugador, proyectiles_enemigos, textos,
    particulas, sacudida=(0, 0),
):
    """Un frame de combate, igual en la mazmorra y en la arena, para 1 o 2 jugadores."""
    if escenario is None:
        return  # sin lugar de combate (cambio de escena a medio frame en Online): nada que simular
    teclas = pygame.key.get_pressed()
    en_combate = jugadores_en_combate(jugadores)
    for jugador, entrada, proyectiles in zip(jugadores, entradas, proyectiles_por_jugador):
        jugador.actualizar_invulnerabilidad(dt)
        jugador.actualizar_dash(dt)
        # Se lee aunque esté caído, para que un botón mantenido no cuente
        # como "recién apretado" al revivir.
        pedido = _leer_entrada(entrada, teclas, sacudida)
        if getattr(jugador, "expulsado", False):
            # Fantasma (lo expulsaron en una reunión, modo Online): camina, no pelea.
            jugador.manejar_input(replace(pedido, dash=False), dt, escenario.rect)
            continue
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


def _dibujar_fantasma(lienzo, jugador, tiempo):
    """El expulsado se ve a sí mismo medio transparente (los demás no lo ven)."""
    from src.ui import sprites
    imagen = sprites.sprite_jugador(jugador.COLOR, rol=jugador.rol, tiempo=tiempo,
                                    caminando=jugador.velocidad_actual.length_squared() > 0,
                                    apariencia=getattr(jugador, "apariencia", None)).copy()
    imagen.set_alpha(assets.ALFA_FANTASMA)
    lienzo.blit(imagen, imagen.get_rect(midbottom=jugador.rect.midbottom))


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


def _overlay_terminado(overlay):
    """True si el diálogo (terminado) o la cinemática (terminada) ya acabó."""
    return getattr(overlay, "terminado", False) or getattr(overlay, "terminada", False)


PISTA_POR_ESCENA = {
    Escena.CIUDAD: "ciudad",
    Escena.MAZMORRA: "combate",
    Escena.DECISION: "decision",
    Escena.RESULTADO: "misterio",
    Escena.JEFE: "jefe",
    Escena.VICTORIA: "victoria",
    Escena.DERROTA: "derrota",
}


def _pista_para(escena, en_cinematica, en_crisis=False, en_redencion=False, en_final_derrota=False):
    """Pista de lo que está pasando: una crisis o una redención mandan sobre
    la escena; las demás cinemáticas usan la de misterio."""
    if en_final_derrota:
        return "derrota"
    if en_crisis:
        return "crisis"
    if en_redencion:
        return "redencion"
    return "misterio" if en_cinematica else PISTA_POR_ESCENA.get(escena, "ciudad")


def _punto_evidencia(mazmorra):
    """Dónde cae la prueba del cuarto actual: en el centro, algo arriba,
    lejos de puertas y de la terminal."""
    rect = mazmorra.cuarto.rect
    return (rect.centerx, rect.centery - 40)


def _baliza_mision(campania, indices):
    """(índice, posición en el mundo, texto) de la etapa de redención pendiente,
    o None. La etapa 2 está en el Kiosco de la Plaza y la 3, frente a la zona."""
    for indice in indices:
        mision = campania.mision_de(indice)
        if mision is None:
            continue
        if mision.etapa == ETAPA_CORREGIR:
            return indice, ciudad_mapa.posicion_aparicion(ZONA_INICIO), "E: publicar la corrección en el Kiosco Civitas"
        if mision.etapa == ETAPA_CONFIANZA:
            return indice, ciudad_mapa.posicion_aparicion(mision.zona), f"E: ayudar a {mision.ayuda['ciudadano']}"
    return None


def _baliza_cercana(campania, indices, jugador):
    baliza = _baliza_mision(campania, indices)
    if baliza is None:
        return None
    distancia = pygame.Vector2(jugador.posicion.x, jugador.posicion.y).distance_to(baliza[1])
    return baliza[0] if distancia <= assets.ALCANCE_BALIZA else None


def _dibujar_baliza_mision(pantalla, campania, indices, jugador, tiempo):
    baliza = _baliza_mision(campania, indices)
    if baliza is None:
        return
    camara_x, camara_y = ciudad_render.camara_para((jugador.posicion.x, jugador.posicion.y))
    vista = ciudad_render.vista()
    punto = (baliza[1][0] + vista.x - camara_x, baliza[1][1] + vista.y - camara_y)
    cerca = pygame.Vector2(jugador.posicion.x, jugador.posicion.y).distance_to(baliza[1]) <= assets.ALCANCE_BALIZA
    feed_render.dibujar_baliza(pantalla, punto, vista, tiempo)
    if cerca:
        ciudad_render.dibujar_aviso(pantalla, baliza[2], assets.COLOR_VERIFICADO)


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


def _dibujar_ciudad(pantalla, partida, jugador, destino, tiempo, mostrar_ruta, mostrar_mapa_mundo, indice_local=0,
                    bloques=None, mision=None, transcurrido_mision=1.0):
    """Escena CIUDAD completa: el mundo (o el mapa del mundo con M) y el HUD
    por bloques (src/ui/hud_partida.py; `bloques` de hud_visibilidad, por
    defecto los esenciales). Retorna el rect de la línea de misión (o None)."""
    if bloques is None:
        bloques = hud_visibilidad.bloques_visibles(Escena.CIUDAD, mapa_mundo=mostrar_mapa_mundo)
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
                if _j_otro is not jugador and getattr(_j_otro.invulnerabilidad, "visible", True) \
                        and not getattr(_j_otro, "expulsado", False):
                    from src.ui import sprites
                    _rect_v = ciudad_render.vista()
                    _cam = ciudad_render.camara_para((jugador.posicion.x, jugador.posicion.y))
                    _dx, _dy = _rect_v.x - _cam[0], _rect_v.y - _cam[1]
                    _img = sprites.sprite_jugador(_j_otro.COLOR, rol=_j_otro.rol, tiempo=tiempo,
                                                  caminando=getattr(_j_otro, "caminando_en_ciudad", False),
                                                  apariencia=getattr(_j_otro, "apariencia", None))
                    sprites.dibujar_centrado(pantalla, _img, (round(_j_otro.posicion.x + _dx), round(_j_otro.posicion.y + _dy - 6)))
        titulo = assets.TITULO_CIUDAD
    # La toxicidad de cada lugar se lee cerca de su puerta (y en el mapa del mundo).
    aviso = None
    zona = ciudad_mapa.entrada_cercana(posicion)
    sellada = not partida.alcaldia_desbloqueada()
    if mostrar_mapa_mundo:
        pass
    elif zona is not None and not (zona == ZONA_FINAL and sellada):
        aviso = (assets.TEXTO_AVISO_ENTRADA.format(zona=zona, nivel=partida.toxicidad(zona)),
                 assets.COLOR_AVISO_ENTRADA, assets.POSICION_AVISO_ENTRADA)
    elif sellada and ciudad_mapa.entrada_cercana(posicion, ALCANCE_AVISO_SELLADA) == ZONA_FINAL:
        aviso = (assets.TEXTO_ALCALDIA_SELLADA, assets.COLOR_AVISO_SELLADA, assets.POSICION_AVISO_ENTRADA)
    ctx = hud_partida.ContextoHud(
        jugador=jugador, colapso=partida.colapso, titulo=titulo, destino=destino,
        calles_bloqueadas=len(partida.ciudad.bloqueadas), mision=mision, transcurrido_mision=transcurrido_mision,
        titulares=partida.titulares(), tiempo=tiempo, reputacion=partida.campania.rep(indice_local).valor,
        controles=hud.CONTROLES_MAPA_MUNDO if mostrar_mapa_mundo else hud.CONTROLES_CIUDAD, aviso=aviso)
    rect_mision = hud_partida.dibujar_hud(pantalla, bloques, ctx)
    if mostrar_ruta and not mostrar_mapa_mundo:
        # G es una petición explícita: su chip se ve aunque el HUD esté limpio.
        texto = (assets.TEXTO_RUTA_DESTINO.format(destino=destino, costo=ruta[1]) if ruta
                 else assets.TEXTO_SIN_RUTA)
        dibujo.chip(pantalla, texto, assets.POSICION_AVISO_RUTA, assets.COLOR_RUTA_CIUDAD, assets.COLOR_PANEL_HUD,
                    assets.COLOR_RUTA_CIUDAD, assets.TAMANIO_FUENTE_PEQUENA, ancla="topright", alto=26, margen=10)
    return rect_mision


def _curar(jugadores):
    """Cada mazmorra (normal o final) se empieza con la vida llena (y sin dash a medias)."""
    for jugador in jugadores:
        jugador.vida = jugador.vida_maxima
        jugador.invulnerabilidad.reiniciar()
        jugador.dash.reiniciar()
        jugador.detener()


def _jugadores_nuevos(jugadores):
    """Los mismos roles desde cero para la partida nueva tras la derrota
    global. La apariencia del vestidor y el impostor (modo Online) no son
    progreso de la partida: se conservan, porque no se vuelve al lobby."""
    nuevos = [type(j)(0, 0) for j in jugadores]
    for nuevo, viejo in zip(nuevos, jugadores):
        nuevo.apariencia = getattr(viejo, "apariencia", None)
        nuevo.es_impostor = getattr(viejo, "es_impostor", False)
    return nuevos


def _menu_principal(pantalla, reloj, vista, hay_partida, preferencias, audio, presentar, mando):
    """Pantalla de inicio con la ciudad animada, el menú, EXTRAS, CRÉDITOS
    y el modal de ajustes. Teclado, control y ratón se traducen a
    acciones de src/ui/navegacion.py; el sonido sale de lo que retorna
    cada acción (un cambio real), así nunca se duplica. Retorna
    (JUGAR | CONTINUAR | SALIR, control)."""
    menu = MenuPrincipal(hay_partida, preferencias, audio=audio.ajustes)
    sticks = (_StickMenu(),
              _StickMenu(pygame.CONTROLLER_AXIS_LEFTY, navegacion.ARRIBA, navegacion.ABAJO))
    guardadas = replace(preferencias)
    audio_guardado = replace(audio.ajustes)
    pygame.mouse.set_visible(True)
    while True:
        dt = reloj.tick_busy_loop(FPS) / 1000
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return SALIR, mando
            if evento.type == pygame.KEYDOWN and evento.key == TECLA_SILENCIO:
                audio.alternar_silencio()
                continue
            accion = _accion_menu(evento, sticks)
            sonido = menu.accion(accion) if accion is not None else vista.manejar_mouse(evento, menu)
            audio.reproducir(sonido)
        resultado = menu.actualizar(dt)
        # Los ajustes se aplican al instante y se guardan en disco al
        # cambiar (si se arrastra un slider, al soltarlo).
        if audio.ajustes != audio_guardado:
            audio.aplicar()
            if not vista.arrastrando:
                audio.guardar()
                audio_guardado = replace(audio.ajustes)
        if preferencias != guardadas and not vista.arrastrando:
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


def _menu_inicio(pantalla, reloj, mando, presentar, audio=None, preferencias=None):
    """Pantalla de modo y luego la de roles (Esc en roles vuelve al modo).
    Retorna (clases de rol en orden J1, J2..., control o None, entrada_extra), VOLVER
    con Esc en la pantalla de modo, o None si se cierra la ventana."""
    while True:
        modo = _elegir_modo(pantalla, reloj, mando, presentar, audio, preferencias)
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
        clases = _elegir_roles(pantalla, reloj, modo, mando, presentar, audio, preferencias)
        if clases is None:
            return None
        if clases != VOLVER:
            return clases, mando, None


def _elegir_modo(pantalla, reloj, mando, presentar, audio=None, preferencias=None):
    """1 o 2 jugadores, con teclado o con el control. Dos jugadores exige
    un control: si no hay, se avisa y se espera a que se conecte uno.
    Retorna (modo, control), VOLVER con Esc u ○, o None si se cierra."""
    selector = SelectorModo()
    stick = _StickMenu()
    aviso = 0.0  # segundos que le quedan al aviso "Conecta un control"
    if audio is not None:
        audio.musica("lobby")
    while True:
        dt = reloj.tick(FPS) / 1000
        aviso = max(0.0, aviso - dt)
        confirmar = False
        modo_antes = selector.seleccionado
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_SALIR:
                    return VOLVER
                if _tecla_de_audio(evento.key, audio, preferencias):
                    continue
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
        if audio is not None and selector.seleccionado != modo_antes:
            audio.reproducir(navegacion.SONIDO_NAVEGAR)
        if confirmar:
            if selector.seleccionado == DOS_JUGADORES and mando is None:
                aviso = assets.DURACION_AVISO_MODO
                if audio is not None:
                    audio.reproducir("error_decision")
            else:
                if audio is not None:
                    audio.reproducir(navegacion.SONIDO_CONFIRMAR)
                return selector.seleccionado, mando

        dibujar_modo(pantalla, selector, mando.name if mando is not None else None, aviso > 0)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_MODO)
        presentar()


def _elegir_roles(pantalla, reloj, modo, mando, presentar, audio=None, preferencias=None):
    """Lobby: cada jugador mueve su cursor sobre las tarjetas y confirma; la
    partida empieza cuando todos confirmaron (tras un fundido corto). J1:
    flechas o A/D, Enter o Espacio, 1-4 directo, Retroceso para cambiar, o
    el ratón (señalar y clic). J2: cruceta o stick, ✕ confirma, ○ para
    cambiar. N silencia y - / + cambian el volumen general. Retorna la
    lista de clases elegidas, VOLVER con Esc, o None si se cierra."""
    cantidad = 1 if modo == UN_JUGADOR else 2
    seleccion = SeleccionRoles(cantidad, len(CLASES_ROL))
    vista = VistaSeleccion(len(CLASES_ROL), escena_lobby_render.crear(), _tablero_mazmorras())
    j1 = seleccion.cursores[0]
    j2 = seleccion.cursores[1] if cantidad > 1 else None
    stick = _StickMenu()
    pygame.mouse.set_visible(True)

    def sonar(nombre):
        if audio is not None:
            audio.reproducir(nombre)

    if audio is not None:
        audio.musica("lobby")
    while True:
        dt = reloj.tick(FPS) / 1000
        antes = [(cursor.indice, cursor.confirmado) for cursor in seleccion.cursores]
        for evento in pygame.event.get():
            mando = _actualizar_mando(evento, mando)
            if evento.type == pygame.QUIT:
                return None
            if vista.salida is not None:
                continue  # ya eligieron todos: solo queda el fundido
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_SALIR:
                    sonar(navegacion.SONIDO_VOLVER)
                    return VOLVER
                if _tecla_de_audio(evento.key, audio, preferencias):
                    continue
                if evento.key in TECLAS_MENU_J1:
                    j1.mover(TECLAS_MENU_J1[evento.key])
                elif evento.key in TECLAS_ROL:
                    j1.elegir(TECLAS_ROL[evento.key])
                elif evento.key in TECLAS_CONFIRMAR_MENU:
                    j1.confirmar()
                elif evento.key == TECLA_CANCELAR:
                    j1.cancelar()
            elif evento.type == pygame.MOUSEMOTION and not j1.confirmado:
                indice = vista.tarjeta_en(evento.pos, len(CLASES_ROL))
                if indice is not None:
                    j1.indice = indice
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                indice = vista.tarjeta_en(evento.pos, len(CLASES_ROL))
                if indice is not None:
                    j1.elegir(indice)
            elif j2 is not None and evento.type == pygame.CONTROLLERBUTTONDOWN:
                if evento.button in BOTONES_MENU_J2:
                    j2.mover(BOTONES_MENU_J2[evento.button])
                elif evento.button == BOTON_CONFIRMAR:
                    j2.confirmar()
                elif evento.button == BOTON_CANCELAR:
                    j2.cancelar()
            elif j2 is not None and (direccion := stick.paso(evento)) is not None:
                j2.mover(direccion)
        # Un sonido por cambio real: confirmar, arrepentirse o moverse.
        for (indice_antes, confirmado_antes), cursor in zip(antes, seleccion.cursores):
            if cursor.confirmado and not confirmado_antes:
                sonar(navegacion.SONIDO_CONFIRMAR)
            elif confirmado_antes and not cursor.confirmado:
                sonar(navegacion.SONIDO_VOLVER)
            elif cursor.indice != indice_antes:
                sonar(navegacion.SONIDO_NAVEGAR)
        if seleccion.lista:
            vista.empezar_salida()

        vista.actualizar(dt, seleccion)
        volumen = audio.ajustes.volumen_general if audio is not None else 100
        silenciado = audio.silenciado if audio is not None else False
        reducir = preferencias.reducir_movimiento if preferencias is not None else False
        vista.dibujar(pantalla, CLASES_ROL, seleccion, volumen, silenciado, reducir)
        hud.dibujar_barra_controles(pantalla, hud.CONTROLES_SELECCION_DOS if j2 else hud.CONTROLES_SELECCION)
        presentar()
        if vista.salida_terminada:
            return [CLASES_ROL[indice] for indice in seleccion.indices()]


def _tablero_mazmorras():
    """Filas del tablero del lobby: cada mazmorra registrada con la
    toxicidad inicial de su zona. El lobby abre una partida nueva, así que
    todas empiezan pendientes."""
    partida = Partida()
    return registro_mazmorras.filas_tablero(partida.toxicidad, partida.campania.zonas_purificadas())


def _tecla_de_audio(tecla, audio, preferencias):
    """N silencia; - y + suben o bajan el volumen general. True si la
    tecla era de audio (y ya se atendió)."""
    if audio is None:
        return False
    if tecla == TECLA_SILENCIO:
        audio.alternar_silencio()
        return True
    if tecla in TECLAS_VOLUMEN:
        paso = TECLAS_VOLUMEN[tecla] * PASO_VOLUMEN_LOBBY
        audio.cambiar("volumen_general", audio.ajustes.volumen_general + paso)  # se aplica y se guarda
        audio.reproducir(navegacion.SONIDO_NAVEGAR)
        return True
    return False


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
    if mazmorra is None or getattr(mazmorra, "mazmorra", None) is None:
        return "Mazmorra infectada", ""
    m = mazmorra.mazmorra
    cuartos = sorted(m.grafo.nodos())
    numero = (cuartos.index(m.actual) + 1) if m.actual in cuartos else 1
    limpios, total = m.cuartos_limpios()
    subtitulo = f"Cuarto {numero} de {len(cuartos)}  ·  Limpios {limpios}/{total}"
    if m.actual == m.cuarto_final:
        subtitulo += "  ·  Cuarto final"
    return f"{m.nombre_zona} infectado", subtitulo


def _dibujar_mensaje(pantalla, cadena, color, centro):
    dibujo.chip(pantalla, cadena, centro, color, assets.COLOR_FONDO_PANEL, color,
                assets.TAMANIO_FUENTE_MEDIA, ancla="center", alto=36, margen=16)


def _texto_espera_lectura(indices):
    """'Esperando a que J2 termine de leer' (o 'J2 y J3 terminen')."""
    nombres = [f"J{indice + 1}" for indice in indices]
    if len(nombres) == 1:
        return assets.TEXTO_ESPERA_LECTURA_UNO.format(quien=nombres[0])
    return assets.TEXTO_ESPERA_LECTURA_VARIOS.format(quienes=", ".join(nombres[:-1]) + " y " + nombres[-1])


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
