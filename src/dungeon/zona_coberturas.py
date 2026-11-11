"""Las coberturas de un lugar de combate y todo lo que chocan (puro, sin Pygame).

Junta la lista de Cobertura de un cuarto (src/dungeon/coberturas.py) con
su grafo de navegación (src/dungeon/navegacion_cuarto.py) y ofrece las
operaciones que usan el cuarto, la arena del jefe y el loop de combate:

    frenar(cuerpo, anterior)   un jugador o enemigo no atraviesa un mueble
    sacar(cuerpo)              lo saca si quedó dentro de uno
    impactar(proyectil)        una bala choca con un mueble y lo daña
    aplastar(rect)             el jefe rompe lo que pisa
    asegurar_caminos(puntos)   ningún mueble deja una puerta sin salida
    actualizar(dt)             temblores y, si algo se rompió, rehace el grafo

Un `cuerpo` es cualquier cosa con `.posicion` (x, y en float) y `.rect`
(con width, height y center): jugadores y enemigos.
`vidas()` / `aplicar_vidas()` copian el estado para el modo en red.
"""

from src.core.balance import ESQUINA_COBERTURA
from src.dungeon import coberturas as reglas
from src.dungeon.navegacion_cuarto import NavegacionCuarto


class ZonaCoberturas:
    def __init__(self, limites, plan=()):
        """`limites` = (izquierda, arriba, derecha, abajo) del cuarto;
        `plan` = [(nombre, rect, solido)] (src/ui/decor_mazmorra.plan)."""
        self.limites = tuple(limites)
        self.lista = reglas.crear(plan)
        self.navegacion = NavegacionCuarto(self.limites, self.solidas())
        self._grafo_viejo = False
        self.rotas_recientes = []  # coberturas rotas este frame (para polvo y sonido)
        # Modo en red, invitado: las balas se frenan aquí pero el daño lo
        # decide el host (llega con aplicar_vidas). Lo activa el primer estado.
        self.espejo = False

    def __bool__(self):
        return bool(self.lista)

    def solidas(self):
        return reglas.solidas(self.lista)

    def en_pie(self):
        return [c for c in self.lista if not c.rota]

    # ------------------------------------------------------------------
    # Cuerpos
    # ------------------------------------------------------------------

    @staticmethod
    def _tamanio(cuerpo):
        return (cuerpo.rect.width, cuerpo.rect.height)

    @staticmethod
    def _poner(cuerpo, x, y):
        cuerpo.posicion.x, cuerpo.posicion.y = x, y
        cuerpo.rect.center = (round(x), round(y))

    def frenar(self, cuerpo, anterior, resbalar=0.0):
        """Corrige el movimiento de este frame de `cuerpo` (venía de
        `anterior`): contra un mueble se detiene en ese eje y resbala por
        el otro. Con `resbalar` (px), si quedó enganchado en una esquina
        se corre hasta esa distancia para librarla (los enemigos no se
        traban en el canto de un mueble). Devuelve (choco_x, choco_y).
        O(n) con n coberturas."""
        obstaculos = self.solidas()
        if not obstaculos:
            return (False, False)
        tamanio = self._tamanio(cuerpo)
        # Si ya venía dentro de uno (lo empujaron, apareció ahí), primero sale.
        anterior = reglas.expulsar(anterior, tamanio, obstaculos, self.limites)
        pedido = (cuerpo.posicion.x, cuerpo.posicion.y)
        x, y, choco_x, choco_y = reglas.separar(anterior, pedido, tamanio, obstaculos)
        if resbalar > 0 and choco_x != choco_y:
            x, y = self._librar_esquina((x, y), pedido, tamanio, obstaculos, choco_x, resbalar)
        if choco_x or choco_y or (x, y) != pedido:
            self._poner(cuerpo, x, y)
        return (choco_x, choco_y)

    @staticmethod
    def _librar_esquina(centro, pedido, tamanio, obstaculos, en_x, paso):
        """Chocó en un solo eje: si el mueble apenas lo engancha por una
        esquina (menos de ESQUINA_COBERTURA px), se corre por el otro eje
        hacia el lado libre, hasta `paso` px, sin meterse en otro mueble."""
        x, y = centro
        ancho, alto = tamanio
        intento = (pedido[0], y) if en_x else (x, pedido[1])
        cuerpo = (intento[0] - ancho / 2, intento[1] - alto / 2, ancho, alto)
        for ox, oy, ow, oh in obstaculos:
            if not reglas.se_tocan(cuerpo, (ox, oy, ow, oh)):
                continue
            if en_x:
                antes, despues = (y + alto / 2) - oy, (oy + oh) - (y - alto / 2)
            else:
                antes, despues = (x + ancho / 2) - ox, (ox + ow) - (x - ancho / 2)
            enganche = min(antes, despues)
            if enganche > ESQUINA_COBERTURA:
                return (x, y)  # está de frente al mueble: lo rodea el grafo
            corrimiento = min(paso, enganche) * (-1 if antes <= despues else 1)
            destino = (x, y + corrimiento) if en_x else (x + corrimiento, y)
            nx, ny, _, _ = reglas.separar((x, y), destino, tamanio, obstaculos)
            return (nx, ny)
        return (x, y)

    def sacar(self, cuerpo):
        """Si `cuerpo` quedó dentro de un mueble, lo corre al borde más cercano."""
        obstaculos = self.solidas()
        if not obstaculos:
            return
        x, y = reglas.expulsar((cuerpo.posicion.x, cuerpo.posicion.y), self._tamanio(cuerpo),
                               obstaculos, self.limites)
        if (x, y) != (cuerpo.posicion.x, cuerpo.posicion.y):
            self._poner(cuerpo, x, y)

    def punto_libre(self, punto, tamanio):
        """¿Cabe un cuerpo de `tamanio` centrado en `punto` sin tocar un mueble?"""
        cuerpo = (punto[0] - tamanio[0] / 2, punto[1] - tamanio[1] / 2, tamanio[0], tamanio[1])
        return not any(reglas.se_tocan(cuerpo, o) for o in self.solidas())

    # ------------------------------------------------------------------
    # Daño
    # ------------------------------------------------------------------

    def impactar(self, proyectil):
        """Si `proyectil` toca un mueble en pie, le aplica su efecto
        (`proyectil.al_chocar_cobertura`: por defecto lo daña y se
        destruye). Devuelve la cobertura golpeada o None."""
        if not getattr(proyectil, "vivo", False):
            return None
        for cobertura in self.lista:
            if cobertura.rota or not proyectil.colisiona_con(_Rect(cobertura.hitbox)):
                continue
            vida_antes = cobertura.vida
            proyectil.al_chocar_cobertura(cobertura)
            if cobertura.vida == vida_antes:
                continue  # ya la había golpeado (onda expansiva)
            if self.espejo:
                cobertura.vida = vida_antes  # el daño real llega del host
            self._anotar(cobertura)
            return cobertura
        return None

    def aplastar(self, rect):
        """Rompe de golpe los muebles que toca `rect` (x, y, w, h): el jefe."""
        for cobertura in self.lista:
            if not cobertura.rota and reglas.se_tocan(rect, cobertura.hitbox):
                cobertura.romper()
                self._anotar(cobertura)

    def _anotar(self, cobertura):
        if cobertura.rota:
            self.rotas_recientes.append(cobertura)
            self._grafo_viejo = True

    def actualizar(self, dt):
        for cobertura in self.lista:
            cobertura.actualizar(dt)
        if self._grafo_viejo:
            # Se rompió algo: su hueco ahora es camino.
            self.navegacion.reconstruir(self.solidas())
            self._grafo_viejo = False

    # ------------------------------------------------------------------
    # Caminos
    # ------------------------------------------------------------------

    def asegurar_caminos(self, puntos, desde):
        """Garantía de diseño: desde `desde` se llega caminando a todos los
        `puntos` (puertas, evidencia). Si un mueble lo impide, se quitan
        coberturas del plan, de la última a la primera, hasta que haya
        camino (un BFS por intento). En la práctica el plan ya lo cumple."""
        while self.lista and not all(self.navegacion.alcanzable(p, desde) for p in puntos):
            self.lista.pop()
            self.navegacion.reconstruir(self.solidas())

    # ------------------------------------------------------------------
    # Red: el host manda la vida de cada cobertura, en orden
    # ------------------------------------------------------------------

    def vidas(self):
        return [c.vida for c in self.lista]

    def aplicar_vidas(self, vidas):
        """Copia las vidas del host (misma lista, mismo orden: el plan es
        determinista). Lo que se rompió allá se rompe aquí."""
        if not isinstance(vidas, list) or len(vidas) != len(self.lista):
            return
        self.espejo = True
        for cobertura, vida in zip(self.lista, vidas):
            if not isinstance(vida, (int, float)) or vida == cobertura.vida:
                continue
            en_pie = not cobertura.rota
            if vida < cobertura.vida:
                cobertura.recibir_impacto(cobertura.vida - vida)
            else:
                cobertura.vida = min(cobertura.vida_maxima, vida)
            if en_pie and cobertura.rota:
                self._anotar(cobertura)
            elif en_pie != (not cobertura.rota):
                self._grafo_viejo = True


class _Rect:
    """Rect mínimo (left/top/right/bottom) para `proyectil.colisiona_con`,
    que acepta un pygame.Rect o cualquier cosa con esos lados."""

    __slots__ = ("rect", "left", "top", "right", "bottom", "x", "y", "width", "height", "w", "h")

    def __init__(self, rect):
        self.rect = tuple(rect)  # pygame.Rect.colliderect acepta un objeto con `.rect`
        self.x, self.y, self.width, self.height = rect
        self.w, self.h = self.width, self.height
        self.left, self.top = self.x, self.y
        self.right, self.bottom = self.x + self.width, self.y + self.height
