from pathlib import Path

import pandas as pd


OLD_RESULTS = Path(
    "results/yolo_experiments_v2/"
    "conf015_area10/predicted_metrics.csv"
)

NEW_RESULTS = Path(
    "results/soft_sensor_analysis/"
    "session2_validation/pipeline_features_40.csv"
)

OUTPUT_FILE = Path(
    "results/soft_sensor_analysis/"
    "session2_validation/regression_comparison.csv"
)


def main() -> None:
    old_df = pd.read_csv(OLD_RESULTS)
    new_df = pd.read_csv(NEW_RESULTS)

    # Select and rename the old Week 3/4 columns
    old_subset = old_df[
        [
            "image_name",
            "bubble_count",
            "mean_area_pixels",
            "mean_equivalent_diameter_pixels",
            "mean_circularity",
        ]
    ].copy()

    old_subset = old_subset.rename(
        columns={
            "image_name": "filename",
            "mean_area_pixels": "mean_area_px2",
            "mean_equivalent_diameter_pixels":
                "mean_equivalent_diameter_px",
        }
    )

    # Select the equivalent Week 5 columns
    new_subset = new_df[
        [
            "filename",
            "bubble_count",
            "mean_area_px2",
            "mean_equivalent_diameter_px",
            "mean_circularity",
        ]
    ].copy()

    # Match rows by filename
    comparison = old_subset.merge(
        new_subset,
        on="filename",
        suffixes=("_old", "_new"),
        validate="one_to_one",
    )

    metrics = [
        "bubble_count",
        "mean_area_px2",
        "mean_equivalent_diameter_px",
        "mean_circularity",
    ]

    # Calculate new - old for each metric
    for metric in metrics:
        comparison[f"{metric}_diff"] = (
            comparison[f"{metric}_new"]
            - comparison[f"{metric}_old"]
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Regression comparison saved to:\n"
        f"{OUTPUT_FILE}"
    )

    print(
        f"\nImages matched: {len(comparison)}"
    )

    print("\nMaximum absolute differences:")

    for metric in metrics:
        diff_column = f"{metric}_diff"

        max_difference = comparison[
            diff_column
        ].abs().max()

        print(
            f"{metric}: {max_difference}"
        )


if __name__ == "__main__":
    main()