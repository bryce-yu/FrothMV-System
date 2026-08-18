# Week 5 – Soft-Sensor Feature Definition

## 1. Starting Point

Week 5 begins from the validated Week 4 implementation:

* MV pipeline validation complete.
* Python OPC-UA publishing operational.
* EAE successfully reading live MV values.
* OPC-UA acquisition encapsulated in `MV_OPCUA_ACQUISITION`.
* Supervisory health logic encapsulated in `MV_SUPERVISORY_STATUS`.
* Communication, heartbeat, pipeline validity, and failure handling validated.
* Second-laptop portability confirmed.

### Second-Laptop Portability Check

* **Date of test:** 17/08/2026
* **Laptop/system:** ASUS Zenbook
* **Python environment activated successfully:** Yes
* **Python OPC-UA server operated normally:** Yes
* **EAE connected successfully:** Yes
* **Acquisition composite operated correctly:** Yes
* **Supervisory-status composite operated correctly:** Yes
* **MV values updated correctly:** Yes
* **Required configuration change:** OPC-UA endpoint IP/URI only

The Week 4 Python–EAE implementation was successfully reproduced on the second development laptop. No Python code or EAE FB logic changes were required; only the OPC-UA server IP address in the EAE connection URI was updated. This provides evidence that the implementation is portable across the two development environments.

### Frozen MV Configuration

The existing MV configuration remains unchanged for Week 5 feature development:

* **Model:** `models/best.pt`
* **Confidence threshold:** `0.15`
* **Image size:** `640`
* **Maximum detections:** `1000`
* **Minimum contour area:** `10 px²`

The existing Week 4 metrics will also remain unchanged so that Week 5 development is additive and backward-compatible.

---

## 2. Purpose

The purpose of Week 5 is to define and implement additional quantitative froth-morphology features for use as machine-vision soft-sensor variables.

### Soft-Sensor Definition

For this project, the machine-vision soft sensor is defined as:

> A machine-vision system that derives quantitative descriptors of froth bubble morphology from YOLO segmentation results for use within a supervisory industrial automation architecture.

At this stage, the soft sensor is **not** intended to infer process variables such as:

* mineral recovery;
* concentrate grade;
* airflow rate;
* reagent concentration.

The available dataset does not provide labelled process-state data linking the froth images to these quantities.

Instead, the current soft sensor estimates observable froth characteristics including:

* approximate visible bubble population;
* characteristic bubble size;
* bubble-size distribution;
* bubble shape;
* predicted mask/image occupancy.

### Dataset Visibility Limitation

The dataset frequently provides only a partially clear view of the froth surface, with some regions blurred or otherwise unusable.

Consequently, raw `bubble_count` should be interpreted as a **visible-region measurement** rather than an estimate of the complete physical bubble population across the flotation surface.

Distribution-based descriptors such as median ECD, ECD spread, and ECD percentiles may therefore provide more robust characterisation of the visible froth morphology under partial visibility.

---

## 3. Existing Metrics

The current `calculate_contour_metrics()` implementation returns:

* `bubble_count`
* `mean_area_px2`
* `mean_equivalent_diameter_px`
* `mean_circularity`

The current implementation already stores the individual valid-contour measurements internally using:

* `areas`
* `diameters`
* `circularities`

Therefore, additional bubble-size distribution features can be calculated directly from the existing `diameters` list without modifying the YOLO segmentation stage or external-contour extraction method.

### Existing Processing Structure

```text
Combined YOLO mask
        ↓
External contours
        ↓
Individual valid contours
        ↓
Area / ECD / circularity
        ↓
Per-contour measurement lists
        ↓
Existing aggregate metrics
```

Week 5 will extend only the final statistical feature-extraction stage.

---

## 4. Proposed Week 5 Feature Set

The Session 2 implementation will retain all existing metrics and add five new features.

| Feature                         | Source           | Definition                                          | Purpose / Interpretation                                                  |
| ------------------------------- | ---------------- | --------------------------------------------------- | ------------------------------------------------------------------------- |
| `bubble_count`                  | Contours         | Number of valid external contours                   | Approximate visible-region bubble population                              |
| `mean_area_px2`                 | Contours         | Mean valid contour area                             | Existing average bubble-size descriptor                                   |
| `mean_equivalent_diameter_px`   | Contours         | Mean equivalent-circle diameter                     | Existing characteristic bubble-size descriptor                            |
| `median_equivalent_diameter_px` | ECD distribution | Median equivalent diameter                          | More robust characteristic bubble size, less influenced by extreme values |
| `std_equivalent_diameter_px`    | ECD distribution | Standard deviation of equivalent diameter           | Describes bubble-size distribution spread                                 |
| `ecd_p10_px`                    | ECD distribution | 10th percentile equivalent diameter                 | Describes the lower region of the bubble-size distribution                |
| `ecd_p90_px`                    | ECD distribution | 90th percentile equivalent diameter                 | Describes the upper region of the bubble-size distribution                |
| `mean_circularity`              | Contours         | Mean contour circularity                            | Describes average bubble shape / deformation                              |
| `mask_area_fraction`            | Combined mask    | Predicted mask pixels divided by total image pixels | Describes the relative occupancy of the predicted segmentation mask       |

### Potential Feature Redundancy

`mean_area_px2` and `mean_equivalent_diameter_px` both describe bubble size and are mathematically related.

Neither will be removed at this stage. Their statistical relationship will instead be examined during Week 5 feature analysis to determine whether both provide useful independent information.

---

## 5. New Feature Definitions

### 5.1 Median Equivalent Diameter

The median equivalent diameter will be calculated from the existing `diameters` list:

```python
np.median(diameters)
```

**Output name:**

```text
median_equivalent_diameter_px
```

This feature provides a characteristic bubble-size measure that is less sensitive to unusually small or large detected regions than the arithmetic mean.

---

### 5.2 Equivalent-Diameter Standard Deviation

The spread of bubble sizes within an image will be calculated using:

```python
np.std(diameters)
```

**Output name:**

```text
std_equivalent_diameter_px
```

The NumPy default population standard deviation (`ddof=0`) will be used because the metric describes the complete set of valid contours detected within the analysed image.

---

### 5.3 ECD Percentiles

The lower and upper regions of the bubble-size distribution will be represented using the 10th and 90th percentiles:

```python
np.percentile(diameters, 10)
np.percentile(diameters, 90)
```

**Output names:**

```text
ecd_p10_px
ecd_p90_px
```

A separate P50 feature is unnecessary because the 50th percentile is equivalent to the median, which is already represented by `median_equivalent_diameter_px`.

---

### 5.4 Mask Area Fraction

`mask_area_fraction` will be calculated from the combined Boolean segmentation mask rather than from the individual contour lists.

Definition:

[
\text{Mask Area Fraction}
=========================

\frac{\text{Number of non-zero pixels in combined mask}}
{\text{Total number of image pixels}}
]

Conceptual implementation:

```python
mask_area_fraction = (
    np.count_nonzero(combined_mask)
    / combined_mask.size
)
```

**Output name:**

```text
mask_area_fraction
```

### Processing Structure

```text
Combined mask
    │
    ├── extract_external_contours()
    │         ↓
    │   calculate_contour_metrics()
    │         ↓
    │   ECD distribution features
    │
    └── mask_area_fraction
```

Distribution features belong naturally within `calculate_contour_metrics()` because the required per-contour diameter values are already available there.

`mask_area_fraction` is instead a **mask-level feature** and should be calculated separately using the combined Boolean mask.

### Interpretation Limitation

`mask_area_fraction` should not currently be interpreted directly as physical froth-surface coverage.

Because some dataset images contain blurred or unusable regions, this feature is more conservatively defined as:

> The fraction of total image pixels belonging to the combined predicted segmentation mask.

Its behaviour under varying image visibility should be examined during later Week 5 feature analysis.

---

## 6. Edge-Case Behaviour

The existing `calculate_contour_metrics()` function returns zero-valued numerical metrics when no valid contours are detected.

The same behaviour will be maintained for all new contour-derived features.

The updated empty result should therefore be:

```python
{
    "bubble_count": 0,
    "mean_area_px2": 0.0,
    "mean_equivalent_diameter_px": 0.0,
    "mean_circularity": 0.0,
    "median_equivalent_diameter_px": 0.0,
    "std_equivalent_diameter_px": 0.0,
    "ecd_p10_px": 0.0,
    "ecd_p90_px": 0.0,
}
```

Returning `0.0` rather than `NaN` also provides simpler behaviour for later OPC-UA/EAE integration.

Data validity remains independently qualified by the existing pipeline and supervisory status signals.

---

## 7. Feature Categories

The system variables should remain logically separated into three groups.

### MV / Soft-Sensor Features

These describe the observed froth morphology:

```text
bubble_count
mean_area_px2
mean_equivalent_diameter_px
median_equivalent_diameter_px
std_equivalent_diameter_px
ecd_p10_px
ecd_p90_px
mean_circularity
mask_area_fraction
```

### Diagnostic / Operational Variables

These describe model or pipeline operation rather than froth morphology, for example:

```text
yolo_raw_instance_count
yolo_valid_instance_count
processing_time
```

The individual `areas`, `diameters`, and `circularities` lists will remain internal for now rather than being exposed through the normal pipeline output.

### Supervisory Status Variables

These qualify whether the soft-sensor values are operationally valid:

```text
PipelineOK
PipelineStatus
MV_CommsOK
MV_HeartbeatOK
MV_DataValid
```

This separation prevents diagnostic and system-health information from being confused with actual froth soft-sensor measurements.

---

## 8. Session 2 Implementation Plan

### 8.1 Contour-Derived Features

Extend `calculate_contour_metrics()` in `src/mv/metrics.py` to calculate:

```text
median_equivalent_diameter_px
std_equivalent_diameter_px
ecd_p10_px
ecd_p90_px
```

These features will use the existing `diameters` list.

The definitions of the existing four metrics must remain unchanged.

### 8.2 Mask-Level Feature

Add:

```text
mask_area_fraction
```

elsewhere in the metrics/pipeline processing path using the combined Boolean mask.

The exact location will be selected after reviewing how `pipeline.py` currently connects:

```text
combine_instance_masks()
        ↓
extract_external_contours()
        ↓
calculate_contour_metrics()
```

### 8.3 Unit Tests

Extend `tests/test_metrics.py` to verify:

* known contours produce the expected median ECD;
* identical-sized contours produce `std_equivalent_diameter_px == 0`;
* a known diameter distribution produces the expected P10 and P90 behaviour;
* zero valid contours return `0.0` for all new contour-derived metrics;
* a known Boolean mask produces the expected `mask_area_fraction`.

### 8.4 Items Not Modified During Initial Feature Implementation

The following should remain unchanged until the new Python-side features have been implemented and validated:

* OPC-UA server structure;
* EAE OPC-UA acquisition FBs;
* supervisory-status logic;
* HMI/CAT implementation.

The new features should first be proven locally within the MV pipeline before deciding which features should be exposed as OPC-UA/EAE supervisory variables.

---

## Session 1 Outcome

Session 1 establishes the following Week 5 design decisions:

1. The existing Week 4 MV configuration and metrics remain frozen.
2. Existing per-contour measurement lists are sufficient for additional ECD distribution statistics.
3. Median ECD, ECD standard deviation, P10, and P90 will be added as contour-derived features.
4. `mask_area_fraction` will be added separately as a combined-mask-level feature.
5. Zero-contour behaviour will remain consistent with the existing implementation.
6. Raw per-contour arrays will remain internal.
7. Partial froth visibility is explicitly recognised as a dataset limitation and as motivation for investigating distribution-based features alongside raw bubble count.
8. OPC-UA/EAE integration changes will be deferred until the new soft-sensor features have been implemented and validated in Python.


## Session 1 Design Status Update

The soft-sensor feature set defined during Session 1 was subsequently implemented and validated during Week 5 Session 2.

Implementation status:

* `median_equivalent_diameter_px` — Implemented and tested
* `std_equivalent_diameter_px` — Implemented and tested
* `ecd_p10_px` — Implemented and tested
* `ecd_p90_px` — Implemented and tested
* `mask_area_fraction` — Implemented and tested

All six metric unit tests passed.

Single-image, five-image, and 40-image pipeline validation were completed successfully.

The 40-image regression comparison confirmed identical bubble counts and only negligible differences in the remaining pre-existing metrics, indicating that the new soft-sensor feature calculations did not materially alter the validated Week 4 MV method.

Detailed implementation and validation results are recorded separately in the Week 5 Session 2 documentation.
