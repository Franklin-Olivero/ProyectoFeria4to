# Prompt — Civitas: Dash + Partículas + Cooperativo Local

Copia todo desde aquí hasta el final del documento.

---

## Contexto del proyecto

Civitas es un action-RPG top-down en Python 3 + `pygame-ce`. El jugador recorre mazmorras de varios cuartos limpiando enemigos, toma decisiones en el cuarto final de cada mazmorra y pelea contra un jefe final. Hoy solo soporta 1 jugador con teclado+mouse.

### Stack y reglas

- Python 3.14, `pygame-ce`, `venv`.
- Prohibido usar librerías de terceros para árboles o grafos.
- Separación estricta: lógica pura (sin `pygame`) en `src/structures/`, `src/ai/`, `src/entities/dash.py`, `src/core/equipo.py`, `src/core/entrada.py`. Dibujo en `src/ui/`.
- Todo color, tamaño y posición visual va en `src/core/assets.py`. Todo número de balance va en `src/core/balance.py`. Nunca hardcodear valores dispersos.
- El loop principal está en `Main.py`. Usa una máquina de estados (`Escena` en `src/core/escenas.py`): `MAPA_CIUDAD → MAZMORRA → DECISION → RESULTADO → MAPA_CIUDAD`, y `JEFE → VICTORIA`.
- Commits sin línea "Co-Authored-By". No modificar `git config`.

### Estructura de carpetas

```
PruebaPythonGame/
├── Main.py                          # loop principal, máquina de estados
├── src/
│   ├── core/
│   │   ├── assets.py                # paleta, fuentes, tamaños, layout
│   │   ├── balance.py               # stats de roles, jefe, constantes de gameplay
│   │   ├── config.py                # ANCHO=1280, ALTO=720, FPS=60
│   │   ├── colapso.py               # barra 0-100%
│   │   ├── equipo.py                # registrar_kill_equipo (carga compartida)
│   │   ├── escenas.py               # enum Escena, ESCENAS_DE_COMBATE
│   │   └── apuntado.py              # calcular_direccion_apuntado (pura)
│   ├── structures/                  # árbol N-ario, grafo, min-heap (sin pygame)
│   ├── ai/                          # behavior tree (sin pygame)
│   ├── entities/
│   │   ├── player.py                # JugadorBase + Ciudadano
│   │   ├── influencer.py            # Influencer + ProyectilEmpuje
│   │   ├── periodista.py            # Periodista + RayoPerforante
│   │   ├── candidato.py             # Candidato + OndaExpansiva + ProyectilRebotante
│   │   ├── invulnerabilidad.py      # ventana de i-frames (sin pygame)
│   │   ├── projectile.py            # Proyectil base
│   │   ├── enemy.py                 # Enemigo con behavior tree
│   │   └── jefe.py                  # Servidor Central (3 fases)
│   ├── dungeon/
│   │   ├── cuarto.py                # Cuarto con puertas y spawn
│   │   ├── mazmorra.py              # grafo de 6 cuartos (pura)
│   │   ├── mazmorra_jugable.py      # wrapper pygame de la mazmorra
│   │   ├── arena_jefe.py            # wrapper pygame de la arena
│   │   ├── mazmorra_final.py        # lógica del jefe final
│   │   ├── grafo_ciudad.py          # mapa de la ciudad (Dijkstra)
│   │   ├── partida.py               # estado global de la partida
│   │   ├── progreso.py              # mazmorras completadas
│   │   └── charco.py                # charcos tóxicos del jefe
│   └── ui/
│       ├── hud.py                   # HUD superior + barra de controles
│       ├── seleccion_rol.py         # pantalla de selección (dibujo)
│       ├── mapa_ciudad_render.py    # dibujo del mapa
│       ├── mapa_render.py           # minimapa de la mazmorra
│       ├── terminal_decision.py     # árbol N-ario del minijuego
│       ├── terminal_decision_render.py
│       ├── combate_render.py        # mira, cono, números de daño
│       ├── pantalla_victoria.py
│       ├── pantalla_derrota.py
│       ├── pantalla_resultado.py
│       ├── sprites.py               # sprites en pixel art (código)
│       ├── fuentes.py               # carga de fuentes
│       └── dibujo.py                # helpers: texto, panel, chip, barra
```

### Arquitectura clave del jugador actual

`JugadorBase` (en `src/entities/player.py`):
- Atributos: `rect`, `posicion` (Vector2 float), `vida`, `velocidad`, `danio`, `direccion_mirada`, `carga_habilidad`, `invulnerabilidad` (clase `Invulnerabilidad`).
- `manejar_movimiento(teclas, dt, limites)` — lee WASD/flechas directo de `pygame.key.get_pressed()`.
- `apuntar_a(punto_mouse)` — solo si `apunta_con_mouse = True`.
- `actualizar_disparo(dt, disparando)` — acumulador de cooldown, retorna lista de proyectiles nuevos.
- `usar_habilidad(enemigos, proyectiles_salida)` — se carga con kills, no con tiempo.
- `recibir_dano(danio, inicia_invulnerabilidad)` — respeta los i-frames.
- `dibujar(pantalla)` — dibuja el sprite con parpadeo de invulnerabilidad.
- Cada rol hereda y sobreescribe solo `ataque_basico()` y `usar_habilidad()`.
- Candidato tiene `apunta_con_mouse = False` (apunta hacia donde camina).

`Main.py` hoy:
- `_elegir_rol()` — loop que espera tecla 1-4, retorna clase del rol.
- `_frame_de_combate()` — un frame: movimiento, disparo, colisiones, todo para 1 solo jugador.
- `jugadores = [jugador]` — la lista ya existe pero solo tiene 1 elemento.
- `registrar_kill_equipo(asesino, jugadores)` — ya da carga compartida a los aliados.

`src/core/equipo.py` (ya existe, sin pygame):
- `registrar_kill_equipo(asesino, aliados)` — kill completa al asesino, `CARGA_COMPARTIDA` (0.25) a cada aliado.

Movimiento actual: inercia con suavizado exponencial (`ACELERACION_MOVIMIENTO` = 16/s, `FRENADO_MOVIMIENTO` = 22/s). La posición se guarda en float y no se redondea entre frames. El clamp al `limites` anula la velocidad en ese eje.

---

## Qué implementar

Implementa las siguientes 3 features en este orden. Cada feature es un commit separado.

---

### COMMIT 1 — Dash (mecánica + partículas)

#### Mecánica del dash

El dash es un desplazamiento rápido que todos los roles comparten por igual.

**Constantes en `src/core/balance.py`:**

| Constante | Valor | Descripción |
|---|---|---|
| `DASH_VELOCIDAD_MULT` | `4.0` | Multiplicador sobre la velocidad del rol |
| `DASH_DURACION` | `0.12` s | Duración del desplazamiento |
| `DASH_COOLDOWN` | `5.0` s | Cooldown entre dashes |
| `DASH_INVULNERABLE` | `True` | Invulnerable durante el dash |

**Reglas:**
- **Dirección:** va en la dirección de movimiento actual (WASD para J1, stick izquierdo para J2). Si el jugador está quieto, va en `direccion_mirada`.
- **Dirección fijada:** la dirección se fija al iniciar el dash y no cambia aunque el jugador mueva el input durante el desplazamiento.
- **No dispara:** durante el dash el acumulador de disparo queda en pausa. No se puede disparar ni usar la habilidad.
- **No atraviesa muros:** el movimiento se clampea al `limites` del cuarto igual que el movimiento normal. Si choca con un muro, la velocidad en ese eje se anula.
- **Invulnerabilidad:** durante el dash, si `DASH_INVULNERABLE` es True, ningún golpe entra ni abre la ventana de i-frames normal. Al terminar el dash, los i-frames normales no se activan (el dash no cuenta como un golpe recibido).
- **Solo en combate:** solo funciona en las escenas `MAZMORRA` y `JEFE`.
- **Tecla J1:** `LSHIFT`. **Botón J2:** `✕ (Cruz)` del control PS4.

**Archivo nuevo: `src/entities/dash.py`** (sin pygame, lógica pura):

```python
class Dash:
    def __init__(self):
        self.activo = False
        self.cooldown_restante = 0.0
        self.tiempo_restante = 0.0
        self.direccion = (0, 0)

    def iniciar(self, direccion) -> bool:
        """Retorna True si el dash se inició (cooldown cumplido y dirección válida)."""

    def actualizar(self, dt):
        """Descuenta timers."""

    @property
    def velocidad_multiplicador(self) -> float:
        """DASH_VELOCIDAD_MULT si activo, 1.0 si no."""

    @property
    def puede_disparar(self) -> bool:
        """False mientras el dash está activo."""

    @property
    def fraccion_cooldown(self) -> float:
        """0.0 = listo, 1.0 = recién usado. Para el indicador del HUD."""
```

**Integrar en `JugadorBase`:**
- `self.dash = Dash()` en `__init__`.
- Nuevo método `iniciar_dash(direccion_input)`: calcula dirección (input o `direccion_mirada` si quieto), llama `self.dash.iniciar(dir)`.
- En el movimiento: si `self.dash.activo`, mover con `velocidad * dash.velocidad_multiplicador * dt` en `dash.direccion` (la fijada), clampeando a `limites`.
- En `actualizar_disparo()`: si `not self.dash.puede_disparar`, no disparar.
- En `recibir_dano()`: si `self.dash.activo and DASH_INVULNERABLE`, ignorar el golpe (sin iniciar i-frames).
- Llamar `self.dash.actualizar(dt)` cada frame.

#### Partículas y afterimages del dash

**Constantes en `src/core/assets.py`:**

```python
# Dash: partículas trail
DASH_PARTICULAS_POR_FRAME = 3
DASH_PARTICULA_RADIO = 5
DASH_PARTICULA_DURACION = 0.2       # s que vive cada partícula
DASH_PARTICULA_ALFA_INICIAL = 160

# Dash: afterimages (imágenes fantasma del sprite)
DASH_AFTERIMAGES = 3
DASH_AFTERIMAGE_ALFA = (120, 70, 30)   # alfa de cada fantasma, de nueva a vieja
```

**Archivo nuevo: `src/ui/particulas.py`:**

```python
class Particula:
    """Un punto con posición, color, radio y vida que se encoge y desvanece."""

class SistemaParticulas:
    """emitir(x, y, color), actualizar(dt), dibujar(superficie)."""
```

- Cada partícula: posición donde estaba el jugador, color del rol, radio y alfa que decrecen linealmente con la vida.
- Las partículas son **solo visuales**, sin hitbox.
- Afterimages: mientras el dash está activo, guardar las últimas N posiciones y dibujar el sprite del jugador en cada una con alfa decreciente.
- El `SistemaParticulas` se crea en `Main.py` (uno global o uno por jugador) y se llama en el loop de dibujo.

---

### COMMIT 2 — Cooperativo local 2 jugadores

#### Menú de inicio con selección de modo

Antes de elegir el rol, el juego pregunta **"1 jugador" o "2 jugadores"**. Esta pantalla se navega con flechas izquierda/derecha (o teclas 1 y 2) y se confirma con ENTER. También con la cruceta y ✕ del control.

Si se elige "2 jugadores" y no hay control conectado, mostrar un aviso: **"Conecta un control de PS4 para jugar de a dos"** y esperar (detectar `pygame.JOYDEVICEADDED`). Si se conecta a mitad de partida y se había elegido 1 jugador, no pasa nada (no se agrega J2 en caliente; solo al inicio).

#### Selección de rol independiente

Cada jugador tiene su propio cursor sobre las 4 tarjetas de rol y elige de forma independiente:

- **J1:** Flechas izquierda/derecha (o A/D) para mover el cursor, ENTER o SPACE para confirmar, teclas 1-4 para elegir directo. Retroceso para cambiar.
- **J2:** Cruceta o stick izquierdo para mover el cursor, ✕ (Cruz) para confirmar, ○ (Círculo) para cambiar.
- Pueden elegir el **mismo rol** (dos Influencers, etc.).
- Cada cursor muestra un chip "J1" o "J2" del color de su rol encima de la tarjeta.
- Al confirmar, la tarjeta se tiñe levemente y aparece un ✓.
- La partida empieza cuando todos los jugadores han confirmado. ESC vuelve a la pantalla de modo.

La lógica pura de la selección (cursores, confirmación, sin dibujo) debe vivir en `src/ui/seleccion.py`. El dibujo en `src/ui/pantalla_modo.py` (pantalla de modo 1/2 jugadores) y `src/ui/seleccion_rol.py` (actualizado para 2 cursores).

#### Abstracción de input

**Archivo nuevo: `src/core/entrada.py`** (importa pygame, pero la estructura `InputJugador` es pura):

```python
@dataclass
class InputJugador:
    movimiento: tuple[float, float]   # dirección normalizada
    apuntado: tuple[float, float] | None  # punto mundo (mouse) o None
    disparando: bool
    habilidad: bool    # True solo el frame que se presiona
    dash: bool         # True solo el frame que se presiona
```

Dos funciones de lectura:

```python
def leer_input_teclado(teclas, mouse_pos, sacudida, apunta_con_mouse, ...) -> InputJugador:
    """Lee WASD + mouse + SPACE/click + F + LSHIFT."""

def leer_input_mando(controller, zona_muerta=0.15) -> InputJugador:
    """Lee sticks + R2 + L1 + ✕ del control PS4."""
```

**Mapeo del control PS4** (usar `pygame._sdl2.controller`, API GameController de SDL, que normaliza el mapeo entre drivers — los índices crudos de `pygame.joystick` cambian según el sistema):

| Acción | Control PS4 |
|---|---|
| Mover | Stick izquierdo (ejes 0, 1) |
| Apuntar | Stick derecho (ejes 2, 3) |
| Disparar | R2 (eje 5, valor > 0.5) |
| Habilidad | L1 (botón 4) |
| Dash | ✕ Cruz (botón 0) |

La zona muerta del stick: si `|eje| < 0.15`, se trata como 0.

Para el **apuntado de J2 con stick derecho**: el stick da una dirección `(x, y)`. Se convierte en un punto lejano: `centro_jugador + direccion_normalizada * 1000` y se pasa a `apuntar_a()`. Si el stick está neutro, se conserva la última dirección.

**Regla de input:** el combate no usa eventos (`KEYDOWN`) sino el estado de cada frame para movimiento, disparo y apuntado. `habilidad` y `dash` son **pulsos** (True solo el frame en que se aprieta, no mientras se mantiene). Para el mando, comparar con el frame anterior para detectar el flanco.

#### Integración en `JugadorBase`

Agregar `manejar_input(self, inp: InputJugador, dt, limites)` que unifica todo:
- Movimiento (o dash si activo)
- Apuntado (si `apunta_con_mouse` y `inp.apuntado` no es None)
- Los métodos viejos (`manejar_movimiento`, `apuntar_a`) se conservan como helpers internos.

#### Cambios en `Main.py`

- **`jugadores = [jugador1]`** y si hay J2: **`jugadores = [jugador1, jugador2]`**.
- Cada jugador tiene su propia lista de proyectiles para poder acreditar cada kill a quien la hizo.
- **`_frame_de_combate`:** iterar por cada jugador: leer input → `manejar_input` → `actualizar_disparo` → colisiones de sus proyectiles. Los proyectiles enemigos colisionan contra **ambos** jugadores.
- Los escenarios (`Cuarto`, `MazmorraJugable`, `ArenaJefe`) reciben la lista `jugadores`.
- Cada enemigo, súbdito y el jefe apuntan al **jugador en pie más cercano** (`equipo.jugador_mas_cercano`).
- Los charcos dañan a cada jugador que pise uno.
- Ambos jugadores se dibujan. J1 tiene la mira del mouse; J2 tiene una flechita de apuntado del color de su rol.

#### Transición de cuartos (puertas) en cooperativo

- **Al tocar una puerta abierta cualquiera de los dos jugadores**, pasa **todo el equipo** — ambos aparecen junto a la puerta opuesta del cuarto vecino, en fila.
- **Al entrar a una mazmorra** (desde el mapa de la ciudad), se cura a ambos jugadores.

#### Muerte y revivir en cooperativo

- Un jugador sin vida queda **caído**: no se mueve, no dispara, no se dibuja. Los enemigos lo ignoran (no es objetivo de aggro).
- El jugador caído **revive con 1 de vida** al pasar al siguiente cuarto (cuando el compañero cruza una puerta).
- En la arena del jefe: la derrota llega solo si **caen ambos** jugadores.
- Si caen ambos en una mazmorra normal, se comporta como en solitario (se reinicia el cuarto).

Reglas puras en `src/core/equipo.py` (ampliar):
```python
def jugadores_en_combate(jugadores) -> list:
    """Jugadores vivos (para colisiones, aggro, etc.)."""

def jugador_mas_cercano(jugadores, posicion) -> JugadorBase | None:
    """El jugador vivo más cercano a `posicion`."""

def todos_caidos(jugadores) -> bool:
    """True si ningún jugador está vivo."""

def revivir_caidos(jugadores, vida=1):
    """Revive a los jugadores caídos con `vida` puntos."""
```

#### Terminal de decisión en cooperativo

J1 maneja la terminal de decisión (teclado, flechas + ENTER). J2 no interactúa con la terminal.

---

### COMMIT 2 — Paneles laterales de HUD (cooperativo)

Cuando hay 2 jugadores, la información de cada jugador sale en **paneles laterales verticales**:

- **Panel izquierdo** → J1 (teclado+mouse)
- **Panel derecho** → J2 (control PS4)

Cada panel muestra:

1. **Etiqueta "J1" / "J2"** con el color del rol.
2. **Corazones** (vida).
3. **Barra de carga de habilidad** (la actual).
4. **Indicador de cooldown del dash** — un circulito con un icono de personaje corriendo:
   - **Listo para usarse:** a todo color, con un aura neón leve alrededor (glow suave del color del rol).
   - **Recargando:** oscurecido al 50%, con el círculo llenándose progresivamente desde abajo con una animación de ola (onda sinusoidal que sube). Al llenarse por completo: **flash breve** alrededor del indicador (destello blanco de ~0.15s) para avisar que ya está disponible.
5. **Controles clave** — texto pequeño con las teclas/botones de ese jugador:
   - J1: `SPACE Disparar · Mouse Apuntar · SHIFT Dash`
   - J2: `R2 Disparar · Stick R Apuntar · ✕ Dash`

Cuando hay **1 solo jugador**, el HUD superior existente se conserva tal cual (sin paneles laterales).

El indicador animado del dash (y en el futuro de la habilidad) es solo visual y vive en `src/ui/hud.py` o un módulo de dibujo dedicado. Las constantes visuales (radio del indicador, color del glow, velocidad de la ola, duración del flash) van en `assets.py`.

---

## Reglas generales

- Un módulo, una responsabilidad.
- `src/entities/dash.py`, `src/core/entrada.py` (la estructura `InputJugador`) y `src/core/equipo.py` son **puros** (sin `pygame`) para poder testearse en aislado. Las funciones de lectura de input sí usan `pygame`.
- Todo cambio de balance se hace en `src/core/balance.py`, nunca dentro de las clases de rol.
- Placeholders visuales (rectángulos de color) están bien mientras la mecánica funciona.
- No agregar código de multijugador online (`src/network/`) — esto es cooperativo local.
- Commits sin "Co-Authored-By". No modificar `git config`.
