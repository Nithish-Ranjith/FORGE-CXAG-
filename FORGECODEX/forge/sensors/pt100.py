import math
import sys

from config import (
    PT100_FAULT_TEMPERATURE,
    SPI_BUS_ID,
    SPI_DEVICE_ID,
    SPI_MAX_SPEED_HZ,
    SPI_MODE,
    MAX31865_CONFIG_BIAS_AUTO,
    MAX31865_CONFIG_REGISTER,
    MAX31865_RTD_MSB_REGISTER,
)

try:
    import spidev
except ImportError:  # pragma: no cover - hardware dependency fallback
    spidev = None


class PT100Reader:
    def __init__(self) -> None:
        self.spi = None
        if spidev is None:
            print("PT100Reader: spidev unavailable, using fallback values", file=sys.stderr)
            return
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(SPI_BUS_ID, SPI_DEVICE_ID)
            self.spi.max_speed_hz = SPI_MAX_SPEED_HZ
            self.spi.mode = SPI_MODE
            self.spi.xfer2([MAX31865_CONFIG_REGISTER | 0x80, MAX31865_CONFIG_BIAS_AUTO])
        except Exception as exc:
            self.spi = None
            print(f"PT100Reader init error: {exc}", file=sys.stderr)

    def read_temperature(self) -> float:
        if self.spi is None:
            return PT100_FAULT_TEMPERATURE
        try:
            response = self.spi.xfer2([MAX31865_RTD_MSB_REGISTER, 0x00, 0x00])
            raw_value = ((response[1] << 8) | response[2]) >> 1
            resistance = (raw_value * 400.0) / 32768.0
            return (math.sqrt(0.00232 * ((resistance / 100.0) - 1.0) + 1.0) - 1.0) / 0.00116
        except Exception as exc:
            print(f"PT100Reader.read_temperature error: {exc}", file=sys.stderr)
            return PT100_FAULT_TEMPERATURE
