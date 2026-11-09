"""Pantalla de inicio: menú principal, EXTRAS, CRÉDITOS y modal de ajustes (lógica pura).

Flujo (lo corre Main.py; el dibujo vive en src/ui/menu_principal_render.py):

    JUGAR      -> pantalla de modo (1 o 2 jugadores) -> roles -> partida nueva
    CONTINUAR  -> vuelve a la partida en curso de esta sesión (deshabilitado
                  si no hay; el juego no guarda partidas en disco)
    EXTRAS     -> vista secundaria (contenido pendiente)   --Volver--> menú
    CRÉDITOS   -> vista secundaria con los créditos reales --Volver--> menú
    AJUSTES    -> modal de ajustes (también el engranaje de la esquina)
    SALIR      -> cierra el juego

El foco recorre las opciones habilitadas de arriba abajo y luego el
engranaje (y da la vuelta). Al confirmar, la opción queda "pulsada"
DURACION_PULSADO segundos para que se vea el estado antes de actuar;
mientras tanto no se acepta otra acción. Mientras el modal o una vista
secundaria están abiertos, el menú de atrás no recibe nada.
"""

from src.core import assets
from src.ui.ajustes import ModalAjustes
from src.ui.navegacion import (
    ABAJO,
    ARRIBA,
    CONFIRMAR,
    SONIDO_CONFIRMAR,
    SONIDO_NAVEGAR,
    SONIDO_VOLVER,
    VOLVER,
)

JUGAR = "JUGAR"
CONTINUAR = "CONTINUAR"
EXTRAS = "EXTRAS"
CREDITOS = "CRÉDITOS"
AJUSTES = "AJUSTES"
SALIR = "SALIR"
OPCIONES = (JUGAR, CONTINUAR, EXTRAS, CREDITOS, AJUSTES, SALIR)
ENGRANAJE = "engranaje"  # botón de ajustes de la esquina superior derecha

# Opciones que terminan el menú: Main.py actúa según cuál fue.
ACCIONES_DE_SALIDA = (JUGAR, CONTINUAR, SALIR)

VISTA_MENU = "menu"
VISTA_EXTRAS = "extras"
VISTA_CREDITOS = "creditos"

TEXTO_SIN_PARTIDA = "SIN PARTIDA EN CURSO"
TEXTO_EXTRAS = (
    "Vuelve a ver la introducción cinematográfica de Código Nova.",
    "Enter o ✕: ver la introducción   ·   Esc u ○: volver",
)
VER_INTRO = "VER_INTRO"  # acción que Main.py atiende desde EXTRAS
# Solo datos presentes en el repositorio; los integrantes se agregan aquí.
LINEAS_CREDITOS = (
    ("Proyecto", "Estructura de Datos II · Ingeniería de Sistemas"),
    ("", "Universidad del Norte"),
    ("Evento", "VI Feria Gamer · 26 de noviembre de 2026"),
    ("Tipografía", "JetBrains Mono · SIL Open Font License"),
    # La música de Bitcade es CC BY 4.0: este crédito es obligatorio.
    ("Música", "Bitcade Audio (CC BY 4.0) · schniersky.itch.io/bitcade"),
    ("Efectos y arte", "Bitcade SFX (CC0) · packs Modern Urban y School"),
    ("Equipo", "Pendiente: nombres de los integrantes"),
)


class MenuPrincipal:
    def __init__(self, hay_partida, preferencias, duracion_pulsado=assets.DURACION_PULSADO_MENU, audio=None):
        """`audio`: los AjustesAudio que edita la pestaña AUDIO (los del gestor)."""
        self.hay_partida = hay_partida
        self.preferencias = preferencias
        self.audio = audio
        self.duracion_pulsado = duracion_pulsado
        self.foco = CONTINUAR if hay_partida else JUGAR
        self.vista = VISTA_MENU
        self.ajustes = None  # ModalAjustes mientras está abierto
        self.pulsado = None  # opción confirmada que espera su animación
        self.tiempo_pulsado = 0.0
        self._foco_antes_de_ajustes = None

    def habilitada(self, elemento):
        return elemento != CONTINUAR or self.hay_partida

    def anillo(self):
        """Elementos enfocables del menú, en orden de navegación."""
        return [opcion for opcion in OPCIONES if self.habilitada(opcion)] + [ENGRANAJE]

    @property
    def bloqueado(self):
        """True si el menú de atrás no debe recibir input."""
        return self.ajustes is not None or self.vista != VISTA_MENU or self.pulsado is not None

    def accion(self, accion):
        """Aplica una acción de src/ui/navegacion.py. Retorna el sonido a
        reproducir o None."""
        if self.ajustes is not None:
            sonido = self.ajustes.accion(accion)
            if self.ajustes.cerrado:
                self.cerrar_ajustes()
            return sonido
        if self.vista != VISTA_MENU:
            # Vistas secundarias: VOLVER cierra; en EXTRAS, CONFIRMAR pide
            # ver la introducción (actualizar() devuelve VER_INTRO).
            if accion == CONFIRMAR and self.vista == VISTA_EXTRAS:
                self.vista = VISTA_MENU
                self.pedido_intro = True
                return SONIDO_CONFIRMAR
            if accion in (CONFIRMAR, VOLVER):
                self.volver_al_menu()
                return SONIDO_VOLVER
            return None
        if self.pulsado is not None:
            return None
        if accion in (ARRIBA, ABAJO):
            anillo = self.anillo()
            paso = -1 if accion == ARRIBA else 1
            return SONIDO_NAVEGAR if self.enfocar(anillo[(anillo.index(self.foco) + paso) % len(anillo)]) else None
        if accion == CONFIRMAR:
            return self.confirmar()
        return None

    def enfocar(self, elemento):
        """Foco por teclado/control o por hover del ratón. Las opciones
        deshabilitadas no se pueden enfocar. True si cambió."""
        if self.bloqueado or elemento == self.foco or elemento not in self.anillo():
            return False
        self.foco = elemento
        return True

    def confirmar(self, elemento=None):
        """Confirma el foco (o `elemento`, para el clic). La acción se
        ejecuta en actualizar() al terminar la animación de pulsado."""
        elemento = self.foco if elemento is None else elemento
        if self.bloqueado or elemento not in self.anillo():
            return None
        self.foco = elemento
        self.pulsado = elemento
        self.tiempo_pulsado = self.duracion_pulsado
        return SONIDO_CONFIRMAR

    def actualizar(self, dt):
        """Avanza la animación de pulsado. Retorna JUGAR, CONTINUAR, SALIR
        (o VER_INTRO desde EXTRAS) cuando el menú debe terminar; si no, None."""
        if getattr(self, "pedido_intro", False):
            self.pedido_intro = False
            return VER_INTRO
        if self.pulsado is None:
            return None
        self.tiempo_pulsado -= dt
        if self.tiempo_pulsado > 0:
            return None
        elemento, self.pulsado = self.pulsado, None
        if elemento in ACCIONES_DE_SALIDA:
            return elemento
        if elemento == EXTRAS:
            self.vista = VISTA_EXTRAS
        elif elemento == CREDITOS:
            self.vista = VISTA_CREDITOS
        else:  # AJUSTES o ENGRANAJE
            self.abrir_ajustes()
        return None

    def abrir_ajustes(self):
        self._foco_antes_de_ajustes = self.foco
        self.ajustes = ModalAjustes(self.preferencias, self.audio)

    def cerrar_ajustes(self):
        """Cierra el modal y devuelve el foco al control que lo abrió."""
        self.ajustes = None
        self.foco = self._foco_antes_de_ajustes or self.foco

    def volver_al_menu(self):
        """Desde EXTRAS o CRÉDITOS; el foco queda en la opción que se eligió."""
        self.vista = VISTA_MENU
