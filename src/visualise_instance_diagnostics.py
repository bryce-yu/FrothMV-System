"""
Create representative visualisations comparing individual YOLO
instance masks with the combined binary mask and final contours.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from ultralytics import YOLO


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"

SELECTED_CASES_CSV = (
    PROJECT_ROOT
    / "results"
    / "yolo_diagnostics"
    / "selected_diagnostic_cases.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "yolo_diagnostics"
    / "representative_cases"
)

CONFIDENCE = 0.15
IMAGE_SIZE = 640
MAX_DETECTIONS = 1000
MIN_AREA = 10.0


# ---------------------------------------------------------------------
# Mask utilities
# ---------------------------------------------------------------------

def resize_mask(
    mask: np.ndarray,
    image_shape: tuple[int, int],
) -> np.ndarray:
    """Resize a YOLO mask to the original image resolution."""
    height, width = image_shape

    resized = cv2.resize(
        mask.astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_NEAREST,
    )

    return resized > 0.5


def extract_valid_masks(
    result,
    image_shape: tuple[int, int],
    minimum_area: float,
) -> list[np.ndarray]:
    """Return resized instance masks meeting the area threshold."""
    if result.masks is None or result.masks.data is None:
        return []

    raw_masks = result.masks.data.cpu().numpy()

    valid_masks: list[np.ndarray] = []

    for raw_mask in raw_masks:
        binary_mask = resize_mask(raw_mask, image_shape)

        area = int(np.count_nonzero(binary_mask))

        if area >= minimum_area:
            valid_masks.append(binary_mask)

    return valid_masks


def combine_masks(
    masks: list[np.ndarray],
    image_shape: tuple[int, int],
) -> np.ndarray:
    """Combine all valid masks into one binary mask."""
    if not masks:
        return np.zeros(image_shape, dtype=bool)

    return np.logical_or.reduce(masks)


def find_valid_contours(
    combined_mask: np.ndarray,
    minimum_area: float,
) -> list[np.ndarray]:
    """Extract external contours meeting the area threshold."""
    mask_uint8 = combined_mask.astype(np.uint8) * 255

    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    return [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= minimum_area
    ]


# ---------------------------------------------------------------------
# Visualisation utilities
# ---------------------------------------------------------------------

def create_instance_overlay(
    image_rgb: np.ndarray,
    masks: list[np.ndarray],
) -> np.ndarray:
    """
    Overlay individual instance masks using varying display colours.

    Colours are used only to visually distinguish predictions and do
    not represent classes or confidence values.
    """
    overlay = image_rgb.astype(np.float32).copy()

    if not masks:
        return overlay.astype(np.uint8)

    colour_map = plt.get_cmap("hsv")

    for index, mask in enumerate(masks):
        colour = np.array(
            colour_map(index / max(len(masks), 1))[:3]
        ) * 255

        overlay[mask] = (
            0.55 * overlay[mask]
            + 0.45 * colour
        )

    return np.clip(overlay, 0, 255).astype(np.uint8)


def create_contour_overlay(
    image_bgr: np.ndarray,
    contours: list[np.ndarray],
) -> np.ndarray:
    """Draw final combined-mask contours on the source image."""
    contour_image = image_bgr.copy()

    cv2.drawContours(
        contour_image,
        contours,
        contourIdx=-1,
        color=(0, 255, 0),
        thickness=1,
    )

    return cv2.cvtColor(contour_image, cv2.COLOR_BGR2RGB)


def save_diagnostic_figure(
    image_rgb: np.ndarray,
    instance_overlay: np.ndarray,
    combined_mask: np.ndarray,
    contour_overlay: np.ndarray,
    output_path: Path,
    title: str,
    counts_text: str,
) -> None:
    """Save the four-panel diagnostic figure."""
    figure, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0, 0].imshow(image_rgb)
    axes[0, 0].set_title("Original image")

    axes[0, 1].imshow(instance_overlay)
    axes[0, 1].set_title("Individual YOLO instance masks")

    axes[1, 0].imshow(combined_mask, cmap="gray")
    axes[1, 0].set_title("Combined binary mask")

    axes[1, 1].imshow(contour_overlay)
    axes[1, 1].set_title("Combined-mask external contours")

    for axis in axes.flat:
        axis.axis("off")

    figure.suptitle(
        f"{title}\n{counts_text}",
        fontsize=12,
    )

    figure.tight_layout()
    figure.savefig(
        output_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(figure)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    dataset_root_value = os.getenv("FROTH_DATASET_ROOT")

    if not dataset_root_value:
        raise EnvironmentError(
            "FROTH_DATASET_ROOT is not set."
        )

    dataset_root = Path(dataset_root_value)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    if not SELECTED_CASES_CSV.exists():
        raise FileNotFoundError(
            f"Selected-cases CSV not found: {SELECTED_CASES_CSV}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected_df = pd.read_csv(SELECTED_CASES_CSV)

    model = YOLO(str(MODEL_PATH))

    for index, row in selected_df.iterrows():
        filename = row["filename"]

        # Prefer the previously resolved absolute image path.
        if "image_path" in selected_df.columns:
            image_path = Path(str(row["image_path"]))
        else:
            image_path = (
                dataset_root
                / "test"
                / "test_images"
                / filename
            )

        if not image_path.exists():
            image_path = (
                dataset_root
                / "test"
                / "test_images"
                / filename
            )

        image_bgr = cv2.imread(str(image_path))

        if image_bgr is None:
            print(f"Warning: could not read {image_path}")
            continue

        image_rgb = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2RGB,
        )

        height, width = image_bgr.shape[:2]

        predictions = model.predict(
            source=str(image_path),
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            max_det=MAX_DETECTIONS,
            verbose=False,
        )

        result = predictions[0]

        valid_masks = extract_valid_masks(
            result=result,
            image_shape=(height, width),
            minimum_area=MIN_AREA,
        )

        combined_mask = combine_masks(
            valid_masks,
            image_shape=(height, width),
        )

        contours = find_valid_contours(
            combined_mask,
            minimum_area=MIN_AREA,
        )

        instance_overlay = create_instance_overlay(
            image_rgb,
            valid_masks,
        )

        contour_overlay = create_contour_overlay(
            image_bgr,
            contours,
        )

        gt_count = row["ground_truth_contour_count"]
        diagnostic_category = row["diagnostic_category"]

        counts_text = (
            f"GT contours: {gt_count:.0f} | "
            f"YOLO instances: {len(valid_masks)} | "
            f"Combined contours: {len(contours)}"
        )

        safe_stem = Path(filename).stem
        output_path = (
            OUTPUT_DIR
            / f"{diagnostic_category}_{safe_stem}.png"
        )

        save_diagnostic_figure(
            image_rgb=image_rgb,
            instance_overlay=instance_overlay,
            combined_mask=combined_mask,
            contour_overlay=contour_overlay,
            output_path=output_path,
            title=filename,
            counts_text=counts_text,
        )

        print(
            f"[{index + 1}/{len(selected_df)}] "
            f"Saved {output_path.name}"
        )

    print(f"\nVisualisations saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()