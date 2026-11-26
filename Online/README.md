# Guía del Modo Multijugador Online (Civitas)

Este documento detalla la arquitectura, estructuras de datos, módulos y puntos de integración implementados para el modo **Online** de Civitas. Está diseñado como material de estudio para exposiciones del curso **Estructura de Datos 2**.

---

## 1. Arquitectura General y Enfoque Académico

El modo multijugador fue diseñado siguiendo los requerimientos del proyecto de **Estructura de Datos 2**:
- **Sin librerías externas complejas:** Se construyó sobre la librería estándar de Python (`socket`, `threading`, `json`).
- **Arquitectura Cliente-Servidor Autoritativa:** El **Host** (Jugador 1) ejecuta la lógica de la partida y el servidor TCP. El **Invitado** (Jugador 2) se conecta mediante un cliente TCP, envía sus comandos de movimiento/disparo y recibe las actualizaciones del estado.
- **Estructura de Datos Aplicada — Grafo de Sala (`GrafoSala`):**
  - Durante el Lobby, la sala se modela como un **Grafo**:
    - **Nodos (Vértices):** Representan a cada jugador conectado (J1, J2) y almacenan atributos como el rol elegido y si está listo.
    - **Aristas:** Representan el canal de comunicación bidireccional activo entre los nodos.
  - Esto no solo gestiona la lógica de la sala, sino que además se visualiza gráficamente en tiempo real en la pantalla del lobby.

```
       [Nodo: J1 (Host)]
             |
       (Arista TCP)
             |
       [Nodo: J2 (Invitado)]
```

---

## 2. Componentes de la Carpeta `Online/`

La carpeta `Online/` contiene toda la lógica de red desacoplada del juego base:

### 📄 `Online/__init__.py`
Define la carpeta como un paquete de Python y expone los módulos principales.

### 📄 `Online/protocolo.py`
Define las reglas de comunicación y la serialización de datos:
- **Formato de Mensajes:** Diccionarios codificados en JSON terminados en salto de línea (`\n`).
- **Tipos de Mensajes:**
  - `LOBBY`: Actualización del estado de la sala (nodos del grafo, roles elegidos y apariencias).
  - `ELEGIR_ROL`: Envío de la selección o confirmación de rol.
  - `ELEGIR_APARIENCIA`: Un jugador cambió su color de piel, cabeza o traje en un vestidor (ver sección 6).
  - `INICIAR`: Comando emitido por el host para arrancar la partida cuando todos están listos. Lleva `id_impostor` (ver sección 7).
  - `INPUT`: Envío de teclas, dirección y botones del jugador invitado hacia el host.
  - `ESTADO`: Snapshot con posiciones y vidas enviado desde el host al invitado.
  - `DESCONEXION`: Notificación de desconexión limpia.
  - `CELULAR`: el celular (sección 14): `sync` (host → invitado al conectarse: semilla y reloj del feed + historial del chat) y `chat` (invitado → host: texto; host → todos: el mensaje numerado).
- **Clase `GrafoSala`:** Implementación orientada a grafos para gestionar jugadores, adyacencias y estados de confirmación. Cada nodo guarda además la `Apariencia` de su jugador (`elegir_apariencia`, `apariencia_de`).

### 📄 `Online/servidor.py`
Servidor TCP para el Host:
- Corre en un hilo en segundo plano (`threading.Thread(daemon=True)`).
- Escucha en el puerto `7777` (`PUERTO_DEFAULT`) y obtiene automáticamente la IP local de la máquina. `iniciar(puerto, interfaz="0.0.0.0")`: los tests usan `interfaz="127.0.0.1"` para no disparar el aviso del Firewall.
- Usa sockets no bloqueantes para permitir la detención limpia sin congelar la ventana; envía con `enviar_todo()` (ver `red_local.py`).
- Mantiene una instancia de `GrafoSala` para registrar al Host y al Invitado.
- Cada 1 s manda `PING` a cada invitado y con su `PONG` calcula el ping (`latencias`, `latencia_promedio()`); ese ping es el **peso de la arista** host–invitado en el `GrafoSala`.

### 📄 `Online/cliente.py`
Cliente TCP para el Invitado:
- Se conecta a la IP y puerto especificados por el usuario. Si falla, `tipo_error` dice por qué (`timeout`, `rechazada`, `sin_ruta`...).
- Ejecuta un hilo lector en segundo plano que acumula los mensajes entrantes en una cola.
- Provee métodos simples como `enviar_rol()`, `enviar_input()`, `leer_mensajes()` y `detener()` (mismo nombre que en `Servidor`).
- Cada 1 s manda `PING` al host (`latencia_ms`, `ping_medido`) y responde con `PONG` los `PING` del host. Esos dos mensajes no pasan a la cola del lobby.

### 📄 `Online/red_local.py` (diagnóstico de red, sin pygame)
- **Ping real:** `ahora_ms()` usa `time.perf_counter()` (en Windows, `time.time()` con Python < 3.13 avanza de a ~16 ms y en una LAN mediría 0). `suavizar()` es un promedio móvil para que el número no salte. `formatear_ms()` → `"—"`, `"<1 ms"` o `"9 ms"`.
- **`MedidorInternet`:** hilo que cada 2 s mide el ping a internet como el tiempo de abrir una conexión TCP a `1.1.1.1:443` y `8.8.8.8:443` (se queda con el menor). Un `connect` TCP tarda un viaje de ida y vuelta (SYN → SYN/ACK) y, a diferencia del ping ICMP, no pide permisos de administrador.
- **`sin_retraso(sock)`:** activa `TCP_NODELAY` (apaga Nagle) para que los mensajes pequeños salgan al instante.
- **`enviar_todo(sock, datos)`:** reemplazo de `sendall()` para sockets no bloqueantes: si el búfer está lleno espera con `select()` (máx. 1 s) en vez de cortar el mensaje a la mitad.
- **`clasificar_error_conexion(e)` + `CONSEJOS`:** traduce la excepción de `connect()` a un tipo y a consejos en español para la pantalla de error.
- **`InfoRed` / `nombre_red_wifi()`:** IP y nombre del Wi-Fi de esta PC (`netsh wlan show interfaces`), leídos en un hilo.
- Tests: `tests/test_red_online.py`.

### 📄 `Online/firewall.py` (Firewall de Windows)
- **`EstadoFirewall`:** estado que dibuja la sala del Host (`revisando` / `falta` / `esperando` / `permitido` / `denegado`). Revisa con `netsh advfirewall firewall show rule name=Civitas-Online-TCP-7777` (sale con 0 si la regla existe).
- **Tecla `F` en la sala (solo Host):** `pedir_permiso()` abre el permiso de administrador de Windows (UAC) y corre un PowerShell oculto (`-EncodedCommand`, ruta fija de System32) que:
  1. crea la regla **`Civitas-Online-TCP-7777`**: entrante, solo TCP en el puerto 7777, en todos los tipos de red;
  2. desactiva (no borra) las reglas de **bloqueo** entrante de *este* `python.exe`, que Windows crea cuando alguien cierra su aviso del Firewall con "Cancelar" (una regla de bloqueo le gana a cualquier regla que permita).
- No abre otros puertos ni cambia el tipo de red. Para deshacerlo: *Firewall de Windows Defender → Configuración avanzada → Reglas de entrada → `Civitas-Online-TCP-7777` → Eliminar*.

### 📄 `Online/codigo_sala.py` (código de sala de 4 caracteres)
Reemplaza el escribir la IP por un **código de sala** corto, estilo Among Us (ej. `JPVM`):
- **Cómo funciona:** el código guarda los **últimos 20 bits** de la IP del host en base 32 (4 caracteres × 5 bits). El invitado completa los 12 bits altos con **su propia IP**: en la misma red Wi-Fi/LAN esos bits son iguales (`10.20.x.x`, `192.168.x.x`...). No necesita servidor externo ni broadcast.
- **Alfabeto:** `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (sin `I`, `O`, `0`, `1` para no confundirlos al dictarlo).
- **Funciones (puras, sin pygame):** `generar_codigo(ip)`, `resolver_codigo(codigo, ip_propia)`, `resolver_entrada(texto, ip_propia, puerto_default)` (acepta código, IP o `IP:puerto`; lanza `ValueError` si no es nada de eso) e `ip_local()`.
- **El puerto no va en el código:** siempre es `PUERTO_DEFAULT` (7777).
- **Limitación:** si host e invitado están en redes distintas en los 12 bits altos de la IP, el código no sirve; en ese caso se puede escribir la IP completa en el mismo campo.
- Tests: `tests/test_codigo_sala.py`.

### 📄 `Online/lobby.py`
Interfaz visual del modo Online construida con Pygame:
- **Sub-pantalla 1 (Elegir Modo):** Tarjetas interactivas para elegir entre **Crear Sala (Host)** o **Unirse (Join)**.
- **Sub-pantalla 2A (Lobby Host):** Muestra la IP del anfitrión, espera al invitado, permite elegir rol y presionar Enter para iniciar cuando ambos estén listos.
- **Sub-pantalla 2B (Lobby Invitado):** Input interactivo para ingresar la IP del Host, confirmación de rol y espera de inicio.
- **Visualizador del Grafo:** Dibuja los nodos (círculos de colores correspondientes a cada jugador) y la arista conectora en la parte inferior de la pantalla.
- **Vestidores:** las 4 cajas de la sala abren el modal de personalización (sección 6).
- **Función integradora `menu_online()`:** Orquesta todo el flujo previo a la partida y retorna las clases elegidas y la conexión de red activa.

### 📄 `Online/personalizacion.py` y `Online/personalizacion_render.py`
El vestidor estilo Among Us: `Vestidor` (lógica pura: pestañas COLOR / HAT / SKIN, cuadrícula, qué se equipa) y su dibujo + clics. Detalle en la sección 6.

### 📄 `Online/pantalla_rol.py`
La pantalla de revelación de rol que sale al iniciar la partida (impostor o tripulante), con el jugador vestido como eligió. Detalle en la sección 7.

### 📄 `Online/sesion_red.py`
Adaptador entre el bucle de juego de Civitas y la capa de red:
- `serializar_input()` / `deserializar_input()`: Convierte los movimientos y disparos a estructuras serializables livianas.
- `AdaptadorOnlineHost`: Permite al host enviar el estado del juego periódicamente y recibir los comandos del invitado.
- `AdaptadorOnlineJoin`: Permite al invitado transmitir su input y reflejar el estado del mundo.
- `EntradaRed`: Objeto puente que implementa la interfaz requerida por el juego (`.leer()` que retorna un `InputJugador` y `.mando.attached() = True`), permitiendo que el bucle principal de combate acepte al J2 remoto exactamente como si fuera un control conectado localmente.

---

## 3. Integración con el Código Base del Juego

Para mantener el código existente intacto y cumplir la restricción de diseño, solo se realizaron ajustes mínimos en 4 puntos clave del frontend:

### 1. [src/ui/seleccion.py](file:///c:/Users/User/Desktop/Feria4/ProyectoFeria4to/src/ui/seleccion.py)
- **Cambio:** Se agregó la constante `ONLINE = 3` a la tupla `MODOS = (UN_JUGADOR, DOS_JUGADORES, ONLINE)`.
- **Navegación:** Se actualizó `SelectorModo.mover()` para soportar desplazamiento circular tanto a la derecha (`+1 % 3`) como a la izquierda (`-1 % 3`).

### 2. [src/core/assets.py](file:///c:/Users/User/Desktop/Feria4/ProyectoFeria4to/src/core/assets.py)
- **Cambio:** Se redefinieron las dimensiones en `RECTS_OPCION_MODO`:
  ```python
  RECTS_OPCION_MODO = (
      (130, 170, 320, 340),  # Tarjeta 1: 1 jugador
      (480, 170, 320, 340),  # Tarjeta 2: 2 jugadores
      (830, 170, 320, 340),  # Tarjeta 3: Online
  )
  ```
  Esto distribuye uniformemente las 3 tarjetas en la resolución base de 1280x720.

### 3. [src/ui/pantalla_modo.py](file:///c:/Users/User/Desktop/Feria4/ProyectoFeria4to/src/ui/pantalla_modo.py)
- **Cambio:** Se añadió la opción 3 al diccionario `OPCIONES`:
  ```python
  3: ("Online", ["Multijugador en red", "J1 y J2 por TCP / IP", "Lobby con Grafos"]),
  ```
- Se ajustó el límite de sprites para que la tarjeta Online dibuje a los dos muñecos (J1 y J2) sin desbordamiento.

### 4. [Main.py](file:///c:/Users/User/Desktop/Feria4/ProyectoFeria4to/Main.py)
- **Imports:** Importación de `ONLINE`, `menu_online`, `AdaptadorOnlineHost` y `EntradaRed`.
- **Mapeo de teclado:** Tecla `3` (y teclado numérico `KP3`) asignada a `ONLINE`.
- **`_nueva_sesion(clases, mando, entrada_extra=None)`:** Parámetro opcional para inyectar `EntradaRed` en la ranura de entrada del segundo jugador.
- **`_menu_inicio(...)`:** Al seleccionar `ONLINE`, abre `menu_online(...)` y configura la sesión con el adaptador correspondiente.

---

## 4. Guía Rápida para Probar y Demostrar

### Demostración en la Misma Computadora (Localhost)
1. Abrir una primera terminal:
   ```powershell
   python Main.py
   ```
   - Ir a **JUGAR** → **Online** → Tecla `1` (**Crear sala**).
   - Verás la IP local y el Grafo de Sala esperando conexión.

2. Abrir una segunda terminal:
   ```powershell
   python Main.py
   ```
   - Ir a **JUGAR** → **Online** → Tecla `2` (**Unirse**).
   - Escribir `127.0.0.1` y presionar **Enter**.

3. **En el lobby:**
   - Ambos seleccionan su rol y presionan **Enter**.
   - El Host presiona **Enter** para iniciar la partida.

### Demostración entre 2 Computadoras (Red Wi-Fi / LAN)
1. **Ambas PCs con la misma versión del código** (los mismos archivos de `Online/`).
2. **PC 1 (Host):** Crear sala. ROOM SETTINGS muestra el **código de sala** (ej. `JPVM`), el Wi-Fi y la IP en pequeño.
3. **Solo la primera vez en esa PC:** si dice `FIREWALL: [F] permitir entrada`, presiona **F** y acepta el permiso de Windows → `FIREWALL: permitido (TCP 7777)`.
4. **PC 2 (Invitado):** Unirse escribiendo ese código (o la IP completa). Debajo del campo aparece su IP y su Wi-Fi: debe ser la **misma red** que muestra el Host.

---

## 5. Registro de Cambios

### Código de sala en vez de IP
- **Bug corregido:** al unirse, los puntos de la IP se perdían (p. ej. con el punto del teclado numérico) y el `:7777` escrito se pegaba otra vez al puerto, quedando `1020541077777:7777` → `getaddrinfo failed`.
- **Nuevo:** `Online/codigo_sala.py` y `tests/test_codigo_sala.py`.
- **`Online/lobby.py` (ajustes puntuales, sin quitar funciones):**
  - Panel ROOM SETTINGS: "IP DE LA SALA" → **"CÓDIGO DE SALA"** con el código en grande; la IP queda en pequeño al pie del panel.
  - Pantalla de unirse: pide el código de sala; acepta letras y números (se pasan a mayúsculas), el punto del teclado numérico y también una IP o `IP:puerto` como respaldo.
  - `menu_online()`: traduce lo escrito con `resolver_entrada()` antes de conectar; si no es válido muestra la pantalla de error en vez de intentar conectar.
  - Tarjeta "Unirse": textos actualizados al código de sala.

### Cómo probarlo
1. PC Host: JUGAR → Online → Crear sala. Leer el código de ROOM SETTINGS (ej. `J P V M`).
2. PC Invitado (misma Wi-Fi): JUGAR → Online → Unirse → escribir `JPVM` → Enter.
3. Misma PC: el código también funciona (o escribir `127.0.0.1`).

### Conexión entre dos PCs ("timed out"), Firewall y ping real
**Síntoma:** el invitado escribía el código, se resolvía bien (`SAMN` → `192.168.1.108:7777`) pero salía `No se pudo conectar ... — timed out`. Además el panel mostraba `PING: 0 ms`.

**Diagnóstico (hecho en la PC del Host):**
- Windows tenía el Wi-Fi marcado como red **Pública**: ahí el Firewall descarta toda conexión entrante que ninguna regla permita, sin responder; por eso el invitado veía *timed out* y no *rechazada*.
- En esa PC hay **dos Python con pygame**: 3.14 (`...\Programs\Python\Python314\python.exe`) tiene regla de entrada permitida, pero 3.11 (`...\Local\Python\pythoncore-3.11-64\python.exe`, el que abre el `python` del *Python Install Manager*) **no tiene ninguna**. Si el juego se abre con ese Python, la sala no recibe a nadie.
- `PING: 0 ms`: el Host tenía la latencia fija en `0` y el invitado nunca enviaba `PING`.

**Qué se cambió:**
- **Nuevo** `Online/firewall.py`: tecla **F** en la sala del Host = regla `Civitas-Online-TCP-7777` + desactivar bloqueos de este Python (detalle arriba, en la sección 2).
- **Nuevo** `Online/red_local.py`: ping real, ping a internet, Wi-Fi, envío seguro, `TCP_NODELAY` y clasificación de errores.
- `Online/servidor.py`: `PING` a cada invitado cada 1 s, `latencias` + `latencia_promedio()`, el ping como **peso de la arista** del `GrafoSala`, `TCP_NODELAY` al aceptar, `enviar_todo()` en vez de `sendall()`, parámetro opcional `interfaz` en `iniciar()`.
- `Online/cliente.py`: `PING` al host cada 1 s y `PONG` a los del host, `ping_medido`, `tipo_error`, `TCP_NODELAY`, lock de envío (el hilo lector también envía), `enviar_todo()`, y `detener()` (la sala llamaba `conexion.detener()` también en el invitado y Esc lo cerraba con `AttributeError`).
- `Online/lobby.py`: ROOM SETTINGS muestra `RED` (nombre del Wi-Fi), `PING SALA`, `INTERNET` y, en el Host, `FIREWALL` (+ `F` en la barra de controles); el radar escribe el ping sobre cada arista; la pantalla de unirse muestra la IP y el Wi-Fi propios; si la conexión falla, la pantalla de error explica qué revisar según el tipo de error.

**Qué significa cada error al unirse:**

| Error | Qué pasa | Qué hacer |
|---|---|---|
| `timed out` | Los paquetes no reciben respuesta: Firewall del Host o la red los descarta | En el Host: **F** en la sala y aceptar. Misma red Wi-Fi. Redes de invitados/universidad aíslan equipos: usar el hotspot de un celular |
| `rechazada` | La PC existe pero no tiene sala abierta | Que el Host esté en la sala de espera; revisar el código |
| `sin ruta` | No hay camino de red hasta esa IP | Las PCs están en redes distintas: conectarlas al mismo Wi-Fi |

**Cómo se mide el ping (para la exposición):**
- **PING SALA:** cada segundo cada lado manda `PING` con su hora (`perf_counter` en ms); el otro lo devuelve tal cual como `PONG`; ping = hora actual − hora del mensaje. Como la hora vuelve a la misma PC que la puso, no importa que los relojes de las dos PCs sean distintos. Incluye el tiempo de procesamiento del juego (los hilos revisan el socket cada ~5 ms), así que en la misma PC da ~5–9 ms.
- **INTERNET:** tiempo de abrir una conexión TCP a `1.1.1.1:443` / `8.8.8.8:443` (se queda con el menor), cada 2 s.
- **Grafo:** el ping del invitado `j` es el peso de la arista `(0, j)` del `GrafoSala` y se dibuja sobre la arista en el radar del lobby.

### Corrección de Crash en PC Invitado, Sincronización en Tiempo Real, Reconexión en Caliente y Teletransporte a Mazmorras

**Problemas reportados por el usuario:**
1. **Crash al arrancar la partida:** En la PC del invitado el juego se cerraba inmediatamente con el error `AttributeError: 'NoneType' object has no attribute 'attached'` en `Main.py:297` (`if len(entradas) > 1 and not entradas[1].mando.attached():`).
2. **El invitado no podía jugar al mismo tiempo:** El invitado no enviaba sus pulsaciones de teclado ni recibía la sincronización de la partida.
3. **Atrapado en el lobby al reconectar:** Si el invitado se unía con el mismo código mientras el host ya estaba jugando, era enviado a la sala de espera con "Esperando a que el host inicie..." sin poder saltar a la partida en curso.
4. **Falta de teletransporte a mazmorras:** Si uno de los jugadores entraba a una mazmorra desde la ciudad, el otro jugador no era transportado a la misma mazmorra.

**Causas identificadas:**
1. En `Main.py`, `_menu_inicio` retornaba `None` como `entrada_extra` para el invitado, lo que provocaba que `_nueva_sesion` asignara `EntradaMando(None)` al slot J2; al no tener control conectado, `mando.attached()` fallaba con `NoneType`.
2. `AdaptadorOnlineJoin` y `AdaptadorOnlineHost` no estaban integrados al loop principal de juego (`_jugar` en `Main.py`), por lo que no se transmitían inputs ni snapshots de estado durante el gameplay.
3. El servidor TCP no registraba el estado `self.iniciado = True` ni guardaba la escena activa; por ende, un nuevo cliente recibía solo `BIENVENIDA` pero nunca la orden `INICIAR`, quedándose en el lobby.
4. No existía protocolo de eventos para sincronizar cambios de escena (`CIUDAD`, `MAZMORRA`, `JEFE`, `DECISION`) ni avance de cuartos entre ambos clientes.

**Soluciones implementadas (respetando la regla de no eliminar código base existente, solo agregar):**
- **Protocolo de red (`Online/protocolo.py`):**
  - Se agregaron los tipos de mensaje `ENTRAR_MAZMORRA`, `CAMBIO_ESCENA` y `CAMBIO_CUARTO`.
  - Funciones auxiliares `msg_entrar_mazmorra(zona)`, `msg_cambio_escena(escena, zona, cuarto)` y `msg_cambio_cuarto(cuarto)`.
  - `msg_bienvenida` y `msg_iniciar` ahora transportan la bandera `iniciado` y el diccionario `estado_partida`.
- **Servidor y Reconexión en Caliente (`Online/servidor.py`):**
  - Se implementó `self.iniciado`, `self.estado_partida` y `self.ultimo_snapshot_estado`.
  - Al recibir una conexión cuando la partida ya está en curso, el servidor le envía inmediatamente `BIENVENIDA` con `iniciado=True` y la orden `INICIAR`, más el último snapshot.
  - Se utiliza `threading.RLock()` para garantizar concurrencia libre de deadlocks.
  - Procesa mensajes `ENTRAR_MAZMORRA` para retransmitirlos y alertar al Host.
- **Cliente TCP (`Online/cliente.py`):**
  - `Cliente` rastrea `self.estado_partida`. Al recibir `BIENVENIDA` con `iniciado=True` o `INICIAR`, activa `self.iniciado = True`.
  - Método `enviar_entrar_mazmorra(zona)` para solicitar acceso a mazmorras desde el invitado.
- **Lobby interactivo (`Online/lobby.py`):**
  - `pantalla_sala_espera`: si detecta que `conexion.iniciado` ya es `True` (unión a partida en curso), salta inmediatamente a la partida sin esperar en el lobby.
  - Al iniciar el host (vía botón o tecla Enter), llama a `conexion.marcar_iniciado()` y difunde `INICIAR` con el estado de la partida.
- **Adaptadores y Controladores de Entrada (`Online/sesion_red.py`):**
  - `_MandoFicticio`: implementa `.attached() = True`, `.get_axis() = 0.0` y `.get_button() = False` para evitar cualquier crash de GameController.
  - `EntradaLocalCliente`: permite al invitado jugar con su propio teclado y ratón local (WASD, apuntado, disparo, dash y habilidad), transmitiendo en cada frame su `InputJugador` serializado al host.
  - `EntradaRemotaHost`: ranura en el invitado para reflejar la presencia del Host.
  - `preparar_sesion_online`: construye la configuración `ConfigSesionHost` o `ConfigSesionJoin` que adapta dinámicamente las entradas y el rol local.
  - `AdaptadorOnlineHost.actualizar`: procesa peticiones de mazmorras de invitados, sincroniza cambios de escena y cuartos, y transmite el snapshot de combate y colapso electoral a ~30 Hz.
  - `AdaptadorOnlineJoin.actualizar`: sincroniza de forma inmediata teletransportes a mazmorras cuando el host o el invitado ingresan a un edificio, y aplica snapshots de posiciones y vidas.
- **Integración no invasiva (`Main.py` y `src/core/entrada.py`):**
  - Se añadieron verificaciones de seguridad para mandos nulos en `src/core/entrada.py` y `Main.py`.
  - Se conectó `sesion.adaptador_red.actualizar` y `actualizar_ciudad` en el loop principal sin borrar ninguna línea preexistente.
  - Se renderizan ambos avatares en la ciudad mediante `partida.jugadores_online`.

---

## 4. Corrección de Cierre al Entrar a Mazmorras y Registro Seguro

### Diagnóstico de Fallas Reportadas
1. **Cierre en la PC secundaria al entrar a una mazmorra:**
   - **Causa raíz:** En `Main.py`, `escenario = _escenario_activo(escena, arena, mazmorra)` se calculaba en cada frame *antes* de invocar `adaptador_red.actualizar(...)`. Cuando el adaptador transportaba al jugador a la escena `MAZMORRA`, la variable local `escenario` mantenía el valor `None` (propio de la ciudad). Al ejecutarse el bloque `_frame_de_combate`, la instrucción `restriccion_armas = escenario.gracia.activa` causaba un `AttributeError: 'NoneType' object has no attribute 'gracia'` que cerraba el juego inesperadamente.
   - Adicionalmente, el pipeline de renderizado y el despachador de eventos ejecutaban llamadas sobre `escenario.dibujar()`, `escenario.manejar_evento()` y `_titulo_mazmorra(mazmorra)` sin guards defensivos para estados transitorios.

### Mejoras Implementadas
1. **Normalización Dinámica de Escena (`Online/sesion_red.py`):**
   - Función `normalizar_escena(escena, arena, mazmorra, resultado, jugador, partida)`: asegura la coherencia estructural de la escena actual. Si por latencia o desfase de red se recibe una escena de combate sin su estructura activa (`MAZMORRA` sin mazmorra o `JEFE` sin arena), la redirige a un estado seguro sin interrumpir la ejecución.
2. **Recálculo de Escenario y Guardias de Seguridad (`Main.py`):**
   - Inmediatamente después de `adaptador_red.actualizar(...)`, `Main.py` normaliza la escena y recalcula `escenario = _escenario_activo(...)`.
   - Se añadió un guard temprano en `_frame_de_combate`: si `escenario is None` durante un frame de cambio de escena, omite la simulación de combate de ese ciclo sin fallar.
   - En el loop de dibujo, si `escenario is None`, se realiza un `presentar()` defensivo y continúa al siguiente frame.
   - En `manejar_evento`, cálculo de sacudida y `_titulo_mazmorra`, se verifican las referencias nulas.
3. **Módulo de Registro de Errores (`Online/registro_errores.py`):**
   - Garantiza que ninguna anomalía o excepción en la sincronización de red tumbe el proceso del juego a escritorio.
   - Centraliza el registro en `Online/errores_online.log` con traceback detallado y control de repeticiones para proteger el rendimiento y disco.
4. **Protección Integral de Partida (`proteger_partida_online`):**
   - Decorador aplicado sobre `Main._jugar`: si surge un fallo no controlado durante una sesión de red, se captura limpiamente, se registra el error y se devuelve el control al menú principal (`MENU`), preservando el estado de la sesión para reanudar con la opción `CONTINUAR`.
5. **Sincronización de Balas y Limpieza de Combate (`compartir_combate_con_sesion`):**
   - Conecta el vaciado de proyectiles (`limpiar_combate`) y la lista de proyectiles enemigos de la sesión para que los clientes invitados visualicen y limpien proyectiles enemigos de forma espejo sincronizada con el anfitrión.

### Validación de Tests
Para verificar que ningún cambio rompió el juego base ni los tests del sistema:
```powershell
pytest tests/
```
*(Todos los 580 tests pasan exitosamente al 100%).*

---

## 5. Derrota por Muerte de Equipo, Decisiones Colaborativas y Sincronización de Detonación

### Diagnóstico de Fallas Reportadas
1. **Los jugadores no pierden al morir en la mazmorra:**
   - **Problema:** En cooperativo/online, cuando todos los jugadores se quedaban sin corazones (mostrando "CAÍDO"), la mazmorra no terminaba. Los jugadores quedaban atrapados con 0 vidas en el cuarto mientras los enemigos seguían disparándoles.
   - **Causa raíz:** En `Main.py`, dentro de `escena == Escena.MAZMORRA`, no existía una verificación de `todos_caidos(jugadores)`. A diferencia de `Escena.JEFE` (que llama a `_derrota()`), la mazmorra normal solo evaluaba cambios de cuarto o la llegada a la fase de decisión.
2. **Los invitados no podían interactuar ni tomar decisiones en la Terminal:**
   - **Problema:** En el cuarto final, solo el Host podía moverse en el árbol y elegir opciones; el teclado de los invitados no respondía.
   - **Causa raíz:** En `Online/sesion_red.py`, la función `_congelar_terminal(terminal)` reemplazaba `terminal.navegar = _nada`, bloqueando cualquier entrada en los clientes invitados sin reenviarla al anfitrión.
3. **La pantalla de Detonación por tiempo solo salía en el Host:**
   - **Problema:** Cuando el cronómetro llegaba a `0.0 s`, el Host pasaba a la pantalla de "Detonación" ("Se acabó el tiempo sin decidir. La publicación se propagó y la incursión falló"), pero el invitado se quedaba congelado en la pantalla de la terminal mostrando "Tiempo restante 0.0 s".
   - **Causa raíz:** En el frame donde el tiempo se agotaba, el Host cerraba la mazmorra y pasaba a `Escena.RESULTADO` borrando la referencia local de `mazmorra`. El snapshot de red dejaba de enviar el paquete `term`, y `AdaptadorOnlineJoin._converger` recibía `escena_host == Escena.RESULTADO`, pero devolvía `Escena.DECISION` sin instanciar un `ResultadoMazmorra` en el invitado. Como la terminal del invitado estaba congelada con `_nada`, no se actualizaba ni cerraba nunca.

### Soluciones Implementadas

1. **Derrota y Detonación por Equipo Caído (`Main.py`, `src/ui/pantalla_resultado.py`, `Online/sesion_red.py`):**
   - Se importó `todos_caidos` en `Main.py` desde `src.core.equipo`.
   - En `Escena.MAZMORRA`, se agregó la condición:
     ```python
     elif mazmorra is not None and todos_caidos(jugadores):
         colapso_antes = partida.colapso.valor
         partida.registrar_decision(mazmorra.mazmorra.nombre_zona, DETONACION)
         colapso_despues = partida.colapso.valor
         resultado = ResultadoMazmorra(
             DETONACION, "Derrota", colapso_antes, colapso_despues, mazmorra.mazmorra.nombre_zona
         )
         if hasattr(sesion, "adaptador_red") and sesion.adaptador_red is not None and hasattr(sesion.adaptador_red, "notificar_resultado"):
             sesion.adaptador_red.notificar_resultado(resultado)
         mazmorra = None
         escena = Escena.RESULTADO
         limpiar_combate()
     ```
   - En `src/ui/pantalla_resultado.py`: se agregó la explicación de derrota a `EXPLICACIONES`:
     ```python
     "Derrota": "Todo el equipo cayó en combate. La zona detonó y la incursión falló."
     ```
   - En `Online/sesion_red.py`: `AdaptadorOnlineHost` detecta el wipe o recibe `notificar_resultado(...)` y difunde el dict `_fin` a todos los invitados.

2. **Decisiones Colaborativas en la Terminal (`Online/protocolo.py`, `Online/cliente.py`, `Online/servidor.py`, `Online/sesion_red.py`, `Main.py`):**
   - **Protocolo:** Nuevo tipo de mensaje `DECISION_NAV` y función `msg_decision_nav(direccion, id_jugador)`.
   - **Cliente:** `Cliente.enviar_decision_nav(direccion)` y `AdaptadorOnlineJoin.enviar_decision_nav(direccion)`.
   - **Servidor:** Al recibir `DECISION_NAV` de cualquier cliente, lo encola en `mensajes_host`.
   - **Host autoritativo:** `AdaptadorOnlineHost` extrae los comandos de navegación de la cola (`IZQUIERDA`, `DERECHA`, `CONFIRMAR`) y los aplica sobre la terminal autoritativa (`terminal.navegar(d)`).
   - **Sincronización:** Cada frame, el Host difunde `estado["term"]` con el `nodo_actual`, `indice_seleccionado` y `tiempo_restante`. Todos los invitados ven el cursor moverse y avanzar en tiempo real cuando cualquier jugador presiona una tecla.
   - **Intercepción en Main:** En `Main.py` para `Escena.DECISION`, las teclas de `TECLAS_TERMINAL` se envían al adaptador mediante `sesion.adaptador_red.enviar_decision_nav(...)`.

3. **Sincronización de Pantalla de Detonación y Resultados (`Online/sesion_red.py`, `Main.py`):**
   - **Envío de Resultado:** Al terminar la decisión (por opción elegida, por agotamiento del tiempo a 0.0 s o por caída en combate), el Host notifica a `AdaptadorOnlineHost.notificar_resultado(resultado)` y envía en el snapshot de red el bloque `res_info` con: `res`, `opcion`, `antes`, `despues` y `zona`.
   - **Recepción en Invitados:** En `AdaptadorOnlineJoin._converger`, al detectar `escena_host == Escena.RESULTADO`:
     - Se extrae `res_info` o `fin`.
     - Se instancia un `ResultadoMazmorra` completo y se asigna a `self.resultado_remoto`.
     - Se limpia el combate y se retorna `Escena.RESULTADO`.
   - **Transición en `Main.py`:** Si `sesion.adaptador_red.resultado_remoto` existe, se asigna a la variable `resultado` local de `Main._jugar`. `normalizar_escena` valida que `resultado is not None` y la escena permanece en `Escena.RESULTADO`.
   - **Retorno a Ciudad Nova:** Al presionar Enter en la pantalla de resultado, o cuando el Host regresa a `Escena.CIUDAD`, todos los clientes invitados regresan en sincronía a `Escena.CIUDAD` con las barricadas y el colapso electoral actualizados.

### Suite de Tests Añadida
En `tests/test_online_sincronizacion.py`:
- `test_derrota_cuando_todos_caen_en_mazmorra()`: Verifica la caída total del equipo y la generación de la pantalla de Detonación con la explicación de derrota.
- `test_decision_nav_protocolo_y_cliente_servidor()`: Verifica la serialización del mensaje `DECISION_NAV`, el despacho en el servidor y la navegación autoritativa en el terminal del host.
- `test_sincronizacion_pantalla_resultado_a_invitados()`: Verifica la convergencia a `Escena.RESULTADO`, la construcción del objeto `ResultadoMazmorra` en el invitado y el retorno coordinado a la ciudad.

---

## 6. Vestidores estilo Among Us (personalizar el personaje)

### Qué hace
Los 4 carritos de equipaje del salón (`VESTIDOR 1` a `VESTIDOR 4`, ver la sección 13) son vestidores. Al acercarse a uno, se ilumina y aparece **"Presiona [E] o clic: vestidor"**. Se abre un modal como el de Among Us, con seis pestañas:

| Pestaña | Qué cambia | Opciones |
|---|---|---|
| **COLOR** | Tono de piel (cara y manos) | AUTO + 8 tonos |
| **HAT** | La parte de arriba: pelo, cara y lentes | AUTO + la cabeza de cada uno de los 4 roles |
| **SKIN** | El traje: camisa, pantalón y zapatos | AUTO + el traje de cada uno de los 4 roles |
| **HAIR** | Color del pelo de la cabeza que lleves | AUTO + 9 colores |
| **SHIRT** | Color de la camisa o chaqueta del traje | AUTO + 9 colores (el primero, morado Civitas) |
| **PANTS** | Color del pantalón | AUTO + 9 colores |

- **AUTO** = lo de tu rol: quien nunca usa un vestidor se ve igual que siempre, y si cambias de rol en la laptop, lo que esté en AUTO cambia solo.
- El **accesorio** (megáfono, palo selfie, micrófono, mano) siempre es el de tu **rol**, porque identifica su habilidad.
- Los cambios se equipan al instante y **toda la sala los ve** (en su avatar del lobby). La apariencia también se ve **durante la partida**: en Ciudad Nova y en combate, en todas las PCs.
- Controles: flechas/WASD eligen, `Tab` / `1-6` cambian de pestaña, clic en una casilla o pestaña, `E` / `Esc` / `Enter` (o clic fuera / en la X) cierran.

### Sin arte nuevo: el personaje se arma por partes
No se agregó ningún sprite. Cada personaje viene de una receta de Pixelbolt (`assets/sprites/fuentes/<rol>.pixel.json`) que dibuja sus cuadros "estampando" símbolos: `cabeza`, `torso`, `piernas_*` y el accesorio del rol, cada uno con la paleta de su rol. `src/ui/receta_jugador.py` repite las estampas del rol del jugador, pero toma la `cabeza` de la receta elegida en HAT y el `torso`/`piernas` de la elegida en SKIN; la letra de la piel (`s`) se pinta con el tono de COLOR. Con todo en AUTO el resultado es **idéntico píxel a píxel** a la hoja PNG del rol (está probado en los tests).

### Estructura de datos: atributo del nodo del grafo
La apariencia es un atributo más de cada **nodo** del `GrafoSala`, igual que el rol:
- `src/core/apariencia.py`: `Apariencia(piel, cabeza, traje)`, inmutable; `None` = lo del rol. `de_dict()` valida campo por campo, así un dato roto o de otra versión del juego nunca tumba el lobby.
- `GrafoSala.elegir_apariencia(id, apariencia)` / `apariencia_de(id)`: O(1). `a_dict()` / `de_dict()` la incluyen en cada nodo (una versión vieja sin el campo queda con la predeterminada).

### Flujo por red
1. **Invitado:** cada cambio llama `Cliente.enviar_apariencia(ap)` → mensaje `ELEGIR_APARIENCIA`.
2. **Servidor (host):** guarda la apariencia en el nodo de **esa conexión** (usa el id del socket, no el del mensaje: nadie puede vestir a otro) y difunde `LOBBY` a todos.
3. **Host:** sus propios cambios van directo a `servidor.sala` + `LOBBY` a todos (igual que su rol).
4. **Al iniciar la partida:** `ConfigSesionHost` / `ConfigSesionJoin` (`Online/sesion_red.py`) copian la apariencia de cada nodo a su jugador (`JugadorBase.apariencia`), y `sprite_jugador(..., apariencia=)` la dibuja en la ciudad y en combate.

### Archivos
- Nuevos: `src/core/apariencia.py`, `src/ui/receta_jugador.py`, `Online/personalizacion.py`, `Online/personalizacion_render.py` y sus tests.
- Modificados: `src/core/assets.py` (tonos de piel, partes de las recetas y colores del modal), `src/ui/sprites.py` (`sprite_jugador(..., apariencia=)`, `sprite_parte_jugador`), `Online/protocolo.py`, `Online/servidor.py`, `Online/cliente.py`, `Online/lobby.py`, `Online/sesion_red.py`, `src/entities/player.py`, `src/ui/ciudad_render.py` y `Main.py`.

### Cómo probarlo
1. Host y un invitado en la sala (misma PC o dos PCs).
2. Camina hasta cualquier caja → `E` → elige un tono, una cabeza y un traje.
3. En la otra pantalla tu avatar cambia al instante.
4. Inicia la partida: en Ciudad Nova y en las mazmorras cada jugador conserva lo que eligió.

---

## 7. Impostor y pantalla de revelación de rol

### Qué hace
Al iniciar la partida, el host sortea a **1 impostor** entre los jugadores conectados (1 de 2, 1 de 3 o 1 de 4). Antes de salir del lobby, cada PC muestra una pantalla de 3.8 s con lo que le tocó:

| | Impostor | Los demás |
|---|---|---|
| Fondo | Negro con un óvalo rojo que pulsa | Negro limpio (`#0B0E14`) |
| Arriba | **IMPOSTOR** en `#FF1A1A` | "Tu rol es" y el nombre de su rol, en `#70E5FF` |
| Centro | El jugador **con la ropa de los vestidores**, flotando | Igual |
| Abajo | "Evita que los demás completen sus tareas saboteándolos" | "Completa tus tareas y descubre al impostor" |

- El avatar es el mismo sprite vestido de la sala y de la partida (`sprite_jugador(..., apariencia=)`), no una imagen aparte; no se agregó arte. El texto "pixelado" es la fuente del juego sin suavizado, ampliada sin interpolar.
- Línea de tiempo: 0.5 s de fundido desde negro, jugador fijo y 0.5 s de fundido a negro. **Espacio** o **Enter** saltan al fundido de salida, pero solo pasados 2 s.
- Respeta el filtro de daltonismo (usa el `presentar` del juego) y **Reducir movimiento** (sin flotar ni pulsar).
- El impostor **sabotea la terminal de decisión** al final de cada mazmorra (sección 8). Su clase de combate sigue siendo el rol que eligió; no hay tareas ni votación.

### Flujo por red (host autoritativo)
1. `Servidor.marcar_iniciado()` llama a `sortear_impostor()`: `random.choice` sobre los vértices del `GrafoSala` (`sala.jugadores()`: O(V log V) por su `sorted`; `random.choice` es O(1)), una sola vez por partida.
2. El lobby difunde `msg_iniciar(estado, id_impostor=...)`. Nadie conoce al impostor antes de iniciar.
3. `Cliente._procesar` guarda `id_impostor` **antes** de poner `iniciado = True`: el lobby lee ese flag desde otro hilo y ahí mismo pregunta quién es.
4. Cada PC compara con su propio id: `es_impostor = (id_local == id_impostor)`.
5. `lobby._entrar_a_partida` fija las clases y el orden de los jugadores (`conexion.ids_partida`) **antes** de la pantalla: si alguien se desconecta durante esos casi 4 s, cada clase sigue emparejada con su id.
6. `ConfigSesionHost` / `ConfigSesionJoin` (`_asignar_impostor`) dejan `sesion.id_impostor` y `jugador.es_impostor`. Tras una derrota global se conserva, porque no se vuelve al lobby.

Como la apariencia se lee de la sala **después** de la pantalla, un cambio de ropa hecho justo antes del Enter del host alcanza a llegar a todas las PCs.

### Quien vuelve a una partida en curso
Un invitado que se reconecta recibe `id_impostor` ya en la `BIENVENIDA` (`unido_en_curso = True`, porque `iniciado` se activa antes de que llegue `INICIAR`) y **no ve la pantalla**: entra directo, como antes.

### Archivos
- Nuevos: `Online/pantalla_rol.py` y `tests/test_impostor_online.py`.
- Modificados: `Online/protocolo.py` (`msg_iniciar`, `msg_bienvenida`), `Online/servidor.py` (sorteo), `Online/cliente.py`, `Online/lobby.py` (`_entrar_a_partida`, `_revelar_rol`, `_motivo_para_no_iniciar`), `Online/sesion_red.py`, `src/entities/player.py`, `src/core/assets.py` y `Main.py`.

### Cómo probarlo
1. Host y al menos un invitado en la sala. Vístanse en las cajas.
2. El host presiona Enter o el botón START.
3. Cada PC ve su pantalla con su ropa; exactamente una dice IMPOSTOR.
4. Después sigue el juego de siempre (la introducción del modo historia y Ciudad Nova).

---

## 8. Sabotaje del impostor en la terminal de decisión

### Qué hace
Al final de cada mazmorra normal el equipo comparte un cursor sobre el árbol de decisión: cualquiera lo mueve (← →) o confirma (Enter). El impostor también, pero **al abrirse la terminal queda bloqueado** un tiempo que el host sortea entre **10 y 15 s** (`balance.COOLDOWN_SABOTAJE_MIN` y `COOLDOWN_SABOTAJE_MAX`; cada terminal sortea el suyo). Mientras tanto los demás buscan la respuesta correcta. Después **elige normal**: mueve y confirma todas las veces que quiera, y así sabotea (lleva el cursor a una respuesta mala o la confirma antes que los demás).

- Solo el impostor ve su indicador, arriba al centro de la terminal: "Se habilita en N s" con una barra que se llena, "Listo: ya puedes mover y confirmar" cuando termina, y "Aún no" si aprieta durante el bloqueo. Su barra de controles dice "sabotear".
- Los demás no ven nada distinto: tienen que descubrir quién mueve el cursor. Como el bloqueo cambia entre 10 y 15 s, tampoco saben el segundo exacto en que el impostor puede empezar.
- Para un bloqueo fijo, basta poner los dos valores iguales en `balance.py`.
- Fuera de la terminal (por ejemplo, la investigación del capítulo 3) el impostor navega libre.

### Host autoritativo
- `Online/sabotaje.py` (puro): `Sabotaje` con `seguir_terminal(terminal)` (una terminal nueva sortea su bloqueo con un `random.Random` inyectable; la misma sigue su cuenta), `actualizar(dt)` y `listo` (terminó el bloqueo; elegir no gasta nada). O(1).
- `AdaptadorOnlineHost.puede_navegar(indice, terminal)`: descarta los `DECISION_NAV` del impostor durante su bloqueo, antes de cargarle la decisión (`registrar_actor`). En Main, teclado y control pasan por un solo camino (`navegar_terminal`), que consulta este método con la terminal que se ve, así el bloqueo corre desde el primer frame aunque el impostor sea el host o juegue con control.
- El host manda en el ESTADO lo que falta (`term.sab`) y el total sorteado (`term.sabt`); cada invitado los refleja (`AdaptadorOnlineJoin.puede_navegar`, `restante_sabotaje` y `espera_sabotaje`) solo para no mandar teclas en vano y dibujar el indicador.

---

## 9. La presentación del capítulo sale en todas las PCs

### El bug
Al entrar a una mazmorra, la tarjeta del capítulo y su diálogo solo salían en la PC que apretó E (normalmente el host). La presentación se encolaba en el manejador de la tecla E de `Main._jugar`, y los adaptadores llevan a los demás a la mazmorra por otro camino (`AdaptadorOnlineJoin._entrar_mazmorra` en el invitado y `AdaptadorOnlineHost._atender_solicitudes` cuando lo pide un invitado), sin pasar por ahí.

### La corrección
- `Main._jugar` tiene un solo punto de entrada a una zona, `al_entrar_a_zona(zona)`, que usan la E y también la red: si después de `adaptador_red.actualizar(...)` la escena pasó de CIUDAD a MAZMORRA o JEFE, cada PC presenta el capítulo (una vez por zona, `campania.intros_vistas`). Donde se decide la historia (host o partida local) también corren los matices de entrada (fuente del Periodista, ayuda ciudadana), que antes faltaban si la entrada la pedía un invitado.
- **El mundo espera a quien lee.** Cada invitado avisa al host cuando abre o cierra una escena de la historia (`HISTORIA` con evento `lectura`). En combate, el host no simula mientras alguien lee (`esperando_lectura()`), así a nadie lo atacan durante la tarjeta del capítulo o la cinemática del jefe. Muestra "Esperando a que J2 termine de leer" y lo manda en el ESTADO (`leen`), para que los demás vean el mismo aviso. Quien se desconecta deja de contar.

### Cómo probarlo
1. Dos PCs en una partida Online. Cierren la intro.
2. El host entra al Colegio con E: **las dos** PCs ven la tarjeta "Capítulo 1: El rumor" y su diálogo.
3. Si una PC sigue leyendo, la otra ve "Esperando a que J… termine de leer" y el cuarto queda quieto hasta que termine.

---

## 10. Reunión de emergencia (botón REPORTAR)

### Qué hace
Como en Among Us, cualquier jugador puede llamar a una reunión para debatir quién es el impostor.
- **Botón REPORTAR** a la izquierda (o la tecla **R**, o un clic; dónde exactamente, en la sección 13; en la terminal va chico a la izquierda de la barra de controles). Se puede usar **cada 60 s** (`balance.COOLDOWN_REUNION`): el tiempo cuenta desde que arranca la partida y desde que termina cada reunión. Mientras recarga se ve apagado con los segundos que faltan.
- Al apretarlo, el juego **se detiene en todas las PCs** (combate, caminar por la ciudad, el reloj de la terminal y el bloqueo del impostor) y se abre la reunión: **60 s** (`balance.DURACION_REUNION`) para hablar por el **chat** y **votar**.
- **Votar:** flechas para elegir y **Enter dos veces** (o dos clics) sobre un jugador o sobre **Saltar votación**. El voto no se cambia. Durante la votación solo se ve quién ya votó; a quién, recién en el resultado.
- **Chat:** se escribe con el teclado y se envía con Enter (80 caracteres por mensaje; se ven los últimos 14).
- **Conteo:** se acaba el minuto (o ya votaron todos) y **solo cuentan los votos emitidos**: quien no votó no le suma a nadie. Si alguien tiene más votos que cualquier otro y que los saltos, queda **expulsado** y todos ven si **era el impostor**. Empate, mayoría de saltos o nadie votó: no se expulsa a nadie. El resultado se ve 6 s.
- **Expulsado = fantasma:** los demás ya no lo ven (ni su muñeco ni su panel), los enemigos no lo persiguen y no recibe daño. Él sigue viendo a todos normal y se ve a sí mismo medio transparente; camina, pero no dispara, no usa habilidad ni dash, no recoge pruebas, no abre puertas ni entra a edificios. Tampoco mueve la terminal ni la investigación del capítulo 3, no vota, no escribe y no convoca (`src/core/equipo.py`, `jugador.expulsado`).
- **Fin de la partida:** si expulsan al **impostor**, gana la tripulación: pantalla "¡Felicidades! Has descubierto al impostor · Civitas se ha salvado" (con 2, 3 o 4 jugadores). Si expulsan inocentes hasta que quedan **solo el impostor y uno más** (con 2 jugadores: basta expulsar al otro), gana el impostor: los demás ven "El impostor quedó en pie · y él destruyó Civitas" y el impostor "¡Felicidades! Has eliminado a los demás jugadores · Has destruido Civitas con éxito" (con 4 jugadores hacen falta 2 inocentes). Las dos muestran quién era el impostor; tras 2 s, Enter vuelve al menú y la partida Online se cierra (`balance.JUGADORES_MINIMOS_VICTORIA_IMPOSTOR`).
- Solo hay botón en una partida Online con impostor, en la ciudad, las mazmorras, la terminal y el jefe (no en las pantallas de resultado ni en los finales).

### Host autoritativo
- `Online/reunion.py` (puro): `contar_votos`, `Reunion` (reloj, un voto por jugador, chat) y `ControlReuniones` (el botón, la reunión, el resultado y los expulsados). `a_dict()` viaja en el ESTADO (`reu`) y `vista_de_dict()` lo lee en el invitado sin confiar en sus tipos.
- Mensaje nuevo `REUNION` (invitado → host) con `evento` = `convocar`, `votar` (`objetivo`: índice o `"saltar"`) o `chat` (`texto`). El servidor le pone el id de la conexión: nadie vota por otro.
- `AdaptadorOnlineHost`: `convocar_reunion`, `votar_reunion`, `escribir_reunion`, `estado_reunion`, `reunion_en_curso` y `expulsado`. El invitado tiene los mismos métodos, pero se los pide al host. `puede_navegar` responde False durante la reunión y para los expulsados, así el host descarta sus `DECISION_NAV`.
- `Main._jugar`: la reunión se lleva todos los eventos (teclado, texto, ratón y control) mientras está abierta. `en_reunion` detiene el combate, la ciudad y el reloj de la terminal. El dibujo está en `Online/reunion_render.py`.

### Cómo probarlo
1. Dos PCs en una partida Online (hay impostor). Esperen 60 s o, en los tests, usen `ControlReuniones(recarga=0)`.
2. Una PC aprieta **R**: las dos ven la reunión y el mundo queda quieto.
3. Escriban en el chat, voten (Enter dos veces) o salten. Al terminar, todos ven el resultado y el botón vuelve a recargar 60 s.

Tests: `tests/test_reunion_online.py` (conteo, reglas, host, invitado, red real, loop real de Main y dibujo).

---

## 11. Botón SABOTEAR del impostor (publicación viral)

### Qué hace
- Solo el impostor ve el botón **SABOTEAR** (tecla **Q** o clic), junto a REPORTAR (a la izquierda). Se puede cada **75 s** (`balance.COOLDOWN_POST_SABOTAJE`), en la ciudad, las mazmorras y el jefe (no en la terminal: ahí ya hay una decisión).
- Al apretarlo, a **todas las PCs** les salta en el celular una **publicación falsa** (como la terminal del final de la mazmorra, con el árbol fijo: Verificar / Me gusta / Compartir / Reportar / Ignorar) y el mundo se detiene. Nadie sabe quién la lanzó; arriba sale "¡Publicación viral! Decidan rápido qué hacer".
- Hay **20 s** (`DURACION_POST_SABOTAJE`). Verificar o Reportar la **frenan**; Me gusta, Compartir o Ignorar la **vuelven viral**, y si se acaba el tiempo también.
- El impostor también elige, pero recién después de **5 s** (`BLOQUEO_POST_SABOTAJE`, ve su indicador "Se habilita en N s"): si nadie eligió bien antes, puede elegir una mala.
- Resultado (4 s para todos): "¡Sabotaje frenado!" (sube la información verificada) o "El sabotaje funcionó" (sube la desinformación y la barra de colapso, como una incursión fallida). Los efectos están en `balance.EFECTOS_POST_SABOTAJE_*`.
- Las publicaciones salen de `content/campaign.json` ("sabotajes", validadas por `contenido.py`) sin repetirse hasta usarlas todas.

### Host autoritativo
- `Online/post_sabotaje.py` (puro): `ControlSabotajes` (botón, publicación en curso con su `TerminalDecision`, bloqueo del impostor y resultado) y `vista_de_dict` para el invitado.
- Mensaje nuevo `SABOTAJE` (invitado → host). Mientras hay publicación, el host manda **todas** las `DECISION_NAV` a ella (`navegar_sabotaje`); el impostor espera su bloqueo y el expulsado no elige. El host aplica los efectos **una sola vez** al terminar.
- El ESTADO lleva `sbp`; el invitado arma una copia congelada de la publicación (`terminal_sabotaje`) para dibujarla con la terminal tipo celular.
- No hay reunión durante una publicación ni publicación durante una reunión.

---

## 12. La terminal tipo celular en todas las PCs, y el aviso de versión

- La terminal del final de la mazmorra se dibuja como dos celulares (`src/ui/terminal_decision_render.py` y `src/ui/celular_render.py`) en **todas** las PCs: es el mismo código. Si en una PC se ve la terminal vieja (azul, con tarjetas), esa PC tiene otro código: copien o actualicen el proyecto completo en todas las PCs (por ejemplo con `git pull` después del commit).
- Para notarlo en el momento: el invitado manda su `VERSION_ESTADO` en cada INPUT y el host la suya en el ESTADO. Si no coinciden, aparece arriba "J2 tiene otra versión del juego: copien el mismo código en todas las PCs" (o "El host tiene otra versión…").
- Si el host llega a la terminal antes de que el invitado limpie el cuarto, el invitado arma la terminal con el **árbol de la historia** del cuarto (`fabrica_arbol`), no con el árbol fijo: misma publicación y mismos ids que el host.
- Al empezar una partida nueva o al terminar una Online, la red de la partida anterior se cierra (`cerrar_red_de_sesion`), así el puerto 7777 queda libre para volver a crear una sala.

Tests: `tests/test_fin_y_sabotaje_online.py` (fantasma, fin de partida, sabotaje, versión, terminal del invitado) y `tests/test_terminal_celular.py` (la terminal tipo celular).

---

## 13. Lobby con el estilo de ahora, más ropa, 2 jugadores y botones a la izquierda

### La sala de espera es un salón del hotel
La sala Online tenía el estilo viejo (nave neón con baldosas, "AIRLOCK", laptop "CUSTOMIZE"). Ahora es un salón del **mismo hotel Backrooms** del lobby del juego, con sus tiles y props (sin arte nuevo):
- **Recepción** (el escritorio con el computador): ahí se elige el rol (`E` o clic), como antes en la laptop.
- **4 carritos de equipaje** en las esquinas: los vestidores, cada uno con su cartel y la vitrina de la cabeza y el traje de un rol.
- Pared del fondo con el letrero de neón, el reloj con la hora real, apliques que parpadean, el llavero y el ascensor; palmeras y lámparas de pie; polvo en el aire.
- Paneles de la derecha (ROOM SETTINGS, grafo de sala), el vestidor y los avisos con el **morado de Civitas** (vidrio oscuro, como el resto del juego).

Archivos (todos en `Online/`):
- `Online/datos/sala_hotel.json`: la composición del salón (rectángulos, mismo formato que las composiciones del lobby). Cada objeto dice qué es: `"rol": "recepcion"`, `"rol": "vestidor"` u `"obstaculo": true`.
- `Online/sala_hotel.py` (puro): la arma con `src/dungeon/compositor_interior.py` y la pasa a px de pantalla (`disposicion`: piso por donde se camina, recepción, vestidores, obstáculos y dónde aparece cada jugador).
- `Online/sala_hotel_render.py`: la dibuja con la escena del lobby del hotel (`src/ui/escena_lobby_render.EscenaLobby`, sin tocarla) corrida a la sala, más los carteles, halos e invitaciones. Si falta el arte Backrooms, vuelve la sala neón de antes.
- `Online/lobby.py` toma de ahí todas las posiciones.

### Más cosas para editar la skin: HAIR, SHIRT y PANTS
Tres pestañas nuevas en el vestidor (9 colores cada una más AUTO). No hay sprites nuevos: se **recolorea** el arte de las recetas.
- `src/ui/receta_jugador.py` encuentra en cada receta qué letras de la paleta son el pelo (`h` y sus tonos parecidos), la camisa (la letra que más se usa en el torso, sin contorno, piel ni blanco, y sus sombras) y el pantalón (`d`), y las tiñe con `teñir`, que conserva la luz de cada tono (las sombras siguen siendo sombras). Los lentes del Periodista, los cuellos, las corbatas y los zapatos no cambian.
- `src/core/apariencia.py`: `Apariencia` suma `pelo`, `ropa` y `pantalon` (viajan por red; una versión vieja sin esos campos los deja en AUTO). Las paletas están en `src/core/assets.py` (`TONOS_PELO`, `COLORES_ROPA`, `COLORES_PANTALON`) porque las usa el dibujo del jugador en todo el juego; sus nombres, en `Online/personalizacion.py`.
- Se ven en la sala, en la revelación del rol, en la ciudad, en las mazmorras y en la reunión.
- Fuera de `Online/` solo se tocó lo obligatorio: `src/core/apariencia.py`, `src/ui/receta_jugador.py`, `src/ui/sprites.py` (vista previa con colores) y las paletas en `src/core/assets.py`.

### Con 2 jugadores también gana el impostor
`balance.JUGADORES_MINIMOS_VICTORIA_IMPOSTOR = 2`: si en una partida de 2 la votación expulsa al inocente, el impostor queda en pie y la partida termina al instante con las pantallas de la sección 10 ("El impostor quedó en pie · y él destruyó Civitas" para los demás, "¡Felicidades! Has eliminado a los demás jugadores · Has destruido Civitas con éxito" para el impostor). Un empate no expulsa a nadie y el juego sigue.

### Los botones REPORTAR y SABOTEAR a la izquierda
A la derecha estaban tapando el feed de Civitas (los comentarios de los ciudadanos, abajo a la derecha). Ahora `Online/disposicion_hud.py` (puro) decide dónde van, siempre a la izquierda:

| Escena | Dónde |
|---|---|
| Ciudad | abajo a la izquierda |
| Mazmorra o jefe con 2 jugadores | en el margen izquierdo, bajo el panel de J1 (uno sobre otro) |
| Mazmorra o jefe con 3 o 4 | en el rincón inferior izquierdo del cuarto (el margen es del panel de J3); con el "HUD detallado", encima del panel de misión |
| Terminal | REPORTAR chico, a la izquierda de la barra de controles |

### Cómo probarlo
1. Creen una sala: el lobby es el salón del hotel. Caminen hasta un carrito → `E` → prueben HAIR, SHIRT y PANTS; en la otra PC el avatar cambia al instante.
2. Inicien una partida de 2 y voten al inocente: sale "El impostor quedó en pie" en su PC y "¡Felicidades! Has eliminado a los demás jugadores" en la del impostor.
3. En la ciudad, el botón REPORTAR está abajo a la izquierda y ya no tapa el feed de la derecha.

Tests: `tests/test_lobby_online_hotel.py` (sala, se llega a cada estación, arte existente, botones sin tapar nada, HAIR/SHIRT/PANTS y el recoloreado) y los de `tests/test_fin_y_sabotaje_online.py` (2 jugadores).

---

## 14. Celular: feed en vivo y chat de la sala

### Qué hace
- Botón **CELULAR** (tecla **C**, clic, o **Share** en el control de PS4) en el modo Online: en la sala de espera y en la partida (ciudad, mazmorra y jefe). Con el celular cerrado, el botón muestra una **insignia roja** con los mensajes sin leer; cuando otro jugador escribe sale un **globo** junto al botón ("J2 · Candidato: hola") y suena `notificacion`.
- Al abrirlo sale un celular (el mismo estilo que la terminal tipo celular) con la app **Civitas** y dos pestañas:
  - **Inicio (feed en vivo):** arriba una **transmisión EN VIVO** (título, foto, "N mil viendo" que sube y un mini chat con mensajes aleatorios que van llegando). Debajo, publicaciones de ciudadanos, cuentas oficiales, rumores y campañas con **me gusta, compartidos y comentarios que suben en vivo**: el número salta cada fracción de segundo y sale un "+N" que sube y se desvanece. Bajo cada publicación, el último comentario. Arriba bajan banners de notificación ("Hugo Salas le dio me gusta a una publicación", "Tendencia en Ciudad Nova: #VerificaAntesDeCompartir").
  - **Me gusta y repost propios:** clic en el corazón o en el ícono de compartir. El ícono se llena con su color (rojo / cian), "salta" (crece y vuelve, con un anillo que se abre) y su número sube con el "+1". Otro clic lo quita. Son solo de esta PC.
  - **Abrir una publicación:** clic en la tarjeta. Se ve completa con **todos sus comentarios** (8 a 14 "de antes", más los que siguen llegando en vivo, que entran deslizándose) y abajo una caja **"Escribe un comentario..."**: Enter (o el botón) lo publica arriba de la lista. **Los comentarios de los jugadores viajan por la red y los ven todos**, con su foto de perfil y "J2 · Candidato" (el propio como "Tú"); el contador de comentarios sube con su "+1" en todas las PCs. Esc o la flecha "<" vuelven al feed.
  - **Chat (privados):** primero se ve la **lista de chats**, como en un celular: **Sala (todos)** y una fila por **cada jugador conectado**, con su **foto de perfil** (el retrato del personaje que eligió, recortado en la cara, con un anillo de su color), "J2 · Candidato", el último mensaje, cuándo llegó y la insignia de no leídos. Clic en un jugador abre el **chat privado** con él ("Chat privado" bajo su nombre): solo lo leen ustedes dos. Burbujas propias a la derecha (violeta), ajenas a la izquierda; en la sala, además, los avisos "J3 entró a la sala". Respuestas rápidas clicables: ¡Hola!, ¡Vamos!, Ayuda, Cuidado. Esc o "<" vuelven a la lista. El **expulsado** por votación (fantasma) solo lee: el host además lo silencia.
- **Con el celular abierto tu personaje se queda quieto** (no camina ni dispara), pero el mundo sigue: es Online, nadie pausa (en el host el combate de todos sigue corriendo). En la mazmorra y el jefe sale una franja ámbar: "Sigues en la mazmorra: tu personaje está quieto".
- Se cierra solo si empieza una reunión, una publicación del sabotaje, un diálogo, la pausa o la terminal.

### Controles (celular abierto)
| Acción | Teclado / ratón | Control |
|---|---|---|
| Abrir / cerrar | C (cerrar con C solo en Inicio), clic en el botón | Share |
| Cerrar | Esc, clic fuera del celular o en la flecha de arriba | ○ |
| Cambiar de app | Tab, clic en la pestaña | L1 / R1 |
| Desplazar | rueda, ↑ ↓, RePág / AvPág, Inicio/Fin = a lo nuevo | cruceta ↑ ↓ |
| Escribir / enviar | teclas / Enter o clic en enviar, Retroceso borra | — |
| Respuesta rápida | clic en el chip | cruceta ← → y ✕ |
| Me gusta / repost | clic en el corazón / en compartir | — |
| Abrir publicación / comentar / volver | clic en la tarjeta / escribir + Enter / Esc o "<" | — |

La "c" con la que se abre no se escribe en el chat (se traga ese TEXTINPUT durante 0.25 s). Con el celular abierto, R, Q, E, Esc y Enter son del celular: no convocan, no sabotean, no entran, no pausan y en la sala no inician ni salen.

### Dónde está el botón (`Online/disposicion_celular.py`)
| Lugar | Dónde |
|---|---|
| Sala de espera | píldora arriba a la derecha, sobre ROOM SETTINGS |
| Ciudad | abajo a la derecha, sobre el aviso "Civitas · Te mencionan" |
| Mazmorra o jefe, 2-3 jugadores | margen derecho bajo el panel de J2 (espejo de REPORTAR) |
| Mazmorra o jefe, 4 jugadores | rincón inferior derecho del cuarto |
| Terminal, resultados y finales | no hay celular |

### Cómo viaja por la red (host autoritativo)
- Mensaje nuevo **`CELULAR`** (`Online/protocolo.py`, `msg_celular`). El Servidor y el Cliente tienen un `CanalCelular` (`conexion.celular`) y `escribir_chat(texto)`.
- **`sync`:** al conectarse un invitado, el host le manda la semilla del feed, su reloj (segundos desde que abrió la sala) y el historial del chat. Luego anuncia "J2 entró a la sala"; al desconectarse, "salió".
- **`chat`:** el invitado manda el texto (y `para`: el id del destinatario si es privado); el host lo limpia, le pone como autor el **id de la conexión** (nadie escribe por otro), aplica el anti-spam (0.3 s por autor) y los silenciados (expulsados) y le da el número siguiente. Si es de la sala lo difunde a todos; si es **privado, solo se lo manda a sus dos jugadores** (y el SYNC de quien entra tampoco trae privados ajenos). Cada invitado lo inserta por número sin duplicar. CELULAR no pasa por la cola de mensajes del lobby ni por el ESTADO.
- **`comentario`:** el invitado manda `pub` (id de la publicación) y el texto; el host lo publica como mensaje de tipo `comentario` y lo difunde a todos. Como el feed es el mismo en todas las PCs, el id de la publicación también: el comentario cae en la misma publicación en cada pantalla.
- Cada mensaje lleva `d` (destinatario, solo los privados) y `p` (publicación, solo los comentarios). Los no leídos se cuentan **por chat** (`CanalCelular.leidos`: chat -> último número visto).
- **Todas las PCs ven el mismo feed sin mandarlo por la red:** el feed es una simulación determinista de (semilla, instante). Como todas usan la semilla y el reloj del host, a la misma hora muestran las mismas publicaciones con los mismos números.
- `VERSION_ESTADO = 5`: si una PC tiene el código viejo, sale el aviso "otra versión del juego".

### Estructuras de datos (para la exposición)
- **MinHeap** (`src/structures/min_heap.py`) como **cola de prioridad de eventos** del feed (`Online/feed_celular.py`): cada evento (publicación nueva, comentario, mensaje en vivo, notificación, nueva transmisión) va con su instante; `avanzar(t)` saca en orden los que ya tocan, O(log n) cada uno. El azar solo se usa al procesar eventos, en orden fijo: por eso da igual llegar a `t` en un paso o en mil, y todas las PCs coinciden.
- **Cola acotada** (`deque`) del chat ordenada por número + un **conjunto** de números: "¿ya lo tengo?" en O(1), descartar el más viejo en O(1) (`Online/chat_celular.py`).
- **Conjuntos** de silenciados y de "me gusta" propios: O(1). **Diccionario** autor → último mensaje (anti-spam) y diccionario de cifras animadas usado como caché LRU (`Online/celular.py`).
- **Comentarios "de antes"** de una publicación (`FeedCelular.comentarios_anteriores`): se generan con un `random.Random` propio sembrado con (semilla del feed, id de la publicación). No gastan el azar de la simulación, así el feed no cambia, y salen iguales en todas las PCs y cada vez que se abre. O(k) con k ≤ 14.
- **Conjuntos** `me_gusta` y `reposts`, **diccionario** id → comentarios propios y diccionario de "golpes" (clave → instante del clic) para la animación del ícono (`Online/celular.py`).
- Las estadísticas son una función pura y no decreciente del tiempo: `base + objetivo·(1 − e^(−edad/τ)) + goteo·tick`, por "ticks" de 0.35–0.9 s para que salten como en vivo.

### Archivos
- Nuevos (todos en `Online/`): `chat_celular.py` (chat y reloj compartido), `feed_celular.py` (feed en vivo), `datos/celular.json` (textos: publicaciones, comentarios, mensajes en vivo, transmisiones, notificaciones, hashtags y respuestas rápidas; también reutiliza ciudadanos, candidatos, cuentas y publicaciones de `content/campaign.json`), `celular.py` (estado de la interfaz), `disposicion_celular.py` (dónde va cada cosa), `celular_render.py` (dibujo y ratón; sin arte nuevo: primitivas, `src/ui/celular_render.py` y las ilustraciones de `assets/story/`), `celular_partida.py` (fachada `ControlCelular`, lo único que conocen Main y la sala).
- Modificados en `Online/` (solo agregados): `protocolo.py`, `servidor.py`, `cliente.py`, `sesion_red.py` (`VERSION_ESTADO`, `bloqueada` en las entradas locales, silenciados) y `lobby.py` (el celular en la sala).
- **Fuera de `Online/`, solo `Main.py`, con 8 agregados:** el import, crear el celular y `celular_disponible()`, dibujarlo al final de `presentar()`, mostrar el ratón con el celular abierto, pasarle los eventos (después de la reunión), actualizarlo cada cuadro, no caminar por la ciudad con el celular abierto y no dibujar la mira con el celular abierto. Sin conexión Online, `celular` es `None` y todo funciona como antes.

### Cómo probarlo
1. Las dos PCs con el **mismo código**: commit y `git pull` en las dos antes de probar.
2. Crear sala y unirse. En la sala, C (o el botón de arriba a la derecha) → pestaña Chat → escribir y Enter: el otro lo ve al instante. En Inicio, los números de las publicaciones suben y son los mismos en las dos pantallas.
3. Iniciar la partida: el chat sigue. Con el celular cerrado, un mensaje del otro trae el globo, el sonido y la insignia.
4. Abrirlo en una mazmorra: tu personaje se queda quieto (franja ámbar) y los enemigos siguen.

Tests: `tests/test_celular_chat.py`, `tests/test_celular_red.py` (red real en 127.0.0.1) y `tests/test_celular_partida.py` (loop real de Main y la sala: C abre, la "c" no se escribe, R no convoca, Esc no pausa ni sale de la sala, el clic en el botón abre en el Chat si hay no leídos, el sonido, la entrada local quieta y el cierre automático).

---

## 15. Vestidor ampliado: los 4 personajes se mezclan y 14 colores por parte

### Qué hace
- El vestidor (sala Online, y en local con V / △) tiene **7 pestañas**: **COLOR** (piel), **HAT** (cabeza), **SKIN** (cuerpo), **HAIR**, **SHIRT**, **PANTS** y **SHOES**. Teclas 1-7 o Tab.
- **HAT:** el peinado y la cara de cualquiera de los 4 personajes de Higgsfield (Ciudadano, Influencer, Periodista, Candidato). **SKIN:** el cuerpo de cualquiera de los 4, con su ropa, su pose y su accesorio (cartel, aro de luz, micrófono...). Con eso hay **16 personajes base**, y cada uno se tiñe con los colores de las demás pestañas.
- **Tu rol y tu habilidad no cambian**: el vestidor solo cambia cómo te ves.
- **Paletas de 14 colores** en COLOR, HAIR, SHIRT, PANTS y SHOES (antes 8-9), en 3 filas de 5 con AUTO. Los colores nuevos van al final de cada paleta: lo que alguien ya tenía guardado (`apariencias.json`) o manda una PC con la versión vieja sigue siendo el mismo color.
- Se ve en la sala, la selección de roles, la revelación del rol, la ciudad, las mazmorras, la reunión y la foto de perfil del celular (que usa la cara elegida en HAT).

### Sin arte nuevo: se recombinan las hojas que ya existen
`src/ui/mezcla_jugador.py` (puro) usa el **mapa de partes** de cada hoja (`assets/sprites/jugadores/<rol>.partes.png`):
1. **Cuello** = primer renglón con ropa; **columnas de la cabeza** = las del pelo por encima del cuello (así las manos levantadas no cuentan).
2. Del cuadro del cuerpo se borra su cabeza y se pega la elegida, alineada por el centro del pelo y el cuello: pelo, cara, los contornos que los tocan y la melena que cae por debajo. Las manos y el accesorio del otro personaje no se copian.
3. El mapa de partes se compone igual, así la mezcla se tiñe como una hoja original.
Se hace una vez por combinación y por cuadro (`quieto`, `paso_a`, `paso_b`, `dash`) y queda en caché (`src/ui/sprites.py`: `_datos_de`, `_componer_datos`).
Los **retratos grandes de Higgsfield** (vista previa del vestidor, selección de roles, lobby) también tienen mapa de partes y se mezclan igual (`_retrato_mezclado`), así se ven **nítidos** y no el sprite pixelado. Como son mucho más grandes, los márgenes del corte crecen con `escala` (alto del retrato / 40). Para que no se cuelen pedazos del otro personaje:
- de los píxeles sin parte solo se copia el contorno oscuro y lo que queda encerrado entre pelo o cara (ojos, lentes): el cartel y el aro de luz, que son claros, no;
- junto al cuello, solo el contorno con cara justo encima (la barbilla), no el del cuello de la camisa;
- se borra la melena del cuerpo que caía sobre los hombros;
- al final se queda solo la pieza conectada más grande (BFS), que es la cabeza: lo que quedó suelto se descarta.
Pueden quedar uno o dos trazos finos junto al cuello en algunas combinaciones.

### Archivos
- Nuevo: `src/ui/mezcla_jugador.py`.
- Agregados fuera de `Online/` (obligatorios: el dibujo del jugador se usa en todo el juego): `src/ui/sprites.py` (la hoja mezclada), `src/core/assets.py` (colores nuevos al final de cada paleta) y el texto de ayuda "1-7" del vestidor local en `Main.py`.
- En `Online/`: `personalizacion.py` (HAT, SKIN y los nombres de los colores nuevos), `personalizacion_render.py` (7 pestañas, casillas de 84 px, vistas de HAT y SKIN), `lobby.py` (teclas 1-7) y `celular_render.py` (la foto de perfil con la cara elegida).
- Tests: `tests/test_apariencia.py` (las 16 combinaciones, la mezcla y el retrato) y los del vestidor actualizados.

---

## 16. Jugar el Online con el PC y con el control de PS4

### Qué hace
En cada PC se puede jugar **con teclado y ratón, con el control de PS4 o con los dos a la vez**, en todo el modo Online. El control se detecta solo, y si se conecta (o se desconecta) a mitad de la partida, el juego lo toma sin reiniciar.

| Pantalla | Control de PS4 |
|---|---|
| Crear o unirse | cruceta o stick ← → eligen, ✕ confirma, ○ vuelve |
| Código de sala | ↑ ↓ eligen la letra (se ve en una cajita al lado), ✕ o → la agregan, △ o ← borran, START conecta, ○ vuelve |
| Error de conexión | ✕ u ○ vuelven |
| Sala de espera | stick o cruceta caminan, ✕ = E (vestidor cerca de un carrito, si no la recepción de roles), cruceta ← → cambian de rol, START inicia (host), Share abre el celular, ○ cierra la recepción (nunca sale de la sala: eso es Esc) |
| Vestidor | cruceta elige, L1 / R1 cambian de pestaña, ✕ / ○ / △ cierran |
| Ciudad | el **stick izquierdo camina** (antes solo WASD), ✕ entra al edificio, □ o R1 REPORTAR, △ SABOTEAR, Share el celular, START la pausa |
| Combate | stick izquierdo mueve, stick derecho apunta, R2 dispara, L1 habilidad, ✕ dash (lo de siempre) |
| Terminal, reunión, publicación del sabotaje, diálogos | cruceta y ✕ (lo de siempre) |
| Resultado de la mazmorra, investigación, victoria y derrota | ✕ = Enter y la cruceta = flechas (antes esperaban el teclado). ○ no se traduce a Esc: en la victoria Esc cierra el juego |

Con un control conectado, la barra de controles de las pantallas del Online muestra los botones del control.

### Cómo está hecho
- **Nuevo `Online/mando_online.py`:** abre el control con la API GameController de SDL (la misma del resto del juego) y **traduce cada botón a la tecla que ya hace lo mismo** (`como_tecla`, con una tabla por pantalla: `MENU`, `SALA`). Así las pantallas del lobby no duplican su lógica. El stick como flecha da una pulsación por inclinación. `direccion()` suma el stick (con zona muerta) y la cruceta para caminar por la sala.
- **`Online/lobby.py`:** cada pantalla pasa sus eventos por `como_tecla`; el código de sala tiene su selector de letras; la sala camina con `direccion()` si no hay teclas y usa `evento_vestidor_mando` con el vestidor abierto.
- **`Online/sesion_red.py`:** `_revisar_mando` (en `EntradaTecladoRed` y `EntradaLocalCliente`) busca un control cada ~1 s mientras no hay uno conectado; `mando_local_online(sesion)` da el control de esta PC para caminar por la ciudad.
- **Fuera de `Online/`, solo `Main.py` (agregados):** el import, `mando=mando_local_online(sesion)` al caminar por la ciudad (en una partida local es None: el control es del J2) y, en las pantallas de resultado del Online, postear la tecla equivalente al botón.
- Tests: `tests/test_mando_online.py` (traducción, stick, cada pantalla del lobby con eventos del control, la sala, el control en caliente y las pantallas de resultado).

### Corrección: la ✕ en la ciudad sacaba de la partida
- **El bug:** en `Main._jugar`, la ✕ (o □) en la ciudad llamaba a `partida.entrada_cercana(...)` y `campania.zona_desbloqueada(...)`, que **no existen**. El error lo atrapaba la protección del Online (`proteger_partida_online`) y la partida volvía al menú: parecía que el control "te sacaba". Lo dejó `Online/errores_online.log` (`AttributeError: 'Partida' object has no attribute 'entrada_cercana'`).
- **La corrección:** la ✕ en la ciudad ahora postea la tecla E, así hace exactamente lo mismo que el teclado: la baliza de la misión, la Alcaldía sellada, el fantasma y, en el invitado, pedirle la entrada al host.
- **Para que no vuelva a pasar:** `tests/test_mando_online.py` aprieta **todos los botones y ejes del control** en el loop real de Main (ciudad, mazmorra y terminal; como host y como invitado; con el celular y la reunión activos), en la pausa y en la sala de espera, y falla si algo se atrapa como error o la partida se cierra. También prueba que la ✕ frente a la puerta del Colegio entra a la mazmorra.

---

## 17. Personajes animados (caminar, respirar, parpadear y darse vuelta)

### Qué cambió
Antes cada personaje de Higgsfield tenía 4 cuadros (quieto, paso_a, paso_b, dash): al caminar solo cambiaban los pies y quieto era una foto. Ahora, en todo el juego (sala de espera, ciudad, mazmorras, jefe; Online y local):
- **Caminar (8 cuadros):** en cada pisada el cuerpo baja un píxel y la cabeza lo sigue con un cuadro de retraso, y entre pisadas sube: un rebote con peso. Mismo ritmo de paso de antes (600 ms).
- **Quieto:** respira (los hombros bajan y suben despacio) y **parpadea** cada tanto (a veces dos veces seguidas). Al Periodista no lo hace parpadear: sus lentes confunden la búsqueda de los ojos y es mejor ojos abiertos que una mancha.
- **Dash:** el cuerpo se agacha (impulso).
- **Se da vuelta:** en combate mira hacia donde apunta; en la ciudad y en la sala, hacia donde caminó por última vez. En la sala, los jugadores de las otras PCs también animan el paso cuando se mueven (antes se deslizaban quietos).

### Sin arte nuevo
`src/ui/animacion_jugador.py` (puro) arma los ciclos desde los 4 cuadros con el **mapa de partes** de cada hoja:
- `zonas`: el cuello (primer renglón con ropa) y la cadera (primer renglón con pantalón).
- `bajar`: corre hacia abajo lo que está arriba de un renglón (el cuerpo sobre la cadera, o la cabeza sobre el cuello) dejando fijas las piernas.
- `ojos` / `parpadear`: los ojos son píxeles sin parte encerrados por piel en la franja de la cara (agrupados con BFS); al cerrar, se tapan con la piel de al lado y su renglón de abajo queda como párpado. Solo si encuentra dos ojos parecidos a la misma altura.
- `ciclos`: caminar, respirar y dash, cada cuadro con su duración.
Se arma una vez por personaje, colores y escala (caché en `src/ui/sprites.py`, ~0.15 s para los 4 personajes), y funciona igual con los vestidores (colores, HAT y SKIN).

### Archivos (fuera de `Online/`, porque el dibujo del jugador es de todo el juego)
- Nuevo: `src/ui/animacion_jugador.py` y `tests/test_animacion_jugador.py`.
- `src/ui/sprites.py`: la hoja de cada personaje sale de los ciclos; `sprite_jugador(..., mirando_izquierda=)` y `mira_izquierda(dueño, x)`.
- `src/entities/player.py` (combate), `src/ui/ciudad_render.py` y `Main.py` (los otros jugadores en la ciudad): pasan hacia dónde mira. `src/core/assets.py`: `UMBRAL_GIRO_JUGADOR` y `UMBRAL_GIRO_APUNTADO`.
- En `Online/`: `lobby.py` (cada jugador de la sala mira hacia donde camina y los remotos animan el paso).

---

## 18. Mazmorras más difíciles con 2 a 4 jugadores

### Qué cambió
Antes cada cuarto sacaba siempre 2, 3 o 5 enemigos según su toxicidad, jugara uno o cuatro. Ahora **cada jugador además del primero suma enemigos a cada cuarto, en proporción a su toxicidad**: a toxicidad 0 suma 0.4 de enemigo por jugador y a toxicidad 100, 1.0 (redondeado). Vale en el Online y en el cooperativo local.

| Toxicidad del cuarto | 1 jugador | 2 | 3 | 4 |
|---|---|---|---|---|
| baja (ej. 20) | 2 | 3 | 3 | 4 |
| media (ej. 50) | 3 | 4 | 4 | 5 |
| alta (ej. 90) | 5 | 6 | 7 | 8 |

- **Solo cambia la cantidad.** La velocidad, los tipos (perseguidor / tirador / curandero, con las mismas proporciones de `composicion_cuarto`), el jefe, la entrada (sigue sin enemigos) y el juego en solitario quedan igual.
- **Sin saturar:** ningún cuarto pasa de `MAX_ENEMIGOS_CUARTO = 8`. Un cuarto (1000x560) admite 10 enemigos separados al menos 80 px, así que con 8 siguen apareciendo separados (`SEPARACION_MIN_SPAWN_ENEMIGOS`) y lejos de la puerta por donde entra el equipo.
- En el Online la cuenta la hace el host (el invitado copia sus enemigos por id), así todas las PCs ven los mismos.

### Archivos (fuera de `Online/`: el combate es de todo el juego)
- `src/core/balance.py`: `EXTRA_ENEMIGOS_JUGADOR_SIN_TOXICIDAD = 0.4`, `EXTRA_ENEMIGOS_JUGADOR_TOXICIDAD_MAXIMA = 1.0` y `MAX_ENEMIGOS_CUARTO = 8` (para ajustar la dificultad se cambian solo estos números).
- `src/dungeon/clasificador_toxicidad.py`: `enemigos_para_equipo(dificultad, toxicidad, jugadores)` (pura, O(1)).
- `src/dungeon/mazmorra_jugable.py`: guarda cuántos juegan (`colocar_en_entrada`) y cada cuarto nuevo usa `enemigos_para_equipo`.
- Tests: `tests/test_enemigos_por_equipo.py` (la tabla, que crece con la toxicidad y los jugadores, el tope, la entrada y el solitario sin cambios, y una mazmorra real con 1 y con 4 jugadores, con los enemigos separados).

---

## 19. Habilidades especiales: la Burbuja del Ciudadano ya funciona

### Cómo estaban
Se probó cada habilidad (F / L1, con la barra llena) en un cuarto real:
- **Influencer** (atrae a los enemigos): ya funcionaba, fuerza el aggro de los enemigos cercanos.
- **Periodista** (rayo perforante): ya funcionaba, atraviesa enemigos y rompe el escudo del jefe.
- **Candidato** (proyectiles rebotantes): ya funcionaba, dispara 3 balas que rebotan.
- **Ciudadano** (Burbuja Comunitaria): **no hacía nada**. Solo prendía un flag y dibujaba el domo, pero las balas lo atravesaban y no curaba.

### Qué hace ahora la Burbuja Comunitaria
Durante `DURACION_BURBUJA = 4 s`, alrededor del Ciudadano:
- **Frena las balas enemigas** (también las del jefe) que entran al domo. Se deshacen con unas partículas del color de la burbuja.
- **Cura a los aliados que estén adentro**, incluido el Ciudadano: `CURACION_BURBUJA_POR_S = 0.5` de vida por segundo (2 de vida en los 4 s), sin pasar de la vida máxima.
- A un caído no lo levanta (para eso está revivir). Al expulsado (fantasma) no lo toca. Si el Ciudadano cae, el domo deja de proteger.
- El radio pasó de 70 a `RADIO_BURBUJA = 110` px, para que entren uno o dos compañeros.

### En el Online
- El host decide (frena las balas y cura). La vida y las balas llegan a todos en el ESTADO, como siempre.
- **Nuevo:** el ESTADO manda también cuánto le queda a la burbuja (`"bur"` en los extras de cada jugador). Así todas las PCs ven el domo del Ciudadano, no solo la suya.
- Es un campo agregado. Si falta, no se toca nada.

### Archivos (fuera de `Online/`, porque el combate es de todo el juego)
- Nuevo: `src/entities/burbuja.py` (`aplicar_burbujas(jugadores, proyectiles_enemigos, dt)`, pura y O(b·(p+j))).
- `Main.py` (`_frame_de_combate`): la llama justo después de mover las balas enemigas. Es una línea más; lo demás queda igual.
- `src/core/balance.py`: `CURACION_BURBUJA_POR_S = 0.5`. `src/core/assets.py`: `RADIO_BURBUJA` 70 a 110.
- `src/entities/player.py`: solo el docstring del Ciudadano. `docs/ARQUITECTURA.md`: la línea del Ciudadano.
- En `Online/`: `sesion_red.py` (`_datos_extra` manda `"bur"` y el invitado lo aplica en `_aplicar_jugadores`).
- Tests: `tests/test_burbuja.py`:
  - frena las balas de adentro y deja las de afuera;
  - cura sin pasar el máximo;
  - no levanta caídos ni toca fantasmas;
  - se apaga con el tiempo;
  - el frame de combate real: la bala no le llega al Ciudadano y este se cura;
  - el domo viaja por la red.

---

## 20. Capítulos del más fácil al más difícil y mobs con más vida

### El problema
La dificultad de cada mazmorra sale de su toxicidad, y estaba al revés:
- el **Capítulo 1 (Colegio)** era el más tóxico (85, tramo alto: 5 enemigos rápidos);
- el **Capítulo 3 (Empresa de Medios)** era el menos tóxico (15, tramo bajo).

Además los mobs morían en 1 a 3 segundos.

### 1. Orden de los capítulos
Se **intercambiaron los reportes** de toxicidad del Colegio y de la Empresa de Medios (`REPORTES_POR_ZONA` en `src/core/balance.py`). Son los mismos reportes, cambiados de zona. El Hospital no se tocó.

| Capítulo | Zona | Toxicidad | Tramo (enemigos y velocidad) |
|---|---|---|---|
| 1 | Colegio | 15 | bajo: 2 enemigos, x0.8 |
| 2 | Hospital | 50 | medio: 3, x1.0 (igual que antes) |
| 3 | Empresa de Medios | 85 | alto: 5, x1.3 |
| 4 | Alcaldía (jefe) | 100 | máxima (igual que antes) |

La historia, los diálogos y el orden en que se juegan los capítulos no cambian. Lo que acompaña a la toxicidad de cada zona la sigue, como siempre:
- el color y el texto "Toxicidad N" del mapa;
- la dificultad que dicen las instrucciones antes de entrar;
- los titulares del cintillo;
- la cantidad de grafitis de los cuartos.

### 2. Vida de los mobs según la toxicidad
Cada mob nace con la vida de su tipo o variante **multiplicada por la toxicidad del cuarto** donde aparece. La toxicidad es la de ese cuarto, con la propagación incluida. El multiplicador va de x1.5 (toxicidad 0) a x2.5 (toxicidad 100), redondeado y nunca menos que la vida base.

| Vida base | Cap. 1 (15) | Cap. 2 (50) | Cap. 3 (85) | Súbditos del jefe (100) |
|---|---|---|---|---|
| 2 (tiradores, curanderos, ...) | 3 | 4 | 5 | 5 |
| 3 (Hellhound, Demon_A, ...) | 5 | 6 | 7 | 8 |
| 5 (Minotaur) | 8 | 10 | 12 | 13 |
| 6 (Black Knight_C) | 10 | 12 | 14 | 15 |

- Lo único que cambia es la vida. La cantidad de enemigos, su velocidad, el daño, los tipos y el jefe (`VIDA_JEFE = 120`) quedan igual.
- La cura del curandero sigue siendo una fracción de la vida máxima (`FRACCION_CURA`), así que cura en proporción.
- Se suma con la sección 18: con 2 a 4 jugadores, además, hay más mobs por cuarto.
- **En el Online** los mobs los crea el host. El ESTADO ya mandaba `vida` y `vmax` de cada enemigo y súbdito, así que el invitado ve las mismas barras de vida sin cambiar nada de la red.

### Archivos (fuera de `Online/`: el combate es de todo el juego)
- `src/core/balance.py`:
  - `REPORTES_POR_ZONA`: Colegio y Medios intercambiados.
  - Nuevos `VIDA_ENEMIGO_MULT_SIN_TOXICIDAD = 1.5` y `VIDA_ENEMIGO_MULT_TOXICIDAD_MAXIMA = 2.5`. Para ajustar la vida se cambian solo estos dos números.
- `src/dungeon/clasificador_toxicidad.py`: nuevas `vida_por_toxicidad(vida_base, toxicidad)` y `reforzar_con_toxicidad(enemigo, toxicidad)`, puras y O(1).
- `src/dungeon/cuarto.py`: los mobs de cada cuarto nacen con `reforzar_con_toxicidad`.
- `src/dungeon/arena_jefe.py`: los súbditos del jefe, igual, con toxicidad 100.
- Tests:
  - `tests/test_grafo_ciudad.py`: el test del orden ahora espera Colegio bajo, Hospital medio y Medios alto.
  - Nuevo `tests/test_dificultad_capitulos.py`:
    - la toxicidad sube con el número de capítulo;
    - solo se intercambiaron los reportes;
    - la tabla de vida, que crece con la toxicidad;
    - los mobs de mazmorras reales traen la vida de su cuarto;
    - la velocidad y la cantidad no cambian;
    - el enemigo suelto y el jefe no cambian, y los súbditos se refuerzan.
- Verificado: suite completa en verde (1904) y la campaña completa de principio a fin (`test_campania_completa`, corrida con UTF-8) también.
