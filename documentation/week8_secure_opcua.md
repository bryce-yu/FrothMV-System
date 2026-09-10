# Week 8 – Session 2: Secure OPC-UA Communication

**Date:** 10 September 2026  
**System:** FrothMV supervisory soft-sensor  
**Session focus:** OPC-UA encryption, authentication, certificates and security testing

---

## 1. Session objectives

The objectives of this session were to replace the original development-only OPC-UA configuration with a secured configuration and verify that:

- OPC-UA messages are signed and encrypted.
- EAE must provide valid user credentials.
- Anonymous access is disabled.
- Incorrect credentials are rejected.
- The connection cannot silently downgrade to an unsecured endpoint.
- The existing measurement, validity and recovery behaviour continues to operate after security is enabled.

This work provides evidence of alignment with selected IEC 62443 and OPC-UA security principles. It does not constitute IEC 62443 compliance, certification or assignment of a formal security level.

---

## 2. Initial OPC-UA security condition

Before this session, the Python OPC-UA server used the following development configuration:

| Setting | Initial configuration |
|---|---|
| Security policy | `None` |
| Message security mode | `None` |
| Authentication | Anonymous |
| Application certificate | Not configured |
| Endpoint | `opc.tcp://0.0.0.0:4841/froth-test/` |
| Intended use | Isolated prototype testing only |

The published measurement and status nodes had already been made externally read-only during Session 1. However, the original connection did not provide message signing, transport encryption or authenticated client access.

---

## 3. EAE security capability investigation

The EAE V25.0.1 OPC UA Client Editor documentation and configuration interface were reviewed.

The `OPCUA_CONNECT` block supports the following relevant security options:

- Security policies including:
  - `None`
  - `Basic128Rsa15`
  - `Basic256`
  - `Aes128Sha256RsaOaep`
  - `Aes256Sha256RsaPss`
- Security modes:
  - `None`
  - `Sign`
  - `Sign&Encrypt`
- Authentication modes:
  - `Anonymous`
  - `Username&password`

The general EAE PKI documentation also describes certificate generation and certificate transfer to a Soft dPAC. However, the `OPCUA_CONNECT` interface does not expose the certificate-file inputs shown for other blocks such as `MQTT_CONNECTION`.

It was therefore decided to first test the OPC-UA client using its built-in security configuration rather than manually transferring certificates into the Soft dPAC container.

The selected EAE configuration was:

| Setting | Selected value |
|---|---|
| Security Policy | `Aes256Sha256RsaPss` |
| Security Mode | `Sign&Encrypt` |
| Authentication mode | `Username&password` |
| User Name | Dedicated FrothMV EAE account |
| Password | Matching Python server credential |

---

## 4. Python authentication API investigation

The installed Python environment used:

```text
Python 3.12.7
asyncua 2.0.1
````

Runtime inspection confirmed that `asyncua 2.0.1` provides:

* `Server(user_manager=...)`
* `Server.set_identity_tokens(...)`
* `UserManager`
* `User`
* `UserRole`
* `AnonymousIdentityToken`
* `UserNameIdentityToken`
* `X509IdentityToken`

The `UserManager.get_user()` interface was confirmed as accepting:

```text
iserver
username
password
certificate
```

It returns a `User` object when authentication succeeds and `None` when authentication fails.

The available `asyncua` security policies were also inspected. The selected policy was confirmed to be available as:

```python
ua.SecurityPolicyType.Aes256Sha256RsaPss_SignAndEncrypt
```

---

## 5. Username/password authentication implementation

A custom `FrothMVUserManager` was added to the Python OPC-UA communication layer.

The user manager:

* receives the username and password supplied by the OPC-UA client;
* compares them against the configured server credentials;
* returns a `User` with `UserRole.User` when both values match;
* returns `None` when the credentials do not match;
* logs accepted and rejected authentication attempts;
* does not record passwords in the application logs.

The server was configured to accept only:

```python
ua.UserNameIdentityToken
```

Anonymous identity tokens are therefore no longer advertised or accepted.

### Credential storage

The username and password are supplied through:

```text
FROTH_OPCUA_USERNAME
FROTH_OPCUA_PASSWORD
```

The server refuses to start when either environment variable is missing.

This prevents the credentials from being hard-coded into the Python source or committed to Git. Environment variables are considered adequate for the prototype but are not intended to represent production-grade secret storage.

The credentials must be configured in the same PowerShell session used to start the pipeline.

---

## 6. OPC-UA application certificate

A self-signed X.509 application certificate and associated RSA private key were generated for the Python OPC-UA server.

| Certificate property            | Value                                                              |
| ------------------------------- | ------------------------------------------------------------------ |
| Certificate file                | `certificates/frothmv_server_cert.pem`                             |
| Private-key file                | `certificates/frothmv_server_key.pem`                              |
| Application URI                 | `urn:FrothMV:OPCUAServer`                                          |
| Hostname                        | `BryceLaptop`                                                      |
| Server IP address               | `192.168.1.117`                                                    |
| RSA key size                    | 3072 bits                                                          |
| Signature hash                  | SHA-256                                                            |
| Configured validity             | 365 days                                                           |
| Certificate SHA-256 fingerprint | `E40AF13D56B3AE0254F9E48DDA40C4D1814ECBEFD8809995D375684C829A8F18` |

The certificate generator was retained so that a replacement certificate can be generated if the server hostname or IP address changes.

### Application URI correction

The Python server initially retained the default `asyncua` application URI:

```text
urn:freeopcua:python:server
```

This did not match the URI included in the generated certificate and produced a certificate identity warning.

The server application URI was therefore explicitly configured before loading the certificate:

```python
await self.server.set_application_uri(
    "urn:FrothMV:OPCUAServer"
)
```

After this correction, the certificate application-URI warning no longer appeared.

---

## 7. Python server security configuration

Before starting the OPC-UA server, the certificate, private key, security policy and permitted identity tokens are configured as follows:

```python
await self.server.load_certificate(str(certificate_path))
await self.server.load_private_key(str(private_key_path))

self.server.set_security_policy([
    ua.SecurityPolicyType.Aes256Sha256RsaPss_SignAndEncrypt,
])

self.server.set_identity_tokens([
    ua.UserNameIdentityToken,
])
```

The resulting Python configuration is:

| Setting                 | Implemented value               |
| ----------------------- | ------------------------------- |
| Security policy         | `Aes256Sha256RsaPss`            |
| Message security mode   | `SignAndEncrypt`                |
| User authentication     | Username/password               |
| Anonymous access        | Disabled                        |
| Application certificate | FrothMV self-signed certificate |
| Unsecured endpoint      | Not advertised                  |
| Published-node access   | Externally read-only            |

The server remains bound to:

```text
opc.tcp://0.0.0.0:4841/froth-test/
```

EAE connects through:

```text
opc.tcp://192.168.1.117:4841/froth-test/
```

Binding and firewall restrictions remain separate network-hardening considerations.

---

## 8. Private-key protection

The private key was excluded from Git using:

```gitignore
certificates/*_key.pem
```

The exclusion was verified successfully using:

```powershell
git check-ignore -v certificates/frothmv_server_key.pem
```

The public certificate fingerprint was recorded so that later certificate changes can be detected.

The private key is currently stored as an unencrypted local PEM file. More restrictive filesystem permissions or protected key storage would be required for a production deployment.

---

## 9. Logging improvements

The obsolete startup warning describing the server as using `None/None` and anonymous access was removed.

The startup log now records:

```text
OPC-UA security enabled: Security Policy=Aes256Sha256RsaPss,
Message Security Mode=SignAndEncrypt,
username/password required, anonymous access disabled
```

The FrothMV application logger was configured at `INFO`, while third-party `asyncua` output remained at `WARNING`:

```python
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger.setLevel(logging.INFO)
logging.getLogger("asyncua").setLevel(logging.WARNING)
```

The startup output now records:

* model path;
* active inference configuration;
* OPC-UA endpoint;
* active OPC-UA security configuration;
* successful model-integrity verification;
* verified model SHA-256 hash;
* successful pipeline loading.

This provides useful security and configuration evidence without restoring excessive OPC-UA library output.

---

## 10. Security verification

The following tests were completed.

| Test                                   | Expected behaviour                        | Observed behaviour                                             | Result |
| -------------------------------------- | ----------------------------------------- | -------------------------------------------------------------- | ------ |
| Correct credentials with secure policy | Secure connection established             | EAE reported `connected` and `ERROR = 0`; measurements updated | Pass   |
| Incorrect password                     | Authentication rejected                   | EAE entered `faulted`; observed `ERROR = -335`                 | Pass   |
| Anonymous authentication               | Connection rejected                       | EAE entered `faulted`; observed `ERROR = -138`                 | Pass   |
| Correct credentials restored           | Connection recovers                       | Secure acquisition resumed normally                            | Pass   |
| EAE changed to `None/None`             | No compatible endpoint available          | EAE entered `faulted`; observed `ERROR = -139`                 | Pass   |
| Normal secured MV operation            | Measurements continue normally            | Python processing and EAE acquisition remained operational     | Pass   |
| Private key Git exclusion              | Key is not tracked                        | `git check-ignore` confirmed exclusion                         | Pass   |
| Certificate identity check             | Server and certificate URI match          | No application-URI warning after correction                    | Pass   |
| Secure server restart                  | Invalidity followed by automatic recovery | Secure connection recovered in approximately 5–10 seconds      | Pass   |

The numerical EAE errors are recorded as observed results associated with the test conditions. They are not presented as formal Schneider error definitions unless separately verified against the EAE documentation.

---

## 11. Secure restart and recovery test

The Python pipeline was stopped while EAE remained operational.

During the outage:

* the existing OPC-UA session was lost;
* EAE connection status became unavailable;
* downstream measurement validity was removed as expected.

After the Python server restarted:

* EAE automatically attempted to reconnect;
* a transient `BadSessionIdInvalid` message was observed because EAE briefly referenced the previous session;
* a new signed, encrypted and authenticated session was established;
* measurement acquisition and validity recovered;
* recovery occurred within approximately 5–10 seconds;
* no manual recovery was required.

The same non-fatal `BadSessionIdInvalid` behaviour had previously been observed during unsecured server restart testing.

The recovery time remained approximately consistent with the earlier system behaviour, indicating that the added security controls did not cause an unacceptable reduction in availability.

---

## 12. Files changed or added

The principal Session 2 changes were:

| File or location                             | Change                                                                                                                                          |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/communication/opcua_server.py`          | Added custom user manager, environment-variable credentials, certificate loading, application URI, secure policy and identity-token restriction |
| `src/run_opcua_pipeline.py`                  | Updated security logging and application logger level                                                                                           |
| `certificates/generate_opcua_certificate.py` | Added repeatable certificate-generation utility                                                                                                 |
| `certificates/frothmv_server_cert.pem`       | Generated public OPC-UA server certificate                                                                                                      |
| `certificates/frothmv_server_key.pem`        | Generated private key; excluded from Git                                                                                                        |
| `.gitignore`                                 | Added private-key exclusion                                                                                                                     |
| EAE OPC UA Client Editor                     | Configured matching policy, mode and username/password authentication                                                                           |

---

## 13. Cybersecurity checklist update

| Checklist control                                            | Status after Session 2 |
| ------------------------------------------------------------ | ---------------------- |
| Document the previous `None/None` configuration              | ✓                      |
| State that `None/None` is only suitable for isolated testing | ✓                      |
| Assess `Sign` and `SignAndEncrypt`                           | ✓                      |
| Select the strongest mutually supported policy               | ✓                      |
| Enable `Aes256Sha256RsaPss/SignAndEncrypt`                   | ✓                      |
| Configure an OPC-UA server application certificate           | ✓                      |
| Match the server and certificate application URI             | ✓                      |
| Record the certificate fingerprint                           | ✓                      |
| Disable anonymous user authentication                        | ✓                      |
| Implement a named OPC-UA user                                | ✓                      |
| Keep credentials outside Git-tracked source                  | ✓                      |
| Reject incorrect credentials                                 | ✓                      |
| Prevent downgrade to Security Policy ` `None`                | ✓                      |
| Retain externally read-only measurement nodes                | ✓                      |
| Test secure server shutdown and recovery                     | ✓                      |
| Exclude the private key from Git                             | ✓                      |
| Implement explicit mutual certificate trust lists            | ◐                      |
| Demonstrate rejection of untrusted certificates              | ☐                      |
| Demonstrate rejection of expired certificates                | ☐                      |
| Establish certificate renewal and revocation procedures      | ☐                      |
| Use production-grade secret storage                          | ☐                      |

---

## 14. Risk treatment update

The Session 2 changes reduce the likelihood of the following previously identified risks:

* interception of OPC-UA measurements;
* modification of measurements while in transit;
* unauthenticated OPC-UA client access;
* disclosure through anonymous access;
* silent downgrade to an unsecured OPC-UA endpoint;
* accidental publication of the OPC-UA server private key through Git.

Residual risks remain because:

* the certificate is self-signed;
* explicit application-certificate trust-list enforcement has not been demonstrated;
* the private key is locally stored as an unencrypted PEM file;
* environment variables are used for prototype credential storage;
* the server still binds to all local interfaces;
* certificate expiry, renewal and revocation have not been tested.

The corresponding risk-register likelihood and residual-risk scores may be reduced to reflect the implemented controls, while retaining the remaining limitations above.

---

## 15. Evidence retained

Recommended Session 2 evidence includes:

1. EAE OPC UA Client Editor showing the selected security configuration.
2. Successful EAE connection with `connected` status and `ERROR = 0`.
3. Incorrect-password rejection.
4. Anonymous-access rejection.
5. `None/None` downgrade rejection.
6. Successful secure recovery after Python server restart.
7. Python startup log showing the active secure configuration.
8. Certificate identity and subject-alternative-name output.
9. Certificate SHA-256 fingerprint.
10. `git check-ignore` confirmation for the private key.

Passwords and private-key contents must not appear in screenshots or project documentation.

---

## 16. Session outcome

Week 8 Session 2 successfully replaced the original development-only OPC-UA connection with signed, encrypted and authenticated communication between the Python MV server and EAE.

The final connection uses:

* `Aes256Sha256RsaPss`;
* `SignAndEncrypt`;
* a Python server application certificate;
* username/password authentication;
* disabled anonymous access;
* no advertised unsecured endpoint.

Correct operation, invalid-password rejection, anonymous-access rejection, downgrade prevention and secure restart recovery were demonstrated.

The FrothMV measurements, heartbeat, status processing and downstream validity behaviour continued to function after security was enabled. Secure restart recovery remained approximately 5–10 seconds, consistent with the earlier implementation.

The remaining certificate trust, private-key storage and certificate-lifecycle controls are documented as future production requirements. The prototype may therefore be described as **aligned with selected IEC 62443 and OPC-UA security principles**, but not as IEC 62443 compliant, certified or assigned a formal security level.
