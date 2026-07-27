from pathlib import Path
from collections import Counter

from src.dataset_paths import get_dataset_root


SPLIT_FOLDERS = {
    "train": {
        "images": "train_images",
        "masks": "train_masks",
    },
    "valid": {
        "images": "valid_images",
        "masks": "valid_masks",
    },
    "test": {
        "images": "test_images",
        "masks": "test_masks",
    },
}


def get_png_files(folder: Path) -> list[Path]:
    """Return all PNG files in a folder, sorted by filename."""
    if not folder.exists():
        return []

    return sorted(
        file_path
        for file_path in folder.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".png"
    )


def find_duplicate_stems(files: list[Path]) -> list[str]:
    """Find duplicate filenames when extensions are ignored."""
    stem_counts = Counter(file_path.stem for file_path in files)

    return sorted(
        stem
        for stem, count in stem_counts.items()
        if count > 1
    )


def validate_split(
    dataset_root: Path,
    split_name: str,
    image_folder_name: str,
    mask_folder_name: str,
) -> list[str]:
    """Validate one dataset split and return report lines."""

    split_root = dataset_root / split_name
    image_folder = split_root / image_folder_name
    mask_folder = split_root / mask_folder_name

    report_lines = [
        f"Split: {split_name}",
        f"Image folder: {image_folder}",
        f"Mask folder: {mask_folder}",
    ]

    if not split_root.exists():
        report_lines.append("ERROR: Split folder does not exist.")
        return report_lines

    if not image_folder.exists():
        report_lines.append("ERROR: Image folder does not exist.")

    if not mask_folder.exists():
        report_lines.append("ERROR: Mask folder does not exist.")

    image_files = get_png_files(image_folder)
    mask_files = get_png_files(mask_folder)

    image_stems = {file_path.stem for file_path in image_files}
    mask_stems = {file_path.stem for file_path in mask_files}

    missing_masks = sorted(image_stems - mask_stems)
    missing_images = sorted(mask_stems - image_stems)

    duplicate_image_stems = find_duplicate_stems(image_files)
    duplicate_mask_stems = find_duplicate_stems(mask_files)

    report_lines.extend(
        [
            f"PNG images: {len(image_files)}",
            f"PNG masks: {len(mask_files)}",
            f"Images without matching masks: {len(missing_masks)}",
            f"Masks without matching images: {len(missing_images)}",
            f"Duplicate image names: {len(duplicate_image_stems)}",
            f"Duplicate mask names: {len(duplicate_mask_stems)}",
        ]
    )

    if missing_masks:
        report_lines.append(
            "First missing masks: " + ", ".join(missing_masks[:10])
        )

    if missing_images:
        report_lines.append(
            "First missing images: " + ", ".join(missing_images[:10])
        )

    if duplicate_image_stems:
        report_lines.append(
            "Duplicate image names: "
            + ", ".join(duplicate_image_stems[:10])
        )

    if duplicate_mask_stems:
        report_lines.append(
            "Duplicate mask names: "
            + ", ".join(duplicate_mask_stems[:10])
        )

    return report_lines


def main() -> None:
    dataset_root = get_dataset_root()

    output_folder = Path("results") / "dataset_checks"
    output_folder.mkdir(parents=True, exist_ok=True)

    report_path = output_folder / "dataset_structure_report.txt"

    full_report = [
        "Froth Bubble Dataset Structure Report",
        "=" * 40,
        f"Dataset root: {dataset_root}",
        "",
    ]

    for split_name, folder_names in SPLIT_FOLDERS.items():
        split_report = validate_split(
            dataset_root=dataset_root,
            split_name=split_name,
            image_folder_name=folder_names["images"],
            mask_folder_name=folder_names["masks"],
        )

        full_report.extend(split_report)
        full_report.append("")
        full_report.append("-" * 40)
        full_report.append("")

    report_text = "\n".join(full_report)

    print(report_text)
    report_path.write_text(report_text, encoding="utf-8")

    print(f"\nReport saved to: {report_path.resolve()}")


if __name__ == "__main__":
    main()