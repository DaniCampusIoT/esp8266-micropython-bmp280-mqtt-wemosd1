import time
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

# Presión a nivel del mar (QNH) en hPa para calcular altitud.
# 1013.25 hPa es estándar; si lo cambias por el de tu zona mejorará la altitud.
SEA_LEVEL_HPA = 1013.25
SEA_LEVEL_PA = SEA_LEVEL_HPA * 100.0


# --------------------------------------------------------------------
# Función: wifi_status_str(st)
# Utilidad:
#   Convertir el código numérico de estado WiFi (WLAN.status()) en texto
#   para que los logs sean entendibles.
# Entradas:
#   st (int): estado devuelto por sta.status().
# Salida:
#   (str): nombre del estado o el número en texto si no se reconoce.
# Notas:
#   - getattr(..., -999) permite compatibilidad si STAT_CONNECT_FAIL no existe.
# --------------------------------------------------------------------
def wifi_status_str(st):
    m = {
        network.STAT_IDLE: "IDLE",
        network.STAT_CONNECTING: "CONNECTING",
        network.STAT_WRONG_PASSWORD: "WRONG_PASSWORD",
        network.STAT_NO_AP_FOUND: "NO_AP_FOUND",
        getattr(network, "STAT_CONNECT_FAIL", -999): "CONNECT_FAIL",
        network.STAT_GOT_IP: "GOT_IP",
    }
    return m.get(st, str(st))


# --------------------------------------------------------------------
# Función: wifi_connect(timeout_ms=20000)
# Utilidad:
#   Conectar el ESP8266 a la WiFi (modo estación) y esperar hasta obtener IP.
# Entradas:
#   timeout_ms (int): tiempo máximo de espera (milisegundos).
# Salida:
#   sta (network.WLAN): objeto WLAN ya conectado (con IP).
# Errores:
#   - Lanza RuntimeError si se supera el timeout.
# Notas:
#   - Imprime cambios de estado para depuración.
#   - Si ya está conectado, retorna inmediatamente.
# --------------------------------------------------------------------
def wifi_connect(timeout_ms=20000):
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


# --------------------------------------------------------------------
# Función: esp_id_from_mac(sta)
# Utilidad:
#   Generar un identificador estable del dispositivo a partir de su MAC.
# Entradas:
#   sta (network.WLAN): interfaz WiFi.
# Salida:
#   (str): MAC en hexadecimal, sin separadores, p.ej. "a1b2c3d4e5f6".
# Notas:
#   - Útil para topics MQTT únicos por dispositivo.
# --------------------------------------------------------------------
def esp_id_from_mac(sta):
    mac = sta.config("mac")  # bytes
    return ubinascii.hexlify(mac).decode()  # str


# --------------------------------------------------------------------
# Función: safe_rssi(sta)
# Utilidad:
#   Leer el RSSI (potencia de señal WiFi) sin romper el programa si el
#   firmware/placa no soporta sta.status("rssi").
# Entradas:
#   sta (network.WLAN): interfaz WiFi.
# Salida:
#   (int | None): RSSI en dBm, o None si no está disponible.
# --------------------------------------------------------------------
def safe_rssi(sta):
    try:
        return sta.status("rssi")
    except Exception:
        return None


# --------------------------------------------------------------------
# Función: mqtt_connect(esp_id_hex)
# Utilidad:
#   Conectarse al broker MQTT y publicar estado Online (con LWT Offline).
# Entradas:
#   esp_id_hex (str): id del ESP (normalmente MAC en hex).
# Salida:
#   (MQTTClient): cliente MQTT ya conectado.
# Notas:
#   - client_id/topic se codifican a bytes, como espera umqtt.simple.
#   - LWT (Last Will) publica "Offline" si el cliente se cae sin desconectar.
# --------------------------------------------------------------------
def mqtt_connect(esp_id_hex):
    client_id = ("ESP8266Client-" + esp_id_hex).encode()
    lwt_topic = ("orchard/{}/{}/connection".format(TYPE_NODE, esp_id_hex)).encode()

    c = MQTTClient(
        client_id,
        MQTT_HOST,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        keepalive=30,
    )

    c.set_last_will(lwt_topic, b"Offline", retain=True, qos=1)
    c.connect()
    c.publish(lwt_topic, b"Online", retain=True, qos=1)
    return c


# --------------------------------------------------------------------
# Función: build_pub_topic(esp_id_hex)
# Utilidad:
#   Construir el topic MQTT donde se publicarán las lecturas del BMP280.
# Entradas:
#   esp_id_hex (str): id del ESP.
# Salida:
#   (bytes): topic MQTT en bytes, p.ej. b"orchard/meteorologia/<id>/bmp280".
# Notas:
#   - Se devuelve bytes para evitar conversiones en cada publish().
# --------------------------------------------------------------------
def build_pub_topic(esp_id_hex):
    return ("orchard/{}/{}/bmp280".format(TYPE_NODE, esp_id_hex)).encode()


# --------------------------------------------------------------------
# Función: i2c_scan(i2c)
# Utilidad:
#   Detectar dispositivos en el bus I2C y devolver direcciones legibles.
# Entradas:
#   i2c (machine.I2C): bus I2C inicializado.
# Salida:
#   (list[str]): lista con direcciones tipo "0x76", "0x77", etc.
# Notas:
#   - Muy útil para validar cableado y dirección del sensor.
# --------------------------------------------------------------------
def i2c_scan(i2c):
    return ["0x%02X" % a for a in i2c.scan()]


# --------------------------------------------------------------------
# Función: bmp280_init(i2c)
# Utilidad:
#   Inicializar el sensor BMP280 (driver) en el bus I2C.
# Entradas:
#   i2c (machine.I2C): bus I2C inicializado.
# Salida:
#   (BMP280): instancia del driver del sensor.
# Notas:
#   - Algunos drivers soportan "use_case" y "oversample"; si no existen,
#     se ignoran sin fallar.
# --------------------------------------------------------------------
def bmp280_init(i2c):
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


# --------------------------------------------------------------------
# Función: pressure_to_altitude_m(p_pa, sea_level_pa=SEA_LEVEL_PA)
# Utilidad:
#   Calcular altitud aproximada (metros) a partir de presión actual y
#   presión a nivel del mar (QNH).
# Entradas:
#   p_pa (float): presión actual en Pa (Pascales).
#   sea_level_pa (float): presión a nivel del mar en Pa.
# Salida:
#   (float | None): altitud en metros, o None si el cálculo falla.
# Notas:
#   - Es una estimación: depende mucho del QNH real del momento.
# --------------------------------------------------------------------
def pressure_to_altitude_m(p_pa, sea_level_pa=SEA_LEVEL_PA):
    # Fórmula típica: 44330 * (1 - (p / p0) ^ 0.1903)
    try:
        return 44330.0 * (1.0 - math.pow(p_pa / sea_level_pa, 0.1903))
    except Exception:
        return None


# --------------------------------------------------------------------
# Función: bmp280_read(bmp)
# Utilidad:
#   Leer temperatura, presión y altitud del BMP280.
# Entradas:
#   bmp (BMP280): instancia del sensor.
# Salida:
#   (tuple): (t_c, p_hpa, alt_m)
#     - t_c (float | None): temperatura en °C
#     - p_hpa (float | None): presión en hPa
#     - alt_m (float | None): altitud estimada en metros
# Notas:
#   - Si falla la lectura, devuelve Nones y registra el error.
# --------------------------------------------------------------------
def bmp280_read(bmp):
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


# --------------------------------------------------------------------
# Función: main()
# Utilidad:
#   Punto de entrada del programa:
#   - Conecta WiFi
#   - Inicializa I2C + BMP280
#   - Conecta MQTT
#   - Publica JSON periódicamente con t/p/alt + datos del ESP
# Entradas:
#   (ninguna)
# Salida:
#   (ninguna) -> bucle infinito
# Notas:
#   - Si se pierde WiFi, reintenta conexión.
#   - Si falla publish, reintenta reconexión MQTT.
#   - El payload se envía como bytes (ujson.dumps(...).encode()).
# --------------------------------------------------------------------
def main():
    print("[boot] start")

    sta = wifi_connect()
    esp_id_hex = esp_id_from_mac(sta)
    print("[boot] esp_id:", esp_id_hex)

    # Inicializar I2C y mostrar dispositivos detectados
    i2c = I2C(scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=I2C_FREQ)
    print("[i2c] scan:", i2c_scan(i2c))

    # Inicializar BMP280 (si falla, bmp queda None y el programa sigue)
    bmp = None
    try:
        bmp = bmp280_init(i2c)
        print("[bmp280] init OK")
    except Exception as e:
        print("[bmp280] init ERROR:", repr(e))

    # Conectar MQTT y preparar topic de publicación
    mqtt = mqtt_connect(esp_id_hex)
    topic_pub = build_pub_topic(esp_id_hex)
    print("[mqtt] pub topic:", topic_pub)

    last = time.ticks_ms()

    while True:
        # Reintento de WiFi si se cae
        if not sta.isconnected():
            print("[wifi] lost connection, reconnecting...")
            sta = wifi_connect()

        now = time.ticks_ms()

        # Control de envío periódico (cada SEND_PERIOD_MS)
        if time.ticks_diff(now, last) >= SEND_PERIOD_MS:
            last = now

            # Leer sensor (si existe)
            t_c, p_hpa, alt_m = (None, None, None)
            if bmp is not None:
                t_c, p_hpa, alt_m = bmp280_read(bmp)

            # Log local de valores si todo está OK
            if (t_c is not None) and (p_hpa is not None) and (alt_m is not None):
                print("[bmp280] t_c=%.2f p_hpa=%.2f alt_m=%.2f" % (t_c, p_hpa, alt_m))

            # Payload JSON: datos del ESP + sensor
            payload = {
                "esp": {
                    "ms": now,
                    "ip": sta.ifconfig()[0],
                    "rssi": safe_rssi(sta),
                    "mac_hex": esp_id_hex,
                    "i2c": i2c_scan(i2c),
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

            # MQTT publish requiere bytes (no str)
            msg = ujson.dumps(payload).encode()

            try:
                mqtt.publish(topic_pub, msg, qos=0, retain=False)
                print("[mqtt] publish OK", len(msg))
            except Exception as e:
                # Si falla la publicación, intentamos reconectar MQTT
                print("[mqtt] publish ERROR:", repr(e))
                try:
                    mqtt.disconnect()
                except Exception:
                    pass
                mqtt = mqtt_connect(esp_id_hex)

        # Pequeña pausa para no saturar CPU
        time.sleep_ms(50)


main()
