"""
SafetyVision AI — Conveyor Inspection Region of Interest (ROI) Module
Monitors designated spatial zones on industrial conveyor lines, tracks object entry,
checks centering and motion stability, and generates automatic capture triggers.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from app.config import get_config
from app.detector import Detection
from app.logger import get_logger


@dataclass
class ROIStatus:
    """Status of conveyor inspection zone."""
    object_present: bool
    is_centered: bool
    is_stable: bool
    trigger_capture: bool
    consecutive_stable_frames: int
    roi_bbox_pixels: List[int]  # [x1, y1, x2, y2]
    center_offset_x: float
    center_offset_y: float


class ConveyorROIManager:
    """
    Manages dynamic Region of Interest tracking for automated inline conveyor inspection.
    """

    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        conveyor_cfg = self.config.system_config.get("conveyor", {})

        # Normalized coordinates [x1, y1, x2, y2] within [0.0, 1.0]
        self.roi_normalized = conveyor_cfg.get("roi_coordinates", [0.15, 0.15, 0.85, 0.85])
        self.stability_threshold = conveyor_cfg.get("stability_frame_threshold", 5)
        self.center_tolerance = conveyor_cfg.get("center_tolerance", 0.10)

        self._consecutive_stable_frames = 0
        self._last_center: Optional[Tuple[float, float]] = None

    def get_pixel_roi(self, image_width: int, image_height: int) -> List[int]:
        """Converts normalized ROI to absolute pixel coordinates [x1, y1, x2, y2]."""
        nx1, ny1, nx2, ny2 = self.roi_normalized
        return [
            int(nx1 * image_width),
            int(ny1 * image_height),
            int(nx2 * image_width),
            int(ny2 * image_height),
        ]

    def evaluate_frame(
        self,
        frame_shape: Tuple[int, int],
        detections: List[Detection],
        target_class: str = "grinder",
    ) -> ROIStatus:
        """
        Evaluates whether an equipment item is properly aligned and stable inside the ROI.

        Args:
            frame_shape: (height, width)
            detections: List of current detections from detector
            target_class: Target equipment class name

        Returns:
            ROIStatus object indicating if frame capture should trigger.
        """
        h, w = frame_shape[:2]
        roi_pixels = self.get_pixel_roi(w, h)
        rx1, ry1, rx2, ry2 = roi_pixels
        roi_cx = (rx1 + rx2) / 2.0
        roi_cy = (ry1 + ry2) / 2.0

        # Filter detections for target equipment
        equipment_candidates = [d for d in detections if d.class_name == target_class]

        if not equipment_candidates:
            self._consecutive_stable_frames = 0
            self._last_center = None
            return ROIStatus(
                object_present=False,
                is_centered=False,
                is_stable=False,
                trigger_capture=False,
                consecutive_stable_frames=0,
                roi_bbox_pixels=roi_pixels,
                center_offset_x=0.0,
                center_offset_y=0.0,
            )

        # Select most confident target candidate
        target = max(equipment_candidates, key=lambda d: d.confidence)
        bx1, by1, bx2, by2 = target.bbox
        bcx, bcy = target.center

        # Check if center is inside ROI
        inside_roi = (rx1 <= bcx <= rx2) and (ry1 <= bcy <= ry2)

        # Calculate offset relative to ROI dimensions
        rw = max(1.0, float(rx2 - rx1))
        rh = max(1.0, float(ry2 - ry1))
        norm_offset_x = (bcx - roi_cx) / rw
        norm_offset_y = (bcy - roi_cy) / rh

        is_centered = (abs(norm_offset_x) <= self.center_tolerance) and (abs(norm_offset_y) <= self.center_tolerance)

        # Check stability against previous frame
        is_stable = False
        if self._last_center is not None and inside_roi:
            last_cx, last_cy = self._last_center
            dist_moved = np.hypot(bcx - last_cx, bcy - last_cy)
            # If moved less than 1.5% of ROI diagonal, consider stable
            if dist_moved < (0.015 * np.hypot(rw, rh)):
                self._consecutive_stable_frames += 1
                is_stable = True
            else:
                self._consecutive_stable_frames = 0
        else:
            self._consecutive_stable_frames = 1

        self._last_center = (bcx, bcy)

        # Trigger capture when object is centered and stable for required frames
        trigger_capture = is_centered and (self._consecutive_stable_frames >= self.stability_threshold)

        return ROIStatus(
            object_present=inside_roi,
            is_centered=is_centered,
            is_stable=is_stable,
            trigger_capture=trigger_capture,
            consecutive_stable_frames=self._consecutive_stable_frames,
            roi_bbox_pixels=roi_pixels,
            center_offset_x=round(norm_offset_x, 3),
            center_offset_y=round(norm_offset_y, 3),
        )

    def reset(self) -> None:
        """Resets tracking state."""
        self._consecutive_stable_frames = 0
        self._last_center = None
