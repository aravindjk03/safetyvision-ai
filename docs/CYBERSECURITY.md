# SafetyVision AI — Industrial Cybersecurity & Information Assurance

## 1. Compliance Framework Alignment

SafetyVision AI is architected with foundational principles from:
- **ISO/IEC 27001**: Information Security Management Systems.
- **IEC 62443**: Industrial Communication Networks — Network and System Security for Operational Technology (OT).

While the initial prototype operates as a local workstation tool, production deployments must adhere to the defense-in-depth security model outlined below.

---

## 2. Security Controls Architecture

### 2.1 Model & Configuration Integrity
- **Model Tampering Prevention**: Production weights must be validated with SHA-256 cryptographic checksums before loading into GPU memory.
- **Rule Engine Tampering Prevention**: Safety configuration files (`config/safety_rules.yaml`) must be digitally signed or stored in read-only volumes to prevent unauthorized lowering of inspection thresholds.

### 2.2 Network Segmentation (Purdue Model Alignment)
- In factory networks, computer vision systems reside in **Level 2 / Level 3 (Supervisory & Operations Control)**.
- Edge inspection IPCs must not have direct exposure to the public Internet.
- REST APIs (`app/api.py`) must be restricted to authenticated internal corporate VLANs via reverse proxies (e.g. NGINX with mTLS).

### 2.3 Secrets & Environment Isolation
- No passwords, PLC credentials, or database keys are committed to version control.
- Configuration is loaded via `.env` files and validated using strict system schemas.

### 2.4 Evidence & Audit Non-Repudiation
- Every inspection generates an immutable SQLite record containing exact bounding box coordinates, class confidence levels, model version, and timestamps.
- Evidence images contain indelible pixel-level visual banners and watermarks.
- Production storage should be mounted on WORM (Write Once, Read Many) compliant volumes for EHS audit compliance.

### 2.5 Input Sanitization & Attack Surface Hardening
- File uploads via UI or API are strictly validated:
  - File extension whitelisting (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`).
  - Magic byte header inspection to block disguised executables.
  - Strict payload size limits ($< 25 \text{ MB}$) to prevent memory exhaustion DoS attacks.
