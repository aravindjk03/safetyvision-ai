"""
Unit Tests for SafetyVision AI Report Generation Module
"""

from pathlib import Path
import pytest

from app.report import ReportGenerator
from app.rules import RuleEvaluationResult


def test_pdf_report_generation():
    gen = ReportGenerator()

    eval_result = RuleEvaluationResult(
        equipment="grinder",
        equipment_display_name="Industrial Angle Grinder",
        equipment_detected=True,
        equipment_confidence=0.965,
        equipment_bbox=[100, 100, 400, 300],
        overall_status="FAIL",
        highest_severity="CRITICAL",
        checks={
            "guard": {
                "display_name": "Protective Wheel Guard",
                "status": "FAIL",
                "severity": "CRITICAL",
                "confidence": 0.0,
                "is_mandatory": True,
                "is_associated": False,
                "message": "Abrasive wheel guard is missing. Operating without guard risks projectile injury.",
            },
            "handle": {
                "display_name": "Auxiliary Side Handle",
                "status": "PASS",
                "severity": "NONE",
                "confidence": 0.94,
                "is_mandatory": True,
                "is_associated": True,
                "message": "Handle verified in position.",
            },
        },
        missing_components=["guard"],
        findings=["CRITICAL FINDING: Protective wheel guard missing."],
        warnings=[],
        reason="FAIL — Missing mandatory components: guard.",
        recommended_action="Lockout tool immediately and schedule competent-person inspection.",
    )

    pdf_path = gen.generate_pdf(
        inspection_id="TEST-INS-001",
        rule_result=eval_result,
        operator="Test Auditor",
        model_version="0.1.0",
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000  # Valid non-empty PDF

    html_path = gen.generate_html(
        inspection_id="TEST-INS-001",
        rule_result=eval_result,
        operator="Test Auditor",
        model_version="0.1.0",
    )

    assert html_path.exists()
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SAFETYVISION AI" in content
    assert "STATUTORY NOTICE" in content
