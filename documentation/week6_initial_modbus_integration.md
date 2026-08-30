# Week 6 — Session 3: Local EAE–Control Expert Integration

**Date:** 29 August 2026  
**System:** FrothMV-System  
**Status:** Completed successfully

## 1. Session objective

The objective was to establish and verify a local EAE-to-Control Expert communication path without a physical PLC:

```text
EAE supervisory application
        ↓ Modbus TCP
Control Expert PLC Simulator
```

The integration remained supervisory only. No closed-loop process-control action was implemented.

## 2. Configuration

### Control Expert

- PLC platform selected: Modicon M580 BME P58 6040
- Rack selected: BME XBP 0400
- Control Expert PLC Simulator used as the receiving Modbus TCP device
- Simulator project loaded and running
- Test register monitored using an Animation Table

### EAE

- Library: `Standard.IoModbus`
- Function block: `MB_CONNECT`
- Function block: `MB_WRITE_REGISTERS`
- Connection URI tested:

```text
tcp://127.0.0.1:502
```

The connection was local because EAE and the PLC Simulator were running on the same computer.

### `MB_CONNECT` settings

| Parameter | Value |
|---|---:|
| `QI` | `TRUE` |
| `ID` | `1` |
| `URI` | `tcp://127.0.0.1:502` |
| `NEW_CONNECTION` | `TRUE` during connection setup |
| `TIMEOUT` | `T#500ms` |
| `SWAP_BYTES` | `FALSE` |
| `SWAP_WORD` | `FALSE` |
| `SWAP_DWORD` | `FALSE` |

The block reported:

- `QO = TRUE`;
- `STATUS = "Connected"`;
- `ERROR = 0`.

## 3. Constant register-write test

An `MB_WRITE_REGISTERS` block was configured to write a constant test value:

| Parameter | Value |
|---|---:|
| `QI` | `TRUE` |
| `CONNECTION_ID` | `1` |
| `OFFSET` | `0` |
| `STATUS_ID` | `1` |
| `VALUE1` | `123` |

The write block was initialized after the Modbus connection and triggered using its `REQ` event. Its confirmation and error outputs were monitored.

In Control Expert, the value was observed in the Animation Table at:

```text
%MW0 = 123
```

This confirmed that the first Modbus register offset mapped correctly to the first Control Expert memory word used for the test.

## 4. Live `BubbleCount` transfer

After the fixed-value test succeeded, the constant was replaced by the live EAE `BubbleCount` value received from the Python machine-vision pipeline through OPC-UA.

The live value observed during the test was:

```text
BubbleCount = 574
```

The same value was successfully received and displayed in the Control Expert Animation Table. This extended the test beyond a fixed register value and demonstrated the working live path:

```text
Python machine-vision pipeline
        ↓ OPC-UA
EAE acquisition and supervisory system
        ↓ Modbus TCP
Control Expert PLC Simulator
```

The successful value transfer confirmed functional interoperability between the existing EAE soft-sensor system and the simulated Control Expert PLC. The final two-register layout for the 32-bit `DINT` representation remains to be formalised before adjacent registers are allocated.

## 5. Validity-state transfer

The EAE Boolean signal `MV_DataValid` was converted at the Modbus interface boundary into the register-compatible variable:

```text
MV_DataValidWord : UINT
```

The conversion was:

```text
MV_DataValid = TRUE  → MV_DataValidWord = 1
MV_DataValid = FALSE → MV_DataValidWord = 0
```

`MV_DataValidWord` was successfully written to Control Expert and observed through the Animation Table. This demonstrated that the EAE validity state can be transferred through a Modbus holding register.

## 6. Results

| Test | Result | Evidence |
|---|---|---|
| EAE Modbus connection | Passed | `STATUS = Connected`, `QO = TRUE`, `ERROR = 0` |
| Constant register write | Passed | `%MW0` received `123` |
| Live `BubbleCount` transfer | Passed | Live value `574` was received in the Control Expert Animation Table |
| EAE-to-CE validity conversion | Passed | `MV_DataValidWord` received correctly |
| Local simulator communication | Passed | Control Expert Animation Table displayed received values |

## 7. Technical interpretation

The session proved the live open-architecture interface:

```text
Python MV / EAE supervisory outputs
        ↓
EAE Modbus TCP client
        ↓
Control Expert PLC Simulator
```

The `MV_DataValid` signal was retained as a Boolean inside the EAE supervisory logic. Only the Modbus interface converted it to `0` or `1`, keeping protocol-specific adaptation separate from the supervisory design.

The existing `BubbleCount` signal remains a `DINT` in EAE because it matches the established OPC-UA `Int32` interface and preserves a 32-bit range. Its live value was transferred successfully, while its final documented Modbus mapping will be confirmed in Session 4 because a 32-bit value may occupy two 16-bit registers.

## 8. Limitations and deferred work

The following items were intentionally deferred to Session 4:

- final register allocation for all measurements and status signals;
- confirmation of DINT/REAL two-register mappings and word order;
- transfer of the complete selected MV signal set;
- implementation of `MV_UpdateCounter` freshness monitoring;
- PLC-side availability and alarm logic;
- communication-loss and recovery testing;
- final end-to-end documentation and screenshots.

The current result is a successful local proof of concept, not a complete production PLC integration or an IEC 62443-compliant deployment.

## 9. Session conclusion

Session 3 successfully established and verified the local EAE-to-Control Expert Modbus TCP interface. The Control Expert PLC Simulator received an initial constant test value, a live `BubbleCount` value of `574`, and the converted `MV_DataValidWord` validity state. The remaining signal mapping, PLC-side supervisory logic and fault testing can proceed in Session 4 without changing the basic connection architecture.
