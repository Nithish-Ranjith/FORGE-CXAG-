import sys
from pathlib import Path

import numpy as np

from config import (
    AUDIO_CHANNELS,
    AUDIO_DEVICE_INDEX,
    CHUNK_SIZE,
    CUTTING_RMS_THRESHOLD,
    DEFAULT_SENSOR_TEMPERATURE,
    DEMO_AUDIO_FILE,
    DEMO_MODE,
    LED_STATUS_PIN,
    PT100_FAULT_TEMPERATURE,
    SAMPLE_RATE,
    ZERO_VIBRATION_DICT,
)
from forge.sensors.mpu6050 import MPU6050Reader
from forge.sensors.pt100 import PT100Reader

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - dependency fallback
    sd = None

try:
    import soundfile as sf
except ImportError:  # pragma: no cover - dependency fallback
    sf = None

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - dependency fallback
    GPIO = None


class SensorCapture:
    def __init__(self) -> None:
        self.sample_rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE
        self.audio_device_index = AUDIO_DEVICE_INDEX
        self.audio_channels = AUDIO_CHANNELS
        self.demo_mode = DEMO_MODE
        self.demo_audio = None
        self.mpu = MPU6050Reader()
        self.pt100 = PT100Reader()
        self.last_raw_rms = 0.0
        self._demo_stroke_count = 0
        self._setup_gpio()
        self._setup_audio()

    def _setup_gpio(self) -> None:
        if GPIO is None:
            return
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(LED_STATUS_PIN, GPIO.OUT)
            GPIO.output(LED_STATUS_PIN, GPIO.LOW)
        except Exception as exc:
            print(f"SensorCapture GPIO setup error: {exc}", file=sys.stderr)

    def _setup_audio(self) -> None:
        if self.demo_mode:
            self._load_demo_audio()
            return
        if sd is None:
            print("SensorCapture: sounddevice unavailable, switching to demo mode", file=sys.stderr)
            self.demo_mode = True
            self._load_demo_audio()

    def _load_demo_audio(self) -> None:
        demo_path = Path(__file__).resolve().parents[2] / DEMO_AUDIO_FILE
        if sf is not None and demo_path.exists():
            try:
                audio_data, sample_rate = sf.read(str(demo_path), dtype="float32")
                if sample_rate != self.sample_rate and audio_data.size > 0:
                    indices = np.linspace(
                        0,
                        len(audio_data) - 1,
                        self.chunk_size,
                        dtype=int,
                    )
                    audio_data = audio_data[indices]
                if audio_data.ndim > 1:
                    audio_data = audio_data[:, 0]
                self.demo_audio = audio_data.astype(np.float32)
                return
            except Exception as exc:
                print(f"SensorCapture demo audio load error: {exc}", file=sys.stderr)
        self.demo_audio = None  # Force synthetic mode if file load fails

    def _generate_synthetic_chunk(self) -> np.ndarray:
        self._demo_stroke_count += 1
        wear_pct = min(1.0, self._demo_stroke_count / 500.0)
        f0 = 1000.0 + (3000.0 * wear_pct)
        f1 = 3000.0 + (9000.0 * wear_pct)
        time_axis = np.arange(self.chunk_size, dtype=np.float32) / np.float32(self.sample_rate)
        signal_low = np.sin(np.float32(2.0 * np.pi * f0) * time_axis)
        signal_high = np.sin(np.float32(2.0 * np.pi * f1) * time_axis)
        chunk = (np.float32(0.05 + 0.05 * wear_pct) * signal_low) + (np.float32(0.03 + 0.07 * wear_pct) * signal_high)
        noise = np.random.normal(0, 0.01 + 0.02 * wear_pct, self.chunk_size).astype(np.float32)
        return chunk + noise

    def capture_chunk(self) -> np.ndarray:
        if self.demo_mode:
            if self.demo_audio is not None and len(self.demo_audio) >= self.chunk_size:
                max_offset = max(1, len(self.demo_audio) - self.chunk_size + 1)
                offset = int(np.random.randint(0, max_offset))
                chunk = self.demo_audio[offset : offset + self.chunk_size]
                if len(chunk) < self.chunk_size:
                    chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)))
            else:
                chunk = self._generate_synthetic_chunk()
            self.last_raw_rms = float(np.sqrt(np.mean(np.square(chunk))))
            return self._normalize_audio(chunk.astype(np.float32))
        recorded = sd.rec(
            frames=self.chunk_size,
            samplerate=self.sample_rate,
            channels=self.audio_channels,
            dtype="float32",
            device=self.audio_device_index,
        )
        sd.wait()
        mono = recorded.reshape(-1)
        self.last_raw_rms = float(np.sqrt(np.mean(np.square(mono))))
        return self._normalize_audio(mono.astype(np.float32))

    def _normalize_audio(self, chunk: np.ndarray) -> np.ndarray:
        peak = float(np.max(np.abs(chunk))) if chunk.size else 0.0
        if peak <= 0.0:
            return np.zeros(self.chunk_size, dtype=np.float32)
        normalized = chunk / np.float32(peak)
        return normalized.astype(np.float32)

    def is_cutting(self, audio_chunk: np.ndarray) -> bool:
        is_active = self.last_raw_rms > CUTTING_RMS_THRESHOLD
        self.blink_led(is_active)
        return is_active

    def read_vibration(self) -> dict[str, float]:
        try:
            return self.mpu.read_all()
        except Exception as exc:
            print(f"SensorCapture.read_vibration error: {exc}", file=sys.stderr)
            return dict(ZERO_VIBRATION_DICT)

    def read_temperature(self) -> float:
        temperature = self.pt100.read_temperature()
        if temperature == PT100_FAULT_TEMPERATURE:
            return DEFAULT_SENSOR_TEMPERATURE
        return temperature

    def blink_led(self, state: bool) -> None:
        if GPIO is None:
            return
        try:
            GPIO.output(LED_STATUS_PIN, GPIO.HIGH if state else GPIO.LOW)
        except Exception as exc:
            print(f"SensorCapture.blink_led error: {exc}", file=sys.stderr)
