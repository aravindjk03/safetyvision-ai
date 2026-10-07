"""
SafetyVision AI — Object Detection Engine
Wraps Ultralytics YOLO inference, extracts detections, and normalizes coordinates.
Separated strictly from safety decision logic.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image

from app.config import get_config
from app.logger import get_logger


@dataclass
class Detection:
    """Standardized representation of a single detected visual element."""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2] in absolute pixel coordinates
    center: List[float]  # [center_x, center_y]
    width: float
    height: float
    area: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DetectionEngine:
    """Manages YOLO model loading, inference execution, and detection parsing."""

    def __init__(self, weights_path: Optional[Union[str, Path]] = None, device: Optional[str] = None):
        self.logger = get_logger()
        self.config = get_config()
        self.device = device or self.config.device_setting

        self.custom_weights_path = Path(weights_path) if weights_path else self.config.custom_weights_path
        self.demo_weights_path = self.config.demo_weights_path

        self.model = None
        self.is_custom_model = False
        self.model_name = "Uninitialized"
        self.model_version = "0.0.0"
        self.load_model()

    def load_model(self) -> None:
        """Loads custom safety model if available, else gracefully falls back to demo mode."""
        from ultralytics import YOLO

        target_path = None
        if self.custom_weights_path.exists():
            target_path = str(self.custom_weights_path)
            self.is_custom_model = True
            self.model_name = self.config.model_config.get("name", "SafetyVision-YOLO26")
            self.model_version = self._registry_version(self.model_name)
            self.logger.info(f"Loaded CUSTOM SAFETY MODEL: {target_path} (v{self.model_version})")
        else:
            target_path = self.demo_weights_path
            self.is_custom_model = False
            self.model_name = "SafetyVision-Demo-YOLO"
            self.model_version = "0.0.1"
            self.logger.warning(
                f"Custom weights not found at '{self.custom_weights_path}'. "
                f"Loaded DEMO MODEL '{target_path}' — NOT TRAINED FOR INDUSTRIAL SAFETY INSPECTION."
            )

        try:
            self.model = YOLO(target_path)
            self.logger.info(f"YOLO model initialized on device preference: {self.device}")
        except Exception as e:
            self.logger.error(f"Failed to initialize YOLO model from {target_path}: {e}")
            raise RuntimeError(f"Could not load YOLO model: {e}") from e

    def _registry_version(self, model_name: str) -> str:
        """Resolves the model version from models/model_registry.yaml, falling back to the system version."""
        registry = self.config._load_yaml(self.config.root_dir / "models" / "model_registry.yaml")
        active = registry.get("registry", {})
        if active.get("active_model") == model_name and active.get("active_version"):
            return str(active["active_version"])
        for entry in registry.get("models", []) or []:
            if entry.get("model_name") == model_name and entry.get("model_version"):
                return str(entry["model_version"])
        return str(self.config.system_info.get("version", "0.1.0"))

    def detect(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        conf_threshold: Optional[float] = None,
        imgsz: Optional[int] = None,
    ) -> Tuple[List[Detection], float]:
        """
        Runs YOLO inference on an image and returns normalized Detections.

        Args:
            image: Image filepath, numpy BGR/RGB array, or PIL Image.
            conf_threshold: Minimum confidence cutoff. Defaults to low_cutoff in config.
            imgsz: Inference image size. Defaults to config model imgsz.

        Returns:
            Tuple of (detections_list, inference_time_ms)
        """
        if self.model is None:
            raise RuntimeError("Detection model is not loaded.")

        cutoff = conf_threshold if conf_threshold is not None else self.config.low_cutoff_threshold
        target_imgsz = imgsz if imgsz is not None else int(self.config.model_config.get("imgsz", 320))

        # Convert/validate input image
        start_time = time.perf_counter()
        results = self.model.predict(
            source=image,
            conf=cutoff,
            imgsz=target_imgsz,
            device=self.device if self.device != "auto" else None,
            verbose=False,
        )
        inference_time_ms = (time.perf_counter() - start_time) * 1000.0

        detections: List[Detection] = []
        if not results:
            return detections, inference_time_ms

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return detections, inference_time_ms

        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            x1, y1, x2, y2 = xyxy
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)
            cx = x1 + (w / 2.0)
            cy = y1 + (h / 2.0)
            area = w * h

            # Resolve human-readable class name from model names or config mapping
            if self.is_custom_model:
                class_name = self.config.get_class_name(cls_id)
            else:
                # In demo mode, use whatever names the pretrained model has
                class_name = self.model.names.get(cls_id, f"class_{cls_id}")

            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=conf,
                    bbox=[round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    center=[round(cx, 2), round(cy, 2)],
                    width=round(w, 2),
                    height=round(h, 2),
                    area=round(area, 2),
                )
            )

        self.logger.debug(
            f"Inference completed in {inference_time_ms:.2f}ms. Detections count: {len(detections)}"
        )
        return detections, inference_time_ms

    def export_onnx(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """Exports the active model to ONNX format for edge deployment."""
        if self.model is None:
            raise RuntimeError("Model is not loaded for export.")

        target = Path(output_path or self.config.model_config.get("onnx_export_path", "models/safetyvision_yolo26n.onnx"))
        target.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Initiating ONNX export to {target}...")
        exported = self.model.export(format="onnx")
        self.logger.info(f"ONNX export successful: {exported}")
        return Path(exported)
