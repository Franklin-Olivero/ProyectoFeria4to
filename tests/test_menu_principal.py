"""Menú principal y modal de ajustes: navegación, foco y valores (sin pygame)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.preferencias import Preferencias  # noqa: E402
from src.ui.ajustes import BARRA_PESTANAS, CERRAR, PASO_SLIDER, ModalAjustes  # noqa: E402
from src.ui.menu_principal import (  # noqa: E402
    AJUSTES,
    CONTINUAR,
    CREDITOS,
    ENGRANAJE,
    EXTRAS,
    JUGAR,
    SALIR,
    VISTA_CREDITOS,
    VISTA_EXTRAS,
    VISTA_MENU,
    MenuPrincipal,
)
from src.ui.navegacion import (  # noqa: E402
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


def _menu(hay_partida=False):
    return MenuPrincipal(hay_partida, Preferencias(), duracion_pulsado=0.1)


def _terminar_pulsado(menu):
    return menu.actualizar(1.0)


def test_modulos_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = ("import sys, src.ui.menu_principal, src.ui.ajustes, src.ui.navegacion; "
              "print('pygame' in sys.modules)")
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


# --- Menú ---------------------------------------------------------------------


def test_sin_partida_continuar_esta_deshabilitado_y_se_salta():
    menu = _menu()
    assert menu.foco == JUGAR
    assert not menu.habilitada(CONTINUAR)
    assert menu.accion(ABAJO) == SONIDO_NAVEGAR
    assert menu.foco == EXTRAS  # se saltó CONTINUAR
    assert not menu.enfocar(CONTINUAR)  # ni el ratón lo enfoca
    assert menu.confirmar(CONTINUAR) is None


def test_con_partida_el_foco_empieza_en_continuar():
    menu = _menu(hay_partida=True)
    assert menu.foco == CONTINUAR
    menu.confirmar()
    assert _terminar_pulsado(menu) == CONTINUAR


def test_el_foco_da_la_vuelta_pasando_por_el_engranaje():
    menu = _menu()
    menu.accion(ARRIBA)
    assert menu.foco == ENGRANAJE
    menu.accion(ARRIBA)
    assert menu.foco == SALIR
    menu.accion(ABAJO)
    menu.accion(ABAJO)
    assert menu.foco == JUGAR


def test_mismo_foco_no_suena_dos_veces():
    menu = _menu()
    assert menu.enfocar(JUGAR) is False  # ya estaba ahí: no hay cambio ni sonido


def test_confirmar_espera_la_animacion_y_bloquea_otras_acciones():
    menu = _menu()
    assert menu.accion(CONFIRMAR) == SONIDO_CONFIRMAR
    assert menu.pulsado == JUGAR
    assert menu.accion(ABAJO) is None  # bloqueado mientras se ve pulsado
    assert menu.actualizar(0.05) is None
    assert menu.actualizar(0.06) == JUGAR
    assert menu.pulsado is None


def test_salir_termina_el_menu():
    menu = _menu()
    menu.enfocar(SALIR)
    menu.confirmar()
    assert _terminar_pulsado(menu) == SALIR


def test_extras_y_creditos_abren_su_vista_y_vuelven():
    for opcion, vista in ((EXTRAS, VISTA_EXTRAS), (CREDITOS, VISTA_CREDITOS)):
        menu = _menu()
        menu.confirmar(opcion)
        assert _terminar_pulsado(menu) is None
        assert menu.vista == vista
        assert menu.accion(ABAJO) is None  # el menú de atrás no recibe nada
        assert menu.accion(VOLVER) == SONIDO_VOLVER
        assert menu.vista == VISTA_MENU
        assert menu.foco == opcion


def test_ajustes_y_engranaje_abren_el_modal_y_devuelven_el_foco():
    for opener in (AJUSTES, ENGRANAJE):
        menu = _menu()
        menu.confirmar(opener)
        _terminar_pulsado(menu)
        assert menu.ajustes is not None
        assert not menu.enfocar(SALIR)  # nada detrás del modal
        assert menu.accion(VOLVER) == SONIDO_VOLVER
        assert menu.ajustes is None
        assert menu.foco == opener


def test_el_modal_edita_las_mismas_preferencias_del_menu():
    menu = _menu()
    menu.abrir_ajustes()
    menu.accion(ABAJO)  # barra de pestañas -> música
    menu.accion(DERECHA)
    assert menu.preferencias.volumen_musica == 70 + PASO_SLIDER


# --- Modal de ajustes ------------------------------------------------------------


def test_foco_recorre_pestanas_controles_y_cerrar():
    modal = ModalAjustes(Preferencias())
    assert modal.elementos() == [BARRA_PESTANAS, "volumen_musica", "volumen_efectos", CERRAR]
    modal.accion(ARRIBA)
    assert modal.foco == CERRAR
    modal.accion(ABAJO)
    assert modal.foco == BARRA_PESTANAS


def test_pestanas_con_flechas_y_atajos():
    modal = ModalAjustes(Preferencias())
    modal.accion(DERECHA)  # en la barra: cambia de pestaña
    assert modal.pestana == "ACCESIBILIDAD"
    modal.accion(ABAJO)
    modal.accion(PESTANA_SIGUIENTE)  # Q/E o L1/R1 desde cualquier control
    assert modal.pestana == "CONTROLES"
    assert modal.foco == BARRA_PESTANAS
    modal.accion(PESTANA_SIGUIENTE)
    assert modal.pestana == "AUDIO"
    modal.accion(PESTANA_ANTERIOR)
    assert modal.pestana == "CONTROLES"


def test_cambiar_de_pestana_no_pierde_valores():
    p = Preferencias()
    modal = ModalAjustes(p)
    modal.accion(ABAJO)
    modal.accion(IZQUIERDA)
    modal.accion(PESTANA_SIGUIENTE)
    modal.accion(PESTANA_ANTERIOR)
    assert p.volumen_musica == 70 - PASO_SLIDER


def test_sliders_se_acotan_y_cero_silencia():
    p = Preferencias(volumen_efectos=5)
    modal = ModalAjustes(p)
    modal.enfocar("volumen_efectos")
    assert modal.accion(IZQUIERDA) == SONIDO_NAVEGAR
    assert p.volumen_efectos == 0
    assert modal.accion(IZQUIERDA) is None  # ya en 0: sin cambio, sin sonido
    assert modal.fijar("volumen_efectos", 140)
    assert p.volumen_efectos == 100
    assert modal.accion(CONFIRMAR) is None  # Enter no mueve un slider


def test_interruptores_y_selectores():
    p = Preferencias()
    modal = ModalAjustes(p)
    modal.elegir_pestana("ACCESIBILIDAD")
    modal.enfocar("subtitulos")
    assert modal.accion(CONFIRMAR) == SONIDO_CONFIRMAR
    assert p.subtitulos is True
    modal.enfocar("filtro_daltonismo")
    modal.accion(IZQUIERDA)  # da la vuelta: Ninguno -> Tritanopia
    assert p.filtro_daltonismo == "Tritanopia"
    modal.accion(DERECHA)
    assert p.filtro_daltonismo == "Ninguno"  # "Ninguno" restaura el color
    modal.enfocar("reducir_movimiento")
    modal.accion(DERECHA)
    assert p.reducir_movimiento is True


def test_ajustes_del_cono_solo_en_la_vista_mando():
    p = Preferencias()
    modal = ModalAjustes(p)
    modal.elegir_pestana("CONTROLES")
    assert modal.controles() == ["esquema_controles"]
    modal.enfocar("esquema_controles")
    modal.accion(DERECHA)
    assert p.esquema_controles == "mando"
    assert modal.controles() == ["esquema_controles", "mostrar_cono", "opacidad_cono"]
    assert modal.foco == "esquema_controles"  # el foco no salta al cambiar la lista
    modal.enfocar("opacidad_cono")
    modal.fijar("opacidad_cono", 0)
    assert p.opacidad_cono == 0 and p.mostrar_cono is True  # 0% oculta, no desactiva
    assert not modal.fijar("filtro_daltonismo", "Inventado")


def test_cerrar_y_volver_marcan_el_modal_como_cerrado():
    modal = ModalAjustes(Preferencias())
    modal.enfocar(CERRAR)
    assert modal.accion(CONFIRMAR) == SONIDO_VOLVER
    assert modal.cerrado
    otro = ModalAjustes(Preferencias())
    otro.accion(VOLVER)
    assert otro.cerrado
