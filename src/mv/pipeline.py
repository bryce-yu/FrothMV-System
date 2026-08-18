"""
Reusable YOLO-based froth machine-vision pipeline.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from .config import MVConfig
from .metrics import (
    calculate_contour_metrics,
    combine_instance_masks,
    extract_external_contours,
    calculate_mask_area_fraction,
)


class FrothMVPipeline:
    """
    Reusable machine-vision pipeline for froth bubble analysis.

    The YOLO model is loaded once when the pipeline object is created.
    """

    def __init__(self, config: MVConfig) -> None:
        config.validate()

        self.config = config
        self.model = YOLO(str(config.model_path))

    @staticmethod
    def _resize_mask(
        mask: np.ndarray,
        image_shape: tuple[int, int],
    ) -> np.ndarray:
        """
        Resize a YOLO prediction mask to the original image resolution.
        """
        height, width = image_shape

        resized = cv2.resize(
            mask.astype(np.float32),
            (width, height),
            interpolation=cv2.INTER_NEAREST,
        )

        return resized > 0.5

    def _extract_valid_instance_masks(
        self,
        result: Any,
        image_shape: tuple[int, int],
    ) -> list[np.ndarray]:
        """
        Convert YOLO masks to original-resolution binary masks and
        remove masks below the configured minimum area.
        """
        if result.masks is None or result.masks.data is None:
            return []

        raw_masks = result.masks.data.cpu().numpy()

        valid_masks: list[np.ndarray] = []

        for raw_mask in raw_masks:
            binary_mask = self._resize_mask(
                raw_mask,
                image_shape=image_shape,
            )

            mask_area = int(np.count_nonzero(binary_mask))

            if (
                mask_area
                >= self.config.minimum_contour_area
            ):
                valid_masks.append(binary_mask)

        return valid_masks

    def process_image(
        self,
        image_path: str | Path,
    ) -> dict[str, object]:
        """
        Process one image and return structured soft-sensor metrics.
        """
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"OpenCV could not read image: {path}"
            )

        height, width = image.shape[:2]

        start_time = time.perf_counter()

        predictions = self.model.predict(
            source=str(path),
            conf=self.config.confidence,
            imgsz=self.config.image_size,
            max_det=self.config.max_detections,
            save=False,
            verbose=False,
        )

        result = predictions[0]

        valid_instance_masks = (
            self._extract_valid_instance_masks(
                result=result,
                image_shape=(height, width),
            )
        )

        combined_mask = combine_instance_masks(
            instance_masks=valid_instance_masks,
            image_shape=(height, width),
        )

        mask_area_fraction = calculate_mask_area_fraction(
            combined_mask
        )

        contours = extract_external_contours(
            binary_mask=combined_mask,
            minimum_area=(
                self.config.minimum_contour_area
            ),
        )

        contour_metrics = calculate_contour_metrics(
            contours
        )

        processing_time = (
            time.perf_counter() - start_time
        )

        raw_instance_count = 0

        if (
            result.masks is not None
            and result.masks.data is not None
        ):
            raw_instance_count = len(
                result.masks.data
            )

        valid_instance_count = len(
            valid_instance_masks
        )

        bubble_count = int(
            contour_metrics["bubble_count"]
        )

        if bubble_count == 0:
            status = "NO_DETECTIONS"
        else:
            status = "OK"

        if bubble_count > 0:
            instance_to_contour_ratio = (
                valid_instance_count / bubble_count
            )
        else:
            instance_to_contour_ratio = 0.0

        return {
            "filename": path.name,
            "image_path": str(path.resolve()),
            "status": status,
            "bubble_count": bubble_count,
            "mean_area_px2": float(
                contour_metrics["mean_area_px2"]
            ),
            "mean_equivalent_diameter_px": float(
                contour_metrics[
                    "mean_equivalent_diameter_px"
                ]
            ),
            "mean_circularity": float(
                contour_metrics["mean_circularity"]
            ),
            "median_equivalent_diameter_px": float(
                contour_metrics[
                    "median_equivalent_diameter_px"
                ]
            ),
            "std_equivalent_diameter_px": float(
                contour_metrics[
                    "std_equivalent_diameter_px"
                ]
            ),
            "ecd_p10_px": float(
                contour_metrics["ecd_p10_px"]
            ),
            "ecd_p90_px": float(
                contour_metrics["ecd_p90_px"]
            ),
            "mask_area_fraction": float(
                mask_area_fraction
            ),
            "yolo_raw_instance_count": int(
                raw_instance_count
            ),
            "yolo_valid_instance_count": int(
                valid_instance_count
            ),
            "instance_to_contour_ratio": float(
                instance_to_contour_ratio
            ),
            "processing_time_seconds": float(
                processing_time
            ),
            "confidence": self.config.confidence,
            "image_size": self.config.image_size,
            "max_detections": (
                self.config.max_detections
            ),
            "minimum_contour_area": (
                self.config.minimum_contour_area
            ),
        }