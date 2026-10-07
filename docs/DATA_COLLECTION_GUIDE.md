# Industrial Visual Safety Data Collection Guide

## 1. Objective

This guide defines the standardized methodology for capturing, labeling, and validating visual datasets for **SafetyVision AI**.

An industrial inspection model trained only on clean laboratory or catalog photographs **will fail** in a real factory or construction site. Operational computer vision models require rich exposure to environmental noise, dust, glare, operator occlusions, and real-world degradation.

---

## 2. Environmental & Operational Variations Required

To build high-reliability detection models, the training dataset must explicitly sample the following operational conditions:

| Parameter | Laboratory Photography (Avoid Sole Reliance) | Industrial Operational Reality (Must Capture) |
|---|---|---|
| **Lighting** | Diffuse 5000K studio lights | Harsh fluorescent, high-bay sodium vapor, direct sunlight, cast shadows, deep underexposure |
| **Surface Reflection** | Matte, anti-reflective coating | Polished metal guards, chrome flanges, oily sheen, specular hot spots |
| **Background** | Clean white/blue photo backdrop | Cluttered steel workbenches, wooden pallets, swarf bins, metal grating, moving conveyors |
| **Atmospheric Noise** | Clean air | Airborne grinding dust, oil mist, particulate haze on camera lens |
| **Tool Condition** | Brand new out of the box | Scratched paint, grease marks, worn rubber grips, weathered plastic motor chassis |
| **Distance & Framing** | Centered 50cm frame | 30cm macro to 180cm wide, variable focal lengths, off-center positioning |
| **Angles** | Orthogonal 90° overhead | 15°, 30°, 45°, and 60° oblique views, upside-down storage orientations |

---

## 3. Tool Variations to Include

Capture imagery across diverse manufacturers and configurations:
1. **Tool Diameters**: 115mm (4.5"), 125mm (5"), 180mm (7"), and 230mm (9") angle grinders.
2. **Manufacturers**: Bosch (blue), DeWalt (yellow/black), Makita (teal), Milwaukee (red), Metabo (dark green).
3. **Guard Mounts**: Tool-free lever clamp vs. hex-key collar vs. slide-and-lock safety indexers.
4. **Side Handles**: Fixed plastic handles, anti-vibration rubber dampened handles, two-position vs. three-position housings.
5. **Power Types**: Corded heavy rubber cables with molded anti-kink boots vs. cordless battery-pack configurations.

---

## 4. Sampling Matrix: Positive, Negative & Ambiguous Cases

The dataset must be balanced across four core clinical inspection categories:

```
DATASET SAMPLE ALLOCATION:
├── 40% Compliant Positive Controls (PASS)
├── 35% Clear Non-Compliant Violations (FAIL)
│   ├── 15% Missing Guard
│   ├── 10% Missing Handle or Cable
│   └── 10% Physical Structural Damage
└── 25% Ambiguous Edge Cases (REVIEW Benchmark)
```

### A. Positive Examples (Target: PASS)
- Fully assembled grinder with wheel guard correctly positioned over spindle, auxiliary side handle securely threaded, power cord intact with strain relief, and trigger switch visible.
- Ensure variations where tool is held by gloved operator vs. resting on rubber mat.

### B. Negative Examples (Target: FAIL)
- **Missing Guard**: Grinder body with exposed spindle or grinding disc without any protective shroud.
- **Missing Side Handle**: Grinder body with empty threaded mounting hole.
- **Missing Cable**: Severed or absent power connection.
- **Damaged Guard**: Guard with visible crack, dent preventing disc clearance, or broken locking lever.
- **Damaged Cable**: Cable with sliced outer jacket, exposed colored wire insulation (blue/brown/green-yellow), or exposed copper conductors.

### C. Ambiguous / Edge Cases (Target: REVIEW)
- **Severe Occlusion**: Grinder buried under cloth rags, cables, or tool bags where more than 50% of the guard is blocked from view.
- **Motion Blur**: Shutter speed too low for moving conveyor; disc or handle smeared across pixels.
- **Extreme Contrast / Backlight**: Strong silhouette behind the tool rendering the guard region pitch black.
- **Multiple Equipment Items**: Two or more grinders side-by-side in the same frame.

---

## 5. Camera Rigging & Acquisition Protocol

When capturing images on-site:
1. **Resolution**: Minimum $1280 \times 720$ (720p); recommended $1920 \times 1080$ (1080p).
2. **Sensor & Optics**: Industrial global shutter CMOS sensor (to eliminate conveyor rolling shutter skew).
3. **Focal Length**: 8mm to 16mm industrial C-mount lens.
4. **Format**: Uncompressed PNG or high-quality JPEG ($Q \ge 95$). Never use lossy compression that degrades small wire-fray details.
5. **Safety Warning During Capture**: Always ensure tools are de-energized (unplugged or battery removed) before positioning tools for photography.

---

## 6. Annotation Rules in YOLO Format

- Annotate tight bounding boxes around physical components:
  - `0: grinder` — Body and motor gearbox.
  - `1: guard` — Entire semicircular protective cover.
  - `2: handle` — Auxiliary side grip.
  - `3: cable` — Power cord up to 30cm from tool entry.
  - `4: switch` — Trigger button or slide paddle.
  - `5: damaged_guard` — Specific fractured or warped guard.
  - `6: damaged_cable` — Specific damaged cable segment.
  - `7: person` — Operator body or hands.
- Do not guess or annotate invisible components hidden beneath solid occlusions.
