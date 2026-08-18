"""
Week 5 - Session 3
Soft-sensor feature analysis and interpretation.

This script analyses the 40-image Week 5 validation dataset.
It does NOT rerun YOLO or modify the MV pipeline.

Outputs:
- descriptive statistics
- feature variability
- Pearson/Spearman correlations
- mean-vs-median ECD comparison
- exploratory mask-occupancy grouping
- representative-image selections
- plots
- text summary
"""

from pathlib import Path
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "results"
    / "soft_sensor_analysis"
    / "session2_validation"
    / "pipeline_features_40.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "soft_sensor_analysis"
    / "session3_analysis"
)

PLOT_DIR = OUTPUT_DIR / "plots"
REP_IMAGE_DIR = OUTPUT_DIR / "representative_images"

# Folder containing the 40 regression/validation images.
# Change only if your existing folder is elsewhere.
IMAGE_SOURCE_DIR = PROJECT_ROOT / "dataset" / "pipeline_validation_images"


# ============================================================
# Feature definitions
# ============================================================

FEATURES = [
    "bubble_count",
    "mean_area_px2",
    "mean_equivalent_diameter_px",
    "median_equivalent_diameter_px",
    "std_equivalent_diameter_px",
    "ecd_p10_px",
    "ecd_p90_px",
    "mean_circularity",
    "mask_area_fraction",
]

# Diagnostics are analysed only if present.
OPTIONAL_DIAGNOSTICS = [
    "yolo_raw_instance_count",
    "yolo_valid_instance_count",
    "instance_to_contour_ratio",
    "processing_time_s",
]


# ============================================================
# Utility functions
# ============================================================

def find_filename_column(df):
    """
    Try several likely column names for the image filename.
    """
    candidates = [
        "filename",
        "image_name",
        "image",
        "file_name",
        "image_path",
        "path",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    return None


def save_histogram(series, title, xlabel, output_path):
    """
    Save a simple histogram.
    """
    clean = series.dropna()

    plt.figure(figsize=(7, 5))
    plt.hist(clean, bins=10, edgecolor="black")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Number of images")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_scatter(x, y, xlabel, ylabel, title, output_path):
    """
    Save scatter plot.
    """
    plt.figure(figsize=(6, 5))
    plt.scatter(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_correlation_heatmap(corr, title, output_path):
    """
    Save correlation matrix without requiring seaborn.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(
        corr.values,
        vmin=-1,
        vmax=1,
        cmap="coolwarm",
    )

    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90)

    ax.set_yticks(range(len(corr.index)))
    ax.set_yticklabels(corr.index)

    ax.set_title(title)

    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(
                j,
                i,
                f"{corr.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
            )

    fig.colorbar(image, ax=ax, label="Correlation coefficient")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def select_min(df, feature):
    return df.loc[df[feature].idxmin()]


def select_max(df, feature):
    return df.loc[df[feature].idxmax()]


def select_nearest_to_median(df, feature):
    target = df[feature].median()
    index = (df[feature] - target).abs().idxmin()
    return df.loc[index]


def copy_representative_image(filename, destination_name):
    """
    Find an image by basename inside IMAGE_SOURCE_DIR and copy it.
    """
    if not IMAGE_SOURCE_DIR.exists():
        return False

    filename = Path(str(filename)).name

    matches = list(IMAGE_SOURCE_DIR.rglob(filename))

    if not matches:
        return False

    destination = REP_IMAGE_DIR / destination_name
    shutil.copy2(matches[0], destination)

    return True


# ============================================================
# Main analysis
# ============================================================

def main():

    print("\nWeek 5 - Session 3 Soft-Sensor Analysis")
    print("=" * 50)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    REP_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 1. Load data
    # --------------------------------------------------------

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Input CSV not found:\n{INPUT_CSV}"
        )

    df = pd.read_csv(INPUT_CSV)

    print(f"\nLoaded: {INPUT_CSV}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # Check required features
    missing_features = [
        feature for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            "Missing required features:\n"
            + "\n".join(missing_features)
        )

    filename_col = find_filename_column(df)

    if filename_col:
        print(f"Filename column: {filename_col}")
    else:
        print(
            "WARNING: Could not automatically identify filename column.\n"
            "Representative statistics will still be generated, "
            "but image copying will be skipped."
        )

    # --------------------------------------------------------
    # 2. Descriptive statistics
    # --------------------------------------------------------

    stats = df[FEATURES].describe().T

    stats["range"] = stats["max"] - stats["min"]
    stats["iqr"] = stats["75%"] - stats["25%"]

    stats.to_csv(
        OUTPUT_DIR / "descriptive_statistics.csv"
    )

    print("\nDescriptive statistics:")
    print(
        stats[
            ["mean", "std", "min", "25%", "50%", "75%", "max"]
        ].round(4)
    )

    # --------------------------------------------------------
    # 3. Across-image feature variability
    # --------------------------------------------------------

    variability_rows = []

    for feature in FEATURES:

        mean_value = df[feature].mean()
        std_value = df[feature].std()

        if mean_value != 0:
            cv = std_value / abs(mean_value)
        else:
            cv = np.nan

        variability_rows.append(
            {
                "feature": feature,
                "mean": mean_value,
                "std": std_value,
                "coefficient_of_variation": cv,
                "min": df[feature].min(),
                "max": df[feature].max(),
                "range": (
                    df[feature].max()
                    - df[feature].min()
                ),
            }
        )

    variability_df = pd.DataFrame(variability_rows)

    variability_df.to_csv(
        OUTPUT_DIR / "feature_variability.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 4. Feature distributions
    # --------------------------------------------------------

    for feature in FEATURES:

        save_histogram(
            df[feature],
            title=f"Distribution of {feature}",
            xlabel=feature,
            output_path=PLOT_DIR / f"hist_{feature}.png",
        )

    # --------------------------------------------------------
    # 5. Correlation analysis
    # --------------------------------------------------------

    correlation_features = FEATURES.copy()

    for diagnostic in OPTIONAL_DIAGNOSTICS:
        if diagnostic in df.columns:
            correlation_features.append(diagnostic)

    pearson_corr = df[correlation_features].corr(
        method="pearson"
    )

    spearman_corr = df[correlation_features].corr(
        method="spearman"
    )

    pearson_corr.to_csv(
        OUTPUT_DIR / "pearson_correlation.csv"
    )

    spearman_corr.to_csv(
        OUTPUT_DIR / "spearman_correlation.csv"
    )

    save_correlation_heatmap(
        pearson_corr,
        "Pearson Correlation - Soft-Sensor Features",
        PLOT_DIR / "pearson_correlation_heatmap.png",
    )

    save_correlation_heatmap(
        spearman_corr,
        "Spearman Correlation - Soft-Sensor Features",
        PLOT_DIR / "spearman_correlation_heatmap.png",
    )

    # --------------------------------------------------------
    # 6. Mean area vs mean ECD
    # --------------------------------------------------------

    save_scatter(
        df["mean_area_px2"],
        df["mean_equivalent_diameter_px"],
        xlabel="Mean Area (px²)",
        ylabel="Mean ECD (px)",
        title="Mean Bubble Area vs Mean ECD",
        output_path=PLOT_DIR / "mean_area_vs_mean_ecd.png",
    )

    area_ecd_pearson = df[
        ["mean_area_px2", "mean_equivalent_diameter_px"]
    ].corr(method="pearson").iloc[0, 1]

    area_ecd_spearman = df[
        ["mean_area_px2", "mean_equivalent_diameter_px"]
    ].corr(method="spearman").iloc[0, 1]

    # Equivalent diameter corresponding to the MEAN AREA.
    # This is intentionally diagnostic only.
    df["ecd_from_mean_area_px"] = np.sqrt(
        4 * df["mean_area_px2"] / np.pi
    )

    df["mean_ecd_minus_ecd_from_mean_area"] = (
        df["mean_equivalent_diameter_px"]
        - df["ecd_from_mean_area_px"]
    )

    # --------------------------------------------------------
    # 7. Mean ECD vs median ECD
    # --------------------------------------------------------

    df["mean_minus_median_ecd_px"] = (
        df["mean_equivalent_diameter_px"]
        - df["median_equivalent_diameter_px"]
    )

    df["mean_median_difference_percent"] = np.where(
        df["median_equivalent_diameter_px"] != 0,
        (
            df["mean_minus_median_ecd_px"]
            / df["median_equivalent_diameter_px"]
        ) * 100,
        np.nan,
    )

    mean_median_columns = []

    if filename_col:
        mean_median_columns.append(filename_col)

    mean_median_columns += [
        "mean_equivalent_diameter_px",
        "median_equivalent_diameter_px",
        "mean_minus_median_ecd_px",
        "mean_median_difference_percent",
        "std_equivalent_diameter_px",
        "ecd_p10_px",
        "ecd_p90_px",
    ]

    df[mean_median_columns].to_csv(
        OUTPUT_DIR / "mean_vs_median_ecd.csv",
        index=False,
    )

    save_scatter(
        df["median_equivalent_diameter_px"],
        df["mean_equivalent_diameter_px"],
        xlabel="Median ECD (px)",
        ylabel="Mean ECD (px)",
        title="Mean ECD vs Median ECD",
        output_path=PLOT_DIR / "mean_vs_median_ecd.png",
    )

    # --------------------------------------------------------
    # 8. Distribution-width analysis
    # --------------------------------------------------------

    df["ecd_p90_p10_range_px"] = (
        df["ecd_p90_px"]
        - df["ecd_p10_px"]
    )

    save_scatter(
        df["std_equivalent_diameter_px"],
        df["ecd_p90_p10_range_px"],
        xlabel="ECD Standard Deviation (px)",
        ylabel="P90 - P10 ECD Range (px)",
        title="Two Measures of Bubble-Size Distribution Width",
        output_path=PLOT_DIR / "std_vs_p90_p10_range.png",
    )

    # --------------------------------------------------------
    # 9. Count / occupancy relationships
    # --------------------------------------------------------

    save_scatter(
        df["bubble_count"],
        df["mask_area_fraction"],
        xlabel="Bubble Count",
        ylabel="Mask Area Fraction",
        title="Bubble Count vs Mask Area Fraction",
        output_path=PLOT_DIR / "count_vs_mask_fraction.png",
    )

    save_scatter(
        df["bubble_count"],
        df["median_equivalent_diameter_px"],
        xlabel="Bubble Count",
        ylabel="Median ECD (px)",
        title="Bubble Count vs Median Bubble Size",
        output_path=PLOT_DIR / "count_vs_median_ecd.png",
    )

    save_scatter(
        df["mask_area_fraction"],
        df["median_equivalent_diameter_px"],
        xlabel="Mask Area Fraction",
        ylabel="Median ECD (px)",
        title="Mask Area Fraction vs Median ECD",
        output_path=PLOT_DIR / "mask_fraction_vs_median_ecd.png",
    )

    # --------------------------------------------------------
    # 10. Exploratory mask-occupancy groups
    # --------------------------------------------------------

    try:
        df["mask_occupancy_group"] = pd.qcut(
            df["mask_area_fraction"],
            q=3,
            labels=["Low", "Medium", "High"],
            duplicates="drop",
        )

        occupancy_summary = (
            df.groupby(
                "mask_occupancy_group",
                observed=True,
            )[
                [
                    "bubble_count",
                    "mean_equivalent_diameter_px",
                    "median_equivalent_diameter_px",
                    "std_equivalent_diameter_px",
                    "ecd_p10_px",
                    "ecd_p90_px",
                    "mean_circularity",
                    "mask_area_fraction",
                ]
            ]
            .agg(["mean", "median", "std"])
        )

        occupancy_summary.to_csv(
            OUTPUT_DIR / "occupancy_group_summary.csv"
        )

    except ValueError as error:
        print(
            "\nCould not create occupancy groups:",
            error,
        )

    # --------------------------------------------------------
    # 11. Representative images
    # --------------------------------------------------------

    representative_specs = [
        (
            "small_bubbles",
            select_min(df, "median_equivalent_diameter_px"),
        ),
        (
            "typical_bubbles",
            select_nearest_to_median(
                df,
                "median_equivalent_diameter_px",
            ),
        ),
        (
            "large_bubbles",
            select_max(df, "median_equivalent_diameter_px"),
        ),
        (
            "narrow_distribution",
            select_min(df, "std_equivalent_diameter_px"),
        ),
        (
            "broad_distribution",
            select_max(df, "std_equivalent_diameter_px"),
        ),
        (
            "low_mask_fraction",
            select_min(df, "mask_area_fraction"),
        ),
        (
            "high_mask_fraction",
            select_max(df, "mask_area_fraction"),
        ),
        (
            "low_bubble_count",
            select_min(df, "bubble_count"),
        ),
        (
            "high_bubble_count",
            select_max(df, "bubble_count"),
        ),
    ]

    representative_rows = []

    for role, row in representative_specs:

        result = {
            "representative_role": role,
        }

        if filename_col:
            result["filename"] = row[filename_col]

        for feature in FEATURES:
            result[feature] = row[feature]

        representative_rows.append(result)

        if filename_col:

            source_filename = Path(
                str(row[filename_col])
            ).name

            suffix = Path(source_filename).suffix

            destination_name = (
                f"{role}{suffix}"
            )

            copied = copy_representative_image(
                source_filename,
                destination_name,
            )

            if not copied:
                print(
                    f"Could not copy representative image: "
                    f"{source_filename}"
                )

    representatives_df = pd.DataFrame(
        representative_rows
    )

    representatives_df.to_csv(
        OUTPUT_DIR / "representative_images.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 12. Save enriched analysis table
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_DIR / "session3_enriched_features.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 13. Key numerical relationships
    # --------------------------------------------------------

    count_median_corr = df[
        ["bubble_count", "median_equivalent_diameter_px"]
    ].corr(method="spearman").iloc[0, 1]

    count_mask_corr = df[
        ["bubble_count", "mask_area_fraction"]
    ].corr(method="spearman").iloc[0, 1]

    std_range_corr = df[
        [
            "std_equivalent_diameter_px",
            "ecd_p90_p10_range_px",
        ]
    ].corr(method="spearman").iloc[0, 1]

    mean_median_corr = df[
        [
            "mean_equivalent_diameter_px",
            "median_equivalent_diameter_px",
        ]
    ].corr(method="spearman").iloc[0, 1]

    # --------------------------------------------------------
    # 14. Write summary
    # --------------------------------------------------------

    summary_lines = [
        "Week 5 - Session 3 Soft-Sensor Feature Analysis",
        "=" * 55,
        "",
        f"Images analysed: {len(df)}",
        "",
        "Key correlations",
        "----------------",
        (
            "Mean area vs mean ECD Pearson: "
            f"{area_ecd_pearson:.4f}"
        ),
        (
            "Mean area vs mean ECD Spearman: "
            f"{area_ecd_spearman:.4f}"
        ),
        (
            "Mean ECD vs median ECD Spearman: "
            f"{mean_median_corr:.4f}"
        ),
        (
            "Std ECD vs P90-P10 range Spearman: "
            f"{std_range_corr:.4f}"
        ),
        (
            "Bubble count vs median ECD Spearman: "
            f"{count_median_corr:.4f}"
        ),
        (
            "Bubble count vs mask area fraction Spearman: "
            f"{count_mask_corr:.4f}"
        ),
        "",
        "Mean-vs-median ECD",
        "------------------",
        (
            "Mean absolute mean-minus-median difference: "
            f"{df['mean_minus_median_ecd_px'].abs().mean():.4f} px"
        ),
        (
            "Median mean-minus-median difference: "
            f"{df['mean_minus_median_ecd_px'].median():.4f} px"
        ),
        "",
        "Important interpretation notes",
        "------------------------------",
        (
            "- Correlation does not by itself prove that one feature "
            "should be removed."
        ),
        (
            "- Mean area and mean ECD are mathematically related but "
            "are not identical summaries because ECD is calculated "
            "per contour before averaging."
        ),
        (
            "- Std ECD and P90-P10 both describe distribution width. "
            "Strong correlation may indicate redundancy."
        ),
        (
            "- Mask area fraction is predicted mask occupancy of the "
            "whole image, not a direct measurement of visible froth "
            "surface or physical froth coverage."
        ),
        (
            "- Low/medium/high mask-occupancy comparisons are "
            "exploratory only and should not be interpreted as "
            "ground-truth visibility categories."
        ),
    ]

    summary_path = OUTPUT_DIR / "session3_summary.txt"

    summary_path.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print("\n" + "\n".join(summary_lines))

    print("\nAnalysis complete.")
    print(f"Results saved to:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()