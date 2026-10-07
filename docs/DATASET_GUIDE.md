# SafetyVision AI — Dataset Structure & Annotation Specification

## 1. Directory Structure

SafetyVision AI adheres strictly to the standardized YOLO dataset hierarchy:

```
dataset/
├── data.yaml
├── images/
│   ├── train/          # 70% Training imagery
│   ├── val/            # 15% Validation imagery for checkpoint tuning
│   └── test/           # 15% Hold-out test set for final acceptance evaluation
└── labels/
    ├── train/          # Corresponding YOLO .txt annotation files
    ├── val/
    └── test/
```

---

## 2. YOLO Annotation File Format

Each image (e.g. `sample_001.jpg`) must have an identically named label file (`sample_001.txt`) in the corresponding `labels/` directory.

Each row in the text file represents a single observed physical component:
```
<class_id> <center_x> <center_y> <width> <height>
```
All coordinate values are normalized between `0.0` and `1.0` relative to total image width and height:
- `center_x`: $x$-coordinate of bounding box center / image width
- `center_y`: $y$-coordinate of bounding box center / image height
- `width`: bounding box width / image width
- `height`: bounding box height / image height

---

## 3. Class Index Mapping

Classes must never be hard-coded. They are declared in `config/classes.yaml` and reflected in `dataset/data.yaml`:

| Class ID | Class Name | Category | Criticality | Operational Definition |
|---|---|---|---|---|
| **0** | `grinder` | Equipment | Target | Motor chassis and gearbox body of the angle grinder |
| **1** | `guard` | Component | CRITICAL | Semicircular metallic spark and fragment deflector shroud |
| **2** | `handle` | Component | HIGH | Auxiliary side stabilization grip handle |
| **3** | `cable` | Component | HIGH | Heavy-duty AC power cord and rubber anti-kink boot |
| **4** | `switch` | Component | MEDIUM | Operating trigger paddle or lockout dead-man switch |
| **5** | `damaged_guard` | Damage | CRITICAL | Severe deformation, fatigue crack, or broken clamp on guard |
| **6** | `damaged_cable` | Damage | CRITICAL | Frayed outer jacket, split insulation, or exposed wire copper |
| **7** | `person` | Environment | Context | Operator hands, body, or bystander in optical frame |

---

## 4. Quality Assurance & Validation Rules

Before training or evaluation, the dataset must pass `scripts/validate_dataset.py`:
1. **Coordinate Bounds**: $0.0 \le c_x, c_y \le 1.0$ and $0.0 < w, h \le 1.0$.
2. **One-to-One Match**: Every image must have a corresponding label file; no orphan labels or images.
3. **Zero Byte Checks**: Empty annotation files are flagged.
4. **Duplicate Rejection**: MD5 hashing identifies identical images across train and test sets to prevent data leakage.
5. **Class ID Integrity**: Values must belong strictly to the set $\{0, 1, 2, 3, 4, 5, 6, 7\}$.
