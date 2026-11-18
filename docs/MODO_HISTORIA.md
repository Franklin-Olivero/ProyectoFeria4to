# Modo historia: «Civitas: Código Nova — La caída de Ciudad Nova»

Campaña narrativa montada sobre los sistemas que ya tenía Civitas (Ciudad Nova,
mazmorras de 6 cuartos, terminal de decisión, jefe final, cooperativo, Online).
No reemplaza nada: añade lógica pura en `src/story/`, contenido en
`content/campaign.json` y pantallas en `src/ui/`. Pantalla real: **1280×720**.

Simulación ficticia con fines educativos. Candidatos, cuentas, ciudadanos y
hechos son inventados.

## Presentación cinematográfica (3 nov 2026)

| Momento | Qué se ve | Archivos |
|---|---|---|
| Partida nueva | **Prólogo «La ciudad que perdió»** (60 s de video con voces y música, luego «TU MISIÓN»): en la ficticia Ciudad Umbral, Teo comparte una publicación sin verificarla; el rumor se multiplica, los vecinos se enfrentan, una panadera lo acusa y la ciudad colapsa. Él comprende lo que causó («Yo pensé que estaba ayudando...»). Corte a Ciudad Nova, todavía viva, y al nuevo protagonista: «Ellos perdieron su ciudad. Tú todavía puedes salvar la tuya.» Esc salta a los objetivos (Enter no corta el video). | `src/story/cinematica.py` (toma `pelicula`, `Rotulo`), `src/ui/cinematica_render.py`, `src/ui/video_cuadros.py` (modo lineal), `content/campaign.json` → `cinematica_intro`, `objetivos_intro` |
| EXTRAS (menú) | **Ver introducción** otra vez, sin tocar la partida. | `menu_principal.VER_INTRO`, `Main._reproducir_cinematica` |
| Entrar a una zona | **Tarjeta de capítulo** («CAPÍTULO 1 · EL RUMOR») y luego el diálogo de siempre (con variante por rol en el cap. 1). | `Campania.presentacion_zona` |
| Alcaldía | **Cinemática de entrada al jefe** (4 tomas, cambia con las pistas) en vez del diálogo. | `cinematica.guion_entrada_jefe` |
| Siempre | **Panel MISIÓN ACTUAL** (ciudad: bajo el cintillo; combate: abajo a la izquierda, compacto) con objetivos y progreso real («Pruebas 2/3»), aviso «Objetivo completado» con sonido. La misión se deriva del estado cada frame: no es estado nuevo. | `src/story/misiones.py` (puro), `src/ui/mision_render.py` |
| Jefe derrotado | **Caída del servidor** (3 tomas) → panel de victoria → **elecciones con escrutinio animado** → Enter → **cinemática del final** (tarjeta + texto, fondo según el final) → elecciones con el epílogo → Enter vuelve a la ciudad. | `guion_caida_servidor`, `guion_final`, `elecciones_render` |
| Colapso 100 % | Toma de NOVA_404 antes del panel de derrota. | `guion_derrota_global` |
| Audio | Música ambiental sintetizada por escena (menú, ciudad, misterio, jefe) y efectos nuevos (notificación, evidencia, misión, viral, transición, victoria, derrota, glitch). Archivos opcionales en `assets/musica/` y `assets/sonidos/`. | `src/core/audio.py`, `assets.RUTAS_MUSICA`, `TONOS_SONIDOS` |
| Interfaz | Capa común `src/ui/layout.py`: zona segura, texto que siempre cabe (wrap → reduce → «…»), un único modal prioritario (cinemática > diálogo > ayuda > estado), animación de entrada de paneles. Correcciones: nodos del árbol de 3 líneas, leyenda bajo el panel, pie de imagen de la tarjeta, grafo social más chico, nota de elecciones ajustada, tarjeta de evidencia a 2 líneas. | `layout.py`, renders de la historia |

Validación visual: 57 capturas headless (SDL dummy) en `docs/capturas/historia/` generadas conduciendo `Main.main()` con eventos programados (01-30) y con render directo (40-49). No se abrió ventana real en esta sesión.

## Ritmo de lectura (5 nov 2026)

Las escenas con texto ya no se van solas: el jugador lee a su ritmo. Modo manual por defecto
y automático opcional en Ajustes → Accesibilidad (150 palabras por minuto + 2 s, mínimo 7 s,
nunca mientras se escribe). Los textos largos se paginan. Tarjetas de capítulo con número,
nombre, ubicación, contexto y objetivo. La intro es un prólogo en video de 60 s (ver `docs/ASSET_MANIFEST.md`).

## Qué se puede jugar

| Paso | Qué pasa | Teclas |
|---|---|---|
| Partida nueva | **Prólogo en video** (60 s) y la pantalla de misión. | Esc salta · Enter comienza la misión |
| Ciudad Nova | Caminar, ruta sugerida, mapa, **I** estado de la ciudad, **H** ayuda. Cintillo con eventos. | WASD · E · G · TAB · M · I · H |
| Entrar a una zona | **Intro del capítulo** (una vez por zona). El Periodista recibe una prueba al entrar. | Enter / Esc |
| Mazmorra | Combate de siempre, en un escenario propio del lugar. **Cada cuarto limpio deja una prueba en el suelo: hay que recogerla.** La 3.ª de cada zona es una **pista de NOVA_404**. | combate normal |
| Cuarto final | **Terminal de decisión** (45 s) con forma de **celular** (la app Civitas): a la izquierda el perfil de quien publicó, con las pruebas como capturas; al centro el reloj y el árbol; a la derecha el post con la fila de botones Verificar / Me gusta / Compartir / Reportar / Ignorar. El 2.º nivel de Verificar y Reportar sale como hoja inferior del celular. Nada delata la respuesta. | ← → · Enter |
| Resultado | **Indicador de reputación** animado, consecuencia, pruebas con las que decidiste, puntos y cómo cambió Ciudad Nova. | Enter |
| Las 3 zonas | Pantalla **«Así viajó la publicación»**: BFS animado sobre el grafo social, saltos, cadena de contagio, rastreo DFS y alcance de la corrección. | Enter |
| Empresa de Medios | **El origen de la señal**: rastreo por DFS en un grafo de cuentas, con pila y regreso, hasta señalar el origen. | ← → · Enter |
| A -60 de reputación | **Crisis** al volver a la ciudad: aceptar la misión «Segunda oportunidad» o negarse (`docs/SISTEMA_REDENCION.md`). | ← → · Enter |
| Alcaldía | Diálogo pre-jefe (cambia según las pistas) y el combate de siempre, sin decisiones. | combate |
| Victoria | Enter → **Elecciones**: apoyo de 4 candidatos, estado de la ciudad y **final** (renace / dividida / el arquitecto). | Enter vuelve · Esc sale |

Recorrido recomendado para la feria (5–8 min): Colegio → Hospital → Empresa de
Medios → Alcaldía. Si se entra a la Alcaldía con una sola zona purificada o por
colapso alto, el juego no bloquea: el diálogo y el epílogo son los parciales.

## Cómo las estructuras de datos gobiernan la historia

### Árbol N-ario (`src/structures/tree.py` → `src/story/escenarios.py`)
- Cada zona tiene un `EscenarioDecision`: raíz = la publicación; hijos = opciones;
  Verificar y Reportar tienen un nivel intermedio («Publicar aclaración con el
  comunicado» / «Creer el recorte viral»; «Reportar con evidencia» / «Reportar en
  masa»); cada hoja es `Purificación Exitosa` o `Detonación`.
- «Me gusta» (2.ª opción, hoja directa, acción `me_gusta`) amplifica como un
  compartir más suave: detona en Colegio y Empresa de Medios (publicaciones
  engañosas) y purifica en Hospital (verdadera), siempre con menos efecto y menos
  puntos que «Compartir». Verificar sigue primera: es la opción segura bajo el cursor.
- La **forma** del árbol no depende de la evidencia (host e invitado comparten ids);
  lo que cambia es **a qué resultado lleva cada hoja**: con `sin_pruebas` o
  `parcial`, «Publicar aclaración» detona («nadie te creyó»). El estado de evidencia
  (`sin_pruebas` → `parcial` → `verificado`/`desmentido`) sale de cuántas pruebas
  reveló el jugador limpiando cuartos y del veredicto real de la publicación.
- Tiempo agotado (también a mitad del árbol) aplica la consecuencia `tiempo_agotado`
  del escenario, no una genérica.
- `TerminalDecision` navega el árbol sin cambios; `Cuarto` recibe `fabrica_arbol`
  (Partida.fabrica_arbol(zona)) y arma el árbol **en el momento en que se abre la
  terminal**, con la evidencia de ese instante.
- El árbol de reportes de toxicidad sigue decidiendo la dificultad de la mazmorra.
- CRUD y recorridos: `tests/test_tree.py` y
  `test_story_escenarios.py::test_crud_y_recorridos_del_arbol_sobre_un_escenario`.

### Grafo social (`src/structures/graph.py` → `src/story/red_social.py`)
- 10 ciudadanos ficticios y 14 conexiones no dirigidas. **Separado** del grafo de
  calles (`grafo_ciudad.py`), que sigue usando Dijkstra para la ruta sugerida.
- `propagar(origen)`: **BFS** por capas hasta 3 saltos; cada contacto reenvía con una
  probabilidad (`random.Random(semilla)` inyectable); el conjunto de visitados
  garantiza que nadie se cuenta dos veces aunque le llegue por el ciclo.
- `corregir(origen)`: BFS exacto; marca `corregidos` (rebotan con 0.25 en vez de
  0.70). **No borra** `expuestos`: la memoria del rumor queda.
- `rastrear(nodo)`: **DFS** iterativo (quién pudo recibirlo); `cadena_hasta(id)`
  reconstruye la ruta real con los predecesores del BFS.
- Efecto medible: cada alcanzado sin corregir suma desinformación; cada dos corregidos
  suman información verificada. Se ve en la pantalla de propagación y en el resultado.
- Eventos aleatorios al volver a la ciudad (`src/story/eventos.py`): noticia viral,
  corrección comunitaria, cuenta sospechosa, rumor reactivado (solo si alguna zona
  detonó). Los que propagan lo hacen por la misma red: una ciudad con correcciones
  publicadas frena mejor los rumores siguientes.

### Estado de Ciudad Nova (`src/story/estado_ciudad.py`, `campania.py`)
- 7 indicadores enteros 0-100 (`balance.INDICADORES_INICIALES`), reputación individual de -100 a +100 (`docs/SISTEMA_REPUTACION.md`),
  puntos. Todo cambio pasa por `Campania._aplicar_efectos` (acotado).
- **Colapso ↔ indicadores**: el colapso sigue siendo la barra de derrota y lo mueve
  `Partida.registrar_decision` (+0.2 fallo / −0.1 éxito). Los indicadores describen
  cómo quedó la ciudad y deciden elecciones y final. Nunca se derivan uno del otro.
- Sin dobles recompensas: `Partida.cerrar_mazmorra` aplica la consecuencia una vez
  por mazmorra; repetir una zona purificada no vuelve a dar puntos ni reputación
  positiva (sí mueve indicadores: la ciudad reacciona a cada publicación);
  investigación y jefe se registran una sola vez; las pistas son un conjunto.

### Elecciones y finales (`src/story/eleccion.py`)
- Apoyo = base + 0.5·indicador afín (+ 0.1·reputación colectiva si el afín es «bueno»),
  normalizado a 100 %. Determinista; ningún ganador fijo.
- Finales: **arquitecto** = 3 pistas + coordinadora correcta + jefe derrotado;
  **renace** = verificada ≥ 55, confianza ≥ 50, desinformación ≤ 45; si no, **dividida**.
  Umbrales en `balance.py`.

### Roles (un matiz cada uno, `balance.py`)
Influencer: +0.15 de rebote al detonar una zona que propaga · Ciudadano: +2 confianza
por éxito · Periodista: 1 evidencia al entrar · Candidato: penalización reputacional ×1.5.

## Archivos

| Nuevo | Para qué |
|---|---|
| `content/campaign.json` | Prólogo, capítulos, escenarios (post, evidencias, árbol), pistas, red social, eventos, sospechosos, finales, candidatos. Se valida al cargar (`contenido.py`). |
| `src/story/contenido.py` · `estado_ciudad.py` · `escenarios.py` · `dialogo.py` · `red_social.py` · `eventos.py` · `investigacion.py` · `eleccion.py` · `campania.py` | Lógica pura (sin pygame). |
| `src/ui/dialogo_render.py` · `tarjetas_render.py` · `indicadores_render.py` · `red_social_render.py` · `investigacion_render.py` · `elecciones_render.py` · `ayuda_render.py` | Dibujo. |
| `tests/test_story_*.py` | 60+ tests nuevos. |

| Modificado | Cambio |
|---|---|
| `src/dungeon/partida.py` | `campania`, `fabrica_arbol(zona)`, `cerrar_mazmorra(..., terminal=None)`, titulares con eventos, reinicio completo. |
| `src/dungeon/cuarto.py`, `mazmorra_jugable.py` | `fabrica_arbol` y `duracion_terminal` opcionales (por defecto, el árbol fijo de siempre). |
| `Online/sesion_red.py` | El invitado arma la mazmorra con la misma fábrica (mismos ids de nodo). |
| `src/ui/terminal_decision_render.py`, `src/ui/celular_render.py` | La terminal como dos celulares (perfil con las pruebas como capturas y feed con el post y sus botones) y una consola central con el reloj y el árbol. Los iconos y el marco del celular se dibujan con primitivas; la foto del post reutiliza la ilustración del capítulo. Sin assets nuevos. |
| `src/ui/pantalla_resultado.py` | `ResultadoMazmorra(consecuencia, deltas)`; paneles «Tu decisión» y «Así cambió Ciudad Nova». |
| `src/core/preferencias.py`, `src/ui/ajustes*.py`, `src/ui/filtro_color.py` | Preferencia **ALTO CONTRASTE** (toda la imagen). |
| `Main.py` | Overlays: diálogo (pausa el mundo), tarjeta de evidencia, panel I, ayuda H, propagación, investigación, elecciones. Sin tocar combate ni jefe. |
| `src/core/assets.py`, `balance.py`, `hud.py` | Constantes y teclas. |

## Online y cooperativo
- Cooperativo local: J1 con teclado y J2 con control navegan la terminal; quien confirma
  carga con la reputación.
- Online: el host es autoritativo. Manda en cada snapshot reputación, indicadores, pruebas y
  red social (`Campania.resumen_red`) y refleja la investigación del capítulo 3 a los
  invitados. Una crisis de un invitado llega con el mensaje `HISTORIA`. Detalle en
  `docs/SISTEMA_REPUTACION.md` y `docs/SISTEMA_REDENCION.md`.

## Pendiente / límites conocidos
- Qué se validó con ventana real y qué falta: `docs/QA_VISUAL.md`.
- `tests/test_online_sincronizacion.py::test_proteger_partida_online_captura_excepciones`
  necesita el sistema de vídeo de pygame; en entorno headless falla igual en la rama base.
- Arte: lista completa y créditos en `docs/ASSET_MANIFEST.md`; criterios en `docs/ART_DIRECTION.md`.
