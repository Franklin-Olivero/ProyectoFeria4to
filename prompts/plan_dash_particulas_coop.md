# Plan de implementación: Dash, Partículas y Cooperativo Local

## Resumen

Tres features nuevas para Civitas:
1. **Dash** — desplazamiento rápido con invulnerabilidad corta, tecla `SHIFT` (teclado) / `X` (PS4).
2. **Aura / partículas al hacer dash** — trail de partículas con el color del rol que se desvanecen.
3. **Cooperativo local 2 jugadores** — J1 con teclado+mouse, J2 con control de PS4.

---

## Feature 1 — Dash

### Diseño

| Constante | Valor | Lugar |
|---|---|---|
| `DASH_VELOCIDAD_MULT` | `4.0` | `balance.py` — multiplicador sobre la velocidad del rol |
| `DASH_DURACION` | `0.12` s | `balance.py` — tiempo que dura el desplazamiento |
| `DASH_COOLDOWN` | `0.8` s | `balance.py` — tiempo entre dashes |
| `DASH_INVULNERABLE` | `True` | `balance.py` — el jugador es invulnerable durante el dash |

- El dash va **en la dirección de movimiento actual** (WASD/stick izquierdo). Si el jugador está quieto, va en `direccion_mirada`.
- Durante el dash el jugador **no puede disparar ni usar habilidad** (el disparo sostenido se pausa).
- El dash **no atraviesa muros**: el movimiento se clampea al `limites` del cuarto igual que el movimiento normal.
- Cada rol comparte las mismas constantes de dash (no hay dash más largo para el Influencer, etc.) — la diferencia natural sale de que cada rol tiene distinta `velocidad_mult`.

### Implementación

1. **`src/core/balance.py`** — agregar las 4 constantes arriba.

2. **`src/entities/dash.py`** (nuevo, **sin Pygame**) — clase pura `Dash`:
   ```python
   class Dash:
       def __init__(self):
           self.activo = False        # True durante el desplazamiento
           self.cooldown_restante = 0  # segundos hasta el próximo dash
           self.tiempo_restante = 0    # segundos que le quedan al dash actual
           self.direccion = (0, 0)     # dirección fijada al iniciar

       def iniciar(self, direccion) -> bool:
           """Inicia un dash si el cooldown lo permite. Retorna True/False."""

       def actualizar(self, dt):
           """Descuenta timers. Cuando tiempo_restante llega a 0, activo = False."""

       @property
       def velocidad_multiplicador(self) -> float:
           """DASH_VELOCIDAD_MULT si activo, 1.0 si no."""

       @property
       def puede_disparar(self) -> bool:
           """False mientras el dash está activo."""
   ```
   - Lógica pura, sin importar `pygame`. Testeable en aislado.

3. **`src/entities/player.py`** — `JugadorBase`:
   - Agregar `self.dash = Dash()` en `__init__`.
   - En `manejar_movimiento()`: si `self.dash.activo`, mover con `self.velocidad * self.dash.velocidad_multiplicador * dt` en `self.dash.direccion` (la dirección fijada al iniciar, no la del input actual). El clamp al `limites` se conserva.
   - Agregar `def iniciar_dash(self)` que calcula la dirección (input actual o `direccion_mirada`) y llama `self.dash.iniciar(dir)`.
   - En `actualizar_disparo()`: si `not self.dash.puede_disparar`, no disparar (retornar lista vacía sin avanzar el cooldown de disparo).
   - Llamar `self.dash.actualizar(dt)` desde `manejar_movimiento()` o desde Main.
   - Durante el dash, si `DASH_INVULNERABLE`, tratar como invulnerable (la ventana de invulnerabilidad existente puede solaparse; no se reinicia).

4. **`Main.py`**:
   - Capturar `LSHIFT` en el loop de eventos → `jugador.iniciar_dash()` (y lo mismo para J2 con el botón del joystick).
   - La invulnerabilidad del dash se maneja dentro de `Dash` / `JugadorBase`: si `dash.activo and DASH_INVULNERABLE`, `recibir_dano` no aplica daño (igual que los i-frames actuales).

### Qué NO hacer
- No agregar stats de dash distintas por rol. Todos dashean igual.
- No permitir dash fuera de combate (escenas `MAZMORRA` y `JEFE` solamente).

---

## Feature 2 — Aura / Partículas al hacer dash

### Diseño

- Al iniciar el dash y durante su duración, se emiten **partículas** tipo trail que se desvanecen.
- Cada partícula: posición donde estaba el jugador, color del rol (con alfa decreciente), radio que encoge hasta desaparecer.
- Las partículas son **solo visuales** (no tienen hitbox ni afectan gameplay).
- Además del trail, una **imagen fantasma** (afterimage) semitransparente del sprite del jugador se dibuja en las posiciones anteriores (2-3 imágenes, cada vez más tenues).

### Implementación

1. **`src/core/assets.py`** — agregar constantes visuales:
   ```python
   # Dash: partículas y afterimages
   DASH_PARTICULAS_POR_FRAME = 3       # partículas emitidas por frame durante el dash
   DASH_PARTICULA_RADIO = 6            # radio inicial de cada partícula
   DASH_PARTICULA_DURACION = 0.25      # s que vive cada partícula
   DASH_PARTICULA_ALFA_INICIAL = 180   # alfa 0-255
   DASH_AFTERIMAGES = 3                # cuántas imágenes fantasma dejar
   DASH_AFTERIMAGE_ALFA = (120, 70, 30)  # alfa de cada afterimage (de la más nueva a la más vieja)
   ```

2. **`src/ui/particulas.py`** (nuevo) — sistema de partículas ligero:
   ```python
   class Particula:
       """Un punto con posición, color, radio y vida que se encoge y desvanece."""

   class SistemaParticulas:
       """Pool de partículas activas. emitir() agrega, actualizar() descuenta
       vida y quita las muertas, dibujar() las pinta."""
   ```
   - Cada `Particula` guarda `x, y, color_base, radio, vida, vida_max`. En `dibujar()` calcula alfa = `ALFA_INICIAL * (vida / vida_max)` y radio = `RADIO * (vida / vida_max)`.
   - El sistema no toca lógica de juego. Es solo render.

3. **`src/entities/player.py`** — `JugadorBase.dibujar()`:
   - Si `self.dash.activo`, emitir partículas con `self.COLOR` en la posición actual.
   - Dibujar las afterimages: guardar las últimas N posiciones mientras el dash está activo; dibujar el sprite del jugador en cada una con alfa decreciente.

4. **`Main.py`**:
   - Crear un `SistemaParticulas` global (o uno por jugador).
   - En el loop de dibujo, llamar `sistema_particulas.actualizar(dt)` y `sistema_particulas.dibujar(lienzo)` justo después de dibujar al jugador.

---

## Feature 3 — Cooperativo local 2 jugadores

### Diseño

| Jugador | Movimiento | Apuntado | Disparar | Habilidad | Dash |
|---|---|---|---|---|---|
| J1 (teclado) | WASD | Mouse | SPACE / Click izq | F | LSHIFT |
| J2 (control PS4) | Stick izquierdo | Stick derecho | R2 (eje 5) | L1 (botón 4) | X (botón 0) |

- Cada jugador elige su rol de forma independiente (primero J1 con teclas 1-4, luego J2 con los botones △=1, ○=2, X=3, □=4 del control, o las mismas teclas 5-8 si hay un segundo teclado).
- Ambos jugadores comparten la misma pantalla, el mismo cuarto y los mismos enemigos. Mismo HUD arriba con la info de ambos.
- La carga compartida de equipo (`registrar_kill_equipo`) ya funciona con la lista `jugadores` — solo hay que meter al J2 ahí.
- Si un jugador muere, el otro sigue. Si ambos mueren, se aplica la lógica de derrota del cuarto/mazmorra.
- La curación al entrar a una mazmorra aplica a ambos jugadores.

### Mapeo de botones PS4 (pygame)

```python
# pygame usa SDL bajo el capó; con pygame-ce los controles PS4 se mapean así:
# Botón 0 = X (Cruz)         → Dash
# Botón 1 = ○ (Círculo)      → (libre)
# Botón 2 = □ (Cuadrado)     → (libre)
# Botón 3 = △ (Triángulo)    → (libre)
# Botón 4 = L1               → Habilidad
# Botón 5 = R1               → (libre)
# Eje 0 = Stick izquierdo X  → Movimiento horizontal
# Eje 1 = Stick izquierdo Y  → Movimiento vertical
# Eje 2 = Stick derecho X    → Apuntado horizontal
# Eje 3 = Stick derecho Y    → Apuntado vertical
# Eje 4 = L2 (gatillo)       → (libre)
# Eje 5 = R2 (gatillo)       → Disparar (valor > 0.5 = presionado)
```

> [!IMPORTANT]
> Verificar el mapeo exacto con `pygame.joystick` en runtime porque puede variar según el driver y el OS. Usar `pygame.JOYAXISMOTION`, `pygame.JOYBUTTONDOWN`, etc. Considerar usar `pygame.controller` (SDL GameController API) si `pygame-ce` lo soporta bien, porque normaliza los mapeos entre marcas.

### Implementación

1. **`src/core/input.py`** (nuevo, **sin Pygame en la lógica pura**) — abstracción de input por jugador:
   ```python
   @dataclass
   class InputJugador:
       """Estado del input de un jugador en un frame."""
       movimiento: tuple[float, float]  # dirección normalizada (-1..1, -1..1)
       apuntado: tuple[float, float] | None  # punto del mundo (mouse) o dirección (stick)
       disparando: bool
       habilidad: bool  # True el frame que se presiona
       dash: bool       # True el frame que se presiona

   def leer_input_teclado(teclas, mouse_pos, sacudida, apunta_con_mouse) -> InputJugador:
       """Lee WASD + mouse + SPACE/click + F + LSHIFT."""

   def leer_input_joystick(joystick, zona_muerta=0.15) -> InputJugador:
       """Lee sticks + R2 + L1 + X del control."""
   ```
   - Las funciones sí importan `pygame` (para `pygame.key.get_pressed`, `pygame.joystick`), pero la estructura `InputJugador` es pura.
   - `zona_muerta` para los sticks: si `|eje| < 0.15`, se trata como 0. El stick derecho se convierte en dirección de apuntado (como haría el mouse).

2. **`src/entities/player.py`** — `JugadorBase`:
   - Agregar `manejar_input(self, inp: InputJugador, dt, limites)` que unifica `manejar_movimiento`, `apuntar_a` e `iniciar_dash` para cualquier fuente de input:
     ```python
     def manejar_input(self, inp, dt, limites):
         # Movimiento
         if self.dash.activo:
             self._mover_dash(dt, limites)
         elif inp.movimiento != (0, 0):
             self._mover(inp.movimiento, dt, limites)
         # Apuntado
         if inp.apuntado is not None and self.apunta_con_mouse:
             self.apuntar_a(inp.apuntado)
         # Dash
         if inp.dash:
             self.iniciar_dash(inp.movimiento)
     ```
   - Los métodos viejos (`manejar_movimiento`, `apuntar_a`) **no se borran** — se conservan como helpers internos para no romper nada. `manejar_input` los llama.

3. **`Main.py`** — cambios principales:
   - **Detección de joystick al inicio**: después de `pygame.init()`, buscar `pygame.joystick.get_count()`. Si hay al menos 1 joystick, ofrecerle a J2 elegir rol.
   - **Selección de rol**:
     - Primero J1 elige con teclas 1-4 (ya existe).
     - Si hay joystick, J2 elige con los botones del control (△/○/X/□ → roles 1-4) o con teclas 5-8 (fallback).
     - Si no hay joystick, solo es 1 jugador (el flujo actual).
   - **Lista `jugadores`**:
     ```python
     jugadores = [jugador1]
     if jugador2 is not None:
         jugadores.append(jugador2)
     ```
   - **Loop de combate (`_frame_de_combate`)**:
     - Leer `InputJugador` para cada jugador y llamar `jugador.manejar_input(inp, dt, rect)`.
     - Cada jugador tiene sus propias listas de proyectiles → `proyectiles_j1`, `proyectiles_j2` (o una sola lista compartida; la compartida es más simple porque las colisiones ya iteran todos los proyectiles contra todos los enemigos).
     - Colisiones jugador ↔ proyectiles enemigos: iterar para cada jugador.
     - Invulnerabilidad, habilidades, disparo: ya están en `JugadorBase`, así que funciona por jugador.
   - **HUD**: mostrar la info de ambos jugadores: J1 a la izquierda, J2 a la derecha. El HUD actual ya tiene una posición fija para J1; para J2 se espeja o se agrega una segunda columna.
   - **Dibujo**: ambos jugadores se dibujan en el lienzo. La mira solo se dibuja para J1 (el del mouse); J2 puede tener un indicador de dirección de apuntado (una flechita sobre su sprite).
   - **Apuntado de J2 con stick derecho**: el stick derecho da una dirección `(x, y)` que se normaliza. Se convierte en `apuntar_a()` pasando un punto lejano en esa dirección desde el centro del jugador (ej. `centro + direccion * 1000`). Si los dos sticks están neutros, conserva la última dirección.
   - **Cuarto final / decisión**: en coop, la decisión la controla J1 (teclado, flechas+ENTER). J2 no interactúa con la terminal.
   - **Muerte**: si un jugador muere y el otro sigue vivo, el muerto puede revivir al pasar al siguiente cuarto (aparece con 1 de vida). Si ambos mueren en el mismo cuarto, es game over del cuarto (los enemigos se reinician como ahora).

4. **`src/ui/hud.py`** — agregar función `dibujar_hud_jugador2()`:
   - Corazones del J2 y barra de habilidad en la parte derecha del HUD.
   - Label "J2" con el color del rol de J2.

5. **`src/ui/seleccion_rol.py`** — pantalla de selección actualizada:
   - Después de que J1 elige, si hay joystick conectado, mostrar "J2: Elige tu personaje con el control" y esperar input del joystick.
   - Dibujar las mismas tarjetas pero con el mapeo de botones del control en vez de teclas 1-4.

### Diagrama de flujo del input

```
┌─────────────┐     ┌──────────────────┐
│ pygame keys │────▶│ leer_input_      │     ┌────────────────┐
│ pygame mouse│     │ teclado()        │────▶│ InputJugador   │──▶ jugador1.manejar_input()
└─────────────┘     └──────────────────┘     │ (movimiento,   │
                                             │  apuntado,     │
┌─────────────┐     ┌──────────────────┐     │  disparando,   │
│ pygame      │────▶│ leer_input_      │────▶│  habilidad,    │──▶ jugador2.manejar_input()
│ joystick    │     │ joystick()       │     │  dash)         │
└─────────────┘     └──────────────────┘     └────────────────┘
```

---

## Orden de implementación sugerido

1. **Dash** (`balance.py` → `dash.py` → `player.py` → `Main.py`) — ~2h
2. **Partículas** (`assets.py` → `particulas.py` → integrar en `player.py` y `Main.py`) — ~1.5h
3. **Input abstracto** (`input.py` → refactor de `player.py` y `Main.py` para usar `InputJugador`) — ~2h
4. **Cooperativo** (selección J2 → `Main.py` con 2 jugadores → HUD doble → colisiones dobles) — ~3h
5. **Pulido** (testear con control PS4 real, ajustar zona muerta, afterimages, HUD) — ~1.5h

---

## Archivos a crear

| Archivo | Responsabilidad |
|---|---|
| `src/entities/dash.py` | Lógica pura del dash (timers, estados) |
| `src/ui/particulas.py` | Sistema de partículas visual (emitir, actualizar, dibujar) |
| `src/core/input.py` | Abstracción de input: `InputJugador`, `leer_input_teclado`, `leer_input_joystick` |

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `src/core/balance.py` | Constantes de dash |
| `src/core/assets.py` | Constantes visuales de partículas y dash |
| `src/entities/player.py` | `Dash` en `JugadorBase`, `manejar_input()`, integrar partículas |
| `Main.py` | Detección joystick, selección J2, loop con 2 jugadores, HUD doble, input abstracto |
| `src/ui/hud.py` | Info de J2 en el HUD |
| `src/ui/seleccion_rol.py` | Pantalla de selección para J2 con control |

> [!WARNING]
> El mapeo de botones del control PS4 puede variar entre Windows, macOS y Linux. Se recomienda verificar con `pygame.joystick.Joystick(0).get_name()` y logear los ejes/botones al inicio para debug. Considerar un archivo `controles.json` configurable a futuro.

> [!NOTE]
> La regla del proyecto dice que `src/network/` y el multijugador online son alcance futuro. Esta implementación es **cooperativo local** en la misma pantalla, no red — no viola esa restricción.
