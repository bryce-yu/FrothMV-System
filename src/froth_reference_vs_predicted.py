"""Compare FrothMV's saved 40-image predictions with labelled mask references.

Run from the FrothMV-System repository root as
``python .\\src\\froth_reference_vs_predicted.py ...``. The project package is
``src/mv`` and its existing ``mv.metrics`` functions define the measurements.
Requires numpy and opencv-python from the existing pipeline environment.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean

import cv2
import numpy as np

from mv.metrics import (
    calculate_contour_metrics,
    calculate_mask_area_fraction,
    extract_external_contours,
)


FEATURES = (
    "bubble_count",
    "mean_area_px2",
    "mean_equivalent_diameter_px",
    "mean_circularity",
    "median_equivalent_diameter_px",
    "std_equivalent_diameter_px",
    "ecd_p10_px",
    "ecd_p90_px",
    "mask_area_fraction",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def keyed(rows: list[dict[str, str]], key: str, source: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row[key]
        if not name or name in result:
            raise ValueError(f"Blank or repeated {key} in {source}: {name!r}")
        result[name] = row
    return result


def load_binary_mask(path: Path, foreground: str) -> np.ndarray:
    mask = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if mask is None:
        raise ValueError(f"Could not decode mask: {path}")
    if mask.ndim == 3:
        if mask.shape[2] == 4:
            raise ValueError(f"RGBA mask needs an explicit alpha interpretation: {path}")
        if not np.all(mask == mask[:, :, :1]):
            raise ValueError(f"Colour-coded mask needs a custom foreground mapping: {path}")
        mask = mask[:, :, 0]
    if mask.ndim != 2:
        raise ValueError(f"Expected single-channel mask: {path}")
    values = set(np.unique(mask).tolist())
    if not values.issubset({0, 1, 255}):
        raise ValueError(f"Mask is not binary ({sorted(values)}): {path}")
    return mask != 0 if foreground == "nonzero" else mask == 0


def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True,
                        help="Folder containing test/test_images and test/test_masks")
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Original test_reduced.csv")
    parser.add_argument("--predictions", type=Path, required=True,
                        help="Existing pipeline_features_40.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--foreground", choices=("nonzero", "zero"), default="nonzero",
                        help="Use 'zero' if labelled bubbles are black on a white background")
    args = parser.parse_args()

    manifest_rows = read_rows(args.manifest)
    predicted_rows = read_rows(args.predictions)
    if len(manifest_rows) != 40 or len(predicted_rows) != 40:
        raise ValueError("Expected 40 manifest and 40 prediction rows")

    manifest = keyed(manifest_rows, "image_relative_path", args.manifest)
    predictions = keyed(predicted_rows, "filename", args.predictions)
    filenames = [Path(rel).name for rel in manifest]
    if len(set(filenames)) != 40 or set(filenames) != set(predictions):
        raise ValueError("Manifest filenames are duplicated or do not match predictions")

    results: list[dict] = []
    for image_rel, entry in manifest.items():
        filename = Path(image_rel).name
        pred = predictions[filename]
        if pred["status"] != "OK":
            raise ValueError(f"Non-OK prediction for {filename}: {pred['status']}")

        image_path = args.dataset_root / image_rel
        mask_path = args.dataset_root / entry["mask_relative_path"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not decode test image: {image_path}")
        binary = load_binary_mask(mask_path, args.foreground)
        if binary.shape != image.shape[:2]:
            raise ValueError(f"Image/mask dimensions differ for {filename}: "
                             f"{image.shape[:2]} vs {binary.shape}")

        # Same external-contour and summary definitions as src/mv/pipeline.py.
        min_area = float(pred["minimum_contour_area"])
        contours = extract_external_contours(binary, minimum_area=min_area)
        reference = calculate_contour_metrics(contours)
        reference["mask_area_fraction"] = calculate_mask_area_fraction(binary)

        row = {"filename": filename, "mask_relative_path": entry["mask_relative_path"],
               "reference_foreground_fraction": float(np.mean(binary))}
        for feature in FEATURES:
            ref = float(reference[feature])
            predicted = float(pred[feature])
            row[f"reference_{feature}"] = ref
            row[f"predicted_{feature}"] = predicted
            row[f"error_{feature}"] = predicted - ref
            row[f"absolute_error_{feature}"] = abs(predicted - ref)
        results.append(row)

    summary = []
    for feature in FEATURES:
        errors = [row[f"error_{feature}"] for row in results]
        summary.append({
            "feature": feature,
            "n_images": len(errors),
            "mean_reference": mean(row[f"reference_{feature}"] for row in results),
            "mean_predicted": mean(row[f"predicted_{feature}"] for row in results),
            "mae": mean(abs(error) for error in errors),
            "rmse": math.sqrt(mean(error * error for error in errors)),
            "bias_predicted_minus_reference": mean(errors),
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_rows(args.output_dir / "reference_vs_predicted_40.csv", results,
               list(results[0]))
    write_rows(args.output_dir / "reference_vs_predicted_summary.csv", summary,
               list(summary[0]))
    print(f"Compared {len(results)} images. Results saved to {args.output_dir}")
    print("Inspect reference_foreground_fraction and several mask overlays before reporting errors.")


if __name__ == "__main__":
    main()
