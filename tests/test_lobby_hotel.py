"""Lobby del hotel: tablero de mazmorras y escena (lógica pura, sin pygame)."""

import os
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.dungeon import registro_mazmorras as registro  # noqa: E402
from src.ui import escena_lobby  # noqa: E402

TOX = {"Colegio": 84.6, "Hospital": 50.0, "Empresa de Medios": 15.2, "Alcaldía": 100.0}


# ----------------------------------------------------------------------
# Tablero de mazmorras
# ----------------------------------------------------------------------

def test_tablero_lista_las_cuatro_mazmorras_pendientes_al_empezar():
    filas = registro.filas_tablero(TOX.get)
    assert [f.nombre for f in filas] == ["Colegio", "Hospital", "Empresa de Medios", "Alcaldía"]
    assert [f.toxicidad for f in filas] == [85, 50, 15, 100]
    assert {f.estado for f in filas} == {registro.ESTADO_PENDIENTE}
    assert registro.resumen(filas) == (0, 4)


def test_solo_las_purificadas_quedan_completadas():
    filas = registro.filas_tablero(TOX.get, completadas={"Hospital"})
    assert [f.estado for f in filas] == ["pendiente", "completada", "pendiente", "pendiente"]
    assert registro.resumen(filas) == (1, 4)


def test_la_final_se_completa_al_derrotar_al_jefe_no_por_zonas():
    filas = registro.filas_tablero(TOX.get, completadas={"Alcaldía"})
    assert filas[-1].tipo == registro.TIPO_FINAL and filas[-1].estado == registro.ESTADO_PENDIENTE
    filas = registro.filas_tablero(TOX.get, jefe_derrotado=True)
    assert filas[-1].estado == registro.ESTADO_COMPLETADA


def test_registrar_agrega_una_mazmorra_nueva_y_rechaza_ids_repetidos():
    nueva = registro.EntradaMazmorra("pasillos", "Pasillos amarillos", "Pasillos", mundo="backrooms")
    try:
        registro.registrar(nueva)
        filas = registro.filas_tablero(lambda zona: 40.0)
        assert filas[-1].id == "pasillos" and filas[-1].estado == registro.ESTADO_PENDIENTE
        with pytest.raises(ValueError):
            registro.registrar(nueva)
    finally:
        registro.quitar("pasillos")
    assert len(registro.registro()) == 4


# ----------------------------------------------------------------------
# Escena
# ----------------------------------------------------------------------

def test_plantilla_del_lobby_carga_desde_el_repo():
    plantilla = escena_lobby.cargar_plantilla(raiz=RAIZ)
    assert plantilla is not None and plantilla["id"] == "lobby_hotel"
    assert escena_lobby.cargar_plantilla("no_existe", raiz=RAIZ) is None


def test_profundidad_separa_por_la_base_y_ordena_por_y():
    objetos = [{"y": 90}, {"y": 40}, {"y": 84}, {"y": 70}]
    detras, delante = escena_lobby.separar_por_profundidad(objetos, 84)
    assert [i for i, _ in detras] == [1, 3, 2]
    assert [i for i, _ in delante] == [0]


def test_dinamicos_son_animaciones_luces_que_parpadean_y_relojes():
    assert escena_lobby.es_dinamico({"tipo": "animacion"})
    assert escena_lobby.es_dinamico({"tipo": "prop", "parpadeo": "zumbido"})
    assert escena_lobby.es_dinamico({"tipo": "prop", "reloj": True})
    assert not escena_lobby.es_dinamico({"tipo": "prop"})


@pytest.mark.parametrize("patron", escena_lobby.PATRONES)
def test_brillo_entre_0_y_1_determinista_y_fijo_sin_tiempo(patron):
    valores = [escena_lobby.brillo(patron, i * 0.05, semilla=3) for i in range(1, 400)]
    assert all(0.0 <= v <= 1.0 for v in valores)
    assert valores == [escena_lobby.brillo(patron, i * 0.05, semilla=3) for i in range(1, 400)]
    assert escena_lobby.brillo(patron, 0.0) == 1.0  # reducir movimiento: luz fija


def test_las_luces_que_fallan_si_se_apagan_alguna_vez():
    for patron in ("falla", "neon"):
        assert min(escena_lobby.brillo(patron, i * 0.02, semilla=1) for i in range(1, 600)) < 0.5


def test_patron_desconocido_falla():
    with pytest.raises(ValueError):
        escena_lobby.brillo("discoteca", 1.0)


def test_reloj_marca_la_hora():
    assert escena_lobby.angulos_reloj(3, 0, 0) == (90.0, 0.0, 0.0)
    assert escena_lobby.angulos_reloj(15, 30, 15) == (105.0, 181.5, 90.0)
    x, y = escena_lobby.punta_manecilla((0, 0), 90.0, 10)
    assert (round(x), round(y)) == (10, 0)


def test_motas_de_polvo_quedan_dentro_de_su_rect():
    for t in (0.0, 3.7, 120.0):
        for x, y, alfa in escena_lobby.motas_polvo(20, (0, 16, 432, 74), t):
            assert -6 <= x <= 438 and 16 <= y < 90 and 0 <= alfa <= 255
