"""Constantes visuales centralizadas: paleta, fuentes, tamaños y layout.

Todo elemento visual del juego referencia sus colores, tamaños,
posiciones y rutas de archivo desde aquí en lugar de usar valores
hardcodeados dispersos en la lógica. Los sprites en pixel art viven en
src/ui/sprites.py (dibujados en código, sin archivos de imagen); cuando
se agregue arte real, el cambio se limita a reemplazar esos sprites y
los valores de este archivo, sin tocar la lógica de juego.

La pantalla es de 1280x720 (src/core/config.py): HUD arriba (0-62),
barra de controles abajo (660-720) y el cuarto (o la vista de Ciudad
Nova, bajo el cintillo de noticias) en medio.
"""

import os

# ----------------------------------------------------------------------
# Paleta general (estilo "neón sobre noche": 4 acentos sobre azul oscuro)
# ----------------------------------------------------------------------
COLOR_FONDO = (15, 13, 34)
COLOR_FONDO_PANEL = (22, 20, 46)
COLOR_FONDO_PANEL_CLARO = (30, 28, 60)
COLOR_BORDE_PANEL = (58, 54, 100)
COLOR_LINEA_HUD = (44, 40, 80)

COLOR_TEAL = (62, 230, 196)
COLOR_TEAL_OSCURO = (18, 92, 82)
COLOR_MAGENTA = (255, 56, 120)
COLOR_MAGENTA_OSCURO = (110, 26, 60)
COLOR_AMARILLO = (255, 190, 60)
COLOR_MORADO = (164, 110, 255)
COLOR_MORADO_OSCURO = (70, 48, 120)

COLOR_TEXTO_HUD = (236, 236, 246)
COLOR_TEXTO_SECUNDARIO = (150, 150, 182)
COLOR_TEXTO_APAGADO = (96, 94, 130)

# ----------------------------------------------------------------------
# Fuentes (JetBrains Mono, licencia OFL, en assets/fonts). Si el archivo
# falta, src/ui/fuentes.py cae a la fuente por defecto de pygame.
# ----------------------------------------------------------------------
RUTA_FUENTE_REGULAR = os.path.join("assets", "fonts", "JetBrainsMono-Regular.ttf")
RUTA_FUENTE_NEGRITA = os.path.join("assets", "fonts", "JetBrainsMono-Bold.ttf")
TAMANIO_FUENTE_PEQUENA = 13
TAMANIO_FUENTE_NORMAL = 15
TAMANIO_FUENTE_MEDIA = 18
TAMANIO_FUENTE_TITULO = 22
TAMANIO_FUENTE_GRANDE = 34
TAMANIO_FUENTE_ENORME = 48
# Compatibilidad con módulos que piden "la fuente del HUD".
TAMANIO_FUENTE_HUD = TAMANIO_FUENTE_NORMAL
TAMANIO_FUENTE_SELECCION = TAMANIO_FUENTE_NORMAL
TAMANIO_FUENTE_MAPA = TAMANIO_FUENTE_NORMAL
TAMANIO_FUENTE_MINIMAPA = TAMANIO_FUENTE_PEQUENA
TAMANIO_FUENTE_TITULO_VICTORIA = TAMANIO_FUENTE_GRANDE

# ----------------------------------------------------------------------
# Layout general
# ----------------------------------------------------------------------
ALTO_HUD = 62
ALTO_BARRA_CONTROLES = 60
RADIO_PANEL = 6  # esquinas redondeadas de paneles y chips
ESCALA_PIXEL = 3  # 1 píxel de sprite = 3 píxeles de pantalla

# HUD superior
POSICION_JUGADOR_HUD = (26, 31)  # centro de "J1"
POSICION_CORAZONES = (72, 20)  # esquina superior izq. del primer corazón
SEPARACION_CORAZONES = 25
POSICION_HABILIDAD_HUD = (72, 46)  # barra de carga de la habilidad (F)
ANCHO_BARRA_HABILIDAD = 120
ALTO_BARRA_HABILIDAD = 6
POSICION_ENEMIGOS_HUD = (300, 16)
POSICION_TITULO_HUD = (640, 24)  # centro del título del lugar
POSICION_SUBTITULO_HUD = (640, 46)
RECT_BARRA_COLAPSO = (880, 34, 260, 16)  # x, y, ancho, alto
POSICION_ETIQUETA_COLAPSO = (880, 16)
POSICION_VALOR_COLAPSO = (1156, 42)  # midleft del porcentaje
COLOR_BARRA_COLAPSO = COLOR_AMARILLO
COLOR_FONDO_BARRA = (38, 36, 74)
COLOR_BORDE_BARRA = (74, 70, 120)
# Paneles laterales (cooperativo): J1 en el margen izquierdo y J2 en el
# derecho, entre el muro del cuarto (x 122-1158) y el borde de la pantalla.
RECTS_PANEL_JUGADOR = (
    (4, 75, 114, 270),     # J1 (arriba izq)
    (1162, 75, 114, 270),   # J2 (arriba der)
    (4, 360, 114, 270),    # J3 (abajo izq)
    (1162, 360, 114, 270),  # J4 (abajo der)
)  # x, y, ancho, alto para hasta 4 jugadores
CORAZONES_POR_FILA_PANEL = 4
ANCHO_BARRA_HABILIDAD_PANEL = 70
TAMANIO_FUENTE_MINI = 10  # controles clave del panel ("Stick R Apuntar" debe caber en 96 px)

# Indicador del cooldown del dash (círculo con un muñeco corriendo)
RADIO_INDICADOR_DASH = 22
OSCURECER_INDICADOR_DASH = 0.5  # recargando: el icono a la mitad de brillo
COLOR_FONDO_INDICADOR_DASH = (14, 12, 32)
ALFA_AGUA_INDICADOR_DASH = 150  # el "agua" que sube mientras recarga
AMPLITUD_OLA_DASH = 2.5  # px
LARGO_OLA_DASH = 18  # px entre crestas
VELOCIDAD_OLA_DASH = 6.0  # rad/s: qué tan rápido se mueve la ola
CAPAS_AURA_DASH = 4  # anillos del aura neón cuando está listo
ALFA_AURA_DASH = 70  # alfa del anillo más interno (los de afuera se desvanecen)
DURACION_FLASH_DASH = 0.15  # s del destello al quedar disponible
COLOR_FLASH_DASH = (255, 255, 255)
ESCALA_ICONO_DASH = 2
# Compatibilidad: textos sueltos del HUD antiguo
POSICION_TEXTO_COLAPSO = (10, 10)
POSICION_TEXTO_CARGA = (10, 40)

# Chips de tecla en la barra de controles
COLOR_FONDO_CHIP = (30, 28, 62)
COLOR_BORDE_CHIP = (72, 68, 118)
ALTO_CHIP = 26
MARGEN_CHIP = 8
SEPARACION_CONTROLES = 22

# ----------------------------------------------------------------------
# Jugador (comunes a los 4 roles). Velocidad, vida, daño, cadencia y
# carga de cada rol viven en src/core/balance.py.
# ----------------------------------------------------------------------
TAMANIO_JUGADOR = 36
COLOR_CIUDADANO = COLOR_TEAL
COLOR_INFLUENCER = (255, 120, 220)
COLOR_PERIODISTA = (236, 236, 246)
COLOR_CANDIDATO = COLOR_AMARILLO
# Cono de apuntado: abanico translúcido hacia donde mira el jugador.
COLOR_CONO_APUNTADO = (255, 56, 120, 46)  # RGBA
LARGO_CONO_APUNTADO = 230
ANGULO_CONO_ESTRECHO = 8  # grados a cada lado, roles sin abanico

# Dash: partículas (src/ui/particulas.py) e imágenes fantasma. Solo visual;
# la duración y velocidad del dash viven en src/core/balance.py.
DASH_PARTICULAS_POR_FRAME = 3  # partículas emitidas por frame durante el dash
DASH_PARTICULA_RADIO = 5  # radio inicial de cada partícula
DASH_PARTICULA_DISPERSION = 10  # px: desvío aleatorio de la partícula respecto al jugador
DASH_PARTICULA_DURACION = 0.2  # segundos que vive cada partícula
DASH_PARTICULA_ALFA_INICIAL = 160  # alfa 0-255
DASH_AFTERIMAGES = 3  # cuántas imágenes fantasma dejar
DASH_AFTERIMAGE_ALFA = (120, 70, 30)  # alfa de cada una, de la más nueva a la más vieja

# Cooperativo: separación entre jugadores al aparecer (entrada, puerta, arena).
SEPARACION_JUGADORES_COOP = 56
# Indicador de apuntado del J2 (no tiene mira de mouse).
LARGO_INDICADOR_J2 = 34  # px desde el centro del jugador hasta la punta
TAMANIO_PUNTA_INDICADOR_J2 = 8

# ----------------------------------------------------------------------
# Proyectiles
# ----------------------------------------------------------------------
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = COLOR_TEAL
COLOR_PROYECTIL_ENEMIGO = COLOR_MORADO
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
DANIO_PROYECTIL_ENEMIGO = 1
# Estela punteada detrás de cada proyectil (solo dibujo, sin estado).
PUNTOS_ESTELA_PROYECTIL = 4
ESPACIADO_ESTELA_PROYECTIL = 14
ALFA_ESTELA_PROYECTIL = 130

# ----------------------------------------------------------------------
# Enemigo
# ----------------------------------------------------------------------
TAMANIO_ENEMIGO = 40
COLOR_ENEMIGO = COLOR_MAGENTA
COLOR_ENEMIGO_SECUNDARIO = COLOR_MORADO
VELOCIDAD_ENEMIGO = 90  # píxeles por segundo
VIDA_ENEMIGO = 3
RANGO_DISPARO_ENEMIGO = 260  # píxeles
COOLDOWN_DISPARO_ENEMIGO = 1.2  # segundos entre disparos
# Marco amarillo sobre el enemigo al que apunta el jugador
COLOR_OBJETIVO = COLOR_AMARILLO
MARGEN_OBJETIVO = 6
LARGO_ESQUINA_OBJETIVO = 9
GROSOR_OBJETIVO = 2
TOLERANCIA_OBJETIVO = 28  # px de distancia a la línea de apuntado
COLOR_LINEA_OBJETIVO = (255, 56, 120, 150)  # línea discontinua jugador -> objetivo
# Números de daño flotantes ("-1")
COLOR_TEXTO_DANIO = COLOR_AMARILLO
DURACION_TEXTO_DANIO = 0.7  # segundos
VELOCIDAD_TEXTO_DANIO = 40  # px/s hacia arriba
# Globo con el nodo activo del behavior tree (tecla Tab)
COLOR_FONDO_GLOBO = (18, 16, 40)
COLOR_BORDE_GLOBO = COLOR_TEAL
DESPLAZAMIENTO_GLOBO = (64, -84)  # desde el centro del enemigo (hacia un lado y arriba)

# ----------------------------------------------------------------------
# Texto en pantalla (compatibilidad)
# ----------------------------------------------------------------------
COLOR_TEXTO_TERMINAL = COLOR_TEXTO_HUD

# Habilidad del Ciudadano: Burbuja Comunitaria
COLOR_BURBUJA = COLOR_TEAL
GROSOR_BURBUJA = 2
RADIO_BURBUJA = 70  # píxeles
DURACION_BURBUJA = 4.0  # segundos

# ----------------------------------------------------------------------
# Terminal del minijuego de decisión (pantalla completa)
# ----------------------------------------------------------------------
COLOR_FONDO_TERMINAL = COLOR_FONDO
COLOR_BORDE_TERMINAL = COLOR_BORDE_PANEL
COLOR_OPCION_SELECCIONADA = COLOR_TEAL
COLOR_TIEMPO_TERMINAL = COLOR_AMARILLO
ANCHO_TERMINAL = 1280
ALTO_TERMINAL = 720
GROSOR_BORDE_TERMINAL = 2
MARGEN_TERMINAL = 40
SEPARACION_LINEAS_TERMINAL = 50
RECT_TARJETA_PUBLICACION = (40, 142, 340, 440)
COLOR_FONDO_TARJETA = (240, 236, 224)
COLOR_TEXTO_TARJETA = (34, 30, 48)
COLOR_TEXTO_TARJETA_SUAVE = (110, 106, 128)
COLOR_IMAGEN_TARJETA = (40, 34, 84)
RECT_PANEL_ARBOL = (410, 142, 830, 440)
POSICION_TIEMPO_TERMINAL = (1240, 70)  # midright del número grande
RECT_BARRA_TIEMPO = (880, 100, 360, 14)
ANCHO_NODO_ARBOL = 150
ALTO_NODO_ARBOL = 46
ANCHO_NODO_HOJA = 220
COLOR_NODO_RECORRIDO = (24, 72, 66)
COLOR_BORDE_RECORRIDO = COLOR_TEAL
COLOR_NODO_ELEGIBLE = COLOR_TEAL
COLOR_TEXTO_ELEGIBLE = (12, 40, 36)
COLOR_NODO_CERRADO = COLOR_FONDO_PANEL_CLARO
COLOR_BORDE_CERRADO = (84, 78, 140)
COLOR_RAMA = (70, 64, 120)
COLOR_RAMA_RECORRIDA = COLOR_TEAL
GROSOR_RAMA = 2
GROSOR_RAMA_RECORRIDA = 3
POSICION_CAMINO_TERMINAL = (40, 616)  # "Camino" (migas de pan), sobre la barra de controles

# ----------------------------------------------------------------------
# Pantalla de resultado (tras la terminal): dos variantes de color
# ----------------------------------------------------------------------
COLOR_FONDO_EXITO = (10, 42, 46)
COLOR_FONDO_FALLO = (46, 12, 30)
RECT_ILUSTRACION_RESULTADO = (480, 226, 320, 180)
COLOR_MARCO_ILUSTRACION = (34, 30, 72)
RECT_BARRA_RESULTADO = (400, 468, 480, 22)
RECT_BOTON_RESULTADO = (480, 596, 320, 50)

# ----------------------------------------------------------------------
# Selección de personaje: 4 tarjetas (una por rol) con barras de stats
# ----------------------------------------------------------------------
POSICION_TITULO_SELECCION = (640, 70)  # centro
ORIGEN_COLUMNAS_SELECCION = (90, 150)  # esquina superior izq. de la 1ra tarjeta
ANCHO_COLUMNA_SELECCION = 280  # paso entre tarjetas
ANCHO_TARJETA_SELECCION = 250
ALTO_TARJETA_SELECCION = 400
SEPARACION_FILAS_SELECCION = 34
DESPLAZAMIENTO_BARRA_X = 100  # de la etiqueta de la stat al inicio de su barra
ANCHO_MAXIMO_BARRA = 110  # ancho de la barra del rol con el valor máximo
ALTO_BARRA = 10
# Cursores de cada jugador sobre las tarjetas (chip "J1"/"J2" del color del
# rol, arriba a la derecha)
GROSOR_TARJETA_RESALTADA = 4
ALFA_TARJETA_CONFIRMADA = 36  # tinte del color del rol sobre la tarjeta elegida
POSICION_ESTADO_SELECCION = (640, 590)  # centro de "J1: ... · J2: ..."

# ----------------------------------------------------------------------
# Pantalla de modo: 1 o 2 jugadores (antes de elegir personaje)
# ----------------------------------------------------------------------
RECTS_OPCION_MODO = (
    (130, 170, 320, 340),
    (480, 170, 320, 340),
    (830, 170, 320, 340),
)  # x, y, ancho, alto para 1 jugador, 2 jugadores y Online
POSICION_AVISO_MODO = (640, 570)  # centro del estado del control / aviso
DURACION_AVISO_MODO = 2.5  # s que se muestra "Conecta un control..."

# Influencer: cono de sonido (proyectil ancho que empuja) / Live Stream Viral
COLOR_PROYECTIL_INFLUENCER = (255, 150, 230)
TAMANIO_PROYECTIL_INFLUENCER = 26
VELOCIDAD_PROYECTIL_INFLUENCER = 300  # píxeles por segundo
IMPULSO_EMPUJE_INFLUENCER = 30  # píxeles que retrocede el enemigo golpeado
DURACION_LIVE_STREAM = 3.0  # segundos de aggro forzado

# Periodista: rayo perforante / Fact-Checking
COLOR_RAYO_PERIODISTA = (140, 220, 255)
COLOR_RAYO_FACT_CHECK = (90, 255, 140)
TAMANIO_RAYO = 10
VELOCIDAD_RAYO = 900  # píxeles por segundo
LARGO_ESTELA_RAYO = 40  # píxeles de la línea dibujada detrás del rayo
GROSOR_ESTELA_RAYO = 4

# Candidato: onda expansiva radial / Debate Rebotante
COLOR_ONDA_CANDIDATO = COLOR_AMARILLO
GROSOR_ONDA = 3
RADIO_MAXIMO_ONDA = 90  # píxeles
DURACION_ONDA = 0.3  # segundos que tarda en expandirse
COLOR_PROYECTIL_REBOTANTE = (255, 140, 60)
ANGULOS_DEBATE_REBOTANTE = (-20, 0, 20)  # grados respecto a la mirada
MAXIMO_REBOTES = 3
TIEMPO_VIDA_REBOTANTE = 4.0  # segundos

# ----------------------------------------------------------------------
# Cuarto: piso, muros, puertas, grafitis y terminal
# ----------------------------------------------------------------------
ANCHO_CUARTO = 1000
ALTO_CUARTO = 560
CENTRO_CUARTO = (640, 360)
TAMANIO_BALDOSA = 40
COLOR_BALDOSA_A = (30, 27, 62)
COLOR_BALDOSA_B = (36, 33, 72)
COLOR_MURO = (52, 44, 98)
COLOR_MURO_LINEA = (78, 66, 134)  # juntas de los ladrillos
COLOR_MURO_BORDE = (104, 90, 170)
GROSOR_MURO = 18
ALTO_LADRILLO = 9
ANCHO_LADRILLO = 28
ANCHO_PUERTA = 80
GROSOR_PUERTA = 18
COLOR_PUERTA_BLOQUEADA = COLOR_MAGENTA
COLOR_PUERTA_ABIERTA = COLOR_TEAL
COLOR_PUERTA_SELLADA = (170, 130, 30)  # dorado oscuro: no es por enemigos
COLOR_X_PUERTA_SELLADA = (50, 35, 10)
GROSOR_X_PUERTA_SELLADA = 3
# Grafitis: texto girado y manchas, con transparencia, sobre el piso
COLOR_GRAFITI = (255, 56, 120, 70)
COLOR_MANCHA = (255, 56, 120, 34)
TAMANIO_FUENTE_GRAFITI = 40
TEXTOS_GRAFITI = ("SIN FUENTE", "COMPARTE YA", "URGENTE!!", "FAKE", "RT x1000", "#VIRAL")
# Terminal física del cuarto final (sprite + aviso de bloqueo)
MARGEN_TERMINAL_CUARTO = 24  # px entre el muro derecho y la terminal
COLOR_FONDO_TERMINAL_CUARTO = (18, 16, 40)
TEXTO_TERMINAL_BLOQUEADA = "Terminal bloqueada"
TEXTO_TERMINAL_LISTA = "Terminal lista"

# Mazmorra multi-cuarto: al cruzar una puerta el jugador aparece a esta
# distancia (px) de la puerta opuesta, hacia dentro del cuarto nuevo.
DISTANCIA_APARICION_PUERTA = 56
DURACION_MENSAJE_MAZMORRA = 2.0  # s de "Cuarto final desbloqueado" / "Limpia todos..."
COLOR_MENSAJE_MAZMORRA = COLOR_AMARILLO
POSICION_MENSAJE_MAZMORRA = (640, 112)  # centro: bajo el muro superior del cuarto
POSICION_TEXTO_CUARTOS_LIMPIOS = (10, 70)

# ----------------------------------------------------------------------
# Mazmorra final: arena, jefe, charcos y "juice"
# ----------------------------------------------------------------------
ANCHO_ARENA = 1000
ALTO_ARENA = 540
CENTRO_ARENA = (640, 370)  # deja libre la franja superior para el HUD
TAMANIO_JEFE = 128  # hitbox del Flame Golem (el sprite mide 160x140)
COLOR_JEFE = COLOR_MORADO
COLOR_DESTELLO_JEFE = (255, 255, 255)
COLOR_ESCUDO_JEFE = (90, 230, 255)
GROSOR_ESCUDO_JEFE = 3
MARGEN_ESCUDO_JEFE = 10
PERIODO_PARPADEO_JEFE = 0.1  # s entre visible/invisible durante el cambio de fase
COLOR_PROYECTIL_JEFE = COLOR_MAGENTA
TAMANIO_PROYECTIL_JEFE = 12
ALFAS_ESTELA_JEFE = (150, 90, 40)  # de la posición más reciente a la más vieja
COLOR_CHARCO = (120, 230, 80)
ALFA_CHARCO_ACTIVO = 90
GROSOR_CONTORNO_CHARCO = 2
SHAKE_DURACION = 0.25
SHAKE_INTENSIDAD = 5  # px máximos de desplazamiento

# Barra de vida del jefe y textos de la mazmorra final (en el HUD)
RECT_BARRA_JEFE = (440, 40, 400, 12)  # x, y, ancho, alto
COLOR_BARRA_JEFE = COLOR_MAGENTA
COLOR_FONDO_BARRA_JEFE = COLOR_FONDO_BARRA
COLOR_MARCA_FASE = COLOR_TEXTO_HUD
ANCHO_MARCA_FASE = 2
POSICION_TEXTO_FASE = (440, 14)
POSICION_TEXTO_TIEMPO_JEFE = (840, 14)  # topright
POSICION_MENSAJE_CENTRAL = (640, 112)  # centro del texto de derrota
COLOR_MENSAJE_VICTORIA = COLOR_TEAL
COLOR_MENSAJE_DERROTA = COLOR_MAGENTA
DURACION_MENSAJE = 2.5  # s que se muestra la derrota contra el jefe
ESPACIADO_ESTELA_JEFE = 9  # px entre posiciones guardadas de la estela
SEPARACION_INVOCACION = 70  # px a cada lado del jefe donde aparecen súbditos

# Invulnerabilidad del jugador tras un golpe
PERIODO_PARPADEO_INVULNERABLE = 0.08  # s entre visible/invisible

# ----------------------------------------------------------------------
# Pantallas de victoria (jefe) y derrota global
# ----------------------------------------------------------------------
COLOR_VELO_VICTORIA = (8, 20, 24, 200)  # RGBA: oscurece la arena detrás del panel
RECT_PANEL_VICTORIA = (340, 220, 600, 260)  # x, y, ancho, alto
COLOR_FONDO_PANEL_VICTORIA = COLOR_FONDO_PANEL
COLOR_BORDE_PANEL_VICTORIA = COLOR_TEAL
GROSOR_BORDE_PANEL_VICTORIA = 2
SEPARACION_LINEAS_VICTORIA = 44
COLOR_VELO_COLAPSO = (40, 6, 20, 210)
RECT_PANEL_COLAPSO = (340, 220, 600, 260)
COLOR_FONDO_PANEL_COLAPSO = (40, 18, 34)
COLOR_BORDE_PANEL_COLAPSO = COLOR_MAGENTA
GROSOR_BORDE_PANEL_COLAPSO = 2

# ----------------------------------------------------------------------
# Minimapa de la mazmorra (tecla M): panel en la esquina superior
# derecha del cuarto.
# ----------------------------------------------------------------------
ORIGEN_MINIMAPA = (1020, 98)  # esquina superior izquierda de la celda (0, 0)
TAMANIO_CELDA_MINIMAPA = 26
PASO_CELDA_MINIMAPA = 38  # distancia entre celdas vecinas (celda + pasillo)
COLOR_FONDO_MINIMAPA = (18, 16, 40)
MARGEN_FONDO_MINIMAPA = 10
COLOR_PASILLO_MINIMAPA = (80, 74, 130)
GROSOR_PASILLO_MINIMAPA = 3
COLOR_RUTA_MINIMAPA = COLOR_AMARILLO
GROSOR_RUTA_MINIMAPA = 4
GROSOR_BORDE_RUTA_MINIMAPA = 2  # contorno de los cuartos que están en la ruta
COLOR_TOXICIDAD_BAJA = (62, 230, 196)  # teal: toxicidad 0
COLOR_TOXICIDAD_ALTA = (255, 56, 120)  # magenta: toxicidad 100
FACTOR_OSCURO_NO_VISITADO = 0.35  # brillo de un cuarto aún no visitado
COLOR_CUARTO_ACTUAL = (255, 255, 255)
GROSOR_CUARTO_ACTUAL = 2
COLOR_MARCA_FINAL = (20, 20, 24)
COLOR_CANDADO = COLOR_AMARILLO
COLOR_FINAL_DESBLOQUEADO = (255, 255, 255)
TAMANIO_CANDADO = 12  # ancho del cuerpo del candado en px
GROSOR_CANDADO = 2

# ----------------------------------------------------------------------
# Mapa del mundo (tecla M en la escena CIUDAD): el grafo de calles en
# abstracto. Cada nodo se dibuja en ORIGEN + casilla * ESCALA, así el
# dibujo conserva la forma de la ciudad y el jugador cae en su lugar.
# ----------------------------------------------------------------------
ORIGEN_MAPA_MUNDO = (32, 56)  # px de pantalla de la casilla (0, 0)
ESCALA_MAPA_MUNDO = (19, 13)  # px de pantalla por casilla, en x y en y
# Dónde va el nombre de cada zona respecto a su círculo: (ancla del
# panel, dx, dy) desde el centro. Fuera del anillo de calles para que
# las líneas no lo crucen.
ETIQUETAS_MAPA_MUNDO = {
    "Plaza": ("topleft", 22, 18),
    "Colegio": ("midbottom", 0, -32),
    "Alcaldía": ("midbottom", 0, -32),
    "Hospital": ("midtop", 0, 32),
    "Empresa de Medios": ("midtop", 0, 32),
}
MARGEN_FONDO_ETIQUETA = 4  # px de fondo alrededor de cada texto del mapa
RADIO_ZONA_MAPA = 22
RADIO_CRUCE_MAPA = 7
COLOR_ZONA_MAPA = (66, 60, 120)
COLOR_ZONA_ALCALDIA = COLOR_MORADO
COLOR_ZONA_ACTUAL = COLOR_TEAL
COLOR_ZONA_SELECCIONADA = COLOR_AMARILLO
GROSOR_ZONA_SELECCIONADA = 3
COLOR_CALLE = (70, 64, 120)
GROSOR_CALLE = 3
COLOR_CALLE_BLOQUEADA = COLOR_MAGENTA
COLOR_RUTA_SEGURA = COLOR_AMARILLO
GROSOR_RUTA_SEGURA = 6
RADIO_ETIQUETA_PESO = 13
GROSOR_BORDE_ETIQUETA_PESO = 2
COLOR_FONDO_ETIQUETA_PESO = COLOR_FONDO_PANEL
RECT_PANEL_RUTA = (40, 590, 760, 62)
POSICION_TEXTO_RUTA = (56, 598)
ESCALA_JUGADOR_MAPA_MUNDO = 2  # el jugador en el mapa del mundo, más chico
TITULO_MAPA_MUNDO = "Mapa del mundo"
POSICION_MENSAJE_MAPA = (640, 162)  # centro del mensaje del último resultado (bajo el chip de la ruta)
DURACION_MENSAJE_MAPA = 4.0  # s que se muestra el resultado al volver a la ciudad

# ----------------------------------------------------------------------
# Ciudad Nova (escena CIUDAD): casillas en pixel art, edificios, auras,
# barricadas, ruta sugerida y cintillo de noticias.
# ----------------------------------------------------------------------
ALTO_CINTILLO = 28
# Zona de pantalla donde se ve el mundo: entre el cintillo y la barra de controles.
RECT_VISTA_CIUDAD = (0, ALTO_HUD + 2 + ALTO_CINTILLO, 1280,
                     720 - ALTO_HUD - 2 - ALTO_CINTILLO - ALTO_BARRA_CONTROLES)
RECT_CINTILLO = (0, ALTO_HUD + 2, 1280, ALTO_CINTILLO)
TITULO_CIUDAD = "Ciudad Nova"

# Casillas (paleta nocturna, misma familia que el piso de los cuartos)
COLOR_PASTO = (20, 38, 48)
COLOR_PASTO_BROTE = (30, 60, 64)
COLOR_PASTO_SOMBRA = (15, 28, 40)
COLOR_ACERA = (38, 35, 70)
COLOR_ACERA_JUNTA = (28, 26, 54)
COLOR_ACERA_BRILLO = (48, 45, 86)
COLOR_PLAZA = (46, 40, 84)
COLOR_PLAZA_ROMBO = (56, 50, 102)
COLOR_PLAZA_JUNTA = (34, 31, 64)
# Mosaico circular en el centro de la Plaza: anillos (radio en casillas, color)
ANILLOS_MOSAICO_PLAZA = ((3.2, (40, 70, 92)), (2.6, (30, 28, 58)), (2.2, (70, 56, 128)), (1.3, (30, 28, 58)),
                         (0.9, (62, 230, 196)), (0.6, (30, 28, 58)))
COLOR_ASFALTO = (24, 22, 40)
COLOR_ASFALTO_GRANO = (31, 29, 52)
COLOR_CARRIL = (150, 116, 50)  # amarillo apagado: la marca del carril no compite con el neón
COLOR_COPA = (22, 82, 76)
COLOR_COPA_BRILLO = (40, 124, 108)
COLOR_COPA_SOMBRA = (14, 52, 54)
COLOR_COPA_BORDE = (10, 34, 40)
COLOR_TRONCO = (64, 42, 54)
COLOR_SOMBRA_SUELO = (12, 24, 34)
COLOR_POSTE = (84, 80, 130)
COLOR_POSTE_OSCURO = (52, 48, 90)
COLOR_LAMPARA = (255, 226, 150)
COLOR_HALO_FAROLA = (255, 190, 90, 64)  # RGBA del halo de luz
RADIO_HALO_FAROLA = 78
DESPLAZAMIENTO_HALO_FAROLA = (0, -14)  # el halo se centra en la lámpara, no en la casilla
COLOR_MURO_CASA = (42, 38, 80)
COLOR_MURO_CASA_JUNTA = (34, 30, 66)
COLOR_TECHO_CASA = (56, 46, 96)
COLOR_TECHO_CASA_BRILLO = (78, 66, 132)
COLOR_TECHO_CASA_LINEA = (44, 36, 78)
COLOR_ALERO = (20, 18, 40)
COLOR_MARCO_VENTANA = (16, 14, 30)
COLOR_VENTANA_ENCENDIDA = (255, 204, 110)
COLOR_VENTANA_APAGADA = (30, 28, 56)
COLOR_VENTANA_NEON = (120, 220, 255)

# Edificios de zona: muro común y un color de neón por zona (rótulo,
# ventanas de acento y emblema). La Alcaldía usa su morado de siempre.
COLOR_MURO_EDIFICIO = COLOR_ZONA_MAPA
COLOR_MURO_EDIFICIO_LINEA = (54, 48, 100)
COLOR_BASE_EDIFICIO = (34, 30, 64)
COLOR_COLUMNA = (150, 144, 200)
COLORES_NEON_ZONA = {
    "Colegio": COLOR_TEAL,
    "Hospital": COLOR_MAGENTA,
    "Empresa de Medios": COLOR_AMARILLO,
    "Alcaldía": COLOR_ZONA_ALCALDIA,
}
FACTOR_PUERTA_OSCURA = 0.35  # brillo de la puerta respecto al neón de la zona
ANCHO_ROTULO_CASILLAS = 6  # ancho de la placa del rótulo, en casillas
TAMANIO_FUENTE_ROTULO = 15
ALFA_BRILLO_ROTULO = 70  # resplandor detrás de las letras del rótulo

# Aura neón sobre cada edificio: color de toxicidad (verde -> rojo),
# alfa que pulsa entre MIN y MAX con el periodo dado.
GROSOR_AURA = 5
MARGEN_AURA = 8
ALFA_AURA_MIN = 120
ALFA_AURA_MAX = 230
PERIODO_AURA = 1.6  # s
CAPAS_AURA = 3  # bordes concéntricos cada vez más tenues

# Barricada (franjas amarillo/negro sobre la calle)
COLOR_BARRICADA_A = COLOR_AMARILLO
COLOR_BARRICADA_B = (16, 14, 30)
COLOR_PATA_BARRICADA = (110, 104, 150)

# Ruta sugerida (tecla G): línea punteada sobre las calles
COLOR_RUTA_CIUDAD = COLOR_AMARILLO
GROSOR_RUTA_CIUDAD = 4
LARGO_TRAZO_RUTA = 14
HUECO_TRAZO_RUTA = 10
RADIO_DESTINO_RUTA = 10

# Avisos de la ciudad (chips sobre la parte baja de la vista)
POSICION_AVISO_ENTRADA = (640, 624)
POSICION_AVISO_RUTA = (1260, 112)  # topright del chip "Ruta: ..." / "Sin ruta"
COLOR_AVISO_ENTRADA = COLOR_TEAL
COLOR_AVISO_SELLADA = COLOR_MAGENTA
TEXTO_AVISO_ENTRADA = "E: entrar a {zona} (Toxicidad {nivel:.0f})"
TEXTO_ALCALDIA_SELLADA = "Alcaldía sellada: purifica una mazmorra"
TEXTO_SIN_RUTA = "Sin ruta"
TEXTO_RUTA_DESTINO = "Ruta a {destino}  ·  saturación {costo:g}"

# Cintillo "Breaking News Civitas"
ETIQUETA_CINTILLO = "BREAKING NEWS CIVITAS"
COLOR_FONDO_CINTILLO = COLOR_FONDO_PANEL
COLOR_ETIQUETA_CINTILLO = COLOR_MAGENTA
COLOR_TEXTO_CINTILLO = COLOR_TEXTO_HUD
VELOCIDAD_CINTILLO = 80  # px/s hacia la izquierda
SEPARADOR_CINTILLO = "   ·   "

# Fundido corto al entrar y salir de un edificio
DURACION_FUNDIDO = 0.35  # s
COLOR_FUNDIDO = COLOR_FONDO

# ----------------------------------------------------------------------
# Mira del apuntado con mouse (se dibuja sobre el HUD, sin sacudida)
# ----------------------------------------------------------------------
COLOR_MIRA = COLOR_TEAL
RADIO_MIRA = 9
GROSOR_MIRA = 2
LARGO_CRUZ_MIRA = 5  # px de cada brazo de la cruz que sale del círculo
COLOR_LINEA_APUNTADO = (62, 230, 196, 70)  # RGBA: línea tenue jugador -> mira
GROSOR_LINEA_APUNTADO = 1
# Opacidad del cono ajustable (pestaña CONTROLES): 100% = este alfa. El
# 40% predeterminado da el alfa 46 de COLOR_CONO_APUNTADO.
ALFA_MAXIMO_CONO = 115
ANGULO_CONO_VISTA_PREVIA = 14  # grados a cada lado en la vista previa de los ajustes

# ----------------------------------------------------------------------
# Pantalla de inicio: paleta retrofuturista (negro, azul noche, violeta
# neón y cian de acento)
# ----------------------------------------------------------------------
COLOR_CIAN_NEON = (80, 220, 255)
COLOR_MENU_SELECCION = (196, 120, 255)  # violeta neón: foco, títulos, bordes activos
COLOR_RESPLANDOR_MENU = (150, 70, 255)
COLOR_MENU_PULSADO = (150, 80, 240)
COLOR_TEXTO_PULSADO = (20, 8, 40)
COLOR_TEXTO_DESHABILITADO = (88, 84, 120)
COLOR_FONDO_MENU = (8, 6, 24, 205)  # RGBA: panel detrás de las opciones
COLOR_BORDE_MENU = (84, 60, 140)
COLOR_ENGRANAJE = (176, 170, 214)
TAMANIO_FUENTE_MENU = 24

# Título CIVITAS (src/ui/titulo_civitas.py)
CENTRO_Y_TITULO = 0.2  # fracción del alto de la pantalla
ESCALA_TITULO = 13  # px por píxel de letra (5x7)
COLOR_TITULO = (176, 96, 255)
COLOR_TITULO_LUZ = (226, 184, 255)
COLOR_TITULO_SOMBRA = (52, 20, 96)
COLOR_RESPLANDOR_TITULO = (140, 50, 255)
RADIO_RESPLANDOR_TITULO = 14
COLOR_GLITCH_CIAN = (30, 190, 230)
COLOR_GLITCH_MAGENTA = (230, 40, 150)
COLOR_DESTELLO_TITULO = (60, 44, 84)
INTERVALO_GLITCH_TITULO = (2.5, 6.0)  # s entre glitches (al azar)
DURACION_GLITCH_TITULO = 0.22
SEPARACION_CROMATICA_TITULO = (3, 7)  # px
DESPLAZAMIENTO_FRANJA_TITULO = (6, 18)  # px
PASO_SCANLINES_TITULO = 4  # una fila oscura cada 4 px
BRILLO_SCANLINES_TITULO = 175  # 0-255: brillo que conserva la fila oscura

# Opciones del menú (src/ui/menu_principal_render.py)
INICIO_OPCIONES_MENU = 0.39  # y de la primera opción, fracción del alto
PASO_OPCIONES_MENU = 50
ANCHO_OPCION_MENU = 360
ALTO_OPCION_MENU = 42
DURACION_PULSADO_MENU = 0.14  # s que se ve la opción pulsada antes de actuar
DURACION_REALCE_MENU = 0.12  # s de la animación de entrada al seleccionar
DESLIZAMIENTO_OPCION_MENU = 14  # px desde los que entra la opción seleccionada
PULSO_OPCION_MENU = 4.0  # rad/s del pulso de brillo de la opción seleccionada
RADIO_RESPLANDOR_MENU = 6
LADO_BOTON_ENGRANAJE = 52
MARGEN_BOTON_ENGRANAJE = 22
ESCALA_ENGRANAJE = 3
GIRO_ENGRANAJE = 90  # grados/s mientras tiene el foco
TAMANIO_PANEL_VISTA = (760, 360)  # EXTRAS / CRÉDITOS
CENTRO_Y_PANEL_VISTA = 0.6
COLUMNA_CREDITOS = 220  # x (desde el borde del panel) donde empiezan los valores

# Modal de ajustes (src/ui/ajustes_render.py)
TAMANIO_MODAL_AJUSTES = (900, 520)
CENTRO_Y_MODAL_AJUSTES = 0.47
DURACION_TRANSICION_MODAL = 0.18
DESPLAZAMIENTO_ENTRADA_MODAL = 24  # px desde los que sube el modal al abrirse
ALFA_VELO_MODAL = 153  # 60% de negro sobre el fondo
REDUCCION_DESENFOQUE_MODAL = 4  # el fondo se reduce a 1/4 y se vuelve a ampliar
COLOR_FONDO_MODAL = (12, 10, 30)
COLOR_FONDO_MODAL_ALFA = (12, 10, 30, 225)
COLOR_BORDE_MODAL_INTERIOR = (40, 90, 120)
COLOR_FILA_ENFOCADA = (34, 22, 66)
COLOR_PESTANA_ACTIVA = (60, 34, 112)
COLOR_FONDO_VISTA_PREVIA = (18, 16, 40)
ANCHO_BOTON_CERRAR = 130
ANCHO_PESTANA = 190
ALTO_FILA_AJUSTES = 56
ANCHO_ETIQUETA_AJUSTES = 300
ANCHO_ETIQUETA_COLUMNA = 196  # filas de la columna derecha (cono, en la vista MANDO)
ANCHO_ZONA_MANDO = 450
SEGMENTOS_SLIDER = 20
COLOR_SEGMENTO_ACTIVO = (164, 90, 255)
COLOR_SEGMENTO_LUZ = (214, 170, 255)
COLOR_SEGMENTO_INACTIVO = (36, 30, 66)
COLOR_CUERPO_MANDO = (34, 30, 64)
COLOR_BORDE_MANDO = (110, 80, 180)
COLOR_LINEA_GUIA_MANDO = (70, 110, 150)
COLORES_BOTONES_PS = {"✕": (120, 170, 255), "○": (255, 90, 110), "□": (230, 130, 220), "△": (80, 220, 170)}

# Ciudad animada del fondo (src/ui/fondo_ciudad.py). Velocidades en px/s
# de pantalla; tamaños de edificios en píxeles de la baja resolución.
SEMILLA_FONDO_CIUDAD = 2026  # misma ciudad en cada arranque
ESCALA_PIXEL_FONDO = 3
COLOR_CIELO_ARRIBA = (6, 5, 22)
COLOR_CIELO_HORIZONTE = (46, 18, 82)
COLOR_NUBE = (14, 12, 40)
COLOR_BORDE_NUBE = (32, 26, 76)
CANTIDAD_NUBES = 9
COLOR_ESTRELLA = (120, 120, 190)
CANTIDAD_ESTRELLAS = 24
COLOR_BRUMA = (255, 60, 170)
ALFA_BRUMA = 70
INICIO_BRUMA = 0.45  # la bruma empieza a esta fracción del alto
COLOR_LUZ_ANTENA = (255, 50, 70)
CAPAS_FONDO_CIUDAD = (
    {   # lejana: siluetas azules con pocas ventanas
        "velocidad": 5, "ancho": (10, 26), "alto": (90, 175), "hueco": (0, 3),
        "cuerpo": (22, 24, 64), "borde": (40, 46, 100), "cornisa": None,
        "ventanas": ((44, 52, 120), (64, 44, 116)), "paso_ventana": 3, "densidad_ventanas": 0.18,
        "prob_antena": 0.25, "prob_letrero": 0.0,
    },
    {   # media: torres azul eléctrico con cornisa cian
        "velocidad": 12, "ancho": (14, 34), "alto": (70, 150), "hueco": (1, 6),
        "cuerpo": (30, 38, 110), "borde": (70, 120, 220), "cornisa": (90, 220, 255),
        "ventanas": ((90, 140, 255), (150, 190, 255), (255, 80, 170)), "paso_ventana": 3,
        "densidad_ventanas": 0.3, "prob_antena": 0.35, "prob_letrero": 0.15,
    },
    {   # cercana: edificios oscuros con borde magenta y letreros holográficos
        "velocidad": 26, "ancho": (24, 48), "alto": (45, 120), "hueco": (2, 10),
        "cuerpo": (16, 14, 48), "borde": (130, 44, 170), "cornisa": (200, 70, 200),
        "ventanas": ((255, 90, 180), (255, 140, 90), (120, 90, 220)), "paso_ventana": 4,
        "densidad_ventanas": 0.16, "prob_antena": 0.2, "prob_letrero": 0.6,
    },
    {   # primer plano: azoteas casi negras
        "velocidad": 48, "ancho": (30, 80), "alto": (10, 30), "hueco": (0, 14),
        "cuerpo": (9, 7, 24), "borde": (70, 30, 100), "cornisa": (110, 40, 140),
        "ventanas": ((60, 30, 90),), "paso_ventana": 6, "densidad_ventanas": 0.05,
        "prob_antena": 0.3, "prob_letrero": 0.0,
    },
)
# Letreros holográficos: textos del universo del juego.
TEXTOS_LETREROS = ("VERIFICA", "#VIRAL", "FAKE?", "REPORTA", "TRENDING", "FUENTE?", "LIKE x1000",
                   "NOTICIAS 24H", "CIVITAS", "VOTA")
COLORES_LETREROS = ((255, 56, 120), (255, 80, 80), (62, 230, 240), (200, 110, 255))
COLOR_FONDO_LETRERO = (24, 10, 34)
COLOR_LETRERO_APAGADO = (10, 6, 20, 170)  # RGBA encima del letrero que parpadea
TAMANIO_FUENTE_LETRERO = 13
PROB_LETRERO_VERTICAL = 0.35
LETRAS_MAXIMAS_LETRERO_VERTICAL = 6  # textos más largos van siempre en horizontal
INTERVALO_PARPADEO_LETRERO = (0.8, 2.5)  # s entre parpadeos
DURACION_PARPADEO_LETRERO = 0.14
# Naves: una por profundidad; "capa" = se dibuja justo encima de esa capa.
PROFUNDIDADES_NAVES = (
    {"capa": 0, "escala": 2, "velocidad": (35, 55), "altura": (0.12, 0.35), "largo_estela": 24},
    {"capa": 0, "escala": 2, "velocidad": (40, 60), "altura": (0.1, 0.3), "largo_estela": 24},
    {"capa": 1, "escala": 3, "velocidad": (70, 100), "altura": (0.15, 0.45), "largo_estela": 40},
    {"capa": 2, "escala": 4, "velocidad": (130, 180), "altura": (0.2, 0.5), "largo_estela": 70},
)
ESPERA_MAXIMA_NAVE = 6.0  # s de pausa máxima antes de volver a cruzar
COLOR_ESTELA_NAVE = COLOR_CIAN_NEON
ALFA_ESTELA_NAVE = 170
# Lluvia
CANTIDAD_GOTAS_LLUVIA = 120
VELOCIDAD_LLUVIA = (520, 760)
LARGO_GOTA_LLUVIA = (8, 16)
INCLINACION_LLUVIA = 0.18  # px en x por px en y
COLORES_LLUVIA = ((70, 80, 170), (100, 90, 200), (60, 120, 200))

# ----------------------------------------------------------------------
# Sonidos (src/core/audio.py). Si existe el archivo se usa; si no, el
# efecto se genera en código con estos tonos (Hz) y duración (s).
# ----------------------------------------------------------------------
RUTAS_SONIDOS = {
    "navegar": os.path.join("assets", "sonidos", "navegar.wav"),
    "confirmar": os.path.join("assets", "sonidos", "confirmar.wav"),
    "volver": os.path.join("assets", "sonidos", "volver.wav"),
}
TONOS_SONIDOS = {
    "navegar": ((880,), 0.04),
    "confirmar": ((660, 990), 0.12),
    "volver": ((520, 390), 0.1),
}
AMPLITUD_SONIDO_SINTETIZADO = 0.18  # fracción del máximo de 16 bits
RUTA_MUSICA_MENU = os.path.join("assets", "musica", "menu.ogg")

# ----------------------------------------------------------------------
# Hojas de sprites (arte real, pixel art hecho con Pixelbolt). Cada hoja
# es <carpeta>/<id>.png (tira horizontal a resolución nativa) con su
# <id>.atlas.json al lado (rect y duración de cada cuadro, animaciones).
# Si falta el PNG se usa el pixel art dibujado en código (sprites.py).
# Las recetas editables viven en assets/sprites/fuentes/<id>.pixel.json.
# ----------------------------------------------------------------------
RUTA_SPRITES_JUGADORES = os.path.join("assets", "sprites", "jugadores")  # <rol>.png, 16x20
RUTA_SPRITES_JEFE = os.path.join("assets", "sprites", "jefe")
ID_SPRITE_JEFE = "servidor_central"  # 24x24
RUTA_SPRITES_RETRATOS = os.path.join("assets", "sprites", "retratos")  # <rol>.png (ilustración grande)
ANIMACION_CAMINAR = "caminar"  # jugadores y enemigos
ANIMACION_DASH = "dash"  # jugadores (un solo cuadro)
ANIMACION_JEFE_IDLE = "idle"
ANIMACION_JEFE_FURIA = "furia"  # fase 3
ESCALA_SPRITE_JEFE = 4  # hoja anterior: 24 px * 4 = 96 px
# Jefe final con arte "enemigos 2.0": Flame Golem (32x28 nativo). Si es None
# o falta el PNG se usa la hoja anterior del Servidor Central.
JEFE_V2 = "Flame Golem"
ESCALA_JEFE_V2 = 5  # 160x140 px
DURACION_CUADRO_JEFE_V2 = 0.12
DURACION_CUADRO_JEFE_V2_FURIA = 0.06  # en fase 3 camina el doble de rápido
ALTO_RETRATO_SELECCION = 92  # alto del retrato en la tarjeta de selección
# Cuarto: piso y muro (cuarto.png, 16x16 por cuadro), puertas (puerta.png,
# 27x6: abierta / bloqueada / sellada) y charco tóxico (charco.png, 30x30:
# aviso / activo). Sin el PNG se dibujan con formas, como antes.
RUTA_SPRITES_CUARTO = os.path.join("assets", "sprites", "cuarto")
ID_SPRITE_CUARTO = "cuarto"
ID_SPRITE_PUERTA = "puerta"
ID_SPRITE_CHARCO = "charco"
CUADROS_PISO = ("piso_a", "piso_b")  # tablero: (fila + columna) par / impar
CUADROS_PISO_DETALLE = ("piso_grieta", "piso_rejilla")  # reemplazan a una baldosa de vez en cuando
PROBABILIDAD_PISO_DETALLE = 0.06
CUADRO_MURO = "muro"
TAMANIO_BALDOSA_HOJA = 16 * ESCALA_PIXEL  # 48 px por baldosa cuando hay hoja
CUADRO_PUERTA = {"abierta": "abierta", "bloqueada": "bloqueada", "sellada": "sellada"}
ANIMACION_CHARCO_AVISO = "aviso"
ANIMACION_CHARCO_ACTIVO = "activo"
ALFA_CHARCO_SPRITE = 215  # el charco dibujado deja ver un poco el piso

# ----------------------------------------------------------------------
# Tipos de enemigo: todo lo visual de cada tipo, en un solo lugar. Las
# claves son los valores de TipoEnemigo (src/entities/tipos_enemigo.py).
# Para usar arte real basta con dejar <ID_SPRITE_ENEMIGO[tipo]>.png en
# RUTA_SPRITES_ENEMIGOS (ver sprites.sprite_enemigo).
# ----------------------------------------------------------------------
RUTA_SPRITES_ENEMIGOS = os.path.join("assets", "sprites", "enemigos")
ID_SPRITE_ENEMIGO = {
    "perseguidor": "perseguidor",
    "tirador": "tirador",
    "curandero": "curandero",
}
# Arte "enemigos 2.0" (prueba): tiras <nombre>_Walk.png de cuadros de 100x100
# con el personaje mirando a la derecha. Solo los tipos listados lo usan;
# los demás siguen con su hoja anterior. Vaciar el dict desactiva la prueba.
RUTA_SPRITES_ENEMIGOS_V2 = os.path.join("assets", "sprites", "enemigos 2.0", "Characters(100x100 split)")
CUADRO_ENEMIGO_V2 = 100  # lado de cada cuadro de la tira
DURACION_CUADRO_ENEMIGO_V2 = 0.1  # s por cuadro de la animación
# Escala por tipo (px nativos * escala): el Hellhound queda pequeño y el
# Warlock se ve mucho más grande. Un tipo sin entrada usa ESCALA_ENEMIGO_V2_BASE.
ESCALA_ENEMIGO_V2_BASE = 2
ESCALA_ENEMIGO_V2 = {
    "perseguidor": 2,  # Hellhound 29x17 -> 58x34
    "tirador": 4,  # Warlock 21x26 -> 84x104
}
ENEMIGO_V2 = {
    "perseguidor": "Hellhound",
    "tirador": "Warlock",
}
COLOR_PRINCIPAL_ENEMIGO = {
    "perseguidor": (232, 52, 64),  # rojo: agresivo
    "tirador": (255, 120, 60),  # naranja
    "curandero": (70, 200, 120),  # verde
}
COLOR_SECUNDARIO_ENEMIGO = {
    "perseguidor": (120, 20, 40),
    "tirador": COLOR_MAGENTA,
    "curandero": (236, 246, 236),
}
TAMANIO_ENEMIGO_TIPO = {  # hitbox lógica (px de lado)
    "perseguidor": 38,
    "tirador": 56,  # Warlock grande (el sprite mide 84x104)
    "curandero": 36,
}
COLOR_PROYECTIL_TIRADOR = (255, 140, 70)
TAMANIO_PROYECTIL_TIRADOR = 10
COLOR_TELEGRAFIA_TIRADOR = (255, 230, 150)  # el tirador se ilumina antes de disparar
COLOR_RAYO_CURA = (90, 240, 140)
GROSOR_RAYO_CURA = 3
COLOR_PARTICULA_CURA = (140, 255, 170)
CANTIDAD_PARTICULAS_CURA = 6
TAMANIO_PARTICULA_CURA = 5
COLOR_PANICO_CURANDERO = COLOR_MAGENTA  # contorno del curandero en pánico

# Gracia al entrar al cuarto: anillo de cuenta regresiva sobre el
# jugador y enemigos que parpadean (alfa pulsante) mientras dura.
COLOR_ANILLO_GRACIA = COLOR_TEAL
COLOR_FONDO_ANILLO_GRACIA = (40, 60, 80)
RADIO_ANILLO_GRACIA = 30
GROSOR_ANILLO_GRACIA = 4
ALFA_MIN_ENEMIGO_GRACIA = 90
ALFA_MAX_ENEMIGO_GRACIA = 220
PERIODO_PARPADEO_GRACIA = 0.35  # s por pulso
