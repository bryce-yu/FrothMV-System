"""
Contour extraction and bubble-metric calculations for FrothMV.
"""

from __future__ import annotations

import cv2
import numpy as np


def combine_instance_masks(
    instance_masks: list[np.ndarray],
    image_shape: tuple[int, int],
) -> np.ndarray:
    """
    Combine multiple binary instance masks into one binary mask.

    Parameters
    ----------
    instance_masks:
        List of Boolean masks at the original image resolution.

    image_shape:
        Image shape as (height, width).

    Returns
    -------
    np.ndarray
        Combined Boolean mask.
    """
    if not instance_masks:
        return np.zeros(image_shape, dtype=bool)

    return np.logical_or.reduce(instance_masks)


def extract_external_contours(
    binary_mask: np.ndarray,
    minimum_area: float,
) -> list[np.ndarray]:
    """
    Extract valid external contours from a binary mask.
    """
    mask_uint8 = binary_mask.astype(np.uint8) * 255

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


def calculate_contour_metrics(
    contours: list[np.ndarray],
) -> dict[str, float | int]:
    """
    Calculate aggregate bubble metrics from valid contours.

    Returned values:
    - bubble_count
    - mean_area_px2
    - mean_equivalent_diameter_px
    - mean_circularity
    """
    if not contours:
        return {
            "bubble_count": 0,
            "mean_area_px2": 0.0,
            "mean_equivalent_diameter_px": 0.0,
            "mean_circularity": 0.0,
        }

    areas: list[float] = []
    diameters: list[float] = []
    circularities: list[float] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))

        equivalent_diameter = 2.0 * np.sqrt(area / np.pi)

        if perimeter > 0:
            circularity = (
                4.0 * np.pi * area
            ) / (perimeter ** 2)
        else:
            circularity = 0.0

        areas.append(area)
        diameters.append(float(equivalent_diameter))
        circularities.append(float(circularity))

    return {
        "bubble_count": len(contours),
        "mean_area_px2": float(np.mean(areas)),
        "mean_equivalent_diameter_px": float(
            np.mean(diameters)
        ),
        "mean_circularity": float(
            np.mean(circularities)
        ),
    }