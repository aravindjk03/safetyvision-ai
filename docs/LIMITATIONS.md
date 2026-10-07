# SafetyVision AI — System Limitations & Regulatory Safety Boundary

> [!CAUTION]
> **MANDATORY INDUSTRIAL SAFETY NOTICE:**  
> SafetyVision AI provides automated visual condition verification against configured visual safety criteria only. It **does NOT** certify universal, physical, mechanical, or electrical equipment safety and **never replaces** statutory inspections, manufacturer maintenance guidelines, or evaluations conducted by a certified Competent Person.

---

## 1. What the System Observes vs. What It Cannot Observe

SafetyVision AI is an **optical surface inspection system**. Understanding its physical boundary is critical for risk management:

### Observable Physical Conditions (Supported by AI)
- Presence and spatial attachment of protective wheel guard.
- Presence and spatial attachment of auxiliary side handle.
- Presence and strain-relief attachment of power cable.
- Presence of operator throttle / safety paddle switch.
- Gross structural fractures, missing guard sections, or severe physical bends.
- Sliced, split, or severely frayed external cable insulation with visible colored conductors.

### Non-Observable Physical Conditions (Out of Optical Scope)
- **Mechanical Fastener Torque**: Whether the guard clamp or handle bolt is torqued to manufacturer specification or loose.
- **Internal Electrical Insulation**: Insulation resistance, dielectric breakdown, or grounding continuity (requires Megohmmeter testing).
- **Mechanical Fatigue & Subsurface Cracks**: Micro-cracks in abrasive discs or gearbox casting that require ultrasonic or dye-penetrant testing.
- **Spindle Runout & Bearing Play**: Mechanical spindle eccentricity or internal bearing failure.
- **Abrasive Wheel Speed Rating**: Verification of whether the mounted disc RPM rating matches the tool's maximum operating speed (unless clearly readable in high-res macro optical capture).

---

## 2. Environmental & Operational Failure Modes

1. **Severe Occlusion**:
   - If an operator's arm or workbench rag occludes $> 50\%$ of the wheel guard, the system cannot verify attachment. In such cases, the system **must** trigger `REVIEW` rather than assuming presence.
2. **Glare and Polished Steel Reflections**:
   - Specular reflections from chrome or unpainted metal guards can create hot spots that degrade edge detection.
3. **Motion Blur**:
   - Moving conveyors without synchronized strobe lighting or high shutter speeds produce blurred edges, reducing confidence below the acceptance cutoff.
4. **Lens Contamination**:
   - Grinding debris, dust, or oil mist deposited on the camera protective glass will degrade visual contrast over time.

---

## 3. Regulatory Distinction: Competent Person vs. AI

Under **OSHA 29 CFR 1926.32(f)**:
> *"Competent person means one who is capable of identifying existing and predictable hazards in the surroundings or working conditions which are unsanitary, hazardous, or dangerous to employees, and who has authorization to take prompt corrective measures to eliminate them."*

- **AI is NOT a Competent Person**.
- SafetyVision AI functions as an **automated visual screening filter** and compliance documentation assistant.
- Any equipment flagging `FAIL` or `REVIEW` must be routed to a qualified human technician before operational release.
