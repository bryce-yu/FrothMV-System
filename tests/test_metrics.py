"""
Basic tests for FrothMV contour metric functions.
"""

import cv2
import numpy as np

from src.mv.metrics import (
    calculate_contour_metrics,
    calculate_mask_area_fraction,
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
    assert (
        metrics[
            "median_equivalent_diameter_px"
        ]
        == 0.0
    )
    assert (
        metrics[
            "std_equivalent_diameter_px"
        ]
        == 0.0
    )
    assert metrics["ecd_p10_px"] == 0.0
    assert metrics["ecd_p90_px"] == 0.0


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

    assert np.isclose(
        metrics[
            "std_equivalent_diameter_px"
        ],
        0.0,
    )

    assert np.isclose(
        metrics[
            "median_equivalent_diameter_px"
        ],
        metrics[
            "mean_equivalent_diameter_px"
        ],
    )


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


def test_ecd_distribution_metrics() -> None:
    mask = np.zeros(
        (300, 300),
        dtype=np.uint8,
    )

    cv2.circle(
        mask,
        (50, 150),
        10,
        1,
        thickness=-1,
    )

    cv2.circle(
        mask,
        (150, 150),
        20,
        1,
        thickness=-1,
    )

    cv2.circle(
        mask,
        (250, 150),
        30,
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

    expected_diameters = []

    for contour in contours:
        area = float(
            cv2.contourArea(contour)
        )

        diameter = 2.0 * np.sqrt(
            area / np.pi
        )

        expected_diameters.append(
            diameter
        )

    assert np.isclose(
        metrics[
            "median_equivalent_diameter_px"
        ],
        np.median(expected_diameters),
    )

    assert np.isclose(
        metrics[
            "std_equivalent_diameter_px"
        ],
        np.std(expected_diameters),
    )

    assert np.isclose(
        metrics["ecd_p10_px"],
        np.percentile(
            expected_diameters,
            10,
        ),
    )

    assert np.isclose(
        metrics["ecd_p90_px"],
        np.percentile(
            expected_diameters,
            90,
        ),
    )


def test_mask_area_fraction() -> None:
    mask = np.zeros(
        (10, 10),
        dtype=bool,
    )

    mask[:5, :] = True

    fraction = calculate_mask_area_fraction(
        mask
    )

    assert np.isclose(
        fraction,
        0.5,
    )


def test_empty_mask_area_fraction_is_zero() -> None:
    mask = np.zeros(
        (10, 10),
        dtype=bool,
    )

    fraction = calculate_mask_area_fraction(
        mask
    )

    assert fraction == 0.0