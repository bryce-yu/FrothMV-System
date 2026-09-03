# FrothMV-System — Week 7 Session 2: Bidirectional Modbus and Collated Validity

## Session focus

Week 7 Session 2 extended the local EAE-to-Control Expert interface from one-way measurement publication to two-way information exchange over Modbus TCP.

The session also introduced a collated validity result that combines machine-vision validity with Control Expert process status and Modbus read health. This collated result was then returned to Control Expert.

The completed information flow is:

```text
Python machine vision
→ OPC-UA
→ EAE acquisition and supervisory status
→ EAE reads Control Expert process status using Modbus TCP
→ EAE combines MV validity with Control Expert status
→ EAE writes measurements and collated validity to Control Expert
```

The system remains supervisory only. No closed-loop control was introduced.

---

## Starting baseline

Week 7 Session 1 had already established the following EAE-to-Control Expert transfers:

| Signal | Modbus offset(s) | Control Expert address/type |
|---|---:|---|
| `MV_BubbleCountWord` | 0 | `%MW0`, `UINT` |
| `MV_DataValidWord` | 1 | `%MW1`, `UINT` |
| `MV_UpdateCounter` | 2 | `%MW2`, `INT` |
| `MV_MedianECD` | 10–11 | `%MW10`, `REAL` |

The live `MedianECD` path was:

```text
EAE MedianECD : LREAL
→ LREAL_TO_REAL
→ one REAL MB_WRITE_REGISTERS operation
→ offsets 10–11
→ Control Expert MV_MedianECD : REAL at %MW10
```

The existing Control Expert stale-update timer continued monitoring `MV_UpdateCounter` to determine whether EAE publication remained active.

---

## Register ownership

Separate register ranges were defined to avoid both systems writing to the same locations:

| Range | Owner | Intended operation |
|---|---|---|
| Offsets `0–99` | EAE | EAE writes; Control Expert receives |
| Offsets `100–199` | Control Expert | Control Expert writes; EAE reads |

This establishes explicit data ownership even though EAE acts as the Modbus client for both reads and writes.

---

## Control Expert process-status signal

A process-readiness status was created in Control Expert:

| Variable | Type | Address | Purpose |
|---|---|---|---|
| `CE_ProcessReady` | `BOOL` | Unlocated | Logical process-readiness state |
| `CE_ProcessReadyWord` | `UINT` | `%MW100` | Modbus representation read by EAE |

The following logic was added to the cyclic `MV_Supervisory` Structured Text section:

```iecst
IF CE_ProcessReady THEN
    CE_ProcessReadyWord := 1;
ELSE
    CE_ProcessReadyWord := 0;
END_IF;
```

This produces:

```text
CE_ProcessReady = FALSE → CE_ProcessReadyWord = 0
CE_ProcessReady = TRUE  → CE_ProcessReadyWord = 1
```

The logic is executed every PLC scan and is the only logic writing to `%MW100`.

---

## EAE Modbus read implementation

An `MB_READ_REGISTERS` block from `Standard.IoModbus` was added to the existing EAE–Control Expert Modbus composite.

The read used the same connection already established for the Modbus writes:

```text
QI            = TRUE
CONNECTION_ID = existing EAE–CE Modbus connection
OFFSET        = 100
INPUT_TYPE    = FALSE
STATION_ID    = 1
VALUE1 type   = UINT
```

`INPUT_TYPE = FALSE` was selected because `%MW100` is accessed as a holding register. The block output `VALUE1` was connected to `CE_ProcessReadyWord : UINT`.

The Modbus interface exposed the following read outputs:

```text
CE_ProcessReadyWord : UINT
CE_ReadQO           : BOOL
CE_ReadError        : DINT
CE_ReadStatus       : STRING
CE_DATA_UPDATED     : event
```

Connections from the read block were:

```text
VALUE1 → CE_ProcessReadyWord
QO     → CE_ReadQO
ERROR  → CE_ReadError
STATUS → CE_ReadStatus
CNF    → CE_DATA_UPDATED
```

The read result and diagnostics were associated with `CE_DATA_UPDATED` using event `WITH` relationships.

---

## Separate Control Expert status composite

A dedicated `MV_CE_STATUS` composite was created rather than placing the status interpretation inside the communication composite.

This preserves the architectural separation between:

- communication and raw values in the EAE–CE Modbus composite; and
- interpretation, health and supervisory meaning in `MV_CE_STATUS`.

This mirrors the existing separation between `MV_OPCUA_ACQUISITION` and `MV_SUPERVISORY_STATUS`.

### Interface

Inputs:

```text
CE_ProcessReadyWord : UINT
ReadQO              : BOOL
ReadError           : DINT
REQ                 : event
```

Outputs:

```text
CE_ProcessReady : BOOL
CE_StatusReadOK : BOOL
CE_STATUS_UPDATED : event
```

### Process-ready conversion

The received `UINT` was converted to a Boolean using:

```iecst
STATUS_BOOL := STATUS_WORD <> 0;
```

This produces:

```text
CE_ProcessReadyWord = 0     → CE_ProcessReady = FALSE
CE_ProcessReadyWord = nonzero → CE_ProcessReady = TRUE
```

### Read-health logic

The read error was compared with zero and combined with the read block qualifier:

```text
CE_StatusReadOK = ReadQO AND (ReadError = 0)
```

The internal event sequence is:

```text
REQ
→ UINT-to-BOOL conversion
→ error comparison
→ ReadQO AND ErrorEqualZero
→ CE_STATUS_UPDATED
```

`CE_ProcessReady` may retain its last value after a communication failure, but it is not treated as trustworthy while `CE_StatusReadOK = FALSE`.

---

## Application-level event-flow correction

The Modbus composite originally used one general `REQ` event for both reads and writes. This would cause measurements sourced from the final soft-sensor composite to be written before the current Control Expert status had been read and collated.

The general event was therefore split into:

```text
READ_REQ
WRITE_REQ
```

The resulting application-level sequence is:

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

Inside the Modbus composite:

- `READ_REQ` triggers only the Control Expert status read;
- `WRITE_REQ` triggers only the EAE-to-Control Expert measurement and status writes.

This prevents an event loop and ensures that outgoing values are written after the collated result has been calculated.

During the interface update, EAE temporarily reported that `READ_REQ` did not exist even though it appeared in the type interface. The issue was resolved by deleting the event input, recreating it and saving the type. This was treated as a stale interface-definition issue rather than a logic error.

---

## Soft-sensor aggregation

`MV_SOFT_SENSOR`, which previously acted primarily as a pass-through for HMI outputs, was extended into the final aggregation layer.

The existing machine-vision measurements and statuses remain available as outputs. Two new inputs were added:

```text
CE_ProcessReady_IN : BOOL
CE_StatusReadOK_IN : BOOL
```

A new output was added:

```text
CollatedResultValid : BOOL
```

The implemented calculation is:

```text
CollatedResultValid =
    DataValid_IN
    AND CE_ProcessReady_IN
    AND CE_StatusReadOK_IN
```

The inputs represent:

| Input | Meaning |
|---|---|
| `DataValid_IN` | Python/EAE machine-vision measurement is valid |
| `CE_ProcessReady_IN` | Control Expert indicates the monitored process is ready |
| `CE_StatusReadOK_IN` | The Control Expert status was read successfully |

The original `DataValid` output was retained as raw upstream MV validity. It was not replaced by the collated value, allowing the origin of invalidity to be diagnosed.

The former general completion output was renamed:

```text
COLLATED_DATA_UPDATED
```

The event is produced after the collated-validity AND operation completes. It triggers the Modbus `WRITE_REQ`, ensuring the outgoing measurement set and validity states correspond to the completed aggregation step.

The Modbus inputs for `BubbleCount`, `MedianECD` and raw `MV_DataValid` were taken from `MV_SOFT_SENSOR` outputs, providing one authoritative downstream interface for both the HMI and Control Expert.

---

## Returning collated validity to Control Expert

`CollatedResultValid : BOOL` was added as an input to the Modbus composite.

Inside the composite, it was converted to a `UINT` and written after `WRITE_REQ`:

```text
WRITE_REQ
→ BOOL-to-UINT conversion
→ conversion CNF
→ MB_WRITE_COLLATED_VALID.REQ
```

The conversion is:

```text
CollatedResultValid = TRUE  → MV_CollatedValidWord = 1
CollatedResultValid = FALSE → MV_CollatedValidWord = 0
```

The word was assigned to the next free EAE-owned register:

| Signal | Offset | Control Expert address/type |
|---|---:|---|
| `MV_CollatedValidWord` | 3 | `%MW3`, `UINT` |

Control Expert successfully received `MV_CollatedValidWord`.

---

## Final Session 2 register map

| Signal | Direction | Modbus offset(s) | Control Expert address/type | Owner |
|---|---|---:|---|---|
| `MV_BubbleCountWord` | EAE → CE | 0 | `%MW0`, `UINT` | EAE |
| `MV_DataValidWord` | EAE → CE | 1 | `%MW1`, `UINT` | EAE |
| `MV_UpdateCounter` | EAE → CE | 2 | `%MW2`, `INT` | EAE |
| `MV_CollatedValidWord` | EAE → CE | 3 | `%MW3`, `UINT` | EAE |
| `MV_MedianECD` | EAE → CE | 10–11 | `%MW10`, `REAL` | EAE |
| `CE_ProcessReadyWord` | CE → EAE | 100 | `%MW100`, `UINT` | Control Expert |

---

## Validation tests

### 1. Control Expert status conversion

`CE_ProcessReady` was toggled in Control Expert and `%MW100` responded correctly:

```text
FALSE → CE_ProcessReadyWord = 0
TRUE  → CE_ProcessReadyWord = 1
```

### 2. EAE status read

EAE successfully read offset 100 and converted the received word:

```text
CE_ProcessReadyWord = 0 → CE_ProcessReady = FALSE
CE_ProcessReadyWord = 1 → CE_ProcessReady = TRUE
```

Repeated `FALSE → TRUE → FALSE → TRUE` transitions were observed successfully.

### 3. Simultaneous two-way operation

While EAE read `CE_ProcessReadyWord` from Control Expert, Control Expert continued receiving:

- `BubbleCount`;
- raw `MV_DataValidWord`;
- `MV_UpdateCounter`;
- live `MedianECD`.

This confirmed simultaneous two-way application-data exchange over the same Modbus TCP interface.

### 4. PLC Simulator interruption

The Control Expert PLC Simulator was exited while EAE continued running.

Observed EAE read diagnostics included:

```text
CE_ReadError = -133011
CE_ReadStatus = "Connection closed"
CE_StatusReadOK = FALSE
```

The general EAE–CE connected indication could remain `TRUE` temporarily while the individual read correctly reported failure. This confirmed the need to assess read health using the read operation rather than relying only on the general connection output.

### 5. PLC Simulator recovery

After restarting the PLC Simulator, the read recovered automatically:

```text
CE_ReadError = 0
CE_ReadStatus = "ok"
CE_StatusReadOK = TRUE
```

`CE_ProcessReady` again followed `%MW100`, and the outgoing EAE measurements continued updating in Control Expert.

### 6. Collated-validity logic

With upstream MV validity healthy:

```text
MV_DataValidWord = 1
CE_ProcessReady = TRUE
CE_StatusReadOK = TRUE
→ MV_CollatedValidWord = 1
```

`CE_ProcessReady` was then changed to `FALSE` while raw MV validity remained true:

```text
MV_DataValidWord = 1
CE_ProcessReady = FALSE
→ MV_CollatedValidWord = 0
```

After restoring `CE_ProcessReady = TRUE`:

```text
MV_CollatedValidWord = 1
```

This confirmed that the collated word returned to Control Expert was genuinely dependent on both MV validity and Control Expert process status, rather than simply duplicating raw `MV_DataValid`.

---

## Session outcome

Week 7 Session 2 successfully demonstrated:

- Control Expert-to-EAE status transfer through `MB_READ_REGISTERS`;
- EAE-to-Control Expert measurement and status publication;
- explicit Modbus register ownership by direction;
- separation of communication and CE-status interpretation;
- independent Modbus read-health evaluation;
- detection of PLC Simulator communication interruption;
- automatic recovery after simulator restart;
- combination of MV validity with Control Expert process readiness and read health;
- return of the collated validity result to Control Expert;
- an ordered read–process–collate–write event flow.

The implemented architecture is now:

```text
Images
→ Python YOLOv8-seg / FrothMVPipeline
→ OPC-UA
→ MV_OPCUA_ACQUISITION
→ MV_SUPERVISORY_STATUS
→ EAE_CE_MODBUS_EXCHANGE reads CE status
→ MV_CE_STATUS
→ MV_SOFT_SENSOR aggregation
→ EAE_CE_MODBUS_EXCHANGE writes results
→ Control Expert PLC Simulator
```

This satisfies the core demonstration that the soft dPAC can read Control Expert status, Control Expert can receive soft-dPAC measurements/status, and the segmentation result can be combined with Control Expert status and returned to Control Expert.

---

## Remaining work

The following work is carried forward to the next session:

- convert `MV_CollatedValidWord` to a Boolean in Control Expert;
- incorporate collated validity into the Control Expert `MV_Available` calculation;
- retain the existing EAE-publication stale check alongside collated validity;
- add held-last-valid behaviour for `MedianECD` if required;
- consider an optional `CE_MVEnable` status only if it provides a distinct supervisory purpose;
- extend the register map to selected additional REAL measurements if time permits;
- repeat corrupt-image, OPC-UA interruption and stale-publication tests with the collated interface;
- complete final Week 7 consolidation and thesis-ready diagrams/documentation.

