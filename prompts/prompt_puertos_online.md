# Prompt para Opus 5.5: encontrar un puerto que funcione en la red de la universidad

Copia todo lo que está debajo de la línea y pégalo en Claude Code (modelo Opus 5.5), abierto en `ProyectoFeria4to`.

---

Estoy en la red WiFi de la universidad y el modo Online de Civitas no conecta: la red bloquea algunos puertos TCP entre laptops. Hoy el juego usa siempre el puerto **7777** (`PUERTO_DEFAULT` en `Online/servidor.py`). Quiero que pruebes distintos puertos hasta encontrar uno que deje jugar de verdad entre dos laptops, y que el juego lo use.

## Reglas

- Trabaja dentro de `Online/`. Toca algo fuera solo si es obligatorio.
- No agregues sprites ni assets. No hagas commit. No cambies la configuración de git.
- Responde en español informal. Documenta todo en `Online/README.md` (una sección nueva).
- No abras puertos en el firewall de Windows sin decírmelo antes: eso pide permisos de administrador.
- No intentes saltarte la seguridad de la red de la universidad (nada de túneles ni VPN escondidas). Solo se prueban puertos TCP normales de la red local.

## Lo que hay que averiguar primero

1. Lee `Online/servidor.py`, `Online/cliente.py`, `Online/codigo_sala.py` (el código de sala se arma con la IP y el puerto), `Online/lobby.py` (pantalla de unirse, `resolver_entrada`) y `Online/firewall.py` / `Online/red_local.py` (diagnóstico y reglas de firewall).
2. Revisa si el problema es el puerto o es otra cosa, porque muchas redes de universidad bloquean la comunicación entre equipos (aislamiento de clientes) sin importar el puerto. Con un script de diagnóstico, prueba en la misma laptop y luego entre las dos:
   - ¿Un `ping` a la IP del host responde desde la otra laptop?
   - ¿Un puerto abierto en el host se alcanza desde la otra laptop (`Test-NetConnection -ComputerName <ip> -Port <p>`)?
   Dime qué pasa antes de seguir. Si ni el ping ni ningún puerto llegan, el problema es el aislamiento de la red y cambiar de puerto no lo arregla: en ese caso propón alternativas (hotspot del celular, otra red) y para ahí.

## Lo que hay que construir (si el problema sí es el puerto)

1. **Herramienta de prueba de puertos** en `Online/sondeo_puertos.py` (lógica pura, sin pygame, con tests):
   - Una lista de candidatos ordenada por probabilidad de estar permitida en redes de universidad: 443, 80, 8080, 8443, 3389, 53, 22, 25565, 5000, 8000, 8888, 9999, 7777 y algunos más altos (por ejemplo 50000 a 50010).
   - Modo **host**: abre un servidor de prueba por cada puerto candidato (uno a la vez o varios) y responde a un mensaje corto.
   - Modo **invitado**: dada la IP del host, prueba conectarse a cada puerto con un tiempo de espera corto (1 a 2 s) y manda un "hola"; devuelve qué puertos respondieron.
   - Que se pueda correr desde la terminal en las dos laptops (`python -m Online.sondeo_puertos host` y `python -m Online.sondeo_puertos invitado <ip>`) y que imprima una tabla clara: puerto, resultado (abierto, bloqueado, sin respuesta) y el tiempo.
   - Aviso: los puertos por debajo de 1024 en Windows suelen necesitar permisos o ya están en uso; si falla abrirlos, pasar al siguiente sin romperse.
2. **Que el juego use el puerto que sirvió**:
   - El host elige el primer puerto libre de la lista de candidatos que le funcione (no solo 7777) y lo muestra en el panel de la sala.
   - El **código de sala** debe llevar el puerto, para que el invitado no tenga que escribirlo. Mira cómo `Online/codigo_sala.py` codifica hoy la IP y mantén compatibilidad con los códigos viejos (puerto 7777).
   - El invitado, si no logra conectar al puerto del código, prueba los demás candidatos antes de rendirse, con un mensaje claro en pantalla ("Probando puerto 8080...").
   - El diagnóstico del lobby (firewall) debe hablar del puerto real y no de un 7777 fijo (`Online/firewall.py`, `lobby.py` líneas donde sale "TCP 7777").
3. **Tests** en `tests/` con sockets reales en `127.0.0.1`: el sondeo detecta un puerto abierto y uno cerrado, el host salta un puerto ocupado, el código de sala con puerto ida y vuelta, compatibilidad con códigos viejos, y el invitado que reintenta con otro puerto. Corre la suite completa al final (`python -m pytest -q -p no:cacheprovider`) y dime el resultado real.

## Cómo entregarlo

1. Primero diagnostica y cuéntame en pocas líneas qué encontraste (puerto bloqueado o aislamiento de red).
2. Luego implementa, prueba y documenta.
3. Dime exactamente qué comandos corro yo en cada laptop de la universidad para ver cuál puerto sirve, y qué debo hacer después (por ejemplo, "haz commit y `git pull` en la otra laptop").
4. Al final, un resumen corto: qué cambió, qué probaste de verdad (y qué no se pudo probar sin las dos laptops) y qué pendientes quedan.
