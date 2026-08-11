import os
import shutil
from pathlib import Path

import pandas as pd


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Update this if your manifest is stored somewhere different
MANIFEST_PATH = PROJECT_ROOT / "dataset" / "manifests" / "test_reduced.csv"

OUTPUT_DIR = PROJECT_ROOT / "dataset" / "pipeline_validation_images"


def main():
    dataset_root = os.environ.get("FROTH_DATASET_ROOT")

    if not dataset_root:
        raise RuntimeError("FROTH_DATASET_ROOT is not set.")

    dataset_root = Path(dataset_root)

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(MANIFEST_PATH)

    if "image_relative_path" not in df.columns:
        raise ValueError(
            "Manifest does not contain 'image_relative_path'. "
            f"Columns found: {list(df.columns)}"
        )

    copied = 0

    for relative_path in df["image_relative_path"]:
        source = dataset_root / Path(relative_path)
        destination = OUTPUT_DIR / source.name

        if not source.exists():
            print(f"Missing: {source}")
            continue

        shutil.copy2(source, destination)
        copied += 1
        print(f"[{copied}/{len(df)}] Copied: {source.name}")

    print()
    print(f"Copied {copied} of {len(df)} images.")
    print(f"Validation folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()