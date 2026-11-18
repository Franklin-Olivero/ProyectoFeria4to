# Manifiesto de assets del modo historia

Regla: **nada se genera con Higgsfield sin aprobación del equipo** (créditos). El
juego arranca completo sin ningún archivo de esta lista: cada imagen y video tiene un
fallback. Costos: Higgsfield los muestra al pedir una generación;
no se inventan aquí.

## Lo que ya se dibuja en código o con hojas existentes (reutilizado)
- Retratos de los 4 roles (`assets/sprites/retratos/<rol>.png`, 512 px, Higgsfield,
  ya existentes) → diálogos y selección.
- Hojas de sprites de roles, enemigos, jefe, cuarto, puertas, charco (Pixelbolt).
- Ciudad Nova, HUD, terminal, tarjetas, paneles, grafo social, elecciones: Pygame.
- Iconos de Civitas y NOVA_404 en los diálogos: dibujados en código
  (`dialogo_render._icono_sistema`).

## Style guide (inglés, para reutilizar sin gastar tokens)
Top-down 2D pixel-art-inspired cyberpunk civic mystery. Crisp readable silhouettes,
restrained teal (#3EE6C4) / violet (#A46EFF) / amber (#FFBE3C) palette on deep navy
(#0F0D22), consistent soft neon lighting, night city mood. No text, no watermark,
no UI typography, no logos. Original design, game-ready, 16:9 unless stated.

## Generadas el 3 nov 2026 (aprobadas por el equipo)
Modelo Higgsfield `nano_banana_2` (servido como nano_banana_flash), 1k, 1.5 créditos
cada una (12 créditos en total de 1200). Re-guardadas con pygame (sin metadatos
C2PA/XMP) y escaladas a 1280×720; retratos con fondo recortado a transparente, 512×512.

| Id | Archivo | Uso |
|---|---|---|
| A01 | `assets/story/portada.png` | Fondo del prólogo (`assets.FONDO_PROLOGO`). |
| A02 | `assets/sprites/retratos/civitas.png` | Retrato de Civitas en diálogos. |
| A02b | `assets/sprites/retratos/nova.png` | Retrato de NOVA_404 en diálogos. |
| A03 | `assets/story/capitulo_colegio.png`, `capitulo_hospital.png`, `capitulo_medios.png` | Fondo de la intro de cada capítulo (`assets.FONDO_POR_ZONA`). |
| A04 | `assets/story/servidor_central.png` | Fondo del diálogo pre-jefe. |
| A06 | `assets/story/elecciones.png` | Fondo de la pantalla de elecciones. |

Carga: `sprites.fondo_historia(nombre, tamanio)` con caché; `retrato_rol("civitas"/"nova")`.
Si falta un archivo, cada pantalla dibuja su versión anterior (velo / icono en código).

## Generadas el 3 nov 2026 (cinemáticas, 7,5 créditos de un tope autorizado de 12)
Modelo `nano_banana_2` (servido como nano_banana_flash), 16:9 1k (1376×768), **1,5 créditos cada una**
(costo verificado con `get_cost`), con `portada.png` como referencia de estilo. Re-guardadas con pygame
a 1280×720 sin metadatos. Prompts completos en `docs/PLAN_ASSETS_CINEMATICOS.md`.

| Id | Archivo | Uso |
|---|---|---|
| C01 | `assets/story/ciudadanos_civitas.png` | Intro: escenas «Civitas» y «El caos» (`assets.FONDO_CIUDADANOS`). |
| C02 | `assets/story/pantallas_nova.png` | Intro: «La amenaza»; cinemática de derrota global (`FONDO_PANTALLAS_NOVA`). |
| C03 | `assets/story/servidor_caido.png` | Caída del servidor y final «El arquitecto» (`FONDO_SERVIDOR_CAIDO`). |
| C04 | `assets/story/final_renace.png` | Final «Ciudad Nova renace» (`FONDO_POR_FINAL`). |
| C05 | `assets/story/final_dividida.png` | Final «La ciudad dividida». |

## Generadas el 5 nov 2026 (reputación y redención, 57 créditos)

Saldo: 1180,5 → 1123,5 (verificado con `balance`). Costos verificados con `get_cost` antes de
generar. Sin descartes: cada generación se usa en el juego. Referencias: `portada.png` para
lugares, retrato base para personajes, para que nadie cambie de cara.

| Id | Archivo | Modelo | Créditos | Uso |
|---|---|---|---|---|
| D01 | `assets/story/crisis_reputacion.png` | nano_banana_2 | 1,5 | Crisis |
| D02 | `assets/story/redencion.png` | nano_banana_2 | 1,5 | Elección, misión y recuperación |
| D03 | `assets/story/final_confianza_perdida.png` | nano_banana_2 | 1,5 | Final de derrota |
| D04 | `assets/story/nova_aparicion.png` | nano_banana_2 | 1,5 | Cuadro base del clip de NOVA_404 |
| D05 | `assets/sprites/retratos/rosa.png` | nano_banana_2 | 1,5 | Rosa Beltrán, la mediadora |
| D06 | `assets/sprites/retratos/<rol>_preocupado.png` y `<rol>_decidido.png` (8) | nano_banana_2 | 12 | Retratos según reputación |
| V01 | `assets/story/video/intro_ciudad/` | kling3_0, 5 s, sin sonido | 7,5 | Primera toma de la intro (recortado a 44 cuadros) |
| V02 | `assets/story/video/nova_aparicion/` | kling3_0 | 7,5 | Primera aparición de NOVA_404 |
| V03 | `assets/story/video/crisis/` | kling3_0 | 7,5 | Crisis (recortado a 34 cuadros: al final se deformaba) |
| V04 | `assets/story/video/redencion/` | kling3_0 | 7,5 | Recuperación |
| V05 | `assets/story/video/jefe/` | kling3_0 | 7,5 | Entrada al Servidor Central |

Se descartó Seedance 2.5 (35 créditos por clip de 5 s) porque Kling mantenía bien el pixel art.

Video: cuadros JPG de 1280×720 a 12 FPS (30 MB en total), extraídos con
`tools/extraer_cuadros.py`. El juego no necesita ffmpeg ni internet; si falta la carpeta,
la toma usa la ilustración con paneo. Clips con sonido apagado: el audio lo pone el juego.

Retratos: fondo verde quitado con `tools/procesar_retrato.py`.

## Audio (propio, sin costo ni licencias de terceros)

`tools/generar_audio.py` compone por síntesis matemática 10 pistas en `assets/audio/musica/`
(menu, ciudad, combate, jefe, misterio, decision, crisis, redencion, victoria, derrota; 15 MB,
WAV de 22 kHz) y 15 efectos en `assets/audio/sfx/`. Si faltan, el juego sintetiza colchones y
pitidos. **Nadie las ha escuchado aún:** ver `docs/QA_VISUAL.md`.

## Escenarios de mazmorra y fachadas (Higgsfield, 10 nov 2026)

16 imágenes con `nano_banana_2` (1k, 1,5 cr c/u = **24 créditos**; saldo 1099,5), todas con
el pack escolar comprado (`assets/colegio/props.png`) como `image_references` para heredar su
pixel art 3/4 frontal. Prompts en `prompts/higgsfield_mazmorras.md`. Ninguna se usa entera
como fondo: `tools/procesar_higgsfield.py` las convierte en piezas (croma verde, separación
por islas, reducción a la rejilla nativa ~8 px, paleta corta, contorno, bordes repetibles).

| Archivos | Origen | Uso |
|---|---|---|
| `assets/mazmorras/{hospital,medios,alcaldia}/piso.png` (128×128, ×2) | textura 4×4 | multiplicada sobre el piso pintado |
| `assets/mazmorras/{hospital,medios,alcaldia}/muro.png` (franja de 36 px) | muro frontal 16:9 | cara del muro |
| `assets/mazmorras/<tema>/props/*.png` (52 objetos, ×2) | 7 hojas sobre verde | `src/ui/decor_mazmorra.py` los coloca junto a los muros (plan puro `plan_decor.py`) |
| `assets/ciudad/fachadas/{hospital,medios,alcaldia}.png` (264×144 / 264×96, ×2) | edificio 16:9 / 21:9 | `edificios_ciudad.imagen` (huella exacta) |

Descartados: de la hoja `hospital_b` se usan 6 de 11 objetos (los demás salieron isométricos);
`cables` de Medios no se coloca (a tamaño de juego parecía un enemigo). El Colegio conserva el
pack comprado para el aula; la biblioteca y el laboratorio suman objetos generados. El lobby
(pack Backrooms) no se tocó. Sin los PNG, todo vuelve al pintado en código de `temas_mazmorra.py`.
Capturas antes/después: `tools/capturas_mazmorras.py` → `docs/capturas/mazmorras/`.

## Prólogo «La ciudad que perdió» (Higgsfield, 13 nov 2026, 133 créditos)

Saldo 1099,5 → 966,47 (verificado con `balance`). Costos verificados con `get_cost` antes de
generar: `nano_banana_2` 1,5 por imagen; `kling3_0` 5 s std 7,5 sin sonido, 10 con sonido,
8,75 en modo pro; ElevenLabs v4 0,46 por línea; ElevenLabs Music v2.5 ≈ 8,7 por 60 s.

| Qué | Modelo | Cantidad | Uso |
|---|---|---|---|
| Hoja de personaje de Teo (defensor de Ciudad Umbral) | nano_banana_2 (ref. retrato `periodista` + `portada`) | 1 | Referencia de todas las tomas con Teo |
| Ciudad Umbral antes del colapso | nano_banana_2 (ref. `portada`) | 1 | Referencia de lugar y cuadro inicial de la transición |
| Cuadros clave de cada toma | nano_banana_2 (ref. hoja de Teo + Umbral) | 15 (3 rehechas: dos teléfonos, logo parecido a una red real, bufanda que parecía una garra) | Cuadro inicial/final de cada clip |
| Tomas animadas | kling3_0, 16:9 | 11 (1 descartada) | Ver tabla de tomas en `tools/montar_prologo.py` |
| Voces en español (Lía, la panadera, Teo y el narrador) | elevenlabs_v4 | 9 líneas | Diálogos y narración |
| Música de tensión (42 s) y heroica (20 s) | elevenlabs_music_v2_5, instrumental | 2 | Banda sonora |

Efectos: los del juego (`notificacion`, `viral`, `glitch`, `transicion`) y el ambiente de
multitud que Kling generó en 3 tomas. Ciudad Nova reutiliza los clips V01 (`intro_ciudad`) y
V02 (`nova_aparicion`) de esta tabla, sin costo nuevo.

Montaje: `tools/montar_prologo.py` (ffmpeg de `imageio-ffmpeg`, solo para producir) arma la
lista de tomas, mezcla voces + música (la música baja sola cuando alguien habla) + efectos y
escribe `assets/story/video/prologo_umbral/` (906 cuadros JPG de 960×540 a 15 fps, 55 MB,
`"lineal": true`) y `assets/audio/musica/prologo_umbral.ogg` (60,5 s). Los subtítulos, la
alerta «CIUDAD UMBRAL — COLAPSO TOTAL», el lema y el título los dibuja el juego
(`content/campaign.json` → `rotulos`). `tools/exportar_prologo.py` renderiza el corto con el
dibujo real del juego a MP4 y deja capturas en `docs/capturas/prologo/`.
Fuentes completas (clips MP4, voces, música, cuadros clave, máster y video final) en
`_packs/prologo_umbral/`, fuera de git. Respaldo sin video: `assets/story/umbral_colapso.png`.

### Segunda versión (13 nov 2026, 45,4 créditos; saldo 921,1): audio, español y «tuvo opciones»

- **Audio inaudible, causa real:** la banda sonora (con voces) sonaba por el volumen de
  *música*; sin `ajustes_audio.json`, el juego rescataba `volumen_musica: 22` de un
  `preferencias.json` viejo → 1,0 × 0,22 × 0,85 = 0,19. Ahora las pistas de
  `assets.PISTAS_CINEMATICA` usan solo el volumen general (categoría `cinematica`, 1,0):
  aplicado 1,00 medido en ventana real. El archivo además se masteriza a -16 LUFS,
  pico verdadero -1,15 dBTP (antes -18,4 LUFS), cada voz normalizada por separado y la
  música con ducking bajo los diálogos.
- **Voces:** 17 líneas nuevas en español con `elevenlabs_v4` (Leo = Teo, Isabella = Lía,
  Nora = la ciudadana, Sterling = narrador) con dirección «[Latin American Spanish accent]» y
  de emoción (no se pronuncia: verificado con Whisper). Ninguna voz del catálogo es nativa en
  español (sus muestras, transcritas, están en inglés): el acento hay que validarlo de oído.
  Whisper reconoce las 17 líneas dentro de la mezcla final.
- **Tomas nuevas** (kling3_0, desde los cuadros clave existentes): Teo en el balcón con las
  balizas de misión sobre el Colegio, el Hospital y la Empresa de Medios; la misión en el
  teléfono que él descarta; las tres entradas con las balizas apagándose; la réplica de la
  confrontación (desde el último cuadro de la anterior, modo pro). 3 imágenes + 4 clips +
  21 voces (17 + 4 de prueba de acento). Ciudad Nova suma las ilustraciones de capítulo.
- Rótulos de juego dibujados por el motor: misión, «MISIÓN DESCARTADA», días, publicaciones
  falsas, barra «COLAPSO DE UMBRAL» de 18 % a 94 %, lugares de Nova y la pregunta final.

## Pendiente (opcional, sin generar)

| Id | Nombre lógico | Archivo esperado | Tamaño | Dónde se usaría | Fallback actual |
|---|---|---|---|---|---|
| A05 | Iconos de interfaz (pista, evidencia, candidato) | `assets/story/iconos/*.png` | 32×32, transparente | Tarjetas | Chips de texto |

## Procedencia y licencia
Todas las imágenes de `assets/story/` y los retratos de Civitas, NOVA_404, Rosa y las emociones: generados el 3 y 5 nov 2026
con Higgsfield (nano_banana_2) desde la cuenta del equipo, con los prompts del style guide
(sin texto ni logos), para uso en este proyecto académico. Se guardan en el repo; nunca se
referencian URL temporales en runtime.
