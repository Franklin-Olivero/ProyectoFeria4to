# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto

* Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
* Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
* Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
* Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego

Civitas es un action-RPG top-down **cooperativo, de 1 a 4 jugadores** (soporta solitario, online más adelante). Inspirado en *The Binding of Isaac*: el jugador recorre una ciudad y entra a distintas mazmorras repartidas por ella.

Cada mazmorra tiene un **nivel de toxicidad por mal uso de redes** propio de su contexto (ciberbullying, acoso, desinformación posteada, etc.) — ese nivel determina su dificultad (más/menos enemigos, más/menos agresivos). Dentro de la mazmorra: cuartos con enemigos que el jugador limpia con sus poderes, al estilo Isaac.

## Minijuego de decisión (fin de cada mazmorra normal)

Al matar a todos los monstruos de una mazmorra **normal** (no la final), aparece un minijuego de decisión contra reloj: una situación de redes sociales (ej. publicación de desinformación) y el jugador debe decidir qué hacer — reportar, ignorar, u otra opción según la situación. Esto SÍ es una interfaz que el jugador navega activamente, gobernada por el árbol N-ario:

Raíz "Publicación Viral" → Verificar / Compartir / Reportar / Ignorar → Contrastar con fuente oficial / Creer rumor → Purificación Exitosa / Detonación. Contra reloj (10s).

Completar mazmorras así resta Colapso Electoral; fallar o no decidir a tiempo lo suma.

## Mazmorra final (boss): solo combate, sin decisiones

La mazmorra final tiene el nivel de toxicidad más alto del juego y es deliberadamente **frenética** (lo más parecido a bullet hell que el tiempo permita) para enganchar al jugador. **No hay ningún minijuego de decisión aquí** — se gana únicamente peleando con las habilidades de los 4 roles. Es el cierre de la demo en la Feria.

## Colapso Electoral
Barra 0.0%-100.0%. Sube con mazmorras fallidas/decisiones incorrectas, baja con mazmorras purificadas. Si llega a 100%, el jugador pierde y reinicia.

## Los 4 roles jugables
Influencer, Periodista, Ciudadano, Candidato. Cada uno: ataque básico + habilidad activa que **se carga matando enemigos dentro de la mazmorra** (no por temporizador) — una barra de carga que se llena con kills y se gasta al usar la habilidad. Sinergia: Influencer agrupa, Periodista expone, Candidato remata, Ciudadano sostiene.

* Influencer: cono de sonido expansivo (empuja) / Live Stream Viral (fija aggro de todos los enemigos del cuarto hacia él por unos segundos)
* Periodista: rayo perforante lineal / Fact-Checking (destruye escudos de anonimato de enemigos atrapados)
* Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (domo que frena proyectiles hostiles y regenera vida de aliados dentro)
* Candidato: onda expansiva radial / Debate Rebotante (proyectiles que rebotan en paredes)

MVP actual solo implementa Ciudadano; los otros 3 son visión futura, no crear código placeholder para ellos todavía.

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
│-- main.py
│-- requirements.txt
│-- assets/
│-- src/
│   │-- core/          # constantes, configuración de pantalla, reloj
│   │-- structures/     # árboles y grafos puros, sin dependencias de Pygame
│   │-- entities/       # jugadores (roles), proyectiles, enemigos
│   │-- dungeon/        # cuartos, puertas, spawners, clasificador de toxicidad
│   │-- ui/             # HUD de colapso, minijuego de decisión, pantallas de carga
│   └-- network/        # protocolo sockets, serialización, server/client
```
No mezclar responsabilidades entre carpetas. `structures/` no debe importar `pygame`.

## Estado real del MVP

1. `tree.py` con CRUD/recorridos — completado
2. Cuarto con puertas bloqueables y spawn placeholder — completado
3. Behavior tree (Selector→Sequence) + Ciudadano + proyectiles — completado
4. `docs/ARQUITECTURA.md` — completado
5. Clasificador de toxicidad (`src/dungeon/clasificador_toxicidad.py`) conectado al spawn del cuarto — completado
6. Variable de colapso en pantalla (`src/core/colapso.py`) — completado
7. Minijuego de decisión (Verificar/Compartir/Reportar/Ignorar) al final de mazmorra normal, usando `tree.py` como segunda estructura — completado
8. Carga de habilidad por kills (reemplaza cooldown por tiempo) — completado
9. Mazmorra final frenética sin decisiones (jefe "Servidor Central": `src/entities/jefe.py`, `src/dungeon/mazmorra_final.py`, `src/dungeon/arena_jefe.py`, `src/dungeon/charco.py`; se entra con B si está desbloqueada) — completado

No agregues código de Ciudad Nova, sockets ni `graph.py` salvo que se te pida explícitamente — son alcance de entregas futuras.

## Convenciones de código

* Un módulo, una responsabilidad.
* Priorizar código explicable sobre código optimizado en exceso — se sustenta en voz alta ante la profesora.
* Todo árbol/grafo debe exponer sus operaciones de forma que se puedan probar de forma aislada (sin Pygame).
* Todo elemento visual debe referenciar una constante o ruta de sprite centralizada en `src/core/assets.py`, nunca un color hardcodeado disperso.
* Placeholders (rectángulos de color) intencionales mientras se valida la mecánica; el arte real solo reemplaza la ruta del sprite, sin tocar lógica.

## Instrucciones de Git

* Al hacer commits, NO incluyas la línea "Co-Authored-By: Claude" ni ninguna línea de atribución a Claude/Anthropic.
* No modifiques `git config user.name` ni `user.email` del repo bajo ninguna circunstancia.

## Fechas relevantes

* Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
* Entrega 2 (grafos): 20-30 oct 2026
* Entrega Final (integración + red): 16-20 nov 2026
* Feria Gamer: 26 nov 2026