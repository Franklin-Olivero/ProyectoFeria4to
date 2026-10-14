# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto

* Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
* Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
* Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
* Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego

Civitas es un action-RPG top-down **cooperativo, de 1 a 4 jugadores** (soporta solitario, online más adelante). Inspirado en *The Binding of Isaac*: el jugador recorre una ciudad y entra a distintas mazmorras repartidas por ella. (Hoy: 1 jugador local; la ciudad es **Ciudad Nova**, un mapa 2D de casillas visto desde arriba, estilo Pokémon, por el que el jugador camina y entra por la puerta de cada edificio — Colegio, Hospital y Empresa de Medios con mazmorra normal de varios cuartos, Alcaldía con la mazmorra final. El multijugador es visión futura.)

Cada mazmorra tiene un **nivel de toxicidad por mal uso de redes** propio de su contexto (ciberbullying, acoso, desinformación posteada, etc.) — ese nivel determina su dificultad (más/menos enemigos, más/menos agresivos). Dentro de la mazmorra: cuartos con enemigos que el jugador limpia con sus poderes, al estilo Isaac.

## Ciudad Nova (mapa de casillas + grafo de calles)

**Regla:** las calles de Ciudad Nova son un grafo: Dijkstra marca la ruta sugerida y una calle saturada se bloquea solo si la ciudad sigue conexa.

* `src/dungeon/ciudad_mapa.py` (puro): el mapa como lista de cadenas (64x44 casillas de `TAM_CASILLA` = 16 × `ESCALA_PIXEL` = 48 px; pasto, acera/plaza, calle, edificio, casa, árbol, farola, entrada, barricada), los 4 edificios con su puerta, el spawn en la Plaza, `NODOS_CALLE` y `TRAMOS` (casillas de cada calle y su sección de barricada). Funciones: `es_solida`, `casilla_de`, `entrada_cercana` (`ENTRADA_ALCANCE` = 60 px), `mover_con_colision` (ejes separados: resbala por el eje libre), `calcular_camara` (limitada a los bordes), `grafo_casillas` y `polilinea_ruta`.
* `src/dungeon/grafo_ciudad.py` (puro): 9 nodos — Plaza, 4 cruces y la entrada de cada edificio — y 12 calles con su saturación (`balance.PESOS_INICIALES_CIUDAD`). El trazado es una rueda: ninguna arista es puente y cada edificio tiene dos rutas. `nodo_mas_cercano` (BFS sobre casillas, nunca al otro lado de una barricada) y `ruta_sugerida` (Dijkstra con `MinHeap` manual ignorando calles bloqueadas). Pesos dinámicos al resolver una mazmorra, en las calles del nodo de entrada de esa zona: Detonación +3, Purificación Exitosa -2 (rango [1, 10]). Una calle se bloquea al llegar a `BLOQUEO_PESO` = 8 y se desbloquea al bajar de `DESBLOQUEO_PESO` = 6; `puede_bloquearse` copia el grafo sin las bloqueadas y sin ella y pregunta `es_conexo` (DFS); si no puede, queda abierta al máximo (10). La barricada es física: las casillas de su sección se vuelven sólidas.
* Caminar es gratis (ya no existe costo de viaje en colapso): el costo de una calle saturada es que se bloquea y hay que rodear.
* La Alcaldía empieza sellada con barricadas frente a su puerta; desaparecen cuando `esta_desbloqueada(colapso, mazmorras_completadas)` es True. Sellada, al acercarse se ve "Alcaldía sellada: purifica una mazmorra".
* Escena CIUDAD (`Main.py`, dibujo en `src/ui/ciudad_render.py`, pixel art en `src/ui/casillas_ciudad.py`): se arranca aquí tras elegir rol. WASD/flechas caminan con la velocidad del rol, sin disparar ni apuntar (cursor visible). Junto a una puerta: "E: entrar a <zona> (Toxicidad N)". G alterna la ruta sugerida (línea punteada sobre las calles) al destino que TAB cicla entre edificios ("Sin ruta" si no hay). M abre el mapa del mundo (`src/ui/mapa_ciudad_render.py`): el grafo en abstracto, solo lectura, con tu ubicación, los pesos y las calles bloqueadas. Aura neón pulsante sobre cada edificio con el color de su toxicidad y cintillo "Breaking News Civitas" con titulares de `generar_titulares(estado)` (`src/dungeon/noticias.py`, puro). Fundido corto al entrar y salir de un edificio.
* Colegio tiene reportes de gravedad alta, Hospital media y Empresa de Medios baja; la Plaza es solo el inicio y la Alcaldía es la mazmorra final.

## Mazmorras normales de varios cuartos (grafo de cuartos)

`src/dungeon/mazmorra.py` (pura) + `src/dungeon/mazmorra_jugable.py` (cuerpo Pygame): 6 cuartos generados con DFS aleatorio sobre una cuadrícula 3x3 (aristas del DFS = pasillos, +1 arista extra para crear un ciclo si existe). Puertas solo donde hay arista; al cruzar una puerta abierta se aparece junto a la puerta opuesta del cuarto vecino. Entrada = primer cuarto (sin enemigos, cuenta como limpio); cuarto final = el más lejano por BFS (desempate: menor id) cuya eliminación no desconecta al resto, así ningún cuarto queda atrapado detrás de él. **El cuarto final de una mazmorra normal solo se abre cuando todos los demás cuartos están limpios; la mazmorra se completa al resolver la decisión en ese cuarto.** Mientras tanto, todas las puertas que llevan al final (pueden ser dos por el ciclo) quedan selladas — dorado oscuro con una X, distinto de la puerta roja por enemigos — y al tocarlas aparece "Limpia todos los cuartos primero" (2 s); al limpiar el último pendiente aparece "Cuarto final desbloqueado" (2 s). Un cuarto nunca visitado cuenta como pendiente. HUD: "Cuartos limpios: X/N". La decisión solo puede iniciarse con el sello cumplido y `Partida.cerrar_mazmorra` aplica el resultado una sola vez por mazmorra. Cada cuarto se genera al entrar por primera vez con `nivel_a_dificultad(toxicidad_local)`; los limpiados quedan limpios. Propagación: cada 15 s en un cuarto con enemigos vivos, BFS desde ahí y cada cuarto aún no generado a distancia d suma 10/d de toxicidad (tope 100). Minimapa con la tecla M (`src/ui/mapa_render.py`): color por toxicidad, pendientes (oscuros) vs limpios, cuarto actual, el final con candado mientras está sellado y estrella al desbloquearse, y la ruta BFS al final.

## Minijuego de decisión (fin de cada mazmorra normal)

Al matar a todos los monstruos del **cuarto final** de una mazmorra **normal** (no en los cuartos intermedios ni en la mazmorra final), aparece un minijuego de decisión contra reloj: una situación de redes sociales (ej. publicación de desinformación) y el jugador debe decidir qué hacer — reportar, ignorar, u otra opción según la situación. Esto SÍ es una interfaz que el jugador navega activamente, gobernada por el árbol N-ario:

Árbol actual (`construir_arbol_publicacion()` en `src/ui/terminal_decision.py`): raíz "Publicación Viral" → Verificar / Compartir / Reportar / Ignorar → cada opción lleva directo a su hoja: Verificar y Reportar → Purificación Exitosa; Compartir e Ignorar → Detonación. Contra reloj (10 s); si se acaba el tiempo, Detonación. (Un nivel intermedio tipo "Contrastar con fuente oficial / Creer rumor" es idea de diseño, no está implementado.)

Purificación Exitosa resta Colapso Electoral; Detonación (o no decidir a tiempo) lo suma. Al resolverse, se ajustan los pesos (y barricadas) de las calles de esa zona y se vuelve a Ciudad Nova, frente a la puerta de ese edificio.

**Regla de desbloqueo:** una mazmorra normal cuenta como *completada* SOLO si su decisión termina en Purificación Exitosa. Una Detonación suma colapso pero no cuenta como completada (`src/dungeon/progreso.py`).

## Mazmorra final (boss): solo combate, sin decisiones

La mazmorra final tiene el nivel de toxicidad más alto del juego y es deliberadamente **frenética** (lo más parecido a bullet hell que el tiempo permita) para enganchar al jugador. **No hay ningún minijuego de decisión aquí** — se gana únicamente peleando. Es el cierre de la demo en la Feria.

Como está implementada: jefe "Servidor Central" en un solo cuarto grande, con 3 fases según su vida (>60%, >30%, resto), escudo de anonimato en fase 2 (15 impactos; el Fact-Checking lo rompe de golpe), charcos tóxicos en fase 3 y límite de 180 s.

**Regla de diseño: TODO patrón del jefe, en las 3 fases, debe ser esquivable** (lo verifica `tests/test_jefe_esquivable.py`: siempre queda un pasillo de al menos 3 anchos de jugador en radios 120/180/240 px).
* Fase 1: ráfaga radial de 16 posiciones con un hueco de 3 balas consecutivas; el hueco salta a más de 60° del anterior y evita apuntar contra un muro cercano. Invoca súbditos.
* Fase 2: espiral de 2 brazos que gira lento (50°/s), con balas a la velocidad de la fase 1, + disparo dirigido.
* Fase 3: ciclo de 8 s en vez de todo junto: ráfagas con hueco en 0 y 1.2 s, espiral de 4.0 a 6.5 s y 1.5 s de descanso sin ataques (ventana para castigar). El disparo dirigido nunca sale junto a una ráfaga (espera 0.8 s). Charcos: uno cada 6 s, máximo 2 vivos, nunca a menos de 90 px del jugador ni sobre el jefe.
* Nunca hay más de `MAX_PROYECTILES_JEFE` = 40 balas del jefe vivas: con el tope lleno omite emitir.
* Todas estas constantes viven en `balance.py`. Tiempo agotado o jugador muerto → derrota: suma colapso y la pelea se reinicia. Jefe muerto → resta colapso y pantalla de victoria: ENTER vuelve a Ciudad Nova frente a la Alcaldía (colapso y progreso se conservan), ESC cierra el juego.

**Regla de desbloqueo:** se entra por la puerta de la Alcaldía (E), solo si el colapso es mayor a 80% o si hay al menos 1 mazmorra completada (con Purificación Exitosa). Si no, sus barricadas tapan la puerta y se muestra "Alcaldía sellada: purifica una mazmorra".

## Enemigos: agresividad absoluta
Los enemigos nunca se quedan quietos: con `agro_permanente = True` (por defecto, en los cuartos normales y en los súbditos del jefe) el nodo de detección del behavior tree siempre tiene éxito y cada tipo hace lo suyo desde cualquier distancia. `RANGO_DISPARO_ENEMIGO` se conserva para el caso `agro_permanente = False`. (La única huida es la del Curandero, que es su rol, y nunca bloquea el cuarto: ver abajo.)

## Gracia de entrada (1 s al entrar a un cuarto)
`GRACIA_ENTRADA_CUARTO_S` = 1.0 (`src/dungeon/gracia_entrada.py`, objeto puro `GraciaEntrada`): se reinicia al empezar la mazmorra, en cada puerta cruzada (también al volver a un cuarto limpio) y al entrar o reiniciar la arena del jefe. Mientras dura, la rama "¿congelado?" es la PRIMERA del Selector de todo enemigo (prioridad sobre `agro_permanente`): no persiguen, no disparan ni golpean; en la arena el jefe ni se actualiza. El jugador puede moverse pero no dispara ni usa F (`JugadorBase.armas_bloqueadas`, lo pone Main.py). Se ve como un anillo de cuenta regresiva alrededor del jugador y enemigos con alfa pulsante. Los proyectiles en vuelo se limpian al cambiar de cuarto. Los enemigos de un cuarto nuevo aparecen a >= `DISTANCIA_MIN_SPAWN_ENEMIGO` (260 px) del punto por donde entra el jugador (`src/dungeon/spawn.py`).

## Tipos de enemigo
`src/entities/tipos_enemigo.py` (puro: `TipoEnemigo`, `CONFIG_TIPO` desde `balance.STATS_TIPO_ENEMIGO`, `composicion_cuarto`) + `src/entities/enemigos.py` (`Perseguidor`, `Tirador`, `Curandero` heredan de `Enemigo`: reutilizan vida, empuje, escudo, agro, aggro forzado y carga por kill; solo cambia su behavior tree, armado con `src/ai/behavior_tree.py` y los nodos puros de `src/ai/nodos_combate.py`: `DistanciaMenorQue`, `MantenerDistancia`, `Huir`, `CurarAliado`, `DispararApuntado`).
* Perseguidor: velocidad ×1.15, vida 3, daño por contacto 1 cada 0.8 s, no dispara.
* Tirador: velocidad ×0.8, vida 2; mantiene 320 ± 40 px (retrocede, se acerca u orbita) y dispara apuntado cada 1.8 s tras 0.25 s de telegrafía (se ilumina); bala a 260 px/s.
* Curandero: velocidad ×0.7, vida 2, no ataca; se esconde detrás de sus aliados, huye si el jugador está a < 200 px y cada 3 s cura el 34 % de la vida máxima al aliado más herido a <= 280 px. Nunca a sí mismo ni al jefe, máximo 2 curas por aliado por cuarto. Tras 6 s siendo el único vivo entra en pánico: persigue a velocidad normal y deja de curar. El cuarto no se libera mientras quede cualquier enemigo vivo.
* Composición por tramo (`composicion_cuarto(nivel_dificultad, es_cuarto_final, rng, es_cuarto_inicial)`): BAJA (2) solo perseguidores, el final puede traer 1 tirador; MEDIA (3) 2 perseguidores + 1 tirador o 1 + 1 + 1 curandero (25 %); ALTA (5) 2 tiradores, 1-2 curanderos (nunca más que los demás) y el resto perseguidores, el final con ≥ 1 curandero y ≥ 2 tiradores. La entrada y sus vecinos (cuartos iniciales) nunca tienen curanderos; siempre hay ≥ 1 enemigo que no es curandero. Los curanderos aparecen en las posiciones más lejanas a la entrada. Porcentajes y máximos en `balance.py`.
* Los súbditos del jefe alternan Perseguidor y Tirador.
* Arte: todo el render de enemigos pide su imagen a `sprites.sprite_enemigo(tipo)`. Hoy devuelve un pixel art distinto por tipo (`PIXEL_ART_ENEMIGO`); si existe `assets/sprites/enemigos/<ID_SPRITE_ENEMIGO[tipo]>.png` lo carga (con caché) y si no, cae al placeholder. Colores, tamaño de hitbox e id de sprite por tipo en `assets.py`.

## Colapso Electoral
Barra 0.0%-100.0%: +0.2 por cada fallo (Detonación o derrota contra el jefe) y -0.1 por cada éxito (Purificación Exitosa o jefe derrotado). Caminar por la ciudad no cuesta colapso. **Derrota global:** si llega a 100% (en cualquier escena), la escena DERROTA muestra "Colapso total" con el input de combate desactivado; ENTER reinicia la partida completa (colapso 0, progreso 0, en la Plaza, pesos de las calles restablecidos y sin barricadas, mismo rol) y ESC sale.

## Controles

* WASD o flechas: mover (en combate y caminando por Ciudad Nova).
* En Ciudad Nova: E entra al edificio cercano, G muestra/oculta la ruta sugerida, TAB cambia el destino, M abre/cierra el mapa del mundo.
* Mouse: apuntar en combate (Ciudadano, Influencer y Periodista). En combate el cursor del sistema se oculta y se dibuja una mira con una línea tenue desde el jugador (`MOSTRAR_LINEA_APUNTADO` en `balance.py`). El Candidato no usa el mouse: cursor normal, sin mira.
* SPACE o click izquierdo (mantenidos): disparar (`CLICK_DISPARA` en `balance.py`). Mismo cooldown y cadencia con cualquiera de los dos.
* F: habilidad. M: minimapa (en la mazmorra).
* ENTER y flechas: menús y terminal de decisión.

**Regla de apuntado:** la dirección de disparo siempre sale de `direccion_mirada`. En los roles con `apunta_con_mouse = True` solo la actualiza `apuntar_a()`; el Candidato (`apunta_con_mouse = False`) la actualiza al caminar porque su ataque es radial y su habilidad sale hacia donde camina. Los roles nunca calculan su propia dirección. La cuenta vive en `src/core/apuntado.py` (pura; zona muerta `ZONA_MUERTA_APUNTADO` = 6 px) y `Main.py` le resta al mouse la sacudida de pantalla antes de apuntar.

## Los 4 roles jugables
Influencer, Periodista, Ciudadano, Candidato — los 4 están implementados y se eligen con las teclas 1-4 al empezar. Cada uno: ataque básico con disparo sostenido (SPACE o click izquierdo mantenidos, limitado por la cadencia del rol) + habilidad activa (F) que **se carga matando enemigos dentro de la mazmorra** (no por temporizador) — una barra de carga que se llena con kills y se gasta completa al usar la habilidad. Sinergia: Influencer agrupa, Periodista expone, Candidato remata, Ciudadano sostiene.

* Influencer: proyectil ancho que empuja al enemigo golpeado / Live Stream Viral (fija el aggro de todos los enemigos vivos del cuarto hacia él durante 3 s)
* Periodista: rayo perforante lineal / Fact-Checking (rayo perforante que quita el escudo de anonimato de cada enemigo que cruza; al jefe se lo rompe de golpe)
* Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (diseño: domo que frena proyectiles hostiles y regenera vida de aliados dentro; hoy solo se activa como flag con duración de 4 s y radio dibujado, sin frenar proyectiles ni curar)
* Candidato: onda expansiva radial / Debate Rebotante (3 proyectiles que rebotan en las paredes hasta 3 rebotes o 4 s)

Clase base común: `JugadorBase` en `src/entities/player.py`; cada rol solo sobreescribe `ataque_basico()` y `usar_habilidad()` (y el Candidato, además, `apunta_con_mouse = False`).

**Invulnerabilidad tras un golpe (i-frames):** al recibir daño, el jugador queda invulnerable `INVULNERABILIDAD_DURACION` = 0.6 s (en `balance.py`) y su sprite parpadea cada 0.08 s. Vale para los 4 roles, en el cuarto normal y en la arena del jefe. No se acumula: un golpe durante la ventana no la reinicia. Los charcos tóxicos respetan la ventana (no dañan durante ella) pero su daño continuo no la abre.

## Roles: stats y trade-offs

Multiplicadores relativos a la base (`VELOCIDAD_BASE` = 220 px/s, `VIDA_BASE` = 5, `DANIO_BASE` = 1). Cadencia en volleys por segundo; carga en kills para llenar la habilidad; proyectiles nominales = proyectiles que impactan a un objetivo por volley (para el DPS).

| Rol | Velocidad | Cadencia | Daño | Vida | Carga | Proyectiles | Fortaleza / debilidad |
|---|---|---|---|---|---|---|---|
| Ciudadano | 0.85 | 2.4 | 0.6 | 1.40 | 6 | 1.5 | El que más aguanta y dispara más seguido / el más lento, poco daño por proyectil |
| Influencer | 1.25 | 2.0 | 1.0 | 0.85 | 5 | 1.0 | El más rápido / el más frágil |
| Periodista | 1.05 | 1.4 | 1.6 | 0.90 | 5 | 1.0 | Alto daño por rayo y buena movilidad / cadencia baja, poca vida |
| Candidato | 0.95 | 0.9 | 3.0 | 1.15 | 4 | 1.0 | Mayor daño por golpe y habilidad más barata / la cadencia más lenta |

Además: buff por kill propia (cadencia x1.25 durante 2 s, sin acumular), cadencia acotada a un intervalo mínimo de 0.08 s y un tope de 12 volleys/s, y carga compartida de equipo (cada aliado recibe 0.25 de la kill de otro).

Todo cambio de balance se hace en `src/core/balance.py`, nunca dentro de las clases de rol. Cada rol debe tener una fortaleza y una debilidad clara; ningún rol puede dominar a otro en todas las estadísticas.

## Estructura de carpetas obligatoria
```text
PruebaPythonGame/
│-- Main.py
│-- requirements.txt
│-- assets/             # (aún no existe: llegará con el arte real)
│-- src/
│   │-- core/          # constantes, balance, configuración de pantalla, reloj, escenas, apuntado
│   │-- structures/     # árbol N-ario, grafo y min-heap puros, sin dependencias de Pygame
│   │-- ai/             # behavior tree genérico y nodos de combate, sin dependencias de Pygame
│   │-- entities/       # jugadores (roles), proyectiles, enemigos y sus tipos, jefe
│   │-- dungeon/        # cuartos, mazmorra multi-cuarto, mapa de casillas y grafo de calles de Ciudad Nova, noticias, partida, clasificador, mazmorra final
│   │-- ui/             # minijuego de decisión, selección de rol, Ciudad Nova (casillas y render), mapa del mundo, minimapa, victoria/derrota
│   └-- network/        # (aún no existe) protocolo sockets, serialización, server/client
```
No mezclar responsabilidades entre carpetas. `structures/` y `ai/` no deben importar `pygame`. La lógica de jefe, charcos, mazmorra final, invulnerabilidad, progreso, balance, terminal de decisión, mazmorra multi-cuarto, mapa de casillas de Ciudad Nova, grafo de calles, noticias, partida, escenas, selector de destino, gracia de entrada, posiciones de aparición, tipos de enemigo y su composición también es pura (sin `pygame`) para poder probarse en aislado; su dibujo vive en módulos aparte.

## Estado real del MVP

1. `tree.py` con CRUD/recorridos — completado
2. Cuarto con puertas bloqueables y spawn placeholder — completado
3. Behavior tree (Selector→Sequence) + jugador + proyectiles — completado
4. `docs/ARQUITECTURA.md` — completado
5. Clasificador de toxicidad (`src/dungeon/clasificador_toxicidad.py`) conectado al spawn del cuarto — completado
6. Variable de colapso en pantalla (`src/core/colapso.py`) — completado
7. Minijuego de decisión (Verificar/Compartir/Reportar/Ignorar) al final de mazmorra normal, usando `tree.py` como segunda estructura — completado
8. Carga de habilidad por kills (reemplaza cooldown por tiempo) — completado
9. Mazmorra final frenética sin decisiones (jefe "Servidor Central": `src/entities/jefe.py`, `src/dungeon/mazmorra_final.py`, `src/dungeon/arena_jefe.py`, `src/dungeon/charco.py`; se entra desde la Alcaldía del mapa si está desbloqueada) — completado
10. Los 4 roles (Ciudadano, Influencer, Periodista, Candidato) sobre `JugadorBase`, con selección 1-4 — completado (la Burbuja Comunitaria del Ciudadano aún no frena proyectiles ni cura)
11. Balance por rol en `src/core/balance.py`, disparo sostenido y carga compartida de equipo — completado
12. Invulnerabilidad tras un golpe, pantalla de victoria (ENTER/ESC) y máquina de estados de escena en `Main.py` — completado
13. Derrota global al llegar el colapso a 100% (escena DERROTA, `src/ui/pantalla_derrota.py`, reinicio en `src/dungeon/partida.py`) — completado
14. `MinHeap` binario manual (`src/structures/min_heap.py`) — completado
15. `Grafo` con lista de adyacencia, CRUD, BFS, DFS iterativo, `es_conexo`, `camino` y Dijkstra (`src/structures/graph.py`) — completado
16. Mazmorra normal de 6 cuartos sobre el grafo: generación DFS 3x3 con un ciclo, cuarto final por BFS, generación perezosa y propagación de toxicidad por BFS (`src/dungeon/mazmorra.py`, `mazmorra_jugable.py`) — completado
17. Grafo de la ciudad con Dijkstra y pesos dinámicos (`src/dungeon/grafo_ciudad.py`); hoy es la red de calles de Ciudad Nova (punto 22) — completado
18. Minimapa de la mazmorra con la tecla M (`src/ui/mapa_render.py`) — completado
19. Apuntado con mouse para Ciudadano, Influencer y Periodista (`src/core/apuntado.py`, `JugadorBase.apuntar_a`, mira en `Main.py`) y click izquierdo como segundo gatillo; el Candidato sigue apuntando al caminar — completado
20. Sello del cuarto final: solo se entra con todos los demás cuartos limpios (también por el ciclo), el final nunca es punto de corte y la decisión cierra la mazmorra una sola vez — completado
21. Jefe esquivable (ráfaga con hueco, espiral lenta, fase 3 por ciclos con descanso, tope de 40 balas, charcos justos) y agresividad absoluta de enemigos y súbditos (`agro_permanente`) — completado
22. Ciudad Nova caminable: mapa de casillas con colisión y cámara (`src/dungeon/ciudad_mapa.py`), red de calles como grafo con ruta sugerida (Dijkstra), barricadas por saturación con histéresis 8/6 que nunca desconectan la ciudad, Alcaldía sellada con barricadas, escena CIUDAD con fundido, mapa del mundo (M), auras de toxicidad y cintillo de noticias (`src/dungeon/noticias.py`, `src/ui/ciudad_render.py`, `src/ui/casillas_ciudad.py`); sin costo de viaje — completado

23. Segundo de gracia al entrar a cada cuarto (enemigos congelados, jugador sin armas, aparición a >= 260 px) y tres tipos de enemigo (Perseguidor, Tirador, Curandero) con composición por tramo de toxicidad y arte intercambiable vía `sprite_enemigo` (`src/dungeon/gracia_entrada.py`, `src/dungeon/spawn.py`, `src/entities/tipos_enemigo.py`, `src/entities/enemigos.py`, `src/ai/nodos_combate.py`, `src/ui/enemigo_render.py`); capturas en `docs/capturas/` — completado

Ciudad Nova es un mapa de casillas sin NPCs: no agregues NPCs ni sockets / `src/network/` salvo que se te pida explícitamente — son alcance de entregas futuras.

## Convenciones de código

* Un módulo, una responsabilidad.
* Priorizar código explicable sobre código optimizado en exceso — se sustenta en voz alta ante la profesora.
* Todo árbol/grafo debe exponer sus operaciones de forma que se puedan probar de forma aislada (sin Pygame).
* Todo elemento visual debe referenciar una constante o ruta de sprite centralizada en `src/core/assets.py`, nunca un color hardcodeado disperso. Los números de balance (stats de roles, jefe, charcos, invulnerabilidad) van en `src/core/balance.py`.
* El arte es pixel art dibujado en código dentro de `src/ui` (filas de caracteres + paleta, cacheadas: `sprites.py`, `casillas_ciudad.py`), con paleta y tamaños centralizados en `assets.py`. Cuando llegue arte real solo se cambia cómo se obtienen las imágenes, sin tocar la lógica. Los enemigos ya cargan su PNG si existe (`sprite_enemigo`, fallback al placeholder).

## Instrucciones de Git

* Al hacer commits, NO incluyas la línea "Co-Authored-By: Claude" ni ninguna línea de atribución a Claude/Anthropic.
* No modifiques `git config user.name` ni `user.email` del repo bajo ninguna circunstancia.

## Fechas relevantes

* Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
* Entrega 2 (grafos): 20-30 oct 2026
* Entrega Final (integración + red): 16-20 nov 2026
* Feria Gamer: 26 nov 2026