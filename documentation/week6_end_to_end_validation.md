# Week 6 — Session 4: End-to-End Control Expert Validation

**Date:** 30 August 2026  
**System:** FrothMV-System  
**Status:** Completed successfully  
**Week:** Final session of Week 6

## 1. Session objective

The objective was to extend the successful Session 3 Modbus proof of concept into a validity-qualified end-to-end supervisory interface and to test its normal and fault behaviour.

The tested architecture was:

```text
Input images
    ↓
Python YOLOv8-seg / FrothMVPipeline
    ↓ OPC-UA
EAE MV_OPCUA_ACQUISITION
    ↓
EAE MV_SUPERVISORY_STATUS
    ↓
EAE_CE_MODBUS
    ↓ Modbus TCP
Control Expert PLC Simulator
```

The interface remained supervisory only and did not perform closed-loop process control.

## 2. Session 3 starting point

Session 4 began from the following verified baseline:

- `MB_CONNECT` connected successfully to the local Control Expert PLC Simulator;
- a fixed value of `123` was written successfully;
- a live `BubbleCount` value was transferred successfully;
- `MV_DataValid` was converted to `MV_DataValidWord` and received in Control Expert;
- received values were observable through the Control Expert Animation Table.

## 3. Final minimal Modbus signal map

The following minimal mapping was implemented:

| Signal | EAE interface type | Modbus offset | Control Expert address | Control Expert type |
|---|---:|---:|---:|---:|
| `MV_BubbleCountWord` | `UINT` | `0` | `%MW0` | `UINT` |
| `MV_DataValidWord` | `UINT` | `1` | `%MW1` | `UINT` |
| `MV_UpdateCounter` | `INT` | `2` | `%MW2` | `INT` |

The original EAE `BubbleCount` remained a `DINT`. A separate `UINT` representation was created only at the Modbus interface boundary. This retained the established OPC-UA/EAE type while avoiding unnecessary two-register DINT handling in the initial PLC interface.

The conversion is safe for the selected pipeline because the frozen configuration uses `max_det = 1000`, which is well within the `UINT` range.

## 4. Interface conversions

### BubbleCount conversion

The live EAE `BubbleCount : DINT` was converted inside `EAE_CE_MODBUS` to:

```text
MV_BubbleCountWord : UINT
```

The converted value was written at Modbus offset `0` and observed at `%MW0` in Control Expert.

### Data-valid conversion

The existing Boolean supervisory validity signal was converted into a register-compatible value:

```text
MV_DataValid = TRUE  → MV_DataValidWord = 1
MV_DataValid = FALSE → MV_DataValidWord = 0
```

`MV_DataValidWord` was written at offset `1` and observed at `%MW1`.

## 5. Update-counter implementation

An EAE `counterBasic` block was used instead of a custom ST counter.

The working configuration was:

```text
Input = TRUE
Composite REQ → counterBasic.E_UPCOUNT
counterBasic.CUO → MB_WRITE_UPDATE_COUNTER.REQ
counterBasic.Value → MB_WRITE_UPDATE_COUNTER.VALUE1
```

The counter output type was `INT`. It was written at Modbus offset `2` and received as an `INT` at `%MW2` in Control Expert.

The counter represents continuing EAE-to-Control Expert publication activity. It is not currently a unique Python image sequence number.

## 6. EAE Modbus event arrangement

The Modbus writes were implemented as parallel branches from the composite request event:

```text
Composite REQ
    ├─ BubbleCount conversion REQ
    │      └─ CNF → BubbleCount write REQ
    │
    ├─ DataValid conversion REQ
    │      └─ CNF → DataValid write REQ
    │
    └─ counterBasic.E_UPCOUNT
           └─ CUO → UpdateCounter write REQ
```

This arrangement operated successfully without observed write conflicts or missing values. Sequential Modbus write chaining was therefore not introduced during this session.

This does not change the established OPC-UA acquisition architecture: `MV_OPCUA_ACQUISITION` remains `E_CYCLE`-driven with parallel reads.

## 7. Control Expert supervisory logic

The following raw interface variables were monitored:

```text
MV_Raw_BubbleCount    UINT    %MW0
MV_DataValidWord      UINT    %MW1
MV_UpdateCounter      INT     %MW2
```

The Control Expert logic converted the received validity word, detected changes in the update counter and qualified the received bubble count before making it available for supervisory use.

The implemented logic followed this structure:

```pascal
MV_Raw_DataValid := (MV_DataValidWord <> 0);

IF MV_UpdateCounter <> MV_PreviousCounter THEN
    MV_NewUpdate := TRUE;
    MV_SeenFirstUpdate := TRUE;
    MV_PreviousCounter := MV_UpdateCounter;
ELSE
    MV_NewUpdate := FALSE;
END_IF;

MV_StaleTimer(
    IN := MV_SeenFirstUpdate AND NOT MV_NewUpdate,
    PT := T#5s
);

MV_CE_CommsOK :=
    MV_SeenFirstUpdate
    AND NOT MV_StaleTimer.Q;

MV_Available :=
    MV_CE_CommsOK
    AND MV_Raw_DataValid;

IF MV_Available THEN
    MV_BubbleCount :=
        UINT_TO_DINT(MV_Raw_BubbleCount);
END_IF;

MV_UnavailableAlarm := NOT MV_Available;
```

The usable `MV_BubbleCount` therefore updates only while the EAE-to-Control Expert data are fresh and the upstream soft-sensor validity state is true. The last usable value may remain held when unavailable, but the alarm and availability state identify it as invalid or stale.

## 8. Stale-update timer

A Control Expert `TON` instance named `MV_StaleTimer` was used to detect loss of EAE updates.

Normal behaviour:

```text
MV_UpdateCounter changes
→ MV_NewUpdate pulses TRUE
→ stale timer resets
→ MV_CE_CommsOK remains TRUE
```

Loss-of-update behaviour:

```text
EAE stops writing
→ MV_UpdateCounter stops changing
→ MV_StaleTimer reaches T#5s
→ MV_StaleTimer.Q becomes TRUE
→ MV_CE_CommsOK becomes FALSE
→ MV_Available becomes FALSE
→ MV_UnavailableAlarm becomes TRUE
```

The timer also recovered as expected when EAE resumed writing and the update counter changed again.

## 9. Validation tests

### 9.1 Normal operation

The complete system was run with valid images.

Confirmed results:

- Python processed and published the live `BubbleCount`;
- EAE received the corresponding value through OPC-UA;
- EAE converted and published the value through Modbus TCP;
- Control Expert displayed the matching value in the Animation Table;
- `MV_DataValidWord` indicated valid data;
- `MV_UpdateCounter` changed continuously;
- the stale timer remained reset;
- `MV_CE_CommsOK` and `MV_Available` remained true.

**Result:** Passed.

### 9.2 EAE stops writing

EAE Modbus publication was stopped while the Control Expert simulator remained running.

Confirmed results:

- `MV_UpdateCounter` stopped changing;
- the stale timer elapsed;
- `MV_CE_CommsOK` became false;
- the measurement became unavailable;
- the unavailable alarm activated;
- normal state recovered when writing resumed.

**Result:** Passed.

### 9.3 Corrupt image

A corrupt image was processed to exercise the existing Python/EAE failure path.

Confirmed results:

- the Python pipeline identified the processing failure;
- invalidity propagated through EAE supervisory status;
- `MV_DataValidWord` changed to the invalid state;
- Control Expert displayed the invalid value in the Animation Table;
- the PLC-side availability logic prevented the measurement from being treated as trustworthy.

**Result:** Passed.

### 9.4 Python OPC-UA server shutdown and restart

The Python OPC-UA server was stopped and restarted while the remaining system was observed.

Confirmed results:

- the upstream communication interruption was detected by the existing EAE supervisory architecture;
- the validity state propagated to Control Expert;
- communication and valid-data operation recovered after the Python server restarted and EAE reconnected.

**Result:** Passed.

## 10. Test-results summary

| Test | Expected result | Actual result | Status |
|---|---|---|---|
| Normal live operation | Values match through Python, EAE and CE | Matching live values confirmed | Passed |
| EAE stops writing | Counter freezes and CE stale timer expires | Expected stale behaviour confirmed | Passed |
| Corrupt image | Invalidity propagates to CE | `MV_DataValidWord` indicated invalid data | Passed |
| Python server shutdown | Upstream data become unavailable | Invalidity/communication state propagated | Passed |
| Python server restart | System reconnects and recovers | Recovery confirmed | Passed |

## 11. Cybersecurity and resilient-design relevance

The Session 4 design demonstrates selected cybersecurity and OT-resilience principles identified earlier in Week 6:

- the Modbus connection remained local using `127.0.0.1` during simulation;
- only required supervisory values were mapped;
- validity information accompanied the measurement;
- stale communication was detected separately from source-data invalidity;
- invalid or stale values were not treated as available measurements;
- failure and recovery behaviour was tested and observable.

Modbus TCP does not provide authentication or encryption in this configuration. Network segmentation, restricted firewall rules and secure deployment controls remain future requirements for physical hardware deployment. This work is informed by selected IEC 62443 and OPC-UA security principles but does not claim standards compliance or certification.

## 12. Deferred work

The following work was deliberately deferred to Week 7 or later:

- add `MedianECD`, `ECD_P10`, `ECD_P90` and `MeanCircularity` to the Modbus interface;
- convert selected EAE `LREAL` measurements to Control Expert-compatible `REAL` values;
- verify two-register REAL encoding and word order;
- extend the final register map;
- consider a Python-originated image sequence number if per-image freshness is required;
- complete any additional communication-loss and recovery tests;
- consider OPC-UA `Sign` or `SignAndEncrypt` for a future deployed configuration;
- consider physical IPC and PLC deployment.

The omission of additional REAL measurements does not affect the Week 6 proof of the open communication architecture, validity propagation or stale-data detection.

## 13. Session and Week 6 conclusion

Session 4 completed the Week 6 objective of demonstrating a local, simulated and validity-qualified open architecture from the Python machine-vision pipeline to a Control Expert PLC application.

The final system successfully transferred a live bubble-count measurement and validity state, monitored continuing EAE publication through an update counter, detected stale writes in Control Expert, propagated corrupt-image invalidity, and recovered after a Python OPC-UA server restart.

Week 6 therefore concluded with both:

1. a cybersecurity-informed system design and practical hardening baseline; and
2. a functioning Python → OPC-UA → EAE → Modbus TCP → Control Expert supervisory demonstration.
