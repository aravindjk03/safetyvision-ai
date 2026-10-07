# Ultralytics YOLO Licensing & Commercial Use Considerations

> **LEGAL NOTICE & DISCLAIMER:**  
> This document provides technical and operational context regarding third-party software licensing for architectural and deployment planning. **It does not constitute legal advice.** Commercial deployers, manufacturing organizations, and software vendors should consult qualified legal counsel to review their specific architecture, licensing terms, and distribution models.

---

## 1. Executive Summary

SafetyVision AI utilizes the **Ultralytics YOLO** framework for computer vision object detection. 

While Ultralytics is open source, it is distributed under a **dual-licensing model**:
1. **Open-Source License**: GNU Affero General Public License v3.0 (**AGPL-3.0**).
2. **Ultralytics Enterprise / Commercial License**: Proprietary commercial agreement with Ultralytics Inc.

A common industry misconception is that "open-source" or "freely downloadable" means unrestricted commercial deployment in closed-source proprietary systems. For enterprise industrial deployment, understanding this distinction is mandatory.

---

## 2. Open-Source Licensing (AGPL-3.0)

Under AGPL-3.0:
- You may freely use, modify, and run the software for research, development, proof-of-concept testing, and non-commercial prototyping.
- **Copyleft Trigger**: If you distribute the software, or if you **run it on a server/network** and make its functionality accessible over a network (e.g., via a SaaS API or internal company cloud service), the AGPL copyleft requirements are triggered.
- Under strict AGPL-3.0 interpretation, any software that links to or forms a combined/derivative work with AGPL-3.0 code must also be made available in source code format under AGPL-3.0 to all network users.

### Application to SafetyVision AI Prototype
- The SafetyVision AI prototype repository is suitable for evaluation, local experimentation, academic research, and engineering proof-of-concept under AGPL-3.0.

---

## 3. Commercial Deployment Options

If an organization intends to:
- Package SafetyVision AI into a proprietary commercial appliance (e.g., an industrial edge computer sold to third parties),
- Offer an inspection SaaS API without releasing the proprietary business logic, rules engine, or user interface under AGPL-3.0,
- Embed Ultralytics YOLO models or inference runtimes into proprietary manufacturing execution systems (MES/SCADA),

The following paths exist:

### Path A: Commercial License from Ultralytics
- Purchase an **Ultralytics Commercial License**.
- This waives the AGPL-3.0 copyleft obligations, allowing closed-source distribution and proprietary SaaS deployment.

### Path B: ONNX / TensorRT Export with Independent Inference Engines
- Export the trained YOLO model weights to an open format such as **ONNX** (`.onnx`) or **TensorRT** (`.engine`).
- Run runtime inference using **ONNX Runtime** (MIT License) or **NVIDIA TensorRT** (Apache 2.0 / NVIDIA SLA) without importing or executing the Ultralytics Python package in the production runtime container.
- *Note:* Consult legal counsel regarding whether model weights trained via the Ultralytics training pipeline constitute derivative works under your jurisdiction and license agreement.

### Path C: Alternative Permissive Frameworks
- Re-train the safety component detection network using permissively licensed backbones:
  - Apache 2.0 backbones (e.g., RT-DETR, YOLO-NAS, PyTorch torchvision models).
  - Cleanroom architectures with MIT/Apache licenses.

---

## 4. Architectural Decoupling in SafetyVision AI

To support whatever commercial path an enterprise selects, SafetyVision AI explicitly enforces **strict architectural decoupling**:

```
[Vision Model Runtime]
       ↓ (Standardized Detection Data Contract)
[Spatial Reasoning Engine]
       ↓
[Deterministic Safety Rule Engine]
       ↓
[Database & Reporting]
```

- The core safety logic (`app/rules.py`, `app/spatial.py`, `app/inspection.py`, `app/report.py`) is **100% independent** of Ultralytics and YOLO.
- The detector module (`app/detector.py`) implements an isolated adapter pattern.
- Replacing the detection runtime with an ONNX Runtime engine, TensorRT C++ server, or alternative model requires changing only `app/detector.py` without touching the safety rules, spatial logic, database, or UI.

---

## 5. Deployment Checklist Before Production

1. [ ] Consult corporate intellectual property legal counsel.
2. [ ] Identify your distribution model (Local edge appliance, on-premise server, cloud SaaS).
3. [ ] If keeping application source closed, obtain an Ultralytics Commercial License or transition inference runtime to decoupled ONNX Runtime.
4. [ ] Audit all Python dependencies in `requirements.txt` against corporate Open Source Software (OSS) compliance policies.
