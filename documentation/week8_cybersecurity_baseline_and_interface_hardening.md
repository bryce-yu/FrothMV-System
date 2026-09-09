# Week 8 — Session 1: Cybersecurity Baseline and Interface Hardening

**Project:** FrothMV-System  
**Date:** 9 September 2026  
**Status:** Completed successfully  

## 1. Session objective

The objective of Week 8 Session 1 was to establish a cybersecurity baseline for the completed supervisory integration and implement several low-complexity interface-hardening measures before attempting secure OPC-UA communication and firewall allow-listing in later sessions.

The session focused on:

1. identifying the security-relevant system assets;
2. documenting logical zones, conduits, register ownership and existing network exposure;
3. removing the obsolete writable `CommandFromEAE` OPC-UA node;
4. explicitly making all remaining OPC-UA application nodes read-only to external clients;
5. validating Modbus Boolean words as exactly `0` or `1`;
6. ensuring malformed status words produce a safe unavailable state;
7. creating an initial system-specific cybersecurity risk register.

This work is aligned with selected IEC 62443, OT-security and OPC-UA security principles. It does not constitute a formal IEC 62443 risk assessment, compliance claim, certification or achieved Security Level.

## 2. Starting system state

The starting architecture was the Week 7 bidirectional supervisory implementation:

```text
Input images
→ Python YOLOv8-seg / FrothMVPipeline
→ Python asyncua OPC-UA server
→ EAE acquisition and supervisory logic
↔ Modbus TCP
↔ Control Expert PLC Simulator
```

The system remained supervisory only. It did not perform closed-loop process control or operate physical actuators.

The existing cybersecurity and fail-safe controls included:

- SHA-256 verification of `models/best.pt` before inference;
- prevention of inference following model-integrity failure;
- propagation of `PipelineOK = FALSE` and invalid MV status after a failure;
- rejection of corrupt images;
- externally read-only measurement and diagnostic OPC-UA nodes, except for the obsolete `CommandFromEAE` node;
- Python heartbeat supervision in EAE;
- `MV_DataValid` derived from OPC-UA communications, heartbeat and pipeline status;
- independent EAE-to-CE publication freshness using `MV_UpdateCounter` and a five-second stale timer;
- independent CE-to-EAE Modbus read-health assessment;
- collated result validity using MV validity, CE process readiness and CE read health;
- automatic detection and recovery following tested Python, OPC-UA, EAE and PLC Simulator interruptions.

Before the Session 1 changes, CE process status was converted from `UINT` using a general `UINT_TO_BOOL` conversion. This interpreted any nonzero value as `TRUE`, meaning unexpected values such as `2` or `65535` could incorrectly be treated as process ready.

## 3. Asset inventory

The inventory covers assets that can affect measurement integrity, source authenticity, communications, availability decisions or system recovery. Process identifiers and network connections are runtime observations rather than permanent asset identifiers.

| ID | Asset | Zone | Purpose and configuration | Location/interface | Security importance | Existing protection or status |
|---|---|---|---|---|---|---|
| `MV-01` | Python development host | MV processing | Runs the MV pipeline and OPC-UA server; Windows 11 Home 25H2, OS build `26200`; Python `3.12.7` | Development laptop and active IPv4 interface | High integrity and availability | Local account controls, Windows security and project backups |
| `MV-02` | Python runtime | MV processing | `ultralytics==8.4.106`; `opencv-python==5.0.0.93`; `numpy==2.5.1`; `asyncua==2.0.1` | Project Python environment | High integrity and availability | Runtime requirements documented; dependency audit planned |
| `MV-03` | FrothMV source code | MV processing | Implements inference, measurement processing, integrity checks and publication | Repository `src/` | High integrity | Git version control, automated tests and known-good repository history |
| `MV-04` | YOLOv8-seg model | MV processing | Selected segmentation model | `models/best.pt` | High integrity and medium availability | SHA-256 checked before pipeline construction or inference |
| `MV-05` | Trusted model hash | MV processing | Expected SHA-256: `be46622b5251bf43f0151a01bd50bdbc0b28b2fdc4dbc57b91ba4936382613ac` | `models/best.pt.sha256` | High integrity | Version controlled; stronger protection of the trust reference remains future work |
| `MV-06` | MV configuration | MV processing | `conf=0.15`, `imgsz=640`, `max_det=1000`, `min_area=10 px²` | `src/mv/config.py` | High integrity | Frozen, logged and documented configuration |
| `MV-07` | Input image source | MV processing | Supplies images for inference | Authorised image folder/dataset path | High integrity and availability | Supported-extension filtering and corrupt-image rejection; size/rate limits remain future work |
| `MV-08` | Python OPC-UA server | MV processing | Publishes MV measurements and diagnostics through `asyncua` | TCP `4841`; namespace `http://froth.project/test` | High integrity, authenticity and availability | All application nodes are now explicitly read-only externally; current transport remains `None`/anonymous |
| `EAE-01` | EAE engineering environment | EAE supervisory | Builds and deploys the IEC 61499 application | EcoStruxure Automation Expert V25.0.1 | High integrity | Project backups and controlled engineering changes |
| `EAE-02` | SimulationdPAC runtime | EAE supervisory | Executes the EAE application | `EcoRT_0` / `Simulation_dPAC` | High integrity and availability | Communications diagnostics and restart testing |
| `EAE-03` | EAE supervisory application | EAE supervisory | Contains `MV_OPCUA_ACQUISITION`, `MV_SUPERVISORY_STATUS`, `MV_CE_STATUS`, `MV_SOFT_SENSOR` and Modbus exchange logic | EAE project `EAE_OPCUA_MV_Supervisory Layer` | High integrity | Deterministic application-level event sequence and tested validity logic |
| `EAE-04` | CAT HMI | EAE supervisory | Displays MV, CE, communications and overall availability status | EAE/CAT runtime | Medium integrity and availability | Diagnostic statuses remain separately visible |
| `CE-01` | Control Expert engineering environment | PLC monitoring | Develops the CE supervisory application | EcoStruxure Control Expert `V16.2 - 250430` | High integrity | Firmware/data-storage project passwords and project backup |
| `CE-02` | CE supervisory project | PLC monitoring | Calculates communications freshness, validity, availability and alarm state | M580 `BME P58 6040`; rack `BME XBP 0400`; Simulation Mode | High integrity | Structured Text logic, Animation Table and `.ZEF` backup |
| `CE-03` | Control Expert PLC Simulator | PLC monitoring | Executes the simulated PLC application and exposes the local Modbus server | Control Expert PLC Simulator `V16.1`; loopback TCP `502` | High integrity and availability | Loopback-only binding and five-second EAE-publication stale detection |
| `SUP-01` | Git repository | Development support | Maintains source, documentation and change history | Local repository and GitHub | High integrity and recoverability | Version control and remote history |
| `SUP-02` | Project backups | Development support | Restores Python, EAE and CE project state | GitHub, OneDrive and project exports | High availability and recoverability | Known-good source and project copies retained |

### 3.1 Security priorities

| Asset or data | Confidentiality | Integrity | Availability | Primary reason |
|---|---|---|---|---|
| `best.pt` and MV configuration | Low | High | Medium | Alteration could change calculated measurements |
| OPC-UA measurements and status | Low | High | High | False or stale results could mislead supervisory monitoring |
| EAE application | Low | High | High | Produces the collated validity result and controls data exchange |
| CE application | Low | High | High | Produces final availability and alarm status |
| Modbus status words | Low | High | High | Unexpected values could affect readiness or availability decisions |
| Project logs and evidence | Medium | High | Medium | Required to reconstruct events and support test claims |
| Future certificate private keys | High | High | Medium | Disclosure would undermine the associated application identity |

For this supervisory prototype, measurement integrity, availability and source authenticity are higher priorities than measurement confidentiality.

## 4. Zones, conduits and permitted data flows

### 4.1 Logical security zones

The zones are currently logical rather than physically segmented because the components execute within a local development and simulation environment.

| Zone | Assets | Trust decision |
|---|---|---|
| MV processing | Images, Python runtime, configuration, model and OPC-UA server | Determines whether a machine-vision measurement is valid |
| EAE supervisory | OPC-UA acquisition, supervisory status, `MV_CE_STATUS`, `MV_SOFT_SENSOR`, Modbus exchange and HMI | Combines MV validity, communications state and CE process status |
| PLC monitoring | Control Expert project and PLC Simulator | Determines whether the received result is current and available for supervisory use |

### 4.2 Runtime conduits

| Conduit | Initiator | Destination | Protocol/port | Permitted operation |
|---|---|---|---|---|
| OPC-UA | EAE | Python server | TCP `4841` | Read required MV measurements and diagnostic status |
| Modbus EAE→CE | EAE client | CE Modbus server | TCP `502` | Write offsets `0–3` and `10–11` |
| Modbus CE→EAE | EAE client | CE Modbus server | TCP `502` | Read CE-owned offset `100` |
| Image input | Python pipeline | Authorised image folder | Filesystem | Read supported image files for inference |

Although application data travels in both directions over Modbus, EAE remains the Modbus client and initiates both reads and writes.

### 4.3 Register ownership and map

Offsets `0–99` are owned and written by EAE. Offsets `100–199` are owned by Control Expert and read by EAE.

| Signal | Direction | Offset(s) | Control Expert address/type |
|---|---|---:|---|
| `MV_BubbleCountWord` | EAE → CE | `0` | `%MW0`, `UINT` |
| `MV_DataValidWord` | EAE → CE | `1` | `%MW1`, `UINT` |
| `MV_UpdateCounter` | EAE → CE | `2` | `%MW2`, `INT` |
| `MV_CollatedValidWord` | EAE → CE | `3` | `%MW3`, `UINT` |
| `MV_MedianECD` | EAE → CE | `10–11` | `%MW10`, `REAL`, low word first |
| `CE_ProcessReadyWord` | CE → EAE | `100` | `%MW100`, `UINT` |

## 5. Current network and protocol exposure

The baseline was captured while the Python OPC-UA server, EAE SimulationdPAC and Control Expert PLC Simulator were running.

### 5.1 Listening services

| Service | Listening address | Port | Captured PID/process | Exposure |
|---|---:|---:|---|---|
| Python OPC-UA server | `0.0.0.0` | `4841` | `5988` / `python` | Listens on every IPv4 interface and may be reachable from other LAN devices, subject to host firewall rules |
| CE Modbus TCP server | `127.0.0.1` | `502` | `38288` / `sim` | Loopback only and accessible only to processes on the same computer |

The captured supporting processes were:

| Captured PID/process | Observed role |
|---|---|
| `13228` / `Simulation_dPAC` | EAE runtime communicating with OPC-UA and Modbus TCP |
| `7232` / `RatSrv` | Additional local Control Expert/EAE-related Modbus connection |

PIDs are included only as evidence from the captured runtime and may change following process restart.

### 5.2 Active connections

| Interface | Captured configuration | Observation |
|---|---|---|
| OPC-UA listener | `0.0.0.0:4841` | The server was bound to all IPv4 interfaces |
| OPC-UA client connection | `192.168.1.117:63471 → 192.168.1.117:4841` | The local EAE runtime connected through the host LAN address |
| Modbus TCP listener | `127.0.0.1:502` | The CE server was not directly exposed to other LAN devices |
| Modbus TCP clients | Local ephemeral ports to `127.0.0.1:502` | Two local runtime connections were observed |
| OPC-UA `TIME_WAIT` entry | Previously closed local connection | Normal TCP connection cleanup; not another listening service |

### 5.3 Current protocol protection

```text
OPC-UA
- Endpoint: opc.tcp://0.0.0.0:4841/froth-test/
- Security Policy: None
- Message Security Mode: None
- Authentication: Anonymous
- Application nodes: externally read-only

Modbus TCP
- Server binding: 127.0.0.1:502
- Authentication: None
- Encryption: None
- Current compensating restriction: loopback-only communication
```

The primary current network-exposure concern is OPC-UA port `4841`. Secure OPC-UA configuration is planned for Session 2, followed by firewall and endpoint restriction in Session 3. Modbus port `502` is already restricted to the local host in the current simulated arrangement.

## 6. Removal of unused OPC-UA write access

The Week 4 test interface included a writable Boolean node named `CommandFromEAE`. It was no longer required because the final two-way application requirement is satisfied through Modbus TCP using `CE_ProcessReadyWord`.

The following were removed from the Python implementation:

- creation of the `CommandFromEAE` OPC-UA node;
- the call to make that node writable;
- the `read_command()` method;
- the asynchronous `command_monitor()` loop;
- creation and cancellation of the associated command-monitor task.

NodeId `ns=2;i=5`, previously used by the command, was intentionally left unused. Later NodeIds were not renumbered, preserving the existing EAE mappings.

All remaining application nodes were explicitly set read-only:

```python
for node in self.nodes.values():
    await node.set_read_only()
```

Testing confirmed that:

- `CommandFromEAE` was absent from the server address space after restart and client refresh;
- external writes to measurement and diagnostic nodes were rejected;
- Python internal server-side writes continued normally;
- removal did not affect Python–EAE–CE operation.

The resulting Python OPC-UA application interface contains no intentionally externally writable application nodes.

## 7. Modbus Boolean-word validation

### 7.1 EAE validation of CE process status

The previous `UINT_TO_BOOL_CONVERSION` was removed from `MV_CE_STATUS`. A `UINT` comparison block was introduced with:

```text
IN1 = CE_ProcessReadyWord
IN2 = UINT#1
```

Because the input is unsigned, its comparison outputs implement:

```text
CE_ProcessReady     = (CE_ProcessReadyWord = 1)
CE_StatusValueValid = (CE_ProcessReadyWord <= 1)
```

This produces the following interpretation:

| Received `UINT` | `CE_StatusValueValid` | `CE_ProcessReady` |
|---:|---|---|
| `0` | `TRUE` | `FALSE` |
| `1` | `TRUE` | `TRUE` |
| `2` | `FALSE` | `FALSE` |
| `65535` | `FALSE` | `FALSE` |

Communication health remains independently calculated as:

```text
CE_StatusReadOK = CE_ReadQO AND (CE_ReadError = 0)
```

Separating read health from value validation allows the system to distinguish a successful Modbus transaction containing an invalid value from a failed transaction.

The application-level event sequence remained ordered:

```text
MV_OPCUA_ACQUISITION.DATA_UPDATED
→ MV_SUPERVISORY_STATUS.REQ
→ EAE_CE_MODBUS_EXCHANGE.READ_REQ
→ MV_CE_STATUS.REQ
→ MV_SOFT_SENSOR.REQ
→ EAE_CE_MODBUS_EXCHANGE.WRITE_REQ
```

Within `MV_CE_STATUS`, the local event chain became:

```text
REQ
→ STATUS_VALUE_COMPARE
→ ERROR_COMPARE
→ STATUS_READ_OK
→ CE_STATUS_UPDATED
```

### 7.2 Updated EAE collated validity

`CE_StatusValueValid` was added as an input to `MV_SOFT_SENSOR`. Collated validity became:

```text
CollatedResultValid =
    DataValid_IN
    AND CE_ProcessReady_IN
    AND CE_StatusReadOK_IN
    AND CE_StatusValueValid_IN
```

A stale retained `CE_ProcessReadyWord` is still not trusted after communication failure because `CE_StatusReadOK` must also be true.

### 7.3 Control Expert validation of EAE status words

Control Expert was updated to validate `MV_DataValidWord` and `MV_CollatedValidWord` before use:

```iecst
MV_DataValidWordValid :=
    (MV_DataValidWord = 0)
    OR (MV_DataValidWord = 1);

MV_CollatedValidWordValid :=
    (MV_CollatedValidWord = 0)
    OR (MV_CollatedValidWord = 1);

MV_Raw_DataValid :=
    (MV_DataValidWord = 1)
    AND MV_DataValidWordValid;

MV_CollatedValid :=
    (MV_CollatedValidWord = 1)
    AND MV_CollatedValidWordValid;

MV_InterfaceValuesValid :=
    MV_DataValidWordValid
    AND MV_CollatedValidWordValid;

MV_Available :=
    MV_CE_CommsOK
    AND MV_CollatedValid
    AND MV_InterfaceValuesValid;

MV_UnavailableAlarm := NOT MV_Available;
```

The dedicated word-validity signals distinguish a legitimate false status from a malformed register value, even though both safely produce `MV_Available = FALSE`.

## 8. Tests and results

All planned Session 1 tests produced the expected fail-safe behaviour. The values below describe the confirmed observations represented by the test screenshots.

### 8.1 Test 1 — normal operation

With valid MV data, healthy communications and `CE_ProcessReadyWord = 1`:

```text
CE_StatusReadOK             = TRUE
CE_StatusValueValid         = TRUE
CE_ProcessReady             = TRUE
MV_DataValid                = TRUE
CollatedResultValid         = TRUE
MV_DataValidWordValid       = TRUE
MV_CollatedValidWordValid   = TRUE
MV_InterfaceValuesValid     = TRUE
MV_CE_CommsOK               = TRUE
MV_Available                = TRUE
MV_UnavailableAlarm         = FALSE
```

Measurements continued to transfer through the existing register map and the EAE update counter continued changing.

> **Figure 1 placeholder:** Normal-operation EAE/HMI and Control Expert status screenshot.

### 8.2 Test 2 — malformed `CE_ProcessReadyWord = 2`

The CE process-ready word was temporarily set to `2` while the Modbus read remained healthy.

Observed behaviour:

```text
CE_StatusReadOK           = TRUE
CE_StatusValueValid       = FALSE
CE_ProcessReady           = FALSE
CollatedResultValid       = FALSE
MV_CollatedValidWord      = 0
MV_Available              = FALSE
MV_UnavailableAlarm       = TRUE
```

This confirmed that an unexpected nonzero value could no longer be interpreted as `TRUE`.

> **Figure 2 placeholder:** EAE and CE status with `CE_ProcessReadyWord = 2`.

### 8.3 Test 3 — malformed `CE_ProcessReadyWord = 65535`

The maximum `UINT` value was used as a second malformed-input test.

Observed behaviour:

```text
CE_StatusReadOK           = TRUE
CE_StatusValueValid       = FALSE
CE_ProcessReady           = FALSE
CollatedResultValid       = FALSE
MV_CollatedValidWord      = 0
MV_Available              = FALSE
MV_UnavailableAlarm       = TRUE
```

This demonstrated that the validation rejects the complete invalid nonzero range, rather than addressing only the value `2`.

> **Figure 3 placeholder:** EAE and CE status with `CE_ProcessReadyWord = 65535`.

### 8.4 Test 4 — malformed `MV_DataValidWord = 2`

`MV_DataValidWord` was temporarily forced to `2` in Control Expert to verify the receiving-side validation.

Observed behaviour:

```text
MV_DataValidWordValid     = FALSE
MV_Raw_DataValid          = FALSE
MV_InterfaceValuesValid   = FALSE
MV_Available              = FALSE
MV_UnavailableAlarm       = TRUE
```

The test confirmed that Control Expert does not interpret an unexpected nonzero data-valid word as valid. The test force was removed after verification and normal EAE publication was restored.

> **Figure 4 placeholder:** Control Expert Animation Table with `MV_DataValidWord` temporarily forced to `2`.

### 8.5 Regression checks

Following restoration of all normal values:

- Python model-integrity verification passed;
- image processing and internal OPC-UA publication continued;
- EAE acquisition and heartbeat supervision remained operational;
- bidirectional Modbus exchange continued;
- the original register addresses and REAL word order were unchanged;
- `CE_ProcessReadyWord = 0` produced a legitimate not-ready condition with `CE_StatusValueValid = TRUE`;
- `CE_ProcessReadyWord = 1` restored valid process readiness;
- normal collated validity and CE availability recovered automatically;
- no event loop or sequencing fault was introduced.

## 9. Initial cybersecurity risk assessment

This register is a preliminary engineering assessment for the local supervisory prototype. Scores are provisional and may be revised as the likelihood assumptions, impact definitions and later test evidence are refined.

### 9.1 Scoring method

```text
Likelihood: 1 = Low, 2 = Medium, 3 = High
Impact:     1 = Low, 2 = Medium, 3 = High
Risk score: Likelihood × Impact

1–2 = Low
3–4 = Medium
6–9 = High
```

The “current residual” score reflects controls demonstrated by the end of Session 1. A target score is included where further treatment is planned. These values may be changed if a different scoring rationale is adopted.

| ID | Asset/conduit | Threat or failure | Potential consequence | Initial L | Initial I | Initial risk | Controls demonstrated by Session 1 | Current gap / planned treatment | Current residual | Target residual |
|---|---|---|---|---:|---:|---:|---|---|---:|---:|
| `R-01` | `best.pt` and trusted hash | Model or reference altered | Incorrect segmentation and misleading measurements | 2 | 3 | 6 High | SHA-256 verification before inference; failed verification blocks pipeline and produces invalid status | An attacker with write access could alter both model and reference; restrict permissions or use a stronger protected release manifest | 3 Medium | 2 Low |
| `R-02` | OPC-UA conduit | Server impersonation, traffic modification or observation | EAE receives untrusted data or measurement traffic is disclosed | 2 | 3 | 6 High | Local development environment; externally read-only application nodes; security posture logged | `None` policy, no signing/encryption and anonymous access; implement trusted certificates and `SignAndEncrypt` in Session 2 | 6 High | 2 Low |
| `R-03` | Modbus TCP conduit | Unauthorised register read/write | False MV status, CE status or measurement values | 2 | 3 | 6 High | Fixed register ownership; exact Boolean-word validation; current server bound to loopback | Modbus has no native authentication/encryption; retain local restriction and apply allow-listing if network-exposed | 3 Medium | 2 Low |
| `R-04` | CE→EAE status input | Malformed Boolean word interpreted as ready | Invalid CE status contributes to an available result | 2 | 3 | 6 High | Exact `0`/`1` validation tested with `2` and `65535`; invalid values force unavailable | Privileged modification of EAE logic remains outside scope | 2 Low | 2 Low |
| `R-05` | EAE→CE status words | Malformed data-valid or collated-valid word | CE treats corrupted status as valid | 2 | 3 | 6 High | Exact CE-side validation; forced `MV_DataValidWord = 2` safely rejected | Other numeric measurements do not yet have complete CE-side range validation | 2 Low | 2 Low |
| `R-06` | EAE publication | Held register values treated as current after EAE stops | Stale data remains available to monitoring logic | 2 | 3 | 6 High | Update counter and intentional five-second CE stale timer | Counter demonstrates EAE publication, not a genuinely new Python inference; add Python result sequence/freshness | 2 Low | 2 Low |
| `R-07` | Python inference results | Pipeline remains alive but no new image result is produced | Old measurement may be repeatedly presented while heartbeat remains active | 2 | 3 | 6 High | Pipeline status and heartbeat are independently monitored | Add per-result sequence number and measurement freshness timeout | 6 High | 2 Low |
| `R-08` | Image input | Corrupt, unsupported, oversized or excessive input | Invalid measurements, processing delay or resource exhaustion | 2 | 2 | 4 Medium | Supported-extension filtering, decode/error handling and invalidity propagation | Add file-size, dimension, finite-value and input-rate validation | 3 Medium | 2 Low |
| `R-09` | Python OPC-UA host interface | Unauthorised LAN host reaches port `4841` | Connection attempts, information exposure or availability impact | 2 | 3 | 6 High | Not publicly exposed; application nodes read-only | Listener uses `0.0.0.0`; implement secure OPC-UA and host-firewall source restrictions | 6 High | 2 Low |
| `R-10` | Python dependencies | Known-vulnerable or unexpected dependency version | Application compromise, failure or unreliable behaviour | 2 | 2 | 4 Medium | Known Python environment and requirements documentation | Pin tested versions and run `pip-audit`; regression-test any upgrades | 4 Medium | 2 Low |
| `R-11` | Python, EAE or CE runtime | Component interruption or communication loss | MV result becomes unavailable | 2 | 2 | 4 Medium | Heartbeat, read-health status, collated validity, update freshness and tested automatic recovery | Timings remain visually estimated; formal synchronized measurement is future work | 2 Low | 2 Low |
| `R-12` | Project files and configuration | Loss or unauthorised engineering change | Inability to reproduce or restore known-good operation | 2 | 3 | 6 High | Git history, remote repository, project copies and CE/EAE exports | Complete a documented restoration test and record approval/change responsibilities | 3 Medium | 2 Low |

### 9.2 Bounded threat model

The prototype aims to resist or detect:

- accidental or unsophisticated modification of the model or configuration;
- malformed application values;
- casual unauthorised access from another device on the development network;
- use of stale or invalid supervisory measurements;
- interruption of Python, OPC-UA, EAE or Control Expert;
- untrusted OPC-UA connection attempts after the planned secure-channel work.

Explicitly outside the demonstrated scope are:

- privileged compromise of the Windows host;
- physical-access attacks;
- advanced persistent threats;
- determined denial-of-service attacks;
- compromise of vendor software, the operating system or dependency repositories;
- formal IEC 62443 compliance, certification or Security Level achievement.

## 10. Alignment with selected IEC 62443 principles

| Foundational requirement | Session 1 contribution | Status |
|---|---|---|
| FR1 — Identification and authentication control | Assets and connection endpoints identified; certificate-based OPC-UA authentication planned | Partial/future |
| FR2 — Use control | Obsolete writable command removed; remaining OPC-UA application nodes explicitly read-only | Demonstrated for the prototype interface |
| FR3 — System integrity | Model hashing, fixed configuration and strict Boolean-word validation | Demonstrated in selected areas |
| FR4 — Data confidentiality | Current OPC-UA and Modbus traffic remains unencrypted | Not implemented; OPC-UA treatment planned |
| FR5 — Restricted data flow | Logical zones, conduits, register ownership and current listening interfaces documented | Partial; firewall allow-listing remains planned |
| FR6 — Timely response to events | Invalid words, read failures, heartbeat loss and stale publication produce diagnostic/unavailable states | Demonstrated in selected tests |
| FR7 — Resource availability | Independent liveness/freshness monitoring and automatic recovery retained | Demonstrated for tested component interruptions; resource-exhaustion controls remain future work |

This mapping is used to show cybersecurity-informed engineering decisions rather than satisfaction of every system requirement associated with an IEC 62443 Security Level.

## 11. Remaining risks and next steps

The highest-priority residual risks at the end of Session 1 are:

1. OPC-UA still uses Security Policy `None`, Message Security Mode `None` and anonymous access.
2. OPC-UA listens on all IPv4 interfaces through `0.0.0.0:4841`.
3. The Python heartbeat does not prove that a genuinely new inference result has been produced.
4. The trusted model hash is not protected against simultaneous modification with the model.
5. Input size, image dimensions, result finiteness and processing rate are not yet bounded.
6. Python security events are not yet retained in a structured rotating log.
7. Runtime dependencies require exact version pinning and vulnerability review.

Planned next work is:

- **Session 2:** determine EAE security capabilities and implement the strongest mutually supported OPC-UA certificate and `SignAndEncrypt` configuration;
- **Session 3:** implement and test network/interface restriction and firewall allow-listing for TCP `4841`, retaining the existing loopback-only Modbus arrangement;
- **later Week 8/9 work:** add Python-originated measurement sequence/freshness, input and measurement validation, durable security-event logging, dependency auditing and restoration evidence.

## 12. Conclusion

Week 8 Session 1 established a documented cybersecurity baseline and strengthened both communication interfaces without changing the supervisory architecture or register map. The obsolete writable OPC-UA command path was removed, leaving all application nodes externally read-only. EAE and Control Expert were updated to accept Boolean Modbus words only when encoded as exactly `0` or `1`.

Normal operation remained successful. Malformed values `2` and `65535` for `CE_ProcessReadyWord` were rejected despite healthy Modbus communication, and a forced `MV_DataValidWord = 2` was rejected in Control Expert. In each negative test, availability became false and the unavailable alarm asserted, demonstrating fail-safe handling rather than interpreting an unexpected nonzero value as true.

The completed asset inventory, zones-and-conduits definition, network-exposure capture and preliminary risk register provide the basis for the next priority: securing the OPC-UA conduit and restricting its network exposure. The system remains a local supervisory prototype aligned with selected IEC 62443 principles, with no claim of formal compliance or an achieved Security Level.

## 13. References

1. IEC, *IEC 62443 cybersecurity guidance and foundational requirements*: <https://syc-se.iec.ch/deliveries/cybersecurity-guidelines/security-standards-and-best-practices/iec-62443/>.
2. OPC Foundation, *OPC Unified Architecture — Part 2: Security Model*: <https://reference.opcfoundation.org/specs/OPC-10000-2/4>.
3. NIST, *SP 800-82 Revision 3: Guide to Operational Technology Security*: <https://doi.org/10.6028/NIST.SP.800-82r3>.
4. CISA, *Schneider Electric Modicon security guidance*, including segmentation and restriction of unauthorised TCP `502` access: <https://www.cisa.gov/news-events/ics-advisories/icsa-24-352-04>.
