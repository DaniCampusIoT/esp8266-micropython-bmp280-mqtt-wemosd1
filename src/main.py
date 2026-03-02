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
    mac = sta.config("mac")
    return ubinascii.hexlify(mac).decode()


def safe_rssi(sta):
    try:
        return sta.status("rssi")
    except Exception:
        return None


def led_set_off(is_off):
    # OFF (apagado) => pin=1 si active-low, si no pin=0
    if LED_ACTIVE_LOW:
        led.value(1 if is_off else 0)
    else:
        led.value(0 if is_off else 1)


def parse_led_command(msg):
    """
    msg: bytes
    Regla: ON/TRUE/1 o número > 0 => True
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
    global topic_sub_device

    if topic != TOPIC_SUB_SIMPLE and (topic_sub_device is None or topic != topic_sub_device):
        return

    cmd_on = parse_led_command(msg)

    # Requisito: ON/1 => APAGAR LED
    if cmd_on:
        led_set_off(True)
        print("[led] cmd=ON/1 => LED OFF")
    else:
        led_set_off(False)
        print("[led] cmd=OFF/0 => LED ON")


def mqtt_connect(esp_id_hex):
    """
    Conecta a Mosquitto, configura LWT, callback y suscripciones.
    """
    global topic_sub_device

    client_id = ("ESP8266Client-" + esp_id_hex).encode()
    lwt_topic = ("orchard/{}/{}/connection".format(TYPE_NODE, esp_id_hex)).encode()

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

    topic_sub_device = ("orchard/{}/{}/activate_led".format(TYPE_NODE, esp_id_hex)).encode()

    # Suscripción al topic simple y al específico por dispositivo
    c.subscribe(TOPIC_SUB_SIMPLE)
    print("[mqtt] subscribed:", TOPIC_SUB_SIMPLE)

    c.subscribe(topic_sub_device)
    print("[mqtt] subscribed:", topic_sub_device)

    return c


def mqtt_disconnect_quiet(mqtt):
    try:
        mqtt.disconnect()
    except Exception:
        pass


def mqtt_is_disconnect_error(e):
    # En umqtt.simple, -1 suele ser “socket cerrado” (broker/red) 
    code = None
    try:
        code = e.errno
    except Exception:
        if e.args:
            code = e.args[0]
    return code in (-1, _ECONNRESET, _ETIMEDOUT, _ENOTCONN, _EPIPE)


def mqtt_poll(mqtt, esp_id_hex):
    """
    Procesa mensajes entrantes sin bloquear.
    Si hay desconexión, reconecta.
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
    return ("orchard/{}/{}/bmp280".format(TYPE_NODE, esp_id_hex)).encode()


def i2c_scan(i2c):
    return ["0x%02X" % a for a in i2c.scan()]


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


def pressure_to_altitude_m(p_pa, sea_level_pa=SEA_LEVEL_PA):
    try:
        return 44330.0 * (1.0 - math.pow(p_pa / sea_level_pa, 0.1903))
    except Exception:
        return None


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


def main():
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

            # Antes/después de publicar, procesa mensajes para mejorar “inmediatez”
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

        # Más aire al sistema (si ves “queue full”, sube a 100-200ms)
        time.sleep_ms(80)


main()
