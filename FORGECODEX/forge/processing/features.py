import numpy as np
import pandas as pd
from scipy import signal, stats

from config import (
    BANDPASS_FILTER_ORDER,
    BANDPASS_HIGH_HZ,
    BANDPASS_LOW_HZ,
    DEFAULT_FEATURE_FILL,
    EPSILON,
    HIGH_BAND_MAX_HZ,
    LOW_BAND_MAX_HZ,
    MID_BAND_MAX_HZ,
    SAMPLE_RATE,
    WELCH_NPERSEG,
)


class FeatureExtractor:
    def __init__(self) -> None:
        pass

    def extract(
        self,
        audio_chunk: np.ndarray,
        vibration_dict: dict,
        sample_rate: int = SAMPLE_RATE,
    ) -> dict[str, float]:
        filtered_chunk = self._apply_bandpass(audio_chunk, sample_rate)
        rms = float(np.sqrt(np.mean(np.square(filtered_chunk))))
        peak_amplitude = float(np.max(np.abs(filtered_chunk)))
        freqs, power = self._compute_welch(filtered_chunk, sample_rate)
        power_sum = float(np.sum(power))
        spectral_centroid = float(np.sum(freqs * power) / (power_sum + EPSILON))
        spectral_bandwidth = float(
            np.sqrt(np.sum(np.square(freqs - spectral_centroid) * power) / (power_sum + EPSILON))
        )
        low_band_energy = self._band_energy(freqs, power, 0.0, LOW_BAND_MAX_HZ)
        mid_band_energy = self._band_energy(freqs, power, LOW_BAND_MAX_HZ, MID_BAND_MAX_HZ)
        high_band_energy = self._band_energy(freqs, power, MID_BAND_MAX_HZ, HIGH_BAND_MAX_HZ)
        dominant_freq = float(freqs[int(np.argmax(power))]) if power.size else DEFAULT_FEATURE_FILL

        features = {
            "rms": rms,
            "kurtosis": float(stats.kurtosis(filtered_chunk, fisher=False, bias=False)),
            "skewness": float(stats.skew(filtered_chunk, bias=False)),
            "crest_factor": float(peak_amplitude / (rms + EPSILON)),
            "peak_amplitude": peak_amplitude,
            "spectral_centroid": spectral_centroid,
            "spectral_bandwidth": spectral_bandwidth,
            "low_band_energy": low_band_energy,
            "mid_band_energy": mid_band_energy,
            "high_band_energy": high_band_energy,
            "high_low_ratio": float(high_band_energy / (low_band_energy + EPSILON)),
            "dominant_freq": dominant_freq,
            "biometric_wear": DEFAULT_FEATURE_FILL,
            "twin_divergence": DEFAULT_FEATURE_FILL,
        }
        return {key: self._safe_float(value) for key, value in features.items()}

    def _apply_bandpass(self, chunk: np.ndarray, sr: int) -> np.ndarray:
        b_coeff, a_coeff = signal.butter(
            BANDPASS_FILTER_ORDER,
            [BANDPASS_LOW_HZ, BANDPASS_HIGH_HZ],
            btype="band",
            fs=sr,
        )
        return signal.filtfilt(b_coeff, a_coeff, chunk).astype(np.float32)

    def _compute_welch(self, chunk: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
        return signal.welch(chunk, sr, nperseg=WELCH_NPERSEG)

    def _band_energy(
        self,
        freqs: np.ndarray,
        power: np.ndarray,
        lower_hz: float,
        upper_hz: float,
    ) -> float:
        mask = (freqs >= lower_hz) & (freqs < upper_hz)
        return float(np.sum(power[mask]))

    def _safe_float(self, value: float) -> float:
        if np.isnan(value) or np.isinf(value):
            return DEFAULT_FEATURE_FILL
        return float(value)

    def to_dataframe_row(self, features: dict, stroke_num: int, tool_id: str) -> pd.DataFrame:
        row = dict(features)
        row["stroke_num"] = stroke_num
        row["tool_id"] = tool_id
        return pd.DataFrame([row])
