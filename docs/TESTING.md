# SafetyVision AI — Testing Suite & Acceptance Criteria Matrix

## 1. Automated Testing Framework

SafetyVision AI uses `pytest` for rigorous unit, integration, and rule validation:

```bash
# Execute Full Test Suite
pytest -v

# Run with Detailed Console Output
pytest -s -v
```

---

## 2. Test Coverage Overview

| Test Module | Coverage Scope | Primary Assertion |
|---|---|---|
| `tests/test_config.py` | Configuration Parsing | Verifies YAML schemas, class index lookups, threshold loading. |
| `tests/test_spatial.py` | Geometric Reasoning | Validates IoU, containment math, center distance, true/false association. |
| `tests/test_rules.py` | Safety Rule Engine | Evaluates PASS, FAIL, REVIEW, damaged components, multiple tools. |
| `tests/test_inspection.py` | Full Pipeline | Validates input checks, evidence rendering, DB storage, report generation. |
| `tests/test_report.py` | Document Generation | Validates ReportLab PDF generation, styling, and statutory safety text. |

---

## 3. Final Acceptance Test Matrix (Section 49)

The prototype must satisfy all five fundamental industrial acceptance tests:

### TEST 1 — PASS (Fully Compliant Tool)
- **Input**: Angle grinder with guard, handle, cable, and switch attached.
- **Expected Status**: `PASS`
- **Severity**: `NONE`
- **Findings**: All mandatory components detected with confidence $\ge 0.85$ and valid spatial binding.

### TEST 2 — FAIL (Missing Safety Guard)
- **Input**: Angle grinder operating with exposed spindle / missing guard.
- **Expected Status**: `FAIL`
- **Severity**: `CRITICAL`
- **Root Reason**: Protective guard not detected.
- **Recommended Action**: Lockout equipment immediately.

### TEST 3 — REVIEW (Degraded Visual Evidence)
- **Input**: Severely underexposed, blurred, or occluded equipment scene.
- **Expected Status**: `REVIEW`
- **Severity**: `MEDIUM`
- **Root Reason**: Insufficient visual evidence or ambiguous component confidence ($< 0.85$).
- **Action**: Mandatory manual competent-person verification.

### TEST 4 — ERROR RESILIENCE (Corrupted File)
- **Input**: 0-byte file, truncated file header, or unsupported format (`.exe`, `.txt`).
- **Expected Status**: Friendly user error returned; no process crashes or unhandled exceptions.

### TEST 5 — AUDIT ARTIFACTS (Full Lifecycle)
- **Verification**: Each inspection successfully creates:
  1. Unique Inspection ID (`INS-YYYYMMDD-XXXXXX`).
  2. Annotated Evidence Image in `evidence/YYYY/MM/DD/`.
  3. Relational record in SQLite `data/safetyvision.db`.
  4. Formatted PDF Audit Certificate in `reports/`.
