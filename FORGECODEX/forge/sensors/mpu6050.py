import sys
from typing import Any

from config import (
    DEFAULT_ACCEL_AXIS_VALUE,
    DEFAULT_GYRO_AXIS_VALUE,
    DEFAULT_MPU_TEMPERATURE,
    GRAVITY_MPS2,
    I2C_BUS_ID,
    MPU6050_ACCEL_SCALE,
    MPU6050_ACCEL_XOUT_H,
    MPU6050_GYRO_SCALE,
    MPU6050_GYRO_XOUT_H,
    MPU6050_I2C_ADDRESS,
    MPU6050_PWR_MGMT_1,
    MPU6050_TEMP_OUT_H,
    ZERO_VIBRATION_DICT,
)

try:
    from smbus2 import SMBus
except ImportError:  # pragma: no cover - hardware dependency fallback
    SMBus = None


class MPU6050Reader:
    def __init__(self) -> None:
        self.address = MPU6050_I2C_ADDRESS
        self.bus = None
        if SMBus is None:
            print("MPU6050Reader: smbus2 unavailable, using fallback values", file=sys.stderr)
            return
        try:
            self.bus = SMBus(I2C_BUS_ID)
            self.bus.write_byte_data(self.address, MPU6050_PWR_MGMT_1, 0)
        except Exception as exc:
            self.bus = None
            print(f"MPU6050Reader init error: {exc}", file=sys.stderr)

    def _read_raw_word(self, register: int) -> int:
        if self.bus is None:
            raise RuntimeError("I2C bus unavailable")
        high = self.bus.read_byte_data(self.address, register)
        low = self.bus.read_byte_data(self.address, register + 1)
        value = (high << 8) | low
        if value >= 0x8000:
            value = -((65535 - value) + 1)
        return value

    def _read_vector(self, start_register: int, scale: float) -> dict[str, float]:
        axis_labels = ("x", "y", "z")
        values = {}
        for index, label in enumerate(axis_labels):
            raw_value = self._read_raw_word(start_register + (index * 2))
            values[label] = raw_value / scale
        return values

    def read_accel(self) -> dict[str, float]:
        if self.bus is None:
            return {
                "ax": DEFAULT_ACCEL_AXIS_VALUE,
                "ay": DEFAULT_ACCEL_AXIS_VALUE,
                "az": DEFAULT_ACCEL_AXIS_VALUE,
            }
        accel = self._read_vector(MPU6050_ACCEL_XOUT_H, MPU6050_ACCEL_SCALE)
        return {
            "ax": accel["x"] * GRAVITY_MPS2,
            "ay": accel["y"] * GRAVITY_MPS2,
            "az": accel["z"] * GRAVITY_MPS2,
        }

    def read_gyro(self) -> dict[str, float]:
        if self.bus is None:
            return {
                "gx": DEFAULT_GYRO_AXIS_VALUE,
                "gy": DEFAULT_GYRO_AXIS_VALUE,
                "gz": DEFAULT_GYRO_AXIS_VALUE,
            }
        gyro = self._read_vector(MPU6050_GYRO_XOUT_H, MPU6050_GYRO_SCALE)
        return {"gx": gyro["x"], "gy": gyro["y"], "gz": gyro["z"]}

    def read_temp(self) -> float:
        if self.bus is None:
            return DEFAULT_MPU_TEMPERATURE
        raw_value = self._read_raw_word(MPU6050_TEMP_OUT_H)
        return (raw_value / 340.0) + 36.53

    def read_all(self) -> dict[str, float]:
        if self.bus is None:
            return dict(ZERO_VIBRATION_DICT)
        try:
            accel = self.read_accel()
            gyro = self.read_gyro()
            temperature = self.read_temp()
        except Exception as exc:
            print(f"MPU6050Reader.read_all error: {exc}", file=sys.stderr)
            return dict(ZERO_VIBRATION_DICT)
        combined: dict[str, Any] = {}
        combined.update(accel)
        combined.update(gyro)
        combined["temperature"] = temperature
        return combined
