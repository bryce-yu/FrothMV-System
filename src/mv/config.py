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

    # Input-integrity restrictions for the current dataset.
    allowed_image_extensions: tuple[str, ...] = (".png",)
    max_image_file_size_bytes: int = 2 * 1024 * 1024
    expected_image_width: int = 800
    expected_image_height: int = 600

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


        if not self.allowed_image_extensions:
            raise ValueError(
                "At least one image extension must be permitted."
            )

        if any(
            not extension.startswith(".")
            for extension in self.allowed_image_extensions
        ):
            raise ValueError(
                "Permitted image extensions must begin with '.'."
            )

        if self.max_image_file_size_bytes <= 0:
            raise ValueError(
                "Maximum image file size must be greater than zero."
            )

        if self.expected_image_width <= 0:
            raise ValueError(
                "Expected image width must be greater than zero."
            )

        if self.expected_image_height <= 0:
            raise ValueError(
                "Expected image height must be greater than zero."
            )