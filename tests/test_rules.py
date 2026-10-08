"""
Unit Tests for SafetyVision AI Deterministic Safety Rule Engine
"""

import pytest

from app.detector import Detection
from app.rules import SafetyRuleEngine


def make_det(class_name: str, confidence: float, bbox: list, cid: int = 0) -> Detection:
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    return Detection(
        class_id=cid,
        class_name=class_name,
        confidence=confidence,
        bbox=bbox,
        center=[x1 + w / 2.0, y1 + h / 2.0],
        width=w,
        height=h,
        area=w * h,
    )


def test_rule_pass_case():
    engine = SafetyRuleEngine("angle_grinder")

    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("guard", 0.94, [440, 220, 560, 400]),
        make_det("handle", 0.92, [390, 120, 450, 240]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "PASS"
    assert res.highest_severity == "NONE"
    assert len(res.missing_components) == 0
    assert len(res.damage_violations) == 0


def test_rule_fail_missing_guard():
    engine = SafetyRuleEngine("angle_grinder")

    # Missing guard
    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("handle", 0.92, [390, 120, 450, 240]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "FAIL"
    assert res.highest_severity == "CRITICAL"
    assert "guard" in res.missing_components
    assert res.checks["guard"]["status"] == "FAIL"


def test_rule_fail_missing_handle():
    engine = SafetyRuleEngine("angle_grinder")

    # Missing handle
    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("guard", 0.94, [440, 220, 560, 400]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "FAIL"
    assert res.highest_severity == "HIGH"
    assert "handle" in res.missing_components


def test_rule_fail_damaged_guard():
    engine = SafetyRuleEngine("angle_grinder")

    # Guard is damaged
    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("guard", 0.94, [440, 220, 560, 400]),
        make_det("damaged_guard", 0.90, [445, 225, 550, 395]),
        make_det("handle", 0.92, [390, 120, 450, 240]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "FAIL"
    assert res.highest_severity == "CRITICAL"
    assert "damaged_guard" in res.damage_violations


def test_rule_review_low_confidence_guard():
    engine = SafetyRuleEngine("angle_grinder")

    # Guard confidence is 0.70 (within medium ambiguous range [0.60, 0.85))
    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("guard", 0.70, [440, 220, 560, 400]),
        make_det("handle", 0.92, [390, 120, 450, 240]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "REVIEW"
    assert res.checks["guard"]["status"] == "REVIEW"


def test_rule_review_no_equipment():
    engine = SafetyRuleEngine("angle_grinder")

    # No grinder in scene (only person or background items)
    detections = [
        make_det("person", 0.90, [50, 50, 200, 400]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "REVIEW"
    assert res.equipment_detected is False


def test_rule_review_multiple_equipment():
    engine = SafetyRuleEngine("angle_grinder")

    # 2 grinders in scene
    detections = [
        make_det("grinder", 0.94, [100, 100, 300, 300]),
        make_det("grinder", 0.88, [350, 100, 550, 300]),
    ]

    res = engine.evaluate(detections)
    assert res.overall_status == "REVIEW"
    assert "Multiple" in res.reason


def test_rule_spatial_rejection():
    engine = SafetyRuleEngine("angle_grinder")

    # Guard is present with 0.99 confidence, but placed far away on workbench
    detections = [
        make_det("grinder", 0.95, [300, 300, 550, 450]),
        make_det("guard", 0.99, [20, 20, 80, 80]),  # Unassociated
        make_det("handle", 0.92, [420, 240, 460, 310]),
        make_det("cable", 0.91, [230, 340, 310, 370]),
        make_det("switch", 0.89, [350, 290, 390, 310]),
    ]

    res = engine.evaluate(detections)
    # The guard is not associated with the grinder, so it counts as missing!
    assert res.overall_status == "FAIL"
    assert "guard" in res.missing_components


def test_auto_selects_grinder_rules():
    engine = SafetyRuleEngine()

    detections = [
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("guard", 0.94, [440, 220, 560, 400]),
        make_det("handle", 0.92, [390, 120, 450, 240]),
        make_det("cable", 0.91, [70, 290, 190, 330]),
        make_det("switch", 0.89, [250, 230, 300, 250]),
    ]

    res = engine.evaluate(detections)
    assert res.equipment == "grinder"
    assert res.overall_status == "PASS"


def test_auto_selects_drill_rules():
    engine = SafetyRuleEngine()

    res = engine.evaluate([
        make_det("drill", 0.93, [200, 200, 460, 400], cid=8),
        make_det("cable", 0.90, [430, 330, 560, 420], cid=3),
    ])
    assert res.equipment == "drill"
    assert res.equipment_display_name == "Electric Power Drill"
    assert res.overall_status == "PASS"


def test_auto_drill_missing_cable_fails():
    engine = SafetyRuleEngine()

    res = engine.evaluate([make_det("drill", 0.93, [200, 200, 460, 400], cid=8)])
    assert res.equipment == "drill"
    assert res.overall_status == "FAIL"
    assert res.missing_components == ["cable"]


def test_auto_grinder_and_drill_requires_review():
    engine = SafetyRuleEngine()

    res = engine.evaluate([
        make_det("grinder", 0.95, [180, 240, 480, 390]),
        make_det("drill", 0.90, [600, 200, 800, 400], cid=8),
    ])
    assert res.overall_status == "REVIEW"
    assert "Multiple" in res.reason


def test_auto_no_equipment_review():
    engine = SafetyRuleEngine()

    res = engine.evaluate([make_det("cable", 0.9, [70, 290, 190, 330], cid=3)])
    assert res.overall_status == "REVIEW"
    assert res.equipment_detected is False
