from pathlib import Path
import shutil
import cv2
import numpy as np

test_folder = Path("dataset/invalid_input_test_images")

valid_image = Path(
    "dataset/pipeline_validation_images/"
    "F5_1_1_1.ts-frames_frame-970.png"
)

test_folder.mkdir(parents=True, exist_ok=True)

# Valid images at the start and end.
shutil.copy2(valid_image, test_folder / "00_valid_start.png")
shutil.copy2(valid_image, test_folder / "05_valid_end.png")

# 1. Empty PNG: exactly zero bytes.
(test_folder / "01_empty.png").write_bytes(b"")

# 2. Corrupt PNG: non-empty, but not actual image data.
(test_folder / "02_corrupt.png").write_bytes(
    b"This is deliberately invalid PNG data."
)

# 3. Oversized PNG: random pixels prevent strong compression.
pixels = np.random.default_rng(42).integers(
    0, 256, size=(1024, 1024, 3), dtype=np.uint8
)
oversized_path = test_folder / "03_oversized.png"
if not cv2.imwrite(str(oversized_path), pixels):
    raise RuntimeError("Could not create oversized PNG")

assert oversized_path.stat().st_size > 2 * 1024 * 1024

# 4. Unsupported extension.
(test_folder / "04_unsupported.txt").write_text(
    "Unsupported input file for validation testing.",
    encoding="utf-8"
)

for path in sorted(test_folder.iterdir()):
    print(f"{path.name}: {path.stat().st_size:,} bytes")