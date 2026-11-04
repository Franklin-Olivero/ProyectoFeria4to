"""Modal de ajustes: pestañas, foco y cambios de valor (lógica pura, sin Pygame).

El modal edita directamente un objeto Preferencias (src/core/preferencias.py).
Cada pestaña es una lista de controles; el foco recorre, de arriba abajo:

    barra de pestañas -> controles de la pestaña -> botón CERRAR

    AUDIO:          volumen_musica, volumen_efectos              (sliders)
    ACCESIBILIDAD:  subtitulos (interruptor), filtro_daltonismo (selector),
                    reducir_movimiento (interruptor), alto_contraste (interruptor)
    CONTROLES:      esquema_controles (selector) y, solo en la vista MANDO,
                    mostrar_cono (interruptor) y opacidad_cono (slider)

Cada control se llama igual que el campo de Preferencias que modifica.
El dibujo y el ratón viven en src/ui/ajustes_render.py.
"""

from src.core.preferencias import ESQUEMA_MANDO, OPCIONES_TEXTO, acotar_porcentaje, valor_valido
from src.ui.navegacion import (
    ABAJO,
    ARRIBA,
    CONFIRMAR,
    DERECHA,
    IZQUIERDA,
    PESTANA_ANTERIOR,
    PESTANA_SIGUIENTE,
    SONIDO_CONFIRMAR,
    SONIDO_NAVEGAR,
    SONIDO_VOLVER,
    VOLVER,
)

PESTANA_AUDIO = "AUDIO"
PESTANA_ACCESIBILIDAD = "ACCESIBILIDAD"
PESTANA_CONTROLES = "CONTROLES"
PESTANAS = (PESTANA_AUDIO, PESTANA_ACCESIBILIDAD, PESTANA_CONTROLES)

BARRA_PESTANAS = "pestanas"  # elemento enfocable: la fila de pestañas
CERRAR = "cerrar"

SLIDERS = ("volumen_musica", "volumen_efectos", "opacidad_cono")
INTERRUPTORES = ("subtitulos", "reducir_movimiento", "alto_contraste", "mostrar_cono")
SELECTORES = tuple(OPCIONES_TEXTO)  # filtro_daltonismo, esquema_controles
PASO_SLIDER = 5  # puntos de porcentaje por pulsación de ← →


class ModalAjustes:
    def __init__(self, preferencias):
        self.preferencias = preferencias
        self.pestana = PESTANA_AUDIO
        self.foco = BARRA_PESTANAS
        self.cerrado = False  # lo pone CERRAR o VOLVER; el menú lo quita

    def controles(self):
        """Controles de la pestaña actual, en orden de foco."""
        if self.pestana == PESTANA_AUDIO:
            return ["volumen_musica", "volumen_efectos"]
        if self.pestana == PESTANA_ACCESIBILIDAD:
            return ["subtitulos", "filtro_daltonismo", "reducir_movimiento", "alto_contraste"]
        if self.preferencias.esquema_controles == ESQUEMA_MANDO:
            return ["esquema_controles", "mostrar_cono", "opacidad_cono"]
        return ["esquema_controles"]

    def elementos(self):
        return [BARRA_PESTANAS] + self.controles() + [CERRAR]

    def accion(self, accion):
        """Aplica una acción de src/ui/navegacion.py. Retorna el nombre
        del sonido a reproducir, o None si nada cambió."""
        if accion in (ARRIBA, ABAJO):
            return self._mover(-1 if accion == ARRIBA else 1)
        if accion in (PESTANA_ANTERIOR, PESTANA_SIGUIENTE):
            return self._cambiar_pestana(-1 if accion == PESTANA_ANTERIOR else 1)
        if accion in (IZQUIERDA, DERECHA):
            paso = -1 if accion == IZQUIERDA else 1
            if self.foco == BARRA_PESTANAS:
                return self._cambiar_pestana(paso)
            return SONIDO_NAVEGAR if self._ajustar(self.foco, paso) else None
        if accion == CONFIRMAR:
            return self._activar()
        if accion == VOLVER:
            self.cerrado = True
            return SONIDO_VOLVER
        return None

    # --- Ratón (src/ui/ajustes_render.py) -------------------------------

    def enfocar(self, elemento):
        """Mueve el foco a `elemento` si existe en la pestaña. True si cambió."""
        if elemento == self.foco or elemento not in self.elementos():
            return False
        self.foco = elemento
        return True

    def elegir_pestana(self, pestana):
        if pestana == self.pestana or pestana not in PESTANAS:
            return False
        self.pestana = pestana
        self.foco = BARRA_PESTANAS
        return True

    def fijar(self, campo, valor):
        """Pone `campo` en `valor` (validado). True si cambió."""
        valor = valor_valido(campo, valor)
        if valor is None or getattr(self.preferencias, campo) == valor:
            return False
        setattr(self.preferencias, campo, valor)
        return True

    # --- Internos --------------------------------------------------------

    def _mover(self, paso):
        elementos = self.elementos()
        indice = (elementos.index(self.foco) + paso) % len(elementos)
        self.foco = elementos[indice]
        return SONIDO_NAVEGAR

    def _cambiar_pestana(self, paso):
        indice = (PESTANAS.index(self.pestana) + paso) % len(PESTANAS)
        self.elegir_pestana(PESTANAS[indice])
        return SONIDO_NAVEGAR

    def _ajustar(self, campo, paso):
        """← → sobre un control: slider ±PASO_SLIDER, selector a la opción
        vecina (da la vuelta), interruptor se invierte."""
        actual = getattr(self.preferencias, campo, None)
        if campo in SLIDERS:
            return self.fijar(campo, acotar_porcentaje(actual + paso * PASO_SLIDER))
        if campo in SELECTORES:
            opciones = OPCIONES_TEXTO[campo]
            return self.fijar(campo, opciones[(opciones.index(actual) + paso) % len(opciones)])
        if campo in INTERRUPTORES:
            return self.fijar(campo, not actual)
        return False

    def _activar(self):
        if self.foco == CERRAR:
            self.cerrado = True
            return SONIDO_VOLVER
        if self.foco == BARRA_PESTANAS:
            # Enter en las pestañas entra al primer control.
            self.foco = self.controles()[0]
            return SONIDO_NAVEGAR
        if self.foco in SLIDERS:
            return None  # un slider se cambia con ← →, no con Enter
        return SONIDO_CONFIRMAR if self._ajustar(self.foco, 1) else None
