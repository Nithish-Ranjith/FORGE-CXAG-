from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    TFT_ATTENTION_HEADS,
    TFT_BATCH_SIZE,
    TFT_DROPOUT,
    TFT_ENCODER_LENGTH,
    TFT_HIDDEN_CONTINUOUS,
    TFT_HIDDEN_SIZE,
    TFT_LEARNING_RATE,
    TFT_MAX_EPOCHS,
    TFT_MODEL_PATH,
    TFT_OUTPUT_SIZE,
    TFT_PREDICTION_LENGTH,
    TFT_QUANTILES,
    TRAINING_DATA_PATH,
)

try:
    import lightning.pytorch as pl
    from lightning.pytorch.callbacks import ModelCheckpoint
except ImportError:  # pragma: no cover
    try:
        import pytorch_lightning as pl
        from pytorch_lightning.callbacks import ModelCheckpoint
    except ImportError:  # pragma: no cover
        pl = None
        ModelCheckpoint = None

try:
    import torch
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    from pytorch_forecasting.data import GroupNormalizer
    from pytorch_forecasting.metrics import QuantileLoss
except ImportError:  # pragma: no cover
    torch = None
    TemporalFusionTransformer = None
    TimeSeriesDataSet = None
    GroupNormalizer = None
    QuantileLoss = None


def load_training_frame(csv_path: str = TRAINING_DATA_PATH) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    frame["stroke"] = frame["stroke"].astype(int)
    frame["remaining_life"] = frame["remaining_life"].astype(float)
    frame["tool_id"] = frame["tool_id"].astype(str)
    return frame


def build_dataset(frame: pd.DataFrame) -> "TimeSeriesDataSet":
    if TimeSeriesDataSet is None or GroupNormalizer is None:
        raise ImportError("pytorch_forecasting is required to build the TFT dataset")
    return TimeSeriesDataSet(
        frame,
        time_idx="stroke",
        target="remaining_life",
        group_ids=["tool_id"],
        max_encoder_length=TFT_ENCODER_LENGTH,
        max_prediction_length=TFT_PREDICTION_LENGTH,
        time_varying_unknown_reals=[
            "rms",
            "kurtosis",
            "spectral_centroid",
            "high_low_ratio",
            "crest_factor",
            "biometric_wear",
            "twin_divergence",
        ],
        time_varying_known_reals=["stroke", "cutting_speed"],
        target_normalizer=GroupNormalizer(groups=["tool_id"]),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )


def train_and_save(
    csv_path: str = TRAINING_DATA_PATH,
    model_path: str = TFT_MODEL_PATH,
) -> str:
    if (
        pl is None
        or torch is None
        or TemporalFusionTransformer is None
        or QuantileLoss is None
        or ModelCheckpoint is None
    ):
        raise ImportError("torch, pytorch_forecasting, and pytorch_lightning are required for training")

    frame = load_training_frame(csv_path)
    training = build_dataset(frame)
    train_loader = training.to_dataloader(train=True, batch_size=TFT_BATCH_SIZE)

    model = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=TFT_LEARNING_RATE,
        hidden_size=TFT_HIDDEN_SIZE,
        attention_head_size=TFT_ATTENTION_HEADS,
        dropout=TFT_DROPOUT,
        hidden_continuous_size=TFT_HIDDEN_CONTINUOUS,
        output_size=TFT_OUTPUT_SIZE,
        loss=QuantileLoss(quantiles=TFT_QUANTILES),
    )

    checkpoint_dir = Path(model_path).parent
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_callback = ModelCheckpoint(
        dirpath=str(checkpoint_dir),
        filename=Path(model_path).stem,
        save_last=True,
        every_n_epochs=1,
        save_top_k=-1,
    )
    trainer = pl.Trainer(
        max_epochs=TFT_MAX_EPOCHS,
        accelerator="cpu",
        devices=1,
        enable_progress_bar=True,
        enable_checkpointing=True,
        callbacks=[checkpoint_callback],
        logger=False,
        default_root_dir=str(checkpoint_dir),
    )
    trainer.fit(model, train_dataloaders=train_loader)
    trainer.save_checkpoint(model_path)
    return model_path


if __name__ == "__main__":
    saved_path = train_and_save()
    print(f"Saved TFT checkpoint to {saved_path}")
