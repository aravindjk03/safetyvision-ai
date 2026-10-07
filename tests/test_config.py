"""
Unit Tests for SafetyVision AI Configuration Management
"""

from pathlib import Path
import pytest

from app.config import ConfigManager, get_config


def test_config_loader():
    cfg = get_config()
    assert cfg is not None
    assert cfg.app_name == "SafetyVision AI"
    assert cfg.system_info["app_name"] == "SafetyVision AI"
    assert cfg.high_confidence_threshold == 0.85
    assert cfg.medium_confidence_threshold == 0.60
    assert cfg.low_cutoff_threshold == 0.25


def test_classes_configuration():
    cfg = get_config()
    classes = cfg.classes
    assert len(classes) >= 8

    # Verify standard class IDs
    assert cfg.get_class_name(0) == "grinder"
    assert cfg.get_class_name(1) == "guard"
    assert cfg.get_class_name(2) == "handle"
    assert cfg.get_class_name(3) == "cable"
    assert cfg.get_class_name(4) == "switch"
    assert cfg.get_class_name(5) == "damaged_guard"
    assert cfg.get_class_name(6) == "damaged_cable"
    assert cfg.get_class_name(7) == "person"

    assert cfg.get_class_id("guard") == 1
    assert cfg.get_class_id("non_existent_class") is None

    # Colors
    color_bgr = cfg.get_class_color_bgr("guard")
    assert isinstance(color_bgr, list) and len(color_bgr) == 3


def test_safety_rules_configuration():
    cfg = get_config()
    rules = cfg.get_equipment_rules("angle_grinder")
    assert rules is not None
    assert rules["equipment_class"] == "grinder"
    assert "guard" in rules["mandatory_components"]
    assert "guard" in rules["critical_components"]
    assert rules["component_severities"]["guard"] == "CRITICAL"
    assert rules["component_severities"]["handle"] == "HIGH"
