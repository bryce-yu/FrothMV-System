# Week 3 MV Diagnostics

## Day 1: YOLO Instance Count and Combined-Contour Count

### Purpose

The purpose of this analysis was to determine whether bubble-count underestimation was primarily caused by missed YOLO detections or by separate predicted instance masks becoming connected when combined into one binary mask.

### Configuration

- Model: `models/best.pt`
- Confidence threshold: 0.15
- Image size: 640
- Minimum area: 10 px²
- Test images: 40 fixed images from `test_reduced.csv`

### Results

- Mean ground-truth contour count: 334.950
- Mean YOLO valid instance count: 282.625
- Mean combined-mask contour count: 232.075
- YOLO instance-count MAE: 93.525
- Combined-contour-count MAE: 103.125
- Mean instance-to-contour reduction: 50.550
- Images affected by mask merging: 40 of 40

After updating max_det:
Mean ground-truth count: 334.950
Mean valid YOLO instance count: 461.575
Mean combined contour count: 309.325

YOLO instance-count MAE: 128.325
Combined contour-count MAE: 32.475

Average instance-to-contour reduction: 152.250
Images affected by mask merging: 40 of 40

### Initial conclusion

The initial diagnostic results indicate that bubble-count error is caused by a combination of missed or inaccurate YOLO instance detections and post-processing mask merging. The mean YOLO instance count was approximately 52 instances below the mean ground-truth contour count. Combining the predicted instance masks caused an additional average reduction of approximately 51 regions, and this reduction occurred across all 40 test images. Therefore, neither model detection nor combined-mask contour processing alone explains the final bubble-count underestimation. Although both stages contribute substantially, the YOLO instance-count MAE remains high, indicating that using instance count directly would reduce post-processing losses but would not completely resolve the bubble-count error.

### Representative observations

| Case | GT count | YOLO instances | Combined contours | Interpretation |
|---|---:|---:|---:|---|
| Dense failure 1 |  |  |  |  |
| Dense failure 2 |  |  |  |  |
| Dense failure 3 |  |  |  |  |
| Merging case 1 |  |  |  |  |
| Merging case 2 |  |  |  |  |
| Merging case 3 |  |  |  |  |
| Successful case 1 |  |  |  |  |
| Successful case 2 |  |  |  |  |

- Dense small-bubble case:
- Mask-merging case:
- Moderate or successful case:

### Next step

The next investigation will inspect the original masks, YOLO polygon labels and representation of dense small-bubble images in the reduced training subset.



## Rerun controlled inference experiments with raised max_det

Three configurations were evaluated on the same fixed 40-image test manifest at an inference image size of 640 pixels.

| Configuration | Confidence | Minimum area (px²) | Bubble-count MAE | Mean-area MAE | Diameter MAE | Circularity MAE |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 0.25 | 10 | 81.3750 | 69.6021 | 2.2856 | 0.0341 |
| Lower confidence | 0.15 | 10 | 32.4750 | 58.8184 | 2.2466 | 0.0172 |
| Smaller contour filter | 0.25 | 5 | 80.9000 | 69.3781 | 2.2667 | 0.0337 |

Interpretations previously made still hold, and lower confidence is still the preferred configuration. 

### Rerun processing time measurements

The selected configuration was timed over the fixed 40-image test subset with visualisation generation disabled.

- Hardware: CPU
- Images: 40
- Confidence threshold: 0.15
- Minimum contour area: 10 px²
- Inference image size: 640 pixels
- Total processing time: ~73.880 seconds (Run 1: 74.661s, Run 2: 73.098s)
- Average processing time: ~1.847 seconds per image (Run 1: 74.661/40=1.867s, Run 2: 73.098/40=1.827s)

This timing includes model inference, mask combination and metric extraction, but excludes visualisation generation.

### Highest-error images

#### Bubble-count percentage error

| Rank | Image | Percentage error | Visual observation |
|---:|---|---:|---|
| 1 | F5_1_1_2.ts-frames_frame-125.png | 34.434% | Dense small bubbles missed |
| 2 | F5_2_1_2.ts-frames_frame-440.png | 33.456% | Dense small bubbles missed |
| 3 | F5_1_1_1.ts-frames_frame-1575.png | 29.439% | Dense small bubbles missed |
| 4 | F5_2_2_1.ts-frames_frame-395.png | 27.748% | Dense small bubbles missed |
| 5 | F5_1_1_1.ts-frames_frame-1540.png | 27.203% | Dense small bubbles missed |

#### Mean-area percentage error

| Rank | Image | Percentage error | Visual observation |
|---:|---|---:|---|
| 1 | F5_1_1_2.ts-frames_frame-125.png | 132.514% | Merged neighbouring bubbles, one large incorrectly predicted contour |
| 2 | F5_1_1_1.ts-frames_frame-1540.png | 78.209% | Merged neighbouring bubbles, one unusual, moderate-sized predicted contour |
| 3 | F5_1_1_1.ts-frames_frame-1575.png | 56.248% | Merged neighbouring bubbles |
| 4 | F5_1_1_1.ts-frames_frame-1480.png | 55.045% | Merged neighbouring bubbles |
| 5 | F5_1_1_1.ts-frames_frame-1105.png | 52.280% | Merged neighbouring bubbles |