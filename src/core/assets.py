"""Constantes visuales centralizadas (colores y tamaños placeholder).

Todo elemento visual nuevo del juego debe referenciar sus colores,
tamaños y velocidades desde aquí en lugar de usar valores hardcodeados
dispersos en la lógica. La versión actual usa placeholders (rectángulos
de color); cuando se agregue arte real, el cambio se limita a
reemplazar los valores de este archivo por rutas de sprite, sin tocar
la lógica de juego.
"""

# Jugador (Ciudadano)
TAMANIO_JUGADOR = 36
COLOR_JUGADOR = (60, 140, 220)
VELOCIDAD_JUGADOR = 220  # píxeles por segundo
VIDA_JUGADOR = 5

# Proyectiles
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = (250, 240, 120)
COLOR_PROYECTIL_ENEMIGO = (230, 60, 60)
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
DANIO_PROYECTIL_JUGADOR = 1
DANIO_PROYECTIL_ENEMIGO = 1

# Enemigo
TAMANIO_ENEMIGO = 40
COLOR_ENEMIGO = (230, 160, 20)
VELOCIDAD_ENEMIGO = 90  # píxeles por segundo
VIDA_ENEMIGO = 3
RANGO_DISPARO_ENEMIGO = 260  # píxeles
COOLDOWN_DISPARO_ENEMIGO = 1.2  # segundos entre disparos

# Texto en pantalla (indicador de colapso)
COLOR_TEXTO_HUD = (235, 235, 235)
TAMANIO_FUENTE_HUD = 28
POSICION_TEXTO_COLAPSO = (10, 10)
POSICION_TEXTO_CARGA = (10, 40)
POSICION_TEXTO_RESULTADO = (10, 70)

# Habilidad del Ciudadano: Burbuja Comunitaria
COLOR_BURBUJA = (120, 220, 200)
GROSOR_BURBUJA = 2
RADIO_BURBUJA = 70  # píxeles
DURACION_BURBUJA = 4.0  # segundos

# Terminal del minijuego de decisión
COLOR_FONDO_TERMINAL = (20, 22, 28)
COLOR_BORDE_TERMINAL = (120, 200, 255)
COLOR_TEXTO_TERMINAL = (235, 235, 235)
COLOR_OPCION_SELECCIONADA = (255, 220, 80)
COLOR_TIEMPO_TERMINAL = (230, 90, 90)
ANCHO_TERMINAL = 600
ALTO_TERMINAL = 220
GROSOR_BORDE_TERMINAL = 3
MARGEN_TERMINAL = 20
SEPARACION_LINEAS_TERMINAL = 50
