"""
Presentation-only viewer for the latest FrothMV segmentation result.
"""

from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PREVIEW_PATH = (
    PROJECT_ROOT
    / "results"
    / "live_preview"
    / "latest_segmentation.jpg"
)

WINDOW_NAME = "FrothMV Live Segmentation"


def main() -> None:
    last_modified_time = None

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL,
    )

    print(f"Watching: {PREVIEW_PATH}")
    print("Press Q or Escape in the preview window to close it.")

    try:
        while True:
            if PREVIEW_PATH.exists():
                modified_time = PREVIEW_PATH.stat().st_mtime_ns

                if modified_time != last_modified_time:
                    preview = cv2.imread(str(PREVIEW_PATH))

                    if preview is not None:
                        cv2.imshow(WINDOW_NAME, preview)
                        last_modified_time = modified_time

            key = cv2.waitKey(100) & 0xFF

            if key in (ord("q"), 27):
                break

    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()