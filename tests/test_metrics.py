"""
Basic tests for FrothMV contour metric functions.
"""

import cv2
import numpy as np

from src.mv.metrics import (
    calculate_contour_metrics,
    combine_instance_masks,
    extract_external_contours,
)


def test_empty_mask_returns_zero_bubbles() -> None:
    mask = np.zeros(
        (100, 100),
        dtype=bool,
    )

    contours = extract_external_contours(
        mask,
        minimum_area=10,
    )

    metrics = calculate_contour_metrics(
        contours
    )

    assert metrics["bubble_count"] == 0
    assert metrics["mean_area_px2"] == 0.0
    assert (
        metrics[
            "mean_equivalent_diameter_px"
        ]
        == 0.0
    )
    assert metrics["mean_circularity"] == 0.0


def test_two_separate_circles_return_two_contours() -> None:
    mask = np.zeros(
        (200, 200),
        dtype=np.uint8,
    )

    cv2.circle(
        mask,
        (60, 100),
        20,
        1,
        thickness=-1,
    )

    cv2.circle(
        mask,
        (140, 100),
        20,
        1,
        thickness=-1,
    )

    contours = extract_external_contours(
        mask.astype(bool),
        minimum_area=10,
    )

    metrics = calculate_contour_metrics(
        contours
    )

    assert metrics["bubble_count"] == 2


def test_overlapping_instance_masks_combine() -> None:
    mask_1 = np.zeros(
        (100, 100),
        dtype=np.uint8,
    )

    mask_2 = np.zeros(
        (100, 100),
        dtype=np.uint8,
    )

    cv2.circle(
        mask_1,
        (45, 50),
        20,
        1,
        thickness=-1,
    )

    cv2.circle(
        mask_2,
        (55, 50),
        20,
        1,
        thickness=-1,
    )

    combined = combine_instance_masks(
        [
            mask_1.astype(bool),
            mask_2.astype(bool),
        ],
        image_shape=(100, 100),
    )

    contours = extract_external_contours(
        combined,
        minimum_area=10,
    )

    assert len(contours) == 1