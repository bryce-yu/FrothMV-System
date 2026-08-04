"""
Configuration definitions for the FrothMV machine-vision pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MVConfig:
    """
    Configuration for YOLO inference and contour-based metric extraction.
    """

    model_path: Path
    confidence: float = 0.15
    image_size: int = 640
    max_detections: int = 1000
    minimum_contour_area: float = 10.0

    def validate(self) -> None:
        """
        Validate the configuration before the pipeline is used.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found: {self.model_path}"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Confidence threshold must be between 0 and 1."
            )

        if self.image_size <= 0:
            raise ValueError(
                "Image size must be greater than zero."
            )

        if self.max_detections <= 0:
            raise ValueError(
                "Maximum detections must be greater than zero."
            )

        if self.minimum_contour_area < 0:
            raise ValueError(
                "Minimum contour area cannot be negative."
            )