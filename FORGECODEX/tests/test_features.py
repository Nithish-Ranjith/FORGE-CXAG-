from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CHUNK_SIZE, SAMPLE_RATE
from forge.processing.features import FeatureExtractor


def main() -> None:
    extractor = FeatureExtractor()
    time_axis = np.arange(CHUNK_SIZE, dtype=np.float32) / np.float32(SAMPLE_RATE)
    audio_chunk = np.float32(0.1) * np.sin(np.float32(2.0 * np.pi * 3000.0) * time_axis)
    vibration = {"ax": 0.0, "ay": 0.0, "az": 0.0, "gx": 0.0, "gy": 0.0, "gz": 0.0}
    features = extractor.extract(audio_chunk, vibration, SAMPLE_RATE)

    assert len(features) == 14
    for key, value in features.items():
        assert not np.isnan(value), f"{key} is NaN"
        assert not np.isinf(value), f"{key} is infinite"
    assert abs(features["spectral_centroid"] - 3000.0) < 300.0

    print("Feature extraction acceptance test passed")
    print(features)


if __name__ == "__main__":
    main()
