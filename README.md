# BMP280 en ESP8266 (Wemos D1) con MicroPython y MQTT

Este repositorio guiado permite a alumnos de 4º ESO:
1) Instalar herramientas en Windows
2) Flashear MicroPython en un ESP8266
3) Subir el driver `bmp280.py`
4) Subir `main.py`
5) Subir `app.mpy`
6) Ver los logs por REPL.

## Estructura del repo

- `firmware/` → firmware `.bin` de MicroPython para ESP8266
- `lib/` → librerías MicroPython (se copian a `:lib/` en el ESP)
- `src/` → código principal (`main.py`)

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

Cuando se abra Visual Studio Code, haz click en la opción por defecto: "Yes, I trust the authors” para habilitar todas las características. Ignora la pantalla de bienvenida central y dirígete al directorio a la izquierda. Allí, desplegamos la carpeta `src` y abrimos `main.py`. 

<img width="1319" height="998" alt="5" src="https://github.com/user-attachments/assets/2eb2abdf-eca1-4da8-b2c6-b2ec61e48413" />


1. Tómate tu tiempo para leer el código.
2. En la sección “Config” tienes el nombre de la red (Línea 12: WIFI_SSID) y la contraseña (Línea 13: WIFI_PASS). Modificarlos por los valores de tu WiFi.
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
2) Abre el apartado **Puertos (COM y LTP)**. Verás algo como:
```
“USB-SERIAL CH340 (COM3)”


“Silicon Labs CP210x USB to UART Bridge (COM5)”


“USB Serial Device (COM4)”
```

El número entre paréntesis es el puerto: **COM3, COM4, etc.**
Si no aparece nada:
- Desconéctalo y vuelve a conectarlo observando qué cambia.
- Puede faltar el driver (CH340 o CP210x según el chip USB que lleve tu placa).

---

## 6) Borrar flash y flashear MicroPython

### 6.1 Borrar la flash (recomendado)
**IMPORTANTE**:  sustituye el número 7 en “COM7” en los siguientes comandos por el número del puerto COM al que acabas de comprobar que está conectado tu ESP8266.

```powershell
py -m esptool --chip esp8266 --port COM7 erase_flash
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

### 7.1 Crear `/lib` en el ESP (si no existe)

```powershell
py -m mpremote connect COM7 fs mkdir lib
```

Qué hace: crea la carpeta `lib` en el ESP para guardar drivers.

***

### 7.2 Subir el driver BMP280 en `.mpy`, que ocupa menos memoria RAM

1) Compilar el driver en el PC:
```powershell
py -m mpy_cross .\lib\bmp280.py
```

2) Subir el `.mpy` al ESP:
```powershell
py -m mpremote connect COM7 fs cp .\lib\bmp280.mpy :lib/bmp280.mpy
```

**AVISO: Si has subido antes el bmp280.py, ejecuta el comando del punto 3, si no, ve al punto 4**

3) Borrar el `.py` del ESP (importante: si existe, “gana” al `.mpy`):
```powershell
py -m mpremote connect COM7 fs rm :lib/bmp280.py
```

4) Verificar:
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

En tu PC:

- Guarda tu programa completo (el largo) como: `.\src\app.py`
- Deja `.\src\main.py` como **stub** mínimo (solo arranca `app`):

Contenido de `.\src\main.py`:

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

**AVISO: Si has subido antes el app.py, ejecuta el comando del punto 3, si no, ve al apartado 7.6**

3) Borrar `app.py` del ESP si existía (muy importante):
```powershell
py -m mpremote connect COM7 fs rm :app.py
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
Si te da ese error, lee el siguiente punto. 

## Problema: MemoryError en ESP8266 (solución con .mpy)

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

---

