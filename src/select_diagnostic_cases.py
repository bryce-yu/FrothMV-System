"""
Select representative images for detailed YOLO instance-mask inspection.
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
    / "selected_diagnostic_cases.csv"
)


def add_case(
    selected_records: list[dict],
    row: pd.Series,
    category: str,
) -> None:
    """Add a case unless the image has already been selected."""
    filename = row["filename"]

    existing_filenames = {
        record["filename"] for record in selected_records
    }

    if filename in existing_filenames:
        return

    record = row.to_dict()
    record["diagnostic_category"] = category
    selected_records.append(record)


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Diagnostic CSV not found: {INPUT_CSV}"
        )

    df = pd.read_csv(INPUT_CSV)

    selected_records: list[dict] = []

    # Largest reduction between YOLO instances and combined contours.
    largest_reductions = df.sort_values(
        "instance_to_contour_difference",
        ascending=False,
    )

    for _, row in largest_reductions.head(2).iterrows():
        add_case(
            selected_records,
            row,
            "largest_instance_to_contour_reduction",
        )

    # Largest final combined-contour count errors.
    largest_final_errors = df.sort_values(
        "absolute_gt_to_contour_error",
        ascending=False,
    )

    for _, row in largest_final_errors.iterrows():
        add_case(
            selected_records,
            row,
            "largest_combined_contour_error",
        )

        if sum(
            record["diagnostic_category"]
            == "largest_combined_contour_error"
            for record in selected_records
        ) >= 2:
            break

    # Best-performing final combined-contour cases.
    best_cases = df.sort_values(
        "absolute_gt_to_contour_error",
        ascending=True,
    )

    for _, row in best_cases.iterrows():
        add_case(
            selected_records,
            row,
            "low_combined_contour_error",
        )

        if sum(
            record["diagnostic_category"]
            == "low_combined_contour_error"
            for record in selected_records
        ) >= 2:
            break

    selected_df = pd.DataFrame(selected_records)
    selected_df.to_csv(OUTPUT_CSV, index=False)

    display_columns = [
        "diagnostic_category",
        "filename",
        "ground_truth_contour_count",
        "yolo_valid_instance_count",
        "combined_contour_count",
        "instance_to_contour_difference",
        "absolute_gt_to_contour_error",
    ]

    print("\nSelected diagnostic cases:")
    print(
        selected_df[display_columns].to_string(index=False)
    )

    print(f"\nSaved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()