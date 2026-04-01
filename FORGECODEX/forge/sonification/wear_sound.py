from pathlib import Path
import sys
import wave

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    SONIFICATION_BASE_FREQ,
    SONIFICATION_DURATION_SEC,
    SONIFICATION_DIVERGENCE_GAIN,
    SONIFICATION_SAMPLE_RATE,
)


class WearSonifier:
    def synthesize(
        self,
        divergence: float,
        duration_sec: float = SONIFICATION_DURATION_SEC,
        sample_rate: int = SONIFICATION_SAMPLE_RATE,
    ) -> np.ndarray:
        bounded_divergence = max(0.0, float(divergence))
        time_axis = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
        fundamental = SONIFICATION_BASE_FREQ + (bounded_divergence * SONIFICATION_DIVERGENCE_GAIN)
        second_harmonic = fundamental * 2.0
        third_harmonic = fundamental * 3.0
        waveform = (
            0.45 * np.sin(2.0 * np.pi * fundamental * time_axis)
            + 0.30 * np.sin(2.0 * np.pi * second_harmonic * time_axis)
            + 0.20 * np.sin(2.0 * np.pi * third_harmonic * time_axis)
        )
        return np.clip(waveform.astype(np.float32), -1.0, 1.0)

    def save_wav(self, output_path: str, divergence: float) -> str:
        waveform = self.synthesize(divergence)
        pcm = np.int16(waveform * 32767)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SONIFICATION_SAMPLE_RATE)
            handle.writeframes(pcm.tobytes())
        return str(output)
