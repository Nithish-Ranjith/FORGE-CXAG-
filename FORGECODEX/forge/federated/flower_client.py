import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH, FLOWER_SERVER_ADDRESS, TFT_MODEL_PATH
from forge.db.audit_log import AuditLog
from forge.prediction.tft_predictor import FORGEPredictor

try:
    import flwr as fl
    import torch
except ImportError:  # pragma: no cover
    fl = None
    torch = None


class FORGEFederatedClient(fl.client.NumPyClient):
    def __init__(self, client_id: int, model_path: str = TFT_MODEL_PATH, db_path: str = DB_PATH) -> None:
        self.client_id = client_id
        self.predictor = FORGEPredictor(model_path)
        self.db = AuditLog(db_path)

    def get_parameters(self, config):
        return [value.detach().cpu().numpy() for value in self.predictor.model.state_dict().values()]

    def fit(self, parameters, config):
        self._set_parameters(parameters)
        loss = self._local_fine_tune(epochs=3)
        local_data = self._load_local_training_frame()
        return self.get_parameters(config), len(local_data), {"loss": float(loss)}

    def evaluate(self, parameters, config):
        self._set_parameters(parameters)
        local_data = self._load_local_training_frame()
        if local_data.empty:
            return 0.0, 0, {"loss": 0.0}
        loss = float(local_data["failure_probability"].mean()) if "failure_probability" in local_data else 0.0
        return loss, len(local_data), {"loss": loss}

    def _set_parameters(self, parameters):
        state_dict = self.predictor.model.state_dict()
        new_state = {}
        for key, value in zip(state_dict.keys(), parameters):
            new_state[key] = torch.tensor(value)
        self.predictor.model.load_state_dict(new_state, strict=True)

    def _local_fine_tune(self, epochs: int):
        local_data = self._load_local_training_frame()
        if local_data.empty or "stroke" not in local_data.columns:
            return 0.0
            
        from forge.prediction.train_tft import build_dataset
        try:
            dataset = build_dataset(local_data)
            dataloader = dataset.to_dataloader(train=True, batch_size=16, num_workers=0)
        except Exception as e:
            print(f"Failed to build local dataset for federated fit: {e}")
            return 0.0
            
        optimizer = torch.optim.Adam(self.predictor.model.parameters(), lr=1e-4)
        self.predictor.model.train()
        last_loss = 0.0
        
        for _ in range(epochs):
            for x, y in dataloader:
                optimizer.zero_grad()
                out, _ = self.predictor.model(x)
                loss = self.predictor.model.loss(out, y)
                loss.backward()
                optimizer.step()
                last_loss = float(loss.detach().cpu().item())
                
        self.predictor.model.eval()
        return last_loss

    def _load_local_training_frame(self) -> pd.DataFrame:
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT tool_id, stroke_num as stroke, rms, kurtosis, spectral_centroid,
                   high_low_ratio, crest_factor, biometric_wear, twin_divergence
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT 500
            """
        ).fetchall()
        conn.close()
        
        if not rows:
            return pd.DataFrame()
            
        frame = pd.DataFrame([dict(row) for row in rows])
        frame["cutting_speed"] = 2.5
        frame["remaining_life"] = np.maximum(0, 500.0 - frame["stroke"])
        frame["failure_probability"] = np.clip(frame["high_low_ratio"].fillna(0.0), 0.0, 1.0)
        return frame


def main() -> None:
    if fl is None:
        raise ImportError("flwr is required for the Flower client")
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", type=int, default=0)
    args = parser.parse_args()
    client = FORGEFederatedClient(client_id=args.client_id)
    fl.client.start_numpy_client(server_address=FLOWER_SERVER_ADDRESS, client=client)


if __name__ == "__main__":
    main()
