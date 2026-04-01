from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import FEDERATED_ROUNDS, FLOWER_SERVER_ADDRESS, MIN_FIT_CLIENTS

try:
    import flwr as fl
except ImportError:  # pragma: no cover
    fl = None


def main() -> None:
    if fl is None:
        raise ImportError("flwr is required for the Flower server")
    strategy = fl.server.strategy.FedAvg(
        min_fit_clients=MIN_FIT_CLIENTS,
        min_available_clients=MIN_FIT_CLIENTS,
        min_evaluate_clients=MIN_FIT_CLIENTS,
    )
    fl.server.start_server(
        server_address=FLOWER_SERVER_ADDRESS,
        config=fl.server.ServerConfig(num_rounds=FEDERATED_ROUNDS),
        strategy=strategy,
    )


if __name__ == "__main__":
    main()
