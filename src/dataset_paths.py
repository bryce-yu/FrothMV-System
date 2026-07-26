import os
from pathlib import Path


def get_dataset_root() -> Path:
    """Return the local path to the full froth dataset."""

    dataset_path = os.getenv("FROTH_DATASET_ROOT")

    if not dataset_path:
        raise RuntimeError(
            "FROTH_DATASET_ROOT is not configured. "
            "Set it to the local location of the full Kaggle dataset."
        )

    dataset_root = Path(dataset_path)

    if not dataset_root.exists():
        raise FileNotFoundError(
            f"The configured dataset folder does not exist: {dataset_root}"
        )

    return dataset_root