# Week 4 – Final Integration and Robustness Validation

## Session 4 – Supervisory Status Logic

Following successful validation of the Python machine-vision pipeline and Python-to-EAE OPC-UA communication, a supervisory status layer was added above the existing OPC-UA acquisition composite.

A second reusable EAE composite function block was created:

`MV_SUPERVISORY_STATUS`

Its purpose is to interpret lower-level communication and pipeline signals and expose higher-level system health indicators for future HMI and supervisory use.

The main inputs are:

```text
Connected
CommsError
Heartbeat
PipelineOK
```

The main outputs are:

```text
MV_CommsOK
MV_HeartbeatOK
MV_DataValid
```

### Communication Status

`MV_CommsOK` is derived from the OPC-UA acquisition status:

```text
MV_CommsOK =
    Connected
    AND
    (CommsError = 0)
```

This distinguishes a successfully established OPC-UA connection from a connection reporting an error condition.

### Heartbeat Watchdog

A dedicated Basic FB was created to monitor the Python-side heartbeat.

The watchdog compares the current heartbeat against the previously received heartbeat once per supervisory update cycle.

If the heartbeat changes:

```text
MV_HeartbeatOK = TRUE
StaleCount = 0
```

If the heartbeat remains unchanged, the stale counter is incremented. After five consecutive stale checks:

```text
MV_HeartbeatOK = FALSE
```

The watchdog therefore provides an application-level liveness check independent of the OPC-UA connection itself.

This allows the supervisory layer to distinguish between:

```text
OPC-UA connection healthy
```

and:

```text
Python application actively updating
```

### Overall Data Validity

The final supervisory validity state is calculated as:

```text
MV_DataValid =
    MV_CommsOK
    AND
    MV_HeartbeatOK
    AND
    PipelineOK
```

This means MV measurements are considered valid only when:

* OPC-UA communication is healthy;
* the Python heartbeat is actively changing; and
* the most recent MV processing operation completed successfully.

The internal execution sequence is event-driven and ordered so that each status is refreshed before `MV_DataValid` is evaluated:

```text
Supervisory update event
        ↓
CommsError comparison
        ↓
MV_CommsOK
        ↓
Heartbeat watchdog
        ↓
MV_HeartbeatOK
        ↓
MV_DataValid
        ↓
STATUS_UPDATED
```

The supervisory composite is triggered from the recurring `DATA_UPDATED` event of the OPC-UA acquisition composite.

---

## Session 5 – Pipeline Failure Handling

Robustness testing identified an issue in the Python OPC-UA runner when an invalid image appeared after a previously successful image.

Originally, if an image failed during processing, the runner only printed the exception:

```text
ERROR: <image>: <exception>
```

No new pipeline failure state was published to OPC-UA.

As a result, if a valid image had already been processed, the OPC-UA nodes retained:

```text
PipelineOK = TRUE
```

together with the previous valid measurement values.

This caused EAE to continue reporting:

```text
MV_DataValid = TRUE
```

even though the current image-processing attempt had failed.

A new failure-update method was therefore added to `FrothOPCUAServer`.

On a processing exception, the server now publishes:

```text
PipelineOK = FALSE
PipelineStatus = processing error description
```

while intentionally retaining the previous valid MV measurements.

This produces the following behaviour:

```text
Valid image
    ↓
new metrics published
PipelineOK = TRUE
MV_DataValid = TRUE

Corrupt image
    ↓
previous metrics retained
PipelineOK = FALSE
MV_DataValid = FALSE

Next valid image
    ↓
new metrics published
PipelineOK = TRUE
MV_DataValid = TRUE
```

Retaining the previous measurements was preferred to forcing the values to zero, because zero may itself represent a legitimate measurement. The `MV_DataValid` signal instead indicates whether the displayed or retained values should currently be trusted.

---

## Robustness Validation

A series of integration robustness checks were performed across the Python and EAE layers.

### Normal Operation

During normal operation:

```text
Connected        = TRUE
CommsError       = 0
MV_CommsOK       = TRUE
MV_HeartbeatOK   = TRUE
PipelineOK       = TRUE
MV_DataValid     = TRUE
```

Machine-vision metrics were successfully transferred from Python through OPC-UA into the EAE acquisition composite.

### Invalid / Corrupt Image

A deliberately invalid `.png` file was inserted into the processing folder.

The Python MV pipeline correctly rejected the image and the updated failure-handling logic propagated the error state through OPC-UA.

The expected supervisory behaviour was observed:

```text
MV_CommsOK       = TRUE
MV_HeartbeatOK   = TRUE
PipelineOK       = FALSE
MV_DataValid     = FALSE
```

The OPC-UA server and heartbeat remained active, correctly indicating that communication was healthy while the MV processing result itself was invalid.

A subsequent valid image restored:

```text
PipelineOK       = TRUE
MV_DataValid     = TRUE
```

confirming that the pipeline can recover automatically following an individual image-processing failure.

### Heartbeat Stale Test

The Python heartbeat task was temporarily disabled while leaving the OPC-UA server running.

This created a condition where communication remained available but the application heartbeat stopped changing.

The expected state was observed:

```text
MV_CommsOK       = TRUE
MV_HeartbeatOK   = FALSE
PipelineOK       = TRUE
MV_DataValid     = FALSE
```

This validates the purpose of the heartbeat watchdog: a functioning OPC-UA connection alone is not sufficient to consider the MV data current.

If the heartbeat becomes stale, EAE marks the data invalid even though the server remains connected.

### Communication Loss / Recovery

The Python OPC-UA server was stopped during EAE operation to observe system behaviour under communication loss.

The supervisory indicators responded to the loss of communication, allowing the acquisition and application-health states to be distinguished from normal operation.

The server was subsequently restarted and communication behaviour was observed to verify recovery of the Python-to-EAE data path.

These tests provide evidence that the supervisory architecture can distinguish between:

```text
Communication failure
Application heartbeat failure
Machine-vision processing failure
Normal operation
```

rather than representing all faults using a single generic status.

---

## HMI Development Status

Initial work was also performed on an EAE CAT-based HMI implementation.

CAT versions of the acquisition and supervisory composites were created, and an HMI service/faceplate was added.

The HMI service FB successfully receives live application values. When observed online in EAE, inputs such as:

```text
BubbleCount
MeanECD
MeanArea
MeanCircularity
ProcessingTime
```

update correctly.

The HMI faceplate was also added to a canvas and Local HMI could be started successfully.

However, the displayed faceplate values currently remain at their default zero values despite the corresponding HMI FB inputs updating correctly.

Several possible causes were investigated, including:

* HMI `DISPLAY` event operation;
* event/data `WITH` associations;
* CAT HMI input mappings;
* symbolic links;
* HMI attributes;
* Local HMI runtime connection state.

The `DISPLAY` event was confirmed to be firing, and the HMI FB input values were confirmed to be correct.

Therefore, the unresolved issue is considered to be within the HMI faceplate/runtime binding layer rather than the machine-vision, OPC-UA, acquisition, or supervisory logic.

The HMI issue has therefore been recorded as an outstanding integration item and is not considered a blocker for validating the Week 4 communication and supervisory architecture.

---

## Remaining Portability Check

Earlier OPC-UA communication testing was successfully reproduced on both development laptops, with only the Python server IP requiring modification.

However, the newly completed supervisory and robustness configuration has not yet been fully repeated on the second laptop.

A short end-to-end portability check remains desirable:

```text
Second laptop
    ↓
update Python OPC-UA endpoint/IP
    ↓
start Python MV server
    ↓
deploy EAE application
    ↓
verify acquisition values
    ↓
verify supervisory status values
```

This can be performed as a brief follow-up check without reopening the core Week 4 implementation work.

---

## Final Week 4 Architecture

The system at the end of Week 4 is:

```text
Froth image
    ↓
FrothMVPipeline
YOLOv8-seg + contour metrics
    ↓
FrothOPCUAServer
    ↓
OPC-UA
    ↓
MV_OPCUA_ACQUISITION
    ↓
BubbleCount
MeanECD
MeanArea
MeanCircularity
ProcessingTime
PipelineOK
Connected
CommsError
Heartbeat
    ↓
MV_SUPERVISORY_STATUS
    ↓
MV_CommsOK
MV_HeartbeatOK
MV_DataValid
    ↓
future HMI / supervisory application
```

The primary supervisory data path remains read-only:

```text
Python → EAE
```

EAE-to-Python command functionality remains optional and is not required for the current supervisory system.

---

## Week 4 Outcome

Week 4 successfully progressed the project from a validated standalone machine-vision pipeline to an integrated and monitored industrial communication architecture.

The following objectives are now complete:

* consolidated MV pipeline validated against the selected Week 3 method;
* Python OPC-UA publishing layer implemented;
* real MV outputs successfully transferred into EAE;
* OPC-UA acquisition logic encapsulated in a reusable EAE composite FB;
* supervisory communication, heartbeat and data-validity logic implemented;
* machine-vision processing failures propagated correctly through OPC-UA;
* corrupt-image recovery validated;
* heartbeat-loss behaviour validated independently from communication health;
* communication-loss behaviour tested;
* last-valid measurement behaviour established;
* core Python-to-EAE supervisory data path validated.

The remaining minor items are:

```text
1. Resolve CAT HMI faceplate value binding.
2. Repeat a short final end-to-end check on the second development laptop.
```

Neither item changes the validated core machine-vision, OPC-UA or supervisory architecture.

Week 4 can therefore be considered substantially complete, with the project ready to progress into Week 5 work on soft-sensor feature interpretation and the meaning/use of the extracted froth measurements.
