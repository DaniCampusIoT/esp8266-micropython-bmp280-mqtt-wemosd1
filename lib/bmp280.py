from micropython import const
from ustruct import unpack
import time

# Author David Stenwall (david at stenwall.io)
# Optimized version: fewer I2C transactions, fewer allocations, buffer reuse,
# improved forced-mode behavior, and fixed oversample() register writes.

# Power Modes
BMP280_POWER_SLEEP = const(0)
BMP280_POWER_FORCED = const(1)
BMP280_POWER_NORMAL = const(3)

BMP280_SPI3W_ON = const(1)
BMP280_SPI3W_OFF = const(0)

BMP280_TEMP_OS_SKIP = const(0)
BMP280_TEMP_OS_1 = const(1)
BMP280_TEMP_OS_2 = const(2)
BMP280_TEMP_OS_4 = const(3)
BMP280_TEMP_OS_8 = const(4)
BMP280_TEMP_OS_16 = const(5)

BMP280_PRES_OS_SKIP = const(0)
BMP280_PRES_OS_1 = const(1)
BMP280_PRES_OS_2 = const(2)
BMP280_PRES_OS_4 = const(3)
BMP280_PRES_OS_8 = const(4)
BMP280_PRES_OS_16 = const(5)

# Standby settings in ms
BMP280_STANDBY_0_5 = const(0)
BMP280_STANDBY_62_5 = const(1)
BMP280_STANDBY_125 = const(2)
BMP280_STANDBY_250 = const(3)
BMP280_STANDBY_500 = const(4)
BMP280_STANDBY_1000 = const(5)
BMP280_STANDBY_2000 = const(6)
BMP280_STANDBY_4000 = const(7)

# IIR Filter setting
BMP280_IIR_FILTER_OFF = const(0)
BMP280_IIR_FILTER_2 = const(1)
BMP280_IIR_FILTER_4 = const(2)
BMP280_IIR_FILTER_8 = const(3)
BMP280_IIR_FILTER_16 = const(4)

# Oversampling setting
BMP280_OS_ULTRALOW = const(0)
BMP280_OS_LOW = const(1)
BMP280_OS_STANDARD = const(2)
BMP280_OS_HIGH = const(3)
BMP280_OS_ULTRAHIGH = const(4)

# Oversampling matrix (PRESS_OS, TEMP_OS, sample time in ms)
# Use tuples (immutable) for potential flash-saving when frozen/precompiled.
_BMP280_OS_MATRIX = (
    (BMP280_PRES_OS_1,  BMP280_TEMP_OS_1,  7),
    (BMP280_PRES_OS_2,  BMP280_TEMP_OS_1,  9),
    (BMP280_PRES_OS_4,  BMP280_TEMP_OS_1, 14),
    (BMP280_PRES_OS_8,  BMP280_TEMP_OS_1, 23),
    (BMP280_PRES_OS_16, BMP280_TEMP_OS_2, 44),
)

# Use cases
BMP280_CASE_HANDHELD_LOW = const(0)
BMP280_CASE_HANDHELD_DYN = const(1)
BMP280_CASE_WEATHER = const(2)
BMP280_CASE_FLOOR = const(3)
BMP280_CASE_DROP = const(4)
BMP280_CASE_INDOOR = const(5)

_BMP280_CASE_MATRIX = (
    (BMP280_POWER_NORMAL, BMP280_OS_ULTRAHIGH, BMP280_IIR_FILTER_4,  BMP280_STANDBY_62_5),
    (BMP280_POWER_NORMAL, BMP280_OS_STANDARD,  BMP280_IIR_FILTER_16, BMP280_STANDBY_0_5),
    (BMP280_POWER_FORCED, BMP280_OS_ULTRALOW,  BMP280_IIR_FILTER_OFF, BMP280_STANDBY_0_5),
    (BMP280_POWER_NORMAL, BMP280_OS_STANDARD,  BMP280_IIR_FILTER_4,  BMP280_STANDBY_125),
    (BMP280_POWER_NORMAL, BMP280_OS_LOW,       BMP280_IIR_FILTER_OFF, BMP280_STANDBY_0_5),
    (BMP280_POWER_NORMAL, BMP280_OS_ULTRAHIGH, BMP280_IIR_FILTER_16, BMP280_STANDBY_0_5),
)

_BMP280_REGISTER_ID = const(0xD0)
_BMP280_REGISTER_RESET = const(0xE0)
_BMP280_REGISTER_STATUS = const(0xF3)
_BMP280_REGISTER_CONTROL = const(0xF4)
_BMP280_REGISTER_CONFIG = const(0xF5)  # IIR filter config
_BMP280_REGISTER_DATA = const(0xF7)

# Calibration base register and length (T1..P9 = 24 bytes)
_BMP280_REGISTER_CALIB = const(0x88)
_BMP280_CALIB_LEN = const(24)

# Control register bit fields
_CTRL_OSRS_T_SHIFT = const(5)   # temp oversampling bits 7..5
_CTRL_OSRS_P_SHIFT = const(2)   # press oversampling bits 4..2
_CTRL_MODE_SHIFT   = const(0)   # power mode bits 1..0


class BMP280:
    def __init__(self, i2c_bus, addr=0x76, use_case=BMP280_CASE_HANDHELD_DYN):
        self._bmp_i2c = i2c_bus
        self._i2c_addr = addr

        # Prefer "readinto" style to reduce allocations if the port supports it.
        self._has_readinto = hasattr(i2c_bus, "readfrom_mem_into")

        # Pre-allocated buffers (avoid repeated object creation / fragmentation).
        self._buf1 = bytearray(1)
        self._buf6 = bytearray(6)
        self._buf24 = bytearray(_BMP280_CALIB_LEN)

        # Read calibration block in one transaction.
        self._readinto(_BMP280_REGISTER_CALIB, self._buf24)
        (self._T1, self._T2, self._T3,
         self._P1, self._P2, self._P3, self._P4, self._P5,
         self._P6, self._P7, self._P8, self._P9) = unpack("<HhhHhhhhhhhh", self._buf24)

        # Raw + computed caches
        self._t_raw = 0
        self._p_raw = 0

        self._t_fine = 0
        self._t = 0.0
        self._p = 0.0

        # Cache validity flags
        self._raw_valid = False
        self._tf_valid = False
        self._t_valid = False
        self._p_valid = False

        # Timing / forced-mode support
        self.read_wait_ms = 0      # computed from oversampling/use_case
        self._new_read_ms = 200    # minimum interval between bus reads (ms)
        self._last_read_ts = time.ticks_ms()

        if use_case is not None:
            self.use_case(use_case)

    # --- Low-level I2C helpers (keep original public API intact) ---

    def _read(self, addr, size=1):
        # Return bytes (same behavior as original)
        return self._bmp_i2c.readfrom_mem(self._i2c_addr, addr, size)

    def _write(self, addr, b_arr):
        # Accept int or bytes/bytearray; write bytes to device
        if isinstance(b_arr, int):
            self._buf1[0] = b_arr & 0xFF
            return self._bmp_i2c.writeto_mem(self._i2c_addr, addr, self._buf1)
        if not isinstance(b_arr, (bytes, bytearray)):
            b_arr = bytearray([b_arr])
        return self._bmp_i2c.writeto_mem(self._i2c_addr, addr, b_arr)

    def _readinto(self, addr, buf):
        # Fill existing buffer (avoid allocations when possible)
        if self._has_readinto:
            return self._bmp_i2c.readfrom_mem_into(self._i2c_addr, addr, buf)
        # Fallback: copy returned bytes into caller buffer
        data = self._bmp_i2c.readfrom_mem(self._i2c_addr, addr, len(buf))
        buf[:] = data
        return None

    def _read_u8(self, addr):
        self._readinto(addr, self._buf1)
        return self._buf1[0]

    def _write_u8(self, addr, v):
        self._buf1[0] = v & 0xFF
        return self._bmp_i2c.writeto_mem(self._i2c_addr, addr, self._buf1)

    # --- Measurement / caching ---

    def _invalidate(self):
        self._raw_valid = False
        self._tf_valid = False
        self._t_valid = False
        self._p_valid = False
        self._t_fine = 0
        self._t = 0.0
        self._p = 0.0

    def _maybe_trigger_forced(self):
        # If in forced mode, trigger a new conversion.
        # In the BMP280, writing mode=FORCED starts a single measurement.
        if self.power_mode == BMP280_POWER_FORCED:
            # Start conversion
            self.force_measure()
            # Wait the estimated conversion time computed from oversampling.
            # (If read_wait_ms is 0, keep a minimal delay to avoid instant stale reads.)
            w = self.read_wait_ms or 5
            time.sleep_ms(w)

    def _gauge(self, force=False):
        # Read data registers (pressure+temp raw) with throttling.
        now = time.ticks_ms()
        if (not force) and self._raw_valid:
            if time.ticks_diff(now, self._last_read_ts) < self._new_read_ms:
                return

        # If in forced mode, start a fresh conversion before reading.
        self._maybe_trigger_forced()

        # Read 6 bytes: p[19:12], p[11:4], p[3:0]+t[19:16], t[15:8], t[7:0]
        self._readinto(_BMP280_REGISTER_DATA, self._buf6)
        d = self._buf6

        self._p_raw = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        self._t_raw = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)

        self._last_read_ts = now
        self._raw_valid = True
        self._tf_valid = False
        self._t_valid = False
        self._p_valid = False
        self._t_fine = 0
        self._t = 0.0
        self._p = 0.0

    # --- Public helpers / debug (kept as in original) ---

    def reset(self):
        self._write_u8(_BMP280_REGISTER_RESET, 0xB6)
        self._invalidate()

    def load_test_calibration(self):
        self._T1 = 27504
        self._T2 = 26435
        self._T3 = -1000
        self._P1 = 36477
        self._P2 = -10685
        self._P3 = 3024
        self._P4 = 2855
        self._P5 = 140
        self._P6 = -7
        self._P7 = 15500
        self._P8 = -14600
        self._P9 = 6000
        self._invalidate()

    def load_test_data(self):
        self._t_raw = 519888
        self._p_raw = 415148
        self._raw_valid = True
        self._tf_valid = False
        self._t_valid = False
        self._p_valid = False

    def print_calibration(self):
        print("T1: {} {}".format(self._T1, type(self._T1)))
        print("T2: {} {}".format(self._T2, type(self._T2)))
        print("T3: {} {}".format(self._T3, type(self._T3)))
        print("P1: {} {}".format(self._P1, type(self._P1)))
        print("P2: {} {}".format(self._P2, type(self._P2)))
        print("P3: {} {}".format(self._P3, type(self._P3)))
        print("P4: {} {}".format(self._P4, type(self._P4)))
        print("P5: {} {}".format(self._P5, type(self._P5)))
        print("P6: {} {}".format(self._P6, type(self._P6)))
        print("P7: {} {}".format(self._P7, type(self._P7)))
        print("P8: {} {}".format(self._P8, type(self._P8)))
        print("P9: {} {}".format(self._P9, type(self._P9)))

    # --- Compensation calculations ---

    def _calc_t_fine(self):
        # From datasheet page 22
        self._gauge()
        if not self._tf_valid:
            var1 = (((self._t_raw >> 3) - (self._T1 << 1)) * self._T2) >> 11
            var2 = (((((self._t_raw >> 4) - self._T1) * ((self._t_raw >> 4) - self._T1)) >> 12) * self._T3) >> 14
            self._t_fine = var1 + var2
            self._tf_valid = True

    @property
    def temperature(self):
        self._calc_t_fine()
        if not self._t_valid:
            self._t = ((self._t_fine * 5 + 128) >> 8) / 100.0
            self._t_valid = True
        return self._t

    @property
    def pressure(self):
        # From datasheet page 22
        self._calc_t_fine()
        if not self._p_valid:
            var1 = self._t_fine - 128000
            var2 = var1 * var1 * self._P6
            var2 = var2 + ((var1 * self._P5) << 17)
            var2 = var2 + (self._P4 << 35)
            var1 = ((var1 * var1 * self._P3) >> 8) + ((var1 * self._P2) << 12)
            var1 = (((1 << 47) + var1) * self._P1) >> 33

            if var1 == 0:
                return 0

            p = 1048576 - self._p_raw
            p = int((((p << 31) - var2) * 3125) / var1)
            var1 = (self._P9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self._P8 * p) >> 19
            p = ((p + var1 + var2) >> 8) + (self._P7 << 4)

            self._p = p / 256.0
            self._p_valid = True
        return self._p

    # --- Bit-field helpers (optimized masks) ---

    def _write_bits(self, address, value, length, shift=0):
        d = self._read_u8(address)
        mask = ((1 << length) - 1) << shift
        d = (d & ~mask) | ((value << shift) & mask)
        self._write_u8(address, d)

    def _read_bits(self, address, length, shift=0):
        d = self._read_u8(address)
        mask = (1 << length) - 1
        return (d >> shift) & mask

    @property
    def standby(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 3, 5)

    @standby.setter
    def standby(self, v):
        assert 0 <= v <= 7
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 3, 5)

    @property
    def iir(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 3, 2)

    @iir.setter
    def iir(self, v):
        assert 0 <= v <= 4
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 3, 2)

    @property
    def spi3w(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 1)

    @spi3w.setter
    def spi3w(self, v):
        assert v in (0, 1)
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 1)

    @property
    def temp_os(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 3, _CTRL_OSRS_T_SHIFT)

    @temp_os.setter
    def temp_os(self, v):
        assert 0 <= v <= 5
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 3, _CTRL_OSRS_T_SHIFT)

    @property
    def press_os(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 3, _CTRL_OSRS_P_SHIFT)

    @press_os.setter
    def press_os(self, v):
        assert 0 <= v <= 5
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 3, _CTRL_OSRS_P_SHIFT)

    @property
    def power_mode(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 2, _CTRL_MODE_SHIFT)

    @power_mode.setter
    def power_mode(self, v):
        assert 0 <= v <= 3
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 2, _CTRL_MODE_SHIFT)

    @property
    def is_measuring(self):
        return bool(self._read_bits(_BMP280_REGISTER_STATUS, 1, 3))

    @property
    def is_updating(self):
        return bool(self._read_bits(_BMP280_REGISTER_STATUS, 1))

    @property
    def chip_id(self):
        return self._read(_BMP280_REGISTER_ID, 1)

    @property
    def in_normal_mode(self):
        return self.power_mode == BMP280_POWER_NORMAL

    def force_measure(self):
        self.power_mode = BMP280_POWER_FORCED
        self._invalidate()

    def normal_measure(self):
        self.power_mode = BMP280_POWER_NORMAL
        self._invalidate()

    def sleep(self):
        self.power_mode = BMP280_POWER_SLEEP
        self._invalidate()

    def use_case(self, uc):
        assert 0 <= uc <= 5
        pm, oss, iir, sb = _BMP280_CASE_MATRIX[uc]
        p_os, t_os, self.read_wait_ms = _BMP280_OS_MATRIX[oss]

        # CONFIG: iir (bits 4..2), standby (bits 7..5)
        self._write_u8(_BMP280_REGISTER_CONFIG, (iir << 2) | (sb << 5))

        # CTRL_MEAS: temp_os (7..5), press_os (4..2), mode (1..0)
        self._write_u8(_BMP280_REGISTER_CONTROL, (t_os << 5) | (p_os << 2) | pm)

        self._invalidate()

    def oversample(self, oss):
        # Keep same public API, but correctly program both temp_os and press_os fields.
        assert 0 <= oss <= 4
        p_os, t_os, self.read_wait_ms = _BMP280_OS_MATRIX[oss]
        self._write_bits(_BMP280_REGISTER_CONTROL, p_os, 3, _CTRL_OSRS_P_SHIFT)
        self._write_bits(_BMP280_REGISTER_CONTROL, t_os, 3, _CTRL_OSRS_T_SHIFT)
        self._invalidate()
