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
Las 4 cajas de la sala de espera (`VESTIDOR-01` a `VESTIDOR-04`) son vestidores. Al acercarse a una, la caja se ilumina y aparece **"Presiona [E] o Click: Vestidor"**. Se abre un modal como el de Among Us, con tres pestañas:

| Pestaña | Qué cambia | Opciones |
|---|---|---|
| **COLOR** | Tono de piel (cara y manos) | AUTO + 8 tonos |
| **HAT** | La parte de arriba: pelo, cara y lentes | AUTO + la cabeza de cada uno de los 4 roles |
| **SKIN** | El traje: camisa, pantalón y zapatos | AUTO + el traje de cada uno de los 4 roles |

- **AUTO** = lo de tu rol: quien nunca usa un vestidor se ve igual que siempre, y si cambias de rol en la laptop, lo que esté en AUTO cambia solo.
- El **accesorio** (megáfono, palo selfie, micrófono, mano) siempre es el de tu **rol**, porque identifica su habilidad.
- Los cambios se equipan al instante y **toda la sala los ve** (en su avatar del lobby). La apariencia también se ve **durante la partida**: en Ciudad Nova y en combate, en todas las PCs.
- Controles: flechas/WASD eligen, `Tab` / `1-3` cambian de pestaña, clic en una casilla o pestaña, `E` / `Esc` / `Enter` (o clic fuera / en la X) cierran.

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
Al final de cada mazmorra normal el equipo comparte un cursor sobre el árbol de decisión: cualquiera lo mueve (← →) o confirma (Enter). El impostor también, pero **cada movimiento suyo es un sabotaje** y solo puede hacerlo con la carga lista. La carga tarda **15 s** (`balance.COOLDOWN_SABOTAJE_IMPOSTOR`) en llenarse al abrir la terminal y después de cada uso. Así los demás siempre tienen 15 s para buscar la respuesta correcta antes de que el impostor pueda mover el cursor a una mala o confirmar.

- Solo el impostor ve su indicador, arriba al centro de la terminal: "Recargando: N s", "Listo: mueve o confirma una opción", y "Aún no" si aprieta con la carga vacía. Su barra de controles dice "sabotear".
- Los demás no ven nada distinto: tienen que descubrir quién mueve el cursor.
- Fuera de la terminal (por ejemplo, la investigación del capítulo 3) el impostor navega libre.

### Host autoritativo
- `Online/sabotaje.py` (puro): `Sabotaje` con `seguir_terminal(terminal)` (una terminal nueva empieza con la carga vacía), `actualizar(dt)`, `listo` e `intentar()` (gasta la carga si estaba lista). O(1).
- `AdaptadorOnlineHost.puede_navegar(indice)`: descarta los `DECISION_NAV` del impostor sin carga, antes de cargarle la decisión (`registrar_actor`). Main usa el mismo método para las teclas del host cuando el impostor es él.
- El host manda la carga en el ESTADO (`term.sab`) y cada invitado la refleja (`AdaptadorOnlineJoin.puede_navegar` y `restante_sabotaje`) solo para no mandar teclas en vano y dibujar el indicador.

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
