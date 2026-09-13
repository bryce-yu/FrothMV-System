# Week 8 – Session 4: Input Validation and Security Logging

**Date:** 13 September 2026  
**System:** FrothMV supervisory soft-sensor  
**Session focus:** Image-input validation, fail-safe supervisory behaviour and persistent security-relevant logging

---

## 1. Session objectives

The objectives of this session were to:

- establish the expected characteristics of the current validation-image dataset;
- reject missing, unsupported, empty, oversized, corrupt or incorrectly dimensioned image inputs before inference results could be published;
- confirm that rejected inputs produced a safe invalid state in EAE without falsely indicating a communications failure;
- confirm automatic recovery when the next valid image was processed;
- add persistent, bounded log-file storage for security-relevant and operational events;
- record successful per-image publication without unnecessarily duplicating every result in the terminal; and
- retain test evidence while removing temporary negative-test inputs from the working dataset.

This work supports selected IEC 62443 principles relating to system integrity, input validation, event logging, least functionality and resource availability. It does not constitute IEC 62443 compliance, certification or achievement of a formal security level.

---

## 2. Initial assessment

### 2.1 Repository state

The session began from a clean Git working tree at:

```text
4df6d53 Restrict OPC-UA network exposure and verify firewall controls
```

This provided a known baseline following the Session 3 network-hardening work.

### 2.2 Validation-image baseline

The initial validation folder contained 41 files, all with a `.png` extension.

| Characteristic | Observed value |
|---|---:|
| Total files | 41 |
| Valid readable images | 40 |
| Deliberately corrupt images | 1 |
| Valid image dimensions | `800 × 600` pixels |
| Minimum file size | `0` bytes, caused by the corrupt test image |
| Maximum observed file size | `790,942` bytes |
| Average file size | Approximately `620,375` bytes |

The deliberately corrupt file was:

```text
F5_2_1_2-corrupt.png
```

OpenCV returned no decoded image for this zero-byte file. The file was retained as a repeatable negative-test input rather than treated as normal process data.

### 2.3 Initial logging state

No `logs` directory existed at the start of the session. The Python application used console-oriented logging and did not retain a persistent application event history between runs.

---

## 3. Image-input validation controls

The image validation policy was defined in `src/mv/config.py` using the following prototype-specific limits:

| Validation property | Configured value |
|---|---|
| Permitted extension | `.png` |
| Maximum file size | `2,097,152` bytes (`2 MiB`) |
| Expected width | `800` pixels |
| Expected height | `600` pixels |

The existing `MVConfig` validation was extended so that the application also rejects invalid configuration values, including:

- an empty image-extension allow-list;
- non-positive maximum file size; and
- non-positive expected image dimensions.

These parameters are configuration values rather than being embedded directly into the inference logic. They can therefore be deliberately updated if the approved image source or deployment requirements change.

### 3.1 Processing checks

The `process_image` path in `src/mv/pipeline.py` was extended to check each input before its measurements could be published. The implemented checks cover:

1. the path exists;
2. the path represents a regular file;
3. the file extension is on the configured allow-list;
4. the file is not empty;
5. the file does not exceed the configured byte limit;
6. OpenCV can decode the image; and
7. the decoded dimensions exactly match the expected `800 × 600` pixels.

If any check fails, an exception is raised for that image. Inference and measurement publication are not performed for the rejected input.

### 3.2 File discovery behaviour

The image-file enumeration in `src/run_opcua_pipeline.py` was changed to pass all regular files in the selected folder to the pipeline validation logic.

This prevents unsupported files from being silently ignored. An unexpected extension is now explicitly rejected and recorded, making the behaviour visible to the operator and in the retained log.

---

## 4. Fail-safe supervisory behaviour

The existing image-processing exception path was retained and used to notify the OPC-UA layer of a pipeline failure. A rejected input therefore does not produce apparently valid measurements.

During a rejected-image condition, EAE showed the following state:

| Supervisory signal | Observed state | Interpretation |
|---|---:|---|
| `CommsOK` | `TRUE` | The secured OPC-UA connection remained available |
| `HeartbeatOK` | `TRUE` | The Python server remained responsive |
| `PipelineOK` | `FALSE` | The image-processing operation failed validation |
| `MV_DataValid` / `DataValid` | `FALSE` | Measurements were not valid for supervisory use |
| `CollatedResultValid` | `FALSE` | The combined EAE/CE result was not valid |

This distinction is important because the system identifies an input or processing failure without incorrectly reporting that the OPC-UA conduit itself has failed.

When the next valid image was processed, normal measurement publication resumed and the EAE validity indicators recovered automatically. The system therefore failed safely for the affected input without requiring a full server restart.

---

## 5. Negative testing

### 5.1 Empty/corrupt image

The retained zero-byte PNG produced the explicit terminal rejection:

```text
[23/41] ERROR: F5_2_1_2-corrupt.png: Image file is empty: dataset\pipeline_validation_images\F5_2_1_2-corrupt.png
```

Expected and observed behaviour:

- the image was not passed to inference;
- the Python process and OPC-UA server remained running;
- the EAE communication and heartbeat indications remained healthy;
- pipeline and data-valid indications became false; and
- processing recovered on the following valid image.

### 5.2 Oversized PNG

A temporary PNG was created with a size one byte above the configured limit. It was rejected with:

```text
Image file exceeds the configured size limit (2097153 > 2097152 bytes)
```

This demonstrated enforcement at the configured boundary of `2 MiB`.

### 5.3 Unsupported extension

A temporary `.txt` file was placed in the image folder. It was discovered by the folder runner and explicitly rejected with:

```text
Unsupported image extension '.txt'
```

This confirmed that an unexpected regular file is reported rather than silently skipped or passed to the decoder.

### 5.4 Incorrect dimensions

A valid PNG with dimensions `640 × 480` was created for testing. It was decoded successfully but rejected with:

```text
Unexpected image dimensions 640x480; expected 800x600
```

This separated the dimension check from the corrupt-file check and demonstrated that a technically valid PNG is still rejected if it does not match the approved source characteristics.

### 5.5 Test cleanup

Evidence was captured for the oversized, unsupported-extension and wrong-dimension tests. These three temporary files were then removed from the validation folder.

The original zero-byte corrupt image was retained as the established repeatable pipeline-failure test. After cleanup, the folder returned to 41 files: 40 valid images and the retained corrupt test image.

---

## 6. Persistent application logging

Persistent logging was added to `src/run_opcua_pipeline.py` using Python's rotating file-handler support.

The active log file is:

```text
logs/froth_mv_pipeline.log
```

The logging arrangement uses bounded rotation so the active log does not grow indefinitely. The implemented configuration uses an approximately 1 MB active-file limit and retains up to three backup files.

The `logs/` directory was excluded from Git so runtime records are not unintentionally committed to the source repository. Test evidence can instead be copied deliberately to the selected evidence location when required.

### 6.1 Append and rotation behaviour

The active log uses append behaviour. Restarting the pipeline does not normally overwrite the existing log; a new timestamped startup sequence is added to the existing file.

When the active file reaches its configured size limit, rotation renames older files and begins a new active log. The configured backup count bounds the retained local history.

The file can technically be cleared manually while the pipeline is stopped, but evidence should be copied elsewhere before clearing it.

### 6.2 Events retained

The log records the following information:

- model path and frozen MV configuration;
- approved image-input validation configuration;
- OPC-UA endpoint;
- enabled OPC-UA security policy and message-security mode;
- requirement for username/password authentication and disabled anonymous access;
- successful model SHA-256 verification and verified digest;
- successful pipeline startup;
- accepted OPC-UA authentication events;
- asyncua warnings and errors, including the known transient `BadSessionIdInvalid` event;
- rejected-image filename and rejection reason; and
- successful per-image result publication, including filename, status, bubble count and processing time.

Passwords, private-key contents and other secret values are not written to the application log.

### 6.3 Example rejected-image record

```text
ERROR | Image processing rejected: file=dataset\pipeline_validation_images\F5_2_1_2-corrupt.png, reason=Image file is empty: dataset\pipeline_validation_images\F5_2_1_2-corrupt.png
```

### 6.4 Example successful-publication record

```text
INFO | Published MV result: file=F5_1_1_1.ts-frames_frame-1105.png, status=OK, bubble_count=203, processing_time_seconds=6.322
```

The successful-publication records are generated through a dedicated results logger. This logger writes to the rotating log file with propagation disabled, so the detailed record is retained without duplicating it in the terminal.

The terminal continues to display the existing concise progress line, for example:

```text
[1/41] F5_1_1_1.ts-frames_frame-1105.png: BubbleCount=203, ... ProcessingTime=6.322s
```

Startup, security, authentication and rejection/error events remain visible according to their existing logger configuration.

### 6.5 Append verification

The pipeline was run more than once and the log was inspected using:

```powershell
Get-Content logs\froth_mv_pipeline.log -Tail 30
```

The output contained separate timestamped startup sequences from both runs. This confirmed that the application appends to the active log rather than replacing it on each normal restart.

The final check also confirmed that `Published MV result` entries remained present in the file but no longer appeared as duplicate timestamped entries in the terminal.

---

## 7. Verification summary

| Verification item | Expected result | Observed result | Outcome |
|---|---|---|---|
| Valid `800 × 600` PNG | Process and publish measurements | Python and EAE operated normally | Pass |
| Empty/corrupt PNG | Reject without publishing valid data | Explicit empty-file error; validity became false | Pass |
| Oversized PNG | Reject above `2 MiB` | `2,097,153`-byte file rejected | Pass |
| Unsupported `.txt` file | Explicitly reject | Unsupported-extension error generated | Pass |
| `640 × 480` PNG | Reject incorrect dimensions | Expected/actual dimensions reported | Pass |
| OPC-UA availability during bad input | Remain connected | `CommsOK` and `HeartbeatOK` remained true | Pass |
| Pipeline validity during bad input | Indicate invalid | `PipelineOK`, data validity and collated validity became false | Pass |
| Recovery on next valid image | Resume normal publication | Validity and measurements recovered | Pass |
| Persistent log | Retain events across restart | Two timestamped runs present | Pass |
| Rejection logging | Record filename and reason | Corrupt-image rejection retained | Pass |
| Successful-publication logging | Retain one record per valid image | Records present in file | Pass |
| Terminal separation | Avoid duplicate detailed result logs | Detailed result records absent from terminal | Pass |
| Temporary test cleanup | Remove generated negative-test files | Oversized, `.txt` and wrong-dimension files removed | Pass |

---

## 8. Cybersecurity checklist update

| Checklist control | Status after Session 4 |
|---|---|
| Define approved image extensions | ✓ Implemented |
| Reject zero-byte inputs | ✓ Implemented and tested |
| Reject oversized image files | ✓ Implemented and tested |
| Reject undecodable/corrupt images | ✓ Implemented and tested |
| Enforce expected source dimensions | ✓ Implemented and tested |
| Prevent invalid measurements being marked valid | ✓ Demonstrated in EAE |
| Recover automatically after a subsequent valid input | ✓ Demonstrated |
| Retain startup and security configuration events | ✓ Implemented |
| Retain authentication and communication events | ✓ Implemented |
| Retain rejected-input filename and reason | ✓ Implemented |
| Retain per-image publication records | ✓ Implemented |
| Bound application-log growth | ✓ Implemented using rotation |
| Keep generated logs outside source control | ✓ Implemented |
| Forward logs to a protected central collector | ☐ Not implemented; future deployment task |
| Protect logs against modification by the local user | ☐ Not implemented beyond normal host access controls |

---

## 9. Risk treatment update

The Session 4 controls reduced the likelihood or impact of:

- unsupported files being silently ignored or unexpectedly processed;
- empty or corrupt files reaching the inference stage;
- unusually large inputs consuming unnecessary processing resources;
- measurements from an unexpected image geometry being treated as valid process information;
- input failures being confused with an OPC-UA communications outage;
- operational or security-relevant events being lost when the terminal closes; and
- unbounded growth of the active application log.

The changes complement earlier Week 8 controls:

- Session 1 reduced exposed functionality and strengthened validity handling;
- Session 2 added signed and encrypted OPC-UA communication, certificate-based server identity and username/password authentication;
- Session 3 restricted the OPC-UA listener and Windows Firewall conduit; and
- Session 4 strengthened input integrity and event traceability.

Residual risks include:

- the `800 × 600`, `.png` and `2 MiB` limits are appropriate for the current prototype dataset but must be reviewed for a different approved image source;
- file-size validation limits encoded input size but is not a complete defence against every decoder or decompression resource-exhaustion scenario;
- OpenCV and other image-processing dependencies still require normal patch and vulnerability-management practices;
- logs are local to the development laptop and are not centrally collected, cryptographically signed or protected from an authorised local user;
- the retained log history is limited by the configured rotation size and backup count;
- the deliberately corrupt image remains in the test dataset and should not be confused with production input;
- dependency vulnerability auditing remains deferred from Session 3; and
- the prototype remains a supervisory demonstration rather than a safety-rated or closed-loop control system.

---

## 10. Evidence retained

Recommended Session 4 evidence includes:

1. Initial dataset extension, file-size and dimension checks.
2. Output identifying `F5_2_1_2-corrupt.png` as unreadable.
3. Normal Python and EAE operation with valid images.
4. Corrupt-image terminal rejection and EAE invalid-state screenshot.
5. Oversized PNG rejection at `2,097,153` bytes.
6. Unsupported `.txt` rejection.
7. Incorrect-dimension `640 × 480` PNG rejection.
8. Confirmation that normal processing continued after each rejected input.
9. Persistent log showing startup, OPC-UA security configuration and model-integrity verification.
10. Persistent log showing accepted authentication and the known non-fatal `BadSessionIdInvalid` event.
11. Persistent log showing the corrupt-image filename and rejection reason.
12. Persistent log containing per-image successful-publication records.
13. Terminal output confirming that detailed publication records are no longer duplicated there.
14. Git status or folder listing confirming removal of the three temporary negative-test files before commit.

Any retained log evidence should be reviewed before sharing to ensure it does not unnecessarily disclose usernames, host paths, addresses or other environment information.

---

## 11. Files changed

| File | Purpose of change |
|---|---|
| `src/mv/config.py` | Added approved extension, maximum file size and expected image-dimension configuration and validation |
| `src/mv/pipeline.py` | Added path, file type, extension, size, decode and dimension checks |
| `src/run_opcua_pipeline.py` | Made unexpected regular files visible to validation; added rejection and publication logging; configured persistent rotating logs and file-only detailed result records |
| `.gitignore` | Excluded runtime log files/directory from source control |

Temporary negative-test files were removed after evidence capture and are not intended to be committed.

---

## 12. Session outcome

Week 8 Session 4 successfully added practical image-input integrity controls and persistent security-relevant logging to the FrothMV supervisory system.

The pipeline now accepts only the configured image type, file-size range and dimensions. Empty, corrupt, oversized, unsupported and incorrectly dimensioned inputs are explicitly rejected before their measurements can be published. Testing demonstrated that EAE continues to distinguish a pipeline/input failure from a communications failure: OPC-UA communications and the heartbeat remain healthy while the pipeline, measurement and collated-result validity indicators become false. Normal operation then recovers on the next valid image.

Persistent rotating logs now retain startup configuration, OPC-UA security status, model-integrity verification, authentication events, communication errors, input-rejection reasons and successful measurement-publication records across application restarts. Detailed per-image publication records are written to the file without duplicating them in the terminal.

Together with the earlier Week 8 sessions, this provides a defendable set of prototype cybersecurity improvements covering asset and trust-boundary identification, reduced functionality, secured OPC-UA communication, restricted network exposure, input integrity, fail-safe validity propagation and event traceability. These controls align with selected IEC 62443 security principles but do not establish compliance, certification or a formal security level.
