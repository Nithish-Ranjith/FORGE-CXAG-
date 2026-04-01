from datetime import datetime
from pathlib import Path
import sys

import librosa
import numpy as np
from scipy.spatial.distance import cosine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    BIOMETRIC_DISTANCE_SCALE,
    CALIBRATION_FACTOR_MAX,
    CALIBRATION_FACTOR_MIN,
    ENROLLMENT_RMS_REFERENCE,
    ENROLLMENT_STROKES,
    MFCC_COUNT,
)


class ToolBiometrics:
    def __init__(self, tool_id: str, physics_engine) -> None:
        self.tool_id = tool_id
        self.physics_engine = physics_engine
        self.identity_vector: np.ndarray | None = None
        self.enrollment_buffer: list[np.ndarray] = []
        self.enrollment_rms_values: list[float] = []
        self.calibrated = False
        self.enrolled_date: str | None = None

    def enroll_stroke(self, audio_chunk: np.ndarray, sr: int = 44100):
        current_mfcc = self._extract_mfcc(audio_chunk, sr)
        self.enrollment_buffer.append(current_mfcc)
        rms_value = float(np.sqrt(np.mean(np.square(audio_chunk))))
        self.enrollment_rms_values.append(rms_value)
        if len(self.enrollment_buffer) == ENROLLMENT_STROKES:
            self._complete_enrollment()
            return "enrolled"
        return None

    def _complete_enrollment(self) -> None:
        self.identity_vector = np.mean(np.vstack(self.enrollment_buffer), axis=0)
        mean_rms = float(np.mean(self.enrollment_rms_values)) if self.enrollment_rms_values else 0.0
        calibration_factor = mean_rms / ENROLLMENT_RMS_REFERENCE if ENROLLMENT_RMS_REFERENCE else 1.0
        if CALIBRATION_FACTOR_MIN <= calibration_factor <= CALIBRATION_FACTOR_MAX:
            self.physics_engine.calibrate_to_tool(calibration_factor)
            self.calibrated = True
        else:
            self.calibrated = False
        self.enrolled_date = datetime.now().isoformat()

    def measure_wear_distance(self, audio_chunk: np.ndarray, sr: int = 44100) -> float:
        if not self.calibrated or self.identity_vector is None:
            return 0.0
        current_mfcc = self._extract_mfcc(audio_chunk, sr)
        distance = cosine(self.identity_vector, current_mfcc) * BIOMETRIC_DISTANCE_SCALE
        if np.isnan(distance) or np.isinf(distance):
            return 0.0
        return float(np.clip(distance, 0.0, 1.0))

    def reset_tool(self, new_tool_id: str) -> None:
        self.tool_id = new_tool_id
        self.identity_vector = None
        self.enrollment_buffer = []
        self.enrollment_rms_values = []
        self.calibrated = False
        self.enrolled_date = None

    def _extract_mfcc(self, audio_chunk: np.ndarray, sr: int) -> np.ndarray:
        mfcc = librosa.feature.mfcc(y=np.asarray(audio_chunk, dtype=np.float32), sr=sr, n_mfcc=MFCC_COUNT)
        return np.mean(mfcc, axis=1)
