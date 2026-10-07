"""
SafetyVision AI — Evidence Image Generator
Generates tamper-evident, annotated inspection evidence images using OpenCV.
Renders bounding boxes, class labels, status badges, and metadata watermarks.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from app.config import get_config
from app.detector import Detection
from app.logger import get_logger
from app.rules import RuleEvaluationResult


class EvidenceGenerator:
    """Renders visual annotations and stores inspection evidence files."""

    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.evidence_dir = self.config.evidence_dir

    def create_evidence_image(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        detections: List[Detection],
        rule_result: RuleEvaluationResult,
        inspection_id: str,
        timestamp: Optional[datetime] = None,
    ) -> Tuple[np.ndarray, Path]:
        """
        Draws visual annotations, overlays status banner and watermark,
        and saves to disk under evidence/YYYY/MM/DD/INS-*.jpg.

        Returns:
            Tuple of (annotated_image_bgr, saved_filepath)
        """
        ts = timestamp or datetime.now()
        
        # 1. Normalize image to OpenCV BGR format
        img_bgr = self._load_as_bgr(image_input)
        h, w = img_bgr.shape[:2]
        canvas = img_bgr.copy()

        # 2. Draw bounding boxes and labels for each detection
        for d in detections:
            color = self.config.get_class_color_bgr(d.class_name)
            x1, y1, x2, y2 = [int(v) for v in d.bbox]

            # Bounding box
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)

            # Label badge
            label_text = f"{d.class_name} {d.confidence * 100:.1f}%"
            (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            
            # Ensure label badge is inside image boundaries
            bg_y1 = max(0, y1 - th - baseline - 4)
            bg_y2 = y1
            cv2.rectangle(canvas, (x1, bg_y1), (x1 + tw + 6, bg_y2), color, -1)
            cv2.putText(
                canvas,
                label_text,
                (x1 + 3, bg_y2 - baseline),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 3. Draw Top Status Banner
        status = rule_result.overall_status.upper()
        if status == "PASS":
            banner_color = (34, 139, 34)    # Forest green (BGR)
            badge_text = "STATUS: PASS (ALL VISUAL CRITERIA SATISFIED)"
        elif status == "FAIL":
            banner_color = (34, 34, 200)    # Crimson red (BGR)
            badge_text = f"STATUS: FAIL ({rule_result.highest_severity} VIOLATION)"
        else:
            banner_color = (0, 140, 255)    # Amber orange (BGR)
            badge_text = "STATUS: REVIEW (INSUFFICIENT VISUAL EVIDENCE)"

        banner_height = 42
        cv2.rectangle(canvas, (0, 0), (w, banner_height), banner_color, -1)
        cv2.putText(
            canvas,
            badge_text,
            (16, 28),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # 4. Draw Bottom Watermark (Audit Trail)
        footer_height = 30
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, h - footer_height), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        watermark_text = (
            f"SAFETYVISION AI  |  ID: {inspection_id}  |  "
            f"TIMESTAMP: {ts.strftime('%Y-%m-%d %H:%M:%S')}  |  "
            f"EQ: {rule_result.equipment_display_name}"
        )
        cv2.putText(
            canvas,
            watermark_text,
            (14, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        # 5. Save Evidence Image
        date_folder = self.evidence_dir / ts.strftime("%Y") / ts.strftime("%m") / ts.strftime("%d")
        date_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{inspection_id}.jpg"
        target_path = date_folder / filename

        cv2.imwrite(str(target_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        self.logger.info(f"Evidence image written to {target_path}")

        return canvas, target_path

    def _load_as_bgr(self, inp: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """Converts diverse image formats into standard BGR numpy array."""
        if isinstance(inp, (str, Path)):
            path = Path(inp)
            if not path.exists():
                raise FileNotFoundError(f"Image not found at {path}")
            # Use imdecode to handle paths with special characters on Windows
            data = np.fromfile(str(path), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Failed to decode image from {path}")
            return img

        if isinstance(inp, Image.Image):
            rgb = np.array(inp.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if isinstance(inp, np.ndarray):
            if len(inp.shape) == 2:
                return cv2.cvtColor(inp, cv2.COLOR_GRAY2BGR)
            if inp.shape[2] == 4:
                return cv2.cvtColor(inp, cv2.COLOR_BGRA2BGR)
            return inp

        raise TypeError(f"Unsupported image input type: {type(inp)}")
