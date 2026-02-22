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
    # Fórmula típica: 44330 * (1 - (p / p0) ^ 0.1903) [web:19]
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

    i2c = I2C(scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=I2C_FREQ)
    print("[i2c] scan:", i2c_scan(i2c))

    bmp = None
    try:
        bmp = bmp280_init(i2c)
        print("[bmp280] init OK")
    except Exception as e:
        print("[bmp280] init ERROR:", repr(e))

    mqtt = mqtt_connect(esp_id_hex)
    topic_pub = build_pub_topic(esp_id_hex)
    print("[mqtt] pub topic:", topic_pub)

    last = time.ticks_ms()
    while True:
        if not sta.isconnected():
            print("[wifi] lost connection, reconnecting...")
            sta = wifi_connect()

        now = time.ticks_ms()
        if time.ticks_diff(now, last) >= SEND_PERIOD_MS:
            last = now

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

            msg = ujson.dumps(payload).encode()

            try:
                mqtt.publish(topic_pub, msg, qos=0, retain=False)
                print("[mqtt] publish OK", len(msg))
            except Exception as e:
                print("[mqtt] publish ERROR:", repr(e))
                try:
                    mqtt.disconnect()
                except Exception:
                    pass
                mqtt = mqtt_connect(esp_id_hex)

        time.sleep_ms(50)


main()
