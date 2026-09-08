# Week 8 — Session 1: Cybersecurity Baseline and Interface Hardening

## 1. Session objective


## 2. Starting system state


## 3. Asset inventory


## 4. Zones, conduits and permitted data flows

| Zone            | Assets                                                                        | Trust decision                                                |
| --------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------- |
| MV processing   | Images, Python, configuration, model, OPC-UA server                           | Determines whether a measurement is valid                     |
| EAE supervisory | OPC-UA acquisition, supervisory status, `MV_CE_STATUS`, `MV_SOFT_SENSOR`, HMI | Combines communications, MV and CE status                     |
| PLC monitoring  | CE simulator and supervisory ST logic                                         | Determines whether the received result is currently available |

| Component            | Local endpoint | Remote peer | Purpose                                   |
| -------------------- | -------------- | ----------- | ----------------------------------------- |
| Python OPC-UA server | `host-IP:4841` | EAE runtime | Publishes MV measurements/status          |
| CE Modbus server     | `CE-IP:502`    | EAE runtime | Receives MV values and provides CE status |

| Conduit       | Initiator  | Destination             | Protocol/port | Permitted operation                        |
| ------------- | ---------- | ----------------------- | ------------- | ------------------------------------------ |
| OPC-UA        | EAE        | Python server           | TCP 4841      | Read MV measurements and diagnostic status |
| Modbus EAE→CE | EAE client | CE server               | TCP 502       | Write offsets `0–3` and `10–11`            |
| Modbus CE→EAE | EAE client | CE server               | TCP 502       | Read offset `100`                          |
| Image input   | Pipeline   | Authorised image folder | Filesystem    | Read image files only                      |

| Signal                 | Direction | Offset | CE address/type  |
| ---------------------- | --------- | -----: | ---------------- |
| `MV_BubbleCountWord`   | EAE → CE  |      0 | `%MW0`, `UINT`   |
| `MV_DataValidWord`     | EAE → CE  |      1 | `%MW1`, `UINT`   |
| `MV_UpdateCounter`     | EAE → CE  |      2 | `%MW2`, `INT`    |
| `MV_CollatedValidWord` | EAE → CE  |      3 | `%MW3`, `UINT`   |
| `MV_MedianECD`         | EAE → CE  |  10–11 | `%MW10`, `REAL`  |
| `CE_ProcessReadyWord`  | CE → EAE  |    100 | `%MW100`, `UINT` |


## 5. Current network and protocol exposure

| Service              | Listening address |   Port |     PID | Exposure                                                                                     |
| -------------------- | ----------------: | -----: | ------: | -------------------------------------------------------------------------------------------- |
| Python OPC-UA server |         `0.0.0.0` | `4841` |  `5988` | All IPv4 interfaces; potentially reachable from other LAN devices, subject to firewall rules |
| CE Modbus TCP server |       `127.0.0.1` |  `502` | `38288` | Loopback only; accessible only by processes on this computer                                 |

- OPC-UA port 4841 has broader network exposure because 0.0.0.0 means the server listens on every IPv4 interface.
- Modbus port 502 is currently local-only because it is bound to 127.0.0.1.
- EAE appears to be connecting to OPC-UA through the computer’s LAN address, 192.168.1.117, even though both ends are on the same host.
- At least two local connections use the Modbus server.
- The TIME_WAIT entry is a recently closed connection and is normal; it is not another listening service.

|     PID | Likely role                                                           | Process Name    |
| ------: | --------------------------------------------------------------------: | --------------- |
|  `5988` | Python OPC-UA server                                                  | python          |
| `38288` | Control Expert Modbus/PLC Simulator service                           | sim             |
| `13228` | EAE/SimulationdPAC client communicating with both OPC-UA and ModS TCP | Simulation_dPAC |
|  `7232` | Another local CE/EAE-related Modbus client                            | RatSrv          |


| Interface             | Current configuration                      | Observation                                                                                                                                       |
| --------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| OPC-UA server         | `0.0.0.0:4841`, PID `5988`                 | Listens on every IPv4 interface. It can potentially receive connections from other devices on the local network, subject to the Windows firewall. |
| OPC-UA active client  | `192.168.1.117:63471 → 192.168.1.117:4841` | An application on the same host, PID `13228`, is connected through the host’s LAN address.                                                        |
| Modbus TCP server     | `127.0.0.1:502`, PID `38288`               | Listens only on the loopback interface and is not directly accessible from other network devices.                                                 |
| Modbus TCP clients    | `127.0.0.1:50069` and `127.0.0.1:53952`    | Two local processes are connected to the CE Modbus server.                                                                                        |
| Closed OPC-UA session | Port `4841` entry in `TIME_WAIT`           | Normal record of a recently closed TCP connection; not an additional listening endpoint.                                                          |

Security assessment:
OPC-UA exposure: Partially restricted
Reason: Port 4841 listens on all IPv4 interfaces using 0.0.0.0.
The endpoint is therefore potentially reachable from the local network.
Actual access also depends on Windows firewall rules.

Modbus TCP exposure: Locally restricted
Reason: Port 502 listens only on 127.0.0.1. Modbus communication is
currently confined to processes on the development host.

Current OPC-UA protection:
- Security Policy: None
- Message Security Mode: None
- Authentication: Anonymous

Current Modbus protection:
- Authentication: None
- Encryption: None
- Compensating restriction: loopback-only binding

## 6. Removal of unused OPC-UA write access
The obsolete CommandFromEAE OPC-UA node and its associated monitoring task were removed. The node is no longer present in the server address space. All remaining application nodes are explicitly configured as read-only to external clients, while internal server-side publication continues normally. Removal did not affect Python–EAE–CE operation.

## 7. Modbus Boolean-word validation
## 8. Tests and results
## 9. Initial risk assessment
## 10. Remaining risks and next steps
## 11. Conclusion