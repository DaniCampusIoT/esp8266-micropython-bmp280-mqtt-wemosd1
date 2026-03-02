# BMP280 en ESP8266 (Wemos D1) con MicroPython y MQTT

Este repositorio guiado permite a alumnos de 4º ESO:
1) Instalar herramientas en Windows
2) Flashear MicroPython en un ESP8266
3) Subir el driver `bmp280.py`
4) Subir `main.py`
5) Ver los logs por REPL.

## Estructura del repo

- `firmware/` → firmware `.bin` de MicroPython para ESP8266
- `lib/` → librerías MicroPython (se copian a `:lib/` en el ESP)
- `src/` → código principal (`main.py`)

## Requisitos previos
Antes de ponernos a trabajar, tenemos que tener instalado en nuestro ordenador los siguientes elementos:

- Visual Studio Code  → https://code.visualstudio.com/
- Driver CH340. Puedes descargarlo desde la siguiente URL:
```
https://sparks.gogo.co.nz/ch340.html?srsltid=AfmBOor7tyDgtSqSAO0hgxhvOsTXVapHI-UHmGEhj92JIU62x5SokqCV
```
(Observa el icono con dos recuadros superpuestos, arriba a la derecha. Hacer click en este icono te permite copiar el contenido del cuadro gris, en este caso, la URL)
**NOTA**: Si aparece algún error a la hora de instalar el driver, instalarlo con la placa Wemos D1 conectada al PC.

- Descargar este repositorio
  1) En la raíz del repositorio, darle al botón verde `<> Code`
  2) Seleccionar `Download ZIP`
  3) En el directorio donde se ha descargado la carpeta comprimida (icono de carpeta con una cremallera), descomprimirlao. Una forma de hacerlo es hacer doble clic en ella. Se abrirá la misma carpeta sin comprimir. Arrastrarla a una carpeta adecuada (por ejemplo a tu escritorio).
- En la carpeta ya descomprimida, hacer click derecho en un espacio en blanco y seleccionar `Abrir en Terminal`
- Comprueba que tienes Python instalado con este comando:
En PowerShell:

```powershell
py --version
```

Output esperado (ejemplo):

```text
Python 3.xx.x
```
- Si ya tienes Python instalado, salta el siguiente punto (punto 0) y ve directamente al punto 1)
**NOTA IMPORTANTE**: Permanece en una esta ventana de comandos, la que has abierto con permisos de administrador, no la cierres. 


---
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
Cuando se abra Visual Studio Code, haz click en la opción por defecto: "Yes, I trust the authors” para habilitar todas las características. Ignora la pantalla de bienvenida central y dirígete al directorio a la izquierda. Allí, desplegamos la carpeta `src` y abrimos `main.py`. 

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

## 7) Subir librerías y programa (mpremote)

> Regla clave: en `mpremote`, los paths que empiezan por `:` son del ESP (remotos).

### 7.1 Crear `/lib` en el ESP (si no existe)

```powershell
py -m mpremote connect COM7 fs mkdir lib
```

Qué hace: crea la carpeta `lib` en el ESP para guardar drivers.

### 7.2 Copiar el driver BMP280 del repo al ESP

```powershell
py -m mpremote connect COM7 fs cp .\lib\bmp280.py :lib/bmp280.py
```

Qué hace: copia `lib\bmp280.py` (PC) a `:lib/bmp280.py` (ESP).

Output esperado:

```text
cp .\lib\bmp280.py :lib/bmp280.py
```


### 7.3 Verificar que está en el ESP

```powershell
py -m mpremote connect COM7 fs ls :lib
```

Qué hace: lista el contenido de `:lib` (ESP).

Output esperado (ejemplo):

```text
bmp280.py
```


### 7.4 Copiar el `main.py` del repo al ESP

```powershell
py -m mpremote connect COM7 fs cp .\src\main.py :main.py
```

Qué hace: sube el programa principal para que se ejecute al arrancar el ESP.

Output esperado:

```text
cp .\src\main.py :main.py
```


### 7.5 Verificar archivos en la raíz del ESP

```powershell
py -m mpremote connect COM7 fs ls
```

Qué hace: lista archivos en `:` (raíz) del ESP.

Output esperado (ejemplo):

```text
lib/
main.py
```


---

## 8) Reset y ver logs por REPL

### 8.1 Reset

```powershell
py -m mpremote connect COM7 reset
```

Qué hace: reinicia el microcontrolador para que arranque con `main.py`.

### 8.2 Abrir REPL

```powershell
py -m mpremote connect COM7 repl
```

Qué hace: abre la consola REPL para ver mensajes del arranque y depurar.

Output esperado (ejemplo):

```text
Connected to MicroPython at COM7
Use Ctrl-] or Ctrl-x to exit this shell

MPY: soft reboot
MicroPython v1.27.0 on 2025-12-09; ESP module with ESP8266
Type "help()" for more information.
>>>
```

Dentro del REPL:

- Pulsa **Ctrl+D** para hacer “soft reboot” y ver otra vez el arranque con los logs de tu programa.
- Es posible que salga un error de este tipo:
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

