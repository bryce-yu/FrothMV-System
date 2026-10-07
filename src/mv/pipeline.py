"""
Reusable YOLO-based froth machine-vision pipeline.
"""

from __future__ import annotations

import time
import logging
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

logger = logging.getLogger(__name__)

class FrothMVPipeline:
    """
    Reusable machine-vision pipeline for froth bubble analysis.

    The YOLO model is loaded once when the pipeline object is created.
    """

    def __init__(
    self,
        config: MVConfig,
        enable_live_preview: bool = False,
        live_preview_path: str | Path = (
            "results/live_preview/latest_segmentation.jpg"
        ),
    ) -> None:
        config.validate()

        self.config = config
        self.model = YOLO(str(config.model_path))

        self.enable_live_preview = enable_live_preview
        self.live_preview_path = Path(live_preview_path)

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

    def _save_live_preview(
        self,
        image: np.ndarray,
        combined_mask: np.ndarray,
        contours: list[np.ndarray],
        metrics: dict[str, object],
    ) -> None:
        """
        Save a presentation-only preview of the latest valid result.
        """
        preview = image.copy()

        # Add a translucent orange segmentation overlay.
        colour_layer = preview.copy()
        colour_layer[combined_mask.astype(bool)] = (0, 165, 255)

        preview = cv2.addWeighted(
            preview,
            0.70,
            colour_layer,
            0.30,
            0.0,
        )

        # Draw the final contours used to calculate the metrics.
        cv2.drawContours(
            preview,
            contours,
            contourIdx=-1,
            color=(0, 255, 0),
            thickness=1,
        )

        text_lines = [
            "FrothMV Live Segmentation",
            f"Image: {metrics['filename']}",
            "Presentation-only display",
        ]

        line_height = 25
        panel_width = 440
        panel_height = 20 + (line_height * len(text_lines))

        image_height = preview.shape[0]
        panel_top = image_height - panel_height

        # Create a semi-transparent panel at the bottom left.
        panel_layer = preview.copy()

        cv2.rectangle(
            panel_layer,
            (0, panel_top),
            (panel_width, image_height),
            color=(0, 0, 0),
            thickness=-1,
        )

        preview = cv2.addWeighted(
            panel_layer,
            0.65,
            preview,
            0.35,
            0.0,
        )

        for line_number, text in enumerate(text_lines):
            cv2.putText(
                preview,
                text,
                (12, panel_top + 25 + line_number * line_height),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        self.live_preview_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Write to a temporary image before replacing the displayed file.
        temporary_path = self.live_preview_path.with_name(
            f"{self.live_preview_path.stem}"
            f".tmp{self.live_preview_path.suffix}"
        )

        write_successful = cv2.imwrite(
            str(temporary_path),
            preview,
        )

        if not write_successful:
            raise OSError(
                f"Could not write live preview: {temporary_path}"
            )

        temporary_path.replace(self.live_preview_path)

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

        if not path.is_file():
            raise ValueError(
                f"Image path is not a regular file: {path}"
            )

        allowed_extensions = {
            extension.lower()
            for extension in self.config.allowed_image_extensions
        }

        if path.suffix.lower() not in allowed_extensions:
            raise ValueError(
                f"Unsupported image extension '{path.suffix}': {path}"
            )

        file_size_bytes = path.stat().st_size

        if file_size_bytes == 0:
            raise ValueError(
                f"Image file is empty: {path}"
            )

        if file_size_bytes > self.config.max_image_file_size_bytes:
            raise ValueError(
                f"Image file exceeds the configured size limit "
                f"({file_size_bytes} > "
                f"{self.config.max_image_file_size_bytes} bytes): {path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"OpenCV could not decode image: {path}"
            )

        height, width = image.shape[:2]

        if (
            width != self.config.expected_image_width
            or height != self.config.expected_image_height
        ):
            raise ValueError(
                f"Unexpected image dimensions "
                f"{width}x{height}; expected "
                f"{self.config.expected_image_width}x"
                f"{self.config.expected_image_height}: {path}"
            )

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(
                f"Unexpected decoded image format; "
                f"expected a three-channel image: {path}"
            )

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

        metrics = {
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

        if self.enable_live_preview:
            try:
                self._save_live_preview(
                    image=image,
                    combined_mask=combined_mask,
                    contours=contours,
                    metrics=metrics,
                )
            except Exception as exc:
                logger.warning(
                    "Live preview could not be updated: %s",
                    exc,
                )

        return metrics