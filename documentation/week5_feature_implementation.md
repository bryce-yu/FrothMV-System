# Week 5 – Session 2 Soft-Sensor Feature Implementation and Validation

## 1. Session Objective

The objective of Session 2 was to implement the soft-sensor features defined during Session 1, validate them through unit and pipeline testing, and confirm that the previously validated Week 4 MV metrics remained materially unchanged.

The implementation focused only on the Python MV pipeline. OPC-UA, EAE supervisory logic, and HMI functionality were intentionally left unchanged during this session.

---

## 2. Implemented Features

The existing contour-processing method and frozen YOLO configuration were retained.

The following new contour-derived features were added to `calculate_contour_metrics()`:

* `median_equivalent_diameter_px`
* `std_equivalent_diameter_px`
* `ecd_p10_px`
* `ecd_p90_px`

These values are calculated using the existing per-contour `diameters` list.

The existing metrics remain:

* `bubble_count`
* `mean_area_px2`
* `mean_equivalent_diameter_px`
* `mean_circularity`

A new mask-level feature was also added:

* `mask_area_fraction`

This is calculated from the combined Boolean segmentation mask as:

[
\text{Mask Area Fraction}
=========================

\frac{\text{Number of non-zero mask pixels}}
{\text{Total image pixels}}
]

The feature therefore represents the fraction of the complete image occupied by the combined predicted segmentation mask.

---

## 3. Pipeline Integration

`pipeline.py` was updated so that the processing flow is now:

```text
YOLO instance masks
        ↓
Valid instance masks
        ↓
Combined binary mask
        ├──→ mask_area_fraction
        │
        ↓
External contours
        ↓
Contour metrics
        ├── mean ECD
        ├── median ECD
        ├── ECD standard deviation
        ├── ECD P10
        ├── ECD P90
        └── mean circularity
        ↓
Structured pipeline result
```

The new features are returned through the existing `FrothMVPipeline.process_image()` result dictionary.

No changes were made to:

* YOLO model selection;
* confidence threshold;
* image size;
* maximum detections;
* minimum contour area;
* contour extraction method;
* existing metric definitions.

---

## 4. Unit Testing

The existing metric test suite was extended from 3 tests to 6 tests.

Command:

```bash
python -m pytest -v
```

Environment:

* Python 3.12.7
* `pytest 9.1.1`
* `FrothMV-venv`

### Test Result

All 6 tests passed:

```text
test_empty_mask_returns_zero_bubbles            PASSED
test_two_separate_circles_return_two_contours   PASSED
test_overlapping_instance_masks_combine         PASSED
test_ecd_distribution_metrics                   PASSED
test_mask_area_fraction                         PASSED
test_empty_mask_area_fraction_is_zero            PASSED
```

### Validation Coverage

The tests confirm:

* empty contour inputs return zero-valued metrics;
* two separate circles are correctly identified as two contours;
* overlapping instance masks combine into one external contour;
* median ECD, ECD standard deviation, P10, and P90 are calculated correctly;
* known masks return the expected mask-area fraction;
* an empty mask returns a mask-area fraction of `0.0`.

Conclusion:

> The new soft-sensor feature calculations are deterministic and operate correctly under the tested synthetic cases.

---

## 5. Single-Image Validation

A previously used validation image was processed:

```text
F5_1_2_1.ts-frames_frame-1785.png
```

### Result

```text
bubble_count                         = 239
mean_area_px2                        = 420.22175732217573
mean_equivalent_diameter_px          = 19.534412863468827
mean_circularity                     = 0.6695332942693857

median_equivalent_diameter_px        = 16.017420774398584
std_equivalent_diameter_px           = 12.38748049686621
ecd_p10_px                           = 10.31094088749354
ecd_p90_px                           = 30.891458203286454
mask_area_fraction                   = 0.22783125

yolo_raw_instance_count              = 361
yolo_valid_instance_count            = 361
instance_to_contour_ratio            = 1.5104602510460252
processing_time_seconds              = 5.928977900010068
```

The first execution showed a relatively high processing time, consistent with previous warm-up behaviour.

### Feature Sanity Check

For this image:

[
P10 < Median < P90
]

with:

```text
P10    = 10.31 px
Median = 16.02 px
P90    = 30.89 px
```

The ECD standard deviation was positive:

```text
12.39 px
```

indicating a relatively broad detected bubble-size distribution.

The mask-area fraction was:

```text
0.22783125
≈ 22.78%
```

Visual inspection of the combined predicted mask showed that the segmented regions occupied approximately a minority of the total image area, making this result qualitatively consistent with the visualisation.

The value should be interpreted only as predicted mask occupancy of the complete image, not as total physical froth-surface coverage.

---

## 6. Five-Image Pipeline Test

The existing five-image pipeline test was rerun.

Results:

```text
[1/5] F5_1_2_1.ts-frames_frame-1785.png
count = 239
time  = 4.121 s

[2/5] F5_1_2_1.ts-frames_frame-380.png
count = 292
time  = 2.091 s

[3/5] F5_2_1_2.ts-frames_frame-415.png
count = 167
time  = 1.401 s

[4/5] F5_2_1_2.ts-frames_frame-440.png
count = 181
time  = 1.270 s

[5/5] F5_2_2_2.ts-frames_frame-1110.png
count = 579
time  = 4.034 s
```

Average processing time:

```text
2.583 s/image
```

CSV and JSON outputs were generated successfully.

The run confirmed that:

* all five images processed successfully;
* the new soft-sensor fields were included in the normal pipeline output;
* no NaN or missing feature values were observed;
* the existing bubble-count behaviour remained consistent.

---

## 7. Forty-Image Performance Validation

Two new 40-image timing runs were completed.

Results:

```text
Run 1: 2.305 s/image
Run 2: 2.175 s/image
Mean:  ~2.240 s/image
```

Previous reference values:

```text
Week 4: ~1.916 s/image
Week 3: ~1.847 s/image
```

The Week 5 extended feature pipeline therefore showed a modest increase in measured average execution time relative to the previous validation runs.

However, the new statistical calculations themselves are computationally lightweight compared with YOLO inference. The measured difference may therefore also reflect normal run-to-run variation, image-density effects, system load, or inference timing variation.

At this stage, no optimisation changes are required because the processing time remains appropriate for the current supervisory soft-sensor scope.

---

## 8. Forty-Image Regression Validation

The new Week 5 results were compared against the previously validated Week 3/4 result set for the same 40 images.

All 40 filenames matched successfully.

### Maximum Absolute Differences

```text
bubble_count:
0

mean_area_px2:
0.03482587064672771

mean_equivalent_diameter_px:
0.002478585761988228

mean_circularity:
0.00023708057765658985
```

### Interpretation

Bubble count was identical across all 40 images.

The remaining metrics showed only negligible numerical differences:

* maximum mean-area difference: approximately `0.0348 px²`;
* maximum mean-ECD difference: approximately `0.00248 px`;
* maximum mean-circularity difference: approximately `0.000237`.

These differences are sufficiently small to indicate that the Session 2 feature additions did not materially alter the previously validated Week 4 MV measurement method.

The new feature calculations can therefore be considered additive rather than a modification of the established segmentation and contour-processing baseline.

---

## 9. Session 2 Outputs

Validation outputs were stored under the Week 5 soft-sensor analysis results.

Recommended structure:

```text
results/
└── soft_sensor_analysis/
    └── session2_validation/
        ├── pipeline_features_40.csv
        └── regression_comparison.csv
```

`pipeline_features_40.csv` contains the expanded Week 5 feature set for each validation image.

`regression_comparison.csv` provides a reproducible comparison between the existing Week 3/4 metrics and the Week 5 implementation.

---

## 10. Session 2 Outcome

Session 2 successfully extended the validated FrothMV pipeline with additional froth-morphology descriptors.

The implemented soft-sensor feature set now includes:

### Bubble Population

* `bubble_count`

### Bubble Size

* `mean_area_px2`
* `mean_equivalent_diameter_px`
* `median_equivalent_diameter_px`

### Bubble-Size Distribution

* `std_equivalent_diameter_px`
* `ecd_p10_px`
* `ecd_p90_px`

### Bubble Shape

* `mean_circularity`

### Mask-Level Occupancy

* `mask_area_fraction`

The new features passed all unit tests and operated successfully on individual images, the five-image pipeline test, and the established 40-image validation set.

Regression validation confirmed that the original Week 4 measurements remained materially unchanged.

---

## 11. Next Step – Session 3

Session 3 should shift from implementation to **feature analysis and interpretation**.

The main tasks should include:

* analysing distributions of the new features across the validation dataset;
* calculating correlations between existing and new features;
* investigating potential redundancy between mean area and mean ECD;
* comparing mean ECD with median ECD;
* examining bubble-size spread using ECD standard deviation and P10/P90;
* comparing `mask_area_fraction` across representative images;
* assessing whether some features appear more robust than raw bubble count under partial or blurred froth visibility;
* selecting representative images for qualitative comparison.

The objective of Session 3 is therefore to determine which implemented features provide the most useful and defensible description of froth morphology before deciding which should become official OPC-UA/EAE supervisory soft-sensor outputs.
