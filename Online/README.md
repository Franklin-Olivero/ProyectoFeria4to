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
  - `LOBBY`: Actualización del estado de la sala (nodos del grafo, roles elegidos).
  - `ELEGIR_ROL`: Envío de la selección o confirmación de rol.
  - `INICIAR`: Comando emitido por el host para arrancar la partida cuando todos están listos.
  - `INPUT`: Envío de teclas, dirección y botones del jugador invitado hacia el host.
  - `ESTADO`: Snapshot con posiciones y vidas enviado desde el host al invitado.
  - `DESCONEXION`: Notificación de desconexión limpia.
- **Clase `GrafoSala`:** Implementación orientada a grafos para gestionar jugadores, adyacencias y estados de confirmación.

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
- **Función integradora `menu_online()`:** Orquesta todo el flujo previo a la partida y retorna las clases elegidas y la conexión de red activa.

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

**Pendiente (no es parte de este cambio):** al iniciar la partida, la pantalla del invitado todavía no se sincroniza con la del Host (`AdaptadorOnlineJoin` no se usa y el Host no llama a `enviar_estado()`): el invitado juega su propia partida local.

### Validación de Tests
Para verificar que ningún cambio rompió el juego base ni los tests del sistema:
```powershell
pytest tests/
```
*(Todos los 549 tests pasan exitosamente).*
