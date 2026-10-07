# SafetyVision AI — System Architecture & Design Specification

## 1. Architectural Philosophy

SafetyVision AI implements a **physically observable, deterministic safety architecture**.

### The Black-Box Failure Mode
Standard deep learning vision models often attempt end-to-end classification:
$$\text{Image} \xrightarrow{\text{CNN / Transformer}} \{\text{SAFE}, \text{UNSAFE}\}$$
In industrial operations, this design is unviable:
1. **Zero Explainability**: When the model marks a machine "UNSAFE", operators cannot determine which physical component is non-compliant.
2. **Silent Hallucinations**: Subtie occlusions or ambient lighting shifts can lead to catastrophic false passes.
3. **Regulatory Non-Compliance**: OSHA, ANSI, and ISO standards require specific component verifications (guards, interlocks, emergency stops). An opaque score cannot satisfy formal audit requirements.

### SafetyVision AI Decoupled Pipeline
SafetyVision AI strictly separates statistical computer vision from deterministic industrial rules:

```
+-------------------------------------------------------------------------+
|                              CAMERA / FRAME                             |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  PHYSICAL DETECTION (app/detector.py)                   |
|  Detects: grinder, guard, handle, cable, switch, damaged_*, person      |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|            SPATIAL RELATIONSHIP ENGINE (app/spatial.py)                 |
|  IoU, Containment, Center Distance, Relative Coordinate Topology        |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              SAFETY RULE ENGINE (app/rules.py & YAML)                   |
|  Evaluates Mandatory & Critical Rules, Damage Classes, Severities       |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  CONFIDENCE & AMBIGUITY EVALUATION                      |
|  High (>=0.85), Medium (0.60..0.85), Low (<0.60), Occlusion Filters     |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         THREE-STATE DECISION                            |
|                 PASS    |    FAIL    |    REVIEW                        |
+-------------------------------------------------------------------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+--------------------------------+             +--------------------------------+
|  AUDIT DATABASE & EVIDENCE     |             |  REPORTS & OPERATOR DASHBOARD  |
|  SQLite WAL & OpenCV Watermark |             |  ReportLab PDF, Streamlit UI   |
+--------------------------------+             +--------------------------------+
```

---

## 2. Core Subsystems & Components

### 2.1 Detection Engine (`app/detector.py`)
- Standardizes object detection across YOLO architectures (`n`, `s`, `m`, `l`, `x`).
- Emits standardized dataclass `Detection`:
  - `class_id`: integer
  - `class_name`: human-readable class
  - `confidence`: float $[0.0, 1.0]$
  - `bbox`: $[x_1, y_1, x_2, y_2]$ in absolute pixel coordinates
  - `center`: $[c_x, c_y]$
  - `width`, `height`, `area`
- Contains **no safety decision logic**.

### 2.2 Spatial Association Engine (`app/spatial.py`)
In complex industrial scenes, components frequently lay disconnected on workbenches. The spatial engine prevents false positives by ensuring a component physically belongs to the equipment chassis:
1. **Intersection over Union (IoU)**:
   $$\text{IoU}(A, B) = \frac{\text{Area}(A \cap B)}{\text{Area}(A \cup B)}$$
2. **Containment Proportion**:
   $$\text{Containment}(C, E) = \frac{\text{Area}(C \cap E)}{\text{Area}(C)}$$
3. **Normalized Center Distance**:
   $$\Delta_{\text{norm}} = \frac{\sqrt{(c_{x,E} - c_{x,C})^2 + (c_{y,E} - c_{y,C})^2}}{\text{Diagonal}(E)}$$
   Where $\text{Diagonal}(E) = \sqrt{W_E^2 + H_E^2}$.
4. **Expanded Bounding Box**:
   Tests whether component center lies within an expanded search hull around the equipment ($1.4 \times$ dimensions).

### 2.3 Deterministic Rule Engine (`app/rules.py`)
- Evaluates configured requirements in `config/safety_rules.yaml`.
- Enforces the Three-State Decision Model:
  - **PASS**: All mandatory visual requirements detected with high confidence ($\ge 0.85$) and valid spatial attachment. Zero damage detected.
  - **FAIL**: Any mandatory visual requirement is absent ($< 0.60$), not spatially attached, or structural damage detected.
  - **REVIEW**: Marginal confidence ($0.60 \le \text{conf} < 0.85$), target equipment ambiguous, multiple candidate objects, or severe scene occlusion.

### 2.4 Evidence Generation (`app/evidence.py`)
- Generates watermarked audit records directly on the image using OpenCV.
- Top status banner with color-coded classification:
  - Green (`#2E7D32`): PASS
  - Red (`#C62828`): FAIL
  - Amber (`#EF6C00`): REVIEW
- Bottom metadata footer embedding inspection ID, timestamp, and equipment type.

### 2.5 Audit Storage & Persistence (`app/database.py`)
- SQLite database with Write-Ahead Logging (`WAL`).
- Normalized relational schema tracking inspections, component check rows, raw bounding box detections, and model registry lineage.

### 2.6 ReportLab PDF Generator (`app/report.py`)
- Formats executive audit certificates suitable for plant EHS reviews.
- Embeds visual evidence, itemized component matrix, root cause finding, corrective action, and statutory legal disclaimer.

---

## 3. Data Contract: Inspection Result Schema

Every inspection produces a standardized JSON-serializable structure:
```json
{
  "inspection_id": "INS-20261005-A1B2C3",
  "timestamp": "2026-10-05 08:30:00",
  "equipment_type": "grinder",
  "equipment_display_name": "Industrial Angle Grinder",
  "overall_status": "FAIL",
  "confidence": 0.952,
  "highest_severity": "CRITICAL",
  "model_version": "0.1.0",
  "checks": {
    "guard": {
      "status": "FAIL",
      "severity": "CRITICAL",
      "confidence": 0.0,
      "message": "Abrasive wheel guard is missing."
    },
    "handle": {
      "status": "PASS",
      "severity": "NONE",
      "confidence": 0.941,
      "message": "Auxiliary Side Handle verified in position."
    }
  },
  "missing_components": ["guard"],
  "reason": "FAIL — Missing mandatory components: guard.",
  "recommended_action": "Lockout tool immediately and schedule competent-person inspection.",
  "timing": {
    "preprocess_ms": 3.4,
    "inference_ms": 18.2,
    "rules_evaluation_ms": 1.1,
    "total_time_ms": 32.5,
    "fps": 30.8
  }
}
```
