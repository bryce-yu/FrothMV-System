"""
Compare YOLO instance counts against contour counts obtained after
combining all predicted instance masks into one binary mask.

The script processes the fixed test manifest and produces:

results/yolo_diagnostics/instance_count_comparison.csv

Metrics:
- Ground-truth contour count
- Raw YOLO instance count
- Valid YOLO instance count after minimum-area filtering
- Combined-mask contour count
- Errors between these counts
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"

TEST_MANIFEST_PATH = (
    PROJECT_ROOT / "dataset" / "manifests" / "test_reduced.csv"
)

GROUND_TRUTH_METRICS_PATH = (
    PROJECT_ROOT / "results" / "mask_metrics" / "test_mask_summary.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "results" / "yolo_diagnostics"
OUTPUT_CSV_PATH = OUTPUT_DIR / "instance_count_comparison.csv"

CONFIDENCE = 0.15
IMAGE_SIZE = 640
MIN_CONTOUR_AREA = 10.0


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def find_filename_column(df: pd.DataFrame) -> str:
    """
    Find a likely filename or image-path column.

    Adjust the candidate list if your manifest uses a different name.
    """
    candidates = [
        "filename",
        "image_filename",
        "image_name",
        "image_path",
        "image_relative_path",
        "path",
    ]

    for column in candidates:
        if column in df.columns:
            return column

    raise ValueError(
        "Could not identify the filename column. "
        f"Available columns: {list(df.columns)}"
    )


def find_ground_truth_count_column(df: pd.DataFrame) -> str:
    """
    Find the bubble-count column in the existing ground-truth CSV.
    """
    candidates = [
        "bubble_count",
        "contour_count",
        "gt_bubble_count",
        "ground_truth_bubble_count",
    ]

    for column in candidates:
        if column in df.columns:
            return column

    raise ValueError(
        "Could not identify the ground-truth bubble-count column. "
        f"Available columns: {list(df.columns)}"
    )


def resolve_image_path(
    manifest_value: str,
    dataset_root: Path,
) -> Path:
    """
    Resolve an image path from the manifest.

    This supports either:
    - a full absolute path;
    - a path relative to FROTH_DATASET_ROOT;
    - a filename only.
    """
    manifest_path = Path(str(manifest_value))

    if manifest_path.is_absolute():
        return manifest_path

    direct_path = dataset_root / manifest_path

    if direct_path.exists():
        return direct_path

    test_image_path = (
        dataset_root
        / "test"
        / "test_images"
        / manifest_path.name
    )

    if test_image_path.exists():
        return test_image_path

    raise FileNotFoundError(
        f"Could not resolve image path for: {manifest_value}"
    )


def normalise_filename(value: str) -> str:
    """
    Reduce a path or filename to the base filename for CSV matching.
    """
    return Path(str(value)).name


def resize_mask_to_image(
    mask: np.ndarray,
    image_shape: tuple[int, int],
) -> np.ndarray:
    """
    Resize a YOLO mask to the original image resolution.
    """
    image_height, image_width = image_shape

    resized = cv2.resize(
        mask.astype(np.float32),
        (image_width, image_height),
        interpolation=cv2.INTER_NEAREST,
    )

    return resized > 0.5


def count_external_contours(
    binary_mask: np.ndarray,
    minimum_area: float,
) -> int:
    """
    Count external contours whose areas meet the minimum threshold.
    """
    mask_uint8 = binary_mask.astype(np.uint8) * 255

    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    valid_contours = [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= minimum_area
    ]

    return len(valid_contours)


def calculate_mask_area(binary_mask: np.ndarray) -> int:
    """
    Calculate the number of foreground pixels in a binary mask.
    """
    return int(np.count_nonzero(binary_mask))


def extract_instance_diagnostics(
    result,
    image_shape: tuple[int, int],
    minimum_area: float,
) -> dict:
    """
    Extract raw instance count, area-filtered instance count,
    and combined-mask contour count from one YOLO result.
    """
    if result.masks is None or result.masks.data is None:
        return {
            "yolo_raw_instance_count": 0,
            "yolo_valid_instance_count": 0,
            "combined_contour_count": 0,
            "combined_mask_area_pixels": 0,
        }

    raw_masks = result.masks.data.cpu().numpy()

    raw_instance_count = len(raw_masks)

    resized_instance_masks: list[np.ndarray] = []
    valid_instance_masks: list[np.ndarray] = []

    for raw_mask in raw_masks:
        binary_mask = resize_mask_to_image(
            raw_mask,
            image_shape=image_shape,
        )

        resized_instance_masks.append(binary_mask)

        instance_area = calculate_mask_area(binary_mask)

        if instance_area >= minimum_area:
            valid_instance_masks.append(binary_mask)

    valid_instance_count = len(valid_instance_masks)

    if valid_instance_masks:
        combined_mask = np.logical_or.reduce(valid_instance_masks)
    else:
        combined_mask = np.zeros(image_shape, dtype=bool)

    combined_contour_count = count_external_contours(
        combined_mask,
        minimum_area=minimum_area,
    )

    return {
        "yolo_raw_instance_count": raw_instance_count,
        "yolo_valid_instance_count": valid_instance_count,
        "combined_contour_count": combined_contour_count,
        "combined_mask_area_pixels": calculate_mask_area(combined_mask),
    }


# ---------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------

def main() -> None:
    dataset_root_value = os.getenv("FROTH_DATASET_ROOT")

    if not dataset_root_value:
        raise EnvironmentError(
            "FROTH_DATASET_ROOT is not set."
        )

    dataset_root = Path(dataset_root_value)

    if not dataset_root.exists():
        raise FileNotFoundError(
            f"Dataset root does not exist: {dataset_root}"
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"YOLO model not found: {MODEL_PATH}"
        )

    if not TEST_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Test manifest not found: {TEST_MANIFEST_PATH}"
        )

    if not GROUND_TRUTH_METRICS_PATH.exists():
        raise FileNotFoundError(
            "Ground-truth metrics CSV not found: "
            f"{GROUND_TRUTH_METRICS_PATH}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_df = pd.read_csv(TEST_MANIFEST_PATH)
    ground_truth_df = pd.read_csv(GROUND_TRUTH_METRICS_PATH)

    manifest_filename_column = find_filename_column(manifest_df)
    gt_filename_column = find_filename_column(ground_truth_df)
    gt_count_column = find_ground_truth_count_column(ground_truth_df)

    manifest_df["normalised_filename"] = manifest_df[
        manifest_filename_column
    ].apply(normalise_filename)

    ground_truth_df["normalised_filename"] = ground_truth_df[
        gt_filename_column
    ].apply(normalise_filename)

    ground_truth_lookup = dict(
        zip(
            ground_truth_df["normalised_filename"],
            ground_truth_df[gt_count_column],
        )
    )

    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    records: list[dict] = []

    total_start_time = time.perf_counter()

    for index, row in manifest_df.iterrows():
        manifest_value = row[manifest_filename_column]
        filename = normalise_filename(manifest_value)

        image_path = resolve_image_path(
            manifest_value=manifest_value,
            dataset_root=dataset_root,
        )

        image = cv2.imread(str(image_path))

        if image is None:
            print(f"Warning: could not read {image_path}")
            continue

        image_height, image_width = image.shape[:2]

        inference_start = time.perf_counter()

        predictions = model.predict(
            source=str(image_path),
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            max_det=1000, # default previously was 300
            verbose=False,
        )

        inference_time = time.perf_counter() - inference_start

        result = predictions[0]

        diagnostic_values = extract_instance_diagnostics(
            result=result,
            image_shape=(image_height, image_width),
            minimum_area=MIN_CONTOUR_AREA,
        )

        ground_truth_count = ground_truth_lookup.get(filename)

        if ground_truth_count is None:
            print(
                "Warning: no ground-truth count found for "
                f"{filename}"
            )
            ground_truth_count = np.nan

        raw_instance_count = diagnostic_values[
            "yolo_raw_instance_count"
        ]

        valid_instance_count = diagnostic_values[
            "yolo_valid_instance_count"
        ]

        combined_contour_count = diagnostic_values[
            "combined_contour_count"
        ]

        if pd.notna(ground_truth_count):
            gt_to_raw_instance_error = (
                raw_instance_count - ground_truth_count
            )

            gt_to_valid_instance_error = (
                valid_instance_count - ground_truth_count
            )

            gt_to_combined_contour_error = (
                combined_contour_count - ground_truth_count
            )

            absolute_gt_to_instance_error = abs(
                gt_to_valid_instance_error
            )

            absolute_gt_to_contour_error = abs(
                gt_to_combined_contour_error
            )

            if ground_truth_count > 0:
                instance_percentage_error = (
                    absolute_gt_to_instance_error
                    / ground_truth_count
                    * 100
                )

                contour_percentage_error = (
                    absolute_gt_to_contour_error
                    / ground_truth_count
                    * 100
                )
            else:
                instance_percentage_error = np.nan
                contour_percentage_error = np.nan
        else:
            gt_to_raw_instance_error = np.nan
            gt_to_valid_instance_error = np.nan
            gt_to_combined_contour_error = np.nan
            absolute_gt_to_instance_error = np.nan
            absolute_gt_to_contour_error = np.nan
            instance_percentage_error = np.nan
            contour_percentage_error = np.nan

        instance_to_contour_difference = (
            valid_instance_count - combined_contour_count
        )

        records.append(
            {
                "filename": filename,
                "image_path": str(image_path),
                "ground_truth_contour_count": ground_truth_count,
                "yolo_raw_instance_count": raw_instance_count,
                "yolo_valid_instance_count": valid_instance_count,
                "combined_contour_count": combined_contour_count,
                "instance_to_contour_difference": (
                    instance_to_contour_difference
                ),
                "gt_to_raw_instance_error": (
                    gt_to_raw_instance_error
                ),
                "gt_to_valid_instance_error": (
                    gt_to_valid_instance_error
                ),
                "gt_to_combined_contour_error": (
                    gt_to_combined_contour_error
                ),
                "absolute_gt_to_instance_error": (
                    absolute_gt_to_instance_error
                ),
                "absolute_gt_to_contour_error": (
                    absolute_gt_to_contour_error
                ),
                "instance_percentage_error": (
                    instance_percentage_error
                ),
                "contour_percentage_error": (
                    contour_percentage_error
                ),
                "combined_mask_area_pixels": diagnostic_values[
                    "combined_mask_area_pixels"
                ],
                "inference_time_seconds": inference_time,
            }
        )

        print(
            f"[{index + 1:02d}/{len(manifest_df):02d}] "
            f"{filename}: "
            f"GT={ground_truth_count}, "
            f"instances={valid_instance_count}, "
            f"contours={combined_contour_count}"
        )

    total_time = time.perf_counter() - total_start_time

    results_df = pd.DataFrame(records)
    results_df.to_csv(OUTPUT_CSV_PATH, index=False)

    print("\nDiagnostic analysis complete.")
    print(f"Processed images: {len(results_df)}")
    print(f"Total processing time: {total_time:.3f} seconds")
    print(f"Saved results to: {OUTPUT_CSV_PATH}")

    if not results_df.empty:
        print("\nMean counts:")
        print(
            results_df[
                [
                    "ground_truth_contour_count",
                    "yolo_valid_instance_count",
                    "combined_contour_count",
                ]
            ].mean()
        )

        print("\nMean absolute errors:")
        print(
            "YOLO instance-count MAE: "
            f"{results_df['absolute_gt_to_instance_error'].mean():.4f}"
        )
        print(
            "Combined-contour-count MAE: "
            f"{results_df['absolute_gt_to_contour_error'].mean():.4f}"
        )

        print(
            "\nAverage number of YOLO instances lost after "
            "mask combination: "
            f"{results_df['instance_to_contour_difference'].mean():.4f}"
        )

        affected_images = (
            results_df["instance_to_contour_difference"] > 0
        ).sum()

        print(
            "Images where combined contour count was below "
            f"instance count: {affected_images}/{len(results_df)}"
        )


if __name__ == "__main__":
    main()