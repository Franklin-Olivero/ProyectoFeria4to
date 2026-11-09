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
    assert p.hud_detallado is False  # HUD limpio por defecto
    assert p.instrucciones_mazmorra == "siempre"
    assert p.subtitulos is False
    assert p.filtro_daltonismo == FILTRO_NINGUNO
    assert p.reducir_movimiento is False
    assert p.esquema_controles == "teclado"
    assert p.mostrar_cono is True
    assert p.opacidad_cono == 40


def test_ida_y_vuelta_por_dict():
    p = Preferencias(hud_detallado=False, subtitulos=True, filtro_daltonismo="Tritanopia",
                     esquema_controles="mando", opacidad_cono=0)
    assert desde_dict(a_dict(p)) == p
    assert a_dict(p)["version"] == 1


def test_campos_invalidos_toman_su_valor_predeterminado():
    p = desde_dict({
        "opacidad_cono": "fuerte",  # tipo equivocado
        "hud_detallado": "no",  # texto no es bool
        "subtitulos": 1,  # 1 no es bool
        "filtro_daltonismo": "Acromatopsia",  # opción inexistente
        "esquema_controles": None,
        "desconocido": 5,  # campo que no existe: se ignora
    })
    assert p == Preferencias()


def test_porcentajes_se_recortan_a_0_100():
    assert desde_dict({"opacidad_cono": 250}).opacidad_cono == 100
    assert desde_dict({"opacidad_cono": -30}).opacidad_cono == 0
    assert desde_dict({"opacidad_cono": 33.6}).opacidad_cono == 34


def test_campos_faltantes_y_no_dict():
    assert desde_dict({"subtitulos": True}).opacidad_cono == 40
    assert desde_dict(["no", "es", "dict"]) == Preferencias()


def test_guardar_y_cargar(tmp_path):
    ruta = str(tmp_path / "prefs.json")
    p = Preferencias(opacidad_cono=25, reducir_movimiento=True)
    assert guardar(p, ruta)
    assert cargar(ruta) == p
    assert not os.path.exists(ruta + ".tmp")


def test_archivo_inexistente_o_corrupto_da_predeterminados(tmp_path):
    assert cargar(str(tmp_path / "no_existe.json"), ruta_legado=None) == Preferencias()
    corrupto = tmp_path / "corrupto.json"
    corrupto.write_text("{ esto no es json", encoding="utf-8")
    assert cargar(str(corrupto), ruta_legado=None) == Preferencias()


def test_archivo_de_version_anterior_conserva_lo_valido(tmp_path):
    viejo = tmp_path / "viejo.json"
    viejo.write_text(json.dumps({"version": 0, "volumen_musica": 15, "subtitulos": True, "brillo": 3}),
                     encoding="utf-8")
    p = cargar(str(viejo))
    assert p.subtitulos is True  # lo válido se conserva; el volumen ya no vive aquí
    assert p.opacidad_cono == 40


def test_sin_archivo_nuevo_se_lee_el_preferencias_viejo_del_juego(tmp_path):
    viejo = tmp_path / "preferencias.json"
    viejo.write_text(json.dumps({"reducir_movimiento": True}), encoding="utf-8")
    assert cargar(str(tmp_path / "datos" / "preferencias.json"), ruta_legado=str(viejo)).reducir_movimiento


def test_por_defecto_se_guarda_en_la_carpeta_de_datos_de_usuario(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVITAS_DATOS", str(tmp_path / "civitas"))
    assert guardar(Preferencias(subtitulos=True))
    assert (tmp_path / "civitas" / "preferencias.json").exists()
    assert cargar(ruta_legado=None).subtitulos is True
