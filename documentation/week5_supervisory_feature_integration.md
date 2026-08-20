# Week 5 – Session 4: Supervisory Feature Integration and End-to-End Validation

## 1. Purpose

The purpose of Session 4 was to move from the feature-analysis stage completed in Session 3 to the **final supervisory soft-sensor integration stage**.

Session 3 identified a reduced set of morphology features that provided useful and comparatively non-redundant information about the detected froth bubble population. Session 4 therefore focused on:

* defining the supervisory soft-sensor feature subset;
* integrating the selected features into the existing Python OPC-UA server;
* adding corresponding acquisition variables within EcoStruxure Automation Expert (EAE);
* validating live Python → OPC-UA → EAE communication;
* confirming that the existing Week 4 communication and supervisory-status architecture remained operational;
* repeating the existing robustness tests after integration.

No changes were made to the frozen YOLOv8-seg inference configuration, combined-mask method, contour extraction, or underlying feature calculations.

---

## 2. Selected Supervisory Soft-Sensor Features

Based on the statistical and visual analysis completed during Session 3, the following features were selected as the primary supervisory morphology outputs:

| Supervisory variable | Python feature                  | Description                                                                         |
| -------------------- | ------------------------------- | ----------------------------------------------------------------------------------- |
| `BubbleCount`        | `bubble_count`                  | Number of external bubble contours detected in the visible/segmentable image region |
| `MedianECD`          | `median_equivalent_diameter_px` | Characteristic detected bubble size                                                 |
| `ECD_P10`            | `ecd_p10_px`                    | Lower portion of the detected bubble-size distribution                              |
| `ECD_P90`            | `ecd_p90_px`                    | Upper portion of the detected bubble-size distribution                              |
| `MeanCircularity`    | `mean_circularity`              | Mean bubble-shape/circularity descriptor                                            |

This selection retains information describing:

* bubble population;
* characteristic bubble size;
* lower and upper bubble-size distribution;
* bubble shape.

### Features retained internally

The full Python pipeline continues to calculate:

```text
mean_area_px2
mean_equivalent_diameter_px
std_equivalent_diameter_px
mask_area_fraction
```

These values were not removed from the machine-vision pipeline.

Instead, the architecture now distinguishes between:

```text
Full Python analytical feature set
                ↓
        Feature selection
                ↓
Reduced supervisory OPC-UA/EAE feature set
```

This allows richer analysis to remain available in Python without unnecessarily increasing the number of process-facing supervisory variables.

---

## 3. Rationale for Supervisory Feature Selection

The Session 3 analysis provided the basis for the selected subset.

### `BubbleCount`

`bubble_count` was retained because it describes the detected visible bubble population and was not strongly redundant with characteristic bubble size.

It continues to be interpreted as a **visible-region measurement**, rather than a complete physical bubble population, because some dataset images contain blurred or poorly resolved regions.

### `MedianECD`

`median_equivalent_diameter_px` was selected as the principal characteristic bubble-size descriptor.

Session 3 showed that median ECD:

* successfully distinguished representative small- and large-bubble images;
* was less influenced by the large-bubble tail than mean ECD;
* provided a robust and directly interpretable measure of the typical detected bubble size.

### `ECD_P10` and `ECD_P90`

The percentile features were selected to complement median ECD and provide information about the bubble-size distribution.

Together:

```text
P10 → smaller-bubble region
Median → characteristic size
P90 → larger-bubble region
```

This representation was considered more directly interpretable for supervisory use than transmitting mean and standard deviation alone.

### `MeanCircularity`

`mean_circularity` was retained because it provides shape information that is distinct from the bubble-size descriptors.

### Features not selected as primary supervisory outputs

`mean_area_px2` and `mean_equivalent_diameter_px` were retained internally because Session 3 demonstrated substantial redundancy between them.

`std_equivalent_diameter_px` was also retained internally because distribution width is already represented through the selected percentile features.

`mask_area_fraction` remains available as an auxiliary analytical descriptor, but was not selected as a primary supervisory variable because its interpretation is affected by blurred and poorly resolved image regions.

---

## 4. Python OPC-UA Server Integration

The existing Python OPC-UA server was extended to expose the newly selected bubble-size distribution variables.

New OPC-UA nodes were added for:

```text
MedianECD
ECD_P10
ECD_P90
```

The existing supervisory outputs:

```text
BubbleCount
MeanCircularity
```

were retained.

Existing Week 4 communication and status nodes were also left unchanged.

The selected OPC-UA data types were:

| Variable          | OPC-UA value type |
| ----------------- | ----------------- |
| `BubbleCount`     | Integer / Int32   |
| `MedianECD`       | Double            |
| `ECD_P10`         | Double            |
| `ECD_P90`         | Double            |
| `MeanCircularity` | Double            |

Floating-point values were retained for all bubble-size and shape descriptors so that feature precision was not lost during communication.

---

## 5. Python Pipeline Publication

The existing OPC-UA pipeline runner was updated so that the new values were obtained directly from the result returned by:

```python
FrothMVPipeline.process_image()
```

The additional result fields used for OPC-UA publication were:

```text
median_equivalent_diameter_px
ecd_p10_px
ecd_p90_px
```

No additional feature calculation was introduced inside the communication layer.

The intended data flow remains:

```text
Image
  ↓
FrothMVPipeline
  ↓
Validated feature dictionary
  ↓
OPC-UA publication
```

This maintains separation between the machine-vision processing layer and the communication layer.

---

## 6. Independent OPC-UA Verification

Before modifying the EAE application, the updated Python OPC-UA server was verified independently using UaExpert.

The new nodes:

```text
MedianECD
ECD_P10
ECD_P90
```

were successfully visible alongside the previously implemented OPC-UA variables.

Live values updated correctly when new images were processed.

A known validation image was used to verify the numerical values:

```text
F5_1_2_1.ts-frames_frame-1785.png
```

Expected values from the previously validated pipeline were approximately:

| Feature           | Expected value |
| ----------------- | -------------: |
| `BubbleCount`     |            239 |
| `MedianECD`       |     16.0174 px |
| `ECD_P10`         |     10.3109 px |
| `ECD_P90`         |     30.8915 px |
| `MeanCircularity` |         0.6695 |

The values observed through OPC-UA matched the Python pipeline outputs, confirming successful publication of the selected soft-sensor variables.

---

## 7. EAE Acquisition Integration

The existing EAE composite:

```text
MV_OPCUA_ACQUISITION
```

was extended to acquire the new OPC-UA variables.

Additional OPC-UA read blocks were created for:

```text
MedianECD
ECD_P10
ECD_P90
```

The same OPC-UA connection configuration and data-acquisition approach validated during Week 4 were reused.

The new variables were configured using the same floating-point EAE type already used for the existing OPC-UA Double values.

The new outputs were exposed from the acquisition composite alongside the existing morphology and communication variables.

---

## 8. EAE Event Execution

The existing event-execution structure of `MV_OPCUA_ACQUISITION` was retained during the Session 4 integration.

The acquisition composite continues to use the established `E_CYCLE`-based cyclic execution arrangement to trigger OPC-UA read operations. The newly added reads for:

```text
MedianECD
ECD_P10
ECD_P90
```

were incorporated using the same acquisition pattern as the existing OPC-UA variables.

No sequential `REQ/CNF` chaining was introduced between the individual OPC-UA reads, as the existing cyclic structure had already operated successfully without observed execution issues.

The deterministic sequential event chain previously developed remains specific to the separate:

```text
MV_SUPERVISORY_STATUS
```

composite, where successive status calculations are triggered using upstream `CNF` events to ensure ordered evaluation.

This preserves the existing architectural separation between:

```text
MV_OPCUA_ACQUISITION
    → cyclic acquisition of OPC-UA values

MV_SUPERVISORY_STATUS
    → deterministic sequential evaluation of status logic
```

---

## 9. End-to-End Python → OPC-UA → EAE Validation

The updated system was deployed successfully to the existing:

```text
EcoRT_0
SimulationdPAC / soft dPAC
```

runtime.

Live values were compared across:

```text
Python pipeline
      ↓
UaExpert
      ↓
EAE watch values
```

The selected supervisory features matched successfully across all stages.

For the known validation image:

```text
F5_1_2_1.ts-frames_frame-1785.png
```

the following values were successfully transmitted:

```text
BubbleCount     ≈ 239
MedianECD       ≈ 16.0174
ECD_P10         ≈ 10.3109
ECD_P90         ≈ 30.8915
MeanCircularity ≈ 0.6695
```

Any differences visible in EAE were limited to normal display rounding.

This confirmed successful end-to-end transmission of the selected machine-vision soft-sensor outputs.

---

## 10. Dynamic Multi-Image Validation

The system was also tested across multiple images to ensure that the EAE values were updating dynamically rather than retaining a single initial result.

For successive processed images:

* `BubbleCount` updated correctly;
* `MedianECD` updated correctly;
* `ECD_P10` updated correctly;
* `ECD_P90` updated correctly;
* `MeanCircularity` updated correctly.

The percentile ordering condition:

[
ECD_{P10} \leq MedianECD \leq ECD_{P90}
]

was also maintained for valid processed images.

This provided an additional check that the EAE variables were mapped to the correct OPC-UA nodes.

---

## 11. Existing Supervisory Status Verification

Following integration of the additional morphology variables, the existing supervisory-status logic was rechecked.

During normal pipeline operation:

```text
MV_CommsOK     = TRUE
MV_HeartbeatOK = TRUE
PipelineOK     = TRUE
MV_DataValid   = TRUE
```

The additional OPC-UA reads therefore did not disrupt the previously validated Week 4 supervisory architecture.

The morphology values and their validity remain intentionally separated.

For example, an EAE variable may retain its most recently received numerical value while:

```text
MV_DataValid = FALSE
```

indicates that the value should not currently be considered valid.

This avoids encoding failure states directly into process measurements using artificial values such as `-1`.

---

## 12. Corrupt-Image Robustness Regression

The corrupt-image test previously established during Week 4 was repeated after the new feature integration.

A corrupt image was deliberately included in the processing sequence.

The expected behaviour was reproduced successfully:

```text
Corrupt image encountered
        ↓
Pipeline processing failure recognised
        ↓
PipelineOK = FALSE
        ↓
MV_DataValid = FALSE
```

The batch-processing system continued operating according to the existing error-handling behaviour.

The additional soft-sensor variables did not interfere with detection or propagation of the invalid pipeline state.

This confirms that the new feature integration did not regress the existing corrupt-image robustness behaviour.

---

## 13. Heartbeat-Stale Robustness Regression

The heartbeat-stale test was also repeated.

Heartbeat updates from Python were deliberately stopped while the OPC-UA connection remained active.

The expected supervisory distinction was reproduced:

```text
OPC-UA connection remains active
            ↓
Heartbeat stops changing
            ↓
MV_CommsOK remains TRUE
            ↓
MV_HeartbeatOK becomes FALSE
            ↓
MV_DataValid becomes FALSE
```

This confirms that the system continues to distinguish between:

* an active OPC-UA communication connection; and
* a source application that is no longer actively updating.

The new morphology feature reads did not interfere with the heartbeat watchdog operation.

---

## 14. Communication-Loss Robustness Regression

The Python OPC-UA server was stopped to reproduce a complete communication-loss condition.

The EAE supervisory system successfully detected the loss of communication.

The expected final state was reproduced:

```text
MV_CommsOK = FALSE
MV_DataValid = FALSE
```

After restarting the Python OPC-UA server, communication and live feature acquisition recovered successfully.

This confirms that the additional supervisory feature nodes did not affect the existing communication-loss and recovery behaviour.

---

## 15. Regression Outcome

The repeated robustness tests demonstrated that extending the OPC-UA interface with the selected Week 5 soft-sensor variables did **not regress the previously validated Week 4 behaviour**.

The following remained operational:

* OPC-UA communication monitoring;
* heartbeat supervision;
* pipeline validity;
* data-validity signalling;
* corrupt-image handling;
* communication-loss detection;
* recovery after communication restoration;
* dynamic image-by-image metric publication.

A new 40-image MV algorithm regression was not required during this session because the underlying machine-vision processing and metric calculations were not changed.

Session 4 validation instead focused on **communication integrity and end-to-end integration**.

---

## 16. Final Week 5 Supervisory Architecture

The resulting architecture is:

```text
                     Input froth image
                            ↓
                        YOLOv8-seg
                            ↓
                   Combined binary mask
                            ↓
                    External contours
                            ↓
                  Full Python feature set
                            │
             ┌──────────────┴───────────────┐
             │                              │
      Analysis / diagnostics        Supervisory selection
                                             │
                                             ├── BubbleCount
                                             ├── MedianECD
                                             ├── ECD_P10
                                             ├── ECD_P90
                                             └── MeanCircularity
                                             │
                                           OPC-UA
                                             ↓
                                MV_OPCUA_ACQUISITION
                                (E_CYCLE acquisition)
                                             ↓
                                MV_SUPERVISORY_STATUS
                                (sequential status logic)
                                             │
                ┌────────────────────────────┴──────────────────────┐
                │                                                   │
        Morphology outputs                                  Status outputs
                                                           MV_CommsOK
                                                           MV_HeartbeatOK
                                                           PipelineOK
                                                           MV_DataValid
```

This maintains separation between:

1. machine-vision inference;
2. full feature extraction;
3. supervisory feature selection;
4. OPC-UA communication;
5. EAE acquisition;
6. supervisory validity monitoring.

---

## 17. Session 4 Conclusions

Session 4 successfully integrated the selected Week 5 machine-vision soft-sensor features into the existing Python → OPC-UA → EAE architecture.

The final selected supervisory morphology set consists of:

```text
BubbleCount
MedianECD
ECD_P10
ECD_P90
MeanCircularity
```

The remaining analytical features continue to be calculated internally within Python but are not required as primary supervisory outputs.

The new variables were successfully:

* generated by the existing MV pipeline;
* published through the Python OPC-UA server;
* independently verified through UaExpert;
* acquired successfully within EAE;
* updated dynamically across multiple images.

The repeated robustness tests also confirmed that the additional feature integration did not disturb the previously validated communication, heartbeat, pipeline-status, or data-validity behaviour.

The resulting implementation therefore demonstrates an end-to-end machine-vision soft-sensor architecture in which a reduced set of meaningful froth morphology descriptors can be supplied to an IEC 61499-based supervisory automation environment while maintaining independent communication and validity monitoring.

---

## 18. Week 5 Outcome and Next Steps

At the completion of Session 4, the main Week 5 soft-sensor objective has been achieved:

```text
Feature definition
        ↓
Feature implementation
        ↓
Numerical validation
        ↓
Statistical interpretation
        ↓
Feature selection
        ↓
OPC-UA/EAE integration
        ↓
End-to-end validation
```

The system now provides validated supervisory measurements describing:

* visible bubble population;
* characteristic bubble size;
* bubble-size distribution;
* bubble shape.

Future work can therefore move toward the next stage of system development.

Likely next activities include:

* consolidating the Week 5 implementation;
* continuing the IEC 61499 supervisory architecture;
* integrating the soft-sensor variables into the wider system design;
* progressing HMI/interface development if required;
* preparing for later Control Expert and complete system-integration testing.

The unresolved CAT/HMI live-value binding issue remains independent of the successful OPC-UA/EAE soft-sensor integration and does not prevent progression of the core system architecture.