# FrothMV Supervisory System

Python machine-vision soft-sensor developed for a final-year thesis investigating the integration of froth-flotation analytics into industrial supervisory automation.

YOLOv8-seg instance masks are combined and processed using OpenCV to extract bubble-population, size-distribution and shape measurements. These are published through secure OPC-UA to EcoStruxure Automation Expert (EAE). EAE exchanges supervisory measurements and validity information with a Control Expert PLC simulator over Modbus TCP.

**This research prototype is for supervisory monitoring only. It does not implement closed-loop process control or a safety-rated function.**

## Final system configuration

- Analytics laptop: Python machine-vision pipeline, OPC-UA server and presentation previewer.
- Second laptop: EAE supervisory application/HMI and Control Expert M580 PLC simulator.
- OPC-UA crosses the network between laptops. EAE-to-simulator Modbus TCP remains local to the second laptop through `127.0.0.1:502`.
- EAE and Control Expert project files are supplied separately from this Python repository.

The five transferred morphology measurements are `BubbleCount`, `MedianECD`, `ECD_P10`, `ECD_P90` and `MeanCircularity`. ECD values are in pixels, not physical length units. Additional Python-side outputs support performance and segmentation analysis.

Heartbeat, communications, pipeline-validity and stale-data monitoring distinguish unavailable or invalid measurements from valid results. The prototype does not classify flotation operating states.

## Repository structure

```text
dataset/        Dataset manifests, 40-image test set and small validation datasets
documentation/  Setup guidance, architecture, testing and cybersecurity evidence
models/         Trained model and reference SHA-256 digest
results/        Selected analysis and validation outputs
src/            Pipeline, communication, analysis and preview source code
tests/          Unit tests and validation utilities
requirements.txt
README.md
```

The full source dataset is stored separately and is not included in the repository. Development scripts and historical evidence may describe earlier configurations; the final runtime is described below.

## Python setup

The project was developed using Python 3.12.7 on Windows 11. Use `requirements.txt` to reproduce the recorded package versions.

From the repository root, create a dedicated environment outside any synchronised project folder:

```powershell
python -m venv C:\PythonEnvironments\FrothMV-venv
C:\PythonEnvironments\FrothMV-venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

An existing dedicated working environment can be used instead. In VS Code, select the same environment's interpreter. Confirm the active interpreter with:

```powershell
python -c "import sys; print(sys.executable); print(sys.version)"
```

PyTorch installation can depend on the hardware and CPU/CUDA build. Record any required installation source or hardware-specific adjustments; a frozen package list alone does not capture these details.

## Dataset and model

- Place the trained model at `models/best.pt` and retain its corresponding `models/best.pt.sha256` file. The integrated runner verifies the digest before allowing image processing.
- The reduced subsets comprised 200 training, 40 validation and 40 test images. Manifests identify the selected data.
- Scripts using the external dataset expect `FROTH_DATASET_ROOT` to identify its local root. Set it for the current PowerShell session, replacing the example path:

```powershell
$env:FROTH_DATASET_ROOT = "D:\Datasets\FrothDataset"
```

The integrated runner accepts an explicit image-folder path; the dataset variable does not automatically select that folder. Obtain externally stored data from the source cited in the thesis and retain its directory structure for manifest-based analysis.

Approved integrated-pipeline inputs are regular, non-empty, decodable `.png` images of `800 x 600` pixels and no more than 2 MiB. Unsupported, oversized, corrupt or incorrectly sized inputs are rejected and reflected in pipeline validity.

The final inference configuration uses confidence `0.15`, image size `640`, maximum detections `1000` and minimum contour area `10 px²`.

## Secure OPC-UA configuration

Complete the deployment/security setup in `documentation/` before starting the integrated runner:

1. Configure the endpoint using an IP address assigned to the analytics laptop. The demonstrated endpoint was `opc.tcp://192.168.1.117:4841/froth-test/`.
2. Generate and configure a server certificate and private key for the target host. The application URI is `urn:FrothMV:OPCUAServer`; certificate hostname/IP entries must match the intended deployment.
3. Set `FROTH_OPCUA_USERNAME` and `FROTH_OPCUA_PASSWORD` in the terminal used to start the pipeline, and configure matching credentials in EAE (see below). Keep real credentials and private keys out of Git.
4. Configure EAE for `Aes256Sha256RsaPss`, `SignAndEncrypt` and username/password authentication, with the required certificate acceptance/trust configuration. Anonymous authentication and unsecured endpoints are disabled.
5. Configure a restricted inbound firewall rule on the analytics laptop for TCP `4841`, its local IP, the approved EAE laptop IP, the actual Python executable and the applicable network profile. Do not enable broad Python inbound access.
6. Start the Control Expert simulator and EAE runtime using their separately supplied projects and deployment instructions.

Addresses, executable paths and certificate fingerprints are deployment-specific. DHCP address changes may require firewall updates. If the server identity/address changes, also review the endpoint and certificate. A new certificate requires the relevant EAE acceptance/trust configuration to be reviewed.

### Set credentials for each terminal session

After activating the Python environment, set these variables in the same PowerShell terminal before starting the integrated pipeline:

```powershell
$env:FROTH_OPCUA_USERNAME = "frothmv_eae"
$env:FROTH_OPCUA_PASSWORD = "example_password"
```

These settings apply only to that terminal session and must be repeated in each new terminal used to start the server. The password shown is an example; use the value configured in EAE. Once the deployment is configured, these are the only additional session settings needed for OPC-UA authentication. Standalone image processing and the separate preview viewer do not require them.

### Update the firewall if the EAE laptop IP changes

On the EAE laptop, run `ipconfig` to identify its current IPv4 address. On the Python server laptop, open PowerShell **as Administrator** and update the existing rule, replacing the example remote address:

```powershell
Get-NetFirewallRule -DisplayName "FrothMV OPC UA Secure - EAE Laptop" |
    Get-NetFirewallAddressFilter |
    Set-NetFirewallAddressFilter -RemoteAddress "192.168.1.116"
```

Verify the configured addresses:

```powershell
Get-NetFirewallRule -DisplayName "FrothMV OPC UA Secure - EAE Laptop" |
    Get-NetFirewallAddressFilter |
    Format-List LocalAddress, RemoteAddress
```

With the Python server running, test from the EAE laptop, using the Python server's address:

```powershell
Test-NetConnection 192.168.1.117 -Port 4841
```

The expected result is `TcpTestSucceeded : True`. If only the EAE laptop's IP changes, the server endpoint and certificate do not need changing. The existing rule must also permit the Python executable actually used to run the server; review its program restriction if the Python environment changes.

### Generate the server certificate and key

On the Python server laptop, activate the Python environment and open a terminal in the folder containing `generate_opcua_certificate.py`. Run:

```powershell
python generate_opcua_certificate.py 192.168.1.117
```

Replace the example address with the Python server laptop's IP address, not the EAE client's address. The script automatically uses the current machine's hostname and creates `frothmv_server_cert.pem` and `frothmv_server_key.pem` alongside itself. It uses application URI `urn:FrothMV:OPCUAServer`, a 3072-bit RSA key, a SHA-256 signature and a certificate validity period of one year.

Ensure the OPC-UA server configuration points to these files. Each execution generates a new certificate/key pair and fingerprint and **overwrites existing files with those names**. Preserve the working pair before regenerating it, and review EAE's certificate acceptance/trust configuration after replacement. Keep the unencrypted private-key file private; another deployment should generate its own pair.

## Run the integrated pipeline

Run from the repository root using the configured Python environment:

```powershell
python src/run_opcua_pipeline.py "dataset\pipeline_validation_images"
```

Replace the folder with the intended input folder. To set the delay between published image results:

```powershell
python src/run_opcua_pipeline.py "path\to\image_folder" --interval 2
```

The interval is an additional delay, not a guaranteed sampling period; processing also takes time. Stop with `Ctrl+C`. Check terminal messages and logs for startup, model-integrity, configuration or input failures.

For standalone image processing without EAE/Control Expert integration:

```powershell
python src/run_single_image.py "path\to\image.png"
python src/run_folder_pipeline.py "path\to\image_folder"
```

## Presentation-only segmentation preview

While the integrated runner processes images, open another terminal using the same environment and repository root:

```powershell
python src/live_preview.py
```

The pipeline saves the latest annotated segmentation image and the viewer displays it in a resizable OpenCV window. Both scripts must use the same preview path. The final deployment uses a non-OneDrive temporary location to reduce synchronisation-related file locking.

The overlay contains the title, image name and presentation-only notice; measurements remain in the main terminal/HMI. Press `Q` or `Escape` in the preview window to close it.

The viewer is separate from the supervisory communication path. Rejected inputs leave the last valid preview visible, so the image does not indicate current system validity. Refer to terminal/HMI statuses instead. Preview-update failures are logged separately from measurement validity.

## Testing and logging

Run pytest-based unit tests from the repository root:

```powershell
python -m pytest
```

Other validation utilities may require specific images, external data or running automation components; inspect their setup before use. Training and network-dependent tests are not required merely to launch the prototype.

Evaluation covered metric extraction, end-to-end transfer, invalid inputs, component interruption/recovery, stale data, authentication failures, security-downgrade rejection, model integrity and network exposure. Selected evidence is retained in `results/` and `documentation/` and discussed in the thesis.

Runtime logs are written to `logs/froth_mv_pipeline.log`, append across restarts and rotate at approximately 1 MB with up to three backups.

## Dependency snapshot maintenance

Only regenerate requirements from the dedicated environment that successfully runs the final system. Confirm the interpreter and run the relevant tests before exporting:

```powershell
python -m pip check
python -m pip freeze > requirements.txt
```

This records installed versions, including transitive dependencies; it does not inspect source imports or prove functionality. For stronger verification, install the exported file in a separate clean environment and repeat relevant tests.

## Limitations

Historical addresses and paths document the tested deployment and must be adapted on another machine. Integrated tests require separately licensed EAE/Control Expert software. No physical PLC, live camera or closed-loop controller is included.

Cybersecurity measures apply selected IEC 62443-aligned principles; they do not establish compliance, certification or a formal security level. Limitations include locally managed credentials/certificates, local logs without tamper protection, deferred dependency vulnerability auditing and unencrypted Modbus protected by loopback-only exposure.
