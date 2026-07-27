from pathlib import Path
import argparse
import csv
import random

from src.dataset_paths import get_dataset_root


SPLIT_CONFIG = {
    "train": {
        "image_folder": "train_images",
        "mask_folder": "train_masks",
        "default_count": 200,
    },
    "valid": {
        "image_folder": "valid_images",
        "mask_folder": "valid_masks",
        "default_count": 40,
    },
    "test": {
        "image_folder": "test_images",
        "mask_folder": "test_masks",
        "default_count": 40,
    },
}


def find_matching_pairs(
    dataset_root: Path,
    split_name: str,
) -> list[tuple[Path, Path]]:
    """Return image-mask pairs with identical filenames."""

    split_config = SPLIT_CONFIG[split_name]

    image_folder = (
        dataset_root
        / split_name
        / split_config["image_folder"]
    )
    mask_folder = (
        dataset_root
        / split_name
        / split_config["mask_folder"]
    )

    if not image_folder.exists():
        raise FileNotFoundError(
            f"Image folder not found: {image_folder}"
        )

    if not mask_folder.exists():
        raise FileNotFoundError(
            f"Mask folder not found: {mask_folder}"
        )

    pairs = []

    for image_path in sorted(image_folder.glob("*.png")):
        mask_path = mask_folder / image_path.name

        if mask_path.exists():
            pairs.append((image_path, mask_path))

    return pairs


def write_manifest(
    output_path: Path,
    dataset_root: Path,
    split_name: str,
    selected_pairs: list[tuple[Path, Path]],
) -> None:
    """Write selected image-mask pairs to a CSV manifest."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "split",
                "image_relative_path",
                "mask_relative_path",
            ],
        )

        writer.writeheader()

        for image_path, mask_path in selected_pairs:
            writer.writerow(
                {
                    "split": split_name,
                    "image_relative_path": image_path.relative_to(
                        dataset_root
                    ).as_posix(),
                    "mask_relative_path": mask_path.relative_to(
                        dataset_root
                    ).as_posix(),
                }
            )


def create_manifest(
    dataset_root: Path,
    split_name: str,
    sample_count: int,
    random_seed: int,
    output_folder: Path,
) -> None:
    """Select reproducible image-mask pairs and write a manifest."""

    matching_pairs = find_matching_pairs(
        dataset_root,
        split_name,
    )

    if sample_count > len(matching_pairs):
        raise ValueError(
            f"Requested {sample_count} pairs from {split_name}, "
            f"but only {len(matching_pairs)} matching pairs exist."
        )

    random_generator = random.Random(random_seed)

    selected_pairs = random_generator.sample(
        matching_pairs,
        sample_count,
    )

    selected_pairs.sort(key=lambda pair: pair[0].name)

    manifest_path = (
        output_folder
        / f"{split_name}_reduced.csv"
    )

    write_manifest(
        output_path=manifest_path,
        dataset_root=dataset_root,
        split_name=split_name,
        selected_pairs=selected_pairs,
    )

    print(
        f"{split_name}: selected {sample_count} "
        f"of {len(matching_pairs)} matching pairs"
    )
    print(f"Saved manifest: {manifest_path}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create reproducible reduced dataset manifests "
            "from the full froth dataset."
        )
    )

    parser.add_argument(
        "--train-count",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--valid-count",
        type=int,
        default=40,
    )

    parser.add_argument(
        "--test-count",
        type=int,
        default=40,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    dataset_root = get_dataset_root()
    output_folder = Path("dataset") / "manifests"

    requested_counts = {
        "train": arguments.train_count,
        "valid": arguments.valid_count,
        "test": arguments.test_count,
    }

    print(f"Dataset root: {dataset_root}")
    print(f"Random seed: {arguments.seed}")
    print()

    for split_name, sample_count in requested_counts.items():
        create_manifest(
            dataset_root=dataset_root,
            split_name=split_name,
            sample_count=sample_count,
            random_seed=arguments.seed,
            output_folder=output_folder,
        )


if __name__ == "__main__":
    main()