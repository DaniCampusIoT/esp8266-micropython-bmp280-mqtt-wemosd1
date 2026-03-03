import time
import errno
import gc
import ubinascii
import ujson
import network
import math
from machine import Pin, I2C
from umqtt.simple import MQTTClient
import bmp280


# ===== Config =====
WIFI_SSID = "HortSost"
WIFI_PASS = "9b11c2671e5b"  # <-- reemplaza esto

MQTT_HOST = "136.112.103.14"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

TYPE_NODE = "meteorologia"
SEND_PERIOD_MS = 5000

# Wemos D1 mini: D2=GPIO4 (SDA), D1=GPIO5 (SCL)
I2C_SDA = 4   # D2
I2C_SCL = 5   # D1
I2C_FREQ = 100000

SEA_LEVEL_HPA = 1013.25
SEA_LEVEL_PA = SEA_LEVEL_HPA * 100.0

# ===== LED built-in (ESP8266/Wemos suele ser active-low en GPIO2) =====
LED_GPIO = 2
LED_ACTIVE_LOW = True
led = Pin(LED_GPIO, Pin.OUT)
led.value(1 if LED_ACTIVE_LOW else 0)  # LED apagado al inicio

# MQTT subscribe topics
TOPIC_SUB_SIMPLE = b"activate_led"
topic_sub_device = None

# Errores "posibles" (en MicroPython puede que no existan todos) 
_ECONNRESET = getattr(errno, "ECONNRESET", -999)
_ETIMEDOUT = getattr(errno, "ETIMEDOUT", -999)
_ENOTCONN = getattr(errno, "ENOTCONN", -999)
_EPIPE = getattr(errno, "EPIPE", -999)


def wifi_status_str(st):
    """
    FUNCIÓN: Convierte un código de estado WiFi a texto legible
    
    ENTRADA: st (número) = código de estado de la red WiFi
    SALIDA: (texto) = estado en formato legible como "IDLE", "CONNECTING", "GOT_IP", etc.
    
    VARIABLES IMPORTANTES:
    - m: diccionario que asocia números con nombres de estado
    - st: el código que recibimos
    
    EJEMPLO: Si el ESP8266 está conectado, devuelve "GOT_IP"
    """
    m = {
        network.STAT_IDLE: "IDLE",
        network.STAT_CONNECTING: "CONNECTING",
        network.STAT_WRONG_PASSWORD: "WRONG_PASSWORD",
        network.STAT_NO_AP_FOUND: "NO_AP_FOUND",
        getattr(network, "STAT_CONNECT_FAIL", -999): "CONNECT_FAIL",
        network.STAT_GOT_IP: "GOT_IP",
    }
    return m.get(st, str(st))


def wifi_connect(timeout_ms=20000):
    """
    FUNCIÓN: Conecta el ESP8266 a una red WiFi
    
    ENTRADA: timeout_ms (número, opcional) = tiempo máximo de espera en milisegundos (por defecto 20 segundos)
    SALIDA: sta = objeto de conexión WiFi conectado
    
    VARIABLES IMPORTANTES:
    - sta: la conexión WiFi del ESP8266
    - t0: hora de inicio para controlar el timeout
    - st: estado actual de la conexión WiFi
    
    QUÉ HACE:
    1. Activa el modo de estación WiFi (conectarse a una red)
    2. Se conecta a la red WIFI_SSID con la contraseña WIFI_PASS
    3. Espera a que se conecte, mostrando el estado cada vez que cambia
    4. Si pasan más de 20 segundos sin conectar, muestra un error
    
    EJEMPLO: Después de esta función, el ESP8266 está conectado a Internet
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    if sta.isconnected():
        return sta

    sta.connect(WIFI_SSID, WIFI_PASS)

    t0 = time.ticks_ms()
    last = None

    while not sta.isconnected():
        st = sta.status()
        if st != last:
            print("[wifi] status:", wifi_status_str(st), "(", st, ")")
            last = st

        if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
            raise RuntimeError("WiFi timeout, status=%s(%r)" % (wifi_status_str(st), st))

        time.sleep_ms(250)

    print("[wifi] connected:", sta.ifconfig())
    return sta


def esp_id_from_mac(sta):
    """
    FUNCIÓN: Obtiene un ID único del ESP8266 basado en su dirección MAC
    
    ENTRADA: sta = objeto de conexión WiFi
    SALIDA: (texto) = ID único del dispositivo en formato hexadecimal (ej: "5ccf7f1a2b3c")
    
    VARIABLES IMPORTANTES:
    - mac: dirección MAC del dispositivo (6 números que identifican el hardware)
    
    QUÉ HACE:
    1. Lee la dirección MAC (número de serie del WiFi del ESP8266)
    2. Lo convierte a código hexadecimal (números y letras)
    3. Lo devuelve como texto para usarlo como identificador único
    
    EJEMPLO: Cada ESP8266 tiene un ID diferente, nunca se repite
    """
    mac = sta.config("mac")
    return ubinascii.hexlify(mac).decode()


def safe_rssi(sta):
    """
    FUNCIÓN: Obtiene la potencia de señal WiFi de forma segura
    
    ENTRADA: sta = objeto de conexión WiFi
    SALIDA: (número) = potencia de la señal en dBm, o None si hay error
    
    VARIABLES IMPORTANTES:
    - rssi: nombre técnico de la potencia de WiFi (cuanto más cercano a 0, mejor)
    
    QUÉ HACE:
    1. Intenta leer la potencia de la señal
    2. Si hay error, devuelve None (nada) para que el programa no se bloquee
    
    EJEMPLO: -50 = señal fuerte, -80 = señal débil, -100 = sin conexión
    """
    try:
        return sta.status("rssi")
    except Exception:
        return None


def led_set_off(is_off):
    """
    FUNCIÓN: Enciende o apaga el LED del ESP8266
    
    ENTRADA: is_off (Verdadero/Falso) = True para apagar, False para encender
    SALIDA: ninguna (solo controla el LED)
    
    VARIABLES IMPORTANTES:
    - LED_ACTIVE_LOW: variable que dice si el LED se apaga con voltaje alto (1) o bajo (0)
    - led: el pin donde está conectado el LED
    
    QUÉ HACE:
    1. Comprueba si el LED es de tipo "active-low" (se apaga mandándole 1)
    2. Enciende o apaga el LED según el parámetro
    
    EJEMPLO: 
    - led_set_off(True) = LED apagado
    - led_set_off(False) = LED encendido
    """
    if LED_ACTIVE_LOW:
        led.value(1 if is_off else 0)
    else:
        led.value(0 if is_off else 1)


def parse_led_command(msg):
    """
    FUNCIÓN: Interpreta un comando de texto para encender/apagar LED
    
    ENTRADA: msg (bytes/texto) = el mensaje recibido por MQTT ("ON", "OFF", "1", "0", etc.)
    SALIDA: (Verdadero/Falso) = True para ENCENDER, False para APAGAR
    
    VARIABLES IMPORTANTES:
    - m: el mensaje limpio (sin espacios)
    
    QUÉ HACE:
    1. Limpia el mensaje quitando espacios
    2. Comprueba si dice "ON", "TRUE", "1" (cualquier variante) → devuelve True
    3. Comprueba si dice "OFF", "FALSE", "0" → devuelve False
    4. Si es un número, comprueba si es mayor que 0
    5. Si no entiende, devuelve False (por defecto apagado)
    
    EJEMPLO:
    - parse_led_command(b"ON") → True (encender)
    - parse_led_command(b"OFF") → False (apagar)
    - parse_led_command(b"5") → True (cualquier número > 0 es ON)
    """
    if msg is None:
        return False

    m = msg.strip()

    if m in (b"ON", b"on", b"On", b"TRUE", b"true", b"True", b"1"):
        return True
    if m in (b"OFF", b"off", b"Off", b"FALSE", b"false", b"False", b"0"):
        return False

    try:
        return int(m) > 0
    except Exception:
        return False


def on_mqtt_msg(topic, msg):
    """
    FUNCIÓN: Se ejecuta automáticamente cuando llega un mensaje MQTT
    
    ENTRADA: 
    - topic (bytes) = tema MQTT de dónde viene el mensaje (ej: b"activate_led")
    - msg (bytes) = contenido del mensaje (ej: b"ON")
    
    SALIDA: ninguna (solo controla el LED)
    
    VARIABLES IMPORTANTES:
    - topic_sub_device: tema específico del dispositivo
    - cmd_on: Verdadero/Falso del comando parseado
    
    QUÉ HACE:
    1. Comprueba si el mensaje es para este dispositivo (comparando temas)
    2. Interpreta el comando (ON/OFF) usando parse_led_command
    3. **IMPORTANTE**: Si comando=ON (1), apaga el LED. Si comando=OFF (0), enciende el LED.
       (Esto es al revés porque así lo decidió el programa)
    4. Muestra en pantalla qué pasó
    
    EJEMPLO:
    - Llega mensaje "ON" → LED apagado → muestra "[led] cmd=ON/1 => LED OFF"
    """
    global topic_sub_device

    if topic != TOPIC_SUB_SIMPLE and (topic_sub_device is None or topic != topic_sub_device):
        return

    cmd_on = parse_led_command(msg)

    # Requisito: ON/1 => ENCENDER LED, OFF/0 => APAGAR LED
    if cmd_on:
        led_set_off(False)
        print("[led] cmd=OFF/0 => LED OFF")
    else:
        led_set_off(True)
        print("[led] cmd=ON/1 => LED ON")


def mqtt_connect(esp_id_hex):
    """
    FUNCIÓN: Conecta el ESP8266 a un servidor MQTT (para enviar/recibir datos)
    
    ENTRADA: esp_id_hex (texto) = ID único del dispositivo en hexadecimal
    SALIDA: c = objeto de conexión MQTT conectado y configurado
    
    VARIABLES IMPORTANTES:
    - client_id: nombre único del cliente MQTT
    - lwt_topic: tema donde se publica si el dispositivo se desconecta ("Last Will Testament")
    - c: la conexión MQTT
    - topic_sub_device: tema específico para este dispositivo
    
    QUÉ HACE:
    1. Crea un ID único para este dispositivo
    2. Define un tema para cuando se desconecte (para que otros lo sepan)
    3. Se conecta al servidor MQTT (mosquitto)
    4. Configura el "testamento" (mensaje que se envía si se desconecta bruscamente)
    5. Configura la función que se ejecuta cuando llega un mensaje: on_mqtt_msg
    6. Se publica como "Online"
    7. Se suscribe a dos temas:
       - Un tema común para todos: "activate_led"
       - Un tema específico solo para este dispositivo: "cabrerapinto/meteorologia/{ID}/activate_led"
    
    EJEMPLO: Ahora el ESP8266 está esperando comandos MQTT
    """
    global topic_sub_device

    client_id = ("ESP8266Client-" + esp_id_hex).encode()
    lwt_topic = ("cabrerapinto/{}/{}/connection".format(TYPE_NODE, esp_id_hex)).encode()

    c = MQTTClient(
        client_id,
        MQTT_HOST,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        keepalive=15,
    )

    c.set_last_will(lwt_topic, b"Offline", retain=True, qos=1)
    c.set_callback(on_mqtt_msg)

    c.connect()
    c.publish(lwt_topic, b"Online", retain=True, qos=1)

    topic_sub_device = ("cabrerapinto/{}/{}/activate_led".format(TYPE_NODE, esp_id_hex)).encode()

    c.subscribe(TOPIC_SUB_SIMPLE)
    print("[mqtt] subscribed:", TOPIC_SUB_SIMPLE)

    c.subscribe(topic_sub_device)
    print("[mqtt] subscribed:", topic_sub_device)

    return c


def mqtt_disconnect_quiet(mqtt):
    """
    FUNCIÓN: Desconecta del servidor MQTT sin causar errores
    
    ENTRADA: mqtt = objeto de conexión MQTT
    SALIDA: ninguna
    
    QUÉ HACE:
    1. Intenta desconectarse del servidor MQTT
    2. Si hay error, lo ignora (por eso "quiet" = silenciosamente)
    
    EJEMPLO: Desconexión limpia sin que el programa se bloquee
    """
    try:
        mqtt.disconnect()
    except Exception:
        pass


def mqtt_is_disconnect_error(e):
    """
    FUNCIÓN: Comprueba si un error significa que se perdió la conexión MQTT
    
    ENTRADA: e = excepción/error capturado
    SALIDA: (Verdadero/Falso) = True si es error de desconexión, False si no
    
    VARIABLES IMPORTANTES:
    - code: el código del error
    - _ECONNRESET, _ETIMEDOUT, etc.: códigos de error de red
    
    QUÉ HACE:
    1. Extrae el código de error de la excepción
    2. Comprueba si es uno de estos errores:
       - -1: socket cerrado (la conexión se cortó)
       - ECONNRESET: la red reinició la conexión
       - ETIMEDOUT: tiempo de espera agotado
       - ENOTCONN: no hay conexión
       - EPIPE: tubería rota (conexión muerta)
    3. Devuelve True si es error de desconexión, False si no
    
    EJEMPLO: Si la red se cae, devuelve True y el programa sabe que debe reconectar
    """
    code = None
    try:
        code = e.errno
    except Exception:
        if e.args:
            code = e.args[0]
    return code in (-1, _ECONNRESET, _ETIMEDOUT, _ENOTCONN, _EPIPE)


def mqtt_poll(mqtt, esp_id_hex):
    """
    FUNCIÓN: Recibe mensajes MQTT sin bloquear el programa. Si se desconecta, reconecta.
    
    ENTRADA: 
    - mqtt = objeto de conexión MQTT
    - esp_id_hex (texto) = ID del dispositivo para reconectar si es necesario
    
    SALIDA: mqtt = objeto de conexión MQTT (posiblemente nuevo si se reconectó)
    
    VARIABLES IMPORTANTES:
    - e: el error capturado (si hay)
    
    QUÉ HACE:
    1. Intenta recibir mensajes MQTT rápidamente (sin esperar)
    2. Si llegan mensajes, ejecuta on_mqtt_msg automáticamente
    3. Si hay error de desconexión:
       - Imprime el error
       - Desconecta limpiamente
       - Libera memoria (gc.collect())
       - Espera 300ms
       - Reconecta automáticamente
    4. Si hay otro tipo de error, lo muestra y lo relanza para investigar
    
    EJEMPLO: Cada vez que llamamos a mqtt_poll, se reciben los mensajes pendientes
    """
    try:
        mqtt.check_msg()  # procesa mensajes y llama al callback 
        return mqtt
    except OSError as e:
        if mqtt_is_disconnect_error(e):
            print("[mqtt] disconnected:", repr(e))
            mqtt_disconnect_quiet(mqtt)
            gc.collect()
            time.sleep_ms(300)
            return mqtt_connect(esp_id_hex)
        # Otros errores: mostrarlos para depurar
        print("[mqtt] check_msg unexpected:", repr(e))
        raise


def build_pub_topic(esp_id_hex):
    """
    FUNCIÓN: Construye el nombre del tema MQTT donde publicar los datos del sensor
    
    ENTRADA: esp_id_hex (texto) = ID único del dispositivo
    SALIDA: (bytes) = tema MQTT completo, ej: b"cabrerapinto/meteorologia/a1b2c3/bmp280"
    
    VARIABLES IMPORTANTES:
    - TYPE_NODE: "meteorologia"
    - esp_id_hex: ID del dispositivo
    
    QUÉ HACE:
    1. Crea el texto del tema usando el ID del dispositivo
    2. Lo convierte a bytes para MQTT
    
    EJEMPLO: Si el ID es "5ccf7f1a2b3c", devuelve b"cabrerapinto/meteorologia/5ccf7f1a2b3c/bmp280"
    """
    return ("cabrerapinto/{}/{}/bmp280".format(TYPE_NODE, esp_id_hex)).encode()


def i2c_scan(i2c):
    """
    FUNCIÓN: Busca todos los sensores conectados al bus I2C
    
    ENTRADA: i2c = objeto de comunicación I2C
    SALIDA: (lista) = lista de direcciones de dispositivos encontrados, ej: ["0x76", "0x77"]
    
    VARIABLES IMPORTANTES:
    - a: dirección de cada dispositivo
    
    QUÉ HACE:
    1. Pregunta al bus I2C qué dispositivos hay conectados
    2. Convierte cada dirección a formato hexadecimal legible (0x76, 0x77, etc.)
    3. Devuelve la lista
    
    EJEMPLO: Si hay un sensor BMP280 en la dirección 0x76, devuelve ["0x76"]
    """
    return ["0x%02X" % a for a in i2c.scan()]


def bmp280_init(i2c):
    """
    FUNCIÓN: Inicializa el sensor de temperatura y presión BMP280
    
    ENTRADA: i2c = objeto de comunicación I2C donde está el sensor
    SALIDA: b = objeto del sensor BMP280 listo para usar
    
    VARIABLES IMPORTANTES:
    - b: el sensor BMP280
    
    QUÉ HACE:
    1. Crea un objeto del sensor BMP280
    2. Intenta configurarlo para "caso meteorología" (mediciones de clima en exterior)
    3. Intenta configurarlo en modo "oversample alto" (más précisión)
    4. Si alguna configuración falla, lo ignora y sigue (para compatibilidad con diferentes sensores)
    
    EJEMPLO: Después de esto, puedes leer température y presión
    """
    b = bmp280.BMP280(i2c)

    try:
        b.use_case(bmp280.BMP280_CASE_WEATHER)
    except Exception:
        pass

    try:
        b.oversample(bmp280.BMP280_OS_HIGH)
    except Exception:
        pass

    return b


def pressure_to_altitude_m(p_pa, sea_level_pa=SEA_LEVEL_PA):
    """
    FUNCIÓN: Calcula la altitud en metros usando la presión del aire
    
    ENTRADA: 
    - p_pa (número) = presión medida en Pascales
    - sea_level_pa (número, opcional) = presión a nivel del mar (por defecto 101325 Pa)
    
    SALIDA: (número) = altitud estimada en metros, o None si hay error
    
    VARIABLES IMPORTANTES:
    - 44330.0, 0.1903: constantes matemáticas de la fórmula barométrica
    
    QUÉ HACE:
    1. Usa una fórmula física para calcular la altitud según la presión
    2. Cuanto menor es la presión, mayor es la altitud (porque hay menos aire arriba)
    3. Si hay error, devuelve None
    
    EJEMPLO: A mayor altura, menos presión → más altitud calculada
    """
    try:
        return 44330.0 * (1.0 - math.pow(p_pa / sea_level_pa, 0.1903))
    except Exception:
        return None


def bmp280_read(bmp):
    """
    FUNCIÓN: Lee los datos del sensor BMP280 (temperatura, presión, altitud)
    
    ENTRADA: bmp = objeto del sensor BMP280
    SALIDA: (tres números) = (temperatura_en_grados, presión_en_hpa, altitud_en_metros)
             Si hay error, devuelve None para los valores que no se puedan leer
    
    VARIABLES IMPORTANTES:
    - t_c: temperatura en Celsius
    - p_pa: presión en Pascales
    - p_hpa: presión en hectopascales (se divide entre 100)
    - alt_m: altitud calculada
    
    QUÉ HACE:
    1. Intenta leer la temperatura completa
    2. Lee la presión en Pascales
    3. Convierte la presión a hectopascales (unidad más común en meteorología)
    4. Calcula la altitud usando la presión
    5. Si hay error, imprime el problema y devuelve None para lo que falló
    
    EJEMPLO: (22.5, 1013.25, 50.0) = 22.5°C, 1013.25 hPa, 50 metros de altitud
    """
    t_c = None
    p_hpa = None
    alt_m = None

    try:
        t_c = bmp.temperature
        p_pa = bmp.pressure
        p_hpa = p_pa / 100.0
        alt_m = pressure_to_altitude_m(p_pa)
    except Exception as e:
        print("[bmp280] read error:", repr(e))

    return t_c, p_hpa, alt_m


def main():
    """
    FUNCIÓN PRINCIPAL: Ejecuta todo el programa del ESP8266 con sensor BMP280 y MQTT
    
    ENTRADA: ninguna
    SALIDA: ninguna (corre infinitamente)
    
    VARIABLES IMPORTANTES:
    - sta: conexión WiFi
    - esp_id_hex: ID único del dispositivo
    - i2c: bus de comunicación con sensores
    - i2c_addrs: lista de sensores encontrados
    - bmp: objeto del sensor BMP280
    - mqtt: conexión al servidor MQTT
    - topic_pub: tema MQTT donde publicar
    - last_send: última vez que se enviaron datos
    - last_ping: última vez que se envió un "ping" MQTT
    - payload: diccionario con todos los datos (se convierte a JSON)
    
    QUÉ HACE (PASO A PASO):
    1. INICIO: muestra "[boot] start"
    2. WIFI: conecta a la red WiFi y obtiene el ID único
    3. I2C: escanea qué sensores hay conectados
    4. SENSOR: inicializa el BMP280 (si está disponible)
    5. MQTT: conecta al servidor de mensajería
    6. BUCLE PRINCIPAL INFINITO (cada 80ms):
       - Comprueba si WiFi sigue conectado, si no reconecta
       - Recibe mensajes MQTT (enciende/apaga LED si lo pide)
       - Cada 10 segundos: envía "ping" para verificar que MQTT sigue vivo
       - Cada 5 segundos: 
         * Lee el sensor BMP280 (temperatura, presión, altitud)
         * Crea un diccionario JSON con TODOS los datos:
           - Información del ESP8266: hora, IP, potencia WiFi, MAC, sensores
           - Información del sensor: temperatura, presión, altitud
         * Publica los datos en MQTT
    
    DATOS QUE PUBLICA (EJEMPLO JSON):
    {
        "esp": {
            "ms": 123456,
            "ip": "192.168.1.100",
            "rssi": -45,
            "mac_hex": "5ccf7f1a2b3c",
            "i2c": ["0x76"]
        },
        "sensor": {
            "bmp280": {
                "ok": true,
                "t_c": 22.50,
                "p_hpa": 1013.25,
                "alt_m": 50.30,
                "sea_level_hpa": 1013.25
            }
        }
    }
    
    ERRORES QUE MANEJA:
    - Si WiFi se cae → reconecta automáticamente
    - Si MQTT se desconecta → reconecta automáticamente
    - Si BMP280 no responde → continúa sin datos del sensor
    - Si hay error enviando → intenta reconectar MQTT
    """
    print("[boot] start")

    sta = wifi_connect()
    esp_id_hex = esp_id_from_mac(sta)
    print("[boot] esp_id:", esp_id_hex)

    # I2C init + scan SOLO UNA VEZ (diagnóstico)
    i2c = I2C(scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=I2C_FREQ)
    i2c_addrs = i2c_scan(i2c)
    print("[i2c] scan:", i2c_addrs)

    # BMP280
    bmp = None
    try:
        bmp = bmp280_init(i2c)
        print("[bmp280] init OK")
    except Exception as e:
        print("[bmp280] init ERROR:", repr(e))

    # MQTT
    mqtt = mqtt_connect(esp_id_hex)
    topic_pub = build_pub_topic(esp_id_hex)
    print("[mqtt] pub topic:", topic_pub)

    last_send = time.ticks_ms()
    last_ping = time.ticks_ms()

    while True:
        # WiFi reconnect
        if not sta.isconnected():
            print("[wifi] lost connection, reconnecting...")
            sta = wifi_connect()

        # MQTT receive (rápido, cada vuelta)
        mqtt = mqtt_poll(mqtt, esp_id_hex)

        now = time.ticks_ms()

        # Ping periódico (Mosquitto suele ir bien, pero esto ayuda a detectar caídas antes)
        if time.ticks_diff(now, last_ping) >= 10000:
            last_ping = now
            try:
                mqtt.ping()
            except Exception as e:
                print("[mqtt] ping ERROR:", repr(e))
                mqtt_disconnect_quiet(mqtt)
                gc.collect()
                time.sleep_ms(300)
                mqtt = mqtt_connect(esp_id_hex)

        # Publish periódico
        if time.ticks_diff(now, last_send) >= SEND_PERIOD_MS:
            last_send = now

            # Lee sensor
            t_c, p_hpa, alt_m = (None, None, None)
            if bmp is not None:
                t_c, p_hpa, alt_m = bmp280_read(bmp)

            if (t_c is not None) and (p_hpa is not None) and (alt_m is not None):
                print("[bmp280] t_c=%.2f p_hpa=%.2f alt_m=%.2f" % (t_c, p_hpa, alt_m))

            payload = {
                "esp": {
                    "ms": now,
                    "ip": sta.ifconfig()[0],
                    "rssi": safe_rssi(sta),
                    "mac_hex": esp_id_hex,
                    "i2c": i2c_addrs,  # NO escanear cada vez
                },
                "sensor": {
                    "bmp280": {
                        "ok": (p_hpa is not None),
                        "t_c": t_c,
                        "p_hpa": p_hpa,
                        "alt_m": alt_m,
                        "sea_level_hpa": SEA_LEVEL_HPA,
                    }
                },
            }

            msg = ujson.dumps(payload).encode()

            # Antes/después de publicar, procesa mensajes para mejorar "inmediatez"
            mqtt = mqtt_poll(mqtt, esp_id_hex)
            try:
                mqtt.publish(topic_pub, msg, qos=0, retain=False)
                print("[mqtt] publish OK", len(msg))
            except Exception as e:
                print("[mqtt] publish ERROR:", repr(e))
                mqtt_disconnect_quiet(mqtt)
                gc.collect()
                time.sleep_ms(300)
                mqtt = mqtt_connect(esp_id_hex)
            mqtt = mqtt_poll(mqtt, esp_id_hex)

        # Más aire al sistema (si ves "queue full", sube a 100-200ms)
        time.sleep_ms(80)


main()
