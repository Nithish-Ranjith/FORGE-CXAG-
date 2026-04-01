from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CHUNK_SIZE, DB_PATH, MACHINE_ID, TOOL_ID
from forge.db.audit_log import AuditLog
from forge.sensors.capture import SensorCapture


def main() -> None:
    audit_log = AuditLog(DB_PATH)
    sensor_capture = SensorCapture()

    audio_chunk = sensor_capture.capture_chunk()
    rms_value = float(np.sqrt(np.mean(np.square(audio_chunk))))
    cutting_state = sensor_capture.is_cutting(audio_chunk)
    vibration = sensor_capture.read_vibration()
    temperature = sensor_capture.read_temperature()

    features = {
        "rms": rms_value,
        "kurtosis": 0.0,
        "spectral_centroid": 0.0,
        "high_low_ratio": 0.0,
        "crest_factor": 0.0,
        "biometric_wear": 0.0,
        "twin_divergence": 0.0,
    }
    audit_log.log_sensor(MACHINE_ID, TOOL_ID, 0, features, vibration, temperature)

    print(f"Audio chunk shape {audio_chunk.shape}")
    print(f"RMS value {rms_value:.6f}")
    print(f"is_cutting {cutting_state}")
    print(
        "accel values "
        f"ax={vibration.get('ax', 0.0):.4f}, "
        f"ay={vibration.get('ay', 0.0):.4f}, "
        f"az={vibration.get('az', 0.0):.4f}"
    )
    print(f"temperature value {temperature:.2f}")

    if audio_chunk.shape != (CHUNK_SIZE,):
        raise RuntimeError(f"Unexpected chunk shape: {audio_chunk.shape}")


if __name__ == "__main__":
    main()
