"""
Unit and Integration Tests for SafetyVision AI Inspection Engine
"""

from pathlib import Path
import tempfile
import cv2
import numpy as np
import pytest

from app.database import DatabaseManager
from app.detector import Detection
from app.inspection import InspectionEngine
from app.rules import SafetyRuleEngine


class MockDetector:
    """Mock detector returning predetermined detections for deterministic testing."""
    def __init__(self, detections=None):
        self.detections = detections or []
        self.model_name = "Mock-SafetyVision-YOLO26"
        self.model_version = "0.1.0"
        self.is_custom_model = True

    def detect(self, image, conf_threshold=None, imgsz=640):
        return self.detections, 12.5


def test_image_validation_errors():
    engine = InspectionEngine(detector=MockDetector())

    # 1. Non-existent file
    with pytest.raises(FileNotFoundError):
        engine.inspect(Path("non_existent_image_12345.jpg"))

    # 2. Empty array
    with pytest.raises(ValueError):
        engine.inspect(np.array([]))


def test_end_to_end_inspection_mock(tmp_path):
    # Construct complete passing grinder detections
    mock_detections = [
        Detection(0, "grinder", 0.95, [180, 240, 480, 390], [330, 315], 300, 150, 45000),
        Detection(1, "guard", 0.94, [440, 220, 560, 400], [500, 310], 120, 180, 21600),
        Detection(2, "handle", 0.92, [390, 120, 450, 240], [420, 180], 60, 120, 7200),
        Detection(3, "cable", 0.91, [70, 290, 190, 330], [130, 310], 120, 40, 4800),
        Detection(4, "switch", 0.89, [250, 230, 300, 250], [275, 240], 50, 20, 1000),
    ]

    detector = MockDetector(mock_detections)
    db = DatabaseManager(db_path=tmp_path / "test.db")
    engine = InspectionEngine(detector=detector, db_manager=db)

    # Create dummy 640x640 frame
    frame = np.ones((640, 640, 3), dtype=np.uint8) * 100

    result = engine.inspect(
        image_input=frame,
        operator="TestInspector",
        comments="Acceptance Test Run",
        save_db=True,
        generate_pdf=True,
    )

    # Assertions
    assert result["inspection_id"].startswith("INS-")
    assert result["overall_status"] == "PASS"
    assert result["highest_severity"] == "NONE"
    assert result["confidence"] == 0.95

    # Check evidence file existence
    ev_path = Path(result["evidence_path"])
    assert ev_path.exists()
    assert ev_path.stat().st_size > 0

    # Check report file existence
    rep_path = Path(result["report_path"])
    assert rep_path.exists()
    assert rep_path.stat().st_size > 0

    # Check SQLite persistence
    db_rec = db.get_inspection(result["inspection_id"])
    assert db_rec is not None
    assert db_rec["overall_status"] == "PASS"
    assert len(db_rec["checks"]) >= 4
    assert len(db_rec["detections"]) == 5
