# FrothMV-System — Week 6 Session 1 Cybersecurity Assessment

## 1. Purpose

This document records the initial cybersecurity assessment for the FrothMV-System prototype. It applies selected operational-technology cybersecurity principles to the system architecture before further EAE-to-Control Expert integration and future hardware deployment.

The assessment is informed by:

- IEC 62443 concepts for industrial automation and control system security;
- IEC 62443-3-2 concepts of system definition, risk assessment, zones and conduits;
- IEC 62443-3-3 system-security principles;
- the OPC UA security model;
- general defence-in-depth practices for IT/OT systems.

This work demonstrates that cybersecurity has been considered during system design. It does **not** claim full IEC 62443 compliance, certification or achievement of a formal IEC 62443 Security Level.

---

## 2. System scope

The system under consideration extends from image input through machine-vision processing and supervisory presentation:

```text
Froth images
    ↓
YOLOv8-seg / FrothMVPipeline
    ↓
Python OPC UA server
    ↓
MV_OPCUA_ACQUISITION
    ↓
MV_SUPERVISORY_STATUS
    ↓
MV_SOFT_SENSOR
    ├── CAT HMI
    └── Proposed EAE-to-Control Expert interface
            ↓
      Control Expert PLC Simulator
```

The current prototype provides supervisory measurements only. Its outputs are not used for automatic closed-loop process control.

### 2.1 Included in this assessment

- Froth-image inputs;
- Python 3.12.7 environment;
- YOLOv8-seg model `models/best.pt`;
- `FrothMVPipeline` and its frozen configuration;
- Python `asyncua` OPC UA server;
- EAE `MV_OPCUA_ACQUISITION`;
- EAE `MV_SUPERVISORY_STATUS`;
- EAE `MV_SOFT_SENSOR` and CAT HMI;
- proposed Modbus TCP connection to the Control Expert PLC Simulator;
- project files, configurations, dependencies and communication settings.

### 2.2 Currently outside scope

- a live froth-flotation process;
- physical sensors and actuators;
- closed-loop control actions;
- a production plant network;
- physical PLC and industrial-PC deployment;
- enterprise identity-management infrastructure;
- formal penetration testing;
- formal IEC 62443 conformity assessment or certification.

---

## 3. Cybersecurity priorities

The priorities for this supervisory machine-vision system are:

1. **Integrity** — measurements, the ML model, software and configuration should not be altered without authorisation or detection.
2. **Availability** — processing and communication failures should be detected, with affected measurements marked invalid.
3. **Authenticity** — receiving components should be able to establish that data originate from the intended system component.
4. **Confidentiality** — froth measurements are not highly sensitive, but credentials, certificates, network configuration and project files should still be protected.

Incorrect data that appear valid could mislead an operator. For this reason, undetected loss of integrity may be more significant than a clearly indicated loss of communication.

---

## 4. Asset inventory

| Asset | Purpose | Current protection/evidence | Main concern |
|---|---|---|---|
| `models/best.pt` | YOLOv8-seg inference model | Fixed model path; project storage | Replacement, modification or corruption |
| Frozen MV configuration | Defines the validated processing method | Documented values and regression tests | Unrecorded parameter changes |
| Python source code | Inference, metric calculation and publishing | Git version control | Unauthorised or accidental modification |
| Python dependencies | Provide ML, image-processing and OPC UA functionality | `requirements.txt`/virtual environment | Vulnerable, incompatible or untrusted packages |
| Froth images | Input to the MV pipeline | Extension handling and corrupt-image tests | Malformed, unauthorised or excessive input |
| Python OPC UA server | Publishes metrics, heartbeat and pipeline status | Local development environment | Unauthorised access, spoofing or tampering |
| EAE project | Acquires data and evaluates validity | Project files and watch-window validation | Logic or configuration modification |
| `MV_SUPERVISORY_STATUS` | Produces communication, heartbeat and overall validity states | Tested fault-handling behaviour | Failure to detect all stale or false data cases |
| `MV_SOFT_SENSOR` | Unified measurement/status interface | Implemented and validated | Invalid data displayed without clear indication |
| CAT HMI | Operator-facing presentation | Live-value and status validation | Operator trusting stale or invalid information |
| Control Expert project | Future PLC supervisory monitoring | Not yet implemented | Incorrect mapping, stale data or unauthorised writes |
| Git/OneDrive repository | Versioning, portability and recovery | Existing project workflow | Exposure of secrets or loss of known-good versions |

### 4.1 Frozen MV configuration

The validated configuration is:

```text
Model: models/best.pt
Confidence: 0.15
Image size: 640
Maximum detections: 1000
Minimum contour area: 10 px²
```

Changes to these values can affect the meaning of the published measurements and should therefore be controlled and recorded.

---

## 5. Logical security zones

The prototype is divided into logical zones using IEC 62443-inspired system-design concepts.

### Zone 1 — Machine-vision processing zone

Contains:

- image source;
- Python runtime and dependencies;
- `FrothMVPipeline`;
- `models/best.pt`;
- Python OPC UA server.

Primary security requirements:

- protect model, source code and configuration integrity;
- validate image inputs;
- restrict access to the OPC UA server;
- detect processing and publication failures.

### Zone 2 — EAE supervisory zone

Contains:

- SimulationdPAC/EcoRT runtime;
- `MV_OPCUA_ACQUISITION`;
- `MV_SUPERVISORY_STATUS`;
- `MV_SOFT_SENSOR`;
- CAT HMI.

Primary security requirements:

- accept data only from the intended MV source;
- detect connection, heartbeat and pipeline failures;
- distinguish valid measurements from retained invalid values;
- prevent unauthorised engineering changes.

### Zone 3 — PLC monitoring zone

Contains:

- Control Expert application;
- Control Expert PLC Simulator;
- future physical Control Expert PLC.

Primary security requirements:

- receive only the required measurements and status values;
- detect EAE-to-PLC communication failure separately;
- prevent invalid or stale measurements from being treated as trustworthy;
- restrict unnecessary write access.

### Prototype limitation

These zones may initially run on the same engineering computer. They are therefore logical rather than physically separated zones. The model nevertheless defines the intended trust boundaries and supports future separation across an IPC, EAE runtime and physical PLC.

---

## 6. Communication conduits and data flows

| Conduit | Source → destination | Protocol/port | Required data | Direction | Current security state |
|---|---|---|---|---|---|
| C1 | Image source → Python pipeline | Local file access | Froth images | Input to Python | File/error handling implemented; source trust not formally controlled |
| C2 | Python → EAE | OPC UA, TCP `4841` | Measurements, heartbeat, `PipelineOK` | Primarily Python → EAE | Security Policy None, Message Security Mode None, anonymous access |
| C3 | EAE acquisition → status/soft sensor/HMI | IEC 61499 internal event/data flow | Measurements and status | Internal | Controlled within the EAE runtime/project |
| C4 | EAE → Control Expert Simulator | Proposed Modbus TCP, TCP `502` | Selected measurements and validity/status | Primarily EAE → PLC | Local simulation planned; mapping not yet implemented |

Only the ports, endpoints and variables required for these conduits should be exposed.

---

## 7. Existing cybersecurity-related controls

The following existing project features contribute to cybersecurity or operational resilience:

- Git-based source and documentation version control;
- frozen and documented MV inference configuration;
- regression testing of the selected measurement method;
- explicit corrupt-image handling;
- `PipelineOK` indicates Python processing validity;
- incrementing Python heartbeat;
- EAE heartbeat watchdog with a stale threshold of five cycles;
- `MV_CommsOK` indicates Python-to-EAE communication state;
- `MV_HeartbeatOK` indicates source liveness;
- `MV_DataValid` combines communication, heartbeat and pipeline status;
- CAT HMI displays communication, heartbeat, pipeline and data-validity states;
- Python server restart and communication-loss tests;
- portability testing across two development laptops;
- supervisory-only scope, with no automatic control action.

The overall validity relationship is:

```text
MV_DataValid = MV_CommsOK AND MV_HeartbeatOK AND PipelineOK
```

This logic addresses availability and some freshness failures. It does not by itself authenticate the data source or prevent deliberate data modification.

---

## 8. OPC UA security assessment

### 8.1 Current development configuration

```text
Endpoint: opc.tcp://<host>:4841/froth-test/
Security Policy: None
Message Security Mode: None
User authentication: Anonymous
```

This configuration was selected to establish interoperability between Python and EAE in an isolated development environment.

### 8.2 Identified limitations

The current configuration does not provide:

- cryptographic verification of the Python OPC UA server identity;
- protection against message modification;
- encryption of measurement data;
- individual user/client accountability;
- strong restriction of unauthorised OPC UA clients.

### 8.3 Secure deployment target

A future deployment should assess:

- OPC UA `Sign` or preferably `SignAndEncrypt`;
- the strongest mutually supported Security Policy;
- application-instance certificates;
- controlled certificate trust lists;
- rejection of unknown or expired certificates;
- named users or application identities instead of anonymous access;
- protection and renewal of private keys and certificates;
- firewall restriction to authorised hosts;
- read-only external access to measurement nodes;
- logging of sessions, rejected certificates and security errors.

The current `None`/anonymous configuration is retained only as a documented prototype limitation unless secure OPC UA is explicitly implemented and revalidated.

---

## 9. Proposed Modbus TCP security assessment

The proposed EAE-to-Control Expert connection will initially use local Modbus TCP simulation.

Modbus TCP does not inherently provide encryption or strong endpoint/user authentication. The design should therefore:

- keep the connection local or within a segmented network;
- prevent internet exposure of TCP port `502`;
- restrict communication to the intended EAE and Control Expert hosts;
- expose only required registers;
- maintain a primarily EAE-to-Control Expert data direction;
- validate register types, word order and permissible ranges;
- provide a separate EAE-to-Control Expert communication-health indication;
- require both EAE data validity and EAE-to-Control Expert communication health before PLC use;
- restrict and validate any future Control Expert-to-EAE command;
- place command signals in a safe inactive state following failure.

A suitable PLC-side availability condition is:

```text
MV_Available = MV_DataValid AND EAE_CE_CommsOK
```

---

## 10. Initial risk register

The ratings below are qualitative development priorities, not formal IEC 62443 Security Levels.

| Threat or failure | Possible consequence | Existing control | Additional treatment | Initial priority |
|---|---|---|---|---|
| `best.pt` replaced or modified | Incorrect but plausible MV measurements | Fixed path and repository history | SHA-256 verification and file-permission control | Medium |
| MV configuration changed | Measurement method no longer matches validated baseline | Frozen settings documented | Log active configuration at startup | Medium |
| Corrupt or unsupported image | Processing failure or invalid results | Corrupt-image handling and `PipelineOK` | Validate source, type, size and dimensions | Low–Medium |
| Excessive or oversized inputs | Resource exhaustion or delayed updates | Sequential processing | Input-rate and size limits | Medium |
| Python server stops | EAE retains stale values | Heartbeat watchdog and `MV_DataValid` | Clear data-age indication and recovery procedure | Medium |
| Old sample mistaken for a new sample | Operator trusts stale data | Server heartbeat | Measurement timestamp or sequence number | Medium |
| OPC UA server spoofing | False measurements accepted by EAE | Isolated prototype network | Certificates and signed messages | Medium in prototype; High if deployed openly |
| OPC UA message modification | Altered measurements or status | None in current Security Policy | `Sign`/`SignAndEncrypt` | Medium in prototype; High if deployed openly |
| Unauthorised OPC UA client | Unauthorised reading or writing | Local development arrangement | Firewall rules, authentication and read-only nodes | Medium |
| EAE-to-Control Expert connection loss | PLC retains outdated values | Not yet implemented | Separate `EAE_CE_CommsOK` and validity gating | Medium |
| Unauthorised Modbus access | PLC measurements/registers altered | Local simulation planned | Segmentation, allow-listing and minimum register exposure | Medium |
| Credentials or keys committed to Git | Unauthorised access | No credentials currently required for anonymous OPC UA | `.gitignore`, secret review and protected key storage | Medium |
| Loss of project files | Delayed recovery or loss of configuration | Git/OneDrive workflow | Known-good backups and restore test | Low–Medium |

---

## 11. Mapping to selected IEC 62443 principles

| Principle | Current evidence | Identified gap or future action |
|---|---|---|
| Identification and authentication control | Components and endpoints are known within the prototype | OPC UA currently permits anonymous access |
| Use control/least privilege | Predominantly one-way supervisory data flow | Confirm measurement nodes are externally read-only and restrict command writes |
| System integrity | Frozen model/configuration and regression tests | Add model hash verification and startup configuration logging |
| Data confidentiality | Local isolated prototype | Use encryption if deployed across an untrusted network |
| Restricted data flow | Required OPC UA and proposed Modbus conduits identified | Implement host/port restrictions and future network segmentation |
| Timely response to events | `PipelineOK`, communication status, heartbeat watchdog and CAT indicators | Extend logging and define operator/maintenance response |
| Resource availability | Heartbeat-loss and server-restart behaviour validated | Consider resource exhaustion, backup and formal recovery procedures |

---

## 12. Selected achievable controls for Week 6

Full implementation of every identified cybersecurity control is outside the current prototype scope. The following controls provide useful, achievable evidence of cybersecurity-by-design:

1. Calculate and verify a trusted SHA-256 hash of `models/best.pt` at Python server startup.
2. Log the active model path, model hash and frozen MV configuration at startup.
3. Confirm that OPC UA measurement nodes cannot be written by external clients.
4. Keep local OPC UA and Modbus ports restricted to required interfaces/hosts where practical.
5. Implement Control Expert validity gating using `MV_DataValid` and a separate EAE-to-Control Expert communication-health signal.
6. Test and document behaviour following invalid images, heartbeat loss, Python shutdown and EAE-to-Control Expert communication loss.

### Future rather than immediate requirements

- full OPC UA certificate deployment;
- `SignAndEncrypt` implementation and interoperability testing;
- removal of anonymous access;
- formal target Security Level assessment;
- physical IT/OT network segmentation;
- IPC and PLC operating-system/device hardening;
- secure remote-access infrastructure;
- formal vulnerability or penetration testing.

---

## 13. Verification evidence to retain

The following evidence should be captured during later Week 6 sessions:

- model hash and startup-configuration log;
- OPC UA node-access test results;
- EAE and Control Expert communication screenshots;
- Modbus register map;
- valid five-image end-to-end test;
- corrupt-image test;
- heartbeat-loss test;
- Python server shutdown/restart test;
- EAE-to-Control Expert communication-loss test;
- confirmation that invalid or stale measurements are not treated as trustworthy;
- updated risk register showing implemented, accepted and deferred treatments.

---

## 14. Current conclusion

The FrothMV-System already contains several availability and fault-detection controls through `PipelineOK`, heartbeat supervision, communications monitoring and `MV_DataValid`. The primary current cybersecurity limitations are the OPC UA `None`/anonymous development configuration, lack of cryptographic model-integrity verification, and the absence of a completed EAE-to-Control Expert communication-health mechanism.

For the local prototype, these limitations can be managed through isolation, restricted communication, clear documentation and validity-aware supervisory logic. Future hardware or plant-network deployment would require stronger authentication, signed/encrypted OPC UA communication, network segmentation, device hardening and formal operational-security procedures.

---

## 15. References

- IEC, *IEC 62443-3-2:2020 — Security risk assessment for system design*: <https://webstore.iec.ch/en/publication/30727>
- IEC, *IEC 62443 cybersecurity guidelines and overview*: <https://syc-se.iec.ch/deliveries/cybersecurity-guidelines/security-standards-and-best-practices/iec-62443/>
- ISA, *ISA/IEC 62443 Series of Standards*: <https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards>
- OPC Foundation, *OPC Unified Architecture Part 2 — Security Model*: <https://reference.opcfoundation.org/Core/Part2/>
- NIST, *SP 800-82 Rev. 3 — Guide to Operational Technology Security*: <https://csrc.nist.gov/pubs/sp/800/82/r3/final>

