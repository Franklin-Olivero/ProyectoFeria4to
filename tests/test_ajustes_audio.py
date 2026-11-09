"""Ajustes de audio (sin pygame): valores por defecto, archivo, valores
corruptos o ausentes, recorte 0-100, volumen efectivo y silencio."""

import json
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

import pytest  # noqa: E402

from src.audio.ajustes_audio import (  # noqa: E402
    NOMBRE_ARCHIVO,
    AjustesAudio,
    a_dict,
    cargar,
    desde_dict,
    guardar,
    valor_valido,
    volumen_efectivo,
)
from src.core.datos_usuario import carpeta_datos  # noqa: E402


def test_modulo_no_importa_pygame():
    codigo = "import sys, src.audio.ajustes_audio, src.ui.pausa; print('pygame' in sys.modules)"
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


def test_valores_predeterminados():
    a = AjustesAudio()
    assert (a.volumen_general, a.volumen_musica, a.volumen_efectos, a.silencio) == (100, 70, 80, False)


# ----------------------------------------------------------------------
# Archivo
# ----------------------------------------------------------------------

def test_guardar_y_cargar(tmp_path):
    ruta = str(tmp_path / "ajustes_audio.json")
    ajustes = AjustesAudio(volumen_general=10, volumen_musica=35, volumen_efectos=0, silencio=True)
    assert guardar(ajustes, ruta)
    assert cargar(ruta) == ajustes
    assert not os.path.exists(ruta + ".tmp")
    assert json.loads(open(ruta, encoding="utf-8").read())["version"] == 1


def test_archivo_ausente_o_corrupto_da_valores_por_defecto(tmp_path):
    assert cargar(str(tmp_path / "no_existe.json")) == AjustesAudio()
    corrupto = tmp_path / "corrupto.json"
    corrupto.write_text("{ volumen: alto", encoding="utf-8")
    assert cargar(str(corrupto)) == AjustesAudio()
    lista = tmp_path / "lista.json"
    lista.write_text("[1, 2, 3]", encoding="utf-8")
    assert cargar(str(lista)) == AjustesAudio()


def test_campos_invalidos_o_ausentes_toman_su_valor_por_defecto():
    a = desde_dict({
        "volumen_general": "fuerte",
        "volumen_musica": True,  # bool no es un volumen
        "volumen_efectos": None,
        "silencio": "si",
        "otro": 3,
    })
    assert a == AjustesAudio()
    assert desde_dict({"volumen_musica": 20}) == AjustesAudio(volumen_musica=20)
    assert desde_dict({"volumen_general": float("nan")}).volumen_general == 100


@pytest.mark.parametrize("entrada, esperado", [(250, 100), (-30, 0), (33.6, 34), (0, 0), (100, 100)])
def test_volumenes_se_recortan_a_0_100(entrada, esperado):
    assert desde_dict({"volumen_general": entrada}).volumen_general == esperado
    assert valor_valido("volumen_efectos", entrada) == esperado


def test_sin_archivo_se_rescatan_los_volumenes_de_un_preferencias_viejo(tmp_path):
    viejo = tmp_path / "preferencias.json"
    viejo.write_text(json.dumps({"volumen_musica": 10, "volumen_efectos": 20, "subtitulos": True}), encoding="utf-8")
    ajustes = cargar(str(tmp_path / "nuevo.json"), ruta_legado=str(viejo))
    assert (ajustes.volumen_musica, ajustes.volumen_efectos, ajustes.volumen_general) == (10, 20, 100)
    # Si ya hay archivo nuevo, el viejo no se mira.
    nuevo = tmp_path / "ajustes.json"
    guardar(AjustesAudio(volumen_musica=90), str(nuevo))
    assert cargar(str(nuevo), ruta_legado=str(viejo)).volumen_musica == 90


def test_ida_y_vuelta_por_dict():
    a = AjustesAudio(volumen_general=42, silencio=True)
    assert desde_dict(a_dict(a)) == a


# ----------------------------------------------------------------------
# Carpeta de datos de usuario (nunca el repositorio)
# ----------------------------------------------------------------------

def test_carpeta_de_datos_por_sistema():
    assert carpeta_datos({"APPDATA": r"C:\U\x\AppData\Roaming"}, "win32", r"C:\U\x").endswith("Civitas")
    assert carpeta_datos({}, "darwin", "/Users/x") == os.path.join("/Users/x", "Library", "Application Support",
                                                                   "Civitas")
    assert carpeta_datos({}, "linux", "/home/x") == os.path.join("/home/x", ".local", "share", "civitas")
    assert carpeta_datos({"XDG_DATA_HOME": "/datos"}, "linux", "/home/x") == os.path.join("/datos", "civitas")
    assert carpeta_datos({"CIVITAS_DATOS": "/tmp/prueba"}, "win32", "C:/") == "/tmp/prueba"


def test_por_defecto_se_guarda_fuera_del_repositorio(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVITAS_DATOS", str(tmp_path / "civitas"))
    assert guardar(AjustesAudio(volumen_general=10))
    assert (tmp_path / "civitas" / NOMBRE_ARCHIVO).exists()
    assert cargar().volumen_general == 10
    assert not os.path.exists(os.path.join(RAIZ, NOMBRE_ARCHIVO))


# ----------------------------------------------------------------------
# Volumen efectivo
# ----------------------------------------------------------------------

def test_volumen_efectivo_es_el_producto_de_todo():
    a = AjustesAudio(volumen_general=50, volumen_musica=40, volumen_efectos=80)
    assert volumen_efectivo(a, es_musica=True) == pytest.approx(0.5 * 0.4)
    assert volumen_efectivo(a, es_musica=False) == pytest.approx(0.5 * 0.8)
    assert volumen_efectivo(a, False, mezcla_categoria=0.8, ganancia=0.5, atenuacion=0.5) == pytest.approx(
        0.5 * 0.8 * 0.8 * 0.5 * 0.5)


def test_silencio_da_cero_sin_perder_los_volumenes():
    a = AjustesAudio(volumen_general=60, silencio=True)
    assert volumen_efectivo(a, True) == 0.0 and volumen_efectivo(a, False) == 0.0
    a.silencio = False
    assert volumen_efectivo(a, True) == pytest.approx(0.6 * 0.7)


def test_volumen_efectivo_nunca_pasa_de_1_ni_baja_de_0():
    a = AjustesAudio(volumen_general=100, volumen_musica=100)
    assert volumen_efectivo(a, True, mezcla_categoria=2.0, ganancia=3.0) == 1.0
    assert volumen_efectivo(AjustesAudio(volumen_general=0), True) == 0.0
