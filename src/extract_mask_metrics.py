from pathlib import Path
import argparse
import csv
import math

import cv2
import numpy as np

from src.manifest_utils import load_manifest


def calculate_contour_metrics(
    mask_path: Path,
    minimum_area: float,
) -> list[dict[str, float]]:
    """Extract geometric measurements from mask contours."""

    mask = cv2.imread(
        str(mask_path),
        cv2.IMREAD_GRAYSCALE,
    )

    if mask is None:
        raise ValueError(
            f"Could not read mask: {mask_path}"
        )

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

    contour_metrics = []

    for contour in contours:
        area = float(cv2.contourArea(contour))

        if area < minimum_area:
            continue

        perimeter = float(
            cv2.arcLength(contour, closed=True)
        )

        equivalent_diameter = (
            2.0 * math.sqrt(area / math.pi)
        )

        circularity = (
            4.0 * math.pi * area / (perimeter ** 2)
            if perimeter > 0
            else 0.0
        )

        contour_metrics.append(
            {
                "area_pixels": area,
                "equivalent_diameter_pixels": equivalent_diameter,
                "perimeter_pixels": perimeter,
                "circularity": circularity,
            }
        )

    return contour_metrics


def summarise_metrics(
    contour_metrics: list[dict[str, float]],
) -> dict[str, float | int]:
    """Calculate one summary row for an image."""

    if not contour_metrics:
        return {
            "bubble_count": 0,
            "mean_area_pixels": 0.0,
            "mean_equivalent_diameter_pixels": 0.0,
            "mean_circularity": 0.0,
        }

    areas = [
        item["area_pixels"]
        for item in contour_metrics
    ]

    diameters = [
        item["equivalent_diameter_pixels"]
        for item in contour_metrics
    ]

    circularities = [
        item["circularity"]
        for item in contour_metrics
    ]

    return {
        "bubble_count": len(contour_metrics),
        "mean_area_pixels": float(np.mean(areas)),
        "mean_equivalent_diameter_pixels": float(
            np.mean(diameters)
        ),
        "mean_circularity": float(
            np.mean(circularities)
        ),
    }


def process_manifest(
    split_name: str,
    minimum_area: float,
) -> Path:
    """Process all masks in one reduced manifest."""

    manifest_path = (
        Path("dataset")
        / "manifests"
        / f"{split_name}_reduced.csv"
    )

    entries = load_manifest(manifest_path)

    output_folder = (
        Path("results")
        / "mask_metrics"
    )
    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_folder
        / f"{split_name}_mask_summary.csv"
    )

    fieldnames = [
        "split",
        "image_name",
        "image_relative_path",
        "mask_relative_path",
        "bubble_count",
        "mean_area_pixels",
        "mean_equivalent_diameter_pixels",
        "mean_circularity",
        "minimum_contour_area",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for index, entry in enumerate(entries, start=1):
            contour_metrics = calculate_contour_metrics(
                mask_path=entry["mask_path"],
                minimum_area=minimum_area,
            )

            summary = summarise_metrics(
                contour_metrics
            )

            writer.writerow(
                {
                    "split": entry["split"],
                    "image_name": entry["image_path"].name,
                    "image_relative_path": (
                        entry["image_relative_path"]
                    ),
                    "mask_relative_path": (
                        entry["mask_relative_path"]
                    ),
                    **summary,
                    "minimum_contour_area": minimum_area,
                }
            )

            if index % 25 == 0 or index == len(entries):
                print(
                    f"{split_name}: processed "
                    f"{index}/{len(entries)} masks"
                )

    print(f"Saved: {output_path}")
    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract bubble metrics from ground-truth masks "
            "listed in reduced manifests."
        )
    )

    parser.add_argument(
        "--split",
        choices=["train", "valid", "test", "all"],
        default="all",
    )

    parser.add_argument(
        "--minimum-area",
        type=float,
        default=10.0,
        help=(
            "Ignore contours smaller than this area "
            "in pixels squared."
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    if arguments.minimum_area < 0:
        raise ValueError(
            "--minimum-area cannot be negative."
        )

    split_names = (
        ["train", "valid", "test"]
        if arguments.split == "all"
        else [arguments.split]
    )

    for split_name in split_names:
        process_manifest(
            split_name=split_name,
            minimum_area=arguments.minimum_area,
        )


if __name__ == "__main__":
    main()