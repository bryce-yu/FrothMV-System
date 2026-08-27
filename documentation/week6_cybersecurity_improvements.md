# Week 6 — Session 2: Practical Cybersecurity Improvements

**Project:** FrothMV-System  
**Date:** 27 August 2026  
**Status:** Completed successfully

## 1. Session objective

Session 2 implemented and validated a small, practical set of cybersecurity controls identified during the Session 1 assessment. The work focused on model integrity, useful startup information, OPC-UA access restrictions, controlled network exposure, and fail-safe behaviour.

This work is aligned with selected IEC 62443 and OPC-UA security principles. It does not claim full IEC 62443 compliance, certification, or production-grade OPC-UA security.

## 2. System boundary

The tested architecture was:

```text
Input images
    ↓
FrothMVPipeline / YOLOv8-seg
    ↓
Python OPC-UA server
    ↓
EAE MV_OPCUA_ACQUISITION
    ↓
EAE MV_SUPERVISORY_STATUS
    ↓
MV_SOFT_SENSOR / CAT HMI
```

The system remains a supervisory monitoring prototype. It does not perform closed-loop process control.

## 3. Files involved

| File | Purpose |
|---|---|
| `tests/run_opcua_pipeline.py` | Starts the pipeline, verifies the model, processes images and starts OPC-UA communication |
| `src/mv/model_integrity.py` | Calculates and verifies the model SHA-256 hash |
| `models/best.pt.sha256` | Stores the trusted hash for `models/best.pt` |
| `src/communication/opcua_server.py` | Creates OPC-UA nodes, publishes values and controls node permissions |
| `tests/test_model_integrity.py` | Tests matching, mismatching and missing model/hash files |

## 4. Model-integrity control

A SHA-256 reference was generated for the known-good model:

```text
models/best.pt
models/best.pt.sha256
```

At startup, `run_opcua_pipeline.py` now:

1. creates the validated `MVConfig`;
2. starts the OPC-UA server and diagnostic status nodes;
3. verifies the model against `models/best.pt.sha256`;
4. creates `FrothMVPipeline` only after verification succeeds;
5. prevents inference when verification fails.

The model configuration remains frozen at:

| Parameter | Value |
|---|---:|
| Model | `models/best.pt` |
| Confidence | `0.15` |
| Image size | `640` |
| Maximum detections | `1000` |
| Minimum contour area | `10.0 px²` |

### Failure behaviour

When the model hash is invalid or the model cannot be verified:

```text
PipelineOK = FALSE
MV_DataValid = FALSE
No image inference is performed
```

The OPC-UA server remains available for diagnostics where possible, allowing the failure to be distinguished from a completely unavailable server.

### Integrity limitation

The hash detects accidental or unauthorised changes to the model when the trusted reference is protected. It does not prove who created the model. A production deployment would require stronger protection of the reference value, such as signed releases or a protected integrity store.

## 5. Startup logging and output control

Startup information was added for:

- model path;
- active MV configuration;
- model verification result;
- OPC-UA endpoint;
- current OPC-UA security posture;
- pipeline startup failure.

Routine `asyncua` protocol messages were suppressed by changing the logging level from `INFO` to `WARNING`. This prevents repetitive messages such as publish acknowledgements and read requests from filling the terminal while retaining warnings and errors.

Normal per-image diagnostic output was also reduced where required. Security and processing failures remain visible.

The current development OPC-UA security posture is logged and documented as:

```text
Security Policy: None
Message Security Mode: None
Authentication: Anonymous
```

This remains acceptable only for the isolated development/interoperability test environment.

## 6. OPC-UA access-control review

`CommandFromEAE` is the only intentionally writable node:

```python
await self.nodes["CommandFromEAE"].set_writable()
```

The published measurements and status values are not made writable by clients. These include:

- `BubbleCount`;
- `MeanECD`;
- `MeanArea`;
- `MeanCircularity`;
- `MedianECD`;
- `ECD_P10`;
- `ECD_P90`;
- `ProcessingTime`;
- `PipelineOK`;
- `PipelineStatus`;
- `TestHeartbeat`.

Python continues to update these values internally using server-side writes. External clients cannot modify the measurement values.

## 7. Network-exposure review

The server currently uses:

```text
opc.tcp://0.0.0.0:4841/froth-test/
```

This permits listening on all local network interfaces so that the validated EAE connection can operate. The endpoint was not exposed to the public internet.

For a future deployment, the endpoint should be restricted to the required network interface and firewall source addresses. Port `4841` should only be accessible to authorised EAE or test clients. The future Modbus TCP conduit on port `502` should receive equivalent restrictions.

## 8. Tests performed

### 8.1 Unit tests

The model-integrity tests successfully covered:

- SHA-256 calculation;
- matching model and trusted hash;
- mismatching model and trusted hash;
- missing model file.

The complete project test suite also passed:

```bash
python -m pytest -v
```

### 8.2 Correct-model startup

With the original `models/best.pt` and correct trusted hash:

- model verification passed;
- `FrothMVPipeline` loaded successfully;
- image processing continued normally;
- metrics were published through OPC-UA;
- heartbeat updates continued;
- EAE received the measurements;
- `PipelineOK` and `MV_DataValid` became valid after successful processing;
- the CAT HMI path remained operational.

### 8.3 Altered trusted-hash test

The trusted hash was temporarily altered without modifying the actual model file.

Expected and observed behaviour:

| Item | Result |
|---|---|
| Hash verification | Failed safely |
| Model inference | Prevented |
| `PipelineOK` | `FALSE` |
| `MV_DataValid` | `FALSE` |
| Normal valid measurement | Not published as valid |

The original trusted hash was restored after the test.

### 8.4 External OPC-UA write test

An external client attempted to write to published measurement/status nodes.

| Node category | Result |
|---|---|
| Measurement nodes | Write rejected |
| `PipelineOK` and status nodes | Write rejected |
| `CommandFromEAE` | Remained writable as intentionally designed |
| Python internal updates | Continued to work |

### 8.5 Existing robustness tests

The previously validated tests were repeated successfully:

- valid image processing;
- five-image processing;
- corrupt image handling;
- stopped heartbeat;
- Python server restart;
- OPC-UA reconnection;
- EAE/HMI value and status validation.

The expected status behaviour remained:

```text
MV_DataValid = MV_CommsOK AND MV_HeartbeatOK AND PipelineOK
```

### 8.6 Transient OPC-UA session warning

During server/client restart testing, the following message appeared briefly:

```text
BadSessionIdInvalid
```

This occurred while a client attempted to use an old OPC-UA session during reconnection. The session recovered, measurements continued updating, and no persistent effect on the tests was observed.

This is recorded as a transient development-runtime reconnection event, not as a persistent pipeline failure. In a production system, repeated or unrecovered session errors would require investigation because they could interrupt data availability.

## 9. Results against Session 2 objectives

| Objective | Status | Evidence |
|---|---|---|
| Verify `best.pt` integrity | Completed | SHA-256 utility, reference file and mismatch test |
| Prevent use of altered model | Completed | Failed-hash test and `PipelineOK = FALSE` |
| Record important startup information | Completed | Startup logging |
| Suppress excessive routine logging | Completed | `asyncua` INFO messages suppressed |
| Restrict measurement-node writes | Completed | External write attempts rejected |
| Review OPC-UA endpoint exposure | Completed | Endpoint and development limitation documented |
| Preserve existing MV/EAE behaviour | Completed | Regression and robustness tests passed |

## 10. Remaining limitations and future work

The following items were considered but intentionally not fully implemented during this session:

- OPC-UA application certificates;
- `Sign` or `SignAndEncrypt` message security;
- removal of anonymous authentication;
- protected certificate private keys and trust-list management;
- physical IT/OT network segmentation;
- formal IEC 62443 risk assessment and security-level assignment;
- hardware/IPC and physical PLC hardening.

These are future deployment requirements rather than necessary controls for the isolated local prototype.

## 11. Conclusion

Session 2 successfully added practical cybersecurity evidence to the FrothMV-System. The project now detects model changes before inference, prevents external modification of published measurements, records its security posture and startup configuration, and preserves invalid-data behaviour when integrity or communication problems occur.

The work demonstrates cybersecurity-informed system design while keeping the scope appropriate for a local supervisory open-architecture prototype.
