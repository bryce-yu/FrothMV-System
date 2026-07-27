from pathlib import Path
import argparse
import random

import cv2
import matplotlib.pyplot as plt

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


def get_split_folders(split_name: str) -> tuple[Path, Path]:
    """Return the image and mask folders for a dataset split."""

    if split_name not in SPLIT_FOLDERS:
        valid_splits = ", ".join(SPLIT_FOLDERS)
        raise ValueError(
            f"Unknown split '{split_name}'. "
            f"Choose one of: {valid_splits}"
        )

    dataset_root = get_dataset_root()
    split_root = dataset_root / split_name

    image_folder = (
        split_root / SPLIT_FOLDERS[split_name]["images"]
    )
    mask_folder = (
        split_root / SPLIT_FOLDERS[split_name]["masks"]
    )

    if not image_folder.exists():
        raise FileNotFoundError(
            f"Image folder was not found: {image_folder}"
        )

    if not mask_folder.exists():
        raise FileNotFoundError(
            f"Mask folder was not found: {mask_folder}"
        )

    return image_folder, mask_folder


def load_image_and_mask(
    image_path: Path,
    mask_path: Path,
) -> tuple:
    """Load an RGB image and its grayscale mask."""

    image_bgr = cv2.imread(str(image_path))
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    if image_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")

    if mask is None:
        raise ValueError(f"Could not read mask: {mask_path}")

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    if image_rgb.shape[:2] != mask.shape[:2]:
        raise ValueError(
            "Image and mask dimensions do not match:\n"
            f"Image: {image_rgb.shape[:2]}\n"
            f"Mask: {mask.shape[:2]}"
        )

    return image_rgb, mask


def create_contour_overlay(
    image_rgb,
    mask,
) -> tuple:
    """Draw external mask contours over the original image."""

    _, binary_mask = cv2.threshold(
        mask,
        127,
        255,
        cv2.THRESH_BINARY,
    )

    contours, _ = cv2.findContours(
        binary_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    overlay = image_rgb.copy()

    cv2.drawContours(
        overlay,
        contours,
        contourIdx=-1,
        color=(255, 0, 0),
        thickness=2,
    )

    return overlay, contours


def find_matching_pairs(
    image_folder: Path,
    mask_folder: Path,
) -> list[tuple[Path, Path]]:
    """Find PNG image and mask files with matching filenames."""

    image_paths = sorted(image_folder.glob("*.png"))
    matching_pairs = []

    for image_path in image_paths:
        mask_path = mask_folder / image_path.name

        if mask_path.exists():
            matching_pairs.append((image_path, mask_path))

    return matching_pairs


def save_visualisation(
    split_name: str,
    image_path: Path,
    mask_path: Path,
) -> Path:
    """Create and save an image, mask and contour comparison."""

    image_rgb, mask = load_image_and_mask(
        image_path,
        mask_path,
    )

    overlay, contours = create_contour_overlay(
        image_rgb,
        mask,
    )

    output_folder = (
        Path("results")
        / "dataset_checks"
        / "sample_visualisations"
        / split_name
    )
    output_folder.mkdir(parents=True, exist_ok=True)

    output_path = output_folder / (
        f"{image_path.stem}_visualisation.png"
    )

    figure, axes = plt.subplots(
        1,
        3,
        figsize=(18, 6),
    )

    axes[0].imshow(image_rgb)
    axes[0].set_title("Original image")

    axes[1].imshow(mask, cmap="gray")
    axes[1].set_title("Ground-truth mask")

    axes[2].imshow(overlay)
    axes[2].set_title(
        f"Detected contours: {len(contours)}"
    )

    for axis in axes:
        axis.axis("off")

    figure.suptitle(
        f"{split_name}: {image_path.name}",
        fontsize=14,
    )

    figure.tight_layout()
    figure.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(figure)

    return output_path


def visualise_samples(
    split_name: str,
    sample_count: int,
    random_seed: int,
) -> None:
    """Select and save visualisations for several image-mask pairs."""

    image_folder, mask_folder = get_split_folders(split_name)

    matching_pairs = find_matching_pairs(
        image_folder,
        mask_folder,
    )

    if not matching_pairs:
        raise RuntimeError(
            f"No matching PNG image-mask pairs found for {split_name}."
        )

    sample_count = min(sample_count, len(matching_pairs))

    random_generator = random.Random(random_seed)
    selected_pairs = random_generator.sample(
        matching_pairs,
        sample_count,
    )

    print(f"Dataset split: {split_name}")
    print(f"Matching pairs found: {len(matching_pairs)}")
    print(f"Samples selected: {sample_count}")

    for image_path, mask_path in selected_pairs:
        output_path = save_visualisation(
            split_name,
            image_path,
            mask_path,
        )

        print(f"Saved: {output_path}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualise image, mask and contour samples "
            "from the froth dataset."
        )
    )

    parser.add_argument(
        "--split",
        choices=["train", "valid", "test"],
        default="train",
        help="Dataset split to inspect.",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of image-mask pairs to visualise.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sample selection.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    visualise_samples(
        split_name=arguments.split,
        sample_count=arguments.count,
        random_seed=arguments.seed,
    )


if __name__ == "__main__":
    main()