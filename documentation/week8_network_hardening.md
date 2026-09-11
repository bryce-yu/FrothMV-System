# Week 8 – Session 3: Network Exposure and Host Hardening

**Date:** 11 September 2026  
**System:** FrothMV supervisory soft-sensor  
**Session focus:** OPC-UA network restriction, firewall verification and dependency consistency

---

## 1. Session objectives

The objectives of this session were to:

- establish the current exposure of OPC-UA port `4841` and Modbus TCP port `502`;
- identify the applications and processes using both conduits;
- reduce unnecessary OPC-UA network exposure without disrupting EAE operation;
- verify the restriction from a second network host;
- confirm that Modbus TCP remained local to the development machine; and
- perform an initial Python dependency-consistency check.

This work supports selected IEC 62443 principles relating to restricted data flow, least functionality, system integrity and resource availability. It does not constitute IEC 62443 compliance or certification.

---

## 2. Initial network exposure assessment

The network checks were performed while the Python pipeline, EAE Simulation dPAC and Control Expert PLC Simulator were operating normally.

### 2.1 Listening services

The initial listener state was:

| Protocol/conduit | Local address | Port | Process | Initial assessment |
|---|---:|---:|---|---|
| OPC-UA | `0.0.0.0` | `4841` | Python | Listening on every IPv4 interface; broader than required |
| Modbus TCP | `127.0.0.1` | `502` | Control Expert PLC Simulator | Restricted to the local host |

The OPC-UA connection between EAE and Python appeared as:

```text
192.168.1.117:<dynamic-port> -> 192.168.1.117:4841
```

The EAE Simulation dPAC therefore connected from the same host address used by the Python server.

The active Modbus connections appeared only on loopback addresses:

```text
127.0.0.1:<dynamic-port> -> 127.0.0.1:502
```

This confirmed that the simulated EAE–Control Expert Modbus conduit was not exposed through the physical network interfaces.

### 2.2 Process ownership

The relevant processes were identified as:

| Process | Function |
|---|---|
| `python` | FrothMV inference and OPC-UA server |
| `Simulation_dPAC` | EAE simulated runtime and OPC-UA client |
| `sim` | Control Expert PLC Simulator and Modbus TCP server |
| `RatSrv` | Schneider Electric supporting process |

Windows reported the Python process image as:

```text
C:\Users\bgyu5\anaconda3\python.exe
```

The intended project environment was separately confirmed from the activated project terminal as:

```text
Executable:  C:\PythonEnvironments\FrothMV-venv\Scripts\python.exe
Environment: C:\PythonEnvironments\FrothMV-venv
asyncua:     2.0.1
```

This confirmed that the project commands used the documented `FrothMV-venv`. The base Anaconda process path reported by Windows was retained in the firewall application filter because it was the process image observed by the host firewall.

---

## 3. Host network and firewall baseline

The active Wi-Fi configuration was:

| Property | Observed value |
|---|---|
| Interface | Wi-Fi |
| IPv4 address | `192.168.1.117/24` |
| Network category | Public |
| IPv4 connectivity | Internet |

Additional VMware interfaces were present at:

- `192.168.124.1/24`; and
- `192.168.72.1/24`.

All Windows Firewall profiles were enabled. The active Public profile used:

```text
BlockInbound,AllowOutbound
```

This provided a default inbound-deny posture, but several explicit allow rules overrode it.

### 3.1 Initial relevant firewall rules

The initial inspection identified:

- two duplicate `FrothMV OPC UA Test` rules allowing inbound TCP port `4841`;
- both rules applied to any firewall profile, program, local address and remote address;
- a broad Public-profile Anaconda Python rule allowing inbound TCP on any local port from any remote address; and
- other broad Python rules associated with an older Python 3.9 installation.

The combination of the `0.0.0.0` server binding and broad allow rules exposed the OPC-UA service more widely than required, even though Session 2 had already added encryption and authentication.

---

## 4. OPC-UA listener restriction

The Python OPC-UA endpoint was changed from:

```text
opc.tcp://0.0.0.0:4841/froth-test/
```

to:

```text
opc.tcp://192.168.1.117:4841/froth-test/
```

This address was selected because it:

- was already used by the EAE client;
- was present in the server certificate generated during Session 2; and
- prevented the service from listening on the VMware interfaces.

After restarting the Python server, the listener was confirmed as:

```text
LocalAddress : 192.168.1.117
LocalPort    : 4841
State        : Listen
```

EAE reconnected successfully, and the existing measurement, heartbeat and validity signals continued to operate normally.

---

## 5. Restricted Windows Firewall rule

A new inbound firewall rule named `FrothMV OPC UA Secure` was created.

| Rule property | Configured value |
|---|---|
| Display name | `FrothMV OPC UA Secure` |
| Enabled | Yes |
| Direction | Inbound |
| Action | Allow |
| Protocol | TCP |
| Local port | `4841` |
| Local address | `192.168.1.117` |
| Permitted remote address | `192.168.1.117` |
| Program | `C:\Users\bgyu5\anaconda3\python.exe` |
| Firewall profile | Public |
| Edge traversal | Blocked |

The rule permits the observed local EAE client connection while restricting the service by protocol, port, local interface, remote source, application and active firewall profile.

### 5.1 Superseded rules

The following broader rules were disabled rather than deleted so that they could be restored if testing failed:

- both duplicate `FrothMV OPC UA Test` rules; and
- the broad Anaconda Python inbound TCP rule.

The final FrothMV rule state was:

| Rule | Enabled | Profile | Direction | Action |
|---|---:|---|---|---|
| `FrothMV OPC UA Test` | No | Any | Inbound | Allow |
| `FrothMV OPC UA Test` | No | Any | Inbound | Allow |
| `FrothMV OPC UA Secure` | Yes | Public | Inbound | Allow |

The disabled rules were retained as a recoverable configuration until the restricted rule had been validated.

---

## 6. Firewall verification

### 6.1 Permitted local operation

Following the firewall changes, the Python OPC-UA server was stopped and restarted to ensure that EAE had to establish a new TCP and OPC-UA session.

The following behaviour was confirmed:

- EAE reconnected successfully using the secured OPC-UA configuration;
- the OPC-UA connection remained signed, encrypted and username/password authenticated;
- measurement values continued through the EAE acquisition and supervisory composites;
- `MV_CommsOK`, `MV_HeartbeatOK` and `MV_DataValid` recovered normally; and
- the firewall change did not disrupt the local Modbus connection or Control Expert monitoring.

### 6.2 Rejected external connection

A second laptop on the same Wi-Fi network was used to test port `4841`.

| Test property | Result |
|---|---|
| Python host | `192.168.1.117` |
| Test laptop source | `192.168.1.119` |
| Ping to Python host | Successful, approximately 4 ms |
| TCP connection to port `4841` | Failed |
| `TcpTestSucceeded` | `False` |

The successful ping established that the second laptop had general network connectivity to the Python host. The failed TCP connection therefore provided direct evidence that access to OPC-UA port `4841` was specifically restricted rather than the host simply being unreachable.

At the same time, the local EAE client continued to communicate successfully from the permitted address `192.168.1.117`.

---

## 7. Dependency consistency check

The Python runtime environment was checked using:

```powershell
python -m pip check
```

The result was:

```text
No broken requirements found.
```

This confirmed that the installed `FrothMV-venv` contained no dependency conflicts or unsatisfied package requirements detectable by `pip`.

`pip-audit` was not installed, so a known-vulnerability audit was not performed during this session. No additional audit packages were installed into the validated runtime environment. Vulnerability review therefore remains a future task rather than being reported as completed.

---

## 8. Verification summary

| Verification item | Expected result | Observed result | Outcome |
|---|---|---|---|
| Modbus listener exposure | Local host only | Port `502` bound to `127.0.0.1` | Pass |
| Restricted OPC-UA listener | Wi-Fi address only | Port `4841` bound to `192.168.1.117` | Pass |
| Normal EAE operation | Secure connection retained | Measurements and validity remained operational | Pass |
| Broad FrothMV rules | Disabled | Both duplicate test rules disabled | Pass |
| Restricted firewall rule | Enabled | Public-profile secure rule enabled | Pass |
| External host test | TCP `4841` rejected | Source `192.168.1.119` blocked | Pass |
| General network reachability | Host remains reachable | Ping succeeded | Pass |
| Dependency consistency | No broken requirements | `pip check` passed | Pass |

---

## 9. Cybersecurity checklist update

| Checklist control | Status after Session 3 |
|---|---|
| Confirm port `502` is not externally exposed | ✓ Demonstrated |
| Confirm port `4841` is not generally network-accessible | ✓ Demonstrated for tested external host |
| Avoid binding OPC-UA to `0.0.0.0` where unnecessary | ✓ Implemented |
| Restrict firewall by required port and protocol | ✓ Implemented |
| Restrict firewall by source address | ✓ Implemented |
| Restrict firewall by application | ✓ Implemented |
| Test permitted EAE communication after hardening | ✓ Demonstrated |
| Test an unexpected external connection | ✓ Demonstrated safely |
| Confirm Python dependency consistency | ✓ Demonstrated |
| Audit dependencies for known vulnerabilities | ☐ Not completed |
| Review unrelated legacy Python firewall rules | ◐ Future host-maintenance task |

---

## 10. Risk treatment update

The Session 3 controls reduced the likelihood of:

- unauthorised network clients reaching the OPC-UA service;
- exposure of OPC-UA through unintended VMware interfaces;
- unnecessary access to port `4841` from other Wi-Fi hosts;
- reliance on broad, application-wide inbound Python permissions; and
- undetected dependency conflicts in the runtime environment.

The controls complement the Session 2 encryption and authentication measures. Session 2 protected the OPC-UA secure channel and user session, while Session 3 reduced which hosts and interfaces could reach that secure endpoint.

Residual risks include:

- the permitted source address is tied to the current single-host simulation architecture;
- the static address and server certificate must be updated if the host IP changes;
- unrelated Python 3.9 and UDP firewall rules remain outside the immediate FrothMV TCP conduit scope;
- an explicit dependency vulnerability audit has not been completed;
- firewall logging of allowed and dropped connections is not enabled; and
- future distributed deployment would require revised source-address rules rather than reuse of the current local-only allow-list.

---

## 11. Evidence retained

Recommended Session 3 evidence includes:

1. Initial TCP listener and established-connection output.
2. Process ownership output for Python, EAE and Control Expert.
3. Windows Firewall profile configuration.
4. Initial broad Python and FrothMV rule details.
5. Restricted OPC-UA listener on `192.168.1.117:4841`.
6. Final FrothMV firewall-rule state.
7. Successful local EAE operation after firewall restriction.
8. Second-laptop `Test-NetConnection` result showing successful ping and failed TCP access.
9. Activated `FrothMV-venv` executable, environment and `asyncua` version output.
10. Successful `pip check` result.

---

## 12. Session outcome

Week 8 Session 3 successfully reduced the network exposure of the FrothMV supervisory system without disrupting its normal operation.

OPC-UA was changed from listening on all IPv4 interfaces to listening only on `192.168.1.117`. Broad and duplicate project firewall permissions were superseded by a rule restricted to the required TCP port, local interface, observed EAE source address, Python process and active Public profile.

The permitted local EAE connection continued to operate normally, while a connection attempt from the second laptop at `192.168.1.119` was rejected. Because ping to the host remained successful, this provided direct evidence of port-specific restricted data flow.

Modbus TCP remained bound to `127.0.0.1`, and `pip check` found no broken Python requirements. A formal dependency vulnerability audit was deferred because `pip-audit` was not installed.

The session therefore provides practical evidence of network segmentation and restricted data flow aligned with selected IEC 62443 principles. It does not establish IEC 62443 compliance, certification or a formal security level.
