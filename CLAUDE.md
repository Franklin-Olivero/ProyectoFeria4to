# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto

* Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
* Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
* Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
* Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego

Civitas es un action-RPG top-down **cooperativo, de 1 a 4 jugadores** (soporta solitario, online más adelante). Inspirado en *The Binding of Isaac*: el jugador recorre una ciudad y entra a distintas mazmorras repartidas por ella. (Hoy: 1 jugador local, un cuarto normal y la mazmorra final; la ciudad recorrible y el multijugador son visión futura.)

Cada mazmorra tiene un **nivel de toxicidad por mal uso de redes** propio de su contexto (ciberbullying, acoso, desinformación posteada, etc.) — ese nivel determina su dificultad (más/menos enemigos, más/menos agresivos). Dentro de la mazmorra: cuartos con enemigos que el jugador limpia con sus poderes, al estilo Isaac.

## Minijuego de decisión (fin de cada mazmorra normal)

Al matar a todos los monstruos de una mazmorra **normal** (no la final), aparece un minijuego de decisión contra reloj: una situación de redes sociales (ej. publicación de desinformación) y el jugador debe decidir qué hacer — reportar, ignorar, u otra opción según la situación. Esto SÍ es una interfaz que el jugador navega activamente, gobernada por el árbol N-ario:

Árbol actual (`construir_arbol_publicacion()` en `src/ui/terminal_decision.py`): raíz "Publicación Viral" → Verificar / Compartir / Reportar / Ignorar → cada opción lleva directo a su hoja: Verificar y Reportar → Purificación Exitosa; Compartir e Ignorar → Detonación. Contra reloj (10 s); si se acaba el tiempo, Detonación. (Un nivel intermedio tipo "Contrastar con fuente oficial / Creer rumor" es idea de diseño, no está implementado.)

Purificación Exitosa resta Colapso Electoral; Detonación (o no decidir a tiempo) lo suma.

**Regla de desbloqueo:** una mazmorra normal cuenta como *completada* SOLO si su decisión termina en Purificación Exitosa. Una Detonación suma colapso pero no cuenta como completada (`src/dungeon/progreso.py`).

## Mazmorra final (boss): solo combate, sin decisiones

La mazmorra final tiene el nivel de toxicidad más alto del juego y es deliberadamente **frenética** (lo más parecido a bullet hell que el tiempo permita) para enganchar al jugador. **No hay ningún minijuego de decisión aquí** — se gana únicamente peleando. Es el cierre de la demo en la Feria.

Como está implementada: jefe "Servidor Central" en un solo cuarto grande, con 3 fases según su vida (>60%, >30%, resto), escudo de anonimato en fase 2 (15 impactos; el Fact-Checking lo rompe de golpe), charcos tóxicos en fase 3 y límite de 180 s. Tiempo agotado o jugador muerto → derrota: suma colapso y la pelea se reinicia. Jefe muerto → resta colapso y pantalla de victoria: ENTER vuelve a una mazmorra normal nueva (colapso y progreso se conservan), ESC cierra el juego.

**Regla de desbloqueo:** se entra con la tecla B desde la mazmorra normal, solo si el colapso es mayor a 80% o si hay al menos 1 mazmorra completada (con Purificación Exitosa). Si no, se muestra "Bloqueada".

## Colapso Electoral
Barra 0.0%-100.0%: +0.2 por cada fallo (Detonación o derrota contra el jefe), -0.1 por cada éxito (Purificación Exitosa o jefe derrotado). Diseño pendiente de implementar: si llega a 100%, el jugador pierde y reinicia (hoy la barra solo se acota en 100%).

## Los 4 roles jugables
Influencer, Periodista, Ciudadano, Candidato — los 4 están implementados y se eligen con las teclas 1-4 al empezar. Cada uno: ataque básico con disparo sostenido (SPACE mantenida, limitado por la cadencia del rol) + habilidad activa (F) que **se carga matando enemigos dentro de la mazmorra** (no por temporizador) — una barra de carga que se llena con kills y se gasta completa al usar la habilidad. Sinergia: Influencer agrupa, Periodista expone, Candidato remata, Ciudadano sostiene.

* Influencer: proyectil ancho que empuja al enemigo golpeado / Live Stream Viral (fija el aggro de todos los enemigos vivos del cuarto hacia él durante 3 s)
* Periodista: rayo perforante lineal / Fact-Checking (rayo perforante que quita el escudo de anonimato de cada enemigo que cruza; al jefe se lo rompe de golpe)
* Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (diseño: domo que frena proyectiles hostiles y regenera vida de aliados dentro; hoy solo se activa como flag con duración de 4 s y radio dibujado, sin frenar proyectiles ni curar)
* Candidato: onda expansiva radial / Debate Rebotante (3 proyectiles que rebotan en las paredes hasta 3 rebotes o 4 s)

Clase base común: `JugadorBase` en `src/entities/player.py`; cada rol solo sobreescribe `ataque_basico()` y `usar_habilidad()`.

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
│   │-- core/          # constantes, balance, configuración de pantalla, reloj
│   │-- structures/     # árboles y grafos puros, sin dependencias de Pygame
│   │-- ai/             # behavior tree genérico, sin dependencias de Pygame
│   │-- entities/       # jugadores (roles), proyectiles, enemigos, jefe
│   │-- dungeon/        # cuartos, puertas, spawners, clasificador de toxicidad, mazmorra final
│   │-- ui/             # minijuego de decisión, selección de rol, pantalla de victoria
│   └-- network/        # (aún no existe) protocolo sockets, serialización, server/client
```
No mezclar responsabilidades entre carpetas. `structures/` y `ai/` no deben importar `pygame`. La lógica de jefe, charcos, mazmorra final, invulnerabilidad, progreso, balance y terminal de decisión también es pura (sin `pygame`) para poder probarse en aislado; su dibujo vive en módulos aparte.

## Estado real del MVP

1. `tree.py` con CRUD/recorridos — completado
2. Cuarto con puertas bloqueables y spawn placeholder — completado
3. Behavior tree (Selector→Sequence) + jugador + proyectiles — completado
4. `docs/ARQUITECTURA.md` — completado
5. Clasificador de toxicidad (`src/dungeon/clasificador_toxicidad.py`) conectado al spawn del cuarto — completado
6. Variable de colapso en pantalla (`src/core/colapso.py`) — completado
7. Minijuego de decisión (Verificar/Compartir/Reportar/Ignorar) al final de mazmorra normal, usando `tree.py` como segunda estructura — completado
8. Carga de habilidad por kills (reemplaza cooldown por tiempo) — completado
9. Mazmorra final frenética sin decisiones (jefe "Servidor Central": `src/entities/jefe.py`, `src/dungeon/mazmorra_final.py`, `src/dungeon/arena_jefe.py`, `src/dungeon/charco.py`; se entra con B si está desbloqueada) — completado
10. Los 4 roles (Ciudadano, Influencer, Periodista, Candidato) sobre `JugadorBase`, con selección 1-4 — completado (la Burbuja Comunitaria del Ciudadano aún no frena proyectiles ni cura)
11. Balance por rol en `src/core/balance.py`, disparo sostenido y carga compartida de equipo — completado
12. Invulnerabilidad tras un golpe, pantalla de victoria (ENTER/ESC) y máquina de estados de escena en `Main.py` — completado
13. Derrota global al llegar el colapso a 100% — **pendiente**

No agregues código de Ciudad Nova, sockets ni `graph.py` salvo que se te pida explícitamente — son alcance de entregas futuras.

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