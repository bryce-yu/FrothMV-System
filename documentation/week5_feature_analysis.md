# Week 5 – Session 3: Soft-Sensor Feature Analysis and Interpretation

## 1. Purpose

The purpose of Session 3 was to move from **feature implementation and validation** to **feature analysis and interpretation**.

Sessions 1 and 2 established the extended machine-vision soft-sensor feature set and confirmed that the new metrics could be added without materially altering the previously validated MV pipeline. Session 3 therefore focused on determining:

* how the soft-sensor features vary across the 40-image validation set;
* whether any features provide redundant information;
* whether mean- or distribution-based bubble-size descriptors are more informative;
* how the numerical features correspond to visually observable froth morphology;
* which features should be considered for eventual supervisory OPC-UA/EAE integration.

No changes were made to the frozen YOLO inference, mask-processing, contour-extraction, or metric-calculation method during this session.

---

## 2. Analysis Dataset

The analysis used the existing 40-image Week 5 validation output:

```text
results/
└── soft_sensor_analysis/
    └── session2_validation/
        └── pipeline_features_40.csv
```

The analysed soft-sensor features were:

### Bubble population

* `bubble_count`

### Bubble size

* `mean_area_px2`
* `mean_equivalent_diameter_px`
* `median_equivalent_diameter_px`

### Bubble-size distribution

* `std_equivalent_diameter_px`
* `ecd_p10_px`
* `ecd_p90_px`

### Bubble shape

* `mean_circularity`

### Mask-level occupancy

* `mask_area_fraction`

Existing diagnostic values, including YOLO instance counts, instance-to-contour ratio, and processing time, remained separate from the primary soft-sensor feature set.

---

## 3. Analysis Script

A new analysis script was created:

```text
src/analyse_soft_sensor_features.py
```

The script operates only on the previously generated 40-image CSV and does not rerun YOLO inference.

The analysis included:

* descriptive statistics;
* feature variability;
* feature histograms;
* Pearson correlation analysis;
* Spearman rank correlation analysis;
* mean area versus mean ECD analysis;
* mean versus median ECD analysis;
* ECD distribution-width analysis;
* bubble count and mask occupancy relationships;
* exploratory mask-occupancy grouping;
* automated selection of representative images.

Outputs were stored under:

```text
results/
└── soft_sensor_analysis/
    └── session3_analysis/
        ├── descriptive_statistics.csv
        ├── feature_variability.csv
        ├── pearson_correlation.csv
        ├── spearman_correlation.csv
        ├── mean_vs_median_ecd.csv
        ├── occupancy_group_summary.csv
        ├── representative_images.csv
        ├── session3_enriched_features.csv
        ├── session3_summary.txt
        ├── representative_images/
        └── plots/
```

The script completed successfully for all 40 images.

---

## 4. Key Correlation Results

The main correlations obtained from the Session 3 analysis were:

| Relationship                                  |  Result |
| --------------------------------------------- | ------: |
| Mean area vs mean ECD – Pearson               |  0.9737 |
| Mean area vs mean ECD – Spearman              |  0.9775 |
| Mean ECD vs median ECD – Spearman             |  0.9221 |
| Std ECD vs P90–P10 range – Spearman           |  0.8208 |
| Bubble count vs median ECD – Spearman         | -0.3778 |
| Bubble count vs mask area fraction – Spearman |  0.5984 |

These results were used primarily to investigate feature redundancy and complementary information rather than to infer process relationships.

---

## 5. Mean Area and Mean Equivalent Diameter

A very strong relationship was observed between:

```text
mean_area_px2
```

and:

```text
mean_equivalent_diameter_px
```

with:

```text
Pearson  = 0.9737
Spearman = 0.9775
```

This indicates that the two features provide substantially overlapping information across the 40-image dataset.

This is expected because equivalent diameter is calculated from contour area:

[
ECD_i = \sqrt{\frac{4A_i}{\pi}}
]

However, the two aggregate quantities are not mathematically identical because mean ECD is calculated by converting each contour area to ECD before averaging.

Therefore:

[
\overline{ECD}
\neq
\sqrt{\frac{4\overline{A}}{\pi}}
]

in general.

Although the two features are not exact duplicates, their very strong correlation indicates limited benefit in transmitting both as supervisory outputs.

### Interpretation

`mean_equivalent_diameter_px` is more directly interpretable as a bubble-size quantity than `mean_area_px2`. Therefore, if a reduced supervisory feature set is required, mean area is a strong candidate to remain an internal analysis metric rather than an OPC-UA/EAE output.

---

## 6. Mean versus Median Equivalent Diameter

Mean and median ECD were also strongly correlated:

```text
Spearman = 0.9221
```

However, the mean ECD was consistently greater than the median ECD across the analysed dataset.

The mean absolute difference was:

```text
2.7526 px
```

and the median mean-minus-median difference was:

```text
2.4260 px
```

The consistently larger mean indicates that the detected bubble-size distributions are generally **right-skewed**, with relatively large detected bubbles pulling the mean upward.

### Interpretation

This supports the use of:

```text
median_equivalent_diameter_px
```

as a robust descriptor of the **characteristic or typical detected bubble size**.

Unlike the mean, the median is less affected by a relatively small number of very large predicted bubbles.

The mean remains useful for analysis, but median ECD currently appears more suitable as a primary supervisory size descriptor.

---

## 7. Bubble-Size Distribution

Bubble-size spread was investigated using:

```text
std_equivalent_diameter_px
```

and the percentile range:

[
ECD_{P90} - ECD_{P10}
]

The Spearman correlation between these two measures was:

```text
0.8208
```

This indicates a strong relationship, suggesting that both capture similar aspects of bubble-size variability, although they are not completely redundant.

Further inspection showed that the standard deviation was more strongly associated with the upper part of the bubble-size distribution than with the lower percentile.

### Interpretation

The percentile-based representation:

```text
P10
Median
P90
```

provides an intuitive description of the bubble-size distribution:

* `P10` represents the smaller-bubble portion;
* `Median` represents the characteristic bubble size;
* `P90` represents the larger-bubble portion.

This may be more informative for supervisory use than transmitting mean and standard deviation alone, particularly where the detected bubble-size distribution is skewed.

---

## 8. Bubble Count versus Bubble Size

The Spearman correlation between bubble count and median ECD was:

```text
-0.3778
```

This represents only a moderate negative relationship.

There is some tendency for images with a larger number of detected bubbles to contain smaller characteristic bubble sizes, but the relationship is not sufficiently strong for the two features to be considered redundant.

### Interpretation

The two features describe different aspects of froth morphology:

```text
bubble_count
```

describes the visible detected bubble population, while:

```text
median_equivalent_diameter_px
```

describes the characteristic size of the detected bubbles.

Both therefore remain useful candidates for the supervisory soft-sensor interface.

---

## 9. Mask Area Fraction

The relationship between bubble count and mask area fraction was:

```text
Spearman = 0.5984
```

indicating a moderate positive association.

Images containing more detected bubbles often also contained a greater number of segmented pixels. However, the relationship was not sufficiently strong for the two measurements to be considered equivalent.

The Session 3 visual analysis also confirmed an important limitation of `mask_area_fraction`.

The feature is defined as:

[
\text{mask area fraction}
=========================

\frac{\text{predicted mask pixels}}
{\text{total image pixels}}
]

Therefore, the denominator includes blurred or otherwise poorly resolved image regions.

Consequently, `mask_area_fraction` should currently be interpreted as an **image-level predicted segmentation occupancy descriptor**, rather than a direct measure of physical froth coverage.

---

## 10. Representative-Image Visual Validation

Representative images were selected from the 40-image dataset to determine whether the calculated soft-sensor features corresponded to visually meaningful differences in froth morphology.

### 10.1 Small Bubble Population – Frame 1135

```text
F5_2_3_1.ts-frames_frame-1135.png
```

The image is dominated by a dense population of relatively small and visually similar bubbles.

The predicted contour visualisation contained approximately 587 contours, with the majority of detections in the clearer upper froth region being small and closely packed.

Although several larger bubbles are present, they do not dominate the distribution.

### Interpretation

The image provides visual support for:

* low median ECD;
* relatively narrow bubble-size spread;
* a large detected bubble population.

This confirms that the calculated median ECD behaves sensibly for an image with a genuinely small characteristic bubble population.

---

### 10.2 Large Characteristic Bubble Size – Frame 1450

```text
F5_1_1_1.ts-frames_frame-1450.png
```

This image contains visibly larger bubble structures than Frame 1135.

The predicted contour visualisation contained approximately 169 contours. Several medium-to-large bubbles occupy a substantial part of the clear upper froth region, while smaller bubbles remain present toward other areas.

Importantly, the large structures are not limited to a single isolated outlier.

### Interpretation

The high median ECD therefore represents a genuine shift toward a larger characteristic bubble population rather than being caused only by one or two extreme predictions.

The comparison between Frames 1135 and 1450 provides strong visual evidence that:

```text
median_equivalent_diameter_px
```

successfully distinguishes between small and large characteristic bubble populations.

---

### 10.3 Broad Bubble-Size Distribution – Frame 1085

```text
F5_1_1_2.ts-frames_frame-1085.png
```

This image contains a clear mixture of bubble sizes.

The upper froth region contains several large bubble structures alongside a much larger population of smaller bubbles.

Its representative metrics included approximately:

```text
Median ECD = 15.68 px
Mean ECD   = 22.26 px
P90 ECD    = 50.99 px
Std ECD    = 19.09 px
```

### Interpretation

The difference between mean and median ECD is visually understandable: the relatively small number of very large bubbles increases the mean substantially, while the median remains representative of the more typical detected population.

This image therefore demonstrates the limitation of using a single mean bubble-size metric for a heterogeneous, right-skewed distribution.

It also supports the use of median and percentile descriptors to characterise both the centre and spread of the detected bubble-size distribution.

---

### 10.4 Low Mask Area Fraction – Frame 1240

```text
F5_2_1_2.ts-frames_frame-1240.png
```

The upper portion contains some identifiable small bubbles, but much of the image, particularly the lower region, is blurred or contains poorly resolved froth texture rather than clearly distinguishable bubble boundaries.

Both the ground-truth and predicted masks contain substantially less segmented area in these poorly resolved regions.

### Interpretation

The relatively low `mask_area_fraction` cannot simply be interpreted as the image containing less physical froth.

Instead, it is influenced by:

* bubble morphology;
* visible bubble area;
* image blur;
* the amount of clearly segmentable froth;
* segmentation behaviour.

This demonstrates why `mask_area_fraction` requires cautious interpretation.

---

### 10.5 High Mask Area Fraction – Frame 1215

```text
F5_1_2_2.ts-frames_frame-1215.png
```

A large proportion of the clearly visible upper froth region is densely populated with successfully segmented bubbles.

The predicted contour visualisation contained approximately 327 contours, and substantial additional segmented regions were also present in the lower part of the frame.

### Interpretation

The high mask-area fraction corresponds visually with extensive successful segmentation across a comparatively large portion of the visible froth region.

The contrast between Frames 1215 and 1240 confirms that mask occupancy responds meaningfully to visible segmentation area, but also reinforces that it is influenced by image visibility and segmentation quality.

---

## 11. Overall Representative-Image Findings

The representative-image analysis produced a consistent relationship between numerical features and observed image morphology:

| Representative case | Interpretation                                                           |
| ------------------- | ------------------------------------------------------------------------ |
| Frame 1135          | Small, dense and relatively uniform bubble population                    |
| Frame 1450          | Larger characteristic bubble population                                  |
| Frame 1085          | Broad, right-skewed mixture of small and large bubbles                   |
| Frame 1240          | Low mask occupancy partly associated with blur and poorly resolved froth |
| Frame 1215          | High mask occupancy associated with dense and extensive segmentation     |

The comparison between Frames 1135, 1450 and 1085 is particularly useful.

Frame 1135 represents a genuinely small characteristic population, Frame 1450 represents a genuinely larger characteristic population, and Frame 1085 demonstrates a heterogeneous distribution where large bubbles significantly influence the mean.

These observations provide visual support for the use of median ECD as the main characteristic-size descriptor and percentile features for distribution information.

---

## 12. Preliminary Supervisory Feature Assessment

Based on the statistical and visual analysis, the current preliminary assessment is:

| Feature                         | Preliminary decision              | Rationale                                                                    |
| ------------------------------- | --------------------------------- | ---------------------------------------------------------------------------- |
| `bubble_count`                  | Keep                              | Provides visible bubble-population information not captured by size metrics  |
| `median_equivalent_diameter_px` | Strong candidate to keep          | Robust and visually meaningful characteristic bubble-size descriptor         |
| `ecd_p10_px`                    | Likely keep                       | Represents smaller-bubble portion of distribution                            |
| `ecd_p90_px`                    | Likely keep                       | Represents larger-bubble tail and heterogeneity                              |
| `mean_circularity`              | Keep for further consideration    | Provides a distinct bubble-shape descriptor                                  |
| `mask_area_fraction`            | Auxiliary / further consideration | Useful segmentation descriptor but affected by image visibility              |
| `mean_equivalent_diameter_px`   | Likely internal only              | Strongly related to median ECD and mean area                                 |
| `mean_area_px2`                 | Likely internal only              | Highly redundant with mean ECD and less intuitive                            |
| `std_equivalent_diameter_px`    | Likely internal only              | Distribution spread may be represented more intuitively using P10/median/P90 |

No features were removed from the Python pipeline during Session 3.

The distinction remains:

```text
Full Python analysis feature set
                ≠
Final supervisory OPC-UA/EAE feature set
```

The Python pipeline may retain a richer set of analytical and diagnostic outputs even if only a subset is exposed to the automation system.

---

## 13. Session 3 Conclusions

Session 3 successfully demonstrated that the expanded Week 5 soft-sensor feature set contains both redundant and complementary information.

The main findings were:

1. Mean bubble area and mean ECD were extremely strongly correlated, indicating substantial redundancy.

2. Mean and median ECD were strongly related, but mean ECD was consistently larger, supporting the presence of right-skewed detected bubble-size distributions.

3. Median ECD provided a visually meaningful measure of characteristic bubble size and successfully distinguished representative small- and large-bubble images.

4. P10 and P90 provide useful complementary information about the lower and upper portions of the bubble-size distribution.

5. Standard deviation and P90–P10 both describe size-distribution width and therefore may not both be necessary as supervisory variables.

6. Bubble count and median ECD provide different information and should not currently be treated as redundant.

7. `mask_area_fraction` provides useful information about predicted segmentation occupancy but is affected by blurred and poorly resolved image regions and therefore should not be interpreted as direct physical froth coverage.

8. Representative-image inspection confirmed that the calculated numerical features generally correspond to meaningful visual differences in froth morphology.

Overall, the results support moving toward a reduced supervisory feature set centred around:

```text
bubble_count
median_equivalent_diameter_px
ecd_p10_px
ecd_p90_px
mean_circularity
```

with `mask_area_fraction` retained as an auxiliary or diagnostic feature unless further analysis justifies its inclusion as a primary supervisory output.

---

## 14. Next Session

Session 4 should move from exploratory analysis to **final supervisory feature selection and integration**.

The intended next steps are:

1. confirm the final Python → OPC-UA → EAE soft-sensor feature subset;
2. retain the complete feature set internally within the Python pipeline;
3. add the selected features to the Python OPC-UA server;
4. update `MV_OPCUA_ACQUISITION` in EAE;
5. verify live Python → OPC-UA → EAE feature values;
6. ensure existing communication, heartbeat, pipeline-validity, and data-validity logic remains operational;
7. perform regression and robustness checks after the additional OPC-UA variables are introduced.