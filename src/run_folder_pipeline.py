"""
Process all supported images in a folder using the consolidated
FrothMV pipeline and save the results to CSV and JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mv import FrothMVPipeline, MVConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process a folder of froth images using "
            "the consolidated MV pipeline."
        )
    )

    parser.add_argument(
        "input_folder",
        type=Path,
        help="Folder containing input images.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            PROJECT_ROOT
            / "results"
            / "pipeline_runs"
        ),
        help="Directory for CSV and JSON outputs.",
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "models" / "best.pt",
        help="Path to the YOLO model.",
    )

    return parser.parse_args()


def find_images(folder: Path) -> list[Path]:
    """
    Return supported image files in deterministic order.
    """
    if not folder.exists():
        raise FileNotFoundError(
            f"Input folder not found: {folder}"
        )

    if not folder.is_dir():
        raise NotADirectoryError(
            f"Input path is not a folder: {folder}"
        )

    return sorted(
        path
        for path in folder.iterdir()
        if (
            path.is_file()
            and path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )


def main() -> None:
    args = parse_arguments()

    image_paths = find_images(
        args.input_folder
    )

    if not image_paths:
        print(
            f"No supported images found in "
            f"{args.input_folder}"
        )
        return

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = MVConfig(
        model_path=args.model,
        confidence=0.15,
        image_size=640,
        max_detections=1000,
        minimum_contour_area=10.0,
    )

    pipeline = FrothMVPipeline(config)

    records: list[dict[str, object]] = []

    for index, image_path in enumerate(
        image_paths,
        start=1,
    ):
        try:
            metrics = pipeline.process_image(
                image_path
            )

            records.append(metrics)

            print(
                f"[{index}/{len(image_paths)}] "
                f"{image_path.name}: "
                f"count={metrics['bubble_count']}, "
                f"time="
                f"{metrics['processing_time_seconds']:.3f}s"
            )

        except Exception as error:
            records.append(
                {
                    "filename": image_path.name,
                    "image_path": str(
                        image_path.resolve()
                    ),
                    "status": "ERROR",
                    "error_message": str(error),
                }
            )

            print(
                f"[{index}/{len(image_paths)}] "
                f"ERROR: {image_path.name}: {error}"
            )

    csv_path = (
        args.output_dir
        / "pipeline_results.csv"
    )

    json_path = (
        args.output_dir
        / "pipeline_results.json"
    )

    results_df = pd.DataFrame(records)
    results_df.to_csv(
        csv_path,
        index=False,
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as json_file:
        json.dump(
            records,
            json_file,
            indent=4,
        )

    successful_records = [
        record
        for record in records
        if record.get("status") != "ERROR"
    ]

    if successful_records:
        average_time = sum(
            float(
                record[
                    "processing_time_seconds"
                ]
            )
            for record in successful_records
        ) / len(successful_records)

        print(
            "\nAverage processing time: "
            f"{average_time:.3f} seconds/image"
        )

    print(f"CSV saved to: {csv_path}")
    print(f"JSON saved to: {json_path}")


if __name__ == "__main__":
    main()