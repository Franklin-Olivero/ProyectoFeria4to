"""Constantes visuales centralizadas (colores y tamaños placeholder).

Todo elemento visual nuevo del juego debe referenciar sus colores,
tamaños y velocidades desde aquí en lugar de usar valores hardcodeados
dispersos en la lógica. La versión actual usa placeholders (rectángulos
de color); cuando se agregue arte real, el cambio se limita a
reemplazar los valores de este archivo por rutas de sprite, sin tocar
la lógica de juego.
"""

COLOR_FONDO = (40, 44, 52)

# Jugador (comunes a los 4 roles). Velocidad, vida, daño, cadencia y
# carga de cada rol viven en src/core/balance.py.
TAMANIO_JUGADOR = 36
COLOR_CIUDADANO = (60, 140, 220)

# Proyectiles
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = (250, 240, 120)
COLOR_PROYECTIL_ENEMIGO = (230, 60, 60)
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
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

# Selección de personaje: 4 columnas (una por rol) con barras de stats
POSICION_TITULO_SELECCION = (20, 60)
ORIGEN_COLUMNAS_SELECCION = (20, 130)  # esquina superior izq. de la 1ra columna
ANCHO_COLUMNA_SELECCION = 195
TAMANIO_FUENTE_SELECCION = 22
SEPARACION_FILAS_SELECCION = 30
DESPLAZAMIENTO_BARRA_X = 80  # de la etiqueta de la stat al inicio de su barra
ANCHO_MAXIMO_BARRA = 100  # ancho de la barra del rol con el valor máximo
ALTO_BARRA = 12
COLOR_FONDO_BARRA = (70, 74, 84)
COLOR_TEXTO_SECUNDARIO = (170, 175, 185)

# Influencer: cono de sonido (proyectil ancho que empuja) / Live Stream Viral
COLOR_INFLUENCER = (220, 80, 200)
COLOR_PROYECTIL_INFLUENCER = (250, 150, 240)
TAMANIO_PROYECTIL_INFLUENCER = 26
VELOCIDAD_PROYECTIL_INFLUENCER = 300  # píxeles por segundo
IMPULSO_EMPUJE_INFLUENCER = 30  # píxeles que retrocede el enemigo golpeado
DURACION_LIVE_STREAM = 3.0  # segundos de aggro forzado

# Periodista: rayo perforante / Fact-Checking
COLOR_PERIODISTA = (240, 240, 240)
COLOR_RAYO_PERIODISTA = (140, 220, 255)
COLOR_RAYO_FACT_CHECK = (90, 255, 140)
TAMANIO_RAYO = 10
VELOCIDAD_RAYO = 900  # píxeles por segundo
LARGO_ESTELA_RAYO = 40  # píxeles de la línea dibujada detrás del rayo
GROSOR_ESTELA_RAYO = 4

# Candidato: onda expansiva radial / Debate Rebotante
COLOR_CANDIDATO = (240, 170, 60)
COLOR_ONDA_CANDIDATO = (255, 200, 90)
GROSOR_ONDA = 3
RADIO_MAXIMO_ONDA = 90  # píxeles
DURACION_ONDA = 0.3  # segundos que tarda en expandirse
COLOR_PROYECTIL_REBOTANTE = (255, 120, 40)
ANGULOS_DEBATE_REBOTANTE = (-20, 0, 20)  # grados respecto a la mirada
MAXIMO_REBOTES = 3
TIEMPO_VIDA_REBOTANTE = 4.0  # segundos

# Mazmorra final: arena, jefe, charcos y "juice"
ANCHO_ARENA = 760
ALTO_ARENA = 470
CENTRO_ARENA = (400, 355)  # deja libre la franja superior para la barra del jefe
TAMANIO_JEFE = 90
COLOR_JEFE = (150, 60, 200)
COLOR_DESTELLO_JEFE = (255, 255, 255)
COLOR_ESCUDO_JEFE = (90, 230, 255)
GROSOR_ESCUDO_JEFE = 4
MARGEN_ESCUDO_JEFE = 8
PERIODO_PARPADEO_JEFE = 0.1  # s entre visible/invisible durante el cambio de fase
COLOR_PROYECTIL_JEFE = (255, 90, 160)
TAMANIO_PROYECTIL_JEFE = 12
ALFAS_ESTELA_JEFE = (150, 90, 40)  # de la posición más reciente a la más vieja
COLOR_CHARCO = (110, 210, 60)
ALFA_CHARCO_ACTIVO = 110
GROSOR_CONTORNO_CHARCO = 2
SHAKE_DURACION = 0.25
SHAKE_INTENSIDAD = 5  # px máximos de desplazamiento

# Barra de vida del jefe y textos de la mazmorra final
RECT_BARRA_JEFE = (220, 14, 360, 16)  # x, y, ancho, alto
COLOR_BARRA_JEFE = (200, 50, 90)
COLOR_FONDO_BARRA_JEFE = (60, 60, 70)
COLOR_MARCA_FASE = (255, 255, 255)
ANCHO_MARCA_FASE = 2
POSICION_TEXTO_FASE = (220, 36)
POSICION_TEXTO_TIEMPO_JEFE = (620, 10)
POSICION_MENSAJE_CENTRAL = (400, 90)  # centro del texto de victoria/derrota
COLOR_MENSAJE_VICTORIA = (120, 255, 160)
COLOR_MENSAJE_DERROTA = (255, 110, 110)
DURACION_MENSAJE = 2.5  # s que se muestra la derrota contra el jefe
ESPACIADO_ESTELA_JEFE = 9  # px entre posiciones guardadas de la estela
SEPARACION_INVOCACION = 70  # px a cada lado del jefe donde aparecen súbditos

# Muros y puertas (cuarto normal y arena del jefe)
COLOR_MURO = (200, 200, 210)
GROSOR_MURO = 4
ANCHO_PUERTA = 80
GROSOR_PUERTA = 20
COLOR_PUERTA_BLOQUEADA = (200, 30, 30)
COLOR_PUERTA_ABIERTA = (30, 180, 60)

# Invulnerabilidad del jugador tras un golpe
PERIODO_PARPADEO_INVULNERABLE = 0.08  # s entre visible/invisible

# Pantalla de victoria del jefe final
COLOR_VELO_VICTORIA = (10, 12, 16, 170)  # RGBA: oscurece la arena detrás del panel
RECT_PANEL_VICTORIA = (150, 200, 500, 200)  # x, y, ancho, alto (bajo el HUD superior)
COLOR_FONDO_PANEL_VICTORIA = (24, 28, 36)
COLOR_BORDE_PANEL_VICTORIA = (120, 255, 160)
GROSOR_BORDE_PANEL_VICTORIA = 3
TAMANIO_FUENTE_TITULO_VICTORIA = 44
SEPARACION_LINEAS_VICTORIA = 44

# Pantalla de derrota global (Colapso Electoral al 100%)
COLOR_VELO_COLAPSO = (30, 6, 10, 190)  # RGBA: tiñe de rojo oscuro la escena detrás del panel
RECT_PANEL_COLAPSO = (150, 200, 500, 200)  # x, y, ancho, alto (mismo hueco que la victoria)
COLOR_FONDO_PANEL_COLAPSO = (36, 20, 24)
COLOR_BORDE_PANEL_COLAPSO = (255, 110, 110)
GROSOR_BORDE_PANEL_COLAPSO = 3

# Mazmorra multi-cuarto: al cruzar una puerta el jugador aparece a esta
# distancia (px) de la puerta opuesta, hacia dentro del cuarto nuevo
# (más que medio jugador + media puerta, para no volver a cruzarla).
DISTANCIA_APARICION_PUERTA = 50

# Minimapa de la mazmorra (tecla M), esquina superior derecha: no tapa
# el cuarto (x 150-650) ni el HUD de la izquierda.
ORIGEN_MINIMAPA = (668, 14)  # esquina superior izquierda de la celda (0, 0)
TAMANIO_CELDA_MINIMAPA = 30
PASO_CELDA_MINIMAPA = 44  # distancia entre celdas vecinas (celda + pasillo)
COLOR_FONDO_MINIMAPA = (24, 26, 32)
MARGEN_FONDO_MINIMAPA = 8
COLOR_PASILLO_MINIMAPA = (110, 115, 125)
GROSOR_PASILLO_MINIMAPA = 3
COLOR_RUTA_MINIMAPA = (255, 220, 80)
GROSOR_RUTA_MINIMAPA = 5
GROSOR_BORDE_RUTA_MINIMAPA = 2  # contorno de los cuartos que están en la ruta
COLOR_TOXICIDAD_BAJA = (60, 200, 90)  # verde: toxicidad 0
COLOR_TOXICIDAD_ALTA = (220, 50, 50)  # rojo: toxicidad 100
FACTOR_OSCURO_NO_VISITADO = 0.35  # brillo de un cuarto aún no visitado
COLOR_CUARTO_ACTUAL = (255, 255, 255)
GROSOR_CUARTO_ACTUAL = 3
COLOR_MARCA_FINAL = (20, 20, 24)
TAMANIO_FUENTE_MINIMAPA = 20

# Mapa de la ciudad (escena MAPA_CIUDAD)
POSICIONES_MAPA_CIUDAD = {  # centro de cada zona en pantalla
    "Plaza": (120, 300),
    "Colegio": (370, 175),
    "Hospital": (260, 410),
    "Empresa de Medios": (560, 375),
    "Alcaldía": (680, 195),
}
# Zonas con nombre y detalle debajo del círculo (las de abajo del mapa,
# para que las calles que suben hacia ellas no crucen el nombre).
ZONAS_ETIQUETA_ABAJO = ("Hospital", "Empresa de Medios")
MARGEN_FONDO_ETIQUETA = 3  # px de fondo alrededor de cada texto del mapa
RADIO_ZONA_MAPA = 26
COLOR_ZONA_MAPA = (90, 110, 150)
COLOR_ZONA_ALCALDIA = (150, 60, 200)  # mismo morado que el jefe
COLOR_ZONA_ACTUAL = (60, 140, 220)
COLOR_ZONA_SELECCIONADA = (255, 220, 80)
GROSOR_ZONA_SELECCIONADA = 4
COLOR_CALLE = (110, 115, 125)
GROSOR_CALLE = 3
COLOR_RUTA_SEGURA = (255, 220, 80)
GROSOR_RUTA_SEGURA = 7
RADIO_ETIQUETA_PESO = 13
GROSOR_BORDE_ETIQUETA_PESO = 2
COLOR_FONDO_ETIQUETA_PESO = (24, 26, 32)
SEPARACION_NOMBRE_ZONA = 16  # px entre el borde del círculo y su nombre
TAMANIO_FUENTE_MAPA = 22
POSICION_TITULO_MAPA = (400, 26)  # centro
POSICION_TEXTO_UBICACION = (10, 40)
POSICION_TEXTO_COMPLETADAS = (10, 70)
POSICION_TEXTO_RUTA = (20, 520)
POSICION_TEXTO_COSTO = (20, 546)
POSICION_TEXTO_AYUDA_MAPA = (20, 572)
POSICION_MENSAJE_MAPA = (400, 70)  # centro del mensaje del último resultado
DURACION_MENSAJE_MAPA = 4.0  # s que se muestra el resultado al volver al mapa

# Mira del apuntado con mouse (se dibuja sobre el HUD, sin sacudida)
COLOR_MIRA = (255, 255, 255)
RADIO_MIRA = 8
GROSOR_MIRA = 2
LARGO_CRUZ_MIRA = 5  # px de cada brazo de la cruz que sale del círculo
COLOR_LINEA_APUNTADO = (255, 255, 255, 60)  # RGBA: línea tenue jugador -> mira
GROSOR_LINEA_APUNTADO = 1

# Sello del cuarto final de una mazmorra normal (cuartos pendientes)
COLOR_PUERTA_SELLADA = (170, 130, 30)  # dorado oscuro: no es por enemigos
COLOR_X_PUERTA_SELLADA = (50, 35, 10)
GROSOR_X_PUERTA_SELLADA = 3
DURACION_MENSAJE_MAZMORRA = 2.0  # s de "Cuarto final desbloqueado" / "Limpia todos..."
COLOR_MENSAJE_MAZMORRA = (255, 220, 80)
POSICION_MENSAJE_MAZMORRA = (400, 70)  # centro: entre el HUD y el muro superior del cuarto
POSICION_TEXTO_CUARTOS_LIMPIOS = (10, 70)
# Minimapa: candado sobre el cuarto final sellado y estrella al desbloquearse
COLOR_CANDADO = (255, 210, 80)
COLOR_FINAL_DESBLOQUEADO = (255, 255, 255)
TAMANIO_CANDADO = 14  # ancho del cuerpo del candado en px
GROSOR_CANDADO = 2
