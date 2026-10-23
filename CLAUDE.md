# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto

* Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
* Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
* Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
* Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego

Civitas es un action-RPG top-down **cooperativo, de 1 a 4 jugadores** (soporta solitario, online más adelante). Inspirado en *The Binding of Isaac*: el jugador recorre una ciudad y entra a distintas mazmorras repartidas por ella. (Hoy: 1 o 2 jugadores locales —el J2 con control de PS4—; la ciudad es un **mapa de selección** sobre un grafo ponderado — Plaza, Colegio, Hospital, Empresa de Medios y Alcaldía — desde donde se viaja a 3 mazmorras normales de varios cuartos y a la mazmorra final. Ciudad Nova como mundo abierto caminable y el multijugador son visión futura.)

Cada mazmorra tiene un **nivel de toxicidad por mal uso de redes** propio de su contexto (ciberbullying, acoso, desinformación posteada, etc.) — ese nivel determina su dificultad (más/menos enemigos, más/menos agresivos). Dentro de la mazmorra: cuartos con enemigos que el jugador limpia con sus poderes, al estilo Isaac.

## Mapa de la ciudad (grafo ponderado)

`src/dungeon/grafo_ciudad.py`: cada zona es un nodo y cada calle una arista cuyo peso es su saturación (pesos iniciales en `balance.PESOS_INICIALES_CIUDAD`; Plaza → Empresa de Medios directo pesa 6, por el Hospital 3 + 2 = 5). En la escena MAPA_CIUDAD las flechas izquierda/derecha eligen zona, se resalta la ruta más segura (Dijkstra con `MinHeap` manual) desde la ubicación actual y su costo; ENTER viaja: el colapso sube `COSTO_VIAJE_COLAPSO` (0.02) por unidad de costo y la ubicación pasa a ser esa zona. Pesos dinámicos: tras la decisión de una mazmorra, Purificación Exitosa baja en 1 las calles de esa zona (mínimo 1) y Detonación las sube en 1 (máximo 10). Colegio tiene reportes de gravedad alta, Hospital media y Empresa de Medios baja; la Plaza es solo el inicio y la Alcaldía es la mazmorra final.

## Mazmorras normales de varios cuartos (grafo de cuartos)

`src/dungeon/mazmorra.py` (pura) + `src/dungeon/mazmorra_jugable.py` (cuerpo Pygame): 6 cuartos generados con DFS aleatorio sobre una cuadrícula 3x3 (aristas del DFS = pasillos, +1 arista extra para crear un ciclo si existe). Puertas solo donde hay arista; al cruzar una puerta abierta se aparece junto a la puerta opuesta del cuarto vecino. Entrada = primer cuarto (sin enemigos, cuenta como limpio); cuarto final = el más lejano por BFS (desempate: menor id) cuya eliminación no desconecta al resto, así ningún cuarto queda atrapado detrás de él. **El cuarto final de una mazmorra normal solo se abre cuando todos los demás cuartos están limpios; la mazmorra se completa al resolver la decisión en ese cuarto.** Mientras tanto, todas las puertas que llevan al final (pueden ser dos por el ciclo) quedan selladas — dorado oscuro con una X, distinto de la puerta roja por enemigos — y al tocarlas aparece "Limpia todos los cuartos primero" (2 s); al limpiar el último pendiente aparece "Cuarto final desbloqueado" (2 s). Un cuarto nunca visitado cuenta como pendiente. HUD: "Cuartos limpios: X/N". La decisión solo puede iniciarse con el sello cumplido y `Partida.cerrar_mazmorra` aplica el resultado una sola vez por mazmorra. Cada cuarto se genera al entrar por primera vez con `nivel_a_dificultad(toxicidad_local)`; los limpiados quedan limpios. Propagación: cada 15 s en un cuarto con enemigos vivos, BFS desde ahí y cada cuarto aún no generado a distancia d suma 10/d de toxicidad (tope 100). Minimapa con la tecla M (`src/ui/mapa_render.py`): color por toxicidad, pendientes (oscuros) vs limpios, cuarto actual, el final con candado mientras está sellado y estrella al desbloquearse, y la ruta BFS al final.

## Minijuego de decisión (fin de cada mazmorra normal)

Al matar a todos los monstruos del **cuarto final** de una mazmorra **normal** (no en los cuartos intermedios ni en la mazmorra final), aparece un minijuego de decisión contra reloj: una situación de redes sociales (ej. publicación de desinformación) y el jugador debe decidir qué hacer — reportar, ignorar, u otra opción según la situación. Esto SÍ es una interfaz que el jugador navega activamente, gobernada por el árbol N-ario:

Árbol actual (`construir_arbol_publicacion()` en `src/ui/terminal_decision.py`): raíz "Publicación Viral" → Verificar / Compartir / Reportar / Ignorar → cada opción lleva directo a su hoja: Verificar y Reportar → Purificación Exitosa; Compartir e Ignorar → Detonación. Contra reloj (10 s); si se acaba el tiempo, Detonación. (Un nivel intermedio tipo "Contrastar con fuente oficial / Creer rumor" es idea de diseño, no está implementado.)

Purificación Exitosa resta Colapso Electoral; Detonación (o no decidir a tiempo) lo suma. Al resolverse, se ajustan los pesos de las calles de esa zona y se vuelve al mapa de la ciudad.

**Regla de desbloqueo:** una mazmorra normal cuenta como *completada* SOLO si su decisión termina en Purificación Exitosa. Una Detonación suma colapso pero no cuenta como completada (`src/dungeon/progreso.py`).

## Mazmorra final (boss): solo combate, sin decisiones

La mazmorra final tiene el nivel de toxicidad más alto del juego y es deliberadamente **frenética** (lo más parecido a bullet hell que el tiempo permita) para enganchar al jugador. **No hay ningún minijuego de decisión aquí** — se gana únicamente peleando. Es el cierre de la demo en la Feria.

Como está implementada: jefe "Servidor Central" en un solo cuarto grande, con 3 fases según su vida (>60%, >30%, resto), escudo de anonimato en fase 2 (15 impactos; el Fact-Checking lo rompe de golpe), charcos tóxicos en fase 3 y límite de 180 s.

**Regla de diseño: TODO patrón del jefe, en las 3 fases, debe ser esquivable** (lo verifica `tests/test_jefe_esquivable.py`: siempre queda un pasillo de al menos 3 anchos de jugador en radios 120/180/240 px).
* Fase 1: ráfaga radial de 16 posiciones con un hueco de 3 balas consecutivas; el hueco salta a más de 60° del anterior y evita apuntar contra un muro cercano. Invoca súbditos.
* Fase 2: espiral de 2 brazos que gira lento (50°/s), con balas a la velocidad de la fase 1, + disparo dirigido.
* Fase 3: ciclo de 8 s en vez de todo junto: ráfagas con hueco en 0 y 1.2 s, espiral de 4.0 a 6.5 s y 1.5 s de descanso sin ataques (ventana para castigar). El disparo dirigido nunca sale junto a una ráfaga (espera 0.8 s). Charcos: uno cada 6 s, máximo 2 vivos, nunca a menos de 90 px del jugador ni sobre el jefe.
* Nunca hay más de `MAX_PROYECTILES_JEFE` = 40 balas del jefe vivas: con el tope lleno omite emitir.
* Todas estas constantes viven en `balance.py`. Tiempo agotado o jugador muerto → derrota: suma colapso y la pelea se reinicia. Jefe muerto → resta colapso y pantalla de victoria: ENTER vuelve al mapa de la ciudad (colapso y progreso se conservan), ESC cierra el juego.

**Regla de desbloqueo:** se entra eligiendo la Alcaldía en el mapa de la ciudad, solo si el colapso es mayor a 80% o si hay al menos 1 mazmorra completada (con Purificación Exitosa). Si no, se muestra "Alcaldía: Bloqueada" y no se viaja.

## Enemigos: agresividad absoluta
Los enemigos nunca se quedan quietos ni huyen: con `agro_permanente = True` (por defecto, en los cuartos normales y en los súbditos del jefe) el nodo de detección del behavior tree siempre tiene éxito y persiguen y disparan desde cualquier distancia. `RANGO_DISPARO_ENEMIGO` se conserva para el caso `agro_permanente = False`.

## Colapso Electoral
Barra 0.0%-100.0%: +0.2 por cada fallo (Detonación o derrota contra el jefe), -0.1 por cada éxito (Purificación Exitosa o jefe derrotado), y +0.02 por unidad de costo de cada viaje por la ciudad. **Derrota global:** si llega a 100% (en cualquier escena), la escena DERROTA muestra "Colapso total" con el input de combate desactivado; ENTER reinicia la partida completa (colapso 0, progreso 0, ubicación en la Plaza, pesos de la ciudad restablecidos, mismo rol) y ESC sale.

## Menú de inicio

1. **Modo**: "1 jugador" o "2 jugadores" (← → o 1-2, Enter; también cruceta y ✕ del control). Elegir 2 sin control conectado muestra "Conecta un control de PS4 para jugar de a dos" y espera; el control se detecta al conectarlo (también a mitad de partida si se desconecta).
2. **Roles**: cada jugador tiene su cursor sobre las 4 tarjetas (chip "J1"/"J2" del color del rol, ✓ al confirmar, la tarjeta elegida se tiñe). J1: A/D o flechas, Enter o Espacio confirma, 1-4 elige directo, Retroceso para cambiar. J2: cruceta o stick, ✕ confirma, ○ para cambiar. Pueden repetir rol. La partida empieza cuando todos confirmaron; Esc vuelve a la pantalla de modo.
Lógica pura en `src/ui/seleccion.py` (`SelectorModo`, `CursorRol`, `SeleccionRoles`); dibujo en `src/ui/pantalla_modo.py` y `src/ui/seleccion_rol.py`.

## Controles

* WASD o flechas: mover. El movimiento tiene inercia: la velocidad real se acerca a la pedida con un suavizado exponencial (`ACELERACION_MOVIMIENTO` = 16/s al caminar, `FRENADO_MOVIMIENTO` = 22/s al soltar, en `balance.py`) y el avance de cada frame es la integral exacta, así se siente igual a cualquier framerate. La posición se guarda en float y no se redondea entre frames (solo al chocar con un muro, que además anula la velocidad en ese eje). El loop usa `reloj.tick_busy_loop(FPS)`: en Windows `tick()` da frames irregulares (16/17/18 ms) que se ven como tirones.
* Mouse: apuntar (Ciudadano, Influencer y Periodista). En combate el cursor del sistema se oculta y se dibuja una mira con una línea tenue desde el jugador (`MOSTRAR_LINEA_APUNTADO` en `balance.py`). El Candidato no usa el mouse: cursor normal, sin mira.
* SPACE o click izquierdo (mantenidos): disparar (`CLICK_DISPARA` en `balance.py`). Mismo cooldown y cadencia con cualquiera de los dos.
* F: habilidad. Shift: dash. M: minimapa.
* ENTER y flechas: menús, mapa de la ciudad y terminal de decisión.
* J2 (control de PS4, cooperativo): stick izquierdo mover, stick derecho apuntar, R2 disparar, L1 habilidad, ✕ (Cruz) dash. Se lee con `pygame._sdl2.controller` (API GameController de SDL), que normaliza el mapeo entre drivers; los índices crudos de `pygame.joystick` cambian según el sistema.

**Regla de input:** el combate no usa eventos sino el estado de cada frame. `src/core/entrada.py` convierte teclado+mouse (`EntradaTeclado`) o el control (`EntradaMando`) en un `InputJugador` (movimiento, punto o dirección de apuntado, disparando, y los pulsos habilidad/dash, True solo el frame en que se aprieta), y `JugadorBase.manejar_input()` lo aplica igual para cualquier jugador.

**Regla de apuntado:** la dirección de disparo siempre sale de `direccion_mirada`. En los roles con `apunta_con_mouse = True` solo la actualiza `apuntar_a()`; el Candidato (`apunta_con_mouse = False`) la actualiza al caminar porque su ataque es radial y su habilidad sale hacia donde camina. Los roles nunca calculan su propia dirección. La cuenta vive en `src/core/apuntado.py` (pura; zona muerta `ZONA_MUERTA_APUNTADO` = 6 px) y `Main.py` le resta al mouse la sacudida de pantalla antes de apuntar.

## Los 4 roles jugables
Influencer, Periodista, Ciudadano, Candidato — los 4 están implementados y se eligen con las teclas 1-4 al empezar. Cada uno: ataque básico con disparo sostenido (SPACE o click izquierdo mantenidos, limitado por la cadencia del rol) + habilidad activa (F) que **se carga matando enemigos dentro de la mazmorra** (no por temporizador) — una barra de carga que se llena con kills y se gasta completa al usar la habilidad. Sinergia: Influencer agrupa, Periodista expone, Candidato remata, Ciudadano sostiene.

* Influencer: proyectil ancho que empuja al enemigo golpeado / Live Stream Viral (fija el aggro de todos los enemigos vivos del cuarto hacia él durante 3 s)
* Periodista: rayo perforante lineal / Fact-Checking (rayo perforante que quita el escudo de anonimato de cada enemigo que cruza; al jefe se lo rompe de golpe)
* Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (diseño: domo que frena proyectiles hostiles y regenera vida de aliados dentro; hoy solo se activa como flag con duración de 4 s y radio dibujado, sin frenar proyectiles ni curar)
* Candidato: onda expansiva radial / Debate Rebotante (3 proyectiles que rebotan en las paredes hasta 3 rebotes o 4 s)

Clase base común: `JugadorBase` en `src/entities/player.py`; cada rol solo sobreescribe `ataque_basico()` y `usar_habilidad()` (y el Candidato, además, `apunta_con_mouse = False`).

**Dash (los 4 roles por igual):** Shift (J1) o ✕ (J2), solo en combate. Va en la dirección de movimiento (quieto: hacia donde mira), con la dirección fijada al iniciarlo. Constantes en `balance.py`: `DASH_VELOCIDAD_MULT` = 4.0 sobre la velocidad del rol, `DASH_DURACION` = 0.12 s, `DASH_COOLDOWN` = 5.0 s (cuenta desde el inicio), `DASH_INVULNERABLE` = True. Durante el dash no se dispara (el acumulador de disparo queda en pausa), no se usa la habilidad y ningún golpe entra ni abre la ventana de i-frames (al terminar tampoco se abren: el dash no cuenta como golpe). No atraviesa muros (mismo clamp que el movimiento). Lógica pura en `src/entities/dash.py`, que también expone `fraccion_cooldown` (1 = recién usado, 0 = listo) y `tiempo_listo` (segundos desde que volvió a estar disponible) para el HUD. Visual: rastro de partículas del color del rol (`src/ui/particulas.py`, solo dibujo, sin hitbox) y 3 imágenes fantasma con alfa decreciente; constantes visuales en `assets.py`.

**Invulnerabilidad tras un golpe (i-frames):** al recibir daño, el jugador queda invulnerable `INVULNERABILIDAD_DURACION` = 0.6 s (en `balance.py`) y su sprite parpadea cada 0.08 s. Vale para los 4 roles, en el cuarto normal y en la arena del jefe. No se acumula: un golpe durante la ventana no la reinicia. Los charcos tóxicos respetan la ventana (no dañan durante ella) pero su daño continuo no la abre.

## Cooperativo local (2 jugadores, misma pantalla)

No es red: J1 con teclado+mouse y J2 con control de PS4, en el mismo equipo. Se activa eligiendo "2 jugadores" en el menú de inicio (ver arriba); con "1 jugador" el juego es el de siempre.
* Comparten cuarto, enemigos, colapso y carga de equipo (`registrar_kill_equipo`). Cada jugador tiene su propia lista de proyectiles para acreditar cada kill a quien la hizo.
* Cada enemigo, súbdito y el jefe apuntan al jugador en pie más cercano (`equipo.jugador_mas_cercano`). Los charcos dañan a cada jugador que pise uno.
* Al tocar una puerta abierta cualquiera de los dos, pasa todo el equipo, en fila junto a la puerta opuesta. Al entrar a una mazmorra se cura a ambos.
* Un jugador sin vida queda **caído** (no se mueve, no dispara, no se dibuja, los enemigos lo ignoran) mientras el otro siga en pie, y revive con `VIDA_AL_REVIVIR` = 1 al pasar al siguiente cuarto. En la arena del jefe la derrota llega solo si caen ambos. Si caen los dos en una mazmorra normal, se comporta como en solitario.
* J1 maneja la terminal de decisión y tiene la mira del mouse; J2 tiene una flechita de apuntado del color de su rol.
* **HUD en cooperativo:** paneles laterales verticales en los márgenes del cuarto (J1 a la izquierda, J2 a la derecha; `hud.dibujar_panel_jugador`). Cada uno: "J1"/"J2" y rol en su color (o "CAÍDO"), corazones, carga de la habilidad (F / L1), indicador del dash y controles clave (J1: SPACE Disparar · Mouse Apuntar · SHIFT Dash; J2: R2 Disparar · Stick R Apuntar · ✕ Dash). Arriba queda solo el lugar, los enemigos y el colapso. Con 1 jugador el HUD superior es el de siempre, sin paneles.
* **Indicador del dash** (`hud.dibujar_indicador_dash`, solo dibujo, lee `jugador.dash`): círculo con un muñeco corriendo. Listo: a todo color con un aura neón suave del color del rol. Recargando: icono al 50% de brillo y el círculo se llena desde abajo con una ola (seno que se desplaza). Al quedar disponible: destello blanco de 0.15 s. Constantes (radio, ola, aura, destello) en `assets.py`.
* Reglas puras en `src/core/equipo.py` (`jugadores_en_combate`, `jugador_mas_cercano`, `todos_caidos`, `revivir_caidos`). Los escenarios (`Cuarto`, `MazmorraJugable`, `ArenaJefe`, `MazmorraFinal`) reciben la lista `jugadores`.

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
│   │-- core/          # constantes, balance, configuración de pantalla, reloj, escenas, apuntado, input por jugador, reglas de equipo
│   │-- structures/     # árbol N-ario, grafo y min-heap puros, sin dependencias de Pygame
│   │-- ai/             # behavior tree genérico, sin dependencias de Pygame
│   │-- entities/       # jugadores (roles), dash, proyectiles, enemigos, jefe
│   │-- dungeon/        # cuartos, mazmorra multi-cuarto, grafo de la ciudad, partida, clasificador, mazmorra final
│   │-- ui/             # minijuego de decisión, menú de inicio (modo y roles), mapa de ciudad, minimapa, victoria/derrota, HUD, partículas
│   └-- network/        # (aún no existe) protocolo sockets, serialización, server/client
```
No mezclar responsabilidades entre carpetas. `structures/` y `ai/` no deben importar `pygame`. La lógica de jefe, charcos, mazmorra final, invulnerabilidad, dash, reglas de equipo, progreso, balance, terminal de decisión, mazmorra multi-cuarto, grafo de la ciudad, partida, escenas, selector del mapa y menú de inicio también es pura (sin `pygame`) para poder probarse en aislado; su dibujo vive en módulos aparte.

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
17. Mapa de la ciudad con Dijkstra, costo de viaje en colapso y pesos dinámicos (`src/dungeon/grafo_ciudad.py`, escena MAPA_CIUDAD, `src/ui/mapa_ciudad*.py`); reemplaza la tecla B — completado
18. Minimapa de la mazmorra con la tecla M (`src/ui/mapa_render.py`) — completado
19. Apuntado con mouse para Ciudadano, Influencer y Periodista (`src/core/apuntado.py`, `JugadorBase.apuntar_a`, mira en `Main.py`) y click izquierdo como segundo gatillo; el Candidato sigue apuntando al caminar — completado
20. Sello del cuarto final: solo se entra con todos los demás cuartos limpios (también por el ciclo), el final nunca es punto de corte y la decisión cierra la mazmorra una sola vez — completado
21. Jefe esquivable (ráfaga con hueco, espiral lenta, fase 3 por ciclos con descanso, tope de 40 balas, charcos justos) y agresividad absoluta de enemigos y súbditos (`agro_permanente`) — completado
22. Dash con invulnerabilidad corta para los 4 roles (`src/entities/dash.py`, Shift / ✕) — completado
23. Rastro de partículas e imágenes fantasma del dash (`src/ui/particulas.py`) — completado
24. Cooperativo local de 2 jugadores con control de PS4 (`src/core/entrada.py`, reglas en `src/core/equipo.py`, panel del J2) — completado; probado con control simulado, falta probarlo con un DualShock 4 real
25. Movimiento fluido: inercia con integración exacta, posición sin redondeo entre frames y frames regulares con `tick_busy_loop` — completado
26. Menú de inicio: pantalla de 1 o 2 jugadores y selección de rol simultánea con un cursor por jugador (`src/ui/seleccion.py`, `src/ui/pantalla_modo.py`) — completado
27. Paneles laterales de HUD en cooperativo con indicador animado del cooldown del dash (aura, ola, destello) y dash con cooldown de 5 s — completado

No agregues código de Ciudad Nova como mundo abierto caminable (la ciudad hoy es solo el mapa de selección) ni sockets / `src/network/` salvo que se te pida explícitamente — son alcance de entregas futuras.

## Convenciones de código

* Un módulo, una responsabilidad.
* Priorizar código explicable sobre código optimizado en exceso — se sustenta en voz alta ante la profesora.
* Todo árbol/grafo debe exponer sus operaciones de forma que se puedan probar de forma aislada (sin Pygame).
* Todo elemento visual debe referenciar una constante o ruta de sprite centralizada en `src/core/assets.py`, nunca un color hardcodeado disperso. Los números de balance (stats de roles, jefe, charcos, invulnerabilidad) van en `src/core/balance.py`.
* Placeholders (rectángulos de color) intencionales mientras se valida la mecánica; el arte real solo reemplaza la ruta del sprite, sin tocar lógica.

## Instrucciones de Git

* Al hacer commits, NO incluyas la línea "Co-Authored-By: Claude" ni ninguna línea de atribución a Claude/Anthropic.
* No modifiques `git config user.name` ni `user.email` del repo bajo ninguna circunstancia.

## Fechas relevantes

* Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
* Entrega 2 (grafos): 20-30 oct 2026
* Entrega Final (integración + red): 16-20 nov 2026
* Feria Gamer: 26 nov 2026