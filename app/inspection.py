"""
SafetyVision AI — Inspection Engine (Orchestrator)
Coordinates image loading, YOLO detection, spatial reasoning, safety rule evaluation,
evidence generation, database persistence, and report creation.
"""

from datetime import datetime
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import cv2
import numpy as np
from PIL import Image

from app.config import get_config
from app.database import DatabaseManager
from app.detector import Detection, DetectionEngine
from app.evidence import EvidenceGenerator
from app.logger import get_logger
from app.report import ReportGenerator
from app.rules import RuleEvaluationResult, SafetyRuleEngine


class InspectionEngine:
    """End-to-end industrial visual inspection orchestrator."""

    def __init__(
        self,
        detector: Optional[DetectionEngine] = None,
        rule_engine: Optional[SafetyRuleEngine] = None,
        db_manager: Optional[DatabaseManager] = None,
        evidence_generator: Optional[EvidenceGenerator] = None,
        report_generator: Optional[ReportGenerator] = None,
    ):
        self.logger = get_logger()
        self.config = get_config()
        self.detector = detector or DetectionEngine()
        self.rule_engine = rule_engine or SafetyRuleEngine()
        self.db = db_manager or DatabaseManager()
        self.evidence_gen = evidence_generator or EvidenceGenerator()
        self.report_gen = report_generator or ReportGenerator()

    def generate_inspection_id(self, timestamp: Optional[datetime] = None) -> str:
        """Generates a standard unique inspection identifier: INS-YYYYMMDD-XXXXXX."""
        ts = timestamp or datetime.now()
        short_uuid = uuid.uuid4().hex[:6].upper()
        return f"INS-{ts.strftime('%Y%m%d')}-{short_uuid}"

    def inspect(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        operator: str = "System Operator",
        comments: str = "",
        save_db: bool = True,
        generate_pdf: bool = True,
        conf_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes a complete inspection workflow.

        Measures:
        - Preprocessing time
        - Model inference time
        - Rule evaluation time
        - Evidence generation time
        - Total inspection time

        Returns comprehensive inspection record dictionary.
        """
        total_start = time.perf_counter()
        now = datetime.now()
        inspection_id = self.generate_inspection_id(now)

        self.logger.info(f"Initiating inspection {inspection_id} for operator '{operator}'...")

        # 1. Image Preprocessing & Validation
        pre_start = time.perf_counter()
        validated_img_bgr = self._validate_and_prepare_image(image_input)
        preprocess_ms = (time.perf_counter() - pre_start) * 1000.0

        # 2. YOLO Object Detection
        detections, inference_ms = self.detector.detect(
            image=validated_img_bgr,
            conf_threshold=conf_threshold,
        )

        # 3. Deterministic Safety Rule Evaluation
        rules_start = time.perf_counter()
        eval_result = self.rule_engine.evaluate(detections)
        rules_ms = (time.perf_counter() - rules_start) * 1000.0

        # 4. Generate Annotated Visual Evidence Image
        evidence_start = time.perf_counter()
        _, evidence_path = self.evidence_gen.create_evidence_image(
            image_input=validated_img_bgr,
            detections=detections,
            rule_result=eval_result,
            inspection_id=inspection_id,
            timestamp=now,
        )
        evidence_ms = (time.perf_counter() - evidence_start) * 1000.0

        # 5. Generate PDF Report (if requested)
        report_path = None
        if generate_pdf:
            report_path = self.report_gen.generate_pdf(
                inspection_id=inspection_id,
                rule_result=eval_result,
                evidence_image_path=evidence_path,
                operator=operator,
                model_version=self.detector.model_version,
                timestamp=now,
            )

        total_ms = (time.perf_counter() - total_start) * 1000.0

        # 6. Build Inspection Summary Payload
        inspection_record = {
            "inspection_id": inspection_id,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "equipment_type": eval_result.equipment,
            "equipment_display_name": eval_result.equipment_display_name,
            "overall_status": eval_result.overall_status,
            "confidence": round(eval_result.equipment_confidence, 4),
            "highest_severity": eval_result.highest_severity,
            "model_version": self.detector.model_version,
            "model_name": self.detector.model_name,
            "is_custom_model": self.detector.is_custom_model,
            "image_path": str(image_input) if isinstance(image_input, (str, Path)) else "in_memory",
            "evidence_path": str(evidence_path),
            "report_path": str(report_path) if report_path else "",
            "operator": operator,
            "comments": comments,
            "reason": eval_result.reason,
            "recommended_action": eval_result.recommended_action,
            "findings": eval_result.findings,
            "warnings": eval_result.warnings,
            "missing_components": eval_result.missing_components,
            "detected_components": eval_result.detected_components,
            "damage_violations": eval_result.damage_violations,
            "checks": eval_result.checks,
            "detections": [d.to_dict() for d in detections],
            "disclaimer": eval_result.disclaimer,
            "timing": {
                "preprocess_ms": round(preprocess_ms, 2),
                "inference_ms": round(inference_ms, 2),
                "rules_evaluation_ms": round(rules_ms, 2),
                "evidence_ms": round(evidence_ms, 2),
                "total_time_ms": round(total_ms, 2),
                "fps": round(1000.0 / total_ms, 1) if total_ms > 0 else 0.0,
            },
        }

        # 7. Persist to SQLite Database
        if save_db:
            db_payload = {
                "inspection_id": inspection_id,
                "timestamp": inspection_record["timestamp"],
                "equipment_type": inspection_record["equipment_type"],
                "overall_status": inspection_record["overall_status"],
                "confidence": inspection_record["confidence"],
                "highest_severity": inspection_record["highest_severity"],
                "model_version": inspection_record["model_version"],
                "image_path": inspection_record["image_path"],
                "evidence_path": inspection_record["evidence_path"],
                "report_path": inspection_record["report_path"],
                "operator": operator,
                "comments": comments,
                "reason": inspection_record["reason"],
                "recommended_action": inspection_record["recommended_action"],
                "inference_time_ms": inspection_record["timing"]["inference_ms"],
                "total_time_ms": inspection_record["timing"]["total_time_ms"],
            }
            try:
                self.db.save_inspection(
                    inspection_data=db_payload,
                    checks=eval_result.checks,
                    detections=detections,
                )
            except Exception as e:
                self.logger.error(f"Failed to save inspection {inspection_id} to database: {e}")

        self.logger.info(
            f"Inspection {inspection_id} complete -> Status: {eval_result.overall_status} "
            f"in {total_ms:.1f}ms."
        )
        return inspection_record

    def _validate_and_prepare_image(self, inp: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """Validates that input is a non-empty, corrupt-free image and returns BGR array."""
        if isinstance(inp, (str, Path)):
            path = Path(inp)
            if not path.exists():
                raise FileNotFoundError(f"Input image path does not exist: {path}")
            if path.stat().st_size == 0:
                raise ValueError(f"Input image file is empty (0 bytes): {path}")

            # Check supported extensions
            valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
            if path.suffix.lower() not in valid_exts:
                raise ValueError(f"Unsupported image format: '{path.suffix}'. Supported: {valid_exts}")

            data = np.fromfile(str(path), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Corrupt or unreadable image file: {path}")
            return img

        if isinstance(inp, Image.Image):
            rgb = np.array(inp.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if isinstance(inp, np.ndarray):
            if inp.size == 0:
                raise ValueError("Input image array is empty.")
            if len(inp.shape) == 2:
                return cv2.cvtColor(inp, cv2.COLOR_GRAY2BGR)
            if inp.shape[2] == 4:
                return cv2.cvtColor(inp, cv2.COLOR_BGRA2BGR)
            return inp

        raise TypeError(f"Unsupported input type for image inspection: {type(inp)}")
