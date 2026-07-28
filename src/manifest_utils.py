from pathlib import Path
import csv

from src.dataset_paths import get_dataset_root


def load_manifest(
    manifest_path: Path,
) -> list[dict[str, Path | str]]:
    """Load a reduced-dataset manifest and resolve local file paths."""

    dataset_root = get_dataset_root()

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest file was not found: {manifest_path}"
        )

    entries = []

    with manifest_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        required_columns = {
            "split",
            "image_relative_path",
            "mask_relative_path",
        }

        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError(
                f"Manifest is missing required columns: {manifest_path}"
            )

        for row_number, row in enumerate(reader, start=2):
            image_path = dataset_root / row["image_relative_path"]
            mask_path = dataset_root / row["mask_relative_path"]

            if not image_path.exists():
                raise FileNotFoundError(
                    f"Missing image at row {row_number}: {image_path}"
                )

            if not mask_path.exists():
                raise FileNotFoundError(
                    f"Missing mask at row {row_number}: {mask_path}"
                )

            entries.append(
                {
                    "split": row["split"],
                    "image_path": image_path,
                    "mask_path": mask_path,
                    "image_relative_path": row["image_relative_path"],
                    "mask_relative_path": row["mask_relative_path"],
                }
            )

    return entries