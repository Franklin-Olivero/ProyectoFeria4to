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
- Escucha en el puerto `5000` (configurable) y obtiene automáticamente la IP local de la máquina.
- Usa sockets no bloqueantes (`timeout=0.1`) para permitir la detención limpia sin congelar la ventana.
- Mantiene una instancia de `GrafoSala` para registrar al Host y al Invitado.

### 📄 `Online/cliente.py`
Cliente TCP para el Invitado:
- Se conecta a la IP y puerto especificados por el usuario.
- Ejecuta un hilo lector en segundo plano que acumula los mensajes entrantes en una cola.
- Provee métodos simples como `enviar_rol()`, `enviar_input()` y `leer_mensajes()`.

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
1. **PC 1 (Host):** Crear sala. La pantalla indicará la IP local (ej. `192.168.1.35`).
2. **PC 2 (Invitado):** Unirse ingresando esa misma IP.

### Validación de Tests
Para verificar que ningún cambio rompió el juego base ni los tests del sistema:
```powershell
pytest tests/
```
*(Todos los 535 tests pasan exitosamente).*
