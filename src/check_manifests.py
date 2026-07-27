from pathlib import Path
import csv

from src.dataset_paths import get_dataset_root


def check_manifest(
    manifest_path: Path,
    dataset_root: Path,
) -> tuple[int, list[str]]:
    """Check that all image and mask paths in a manifest exist."""

    checked_rows = 0
    errors = []

    with manifest_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row_number, row in enumerate(reader, start=2):
            checked_rows += 1

            image_path = (
                dataset_root / row["image_relative_path"]
            )
            mask_path = (
                dataset_root / row["mask_relative_path"]
            )

            if not image_path.exists():
                errors.append(
                    f"Row {row_number}: missing image {image_path}"
                )

            if not mask_path.exists():
                errors.append(
                    f"Row {row_number}: missing mask {mask_path}"
                )

    return checked_rows, errors


def main() -> None:
    dataset_root = get_dataset_root()
    manifest_folder = Path("dataset") / "manifests"

    manifest_paths = sorted(
        manifest_folder.glob("*_reduced.csv")
    )

    if not manifest_paths:
        raise FileNotFoundError(
            "No reduced manifest files were found."
        )

    total_errors = 0

    for manifest_path in manifest_paths:
        checked_rows, errors = check_manifest(
            manifest_path,
            dataset_root,
        )

        print(f"{manifest_path.name}: {checked_rows} pairs checked")

        if errors:
            total_errors += len(errors)

            for error in errors[:10]:
                print(f"  ERROR: {error}")

            if len(errors) > 10:
                print(
                    f"  ...and {len(errors) - 10} more errors"
                )
        else:
            print("  All files found.")

    if total_errors:
        raise RuntimeError(
            f"Manifest validation failed with "
            f"{total_errors} missing files."
        )

    print("\nAll reduced manifests are valid.")


if __name__ == "__main__":
    main()