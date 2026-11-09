# Civitas

Action-RPG top-down cooperativo hecho en Python para el curso **Estructura de Datos II**
(Ingeniería de Sistemas, Universidad del Norte). Demo en vivo en la VI Feria Gamer
(26 nov 2026).

Recorres **Ciudad Nova** y entras a mazmorras cuya toxicidad viene del mal uso de las
redes sociales: limpias cuartos a disparos, reúnes pruebas y, en el cuarto final,
decides contra reloj qué hacer con una publicación viral. Al final te espera el jefe
**Servidor Central** en la Alcaldía.

Las estructuras de datos están hechas a mano y cada una gobierna una mecánica real:

| Estructura | Dónde | Qué mecánica gobierna |
|---|---|---|
| Árbol N-ario | `src/structures/tree.py` | Terminal de decisión del cuarto final |
| Grafo + Dijkstra | `src/structures/graph.py`, `src/dungeon/grafo_ciudad.py` | Calles de Ciudad Nova (ruta sugerida, barricadas) |
| Grafo + BFS/DFS | `src/dungeon/mazmorra.py` | Cuartos de cada mazmorra, cuarto final, propagación de toxicidad |
| Min-heap | `src/structures/min_heap.py` | Cola de prioridad de Dijkstra |
| Behavior tree | `src/ai/behavior_tree.py` | IA de cada tipo de enemigo |

## Instalación

Requiere Python 3.14.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

## Ejecutar

```bash
python Main.py
```

Pruebas y recorrido completo de la campaña sin ventana:

```bash
python -m pytest -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/recorrido_campania.py
```

## Controles

| Acción | Teclado y ratón (J1) | Control PS4 (J2, cooperativo) |
|---|---|---|
| Mover | WASD o flechas | Stick izquierdo |
| Apuntar | Ratón (el Candidato apunta al caminar) | Stick derecho |
| Disparar | Espacio o clic izquierdo, mantenidos | R2 |
| Habilidad (se carga con kills) | F | L1 |
| Dash | Shift | ✕ |
| Minimapa (mazmorra) | M | — |
| Entrar a un edificio | E | — |
| Ruta sugerida / cambiar destino | G / TAB | — |
| Mapa del mundo (ciudad) | M | — |
| Menús y terminal de decisión | Flechas y Enter | Cruceta y ✕ |
| Volver al menú principal (ciudad) | Esc | — |

## Estructura

```text
Main.py          # punto de entrada: menú principal y máquina de estados de escena
src/
  core/          # constantes visuales (assets.py), balance, escenas, entrada, audio, preferencias
  structures/    # árbol N-ario, grafo y min-heap (puros, sin pygame)
  ai/            # behavior tree y nodos de combate (puros)
  entities/      # roles, proyectiles, enemigos y sus variantes, jefe
  dungeon/       # cuartos, mazmorras, Ciudad Nova y su grafo de calles, partida
  story/         # modo historia «Código Nova» (lógica pura)
  ui/            # todo el dibujo: menús, HUD, terminal, mapas, cinemáticas
Online/          # modo en red (lobby, sala, impostor); ver Online/README.md
content/         # campaign.json: textos y datos de la campaña
assets/          # fuentes, música, sonidos, sprites y cuadros de video
tools/           # producción de contenido y QA (audio, video, retratos, recorrido)
tests/           # suite de pytest
docs/            # arquitectura, dirección de arte, guía de sustentación, QA, capturas
prompts/         # encargos para el asistente de código
```

Documentación detallada: `docs/ARQUITECTURA.md` (código), `docs/MODO_HISTORIA.md`
(campaña), `docs/GUIA_SUSTENTACION.md` (exposición) y `CLAUDE.md` (reglas del proyecto).
