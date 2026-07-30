from pathlib import Path
import argparse

import pandas as pd


METRIC_COLUMNS = [
    "bubble_count",
    "mean_area_pixels",
    "mean_equivalent_diameter_pixels",
    "mean_circularity",
]


def safe_percentage_error(
    predicted: pd.Series,
    ground_truth: pd.Series,
) -> pd.Series:
    """
    Calculate percentage error while avoiding division by zero.
    """

    percentage_error = pd.Series(
        float("nan"),
        index=ground_truth.index,
        dtype=float,
    )

    nonzero_mask = ground_truth != 0

    percentage_error.loc[nonzero_mask] = (
        (
            predicted.loc[nonzero_mask]
            - ground_truth.loc[nonzero_mask]
        ).abs()
        / ground_truth.loc[nonzero_mask].abs()
        * 100.0
    )

    return percentage_error


def compare_metrics(
    ground_truth_path: Path,
    predicted_path: Path,
    output_path: Path,
) -> None:
    """Compare ground-truth and predicted image-level metrics."""

    if not ground_truth_path.exists():
        raise FileNotFoundError(
            f"Ground-truth CSV not found: {ground_truth_path}"
        )

    if not predicted_path.exists():
        raise FileNotFoundError(
            f"Predicted CSV not found: {predicted_path}"
        )

    ground_truth = pd.read_csv(ground_truth_path)
    predicted = pd.read_csv(predicted_path)

    required_ground_truth = {
        "image_name",
        *METRIC_COLUMNS,
    }

    required_predicted = {
        "image_name",
        "predicted_instance_count",
        *METRIC_COLUMNS,
    }

    if not required_ground_truth.issubset(
        ground_truth.columns
    ):
        raise ValueError(
            "Ground-truth CSV is missing required columns."
        )

    if not required_predicted.issubset(
        predicted.columns
    ):
        raise ValueError(
            "Predicted CSV is missing required columns."
        )

    ground_truth_subset = ground_truth[
        ["image_name", *METRIC_COLUMNS]
    ].copy()

    predicted_subset = predicted[
        [
            "image_name",
            "predicted_instance_count",
            *METRIC_COLUMNS,
        ]
    ].copy()

    ground_truth_subset = ground_truth_subset.rename(
        columns={
            metric: f"ground_truth_{metric}"
            for metric in METRIC_COLUMNS
        }
    )

    predicted_subset = predicted_subset.rename(
        columns={
            metric: f"predicted_{metric}"
            for metric in METRIC_COLUMNS
        }
    )

    comparison = ground_truth_subset.merge(
        predicted_subset,
        on="image_name",
        how="inner",
        validate="one_to_one",
    )

    for metric in METRIC_COLUMNS:
        ground_truth_column = f"ground_truth_{metric}"
        predicted_column = f"predicted_{metric}"

        comparison[f"absolute_error_{metric}"] = (
            comparison[predicted_column]
            - comparison[ground_truth_column]
        ).abs()

        comparison[f"percentage_error_{metric}"] = (
            safe_percentage_error(
                predicted=comparison[predicted_column],
                ground_truth=comparison[
                    ground_truth_column
                ],
            )
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison.to_csv(
        output_path,
        index=False,
    )

    print(f"Ground-truth rows: {len(ground_truth)}")
    print(f"Predicted rows: {len(predicted)}")
    print(f"Matched rows: {len(comparison)}")
    print(f"Saved comparison: {output_path}")

    print("\nMean absolute errors:")

    for metric in METRIC_COLUMNS:
        column = f"absolute_error_{metric}"

        print(
            f"  {metric}: "
            f"{comparison[column].mean():.4f}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare predicted YOLO metrics against "
            "ground-truth mask metrics."
        )
    )

    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=(
            Path("results")
            / "mask_metrics"
            / "test_mask_summary.csv"
        ),
    )

    parser.add_argument(
        "--predicted",
        type=Path,
        default=(
            Path("results")
            / "yolo_evaluation"
            / "predicted_metrics.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path("results")
            / "yolo_evaluation"
            / "metric_comparison.csv"
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    compare_metrics(
        ground_truth_path=arguments.ground_truth,
        predicted_path=arguments.predicted,
        output_path=arguments.output,
    )


if __name__ == "__main__":
    main()