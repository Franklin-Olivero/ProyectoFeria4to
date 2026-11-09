"""Preferencias del jugador: valores predeterminados, validación y archivo (sin pygame)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.preferencias import (  # noqa: E402
    FILTRO_NINGUNO,
    Preferencias,
    a_dict,
    cargar,
    desde_dict,
    guardar,
)


def test_modulo_no_importa_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = "import sys, src.core.preferencias; print('pygame' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "False"


def test_valores_predeterminados_explicitos():
    p = Preferencias()
    assert (p.volumen_musica, p.volumen_efectos) == (70, 80)
    assert p.subtitulos is False
    assert p.filtro_daltonismo == FILTRO_NINGUNO
    assert p.reducir_movimiento is False
    assert p.esquema_controles == "teclado"
    assert p.mostrar_cono is True
    assert p.opacidad_cono == 40


def test_ida_y_vuelta_por_dict():
    p = Preferencias(volumen_musica=10, subtitulos=True, filtro_daltonismo="Tritanopia",
                     esquema_controles="mando", opacidad_cono=0)
    assert desde_dict(a_dict(p)) == p
    assert a_dict(p)["version"] == 1


def test_campos_invalidos_toman_su_valor_predeterminado():
    p = desde_dict({
        "volumen_musica": "fuerte",  # tipo equivocado
        "volumen_efectos": True,  # bool no es un volumen
        "subtitulos": 1,  # 1 no es bool
        "filtro_daltonismo": "Acromatopsia",  # opción inexistente
        "esquema_controles": None,
        "desconocido": 5,  # campo que no existe: se ignora
    })
    assert p == Preferencias()


def test_porcentajes_se_recortan_a_0_100():
    p = desde_dict({"volumen_musica": 250, "volumen_efectos": -30, "opacidad_cono": 33.6})
    assert (p.volumen_musica, p.volumen_efectos, p.opacidad_cono) == (100, 0, 34)


def test_campos_faltantes_y_no_dict():
    assert desde_dict({"subtitulos": True}).volumen_musica == 70
    assert desde_dict(["no", "es", "dict"]) == Preferencias()


def test_guardar_y_cargar(tmp_path):
    ruta = str(tmp_path / "prefs.json")
    p = Preferencias(volumen_efectos=25, reducir_movimiento=True)
    assert guardar(p, ruta)
    assert cargar(ruta) == p
    assert not os.path.exists(ruta + ".tmp")


def test_archivo_inexistente_o_corrupto_da_predeterminados(tmp_path):
    assert cargar(str(tmp_path / "no_existe.json")) == Preferencias()
    corrupto = tmp_path / "corrupto.json"
    corrupto.write_text("{ esto no es json", encoding="utf-8")
    assert cargar(str(corrupto)) == Preferencias()


def test_archivo_de_version_anterior_conserva_lo_valido(tmp_path):
    viejo = tmp_path / "viejo.json"
    viejo.write_text(json.dumps({"version": 0, "volumen_musica": 15, "brillo": 3}), encoding="utf-8")
    p = cargar(str(viejo))
    assert p.volumen_musica == 15
    assert p.volumen_efectos == 80
