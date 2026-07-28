from pathlib import Path
import argparse
import csv
import math

import cv2
import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO

from src.manifest_utils import load_manifest
from src.extract_mask_metrics import (
    calculate_contour_metrics,
    summarise_metrics,
)


def create_combined_prediction_mask(
    result,
    output_height: int,
    output_width: int,
) -> np.ndarray:
    """
    Combine all YOLO instance masks into one binary mask matching
    the original image dimensions.
    """

    combined_mask = np.zeros(
        (output_height, output_width),
        dtype=np.uint8,
    )

    if result.masks is None or len(result.masks.data) == 0:
        return combined_mask

    instance_masks = result.masks.data.cpu().numpy()

    for instance_mask in instance_masks:
        resized_mask = cv2.resize(
            instance_mask,
            (output_width, output_height),
            interpolation=cv2.INTER_NEAREST,
        )

        combined_mask[resized_mask > 0.5] = 255

    return combined_mask


def save_prediction_visualisation(
    image_path: Path,
    ground_truth_mask_path: Path,
    predicted_mask: np.ndarray,
    split_name: str,
) -> Path:
    """Save an original, ground-truth and prediction comparison."""

    image_bgr = cv2.imread(str(image_path))
    ground_truth_mask = cv2.imread(
        str(ground_truth_mask_path),
        cv2.IMREAD_GRAYSCALE,
    )

    if image_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")

    if ground_truth_mask is None:
        raise ValueError(
            f"Could not read ground-truth mask: "
            f"{ground_truth_mask_path}"
        )

    image_rgb = cv2.cvtColor(
        image_bgr,
        cv2.COLOR_BGR2RGB,
    )

    _, predicted_binary = cv2.threshold(
        predicted_mask,
        127,
        255,
        cv2.THRESH_BINARY,
    )

    predicted_contours, _ = cv2.findContours(
        predicted_binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    prediction_overlay = image_rgb.copy()

    cv2.drawContours(
        prediction_overlay,
        predicted_contours,
        contourIdx=-1,
        color=(255, 0, 0),
        thickness=2,
    )

    output_folder = (
        Path("results")
        / "yolo_evaluation"
        / "visualisations"
        / split_name
    )
    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_folder / (
        f"{image_path.stem}_comparison.png"
    )

    figure, axes = plt.subplots(
        1,
        4,
        figsize=(22, 6),
    )

    axes[0].imshow(image_rgb)
    axes[0].set_title("Original image")

    axes[1].imshow(
        ground_truth_mask,
        cmap="gray",
    )
    axes[1].set_title("Ground-truth mask")

    axes[2].imshow(
        predicted_mask,
        cmap="gray",
    )
    axes[2].set_title("YOLO predicted mask")

    axes[3].imshow(prediction_overlay)
    axes[3].set_title(
        f"Predicted contours: {len(predicted_contours)}"
    )

    for axis in axes:
        axis.axis("off")

    figure.suptitle(
        image_path.name,
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


def calculate_metrics_from_array(
    predicted_mask: np.ndarray,
    temporary_mask_path: Path,
    minimum_area: float,
) -> dict[str, float | int]:
    """
    Save a predicted mask temporarily and reuse the existing
    contour-metric extraction function.
    """

    temporary_mask_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(temporary_mask_path),
        predicted_mask,
    )

    if not success:
        raise RuntimeError(
            f"Could not save temporary mask: "
            f"{temporary_mask_path}"
        )

    contour_metrics = calculate_contour_metrics(
        mask_path=temporary_mask_path,
        minimum_area=minimum_area,
    )

    return summarise_metrics(contour_metrics)


def process_test_manifest(
    model_path: Path,
    confidence: float,
    image_size: int,
    minimum_area: float,
    save_visualisation_count: int,
) -> Path:
    """Run YOLO inference on the fixed reduced test manifest."""

    manifest_path = (
        Path("dataset")
        / "manifests"
        / "test_reduced.csv"
    )

    entries = load_manifest(manifest_path)

    model = YOLO(str(model_path))

    output_root = (
        Path("results")
        / "yolo_evaluation"
    )
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    predicted_mask_folder = (
        output_root / "predicted_masks"
    )
    predicted_mask_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics_path = (
        output_root / "predicted_metrics.csv"
    )

    fieldnames = [
        "split",
        "image_name",
        "image_relative_path",
        "predicted_instance_count",
        "bubble_count",
        "mean_area_pixels",
        "mean_equivalent_diameter_pixels",
        "mean_circularity",
        "confidence_threshold",
        "image_size",
        "minimum_contour_area",
    ]

    with metrics_path.open(
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
            image_path = entry["image_path"]
            mask_path = entry["mask_path"]

            image_bgr = cv2.imread(str(image_path))

            if image_bgr is None:
                raise ValueError(
                    f"Could not read image: {image_path}"
                )

            image_height, image_width = image_bgr.shape[:2]

            results = model.predict(
                source=str(image_path),
                conf=confidence,
                imgsz=image_size,
                verbose=False,
            )

            if not results:
                raise RuntimeError(
                    f"No result returned for: {image_path}"
                )

            result = results[0]

            predicted_mask = create_combined_prediction_mask(
                result=result,
                output_height=image_height,
                output_width=image_width,
            )

            predicted_mask_path = (
                predicted_mask_folder
                / image_path.name
            )

            success = cv2.imwrite(
                str(predicted_mask_path),
                predicted_mask,
            )

            if not success:
                raise RuntimeError(
                    f"Could not save predicted mask: "
                    f"{predicted_mask_path}"
                )

            summary = calculate_metrics_from_array(
                predicted_mask=predicted_mask,
                temporary_mask_path=predicted_mask_path,
                minimum_area=minimum_area,
            )

            predicted_instance_count = (
                len(result.masks.data)
                if result.masks is not None
                else 0
            )

            writer.writerow(
                {
                    "split": entry["split"],
                    "image_name": image_path.name,
                    "image_relative_path": (
                        entry["image_relative_path"]
                    ),
                    "predicted_instance_count": (
                        predicted_instance_count
                    ),
                    **summary,
                    "confidence_threshold": confidence,
                    "image_size": image_size,
                    "minimum_contour_area": minimum_area,
                }
            )

            if index <= save_visualisation_count:
                visualisation_path = (
                    save_prediction_visualisation(
                        image_path=image_path,
                        ground_truth_mask_path=mask_path,
                        predicted_mask=predicted_mask,
                        split_name="test",
                    )
                )

                print(
                    f"Saved visualisation: "
                    f"{visualisation_path}"
                )

            print(
                f"Processed {index}/{len(entries)}: "
                f"{image_path.name}"
            )

    print(f"\nPredicted metrics saved to: {metrics_path}")

    return metrics_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the saved YOLO segmentation model on the "
            "fixed reduced test manifest."
        )
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models") / "best.pt",
        help="Path to the trained YOLO segmentation model.",
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="YOLO confidence threshold.",
    )

    parser.add_argument(
        "--image-size",
        type=int,
        default=640,
        help="Inference image size.",
    )

    parser.add_argument(
        "--minimum-area",
        type=float,
        default=10.0,
        help=(
            "Ignore predicted contours below this area "
            "in pixels squared."
        ),
    )

    parser.add_argument(
        "--visualisations",
        type=int,
        default=10,
        help=(
            "Number of prediction comparisons to save."
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    if not arguments.model.exists():
        raise FileNotFoundError(
            f"Model weight was not found: {arguments.model}"
        )

    if not 0.0 <= arguments.confidence <= 1.0:
        raise ValueError(
            "--confidence must be between 0 and 1."
        )

    if arguments.minimum_area < 0:
        raise ValueError(
            "--minimum-area cannot be negative."
        )

    process_test_manifest(
        model_path=arguments.model,
        confidence=arguments.confidence,
        image_size=arguments.image_size,
        minimum_area=arguments.minimum_area,
        save_visualisation_count=arguments.visualisations,
    )


if __name__ == "__main__":
    main()