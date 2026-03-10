import os
import sys
import time
import shutil
import argparse
import subprocess
import importlib.util
from pathlib import Path


# ============================================================
# Consola UTF-8 en Windows
# ============================================================
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        except Exception:
            pass


# ============================================================
# Config base
# ============================================================
REPO_ROOT = Path(__file__).resolve().parent
FIRMWARE_DIR = REPO_ROOT / "firmware"
LIB_DIR = REPO_ROOT / "lib"
SRC_DIR = REPO_ROOT / "src"

DEFAULT_FIRMWARE_BIN = FIRMWARE_DIR / "ESP8266_GENERIC-20251209-v1.27.0.bin"
BMP280_PY = LIB_DIR / "bmp280.py"
APP_PY = SRC_DIR / "app.py"
MAIN_PY = SRC_DIR / "main.py"

DEFAULT_BAUD = 460800
DEFAULT_MPREMOTE_RETRIES = 4
DEFAULT_MPREMOTE_DELAY_S = 1.0
POST_FLASH_WAIT_S = 3.0
PRE_REPL_WAIT_S = 2.0


# ============================================================
# Lanzador Python
# ============================================================
def python_module_prefix():
    if os.name == "nt" and shutil.which("py"):
        return ["py", "-m"]
    return [sys.executable, "-m"]


# ============================================================
# CLI
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Setup automatico ESP8266 + BMP280 + MicroPython + MQTT"
    )
    parser.add_argument("--port", help="Puerto serie, por ejemplo COM6")
    parser.add_argument("--firmware", help="Ruta al .bin de MicroPython")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Baudios para write-flash")
    parser.add_argument("--flash-size", dest="flash_size", default="detect",
                        help="Valor para flash size: detect, 4MB, 2MB, none")
    parser.add_argument("--no-erase", action="store_true", help="No borrar flash antes de grabar")
    parser.add_argument("--repl", action="store_true", help="Abrir REPL al terminar")
    parser.add_argument("--yes", action="store_true", help="Aceptar por defecto el puerto recomendado")
    parser.add_argument("--mpremote-retries", type=int, default=DEFAULT_MPREMOTE_RETRIES,
                        help="Reintentos para mpremote")
    return parser.parse_args()


# ============================================================
# Utilidades base
# ============================================================
def run(cmd, check=True, capture=False):
    print(f"\n[CMD] {' '.join(str(x) for x in cmd)}")

    if capture:
        result = subprocess.run(cmd, text=True, capture_output=True)
        if check and result.returncode != 0:
            raise RuntimeError(
                f"Comando fallo con codigo {result.returncode}: {' '.join(str(x) for x in cmd)}\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        for line in p.stdout:
            print(line, end="")
    finally:
        p.wait()

    if check and p.returncode != 0:
        raise RuntimeError(f"Comando fallo con codigo {p.returncode}: {' '.join(str(x) for x in cmd)}")

    return p.returncode


def install_pip_package(package_name):
    print(f"[INSTALANDO] {package_name} ...")
    run(python_module_prefix() + ["pip", "install", "--upgrade", package_name])


def ensure_import(import_name, pip_name=None):
    pip_name = pip_name or import_name
    if importlib.util.find_spec(import_name) is None:
        install_pip_package(pip_name)


def ensure_module_cli(module_name, pip_name=None):
    pip_name = pip_name or module_name
    result = subprocess.run(
        python_module_prefix() + [module_name, "--help"],
        text=True,
        capture_output=True
    )
    if result.returncode != 0:
        install_pip_package(pip_name)


def path_exists_or_raise(path_obj, label):
    if not path_obj.is_file():
        raise FileNotFoundError(f"No se encuentra {label}: {path_obj}")


def choose_firmware_path(cli_value=None):
    if cli_value:
        fw = Path(cli_value).expanduser().resolve()
        if not fw.is_file():
            raise FileNotFoundError(f"No se encuentra el firmware indicado: {fw}")
        return fw

    if DEFAULT_FIRMWARE_BIN.is_file():
        return DEFAULT_FIRMWARE_BIN

    bins = sorted(FIRMWARE_DIR.glob("*.bin"))
    if len(bins) == 1:
        print(f"[INFO] Usando firmware detectado automaticamente: {bins[0]}")
        return bins[0]

    if not bins:
        raise FileNotFoundError(
            f"No hay ficheros .bin en {FIRMWARE_DIR}"
        )

    raise RuntimeError(
        "Hay varios .bin en firmware/. Usa --firmware para indicar cual quieres usar."
    )


# ============================================================
# Dependencias
# ============================================================
def ensure_tools():
    print("[STEP] Comprobando/instalando herramientas...")
    ensure_import("serial", "pyserial")
    ensure_module_cli("esptool", "esptool")
    ensure_module_cli("mpremote", "mpremote")
    ensure_module_cli("mpy_cross", "mpy-cross")
    print("[OK] pyserial OK")
    print("[OK] esptool OK")
    print("[OK] mpremote OK")
    print("[OK] mpy-cross OK")


# ============================================================
# Import tardio de pyserial
# ============================================================
def get_serial_ports():
    import serial.tools.list_ports
    return list(serial.tools.list_ports.comports())


# ============================================================
# Deteccion esptool
# ============================================================
def detect_esptool_commands():
    result = run(python_module_prefix() + ["esptool", "--help"], capture=True, check=False)
    help_text = ((result.stdout or "") + "\n" + (result.stderr or "")).lower()

    if "erase_flash" in help_text:
        erase_cmd = "erase_flash"
    elif "erase-flash" in help_text:
        erase_cmd = "erase-flash"
    else:
        erase_cmd = "erase_flash"

    if "write_flash" in help_text:
        write_cmd = "write_flash"
    elif "write-flash" in help_text:
        write_cmd = "write-flash"
    else:
        write_cmd = "write_flash"

    print(f"[INFO] esptool usa erase: {erase_cmd}")
    print(f"[INFO] esptool usa write: {write_cmd}")
    return erase_cmd, write_cmd


def detect_flash_size_option(write_cmd):
    result = run(
        python_module_prefix() + ["esptool", write_cmd, "--help"],
        capture=True,
        check=False
    )
    help_text = ((result.stdout or "") + "\n" + (result.stderr or "")).lower()

    if "--flash_size" in help_text:
        print("[INFO] Opcion flash size detectada: --flash_size")
        return "--flash_size"
    if "--flash-size" in help_text:
        print("[INFO] Opcion flash size detectada: --flash-size")
        return "--flash-size"

    print("[INFO] No se detecta opcion de flash size; se omitira")
    return None


# ============================================================
# Ranking de puertos COM
# ============================================================
def score_port(port_info):
    desc = (port_info.description or "").upper()
    hwid = (port_info.hwid or "").upper()
    manufacturer = (getattr(port_info, "manufacturer", "") or "").upper()
    product = (getattr(port_info, "product", "") or "").upper()

    vid = getattr(port_info, "vid", None)
    pid = getattr(port_info, "pid", None)
    serial_number = getattr(port_info, "serial_number", None)
    location = getattr(port_info, "location", None)

    score = 0
    reasons = []

    known_usb_uart = {
        (0x10C4, 0xEA60): "Silicon Labs CP210x",
        (0x1A86, 0x7523): "CH340",
        (0x1A86, 0x5523): "CH341/CH340",
        (0x0403, 0x6001): "FTDI FT232",
    }

    if (vid, pid) in known_usb_uart:
        score += 100
        reasons.append(f"VID:PID reconocido ({known_usb_uart[(vid, pid)]})")

    strong_tokens = [
        "CP210",
        "CH340",
        "CH341",
        "USB TO UART",
        "USB-SERIAL",
        "SILICON LABS",
        "UART BRIDGE",
        "FTDI",
    ]
    for token in strong_tokens:
        if token in desc or token in hwid or token in manufacturer or token in product:
            score += 40
            reasons.append(f"Coincidencia: {token}")
            break

    if "BLUETOOTH" in desc or "BLUETOOTH" in hwid:
        score -= 80
        reasons.append("Puerto Bluetooth")

    if "USB" in desc or "USB" in hwid:
        score += 10
        reasons.append("Dispositivo USB")

    if serial_number:
        score += 10
        reasons.append("Tiene numero de serie USB")

    if manufacturer:
        score += 5
    if product:
        score += 5
    if location:
        score += 3

    return score, reasons


def format_vidpid(port_info):
    vid = getattr(port_info, "vid", None)
    pid = getattr(port_info, "pid", None)
    if vid is None or pid is None:
        return "-"
    return f"{vid:04X}:{pid:04X}"


def detect_com_port(auto_accept=False):
    ports = get_serial_ports()
    if not ports:
        raise RuntimeError("No se ha encontrado ningun puerto serie. Conecta la placa y prueba de nuevo.")

    ranked = []
    for p in ports:
        score, reasons = score_port(p)
        ranked.append((score, reasons, p))

    ranked.sort(key=lambda x: x[0], reverse=True)

    print("\nPuertos serie detectados:\n")
    for idx, (score, reasons, p) in enumerate(ranked, start=1):
        label = "RECOMENDADO" if idx == 1 and score > 0 else "OTRO"
        manufacturer = getattr(p, "manufacturer", None) or "-"
        product = getattr(p, "product", None) or "-"
        serial_number = getattr(p, "serial_number", None) or "-"
        location = getattr(p, "location", None) or "-"
        vidpid = format_vidpid(p)
        reason_text = ", ".join(reasons) if reasons else "Sin coincidencias claras"

        print(f"[{label}] {idx}) {p.device}")
        print(f"   Descripcion : {p.description}")
        print(f"   Fabricante  : {manufacturer}")
        print(f"   Producto    : {product}")
        print(f"   VID:PID     : {vidpid}")
        print(f"   Serie USB   : {serial_number}")
        print(f"   Ubicacion   : {location}")
        print(f"   Puntuacion  : {score}")
        print(f"   Motivo      : {reason_text}")
        print()

    default_idx = 1

    if auto_accept:
        selected = ranked[default_idx - 1][2].device
        print(f"Seleccionado automaticamente: {selected}")
        return selected

    while True:
        choice = input(
            f"Cual puerto usar? [1-{len(ranked)}, Enter={default_idx}, r=refrescar, q=salir]: "
        ).strip()

        if choice.lower() == "q":
            print("Cancelado.")
            sys.exit(0)

        if choice.lower() == "r":
            return detect_com_port(auto_accept=False)

        if choice == "":
            selected = ranked[default_idx - 1][2].device
            print(f"Seleccionado: {selected}")
            return selected

        try:
            idx = int(choice)
            if 1 <= idx <= len(ranked):
                selected = ranked[idx - 1][2].device
                print(f"Seleccionado: {selected}")
                return selected
            print(f"Numero invalido (usa 1-{len(ranked)})")
        except ValueError:
            print("Introduce un numero, Enter, 'r' o 'q'.")


# ============================================================
# esptool
# ============================================================
def erase_flash(port, erase_cmd):
    print("\n[STEP] Borrando flash del ESP8266...")
    run(
        python_module_prefix() + [
            "esptool",
            "--chip", "esp8266",
            "--port", port,
            erase_cmd
        ]
    )


def flash_firmware(port, firmware_bin, write_cmd, flash_size_opt, flash_size_value, baud):
    print("\n[STEP] Flasheando firmware MicroPython...")

    base_cmd = python_module_prefix() + [
        "esptool",
        "--chip", "esp8266",
        "--port", port,
        "--baud", str(baud),
        write_cmd,
    ]

    cmd = list(base_cmd)

    if flash_size_opt and flash_size_value and str(flash_size_value).lower() != "none":
        cmd.extend([flash_size_opt, str(flash_size_value)])

    cmd.extend([
        "0x00000",
        str(firmware_bin)
    ])

    try:
        run(cmd)
    except RuntimeError:
        if flash_size_opt and flash_size_value and str(flash_size_value).lower() != "none":
            print("[WARN] Fallo con opcion de flash size; reintentando sin esa opcion...")
            fallback_cmd = list(base_cmd) + ["0x00000", str(firmware_bin)]
            run(fallback_cmd)
        else:
            raise


# ============================================================
# mpy-cross
# ============================================================
def compile_one_to_mpy(py_file):
    path_exists_or_raise(py_file, py_file.name)
    out_mpy = py_file.with_suffix(".mpy")

    needs_build = (not out_mpy.exists()) or (py_file.stat().st_mtime > out_mpy.stat().st_mtime)
    if not needs_build:
        print(f"[OK] {out_mpy.name} ya esta actualizado.")
        return out_mpy

    run(python_module_prefix() + ["mpy_cross", str(py_file)])

    if not out_mpy.is_file():
        raise RuntimeError(f"No se genero {out_mpy}")

    print(f"[OK] Generado: {out_mpy}")
    return out_mpy


def compile_to_mpy():
    print("\n[STEP] Compilando modulos a .mpy...")
    path_exists_or_raise(BMP280_PY, "bmp280.py")
    path_exists_or_raise(APP_PY, "app.py")
    path_exists_or_raise(MAIN_PY, "main.py")

    bmp_mpy = compile_one_to_mpy(BMP280_PY)
    app_mpy = compile_one_to_mpy(APP_PY)
    return bmp_mpy, app_mpy


# ============================================================
# mpremote robusto
# ============================================================
def mpremote_cmd(port, *args, check=True, capture=False):
    return run(
        python_module_prefix() + ["mpremote", "connect", port, *args],
        check=check,
        capture=capture
    )


def _combined_output(result_or_text):
    if isinstance(result_or_text, str):
        return result_or_text.lower()
    return (((result_or_text.stdout or "") + "\n" + (result_or_text.stderr or "")).lower())


def is_raw_repl_error_text(text):
    text = _combined_output(text)
    return (
        "could not enter raw repl" in text
        or "transporterror" in text
        or "raw repl" in text
    )


def is_not_found_text(text):
    text = _combined_output(text)
    return "no such file or directory" in text


def mpremote_soft_reset(port, quiet=False):
    result = mpremote_cmd(port, "soft-reset", check=False, capture=True)
    if not quiet:
        if result.returncode == 0:
            print("[INFO] soft-reset OK")
        else:
            print("[INFO] soft-reset no confirmado; continuamos")
    return result.returncode == 0


def mpremote_cmd_retry(port, *args, retries=4, delay_s=1.0, check=True, capture=False, recover=True):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            return mpremote_cmd(port, *args, check=check, capture=capture)
        except RuntimeError as e:
            last_error = e
            msg = str(e)
            print(f"[WARN] mpremote fallo (intento {attempt}/{retries}).")

            if attempt < retries:
                if recover and is_raw_repl_error_text(msg):
                    print("[INFO] Fallo entrando en raw repl; intentando soft-reset antes de reintentar...")
                    mpremote_soft_reset(port, quiet=False)
                else:
                    print("[INFO] Reintentando comando mpremote...")

                time.sleep(delay_s)
            else:
                raise

    raise last_error


def remote_dir_exists(port, remote_path):
    result = mpremote_cmd_retry(
        port, "fs", "ls", remote_path,
        retries=2, delay_s=1.0, check=False, capture=True
    )
    output = _combined_output(result)
    return result.returncode == 0 and not is_not_found_text(output)


def ensure_remote_dir(port, remote_dir_name, retries=4):
    remote_path = f":{remote_dir_name}"
    print(f"\n[STEP] Asegurando carpeta {remote_dir_name} en el ESP8266...")

    if remote_dir_exists(port, remote_path):
        print(f"[OK] La carpeta {remote_path} ya existe.")
        return

    for attempt in range(1, retries + 1):
        print(f"[INFO] Intentando crear {remote_path} (intento {attempt}/{retries})...")
        result = mpremote_cmd(port, "fs", "mkdir", remote_dir_name, check=False, capture=True)
        output = _combined_output(result)

        if result.returncode == 0:
            if remote_dir_exists(port, remote_path):
                print(f"[OK] Carpeta {remote_path} creada correctamente.")
                return
        else:
            if "file exists" in output or "already exists" in output:
                print(f"[OK] La carpeta {remote_path} ya existia.")
                return

            if is_raw_repl_error_text(output):
                print(f"[WARN] Fallo temporal de raw repl al crear {remote_path}.")
                mpremote_soft_reset(port, quiet=True)

        time.sleep(1.0)

        if remote_dir_exists(port, remote_path):
            print(f"[OK] La carpeta {remote_path} ya esta disponible.")
            return

    raise RuntimeError(f"No se pudo crear/verificar la carpeta {remote_path} tras varios intentos.")


def rm_remote_if_exists(port, remote_path):
    print(f"[INFO] Borrando {remote_path} en el ESP si existe...")
    result = mpremote_cmd(port, "fs", "rm", remote_path, check=False, capture=True)
    output = _combined_output(result)

    if result.returncode == 0:
        print(f"[OK] Borrado: {remote_path}")
        return

    if is_not_found_text(output):
        print(f"[INFO] {remote_path} no existe; continuamos.")
        return

    if is_raw_repl_error_text(output):
        print("[WARN] Error temporal de raw repl al borrar; reintentando una vez...")
        mpremote_soft_reset(port, quiet=True)
        result2 = mpremote_cmd(port, "fs", "rm", remote_path, check=False, capture=True)
        output2 = _combined_output(result2)

        if result2.returncode == 0 or is_not_found_text(output2):
            print(f"[INFO] Estado final aceptable para {remote_path}.")
            return

    raise RuntimeError(f"No se pudo borrar {remote_path}:\n{output}")


def prepare_fs(port):
    print("\n[STEP] Preparando sistema de ficheros en el ESP8266...")
    ensure_remote_dir(port, "lib")
    rm_remote_if_exists(port, ":lib/bmp280.py")
    rm_remote_if_exists(port, ":app.py")


def upload_file_with_retry(port, local_file, remote_path, retries=3):
    path_exists_or_raise(local_file, local_file.name)

    for attempt in range(1, retries + 1):
        result = mpremote_cmd(port, "fs", "cp", str(local_file), remote_path, check=False, capture=True)
        output = _combined_output(result)

        if result.returncode == 0:
            print(f"[OK] Copiado: {local_file.name} -> {remote_path}")
            return

        print(f"[WARN] Fallo copiando {local_file.name} (intento {attempt}/{retries}).")

        if remote_path.startswith(":lib/"):
            ensure_remote_dir(port, "lib")

        if is_raw_repl_error_text(output):
            print("[INFO] Recuperando con soft-reset...")
            mpremote_soft_reset(port, quiet=True)

        if attempt < retries:
            time.sleep(1.0)
        else:
            raise RuntimeError(f"No se pudo copiar {local_file} a {remote_path}:\n{output}")


def upload_files(port, bmp_mpy, app_mpy):
    print("\n[STEP] Subiendo ficheros al ESP8266...")
    ensure_remote_dir(port, "lib")

    upload_file_with_retry(port, bmp_mpy, ":lib/bmp280.mpy", retries=4)
    upload_file_with_retry(port, MAIN_PY, ":main.py", retries=4)
    upload_file_with_retry(port, app_mpy, ":app.mpy", retries=4)

    print("\n[STEP] Listando raiz del ESP...")
    mpremote_cmd_retry(port, "fs", "ls", retries=2, delay_s=1.0)

    print("\n[STEP] Listando :lib...")
    mpremote_cmd_retry(port, "fs", "ls", ":lib", retries=2, delay_s=1.0)


# ============================================================
# Reset / REPL
# ============================================================
def reset_device(port):
    print("\n[STEP] Reset del ESP8266...")
    mpremote_cmd_retry(port, "reset", retries=2, delay_s=1.0)


def open_repl_if_requested(port, force_open=False):
    ans = "s" if force_open else input("\nQuieres abrir REPL ahora? [s/N]: ").strip().lower()
    if ans == "s":
        print("\n[STEP] Abriendo REPL (Ctrl+] para salir, Ctrl+D para soft reset)...")
        run(python_module_prefix() + ["mpremote", "connect", port, "repl"], check=False)


# ============================================================
# Main
# ============================================================
def main():
    args = parse_args()

    print("=== Setup automatico ESP8266 + BMP280 + MicroPython + MQTT ===")
    print(f"[INFO] Directorio del repo: {REPO_ROOT}")

    ensure_tools()

    firmware_bin = choose_firmware_path(args.firmware)
    print(f"[INFO] Firmware seleccionado: {firmware_bin}")

    erase_cmd, write_cmd = detect_esptool_commands()
    flash_size_opt = detect_flash_size_option(write_cmd)

    path_exists_or_raise(BMP280_PY, "bmp280.py")
    path_exists_or_raise(APP_PY, "app.py")
    path_exists_or_raise(MAIN_PY, "main.py")

    port = args.port or detect_com_port(auto_accept=args.yes)
    print(f"[INFO] Usando puerto serie: {port}")

    if not args.no_erase:
        erase_flash(port, erase_cmd)
    else:
        print("[INFO] Se omite erase_flash por opcion del usuario.")

    flash_size_value = None if str(args.flash_size).lower() == "none" else args.flash_size
    flash_firmware(port, firmware_bin, write_cmd, flash_size_opt, flash_size_value, args.baud)

    print(f"\n[INFO] Esperando {POST_FLASH_WAIT_S:.0f} segundos tras flashear firmware...")
    time.sleep(POST_FLASH_WAIT_S)

    prepare_fs(port)
    bmp_mpy, app_mpy = compile_to_mpy()
    upload_files(port, bmp_mpy, app_mpy)

    reset_device(port)

    print(f"\n[INFO] Esperando {PRE_REPL_WAIT_S:.0f} segundos antes de abrir REPL...")
    time.sleep(PRE_REPL_WAIT_S)

    print("\n[TODO OK] Proceso completo.")
    print("El ESP deberia arrancar main.py y cargar app.mpy.")
    print("Para volver a ver logs: py -m mpremote connect COMx repl")

    open_repl_if_requested(port, force_open=args.repl)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INT] Cancelado por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        sys.exit(1)
