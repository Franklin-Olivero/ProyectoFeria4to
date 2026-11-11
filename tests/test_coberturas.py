"""Coberturas rompibles: vida, hitbox, colisión y navegación (lógica pura).

src/dungeon/coberturas.py, navegacion_cuarto.py y zona_coberturas.py no
importan pygame: se prueban con tuplas y objetos mínimos.
"""

import math
import os
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core import balance  # noqa: E402
from src.dungeon import coberturas as reglas  # noqa: E402
from src.dungeon.coberturas import ETAPA_ROTA, Cobertura  # noqa: E402
from src.dungeon.navegacion_cuarto import NavegacionCuarto, segmento_corta  # noqa: E402
from src.dungeon.zona_coberturas import ZonaCoberturas  # noqa: E402

LIMITES = (0, 0, 960, 480)


def _cuerpo(x, y, lado=36):
    """Jugador o enemigo mínimo: posición en float y un rect con centro."""
    rect = SimpleNamespace(width=lado, height=lado, center=(x, y))
    return SimpleNamespace(posicion=SimpleNamespace(x=float(x), y=float(y)), rect=rect)


def test_modulos_de_coberturas_no_importan_pygame():
    codigo = ("import sys; import src.dungeon.coberturas, src.dungeon.navegacion_cuarto, "
              "src.dungeon.zona_coberturas; assert 'pygame' not in sys.modules")
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    assert subprocess.run([sys.executable, "-c", codigo], cwd=raiz).returncode == 0


# ----------------------------------------------------------------------
# Vida y etapas
# ----------------------------------------------------------------------

def test_la_hitbox_es_la_base_del_objeto():
    x, y, ancho, alto = reglas.hitbox_de((100, 200, 90, 100))
    assert y + alto == 300  # apoyada en el piso
    assert alto == round(100 * balance.FRACCION_HITBOX_COBERTURA)  # arriba queda "altura": se pasa por detrás
    assert x > 100 and x + ancho < 190  # un poco más angosta que la imagen


def test_se_rompe_por_etapas_y_rota_no_estorba():
    cobertura = Cobertura("mesa_lab", (0, 0, 90, 100), vida=9)
    assert cobertura.etapa == 0 and not cobertura.rota
    etapas = []
    while not cobertura.rota:
        rompio = cobertura.recibir_impacto(1)
        etapas.append(cobertura.etapa)
    assert rompio and etapas == sorted(etapas)  # solo empeora
    assert set(etapas) == {0, 1, 2, ETAPA_ROTA}  # intacta -> agrietada -> muy dañada -> rota
    assert len(etapas) == 9  # aguanta exactamente su vida en impactos de 1
    assert reglas.solidas([cobertura]) == [] and reglas.golpeada(cobertura.hitbox, [cobertura]) is None
    assert cobertura.recibir_impacto(1) is False  # ya rota: no "se rompe" dos veces


def test_vida_por_clase_y_objetos_sin_hitbox():
    assert reglas.vida_de("columna") > reglas.vida_de("mesa_lab") > reglas.vida_de("silla_oficina")
    assert all(vida > 0 for vida in balance.VIDA_COBERTURA.values())
    assert set(balance.CLASE_COBERTURA.values()) <= set(balance.VIDA_COBERTURA)
    plan = [("mesa_lab", (0, 0, 90, 100), True), ("libros", (200, 0, 36, 46), False)]
    assert [c.nombre for c in reglas.crear(plan)] == ["mesa_lab"]
    assert not reglas.es_solido("libros") and reglas.es_solido("camilla")


# ----------------------------------------------------------------------
# Colisión de cuerpos
# ----------------------------------------------------------------------

def test_separar_frena_en_el_eje_que_choca_y_resbala_por_el_otro():
    mueble = (100, 100, 100, 60)
    # Viene de la izquierda y empuja en diagonal: x se detiene en la cara, y avanza.
    x, y, choco_x, choco_y = reglas.separar((70, 130), (90, 140), (36, 36), [mueble])
    assert (x, choco_x, choco_y) == (100 - 18, True, False) and y == 140
    # Sin muebles en el camino no cambia nada.
    assert reglas.separar((10, 10), (20, 30), (36, 36), [mueble]) == (20, 30, False, False)
    # Nunca termina dentro, venga de donde venga.
    for anterior, nuevo in (((250, 130), (190, 130)), ((150, 60), (150, 95)), ((150, 200), (150, 150))):
        x, y, _, _ = reglas.separar(anterior, nuevo, (36, 36), [mueble])
        assert not reglas.se_tocan((x - 18, y - 18, 36, 36), mueble)


def test_expulsar_saca_por_el_lado_mas_corto_sin_salir_del_cuarto():
    mueble = (0, 100, 100, 60)  # pegado al muro izquierdo
    x, y = reglas.expulsar((30, 150), (36, 36), [mueble], LIMITES)
    assert not reglas.se_tocan((x - 18, y - 18, 36, 36), mueble)
    assert x - 18 >= 0  # no lo saca por el muro aunque sea lo más corto
    assert reglas.expulsar((500, 300), (36, 36), [mueble], LIMITES) == (500, 300)


def test_zona_frena_a_un_cuerpo_y_lo_saca_si_aparece_dentro():
    zona = ZonaCoberturas(LIMITES, [("mesa_lab", (400, 150, 100, 100), True)])
    x0, y0, ancho, alto = zona.lista[0].hitbox
    cuerpo = _cuerpo(x0 - 10, y0 + alto / 2)  # el frame lo metió 8 px en el mueble
    assert zona.frenar(cuerpo, (x0 - 30, y0 + alto / 2)) == (True, False)
    assert cuerpo.posicion.x == x0 - 18 and cuerpo.rect.center[0] == round(x0 - 18)
    dentro = _cuerpo(x0 + ancho / 2, y0 + alto / 2)
    zona.sacar(dentro)
    assert zona.punto_libre((dentro.posicion.x, dentro.posicion.y), (36, 36))


def test_un_enemigo_enganchado_en_una_esquina_la_libra():
    zona = ZonaCoberturas(LIMITES, [("mesa_lab", (400, 150, 100, 100), True)])
    x0, y0, _, _ = zona.lista[0].hitbox
    # Camina a la derecha y su borde inferior roza 4 px la esquina de arriba del mueble.
    cuerpo = _cuerpo(x0 - 16, y0 - 14)
    zona.frenar(cuerpo, (x0 - 20, y0 - 14), resbalar=3)
    assert cuerpo.posicion.y < y0 - 14  # se corrió hacia arriba, hacia el lado libre
    # De frente al mueble no resbala: eso lo resuelve el grafo.
    de_frente = _cuerpo(x0 - 16, y0 + 30)
    zona.frenar(de_frente, (x0 - 20, y0 + 30), resbalar=3)
    assert de_frente.posicion.y == y0 + 30


# ----------------------------------------------------------------------
# Navegación (grafo de celdas + BFS)
# ----------------------------------------------------------------------

def test_segmento_corta():
    rect = (40, 40, 20, 20)
    assert segmento_corta((0, 50), (100, 50), rect)
    assert segmento_corta((0, 0), (100, 100), rect)
    assert not segmento_corta((0, 0), (100, 0), rect)
    assert not segmento_corta((0, 50), (30, 50), rect)  # se queda corto


def test_sin_muebles_va_derecho_y_con_uno_en_medio_lo_rodea():
    libre = NavegacionCuarto(LIMITES)
    assert libre.direccion((100, 240), (800, 240)) == (1.0, 0.0)
    muro = (440, 120, 80, 240)  # un mueble alto entre los dos
    nav = NavegacionCuarto(LIMITES, [muro])
    dx, dy = nav.direccion((300, 240), (700, 240))
    assert abs(dy) > 0.3  # ya no es la línea recta: se abre para rodearlo
    assert math.isclose(math.hypot(dx, dy), 1.0)


def test_siguiendo_la_direccion_se_llega_al_otro_lado():
    """Un perseguidor simulado (con la misma colisión del juego) alcanza al
    jugador escondido detrás de un mueble."""
    zona = ZonaCoberturas(LIMITES, [("estanteria", (430, 40, 100, 330), True)])
    cuerpo = _cuerpo(300, 240, lado=48)
    destino = (700, 240)
    for _ in range(600):
        anterior = (cuerpo.posicion.x, cuerpo.posicion.y)
        dx, dy = zona.navegacion.direccion(anterior, destino, 25)
        cuerpo.posicion.x += dx * 3
        cuerpo.posicion.y += dy * 3
        zona.frenar(cuerpo, anterior, resbalar=3)
        if math.dist((cuerpo.posicion.x, cuerpo.posicion.y), destino) < 30:
            break
    assert math.dist((cuerpo.posicion.x, cuerpo.posicion.y), destino) < 30


def test_al_romperse_un_mueble_su_hueco_se_vuelve_camino():
    # Una pared de lado a lado con un solo mueble rompible en el medio.
    plan = [("columna", (0, 100, 440, 100), True), ("mesa_lab", (440, 100, 80, 100), True),
            ("columna", (520, 100, 440, 100), True)]
    zona = ZonaCoberturas(LIMITES, plan)
    arriba, abajo = (480, 40), (480, 400)
    assert not zona.navegacion.alcanzable(arriba, abajo)
    zona.lista[1].romper()
    zona._anotar(zona.lista[1])
    zona.actualizar(0.016)  # rehace el grafo
    assert zona.navegacion.alcanzable(arriba, abajo)


def test_asegurar_caminos_quita_lo_que_encierra():
    plan = [("columna", (0, 100, 960, 100), True)]  # parte el cuarto en dos
    zona = ZonaCoberturas(LIMITES, plan)
    zona.asegurar_caminos([(480, 40)], (480, 400))
    assert zona.lista == [] and zona.navegacion.alcanzable((480, 40), (480, 400))


# ----------------------------------------------------------------------
# Balas y red
# ----------------------------------------------------------------------

class _Bala:
    def __init__(self, rect, danio=1):
        self.rect, self.danio, self.vivo = rect, danio, True

    def colisiona_con(self, otro):
        return self.vivo and reglas.se_tocan(self.rect, otro.rect)

    def al_chocar_cobertura(self, cobertura):
        cobertura.recibir_impacto(self.danio)
        self.vivo = False


def test_una_bala_se_frena_en_el_mueble_y_lo_va_rompiendo():
    zona = ZonaCoberturas(LIMITES, [("silla_oficina", (400, 150, 52, 100), True)])
    cobertura = zona.lista[0]
    x, y, _, _ = cobertura.hitbox
    assert zona.impactar(_Bala((10, 10, 6, 6))) is None  # lejos: sigue de largo
    disparos = 0
    while not cobertura.rota:
        bala = _Bala((x + 5, y + 5, 6, 6))
        assert zona.impactar(bala) is cobertura and not bala.vivo
        disparos += 1
    assert disparos == cobertura.vida_maxima
    assert zona.rotas_recientes == [cobertura]
    assert zona.impactar(_Bala((x + 5, y + 5, 6, 6))) is None  # rota: ya no cubre


def test_el_invitado_copia_las_vidas_del_host_y_no_dania_por_su_cuenta():
    plan = [("mesa_lab", (100, 100, 90, 100), True), ("silla_oficina", (400, 150, 52, 100), True)]
    host, invitado = ZonaCoberturas(LIMITES, plan), ZonaCoberturas(LIMITES, plan)
    host.lista[1].romper()
    host.lista[0].recibir_impacto(3)
    invitado.aplicar_vidas(host.vidas())
    assert invitado.vidas() == host.vidas() and invitado.lista[1].rota
    assert invitado.rotas_recientes == [invitado.lista[1]]
    x, y, _, _ = invitado.lista[0].hitbox
    bala = _Bala((x + 5, y + 5, 6, 6))
    assert invitado.impactar(bala) is invitado.lista[0] and not bala.vivo  # la frena...
    assert invitado.vidas() == host.vidas()  # ...pero el daño lo decide el host
    invitado.aplicar_vidas([1])  # un estado de otro cuarto (otra cantidad) se ignora
    assert invitado.vidas() == host.vidas()
