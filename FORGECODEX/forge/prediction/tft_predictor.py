from collections import deque
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from config import (
    FAILURE_LOWER_BOUND_STROKES,
    TFT_ENCODER_LENGTH,
    TFT_MODEL_PATH,
    TFT_PREDICTION_LENGTH,
)

try:
    import torch
    from pytorch_forecasting import TemporalFusionTransformer
except ImportError:  # pragma: no cover
    torch = None
    TemporalFusionTransformer = None


class FORGEPredictor:
    def __init__(self, model_path: str = TFT_MODEL_PATH) -> None:
        if torch is None or TemporalFusionTransformer is None:
            raise ImportError("torch and pytorch_forecasting are required for FORGEPredictor")
        self.model_path = model_path
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"TFT checkpoint not found at {self.model_path}")
        self.model = self._load_model_checkpoint(self.model_path)
        self.model.eval()
        self.model.to("cpu")
        self.feature_buffer = deque(maxlen=TFT_ENCODER_LENGTH)
        self.fallback_tool_id = self._resolve_fallback_tool_id()

    def _load_model_checkpoint(self, model_path: str):
        try:
            return TemporalFusionTransformer.load_from_checkpoint(model_path)
        except TypeError as exc:
            message = str(exc)
            if "monotone_constraints" not in message and "monotone_constaints" not in message:
                raise
            checkpoint = torch.load(model_path, map_location="cpu")
            hyper_parameters = dict(checkpoint.get("hyper_parameters", {}))
            hyper_parameters.pop("monotone_constraints", None)
            hyper_parameters.pop("monotone_constaints", None)
            checkpoint["hyper_parameters"] = hyper_parameters
            with tempfile.NamedTemporaryFile(suffix=".ckpt", delete=False) as handle:
                temp_path = handle.name
            try:
                torch.save(checkpoint, temp_path)
                return TemporalFusionTransformer.load_from_checkpoint(temp_path)
            finally:
                Path(temp_path).unlink(missing_ok=True)

    def predict(self, feature_vector_dict: dict) -> dict | None:
        self.feature_buffer.append(dict(feature_vector_dict))
        if len(self.feature_buffer) < TFT_ENCODER_LENGTH:
            return None

        frame = self._build_inference_frame()
        with torch.no_grad():
            quantiles = self.model.predict(
                frame,
                mode="quantiles",
                trainer_kwargs={"accelerator": "cpu", "devices": 1, "logger": False, "enable_progress_bar": False},
            )
        return self.get_prediction_dict(quantiles)

    def _build_inference_frame(self) -> pd.DataFrame:
        rows = []
        normalized_tool_id = self._normalize_tool_id(
            str(self.feature_buffer[-1].get("tool_id", self.fallback_tool_id))
        )
        for item in self.feature_buffer:
            row = dict(item)
            row["stroke"] = int(row.get("stroke_num", row.get("stroke", 0)))
            row["tool_id"] = normalized_tool_id
            rows.append(row)

        last_stroke = int(rows[-1]["stroke"])
        tool_id = normalized_tool_id
        cutting_speed = float(rows[-1].get("cutting_speed", 0.0))

        wear_slope = 0.0
        twin_slope = 0.0
        if len(rows) > 1:
            wear_slope = max(0.0, float(rows[-1].get("biometric_wear", 0.0)) - float(rows[-2].get("biometric_wear", 0.0)))
            twin_slope = max(0.0, float(rows[-1].get("twin_divergence", 0.0)) - float(rows[-2].get("twin_divergence", 0.0)))

        for step in range(1, TFT_PREDICTION_LENGTH + 1):
            last_row = rows[-1]
            rows.append(
                {
                    "tool_id": tool_id,
                    "stroke": last_stroke + step,
                    "cutting_speed": cutting_speed,
                    "rms": last_row["rms"],
                    "kurtosis": last_row["kurtosis"],
                    "spectral_centroid": last_row["spectral_centroid"],
                    "high_low_ratio": last_row["high_low_ratio"],
                    "crest_factor": last_row["crest_factor"],
                    "biometric_wear": max(0.0, float(last_row.get("biometric_wear", 0.0)) + wear_slope),
                    "twin_divergence": max(0.0, float(last_row.get("twin_divergence", 0.0)) + twin_slope),
                    "remaining_life": max(0.0, float(last_row.get("remaining_life", 0.0)) - 1.0),
                }
            )
        return pd.DataFrame(rows)

    def _resolve_fallback_tool_id(self) -> str:
        dataset_parameters = getattr(self.model, "dataset_parameters", {}) or {}
        encoders = dataset_parameters.get("categorical_encoders", {})
        for key in ["tool_id", "__group_id__tool_id"]:
            encoder = encoders.get(key)
            classes = getattr(encoder, "classes_", None)
            if isinstance(classes, dict) and classes:
                return next(iter(classes.keys()))
        return "tool_000"

    def _normalize_tool_id(self, tool_id: str) -> str:
        dataset_parameters = getattr(self.model, "dataset_parameters", {}) or {}
        encoders = dataset_parameters.get("categorical_encoders", {})
        for key in ["tool_id", "__group_id__tool_id"]:
            encoder = encoders.get(key)
            classes = getattr(encoder, "classes_", None)
            if isinstance(classes, dict):
                if tool_id in classes:
                    return tool_id
                return self.fallback_tool_id
        return tool_id

    def get_prediction_dict(self, quantiles) -> dict:
        prediction_row = quantiles[0][0] if getattr(quantiles[0], "ndim", 1) > 1 else quantiles[0]
        lower_bound = max(0.0, float(prediction_row[0]))
        median = max(0.0, float(prediction_row[3]))
        upper_bound = max(0.0, float(prediction_row[6]))
        ordered_bounds = sorted([lower_bound, median, upper_bound])
        lower_bound, median, upper_bound = ordered_bounds[0], ordered_bounds[1], ordered_bounds[2]
        if median <= lower_bound:
            median = lower_bound + 1.0
        if upper_bound <= median:
            upper_bound = median + 1.0
        failure_probability = max(0.0, min(1.0, 1.0 - (lower_bound / FAILURE_LOWER_BOUND_STROKES)))
        return {
            "median_remaining_strokes": median,
            "confidence_band": (lower_bound, upper_bound),
            "failure_probability": failure_probability,
            "confidence_pct": 80,
        }
