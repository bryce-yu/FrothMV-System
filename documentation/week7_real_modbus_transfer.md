# FrothMV-System — Week 7 Session 1: REAL Measurement Transfer

## Session focus

Week 7 Session 1 extended the validated Week 6 EAE-to-Control Expert Modbus TCP interface to transfer the first floating-point machine-vision measurement.

The selected measurement was `MedianECD`, which is published by Python through OPC-UA as an `LREAL` in EAE. The objective was to convert it to a 32-bit `REAL`, transfer it over two Modbus holding registers, confirm the register and word arrangement, and verify that Control Expert reconstructed the live value correctly.

The demonstrated path was:

```text
Python MedianECD
→ OPC-UA Double
→ EAE MedianECD : LREAL
→ EAE LREAL-to-REAL conversion
→ EAE MB_WRITE_REGISTERS
→ Modbus offsets 10–11
→ Control Expert MV_MedianECD : REAL at %MW10
```

The existing Week 6 transfer of `BubbleCount`, validity and the EAE update counter remained operational.

---

## Starting baseline

The Week 6 interface was checked before making changes. The existing register map was:

| Signal | EAE Modbus type | Modbus offset | Control Expert address/type |
|---|---|---:|---|
| `MV_BubbleCountWord` | `UINT` | 0 | `%MW0`, `UINT` |
| `MV_DataValidWord` | `UINT` | 1 | `%MW1`, `UINT` |
| `MV_UpdateCounter` | `INT` | 2 | `%MW2`, `INT` |

The following baseline behaviour was confirmed:

- live `BubbleCount` transfer remained operational;
- `MV_DataValidWord` continued to indicate upstream measurement validity;
- `MV_UpdateCounter` continued changing during EAE publication;
- Control Expert stale-update detection remained active;
- `MV_CE_CommsOK`, `MV_Available` and `MV_UnavailableAlarm` behaved normally.

### Supervisory-cycle timing check

A short timing check was also performed after noticing a delay of several seconds between Python processing and the Control Expert register update.

The `E_CYCLE` inside `MV_SUPERVISORY_STATUS` was temporarily changed from:

```text
DT = T#1000ms
StaleCount threshold = 5 cycles
```

to:

```text
DT = T#500ms
StaleCount threshold = 10 cycles
```

This retained an approximate five-second heartbeat timeout. However, it did not improve the observed end-to-end delay and caused `DATA_UPDATED` and `STATUS_UPDATED` to become less synchronised. The change was therefore reverted.

The retained configuration is:

```text
MV_SUPERVISORY_STATUS E_CYCLE DT = T#1000ms
Heartbeat stale threshold = 5 cycles
```

This result indicates that the supervisory-cycle interval is not the principal source of the observed delay. Future latency investigation should instead examine OPC-UA acquisition timing and Modbus publication timing.

---

## Control Expert REAL allocation

Two consecutive Modbus registers were reserved for the first REAL measurement:

| Signal | EAE source type | Modbus offsets | Control Expert declaration |
|---|---|---:|---|
| `MV_MedianECD` | `LREAL`, converted to `REAL` | 10–11 | `MV_MedianECD : REAL` at `%MW10` |

For the M580 project, the located `REAL` was declared at the even starting word address `%MW10`. Because a `REAL` is 32 bits, it automatically occupies both `%MW10` and `%MW11`. The next available non-overlapping word after this value is `%MW12`.

The correct declaration is therefore:

```text
Name:    MV_MedianECD
Type:    REAL
Address: %MW10
```

`%MF10` was not used because Control Expert reported that topological address as invalid for this project.

---

## Fixed-word verification

Before transferring the live measurement, known IEEE-754 test patterns were written as two `UINT` register values. This confirmed how Control Expert orders the two 16-bit words that form a 32-bit REAL.

### Test 1 — REAL value 1.0

The IEEE-754 representation of `1.0` is:

```text
32-bit pattern = 16#3F800000
High word      = 16#3F80 = 16256
Low word       = 16#0000 = 0
```

Writing the high word to offset 10 and the low word to offset 11 produced approximately `2.277951E-41`, corresponding to the reversed bit pattern `16#00003F80`.

The values were therefore swapped:

```text
Offset 10 = UINT#0
Offset 11 = UINT#16256
```

Control Expert then displayed:

```text
MV_MedianECD = 1.0
```

### Test 2 — REAL value 12.34

The approximate IEEE-754 representation of `12.34` is:

```text
32-bit pattern = 16#414570A4
High word      = 16#4145 = 16709
Low word       = 16#70A4 = 28836
```

The verified register arrangement was used:

```text
Offset 10 = UINT#28836   // 16#70A4, low word
Offset 11 = UINT#16709   // 16#4145, high word
```

Control Expert successfully displayed approximately `12.34`.

### Verified word order

The tests established that the Control Expert REAL representation for this interface is:

```text
Lower Modbus offset  = low 16-bit word
Higher Modbus offset = high 16-bit word
```

Therefore:

```text
Offset 10 / %MW10 = low word
Offset 11 / %MW11 = high word
```

The temporary two-`UINT` arrangement was used only to verify the representation. The final live implementation uses one REAL-typed Modbus write.

---

## EAE LREAL-to-REAL conversion

Python publishes `MedianECD` as an OPC-UA Double, which is acquired in EAE as an `LREAL`. A basic conversion function block was added with:

```text
Input:  LREAL_VAL : LREAL
Output: REAL_VAL  : REAL
```

The Structured Text algorithm is:

```iecst
REAL_VAL := LREAL_TO_REAL(LREAL_VAL);
```

The live EAE input was connected as:

```text
MV_MedianECD : LREAL
→ LREAL_TO_REAL_CONVERSION.LREAL_VAL
```

The converted output was connected to the Modbus write as:

```text
LREAL_TO_REAL_CONVERSION.REAL_VAL
→ MB_WRITE_MEDIAN_ECD.VALUE1
```

The event sequence is:

```text
Modbus composite REQ
→ LREAL_TO_REAL_CONVERSION.REQ
→ conversion CNF
→ MB_WRITE_MEDIAN_ECD.REQ
```

This ensures that the `LREAL` input is converted before the REAL value is written.

---

## Final Modbus write configuration

The final live implementation uses one `MB_WRITE_REGISTERS` function block rather than two separate word-writing blocks.

```text
Block:         MB_WRITE_MEDIAN_ECD
QI:            TRUE
CONNECTION_ID: 1
OFFSET:        10
STATION_ID:    1
VALUE1 type:   REAL
VALUE1 source: converted MedianECD REAL
```

With `VALUE1` typed as `REAL`, the EAE Modbus block serialises the 32-bit value across offsets 10 and 11. Two REAL-typed write blocks must not be used at offsets 10 and 11 because each REAL occupies two registers and the writes would overlap.

This final arrangement avoids manual bit splitting during normal operation while retaining the experimentally verified register representation.

---

## Live transfer result

The live `MedianECD` value was successfully transferred through the complete path:

```text
Python
→ OPC-UA
→ EAE LREAL
→ EAE REAL
→ Modbus TCP
→ Control Expert REAL
```

One observed Control Expert value was:

```text
MV_MedianECD = 12.70366
```

The corresponding value observed in `%MW11` was:

```text
%MW11 = 16715 decimal = 16#414B
```

This is consistent with `%MW11` containing the high 16-bit word of the approximately `12.70` IEEE-754 REAL value. `%MW10` contains the low word; neither raw word is expected to resemble the decimal measurement independently.

During the live test, the existing interface also remained operational. Example observed values included:

```text
MV_Raw_BubbleCount = 392
MV_DataValidWord   = 1
MV_UpdateCounter   = 228
MV_CE_CommsOK      = TRUE
MV_Available       = TRUE
MV_UnavailableAlarm = FALSE
```

The Modbus REAL write reported successful operation with `QO = TRUE` and no write error.

---

## Updated provisional register map

| Signal | EAE Modbus type | Modbus offsets | Control Expert address/type | Purpose |
|---|---|---:|---|---|
| `MV_BubbleCountWord` | `UINT` | 0 | `%MW0`, `UINT` | Bubble-count measurement |
| `MV_DataValidWord` | `UINT` | 1 | `%MW1`, `UINT` | Upstream MV validity |
| `MV_UpdateCounter` | `INT` | 2 | `%MW2`, `INT` | Continuing EAE publication |
| `MV_MedianECD` | `REAL` | 10–11 | `%MW10`, `REAL` | Median equivalent circular diameter |

Offsets 3–9 remain available for future integer or status signals. Additional REAL values can begin at later non-overlapping even word addresses, such as `%MW12`, `%MW14` and `%MW16`.

---

## Session validation summary

The following checks passed:

- Week 6 BubbleCount, validity and update-counter transfers remained operational;
- fixed IEEE-754 value `1.0` was reconstructed correctly;
- fixed IEEE-754 value `12.34` was reconstructed correctly;
- low-word-first register ordering was established;
- EAE `LREAL` was successfully converted to `REAL`;
- one REAL-typed Modbus write successfully populated two registers;
- live `MedianECD` was reconstructed correctly in Control Expert;
- Control Expert communication-freshness and availability logic remained operational;
- the new Modbus write completed without an observed error.

---

## Session outcome

Week 7 Session 1 successfully demonstrated the first live REAL-valued machine-vision measurement transfer from EAE to Control Expert.

The final path is:

```text
MedianECD LREAL
→ LREAL_TO_REAL
→ one REAL MB_WRITE_REGISTERS operation
→ offsets 10–11
→ Control Expert REAL at %MW10
```

The result establishes a reusable method for adding other selected REAL-valued measurements to the interface.

---

## Remaining work

The following work is carried forward:

- integrate `MV_MedianECD` into Control Expert held-last-valid behaviour if required;
- add Control Expert-to-EAE status transfer using Modbus reads;
- combine Control Expert process status with the MV result and validity;
- write the collated result/status back to Control Expert;
- extend the register map to selected additional REAL measurements;
- repeat corrupt-image, server-restart and stale-publication tests with the expanded interface;
- document the final bidirectional register map and status semantics.

