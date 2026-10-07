"""
SafetyVision AI — Configuration Loader
Loads and validates system, class, and safety rule configurations.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigManager:
    """Manages application configuration, class mappings, and safety rules."""

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            # Anchor to project root (directory containing 'config' folder)
            current = Path(__file__).resolve().parent
            if (current.parent / "config").exists():
                self.root_dir = current.parent
            else:
                self.root_dir = current
        else:
            self.root_dir = Path(root_dir)

        self.config_dir = self.root_dir / "config"
        self._system_config: Dict[str, Any] = {}
        self._classes_config: Dict[str, Any] = {}
        self._safety_rules_config: Dict[str, Any] = {}

        self.reload()

    def reload(self) -> None:
        """Reload all configuration files from disk."""
        self._system_config = self._load_yaml(self.config_dir / "config.yaml")
        self._classes_config = self._load_yaml(self.config_dir / "classes.yaml")
        self._safety_rules_config = self._load_yaml(self.config_dir / "safety_rules.yaml")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Safely load a YAML file, returning empty dict if missing."""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # System Configuration Accessors
    @property
    def system_config(self) -> Dict[str, Any]:
        return self._system_config

    @property
    def system_info(self) -> Dict[str, Any]:
        return self._system_config.get("system", {})

    @property
    def app_name(self) -> str:
        return self.system_info.get("app_name", "SafetyVision AI")

    @property
    def model_config(self) -> Dict[str, Any]:
        return self._system_config.get("model", {})

    @property
    def custom_weights_path(self) -> Path:
        rel = self.model_config.get("custom_weights_path", "models/safetyvision_yolo26n.pt")
        return (self.root_dir / rel).resolve()

    @property
    def demo_weights_path(self) -> str:
        return self.model_config.get("demo_weights_path", "yolo11n.pt")

    @property
    def device_setting(self) -> str:
        return self.model_config.get("device", "auto")

    @property
    def database_path(self) -> Path:
        rel = self._system_config.get("storage", {}).get("database_path", "data/safetyvision.db")
        path = (self.root_dir / rel).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def evidence_dir(self) -> Path:
        rel = self._system_config.get("storage", {}).get("evidence_dir", "evidence")
        path = (self.root_dir / rel).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        rel = self._system_config.get("storage", {}).get("reports_dir", "reports")
        path = (self.root_dir / rel).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def logs_dir(self) -> Path:
        rel = self._system_config.get("storage", {}).get("logs_dir", "logs")
        path = (self.root_dir / rel).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Confidence Thresholds
    @property
    def high_confidence_threshold(self) -> float:
        return float(self._system_config.get("confidence", {}).get("high", 0.85))

    @property
    def medium_confidence_threshold(self) -> float:
        return float(self._system_config.get("confidence", {}).get("medium", 0.60))

    @property
    def low_cutoff_threshold(self) -> float:
        return float(self._system_config.get("confidence", {}).get("low_cutoff", 0.25))

    # Class Metadata Accessors
    @property
    def classes(self) -> Dict[int, Dict[str, Any]]:
        raw = self._classes_config.get("classes", {})
        return {int(k): v for k, v in raw.items()}

    def get_class_name(self, class_id: int) -> str:
        info = self.classes.get(class_id)
        return info["name"] if info else f"class_{class_id}"

    def get_class_id(self, class_name: str) -> Optional[int]:
        for cid, info in self.classes.items():
            if info.get("name") == class_name:
                return cid
        return None

    def get_class_color_bgr(self, class_name: str) -> List[int]:
        for info in self.classes.values():
            if info.get("name") == class_name:
                return info.get("color_bgr", [0, 255, 0])
        return [0, 255, 0]

    def get_class_color_rgb(self, class_name: str) -> List[int]:
        for info in self.classes.values():
            if info.get("name") == class_name:
                return info.get("color_rgb", [0, 255, 0])
        return [0, 255, 0]

    def get_display_name(self, class_name: str) -> str:
        for info in self.classes.values():
            if info.get("name") == class_name:
                return info.get("display_name", class_name.title())
        return class_name.replace("_", " ").title()

    # Safety Rules Accessors
    def get_equipment_rules(self, equipment_key: str = "angle_grinder") -> Dict[str, Any]:
        equipments = self._safety_rules_config.get("equipment", {})
        return equipments.get(equipment_key, {})

    def get_all_equipment_keys(self) -> List[str]:
        return list(self._safety_rules_config.get("equipment", {}).keys())


# Singleton instance for convenient application-wide access
_cfg_instance: Optional[ConfigManager] = None


def get_config(root_dir: Optional[Path] = None) -> ConfigManager:
    global _cfg_instance
    if _cfg_instance is None or root_dir is not None:
        _cfg_instance = ConfigManager(root_dir)
    return _cfg_instance
