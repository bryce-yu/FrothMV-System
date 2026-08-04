# Week 3 Machine-Vision Diagnostics

## 1. Purpose

The purpose of the Week 3 diagnostic work was to identify the main causes of error in the YOLOv8 froth-bubble measurement pipeline.

The investigation focused on distinguishing between:

1. errors in the number of YOLO-predicted instance masks;
2. reductions in count caused when instance masks are combined into one binary mask;
3. limitations in the dataset masks or YOLO labels;
4. insufficient representation of dense small-bubble images during training.

The diagnostic work also corrected an important inference limitation identified after Week 2: the Ultralytics default maximum detection count of 300 instances per image.

---

## 2. Selected Inference Configuration

The Week 2 controlled experiments were rerun after increasing the maximum detection limit.

The selected configuration is:

* Model: `models/best.pt`
* Confidence threshold: `0.15`
* Minimum contour area: `10 px²`
* Inference image size: `640`
* Maximum detections per image: `1000`
* Test subset: fixed 40-image test manifest
* Hardware: CPU

The fixed manifest and all other evaluation settings were retained so that the effect of increasing `max_det` could be evaluated consistently.

---

## 3. Reason for Rerunning the Week 2 Experiments

During the initial Week 3 diagnostics, many images produced exactly 300 YOLO instances.

This indicated that the model predictions were reaching the Ultralytics default:

```text
max_det = 300
```

The repeated value of 300 was therefore not necessarily the natural number of predictions produced by the model. Instead, dense images were likely being truncated before all detections were returned.

The prediction scripts were updated to use:

```text
max_det = 1000
```

The three Week 2 controlled inference configurations and the timing measurements were then repeated.

The original results were retained under:

```text
results/yolo_experiments_v1/
```

The corrected rerun results were stored under:

```text
results/yolo_experiments_v2/
```

---

## 4. Corrected Controlled Inference Experiments

Three configurations were evaluated on the same fixed 40-image test manifest.

| Configuration          | Confidence | Minimum area (px²) | Bubble-count MAE | Mean-area MAE | Diameter MAE | Circularity MAE |
| ---------------------- | ---------: | -----------------: | ---------------: | ------------: | -----------: | --------------: |
| Baseline               |       0.25 |                 10 |          81.3750 |       69.6021 |       2.2856 |          0.0341 |
| Lower confidence       |       0.15 |                 10 |          32.4750 |       58.8184 |       2.2466 |          0.0172 |
| Smaller contour filter |       0.25 |                  5 |          80.9000 |       69.3781 |       2.2667 |          0.0337 |

### Interpretation

Lowering the confidence threshold from 0.25 to 0.15 remained the most effective tested adjustment.

Compared with the baseline configuration, the lower-confidence configuration reduced the MAE for:

* bubble count;
* mean area;
* equivalent diameter;
* circularity.

Reducing the minimum contour-area threshold from 10 to 5 px² again caused only negligible changes.

This confirms that the primary limitation is not OpenCV removing contours below 10 px².

The preferred inference configuration therefore remains:

```text
confidence = 0.15
minimum contour area = 10 px²
imgsz = 640
max_det = 1000
```

---

## 5. YOLO Instance Count and Combined-Mask Contour Count

### 5.1 Diagnostic definitions

Two predicted bubble-count definitions were compared.

#### YOLO valid instance count

The number of predicted YOLO segmentation masks whose area exceeds the minimum-area threshold.

Each predicted mask is counted as one instance, even if it overlaps heavily with another predicted mask.

#### Combined-mask contour count

All valid YOLO instance masks are merged into one binary mask. OpenCV external contours are then extracted from the combined mask.

Overlapping or touching instance masks may become one connected contour.

---

### 5.2 Diagnostic results

The corrected results using `max_det=1000` were:

* Mean ground-truth contour count: **334.950**
* Mean YOLO valid instance count: **461.575**
* Mean combined-mask contour count: **309.325**
* YOLO instance-count MAE: **128.325**
* Combined-contour-count MAE: **32.475**
* Mean instance-to-contour reduction: **152.250**
* Images affected by instance-to-contour reduction: **40 of 40**

---

## 6. Interpretation of Instance and Contour Counts

The corrected diagnostic results substantially changed the interpretation of the model behaviour.

The raw YOLO instance count was greater than the ground-truth contour count on average:

```text
Mean ground truth:       334.950
Mean YOLO instances:     461.575
```

This indicates that the model is not simply failing to detect enough instances overall.

Instead, it frequently produces:

* overlapping instance masks;
* multiple masks associated with the same connected bubble region;
* fragmented or duplicate predictions;
* separate masks that become connected when combined.

After combining the predicted masks, the average count decreased to:

```text
Mean combined contours:  309.325
```

This was substantially closer to the ground-truth mean.

The corresponding MAEs support this conclusion:

```text
YOLO instance-count MAE:     128.325
Combined-contour-count MAE:   32.475
```

Therefore, the raw YOLO instance count is currently not an appropriate direct estimate of bubble count.

The combined-mask contour count provides a much closer approximation to the ground-truth contour-based bubble definition.

---

## 7. Important Interpretation of the Count Reduction

The average reduction of 152.250 between YOLO instances and combined contours should not automatically be interpreted as 152 correctly detected bubbles being incorrectly merged.

The reduction may include:

* duplicate predictions of the same bubble;
* highly overlapping masks;
* fragmented masks representing parts of one region;
* neighbouring bubbles represented by overlapping masks;
* genuinely separate instances becoming connected during mask combination.

The result should therefore be described as:

> A large and systematic reduction from predicted instance masks to connected combined-mask regions.

Further visual inspection is required to determine the relative contribution of duplicate, fragmented and genuinely merged predictions.

---

## 8. Highest-Error Images

### 8.1 Bubble-count percentage error

| Rank | Image                               | Percentage error | Visual observation                                     |
| ---: | ----------------------------------- | ---------------: | ------------------------------------------------------ |
|    1 | `F5_1_1_2.ts-frames_frame-125.png`  |          34.434% | Dense small bubbles missed or insufficiently separated |
|    2 | `F5_2_1_2.ts-frames_frame-440.png`  |          33.456% | Dense small bubbles missed or insufficiently separated |
|    3 | `F5_1_1_1.ts-frames_frame-1575.png` |          29.439% | Dense small bubbles missed or insufficiently separated |
|    4 | `F5_2_2_1.ts-frames_frame-395.png`  |          27.748% | Dense small bubbles missed or insufficiently separated |
|    5 | `F5_1_1_1.ts-frames_frame-1540.png` |          27.203% | Dense small bubbles missed or insufficiently separated |

### Interpretation

Although the aggregate combined-contour count improved substantially after increasing `max_det`, the highest count errors still occur in dense images containing many small bubbles.

The remaining undercount is likely caused by insufficient separation of neighbouring bubbles rather than only by a lack of raw YOLO predictions.

---

### 8.2 Mean-area percentage error

| Rank | Image                               | Percentage error | Visual observation                                                |
| ---: | ----------------------------------- | ---------------: | ----------------------------------------------------------------- |
|    1 | `F5_1_1_2.ts-frames_frame-125.png`  |         132.514% | Merged neighbouring bubbles and one large incorrect contour       |
|    2 | `F5_1_1_1.ts-frames_frame-1540.png` |          78.209% | Merged neighbouring bubbles and an unusual moderate-sized contour |
|    3 | `F5_1_1_1.ts-frames_frame-1575.png` |          56.248% | Merged neighbouring bubbles                                       |
|    4 | `F5_1_1_1.ts-frames_frame-1480.png` |          55.045% | Merged neighbouring bubbles                                       |
|    5 | `F5_1_1_1.ts-frames_frame-1105.png` |          52.280% | Merged neighbouring bubbles                                       |

### Interpretation

The previous mean-area interpretation remains valid.

When neighbouring bubbles are represented as one connected predicted region:

* the number of contours decreases;
* the area of the connected contour increases;
* mean predicted area becomes overestimated.

The largest area errors therefore remain associated with local merging or insufficient separation of neighbouring bubbles.

---

## 9. Updated Processing-Time Results

The selected configuration was timed over the fixed 40-image test subset with visualisation generation disabled.

* Run 1: **74.661 seconds**
* Run 2: **73.098 seconds**
* Average total time: **73.880 seconds**
* Average processing time: **1.847 seconds per image**

This timing includes:

* model inference;
* mask resizing;
* instance-mask combination;
* contour extraction;
* metric calculation.

It excludes visualisation generation.

The corrected processing time is higher than the previous Week 2 estimate because the model is now allowed to retain and process substantially more than 300 detections.

The increase is considered acceptable for a supervisory soft-sensor application that does not require high-frame-rate closed-loop control.

---

## 10. Revised Overall Conclusion

The initial capped results suggested that YOLO was mainly under-detecting bubble instances.

After increasing `max_det` to 1000, this interpretation was revised.

The corrected results show that:

1. YOLO frequently produces more instance masks than the ground-truth contour count.
2. The raw instance count has a relatively high MAE and is not a reliable direct bubble-count estimate.
3. Combining the masks produces a much lower and more accurate contour count.
4. Dense small-bubble images remain the most difficult cases.
5. Local merging and insufficient separation continue to cause bubble-count underestimation and mean-area overestimation.
6. Lowering the confidence threshold to 0.15 remains the preferred inference adjustment.
7. Reducing the minimum contour-area threshold from 10 to 5 px² provides negligible benefit.

The selected approach remains:

```text
Bubble count:
combined-mask external contour count

Bubble size metrics:
calculated from combined-mask contours

Confidence:
0.15

Minimum contour area:
10 px²

Image size:
640

Maximum detections:
1000
```

---

## 11. Current Limitations

The current MV pipeline has the following known limitations:

* raw YOLO instance count may overestimate the number of physical bubbles;
* multiple predicted masks may overlap or represent the same connected region;
* dense small bubbles are not always separated correctly;
* connected predicted regions can produce underestimated counts;
* merged regions can produce overestimated mean area;
* the ground-truth masks themselves use connected contours as the reference bubble definition;
* pixel-based size values have not yet been converted into calibrated physical units;
* CPU inference currently averages approximately 1.85 seconds per image.

These limitations are acceptable for the current project stage provided they are clearly documented and the system is presented as a supervisory soft sensor rather than an exact physical bubble-count instrument.

---

## 12. Next Diagnostic Work

The next Week 3 work should focus on:

1. visually comparing individual YOLO masks with the combined binary mask;
2. identifying duplicate, fragmented and overlapping predictions;
3. inspecting original masks and reconstructed YOLO polygon labels;
4. checking whether dense small-bubble examples are adequately represented in the reduced training subset;
5. deciding whether one targeted retraining attempt is justified;
6. otherwise retaining the current model and formalising the reusable end-to-end Python pipeline.

The investigation should remain controlled and should not become an open-ended hyperparameter search.


## Representative Instance-Mask Inspection

Six representative images were selected from the corrected `max_det=1000` diagnostic results:

- two with the largest instance-to-contour reductions;
- two with the largest final contour-count errors;
- two with relatively low final contour-count errors.

| Image | Category | GT contours | YOLO instances | Combined contours | Main observation |
|---|---|---:|---:|---:|---|
| F5_2_2_2.ts-frames_frame-1110.png | Largest reduction | 621 | 915 | 579 | Duplicate or overlapping predictions |
| F5_2_2_1.ts-frames_frame-1525.png | Largest reduction | 517 | 832 | 529 | Duplicate or overlapping predictions |
| F5_2_2_1.ts-frames_frame-395.png | Highest final error | 555 | 607 | 401 | Duplicate or overlapping predictions |
| F5_2_1_2.ts-frames_frame-440.png | Highest final error | 272 | 242 | 181 | Duplicate or overlapping predictions |
| F5_1_2_1.ts-frames_frame-380.png | Low final error | 292 | 421 | 292 | Duplicate or overlapping predictions |
| F5_1_2_1.ts-frames_frame-605.png | Low final error | 265 | 369 | 266 | Duplicate or overlapping predictions |

### Visual interpretation

Across the six representative cases, the individual-mask overlays indicate that the reduction from YOLO instance count to combined contour count is primarily associated with duplicate or strongly overlapping predictions covering the same bubble regions.

When the instance masks are combined, these overlapping predictions collapse into single connected components. This substantially reduces the reported count and generally produces a contour count closer to the ground-truth contour count.

Some local merging of neighbouring bubbles and insufficient separation of dense small bubbles are still visible, particularly in the more difficult images. However, these effects appear secondary to the large number of overlapping or duplicate instance predictions.

The observed behaviour confirms that the raw YOLO instance count should not be interpreted directly as the number of physical bubbles. For the current model and dataset, the combined-mask contour count provides the more meaningful bubble-count estimate.