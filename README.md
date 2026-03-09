# BMP280 en ESP8266 (Wemos D1) con MicroPython y MQTT

Este repositorio guiado permite a alumnos de 4º ESO:
1) Instalar herramientas en Windows
2) Flashear MicroPython en un ESP8266
3) Subir el driver `bmp280.py`
4) Subir `main.py`
5) Subir `app.mpy`
6) Ver los logs por REPL.
7) Introducirse en Node-Red

## Estructura del repo

- `firmware/` → firmware `.bin` de MicroPython para ESP8266
- `lib/` → librerías MicroPython (se copian a `:lib/` en el ESP)
- `src/` → código principal (`main.py`) y aplicación (`app.py`)

## Requisitos previos
Antes de ponernos a trabajar, tenemos que tener instalado en nuestro ordenador los siguientes elementos:

- Visual Studio Code  → https://code.visualstudio.com/
- [Descargar aquí](https://sparks.gogo.co.nz/ch340.html) el **Driver CH340**  

**NOTA**: Si aparece algún error a la hora de instalar el driver, instalarlo con la placa Wemos D1 conectada al PC.

- Descargar este repositorio
  1. En la raíz del repositorio, darle al botón verde `<> Code`
  2. Seleccionar `Download ZIP` 
     ![Captura](https://github.com/user-attachments/assets/12e14202-66b2-4644-82ca-646744c06db2)
  3. En el directorio donde se ha descargado la carpeta comprimida (icono de carpeta con cremallera), descomprimirla. Doble clic funciona.


<img width="500" height="400" alt="2" src="https://github.com/user-attachments/assets/c2e1e398-41c8-4878-9a31-a8b7d51addd2" />

Se abrirá la misma carpeta sin comprimir. Arrastrarla a una carpeta adecuada (por ejemplo a tu escritorio).

- En la carpeta ya descomprimida, hacer click derecho en un espacio en blanco y seleccionar `Abrir en Terminal`

<img width="500" height="400" alt="3" src="https://github.com/user-attachments/assets/5751c374-4717-41f1-a6c0-4aeac8affb2c" />


- Comprueba que tienes Python instalado con este comando que vas a copiar y pegar en la terminal: 

```powershell
py --version
```

Output esperado (ejemplo):

```text
Python 3.xx.x
```
- Si ya tienes Python instalado, salta el siguiente punto (punto 0) y ve directamente al punto 1)


## 0) Instalar Python (para usar `py`)

1. Descarga e instala Python desde python.org.
2. En el instalador marca (Observa la imagen, esto es **IMPORTANTE**):
   - “Install launcher for all users (recommended)”
   - “Add python.exe to PATH”
<img width="820" height="522" alt="Screenshot_1" src="https://github.com/user-attachments/assets/c1a7f46d-9b9f-4631-a3ee-fa7a3c3e8301" />



---

## 1) Abrir Visual Studio Code en la carpeta del repo

Vamos a abrir en Visual Studio Code, que es un software para programar, el directorio de este proyecto desde PowerShell con el siguiente comando:

```powershell
code .
```
(Observa el icono con dos recuadros superpuestos, arriba a la derecha. Hacer click en este icono te permite copiar el contenido del cuadro gris, en este caso, la URL) 

Cuando se abra Visual Studio Code, haz click en la opción por defecto: "Yes, I trust the authors” para habilitar todas las características. Ignora la pantalla de bienvenida central y dirígete al directorio a la izquierda. Allí, desplegamos la carpeta `src` y abrimos `app.py`. 

<img width="1008" height="559" alt="Screenshot_1" src="https://github.com/user-attachments/assets/445750df-5b2b-43b0-a414-b7208082676f" />


1. Tómate tu tiempo para leer el código.
2. En la sección “Config” tienes el nombre de la red (Línea 14: WIFI_SSID) y la contraseña (Línea 15: WIFI_PASS). Modificarlos por los valores de tu WiFi.
3. Ve a menú superior para guardar los cambios: “File” > “Save”

---

## 2) Instalar herramientas en el PC
Vuelve a PowerShell y ejecuta:

```powershell
py -m pip install --upgrade esptool
```

Qué hace: instala/actualiza `esptool` (borra y flashea la memoria del ESP8266).

```powershell
py -m pip install --upgrade mpremote
```

Qué hace: instala/actualiza `mpremote` (copiar archivos al ESP y abrir REPL).

---
## 3) Cableado (Wemos D1 + BMP280 por I2C)

En **Wemos D1**, los pines I2C más usados son:

- **D1 = SCL = GPIO5**
- **D2 = SDA = GPIO4**

Si no sabes ubicarlos en la placa, a pesar de que están serigrafiados, búscalos en google (Wemos D1 pinout).

### Conexiones (I2C)

![Nuevo Presentación de Microsoft PowerPoint](https://github.com/user-attachments/assets/03c42897-e598-430f-830e-7facc8c6fbce)


- Wemos **3V3** → BMP280 **VCC / VIN** (usa 3.3V)
- Wemos **G** (GND) → BMP280 **GND**
- Wemos **D1 (GPIO5 / SCL)** → BMP280 **SCL**
- Wemos **D2 (GPIO4 / SDA)** → BMP280 **SDA**


### Pines extra del BMP280 (si tu placa los tiene)

Muchos módulos BMP280 traen pines **CSB** y **SDO**:

- **CSB**: para I2C normalmente debe ir a **3V3** (en algunos módulos ya viene preparado, pero si no detecta el sensor, prueba a fijarlo a 3V3).
- **SDO**: selecciona la dirección I2C (típicamente `0x76` u `0x77`); a **GND** suele dar `0x76` y a **3V3** suele dar `0x77` (depende del módulo).


### Comprobación rápida (I2C scan)

Cuando ejecutes el programa (punto 8.2), en los logs deberías ver algo como:

- `0x76` o `0x77` en el “scan” de I2C
Si aparece vacío `[]`, suele ser cableado, alimentación o dirección.

### Importante: niveles de tensión

Los pines del Wemos D1 mini son **3.3V** (no toleran 5V en señales).
Si tu módulo BMP280 es “solo 5V” o lleva pull-ups a 5V, no lo conectes directo (usa módulo 3V3 o adapta niveles).

---

## 4) Conectar tu placa WeMos al PC
---

## 5) Encontrar el puerto COM del ESP8266

1) Pulsa Win + X → **Administrador de dispositivos**

<img width="466" height="808" alt="Screenshot_1" src="https://github.com/user-attachments/assets/46a15b39-2c04-409d-b343-65886d175b7d" />

2) Abre el apartado **Puertos (COM y LTP)**. Verás algo como:
```
“USB-SERIAL CH340 (COM3)”


“Silicon Labs CP210x USB to UART Bridge (COM5)”


“USB Serial Device (COM4)”
```
<img width="977" height="717" alt="Screenshot_2" src="https://github.com/user-attachments/assets/137c8883-fedb-4aec-83df-62632e458dda" />

El número entre paréntesis es el puerto: **COM3, COM4, etc.**
Si no aparece nada:
- Desconéctalo y vuelve a conectarlo observando qué cambia.
- Puede faltar el driver (CH340 o CP210x según el chip USB que lleve tu placa).

**IMPORTANTE**:  Guarda el número que te salga, por ejemplo, "COM6" (como se ve en la imagen de arriba), ya que lo utilizaremos al ejecutar los comandos para comunicarnos con nuesto ESP8266.

---

## 6) Borrar flash y flashear MicroPython

### 6.1 Borrar la flash (recomendado)
**IMPORTANTE**:  sustituye el número 7 en “COM7” en los siguientes comandos por el número del puerto COM al que acabas de comprobar que está conectado tu ESP8266.

```powershell
py -m esptool --chip esp8266 --port COM7 erase-flash
```

Qué hace: borra toda la flash del ESP8266.

Output esperado (aprox., puede variar):

```text
esptool.py v...
Serial port COM7
Connecting....
Chip is ESP8266
...
Erasing flash (this may take a while)...
Chip erase completed successfully in ...s
```
Si sale un error de configuración de puerto (como el que se ve en la imagen):

<img width="600" height="220" alt="8" src="https://github.com/user-attachments/assets/f5d38f60-d914-4eeb-9934-1ed39aa9ff9e" />

**[Requisitos previos](#requisitos-previos)** ← Reinstala CH341

<img width="528" height="332" alt="7" src="https://github.com/user-attachments/assets/a303b372-5d68-4893-b6f0-ca22d8c30acc" />



### 6.2 Flashear el firmware del repo

```powershell
py -m esptool --chip esp8266 --port COM7 --baud 460800 write-flash --flash-size=detect 0x00000 ".\firmware\ESP8266_GENERIC-20251209-v1.27.0.bin"
```

Qué hace: escribe el `.bin` de `firmware/` en la dirección `0x00000` y autodetecta el tamaño de flash.

Output esperado (aprox., puede variar):

```text
esptool.py v...
Serial port COM7
Connecting....
Chip is ESP8266
...
Detected flash size: ...
Writing at 0x00000000... (xx %)
...
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```


---

## 7) Subir librerías y programa (mpremote) — modo “anti MemoryError”

A veces el ESP8266 se queda sin memoria (RAM) justo al arrancar porque tiene que “leer y preparar” archivos `.py` grandes. Para evitar el **MemoryError**, hacemos esto: dejamos un `main.py` **muy pequeño o "stub"** (solo arranca el programa) y el programa “grande” lo subimos ya **precompilado** como `.mpy`, que ocupa menos RAM al cargar.

> Regla clave: en `mpremote`, los paths que empiezan por `:` son del ESP (remotos).


### 7.1 Crear `/lib` en el ESP 

```powershell
py -m mpremote connect COM7 fs mkdir lib
```

Qué hace: crea la carpeta `lib` en el ESP para guardar drivers.

**NOTA**: Si te da algún error al lanzar este comando, prueba a lanzarlo de nuevo. Puede ser que haya habido un problema con la conexión al inicio. Un truco para volver a poner un comando es utilizar las flechas **ARRIBA** y **ABAJO** del teclado.

***

### 7.2 Subir el driver BMP280 en `.mpy`, que ocupa menos memoria RAM

0) Instalar mpy-cross en Windows

```powershell
py -m pip install --upgrade mpy-cross
```

1) Compilar el driver en el PC:
```powershell
py -m mpy_cross .\lib\bmp280.py
```

2) Subir el `.mpy` al ESP:
```powershell
py -m mpremote connect COM7 fs cp .\lib\bmp280.mpy :lib/bmp280.mpy
```

3) Verificar:
```powershell
py -m mpremote connect COM7 fs ls :lib
```

Output esperado (ejemplo):

```text
bmp280.mpy
```

> Si prefieres no compilar el driver, puedes seguir subiendo `bmp280.py`, pero el riesgo de MemoryError es mayor.

***

### 7.3 Preparar `app.py` (tu programa “grande”) y `main.py` (tu programa "pequeño")

En la carpeta del proyecto, dentro de `src` tenemos **dos archivos del PC** con funciones distintas. **No hay que modificar nada aquí**: solo entiende qué es cada uno y para qué sirve.

- `.\\src\\app.py`: es tu programa **completo** (el “largo”), donde está toda la lógica (WiFi, MQTT, sensor, etc.). Luego se compila a `app.mpy` para que el ESP8266 lo cargue con menos esfuerzo y menos uso de memoria.
- `.\\src\\main.py`: es un **stub** (un “arrancador” muy pequeño). Su única misión es ejecutarse al arrancar el ESP y hacer `import app` (cargar `app.mpy`). Al ser tan pequeño, evita el `MemoryError` que puede aparecer si el archivo principal es demasiado grande.

Contenido de `.\\src\\main.py` (stub):

```python
# main.py (stub mínimo)
try:
    import app  # app.mpy
except Exception as e:
    print("[boot] app import ERROR:", repr(e))
```


***

### 7.4 Compilar `app.py` a `.mpy` en el PC

```powershell
py -m mpy_cross .\src\app.py
```

Qué hace: crea `.\src\app.mpy`.

***

### 7.5 Subir `main.py` (stub) y `app.mpy` al ESP

1) Subir el stub `main.py` (esto hace que autoarranque):
```powershell
py -m mpremote connect COM7 fs cp .\src\main.py :main.py
```

2) Subir el programa compilado:
```powershell
py -m mpremote connect COM7 fs cp .\src\app.mpy :app.mpy
```

***

### 7.6 Verificar archivos en la raíz del ESP

```powershell
py -m mpremote connect COM7 fs ls
```

Output esperado (ejemplo):

```text
boot.py
lib/
main.py
app.mpy
```


***

## 8) Reset y ver logs por REPL

### 8.1 Reset

```powershell
py -m mpremote connect COM7 reset
```

Qué hace: reinicia el microcontrolador para que arranque con `main.py`, que a su vez carga `app.mpy`.

### 8.2 Abrir REPL

```powershell
py -m mpremote connect COM7 repl
```

Qué hace: abre la consola REPL para ver mensajes del arranque y depurar.

Dentro del REPL pulsa **Ctrl+D** para hacer “soft reboot” y ver otra vez el arranque con los logs.

<img width="1299" height="301" alt="Screenshot_1" src="https://github.com/user-attachments/assets/659a3157-4d6a-453e-8d9d-cc889944397a" />


En la pantalla se ve que tu placa (el ESP8266) está conectada al WiFi y empieza a funcionar: intenta buscar el sensor BMP280 por I2C `[i2c] scan: []` pero no encuentra nada y por eso da error al iniciarlo.

Luego se conecta al “correo” de mensajes (MQTT): se suscribe a un canal llamado activate_led (para recibir órdenes) y también a otro canal con su ID, y publica datos en otro canal `.../bmp280`.

**AVISO**: Es posible que salga un error de este tipo:
```
MPY: soft reboot
Traceback (most recent call last):
File "main.py", line 8, in <module>
MemoryError: memory allocation failed, allocating 376 bytes
MicroPython v1.27.0 on 2025-12-09; ESP module with ESP8266
Type "help()" for more information.
>>>
```
Si te da ese error, ve a **[Problema MemoryError](#problema-memoryerror-en-esp8266)** 


## 9) Node‑RED: ver datos y mandar órdenes al ESP8266

Node‑RED es una herramienta para crear “programas” uniendo **bloques** (nodos) con cables. En este proyecto lo usamos como un “panel de control”: por un lado **recibe** los datos que envía el ESP8266 por MQTT (en formato JSON) y los muestra en una web; por otro lado **envía** órdenes al ESP8266 (por ejemplo encender/apagar el LED) publicando en un topic de control.

<img width="1919" height="872" alt="Screenshot_1" src="https://github.com/user-attachments/assets/a8373c5f-c2e4-4b7e-b7e3-7f3eabf9c83d" />


### 9.1 Qué es MQTT en este proyecto

MQTT funciona como un sistema de mensajería con “canales” llamados **topics**. Un dispositivo *publica* mensajes en un topic (por ejemplo, datos del sensor) y otro dispositivo *se suscribe* a ese topic para recibirlos.

- Ejemplo de topic de datos: `.../bmp280` (aquí llegan temperatura y presión).
- Ejemplo de topic de control: `.../activate_led` (aquí mandas ON/OFF).

Al inicio del programa, vemos los topics a los que se van a enviar los datos y a los que nos hemos suscrito para poder controlar lo que queramos. Podemos crear el nuestro:

<img width="1299" height="301" alt="Screenshot_1" src="https://github.com/user-attachments/assets/659a3157-4d6a-453e-8d9d-cc889944397a" />

### 9.2 Nodos que verás en el flujo

#### `mqtt in` (recibir mensajes)

Este nodo se conecta al broker MQTT y se **suscribe** a un topic (un “canal”). Cuando llega un mensaje por ese canal, el nodo lo envía hacia la derecha para que el resto del flujo lo procese (por ejemplo, para leer el JSON y mostrarlo en el Dashboard).

**Un topic con `#` (comodín / “escuchar todo lo que cuelga de aquí”)**
La imagen del topic con `#` significa: “escucha **muchos topics a la vez** que empiezan igual”.

<img width="799" height="79" alt="Screenshot_2" src="https://github.com/user-attachments/assets/becd40f9-43ab-4e2b-9cc4-174ac6be759a" />

Ejemplo: si pones `cabrerapinto/#`, Node‑RED recibirá mensajes de **cualquier** subtopic que empiece por `cabrerapinto/…` (sirve para pruebas y depuración, porque ves todo lo que está enviando la red).

**Un topic más específico (escuchar solo un dispositivo o un sensor)**
En la imagen del topic específico se ve un camino más largo (con varias carpetas) que identifica mejor el origen: zona/proyecto → tipo de nodo → ID del dispositivo → sensor.

<img width="1455" height="337" alt="Screenshot_3" src="https://github.com/user-attachments/assets/b0e56fd3-da4e-4c0c-a8f6-1673ca40f341" />

Esto hace que Node‑RED reciba **solo** los mensajes de ese sensor/dispositivo concreto (por ejemplo, el BMP280 de un ESP en particular), evitando mezclar datos de otros compañeros.

**Configuración del nodo `mqtt in` (elegir servidor y topic correcto)**
En la ventana de configuración se hacen dos cosas clave:

<img width="717" height="616" alt="Screenshot_4" src="https://github.com/user-attachments/assets/d265b629-e082-48d8-a15e-58c31b4e2064" />

1) **Servidor (broker)**: eliges el “servidor de mensajes” al que te conectas (tiene IP y puerto). Si eliges otro broker, no verás tus mensajes.
2) **Topic**: copias/pegas el topic exacto desde el que quieres recibir datos (en tu caso, el que publica tu ESP). Importante: cada alumno/grupo puede tener un topic distinto, así que hay que mirar el vuestro y poner ese.



#### `debug` (ver qué está llegando)

El nodo `debug` muestra en la barra derecha el contenido del mensaje (por ejemplo `msg.payload`). Es el mejor nodo para comprobar si el JSON llega bien y si el topic es el correcto.

<img width="1914" height="675" alt="Screenshot_5" src="https://github.com/user-attachments/assets/d36b938e-a2be-42f6-af77-7592bcdaa76c" />

Durante las prácticas conviene activar el debug al principio, haciendo click en el botón verde que se muestra en la imagen, luego desactivarlo para que no se llene la pantalla de depuración.

#### `function` (extraer un dato del JSON)

El nodo `function` te deja escribir un poco de JavaScript para transformar el mensaje. 

<img width="1569" height="383" alt="Screenshot_6" src="https://github.com/user-attachments/assets/276c2152-20ee-4ba0-a69a-3579525f934a" />

Aquí lo usamos para “pasar de JSON completo a un dato”, por ejemplo, para quedarnos solo con la temperatura. 

<img width="676" height="708" alt="Screenshot_8" src="https://github.com/user-attachments/assets/17d0ebe5-fbeb-49db-8c00-80c6bb32a13a" />

La idea es simple: el JSON llega en `msg.payload`, tú lees la ruta del dato y después pones ese dato como nuevo `msg.payload` (así el siguiente nodo recibe solo un número).

**Caso de uso**: Obtener la temperatura del BMP280:

```js
var p = msg.payload;              // JSON completo
msg.payload = p.sensor.bmp280.t_c; // sacar temperatura
return msg;
```

A continuación, vamos a extraer la temperatura del mensaje JSON, paso a paso:

**1) Llega un mensaje MQTT con un JSON** dentro de `msg.payload`. Un ejemplo simple puede ser:

```json
{
  "esp": { "ip": "10.53.151.83", "rssi": -62 },
  "sensor": {
    "bmp280": { "t_c": 22.45, "p_hpa": 1012.80 }
  }
}
```

**2) Paso recomendado: mira el JSON con un `debug`**
Conecta un nodo `debug` justo después del `mqtt in` y expande el árbol: `payload → sensor → bmp280 → t_c`. El panel Debug te ayuda a entender la estructura del mensaje.

**3) En un nodo `function`, guarda el JSON en una variable**

```js
var p = msg.payload;   // p ahora es el JSON completo
```

**4) Escribe la “ruta” hasta el dato que quieres**

- La temperatura está en: `p.sensor.bmp280.t_c`

```js
var temp = p.sensor.bmp280.t_c;
```

**5) Deja ese valor como `msg.payload` para el siguiente nodo (gauge/texto)**

```js
msg.payload = temp;
return msg;
```

**Código completo del `function` (temperatura):**

```js
var p = msg.payload;
msg.payload = p.sensor.bmp280.t_c;
return msg;
```

> Si la ruta no existe (por ejemplo el JSON no trae `bmp280`), verás `undefined`. En ese caso revisa la estructura en el `debug` y ajusta la ruta.

#### `ui_text` y `ui_gauge` (mostrarlo en una web: Dashboard)

Estos nodos pertenecen al **Dashboard**, que es una página web (tipo “panel de control”) donde ves los datos del ESP8266 en tiempo real: si el ESP publica un nuevo valor por MQTT, aquí se actualiza automáticamente.

<img width="1919" height="878" alt="Screenshot_10" src="https://github.com/user-attachments/assets/ccf257fb-0afe-4be1-be63-dafaf1fc131c" />

En esta captura se ve el resultado final: varios “widgets” (bloques) colocados en la web. Normalmente:

- Arriba aparecen textos con información del ESP (por ejemplo **IP**, **RSSI**, o “Online/Offline”).
- Abajo aparecen medidores tipo reloj/contador para los sensores (por ejemplo **Temperatura** y **Presión**).

La idea es: Node-RED recibe el JSON, extrae valores, y el Dashboard los muestra de forma visual para que sea fácil entenderlos de un vistazo.

- `ui_text`: muestra texto (por ejemplo IP, RSSI o “Online/Offline”).
- `ui_gauge`: muestra un número como un medidor (por ejemplo temperatura o presión).

Esta ventana es donde decides **cómo y dónde** se verá el dato en la web.

<img width="626" height="814" alt="Screenshot_11" src="https://github.com/user-attachments/assets/e512e9e1-dced-42aa-9725-67f93915c458" />

Cosas importantes que hay que entender:

- **Group (Grupo):** es “la caja” o sección del Dashboard donde se colocará el widget.
Piensa en el Dashboard como una página dividida en bloques grandes (grupos). Si eliges otro grupo, el widget aparecerá en otra zona.
- **Label (Etiqueta/Título):** el nombre que verás al lado o encima del widget (por ejemplo “IP”, “RSSI”, “Temperatura”).
- **Format (Formato del valor):** es cómo Node-RED “imprime” el valor que le llega en `msg.payload`.
    - En `ui_text` suele ponerse `{{msg.payload}}` para mostrar el texto/número tal cual llega.
    - En `ui_gauge` normalmente se usa `{{value}}` (el gauge representa el valor numérico recibido).
Si el formato está mal, puede que no se vea nada o que salga “undefined”.
- **Units / min / max (en `ui_gauge`):** aquí defines la unidad (ºC, hPa…) y los límites del medidor. Esto **no cambia el dato real**; solo cambia cómo se representa en la web.

Aquí es donde se organiza toda la web del Dashboard.

<img width="388" height="475" alt="Screenshot_12" src="https://github.com/user-attachments/assets/f8f07f3d-e418-40f5-b27d-87793bd9e791" />


1. En Node-RED mira la barra lateral derecha.
2. Busca la sección de **Dashboard** (icono típico de “panel”).
3. Ahí verás la estructura: **Tabs** y **Groups**.

**Qué significa cada cosa:**

- **Tab (Pestaña):** como una pestaña en una web. Si tienes varias, puedes tener “Página principal”, “Grupo 1”, “Sensores”, etc. Cada tab es una “pantalla” distinta.
- **Group (Grupo):** son secciones dentro de una pestaña. Sirven para ordenar: por ejemplo un grupo para “Información del ESP”, otro para “BMP280”, otro para “Control LED”.
- **Link (Enlace):** un botón/enlace del Dashboard para saltar a otra pestaña o a otra parte. No es obligatorio para que funcione, pero ayuda a navegar.

**Reglas de clase (para no liarse con widgets)**

- **Regla 1:** Primero crea (o elige) un **Tab**, luego crea (o elige) un **Group**, y por último en cada `ui_*` selecciona su **Group**. Si no asignas Group, el widget no aparece.
- **Regla 2:** Un widget debe recibir **un solo valor**. Si quieres mostrar temperatura y presión, usa **dos** widgets (dos `ui_gauge`).
- **Regla 3:** Si no aparece nada, revisa en este orden: `mqtt in` (topic correcto) → `debug` (llega JSON) → `function` (ruta correcta) → `ui_*` (Group + Format correctos).

#### `inject`, `ui_switch` y `mqtt out` (mandar órdenes al ESP8266)

Esta parte sirve para controlar el LED del ESP8266.

<img width="1738" height="396" alt="Screenshot_13" src="https://github.com/user-attachments/assets/e17c4d3d-4880-428c-99c4-5d590c8ece4d" />


- `inject`: botones que envían un mensaje fijo, por ejemplo `"ON"` o `"OFF"`. Aquí podemos seleccionar el tipo de valor que "inyectamos" o enviamos al topic. En este caso, son valores boleanos, es decir, `true` o `false`, pero pueden ser valores numéricos, cadenas de texto...

<img width="693" height="783" alt="Screenshot_15" src="https://github.com/user-attachments/assets/7b634726-464a-4b08-9167-9f0103570371" />

- `ui_switch`: un interruptor en la web que envía `true/false` cuando lo cambias. Este objeto se crea en el dashboard y como el botón `inject`, permite enviar comandos cuando se activa.

<img width="867" height="682" alt="Screenshot_14" src="https://github.com/user-attachments/assets/fdb95f5b-923d-40ff-988b-591e7044be17" />

- `mqtt out`: publica ese mensaje en el topic de control (por ejemplo `activate_led` o un topic específico del dispositivo). Se configura como el nodo `mqtt in`


### 9.3 Cómo “entender” un flujo rápido

Para no perderse, sigue este orden:

- Empieza por los `mqtt in`: ¿qué topic están escuchando? (ahí entra la información).
- Activa un `debug`: mira qué hay dentro de `msg.payload` (ahí ves el JSON real).
- Revisa los `function`: cada uno debería sacar **un dato** y dejarlo como `msg.payload` para el Dashboard.
- Al final mira los nodos `ui_*`: eso es lo que verás en la web del Dashboard.

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

