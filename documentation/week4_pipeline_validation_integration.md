# Week 4 – MV Pipeline Validation and OPC-UA Integration

## Session 1 - MV Pipeline Validation

### Purpose

The consolidated FrothMV pipeline developed during Week 3 was validated to confirm that refactoring the experimental YOLO/OpenCV scripts into reusable modules did not alter the selected soft-sensor calculation.

### Configuration

- Model: `models/best.pt`
- Confidence: 0.15
- Image size: 640
- Maximum detections: 1000
- Minimum contour area: 10 px²

### Unit Tests

`pytest tests/test_metrics.py -v`

Results:
- Empty-mask test: PASS
- Two-separated-contour test: PASS
- Overlapping-mask combination test: PASS

### Test script run:
```text
3 passed in 2.96s
```

Confirmed all three intended metric behaviours:
empty mask → zero bubble metrics
two separated circles → two external contours
overlapping instance masks → one connected contour after combining

- Directly supports the Week 3 design choice of using combined-mask contours as the official soft-sensor measurement basis.

### Single and folder image runs:

- Single image test: python src/run_single_image.py "C:\FrothMV-Data\froth-bubbles-dataset\test\test_images\F5_1_2_1.ts-frames_frame-1785.png"
```text
{
    "filename": "F5_1_2_1.ts-frames_frame-1785.png",
    "image_path": "C:\\FrothMV-Data\\froth-bubbles-dataset\\test\\test_images\\F5_1_2_1.ts-frames_frame-1785.png",
    "status": "OK",
    "bubble_count": 239,
    "mean_area_px2": 420.22175732217573,
    "mean_equivalent_diameter_px": 19.534412863468827,
    "mean_circularity": 0.6695332942693857,
    "yolo_raw_instance_count": 361,
    "yolo_valid_instance_count": 361,
    "instance_to_contour_ratio": 1.5104602510460252,
    "processing_time_seconds": 4.6504221000068355,
    "confidence": 0.15,
    "image_size": 640,
    "max_detections": 1000,
    "minimum_contour_area": 10.0
}
```

- Folder images test: python src/run_folder_pipeline.py dataset/pipeline_test_images

```text
[1/5] F5_1_2_1.ts-frames_frame-1785.png: count=239, time=3.258s
[2/5] F5_1_2_1.ts-frames_frame-380.png: count=292, time=1.902s
[3/5] F5_2_1_2.ts-frames_frame-415.png: count=167, time=1.063s
[4/5] F5_2_1_2.ts-frames_frame-440.png: count=181, time=1.042s
[5/5] F5_2_2_2.ts-frames_frame-1110.png: count=579, time=3.288s

Average processing time: 2.111 seconds/image
CSV saved to: C:\Users\bgyu5\OneDrive\Documents\UNI\Uni-2026\Semester Two\EEET4001\FrothMV-System\results\pipeline_runs\pipeline_results.csv
JSON saved to: C:\Users\bgyu5\OneDrive\Documents\UNI\Uni-2026\Semester Two\EEET4001\FrothMV-System\results\pipeline_runs\pipeline_results.json
```

- Note results for 1785 frame match in both single and folder run
- Inference warm-up/overhead only happens for first image and then does not need to happen for each subsequent image, as seen in processing times - also note longer processing time for the final image which has considerably more bubbles and therefore contours/YOLO detections to process. Reinforces Week 3 finding that raw YOLO instance count can be much higher than final physical bubble count because overlapping/duplicate masks collapse after combination.
- Both tests PASS

### Test error handling runs:

- Missing-image handling detected correctly at pipeline level, but the single-image runner initially exposed the exception as an uncaught traceback. Runner-level exception handling was added for cleaner user-facing behaviour. i.e.

Before:

```text
Traceback (most recent call last):
  File "C:\Users\bgyu5\OneDrive\Documents\UNI\Uni-2026\Semester Two\EEET4001\FrothMV-System\src\run_single_image.py", line 67, in <module>
    main()
  File "C:\Users\bgyu5\OneDrive\Documents\UNI\Uni-2026\Semester Two\EEET4001\FrothMV-System\src\run_single_image.py", line 54, in main
    metrics = pipeline.process_image(
              ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bgyu5\OneDrive\Documents\UNI\Uni-2026\Semester Two\EEET4001\FrothMV-System\src\mv\pipeline.py", line 96, in process_image
    raise FileNotFoundError(
FileNotFoundError: Image not found: does_not_exist.png
```

After:

```text
ERROR: Image not found: does_not_exist.png
```

- Folder runner correctly ignore txt file amongst images 
- Corrupt-image handling: PASS. A deliberately invalid .png file was detected as unreadable by OpenCV. The error was logged for that image only, while the remaining valid images were processed successfully and batch CSV/JSON outputs were still generated.
- i.e. one bad input does not terminate the entire batch

### Regression Validation

Reference:

`results/yolo_experiments_v2/conf015_area10/predicted_metrics.csv`

Comparison dataset:

40-image fixed test subset.

- Copied 40 test images from manifest into dataset/pipeline_validation_images for this validation
- Renamed initial 5 image folder test to 'pipeline_results_initial5folder' and then ran python src/run_folder_pipeline.py dataset/pipeline_validation_images
- All 40 images were successfully processed, result was renamed to 'pipeline_validation_results'
- Manually compared the four main metrics in: 'results\pipeline_runs\pipeline_validation_results.csv' to 'results/yolo_experiments_v2/conf015_area10/predicted_metrics.csv'
- Results were identical based on number of decimal places shown, confirming refactor of processing into pipeline did not change method:

Results:

- Bubble-count maximum difference: 0
- Mean-area maximum difference: 0/negligible
- Mean-ECD maximum difference: 0/negligible
- Mean-circularity maximum difference: 0/negligible

### Processing Performance

- Performed a second proper performance run using consolidated code to check processing time remains consistent:

- Test images: 40
- Run 1 average processing time: 2.028 s/image (from above run)
- Run 2 average processing time: 1.804 s/image
- Mean processing time: ~1.916 s/image
- Week 3 reference: ~1.847 s/image 

### Conclusion

The consolidated `FrothMVPipeline` reproduces the selected experimental soft-sensor outputs and is suitable as the standard MV interface for subsequent industrial communication integration.



## Session 2 – MV / OPC-UA Integration

### Purpose

Integrate the validated FrothMVPipeline with a reusable OPC-UA communication layer while maintaining separation between machine-vision processing and industrial communications.

### Architecture

Image/folder
→ FrothMVPipeline.process_image()
→ structured metrics dictionary
→ FrothOPCUAServer.update_metrics()
→ OPC-UA nodes
→ UaExpert / future EAE client

### OPC-UA Configuration

Endpoint:
`opc.tcp://0.0.0.0:4841/froth-test/`

Namespace:
`http://froth.project/test`

### Nodes

| Variable          | Type    | NodeId      | Direction    |
| ----------------- | ------- | ----------- | ------------ |
| `BubbleCount`     | Int32   | `ns=2;i=2`  | Python → EAE |
| `MeanECD`         | Double  | `ns=2;i=3`  | Python → EAE |
| `TestHeartbeat`   | Int32   | `ns=2;i=4`  | Python → EAE |
| `CommandFromEAE`  | Boolean | `ns=2;i=5`  | EAE → Python |
| `MeanArea`        | Double  | `ns=2;i=6`  | Python → EAE |
| `MeanCircularity` | Double  | `ns=2;i=7`  | Python → EAE |
| `ProcessingTime`  | Double  | `ns=2;i=8`  | Python → EAE |
| `PipelineOK`      | Boolean | `ns=2;i=9`  | Python → EAE |
| `PipelineStatus`  | String  | `ns=2;i=10` | Python → EAE |


### Validation

- OPC-UA server started successfully
- UaExpert connected successfully
- heartbeat incremented
- BubbleCount updated from real MV pipeline
- MeanECD updated
- MeanArea updated
- MeanCircularity updated
- ProcessingTime updated
- PipelineStatus updated
- CommandFromEAE changed successfully from UaExpert
- Python detected command changes
- heartbeat remained responsive during inference

### Conclusion

The validated FrothMVPipeline has been successfully decoupled from and integrated with a reusable OPC-UA communication layer. The Python side is ready for EAE OPC-UA client integration.



## Session 3 – MV Outputs Integrated into EAE

### Purpose

Extend the previously validated Python → EAE OPC UA heartbeat test to transfer actual FrothMV soft-sensor outputs into EcoStruxure Automation Expert.

### Architecture

Image
→ FrothMVPipeline
→ Python asyncua server
→ OPC UA
→ EAE OPCUA_READ
→ supervisory variables

### Read Variables

| Variable | NodeId | EAE Type |
|---|---|---|
| BubbleCount | ns=2;i=2 | DINT |
| MeanECD | ns=2;i=3 | LREAL |
| TestHeartbeat | ns=2;i=4 | DINT |
| MeanArea | ns=2;i=6 | LREAL |
| MeanCircularity | ns=2;i=7 | LREAL |

### Checks / Observations

- No obvious communication delay beyond expected polling/inference time.
- During restart/reconnection test, Connect Function Block indicates temporary 'reconnecting' status and when Python server is restarted it automatically reconnects/polls

### Validation

- OPCUA_CONNECT status: connected
- Connection error: 0
- Heartbeat polling: PASS
- BubbleCount polling: PASS
- MeanECD polling: PASS
- MeanArea polling: PASS
- MeanCircularity polling: PASS
- EAE values matched Python/UaExpert values for selected images
- MV metrics changed sequentially as new images were processed
- Communication remained stable during inference

### Composite Function Block Development

To simplify the EAE application and avoid exposing the individual OPC UA communication blocks throughout the supervisory logic, the working OPCUA_CONNECT and OPCUA_READ structure was encapsulated into a reusable composite function block.

The composite contains:

- one OPCUA_CONNECT block;
- separate OPCUA_READ blocks for:
  - TestHeartbeat
  - BubbleCount
  - MeanECD
  - MeanArea
  - MeanCircularity;
- internal event and data wiring required to initialise the connection and start polling.

The composite exposes the following OutputVars:

- Heartbeat : DINT
- BubbleCount : DINT
- MeanECD : LREAL
- MeanArea : LREAL
- MeanCircularity : LREAL
- Connected : BOOL
- CommsError : DINT

Connected is linked to the internal OPCUA_CONNECT.QO output and CommsError to OPCUA_CONNECT.ERROR.

During testing, the internal OPCUA_READ.VALUE1 values updated correctly, but the composite outputs initially remained at zero because the polling reads did not generate a recurring output event. START_CNF only confirmed polling startup and CNF did not fire cyclically.

This was resolved by adding an internal E_CYCLE block with a periodic trigger of approximately 1 s. Its EO event drives a composite DATA_UPDATED output event, with the exposed data outputs associated using WITH relationships. This causes the latest internal OPC UA values to be propagated through the composite interface at regular intervals.

After this change, all exposed MV and heartbeat values updated correctly, confirming the composite as a functional reusable OPC UA acquisition interface for subsequent supervisory logic and HMI development.

### Conclusion

The validated FrothMV soft-sensor pipeline has now been integrated through OPC UA into the EAE supervisory environment.





