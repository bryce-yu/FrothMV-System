"""
Summarise the YOLO instance-count and combined-contour diagnostic CSV.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "results"
    / "yolo_diagnostics"
    / "instance_count_comparison.csv"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "results"
    / "yolo_diagnostics"
    / "highest_count_differences.csv"
)


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Diagnostic CSV not found: {INPUT_CSV}"
        )

    df = pd.read_csv(INPUT_CSV)

    print("\nDataset-level summary")
    print("-" * 50)

    print(f"Images analysed: {len(df)}")

    print(
        "Mean ground-truth count: "
        f"{df['ground_truth_contour_count'].mean():.3f}"
    )

    print(
        "Mean valid YOLO instance count: "
        f"{df['yolo_valid_instance_count'].mean():.3f}"
    )

    print(
        "Mean combined contour count: "
        f"{df['combined_contour_count'].mean():.3f}"
    )

    print(
        "\nYOLO instance-count MAE: "
        f"{df['absolute_gt_to_instance_error'].mean():.3f}"
    )

    print(
        "Combined contour-count MAE: "
        f"{df['absolute_gt_to_contour_error'].mean():.3f}"
    )

    print(
        "\nAverage instance-to-contour reduction: "
        f"{df['instance_to_contour_difference'].mean():.3f}"
    )

    affected = df["instance_to_contour_difference"] > 0

    print(
        "Images affected by mask merging: "
        f"{affected.sum()} of {len(df)}"
    )

    if affected.any():
        print(
            "Average reduction among affected images: "
            f"{df.loc[affected, 'instance_to_contour_difference'].mean():.3f}"
        )

    exact_matches = (
        df["yolo_valid_instance_count"]
        == df["combined_contour_count"]
    ).sum()

    print(
        "Images where instance and contour counts match: "
        f"{exact_matches} of {len(df)}"
    )

    # Rank images where combining masks caused the largest count loss.
    ranked_df = df.sort_values(
        by="instance_to_contour_difference",
        ascending=False,
    )

    ranked_df.to_csv(OUTPUT_CSV, index=False)

    print("\nLargest instance-to-contour reductions:")
    print(
        ranked_df[
            [
                "filename",
                "ground_truth_contour_count",
                "yolo_valid_instance_count",
                "combined_contour_count",
                "instance_to_contour_difference",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(f"\nRanked results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()