

---


## 6) Node‑RED: montar tu primer flow para ver y enviar datos

En este apartado vamos a construir, paso a paso, un **flow** en Node‑RED.  
El objetivo es que puedas:

1. Recibir los datos que envía tu ESP8266 por MQTT.
2. Comprobar que esos datos llegan bien.
3. Extraer solo la parte que nos interesa, por ejemplo la temperatura.
4. Mostrar esos datos en una página web llamada **Dashboard**.
5. Enviar órdenes al ESP8266, por ejemplo para encender o apagar un LED.

Piensa en Node‑RED como una cadena de montaje:

- Un nodo **recibe** los datos.
- Otro nodo los **muestra** para revisarlos.
- Otro nodo los **transforma**.
- Otro nodo los **enseña en pantalla**.
- Y otro nodo puede **enviar órdenes** de vuelta al ESP8266.


### 6.1 ¿Qué es Node‑RED?

Node‑RED es una herramienta visual para crear programas uniendo bloques llamados **nodos** con líneas.  
Cada nodo hace una tarea concreta, y al unir varios nodos construimos un **flow**, es decir, un flujo de trabajo.

Una forma sencilla de entenderlo es pensar en piezas de LEGO:

- cada pieza hace algo,
- tú decides en qué orden colocarlas,
- y al final todas juntas forman un sistema completo.

En este proyecto, Node‑RED será nuestro **panel de control** del ESP8266.


### 6.2 Antes de empezar

Antes de abrir Node‑RED, comprueba lo siguiente:

- El ESP8266 ya tiene MicroPython instalado.
- El programa del ESP8266 ya está funcionando.
- La placa ya se conecta al WiFi.
- La placa ya está enviando datos por MQTT.

Si en la consola del ESP8266 ves mensajes parecidos a estos:

```text
[wifi] connected
[mqtt] publish OK
```

entonces ya puedes seguir con este apartado.

### 6.3 Qué es un flow

Un **flow** es un conjunto de nodos conectados entre sí.

En esta práctica vamos a crear **dos flows**:

#### Flow 1: recibir y mostrar datos

Este flow servirá para recibir los datos del sensor y enseñarlos en una web.

```text
mqtt in  →  debug  →  function  →  ui_gauge / ui_text
```


#### Flow 2: enviar órdenes al ESP8266

Este flow servirá para mandar órdenes desde Node‑RED a la placa.

```text
inject o ui_switch  →  mqtt out
```


### 6.4 Qué es MQTT en esta práctica

MQTT es un sistema de mensajería.

Los dispositivos envían y reciben mensajes usando “canales” llamados **topics**.

Por ejemplo:

- un topic puede servir para enviar los datos del sensor,
- y otro topic distinto puede servir para enviar órdenes.

Imagina que cada topic es como un buzón con una etiqueta:

- en un buzón se meten los datos del BMP280,
- en otro buzón se meten las órdenes del LED.

Node‑RED “escucha” el buzón correcto y recoge los mensajes que llegan.

### 6.5 Abrir Node‑RED y reconocer la pantalla

Cuando abras Node‑RED verás tres zonas principales:

#### 1) Paleta de nodos

Suele estar en la parte izquierda.
Aquí aparecen los bloques que puedes arrastrar al espacio de trabajo.

Por ejemplo, verás nodos como:

- `mqtt in`
- `debug`
- `function`
- `json`
- `mqtt out`
- `ui_text`
- `ui_gauge`
- `ui_switch`
- `inject`


#### 2) Espacio de trabajo

Está en el centro.
Aquí es donde colocas los nodos y los conectas con líneas.

#### 3) Barra lateral derecha

Aquí aparecen varias pestañas.
La más importante al principio es la pestaña **Debug**, porque ahí verás los mensajes que recibe tu flow.


### 6.6 Primer objetivo: comprobar que llegan datos

Antes de construir paneles bonitos, medidores o botones, lo primero es comprobar que los datos **de verdad están llegando**.

Para eso vamos a crear el flow más simple posible:

```text
mqtt in  →  debug
```

Este primer flow no transforma ni muestra nada en el Dashboard.
Solo sirve para asegurarnos de que Node‑RED está recibiendo mensajes del ESP8266.



### 6.7 Primer nodo: `mqtt in`

Arrastra un nodo `mqtt in` al espacio de trabajo.

Ahora haz doble clic sobre él para configurarlo.

#### Qué debes configurar

##### A) Server

Aquí debes indicar el servidor MQTT, también llamado **broker**.

El broker es el “repartidor” de mensajes.
Si el broker no es correcto, Node‑RED no recibirá nada.

##### B) Topic

Aquí debes escribir el topic donde publica tu ESP8266.

Ejemplo:

```text
cabrerapinto/meteorologia/ecfabca5f251/bmp280
```

Cada placa o cada grupo puede tener un topic diferente, así que copia exactamente el tuyo.

#### Consejo útil

Si al principio no recuerdas el topic exacto, a veces puedes usar un topic más general con `#`, por ejemplo:

```text
cabrerapinto/#
```

Eso significa: “escucha cualquier subtopic que empiece por `cabrerapinto/`”.

**Pero cuidado:** eso está bien para pruebas, pero cuando ya funcione, lo mejor es usar el topic exacto de tu ESP8266 para no mezclar tus mensajes con los de otros compañeros.

### 6.8 Segundo nodo: `debug`

Ahora arrastra un nodo `debug` y conéctalo a la salida del nodo `mqtt in`.

El nodo `debug` sirve para mostrar en la barra lateral derecha el contenido de los mensajes que recibe.

Es muy parecido a usar `print()` en Python:

- no cambia el mensaje,
- no lo arregla,
- solo te enseña qué está pasando.


#### Qué debes hacer ahora

1. Conecta `mqtt in` con `debug`.
2. Pulsa el botón **Deploy** arriba a la derecha.
3. Mira la pestaña **Debug** en la barra lateral.

Si todo está bien, deberían empezar a aparecer mensajes.


### 6.9 Qué aspecto puede tener el mensaje

Un mensaje típico puede ser parecido a este:

```json
{
  "esp": {
    "ip": "10.53.151.83",
    "rssi": -62
  },
  "sensor": {
    "bmp280": {
      "t_c": 22.45,
      "p_hpa": 1012.80
    }
  }
}
```

Vamos a entenderlo paso a paso.

#### Nivel 1: el mensaje completo

Tiene dos partes grandes:

- `esp`
- `sensor`


#### Nivel 2: la parte `esp`

Dentro de `esp` hay información sobre la placa, por ejemplo:

- `ip`
- `rssi`


#### Nivel 2: la parte `sensor`

Dentro de `sensor` hay otra parte llamada `bmp280`.

#### Nivel 3: la parte `bmp280`

Dentro de `bmp280` están los datos que nos interesan:

- `t_c` → temperatura en grados Celsius
- `p_hpa` → presión en hPa


### 6.10 Cómo leer el JSON sin perderse

Una forma fácil de entender el JSON es imaginar **cajas dentro de cajas**.

- Hay una caja grande llamada `sensor`.
- Dentro de esa caja hay otra caja llamada `bmp280`.
- Dentro de esa caja hay una etiqueta llamada `t_c`.

Por eso la ruta hasta la temperatura es:

```js
sensor.bmp280.t_c
```

Y como todo eso está dentro de `msg.payload`, en Node‑RED la ruta completa será:

```js
msg.payload.sensor.bmp280.t_c
```


### 6.11 Tercer nodo: `function` para extraer la temperatura

Ahora vamos a crear un nodo `function` para quedarnos solo con la temperatura.

#### Paso 1: arrastrar el nodo

Arrastra un nodo `function` al espacio de trabajo.

#### Paso 2: conectarlo

Conéctalo después del `mqtt in`.

Puedes dejar también el `debug` conectado en paralelo para seguir viendo el mensaje completo.

Por ejemplo:

```text
mqtt in ──→ debug
   │
   └──→ function
```


#### Paso 3: abrir la configuración

Haz doble clic sobre el nodo `function`.

Ponle un nombre, por ejemplo:

```text
Extraer temperatura
```


#### Paso 4: escribir el código

Escribe este código:

```js
var p = msg.payload;
msg.payload = p.sensor.bmp280.t_c;
return msg;
```

Ahora vamos a entenderlo **línea por línea**.


### 6.12 Explicación línea por línea del código de temperatura

#### Línea 1

```js
var p = msg.payload;
```

Esta línea significa:

> “voy a guardar el contenido de `msg.payload` en una variable llamada `p`”.

¿Por qué hacemos esto?

Porque `msg.payload` es más largo de escribir.
Si lo guardamos en `p`, el código queda más limpio y más fácil de leer.

Es como si dijéramos:

> “a partir de ahora, llamaré `p` a todo este paquete de datos”.


#### Línea 2

```js
msg.payload = p.sensor.bmp280.t_c;
```

Esta es la línea más importante.

Lo que hace es:

1. entrar en `p`,
2. buscar la parte `sensor`,
3. luego la parte `bmp280`,
4. luego la etiqueta `t_c`,
5. y colocar ese valor como nuevo `msg.payload`.

Si la temperatura era `22.45`, entonces después de esta línea `msg.payload` ya no será el JSON completo, sino solo:

```text
22.45
```

Es como si tuvieras una mochila llena de cosas y sacaras solo el **termómetro**, dejando lo demás aparte.


#### Línea 3

```js
return msg;
```

Esta línea significa:

> “ya he preparado el mensaje; ahora envíalo al siguiente nodo”.

Si olvidas esta línea, el mensaje no seguirá avanzando por el flow.


### 6.13 Ejemplo sencillo para entender la idea

Imagina que `msg.payload` fuese esto:

```json
{
  "alumno": {
    "nombre": "Ana",
    "curso": "4ESO"
  },
  "nota": {
    "matematicas": 8.5
  }
}
```

Y escribes este código:

```js
var p = msg.payload;
msg.payload = p.nota.matematicas;
return msg;
```

El resultado final será:

```text
8.5
```

¿qué ha pasado?

- Antes tenías toda la ficha de Ana.
- Después te has quedado solo con la nota de matemáticas.

Eso es exactamente lo mismo que hacemos con la temperatura:

- antes teníamos todo el JSON,
- después nos quedamos solo con el dato que queremos.

### 6.14 Qué hacer si aparece `undefined`

Si en vez de un número aparece `undefined`, significa que la ruta no coincide con el mensaje real.

Puede pasar porque:

- el mensaje no trae `sensor`,
- o no trae `bmp280`,
- o el nombre es distinto,
- o estás intentando acceder a un campo que no existe.

En ese caso, vuelve al nodo `debug` y mira bien cómo llega el JSON.

**Regla de oro:**
primero mirar el `debug`, después escribir la ruta.


### 6.15 Y si el mensaje llega como texto

A veces el mensaje MQTT no llega como un objeto ya organizado, sino como texto.

Por ejemplo, podrías ver algo así:

```text
"{\"sensor\":{\"bmp280\":{\"t_c\":22.45}}}"
```

Eso significa que el JSON está “metido en una cadena de texto”.

Si te pasa eso, añade un nodo `json` entre `mqtt in` y `function`:

```text
mqtt in  →  json  →  function
```

El nodo `json` convierte ese texto en un objeto que ya se puede recorrer por dentro.

#### Cómo saber si necesitas el nodo `json`

- Si en `debug` ves un árbol desplegable con campos, normalmente no hace falta.
- Si ves una sola línea llena de comillas y barras `\`, entonces sí conviene usarlo.

### 6.16 Mostrar la temperatura con `ui_gauge`

Una vez que el nodo `function` ya entrega solo un número, podemos mostrarlo en el Dashboard con un medidor.

Para eso vamos a usar el nodo `ui_gauge`.

#### Paso 1

Arrastra un nodo `ui_gauge`.

#### Paso 2

Conéctalo a la salida del nodo `function`.

#### Paso 3

Haz doble clic sobre él para configurarlo.

#### Paso 4

Configura estos campos:

- **Group**: el grupo donde aparecerá el medidor.
- **Label**: por ejemplo `Temperatura`.
- **Units**: por ejemplo `ºC`.
- **Min**: por ejemplo `0`.
- **Max**: por ejemplo `50`.


#### Qué debes entender

Este nodo necesita recibir un número.

Si le mandas un JSON completo, no sabrá qué hacer con él.
Por eso antes usamos el nodo `function`: para dejar solo la temperatura.


### 6.17 Qué es el Dashboard

El **Dashboard** es la página web donde verás los datos de forma visual.

Ahí puedes colocar:

- textos,
- medidores,
- interruptores,
- botones,
- y otros elementos visuales.

Para organizarlo todo, el Dashboard usa tres ideas importantes:

#### 1) Tab

Una **Tab** es como una pestaña o página.

Por ejemplo, podrías tener:

- `ESP8266`
- `Sensores`
- `Control`


#### 2) Group

Un **Group** es una sección dentro de una Tab.

Por ejemplo, dentro de la pestaña `ESP8266` podrías tener:

- un grupo `Estado`
- un grupo `BMP280`
- un grupo `Control LED`


#### 3) Widget

Un **widget** es cada elemento visual concreto.

Por ejemplo:

- un `ui_text`
- un `ui_gauge`
- un `ui_switch`


#### Forma fácil de recordarlo

- **Tab** = la página
- **Group** = la caja o bloque dentro de la página
- **Widget** = lo que metes dentro de esa caja


### 6.18 Mostrar otros datos con `ui_text`

Además de la temperatura, a veces interesa enseñar datos como la IP o el RSSI.

Para eso va muy bien `ui_text`.

#### Ejemplo: mostrar la IP

Primero crea un nodo `function` con este código:

```js
var p = msg.payload;
msg.payload = p.esp.ip;
return msg;
```

Luego conecta ese `function` a un nodo `ui_text`.

En `ui_text` puedes configurar:

- **Label**: `IP`
- **Format**:

```text
{{msg.payload}}
```

Así, en vez de ver un medidor, verás un texto en la web.


### 6.19 Extraer la presión

Ahora vamos a hacer exactamente lo mismo, pero con la presión.

Crea otro nodo `function` con este código:

```js
var p = msg.payload;
msg.payload = p.sensor.bmp280.p_hpa;
return msg;
```

La lógica es la misma que con la temperatura:

- entras en `sensor`,
- luego en `bmp280`,
- luego en `p_hpa`,
- y te quedas solo con la presión.

Después puedes conectarlo a otro `ui_gauge`.

#### Configuración sugerida del medidor de presión

- **Label**: `Presión`
- **Units**: `hPa`
- **Min**: `900`
- **Max**: `1100`


### 6.20 Montar el primer flow completo

Una versión sencilla del flow puede quedar así:

#### Para temperatura

```text
mqtt in  →  debug
   │
   └──→ function (temperatura)  →  ui_gauge
```


#### Para presión

```text
mqtt in  →  function (presión)  →  ui_gauge
```


#### Para IP

```text
mqtt in  →  function (ip)  →  ui_text
```


### 6.21 Organización recomendada del Dashboard

Para que no quede todo mezclado, puedes organizar el Dashboard así:

#### Tab

`ESP8266`

#### Groups

- `Estado`
- `BMP280`
- `Control`


#### Dentro de `Estado`

- `ui_text` con la IP
- `ui_text` con el RSSI


#### Dentro de `BMP280`

- `ui_gauge` con la temperatura
- `ui_gauge` con la presión


#### Dentro de `Control`

- `ui_switch` para el LED



### 6.22 Ver el Dashboard

Cuando ya tengas los nodos colocados y configurados:

1. pulsa **Deploy**,
2. comprueba que los nodos MQTT aparecen como conectados,
3. abre la página del Dashboard.

Si todo está bien, deberías ver cómo los valores cambian conforme el ESP8266 va publicando datos.



### 6.23 Enviar órdenes al ESP8266

Una vez que ya sabes recibir datos, vamos a mandar una orden.

Para eso haremos un flow muy sencillo.



### 6.24 Opción A: usar `inject`

El nodo `inject` sirve para lanzar un mensaje manualmente.

Es como un botón de prueba.

#### Qué debes hacer

1. Arrastra un nodo `inject`.
2. Haz doble clic sobre él.
3. Configura el valor como `true` o `false`, según lo que espere tu programa.
4. Arrastra un nodo `mqtt out`.
5. Conecta `inject` con `mqtt out`.
6. En `mqtt out`, selecciona el broker correcto.
7. Escribe el topic de control del ESP8266.
8. Pulsa **Deploy**.

Ahora, cada vez que pulses el botón del nodo `inject`, estarás enviando una orden MQTT.


### 6.25 Opción B: usar `ui_switch`

Si quieres controlar la placa desde el Dashboard, usa `ui_switch`.

#### Qué debes hacer

1. Arrastra un nodo `ui_switch`.
2. Asígnalo a una **Tab** y un **Group**.
3. Conéctalo a un nodo `mqtt out`.
4. Configura `mqtt out` con el topic de control correcto.
5. Pulsa **Deploy**.

Ahora verás un interruptor en la web.
Cuando lo cambies, Node‑RED enviará una orden al ESP8266.



### 6.26 Cómo revisar un flow sin perderse

Si algo no funciona, sigue siempre este orden:

1. **`mqtt in`**: comprueba que el broker y el topic están bien.
2. **`debug`**: mira si realmente llegan mensajes.
3. **`json`**: comprueba si hace falta convertir texto a objeto.
4. **`function`**: revisa si la ruta del dato es correcta.
5. **`ui_*`**: comprueba si el widget recibe el tipo de dato correcto.
6. **Dashboard**: revisa que Tab y Group estén bien asignados.


### 6.27 Errores típicos

#### No llega nada al `debug`

Revisa:

- el broker,
- el topic,
- y que el ESP8266 esté publicando datos.


#### Sale `undefined`

La ruta del dato es incorrecta.
Vuelve al `debug` y revisa la estructura del JSON.

#### El widget no aparece

Seguramente no has seleccionado bien la **Tab** o el **Group**.

#### El medidor no funciona

Probablemente no está recibiendo un número, sino un JSON completo o un texto.

#### No se enciende ni apaga el LED

Revisa el topic del `mqtt out` y el tipo de dato que estás enviando.


### 6.28 Objetivo final

Al terminar este apartado deberías tener:

- un flow que reciba los datos del ESP8266,
- un nodo `debug` para inspeccionarlos,
- uno o varios nodos `function` para extraer valores,
- un Dashboard con textos y medidores,
- y un control para enviar órdenes desde Node‑RED al ESP8266.

Si has llegado hasta aquí, ya has montado tu **primer sistema IoT visual**:
tu placa mide, publica, Node‑RED recibe, procesa y muestra los datos, y además puede enviar órdenes de vuelta.


---


## Problemas típicos

- “No such file or directory” al flashear: revisa que estás en la raíz del repo y que exista `.\firmware\ESP8266_GENERIC-20251209-v1.27.0.bin`.
- Puerto COM incorrecto: repite el comando de WMI y cambia `COM7`.
- Puerto ocupado: cierra otros monitores serie antes de `mpremote repl`.
- Problemas con el driver CH340. Para poder utilizar el ESP8266 en la placa Wemos D1 (y familia), es necesario instalar el siguiente driver para Windows:
```
https://sparks.gogo.co.nz/ch340.html?srsltid=AfmBOor7tyDgtSqSAO0hgxhvOsTXVapHI-UHmGEhj92JIU62x5SokqCV
```
- Si a lo largo del proceso fuera necesario realizar operaciones con nivel de ***ADMINISTRADOR***, dentro de la terminal, jecutamos el siguiente comando:
```
$dir = $PWD.Path; Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$dir'" -Verb RunAs
```
- Hay que asegurarnos de que tenemos la ruta con las variables de entorno que vamos a utilizar. Esto nos permite utilizar en la ventana de comandos las funciones que utilizan `esptool` y `mpremote` para flashear ESP8266 en clase. Copia el siguiente comando en la terminal que has abierto con permisos de administrador:

```powershell
setx /M PATH "%PATH%;C:\Users\u_38002831\AppData\Local\Programs\Python\Python314\Scripts"
```

- Si has subido antes el bmp280.py, ejecuta el siguiente comando, si te interesara borrarlo por aumentar espacio:

Borrar el `bmp280.py` del ESP, si existe (importante: si existe, “gana” al `.mpy`):
```powershell
py -m mpremote connect COM7 fs rm :lib/bmp280.py
```
- Si has subido antes el app.py, ejecuta el siguiente comando, si te interesara borrarlo por aumentar espacio:

Borrar `app.py` del ESP, si existía (muy importante):
```powershell
py -m mpremote connect COM7 fs rm :app.py
```
## Problema MemoryError en ESP8266

En ESP8266 es posible ver errores como:
`MemoryError: memory allocation failed, allocating ... bytes` al arrancar/importar módulos.

Una solución recomendada es **precompilar** módulos `.py` a `.mpy` con `mpy-cross` y copiar el `.mpy` al ESP.
Importante: borra el `.py` del ESP si subes el `.mpy`, porque el `.py` puede tener prioridad sobre el `.mpy` al importar.

### A) Instalar mpy-cross en Windows

```powershell
py -m pip install --upgrade mpy-cross
```

### B) Compilar el driver BMP280 del repo

Desde la raíz del repo:

```powershell
py -m mpy_cross .\lib\bmp280.py
```

Esto genera:

- `.\lib\bmp280.mpy`


### C) Copiar bmp280.mpy al ESP y borrar bmp280.py del ESP

```powershell
py -m mpremote connect COM7 fs cp .\lib\bmp280.mpy :lib/bmp280.mpy
py -m mpremote connect COM7 fs rm :lib/bmp280.py
```


### D) Reset y comprobar

```powershell
py -m mpremote connect COM7 reset
py -m mpremote connect COM7 repl
```

Dentro del REPL pulsa **Ctrl+D** para ver el arranque y comprobar que ya no aparece el MemoryError.

---
---

