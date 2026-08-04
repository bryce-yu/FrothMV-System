"""
Run the consolidated FrothMV pipeline on one image.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mv import FrothMVPipeline, MVConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process one froth image using the "
            "consolidated MV pipeline."
        )
    )

    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the input image.",
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "models" / "best.pt",
        help="Path to the YOLO model.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    config = MVConfig(
        model_path=args.model,
        confidence=0.15,
        image_size=640,
        max_detections=1000,
        minimum_contour_area=10.0,
    )

    pipeline = FrothMVPipeline(config)

    metrics = pipeline.process_image(
        args.image_path
    )

    print(
        json.dumps(
            metrics,
            indent=4,
        )
    )


if __name__ == "__main__":
    main()