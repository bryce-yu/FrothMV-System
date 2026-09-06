# FrothMV-System — Week 7 Sessions 3–4: Final Integration and Validation

## Session focus

Week 7 Sessions 3 and 4 completed the Control Expert use of the collated machine-vision validity result and performed final end-to-end validation of the bidirectional supervisory interface.

Session 3 focused on:

- converting the collated-validity word received by Control Expert into a Boolean;
- incorporating that Boolean into the final Control Expert availability decision;
- retaining the existing EAE-publication freshness check;
- adding Control Expert and overall-result indicators to the EAE HMI.

Session 4 focused on:

- normal end-to-end operation;
- Control Expert process-status changes;
- corrupt-image invalidity;
- OPC-UA interruption and recovery;
- EAE publication interruption and recovery;
- Control Expert PLC Simulator interruption and recovery;
- HMI behaviour under healthy and unavailable conditions;
- final Week 7 consolidation.

The completed system remains supervisory only. No closed-loop process control was introduced.

---

## Starting baseline

Week 7 Session 1 had established the first floating-point transfer. Python publishes `MedianECD` as an OPC-UA `Double`, EAE acquires it as an `LREAL`, converts it to a 32-bit `REAL`, and writes it across two Modbus registers. Fixed tests using `1.0` and `12.34` verified the required low-word-first representation.

Week 7 Session 2 had then established bidirectional Modbus TCP communication:

- EAE writes machine-vision measurements and statuses to Control Expert;
- EAE reads `CE_ProcessReadyWord` from Control Expert;
- `MV_CE_STATUS` interprets the received word and Modbus read health;
- `MV_SOFT_SENSOR` combines MV validity with the Control Expert status;
- EAE returns `MV_CollatedValidWord` to Control Expert.

The starting collated-validity calculation in EAE was:

```text
CollatedResultValid =
    MV_DataValid
    AND CE_ProcessReady
    AND CE_StatusReadOK
```

At the start of Session 3, Control Expert could receive `MV_CollatedValidWord` at `%MW3`, but had not yet incorporated it into the final `MV_Available` calculation.

---

## Final architecture

The validated information flow is:

```text
Images
→ Python YOLOv8-seg / FrothMVPipeline
→ OPC-UA
→ MV_OPCUA_ACQUISITION
→ MV_SUPERVISORY_STATUS
→ EAE_CE_MODBUS_EXCHANGE reads Control Expert status
→ MV_CE_STATUS
→ MV_SOFT_SENSOR aggregation and HMI
→ EAE_CE_MODBUS_EXCHANGE writes measurements and validity
→ Control Expert PLC Simulator
```

The feedback information from Control Expert is process status only. It is used to determine whether the MV result is suitable for supervisory use; it does not command or alter the segmentation algorithm and does not create a closed control loop.

---

## Final Modbus register map

| Signal | Direction | EAE Modbus type | Modbus offset(s) | Control Expert address/type | Owner |
|---|---|---|---:|---|---|
| `MV_BubbleCountWord` | EAE → CE | `UINT` | `0` | `%MW0`, `UINT` | EAE |
| `MV_DataValidWord` | EAE → CE | `UINT` | `1` | `%MW1`, `UINT` | EAE |
| `MV_UpdateCounter` | EAE → CE | `INT` | `2` | `%MW2`, `INT` | EAE |
| `MV_CollatedValidWord` | EAE → CE | `UINT` | `3` | `%MW3`, `UINT` | EAE |
| `MV_MedianECD` | EAE → CE | `REAL` | `10–11` | `%MW10`, `REAL` | EAE |
| `CE_ProcessReadyWord` | CE → EAE | `UINT` | `100` | `%MW100`, `UINT` | Control Expert |

Register ownership remains separated by direction:

| Range | Owner | Intended operation |
|---|---|---|
| Offsets `0–99` | EAE | EAE writes; Control Expert receives |
| Offsets `100–199` | Control Expert | Control Expert writes; EAE reads |

This prevents both systems from writing to the same register locations.

### REAL representation

`MV_MedianECD` is transferred using one REAL-typed `MB_WRITE_REGISTERS` block beginning at offset `10`. The block occupies offsets `10–11`.

The verified representation is:

```text
Offset 10 / %MW10 = low 16-bit word
Offset 11 / %MW11 = high 16-bit word
```

The live data path is:

```text
Python MedianECD
→ OPC-UA Double
→ EAE MedianECD : LREAL
→ LREAL_TO_REAL
→ MB_WRITE_REGISTERS VALUE1 : REAL
→ offsets 10–11
→ Control Expert MV_MedianECD : REAL at %MW10
```

---

## Application-level event flow

The final EAE event sequence is:

```text
MV_OPCUA_ACQUISITION.DATA_UPDATED
→ MV_SUPERVISORY_STATUS.REQ

MV_SUPERVISORY_STATUS.STATUS_UPDATED
→ EAE_CE_MODBUS_EXCHANGE.READ_REQ

EAE_CE_MODBUS_EXCHANGE.CE_DATA_UPDATED
→ MV_CE_STATUS.REQ

MV_CE_STATUS.CE_STATUS_UPDATED
→ MV_SOFT_SENSOR.REQ

MV_SOFT_SENSOR.COLLATED_DATA_UPDATED
→ EAE_CE_MODBUS_EXCHANGE.WRITE_REQ
```

Inside `EAE_CE_MODBUS_EXCHANGE`:

- `READ_REQ` triggers the Control Expert status read;
- `WRITE_REQ` triggers the EAE-to-Control Expert measurement and status writes.

This creates the required read–interpret–collate–write sequence and ensures that the returned collated-validity word is based on the latest completed Control Expert status read.

The existing `E_CYCLE`-driven OPC-UA acquisition arrangement was retained. The successful parallel OPC-UA read arrangement inside `MV_OPCUA_ACQUISITION` was not replaced with a sequential read chain.

---

## EAE Control Expert status interpretation

`EAE_CE_MODBUS_EXCHANGE` reads the Control Expert holding register at offset `100` using `MB_READ_REGISTERS`:

```text
QI            = TRUE
OFFSET        = 100
INPUT_TYPE    = FALSE
STATION_ID    = 1
VALUE1 type   = UINT
```

`INPUT_TYPE = FALSE` selects holding-register access for `%MW100`.

The communication composite exposes:

```text
CE_ProcessReadyWord : UINT
CE_ReadQO           : BOOL
CE_ReadError        : DINT
CE_ReadStatus       : STRING
CE_DATA_UPDATED     : event
```

The separate `MV_CE_STATUS` composite converts and interprets these raw outputs:

```text
CE_ProcessReady = CE_ProcessReadyWord <> 0

CE_StatusReadOK =
    CE_ReadQO
    AND (CE_ReadError = 0)
```

The separation means that the Modbus composite performs communication, while `MV_CE_STATUS` assigns supervisory meaning to the returned data and read diagnostics.

A previously received `CE_ProcessReady = TRUE` value may remain visible if the PLC Simulator becomes unavailable. This retained value is not trusted because `CE_StatusReadOK` becomes false and therefore forces `CollatedResultValid` false.

---

## EAE collated validity

`MV_SOFT_SENSOR` acts as the final EAE aggregation layer for the downstream HMI and Control Expert interface.

Its relevant inputs are:

```text
DataValid_IN        : BOOL
CE_ProcessReady_IN  : BOOL
CE_StatusReadOK_IN  : BOOL
```

The implemented calculation is:

```text
CollatedResultValid =
    DataValid_IN
    AND CE_ProcessReady_IN
    AND CE_StatusReadOK_IN
```

The terms have distinct meanings:

| Status | Meaning |
|---|---|
| `DataValid_IN` | Python/OPC-UA machine-vision result is valid |
| `CE_ProcessReady_IN` | Control Expert indicates the monitored process is ready |
| `CE_StatusReadOK_IN` | EAE successfully completed and validated the Control Expert status read |

The raw `DataValid` status remains separately available for diagnosis. It was not replaced by the collated result.

`CollatedResultValid` is converted to a Modbus word:

```text
FALSE → MV_CollatedValidWord = 0
TRUE  → MV_CollatedValidWord = 1
```

The result is written to offset `3` and received by Control Expert at `%MW3`.

---

## Session 3 — Control Expert collated-validity integration

### Word-to-Boolean conversion

An unlocated Control Expert Boolean was added:

```text
MV_CollatedValid : BOOL
```

The received word is converted in the cyclic `MV_Supervisory` Structured Text section:

```iecst
MV_CollatedValid := MV_CollatedValidWord <> 0;
```

This produces:

```text
MV_CollatedValidWord = 0       → MV_CollatedValid = FALSE
MV_CollatedValidWord = nonzero → MV_CollatedValid = TRUE
```

### Final Control Expert availability calculation

The final availability logic is:

```iecst
MV_Available := MV_CE_CommsOK AND MV_CollatedValid;
MV_UnavailableAlarm := NOT MV_Available;
```

`MV_CE_CommsOK` represents continuing EAE-to-Control Expert publication, as determined from the update counter and the existing five-second stale timer.

`MV_CollatedValid` represents the returned EAE decision that the upstream measurement is valid, the Control Expert process is ready, and the Control Expert status read is healthy.

The effective availability condition is therefore:

```text
MV_Available =
    continuing EAE publication at Control Expert
    AND valid Python/OPC-UA MV result
    AND Control Expert process ready
    AND successful EAE read of Control Expert status
```

The original `MV_Raw_DataValid` remains visible as a diagnostic status. It is already included in the collated result and therefore does not need to be repeated in the final Boolean expression.

### Publication-freshness logic retained

The existing freshness mechanism was retained unchanged:

- `MV_UpdateCounter` changes while EAE continues publishing;
- Control Expert detects a change relative to the previous counter value;
- `MV_SeenFirstUpdate` prevents a healthy indication before the first publication;
- `MV_StaleTimer` uses a five-second timeout;
- `MV_CE_CommsOK` becomes false if the counter stops changing for five seconds;
- operation recovers automatically after the counter resumes.

The update counter represents continuing EAE publication, not a unique Python image sequence number.

### Measurement handling

`MV_BubbleCount` retains the previously implemented held-last-valid behaviour in Control Expert. Its accepted value is updated only while `MV_Available = TRUE`.

`MV_MedianECD`, however, is the received live REAL value at `%MW10`. No held-last-valid behaviour is implemented for `MV_MedianECD` at this stage. The value may remain visible or continue changing when the result is unavailable, but the availability and validity flags prevent it from being treated as usable process information.

---

## EAE HMI extension

The EAE HMI was extended to show the new Control Expert and collated statuses alongside the existing machine-vision measurements and diagnostics.

The final HMI status groups are:

### Machine Vision Status

```text
OPCUA Comms
Heartbeat
Pipeline
Data Valid
```

### Control Expert Status

```text
Process Ready
MODBUS Comms
```

### Overall Status

```text
MV Result Available
```

The new HMI signals correspond to:

| HMI label | EAE source | Meaning |
|---|---|---|
| `Process Ready` | `CE_ProcessReady` | Decoded Control Expert process-readiness word |
| `MODBUS Comms` | `CE_StatusReadOK` | Health of the individual Control Expert Modbus read operation |
| `MV Result Available` | `CollatedResultValid` | EAE collated result after MV validity, process readiness and read health are combined |

`MV Result Available` on the EAE HMI represents `CollatedResultValid`. Control Expert's final `MV_Available` additionally includes the CE-side EAE-publication freshness check.

The HMI retains the raw machine-vision status indicators so the source of an unavailable result can be distinguished.

---

## Session 4 — Final validation

### Test 1 — Normal end-to-end operation

The complete system was run with valid images and:

```text
CE_ProcessReady = TRUE
```

Observed behaviour included:

```text
MV_DataValid          = TRUE
CE_ProcessReady       = TRUE
CE_StatusReadOK       = TRUE
CollatedResultValid   = TRUE
MV_CollatedValidWord  = 1
MV_CollatedValid      = TRUE
MV_CE_CommsOK         = TRUE
MV_Available          = TRUE
MV_UnavailableAlarm   = FALSE
```

The update counter continued changing and the stale timer did not expire.

Machine-vision values remained visible through the complete path. One final normal-operation capture showed a Python `BubbleCount` of `392` and `MedianECD` of approximately `12.704`, with Control Expert displaying `MV_Raw_BubbleCount = 392` and `MV_MedianECD = 12.70366`. The small difference in displayed decimal precision is consistent with the EAE `LREAL` to Control Expert `REAL` conversion.

The HMI showed all machine-vision, Control Expert and overall-result indicators healthy.

**Result: PASS**

### Test 2 — Control Expert process not ready

`CE_ProcessReady` was changed to false while the Python pipeline and communications remained healthy.

Observed propagation was:

```text
CE_ProcessReady = FALSE
→ CE_ProcessReadyWord = 0
→ EAE CE_ProcessReady = FALSE
→ CollatedResultValid = FALSE
→ MV_CollatedValidWord = 0
→ MV_CollatedValid = FALSE
→ MV_Available = FALSE
→ MV_UnavailableAlarm = TRUE
```

At the same time:

```text
MV_Raw_DataValid = TRUE
CE_StatusReadOK = TRUE
MV_CE_CommsOK = TRUE
MV_UpdateCounter continued changing
```

This demonstrated that process readiness can make the measurement unavailable without incorrectly reporting an MV-pipeline or communication fault.

The HMI showed `Process Ready` and `MV Result Available` inactive while `MODBUS Comms` and the raw machine-vision indicators remained healthy.

Restoring `CE_ProcessReady = TRUE` restored collated validity and availability automatically.

**Result: PASS**

### Test 3 — Corrupt image with process ready

A corrupt image was introduced while:

```text
CE_ProcessReady = TRUE
```

The Python pipeline reported the image-read failure. Upstream invalidity propagated through EAE and Control Expert:

```text
Pipeline/MV data invalid
→ MV_DataValid = FALSE
→ CollatedResultValid = FALSE
→ MV_DataValidWord = 0
→ MV_CollatedValidWord = 0
→ MV_CollatedValid = FALSE
→ MV_Available = FALSE
→ MV_UnavailableAlarm = TRUE
```

Process readiness and Modbus read health remained true, showing that the unavailability originated from the machine-vision path.

**Result: PASS**

### Test 4 — Corrupt image with process not ready

The corrupt-image condition was also tested with:

```text
CE_ProcessReady = FALSE
```

Both the machine-vision validity input and process-readiness input were false. `CollatedResultValid`, `MV_CollatedValid`, and `MV_Available` remained false, confirming that multiple simultaneous invalid conditions cannot incorrectly produce an available result.

**Result: PASS**

### Test 5 — OPC-UA server shutdown

The Python OPC-UA server was stopped while EAE and Control Expert remained active.

The interruption propagated through the upstream supervisory path:

```text
OPC-UA/heartbeat status unhealthy
→ MV_DataValid = FALSE
→ CollatedResultValid = FALSE
→ MV_DataValidWord = 0
→ MV_CollatedValidWord = 0
→ MV_Available = FALSE
→ MV_UnavailableAlarm = TRUE
```

The EAE-to-Control Expert update counter could continue changing because EAE remained active and continued publishing the invalid status. In that case, `MV_CE_CommsOK = TRUE` correctly indicates a healthy EAE-to-CE publication path, not a healthy upstream OPC-UA source.

The HMI was checked with both process-ready and process-not-ready states. In each case, `MV Result Available` remained inactive when the OPC-UA path was unhealthy.

**Result: PASS**

### Test 6 — OPC-UA server restart

The Python OPC-UA server was restarted after the interruption.

EAE re-established the OPC-UA session, valid measurement acquisition resumed, and the resulting validity states propagated to Control Expert without manual logic reset.

The complete observed end-to-end recovery was approximately `10 seconds`. This was slower than the EAE and PLC Simulator restart cases and is consistent with OPC-UA reconnection and subsequent acquisition/status propagation occurring before the final availability state is restored.

Transient `BadSessionIdInvalid` messages may appear during restart or reconnection. They were treated as non-fatal development behaviour because the session and valid operation recovered automatically.

**Result: PASS**

### Test 7 — EAE application stopped

The EAE application was stopped while Control Expert remained active.

The Control Expert update counter stopped changing. After the configured five-second timeout:

```text
MV_StaleTimer.Q = TRUE
MV_CE_CommsOK = FALSE
MV_Available = FALSE
MV_UnavailableAlarm = TRUE
```

Previously received measurement and validity registers could retain their last values, but the stale-publication logic prevented those frozen values from being accepted as current.

This confirms that the returned collated-validity word does not replace the independent CE-side publication-freshness check.

**Result: PASS**

### Test 8 — EAE application restart

After the EAE application was restarted, the Modbus update counter resumed changing. The stale timer reset, `MV_CE_CommsOK` returned true, and `MV_Available` recovered when the remaining validity conditions were also true.

The observed Control Expert recovery was approximately `1 second` after EAE publication resumed.

**Result: PASS**

### Test 9 — Control Expert PLC Simulator stopped

The PLC Simulator was stopped while Python and EAE remained active.

The EAE Modbus read reported failure. Observed diagnostics included:

```text
CE_ReadError = -133011
CE_ReadStatus = "Connection closed"
CE_StatusReadOK = FALSE
CollatedResultValid = FALSE
```

The last decoded `CE_ProcessReady` value could remain true, but the failed read-health status made that retained value untrusted. The HMI therefore showed `Process Ready` retained, `MODBUS Comms` inactive, and `MV Result Available` inactive.

This validates the decision to derive Modbus read health from the read block's `QO`, `ERROR`, and `STATUS` outputs rather than relying only on the general `MB_CONNECT` indication.

**Result: PASS**

### Test 10 — Control Expert PLC Simulator restart

After the PLC Simulator was restarted and returned to operation, the Modbus read recovered:

```text
CE_ReadError = 0
CE_ReadStatus = "ok"
CE_StatusReadOK = TRUE
```

EAE again read `CE_ProcessReadyWord`, collated validity recovered when all conditions were true, and Control Expert resumed receiving measurements and status words.

The observed recovery was approximately `1 second`.

**Result: PASS**

---

## Final validation matrix

| Test | Key observed response | Result |
|---|---|---|
| Normal operation | Python, EAE, HMI and CE values/statuses healthy; update counter changing | PASS |
| Process not ready | Raw MV and Modbus health remained true; collated validity and CE availability became false | PASS |
| Corrupt image, process ready | MV validity, collated validity and CE availability became false | PASS |
| Corrupt image, process not ready | Multiple false inputs kept collated validity and availability false | PASS |
| OPC-UA shutdown | Upstream validity became false while downstream EAE publication could remain fresh | PASS |
| OPC-UA restart | Acquisition and final availability recovered automatically | PASS |
| EAE stopped | Counter froze; five-second stale timer forced CE communications and availability false | PASS |
| EAE restarted | Counter and CE availability recovered automatically | PASS |
| PLC Simulator stopped | EAE read health and collated validity became false; retained process value was not trusted | PASS |
| PLC Simulator restarted | Modbus read and two-way exchange recovered automatically | PASS |
| HMI state display | Raw MV, CE status and overall collated result agreed with internal EAE/CE states | PASS |

---

## Observed response and recovery times

The following timings were estimated by end-to-end visual observation of the Python terminal, EAE online view, Control Expert Animation Table and HMI:

| Event | Approximate observed behaviour |
|---|---|
| OPC-UA server stopped | Invalidity propagated to the remaining active layers in approximately `1 second` |
| PLC Simulator stopped | EAE Modbus read failure and collated invalidity appeared in approximately `1 second` |
| EAE publication stopped | Counter stopped immediately; CE declared the data stale after the intentional `5-second` timeout |
| OPC-UA server restarted | Full EAE/CE validity recovery took approximately `10 seconds` |
| EAE application restarted | CE updates and availability recovered in approximately `1 second` after publication resumed |
| PLC Simulator restarted | EAE read health and bidirectional operation recovered in approximately `1 second` |

These are approximate observational results, not formal latency measurements. The systems did not use synchronised timestamps or dedicated timing instrumentation. The values therefore demonstrate practical detection and automatic recovery behaviour but should not be presented as statistically characterised communication latency.

---

## Screenshot evidence

The following evidence was captured during the final test session:

| Evidence file | Condition demonstrated |
|---|---|
| `NormalOperation.jpg` | End-to-end Python, EAE and Control Expert normal operation |
| `HMINormalOperation.jpg` | Healthy measurement and status display on the EAE HMI |
| `ProcessNotReady.jpg` | CE process not ready while communications and raw MV validity remain healthy |
| `HMIProcessNotReady.jpg` | HMI process-not-ready and result-unavailable state |
| `ProcessReadyANDCorruptImage.jpg` | Corrupt-image invalidity with CE process ready |
| `ProcessNotReadyANDCorruptImage.jpg` | Simultaneous corrupt-image and process-not-ready conditions |
| `OPCUAServerStopped.jpg` | Upstream OPC-UA interruption and propagated invalidity |
| `HMIImmediatelyAfterOPCUAServerStoppedProcessReady.jpg` | HMI transition immediately after OPC-UA shutdown |
| `HMIOPCUAServerStoppedProcessReady.jpg` | Settled HMI OPC-UA-unavailable state with process ready |
| `HMIOPCUAServerStoppedProcessNotReady.jpg` | HMI OPC-UA-unavailable state with process not ready |
| `OPCUAServerRestart.jpg` | Recovery following OPC-UA server restart |
| `EAEApplicationStoppedAfter5Sec.jpg` | CE stale timer expired after EAE publication stopped |
| `EAERestart.jpg` | CE update and availability recovery after EAE restart |
| `PLCSimulatorStopped.jpg` | EAE behaviour during PLC Simulator interruption |
| `PLCSimulatorStoppedHMI.jpg` | HMI Modbus-unavailable state during PLC interruption |
| `HMIPLCSimulatorStoppedProcessReadyRetainedButNotValid.jpg` | Retained process-ready value rejected because Modbus read health is false |
| `PLCSimulatorRestart.jpg` | Modbus read and measurement transfer recovery after PLC Simulator restart |

---

## Sessions 3–4 outcome

Week 7 Sessions 3 and 4 completed the final validity and availability path between the Python machine-vision pipeline, EAE and Control Expert.

The system now demonstrates that:

- Python segmentation-derived measurements are published through OPC-UA;
- EAE acquires the measurements and evaluates upstream communications, heartbeat and pipeline validity;
- EAE reads Control Expert process status through Modbus TCP;
- the Control Expert status read is independently health-checked;
- EAE combines MV validity, CE process readiness and CE read health;
- EAE returns the collated result to Control Expert;
- Control Expert combines the returned result with its independent EAE-publication freshness check;
- stale, invalid, communication-failed or process-inappropriate values are not treated as available;
- the HMI exposes raw machine-vision status, Control Expert status and the overall collated result;
- all tested communication paths recover automatically after restart.

Together with Sessions 1 and 2, Week 7 demonstrates the required two-way Modbus TCP service:

```text
Control Expert status
→ Modbus TCP read by EAE
→ combined with segmentation-result validity
→ collated result and MV measurements
→ Modbus TCP write to Control Expert
```

---

## Remaining limitations and future work

The following items remain outside the completed Week 7 scope:

- only `MedianECD` has been transferred as a REAL-valued measurement;
- `ECD_P10`, `ECD_P90`, `MeanCircularity`, `MeanArea`, `MaskAreaFraction`, and `ProcessingTime` have not been added to the Control Expert register map;
- `MV_MedianECD` does not implement held-last-valid behaviour;
- the update counter represents EAE publication rather than a Python-originated per-image sequence number;
- response and recovery times were observed manually rather than measured using synchronised timestamps;
- the EAE HMI provides status indication but no alarm history, acknowledgement workflow or trend display;
- the implementation uses local simulated EAE and Control Expert targets rather than physical IPC and PLC hardware;
- Modbus TCP does not provide built-in authentication or encryption;
- the development OPC-UA interface retains Security Policy `None`, Message Security Mode `None`, and anonymous access;
- OPC-UA certificates, `Sign`/`SignAndEncrypt`, removal of anonymous access and deployment firewall rules remain future production work;
- no formal IEC 62443 compliance or certification claim is made;
- the system remains supervisory and does not perform closed-loop control.

An additional `CE_MVEnable` signal was considered but not implemented because `CE_ProcessReady` already provides the required Control Expert process-status input for the current demonstration. A separate enable should only be added if it is assigned a distinct future supervisory meaning.

---

## Week 7 final outcome

Week 7 successfully extended the Week 6 one-way monitoring interface into a bidirectional, validity-aware supervisory integration.

The completed demonstration is:

```text
Python YOLOv8-seg / FrothMVPipeline
→ OPC-UA measurements and status
→ EAE acquisition and supervisory processing
↔ Modbus TCP status and measurement exchange
↔ Control Expert PLC Simulator
```

The implementation transfers a live integer measurement and a live REAL measurement, reads Control Expert process status, combines that status with machine-vision and communication validity, returns the collated result to Control Expert, detects stale publication, presents diagnostic states on the HMI, and recovers after the tested component interruptions.

