"""Menú de pausa dentro de la partida (lógica pura, sin Pygame).

Esc o P lo abren en la ciudad, la mazmorra, la decisión y el jefe. Es un
estado, no un temporizador: mientras `congelada` sea True el bucle de
Main.py no llama a ningún actualizar (enemigos, proyectiles, gracia de
entrada, reloj de la terminal, colapso, propagación de toxicidad,
cintillo...): nadie recibe un dt, así que nada avanza. `avanzar` es esa
misma regla en una función, para probarla sin ventana.

Congela solo en partida individual. Con 2+ jugadores (locales u online)
el menú se abre pero el mundo sigue, salvo que balance.PUEDE_PAUSAR_MULTIJUGADOR
sea True.

Opciones según la escena:
    Continuar · Ajustes · Reiniciar mazmorra (mazmorra, decisión, jefe) ·
    Volver a la ciudad (mazmorra y decisión; nunca en el jefe final) ·
    Salir al menú principal
Reiniciar, volver y salir piden confirmación (Sí / No). Ajustes abre el
modal de src/ui/ajustes.py con la pestaña PARTIDA; Main.py lo crea con los
ajustes reales y aquí solo se le pasan las acciones.

Las acciones son las de src/ui/navegacion.py; cada una devuelve el
sonido a reproducir (o None). La elegida se lee una sola vez con
`tomar_accion()`.
"""

from src.core.balance import PUEDE_PAUSAR_MULTIJUGADOR
from src.core.escenas import Escena
from src.ui.navegacion import (
    ABAJO,
    ARRIBA,
    CONFIRMAR,
    DERECHA,
    IZQUIERDA,
    SONIDO_CONFIRMAR,
    SONIDO_NAVEGAR,
    SONIDO_VOLVER,
    VOLVER,
)

CONTINUAR = "continuar"
AJUSTES = "ajustes"
REINICIAR = "reiniciar"
VOLVER_CIUDAD = "volver_ciudad"
SALIR_MENU = "salir_menu"

ETIQUETAS = {
    CONTINUAR: "CONTINUAR",
    AJUSTES: "AJUSTES",
    REINICIAR: "REINICIAR MAZMORRA",
    VOLVER_CIUDAD: "VOLVER A LA CIUDAD",
    SALIR_MENU: "SALIR AL MENÚ PRINCIPAL",
}
PREGUNTAS = {
    REINICIAR: "¿Reiniciar la mazmorra? Se pierde el avance de esta visita.",
    VOLVER_CIUDAD: "¿Volver a la ciudad? La mazmorra quedará sin terminar.",
    SALIR_MENU: "¿Salir al menú principal? La partida queda para CONTINUAR.",
}
SI, NO = "si", "no"
ESCENAS_PAUSABLES = (Escena.CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE)


def opciones_para(escena):
    """Opciones del menú en `escena`, en orden."""
    opciones = [CONTINUAR, AJUSTES]
    if escena in (Escena.MAZMORRA, Escena.DECISION, Escena.JEFE):
        opciones.append(REINICIAR)
    if escena in (Escena.MAZMORRA, Escena.DECISION):
        opciones.append(VOLVER_CIUDAD)  # en el jefe final no: se gana o se pierde ahí
    opciones.append(SALIR_MENU)
    return opciones


def congela(cantidad_jugadores, en_red, multijugador_permitido=PUEDE_PAUSAR_MULTIJUGADOR):
    """True si la pausa debe detener el mundo."""
    individual = cantidad_jugadores == 1 and not en_red
    return individual or multijugador_permitido


def avanzar(pausa, dt, *actualizables):
    """Un tick del mundo: llama a cada `actualizable(dt)` salvo que la pausa
    lo congele. Retorna True si avanzó."""
    if pausa.congelada:
        return False
    for actualizar in actualizables:
        actualizar(dt)
    return True


class Pausa:
    def __init__(self):
        self.abierta = False
        self.congelada = False
        self.escena = None
        self.opciones = []
        self.foco = 0
        self.confirmando = None  # opción que espera Sí / No
        self.foco_confirmacion = NO  # por seguridad, el foco empieza en No
        self.ajustes = None  # ModalAjustes abierto (lo pone Main.py)
        self._accion = None

    # --- Abrir y cerrar ---------------------------------------------------

    def abrir(self, escena, cantidad_jugadores=1, en_red=False, multijugador_permitido=PUEDE_PAUSAR_MULTIJUGADOR):
        """Abre el menú si `escena` se puede pausar. True si se abrió."""
        if self.abierta or escena not in ESCENAS_PAUSABLES:
            return False
        self.abierta = True
        self.congelada = congela(cantidad_jugadores, en_red, multijugador_permitido)
        self.escena = escena
        self.opciones = opciones_para(escena)
        self.foco = 0
        self.confirmando = None
        self.ajustes = None
        self._accion = None
        return True

    def cerrar(self):
        self.abierta = False
        self.congelada = False
        self.confirmando = None
        self.ajustes = None

    @property
    def opcion_enfocada(self):
        return self.opciones[self.foco] if self.opciones else None

    def tomar_accion(self):
        """La acción elegida (CONTINUAR, REINICIAR, VOLVER_CIUDAD o
        SALIR_MENU), una sola vez; None si todavía no hay."""
        accion, self._accion = self._accion, None
        return accion

    # --- Ajustes ------------------------------------------------------------

    def abrir_ajustes(self, modal):
        self.ajustes = modal

    # --- Navegación ---------------------------------------------------------

    def accion(self, accion):
        """Aplica una acción de navegación. Retorna el sonido o None."""
        if not self.abierta:
            return None
        if self.ajustes is not None:
            sonido = self.ajustes.accion(accion)
            if self.ajustes.cerrado:
                self.ajustes = None
            return sonido
        if self.confirmando is not None:
            return self._accion_confirmacion(accion)
        if accion in (ARRIBA, ABAJO):
            self.foco = (self.foco + (-1 if accion == ARRIBA else 1)) % len(self.opciones)
            return SONIDO_NAVEGAR
        if accion == CONFIRMAR:
            return self.elegir(self.opcion_enfocada)
        if accion == VOLVER:
            return self.elegir(CONTINUAR)
        return None

    def enfocar(self, opcion):
        """Ratón: foco sobre `opcion` (o sobre SI / NO al confirmar). True si cambió."""
        if self.confirmando is not None:
            if opcion in (SI, NO) and opcion != self.foco_confirmacion:
                self.foco_confirmacion = opcion
                return True
            return False
        if opcion in self.opciones and self.opciones.index(opcion) != self.foco:
            self.foco = self.opciones.index(opcion)
            return True
        return False

    def elegir(self, opcion):
        """Activa `opcion` (Enter o clic). Retorna el sonido."""
        if self.confirmando is not None:
            if opcion not in (SI, NO):
                return None
            self.foco_confirmacion = opcion
            return self._accion_confirmacion(CONFIRMAR)
        if opcion == CONTINUAR:
            self._accion = CONTINUAR
            return SONIDO_VOLVER
        if opcion == AJUSTES:
            self._accion = AJUSTES  # Main.py arma el modal y llama a abrir_ajustes
            return SONIDO_CONFIRMAR
        if opcion in PREGUNTAS and opcion in self.opciones:
            self.confirmando = opcion
            self.foco_confirmacion = NO
            return SONIDO_CONFIRMAR
        return None

    def _accion_confirmacion(self, accion):
        if accion in (IZQUIERDA, DERECHA, ARRIBA, ABAJO):
            self.foco_confirmacion = SI if self.foco_confirmacion == NO else NO
            return SONIDO_NAVEGAR
        if accion == VOLVER or (accion == CONFIRMAR and self.foco_confirmacion == NO):
            self.confirmando = None
            return SONIDO_VOLVER
        if accion == CONFIRMAR:
            self._accion, self.confirmando = self.confirmando, None
            return SONIDO_CONFIRMAR
        return None
