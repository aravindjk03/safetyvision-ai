"""
Unit Tests for SafetyVision AI Spatial Reasoning Module
"""

import pytest

from app.spatial import (
    calculate_containment,
    calculate_iou,
    center_distance,
    is_component_associated,
)


def test_calculate_iou():
    box1 = [0, 0, 10, 10]
    box2 = [0, 0, 10, 10]
    assert calculate_iou(box1, box2) == 1.0

    box3 = [10, 10, 20, 20]
    assert calculate_iou(box1, box3) == 0.0

    box4 = [5, 0, 15, 10]
    # Inter: [5, 0, 10, 10] area = 50. Union: 100 + 100 - 50 = 150 -> 50/150 = 1/3
    assert abs(calculate_iou(box1, box4) - (1.0 / 3.0)) < 1e-4


def test_center_distance():
    box1 = [0, 0, 10, 10]     # Center: 5, 5
    box2 = [30, 40, 50, 60]   # Center: 40, 50
    # dx = 35, dy = 45 -> hypot = sqrt(35^2 + 45^2)
    dist = center_distance(box1, box2)
    assert round(dist, 2) == 57.01


def test_calculate_containment():
    equipment = [100, 100, 400, 300]
    component_inside = [150, 150, 200, 200]
    # 100% inside
    assert calculate_containment(component_inside, equipment) == 1.0

    component_outside = [10, 10, 50, 50]
    assert calculate_containment(component_outside, equipment) == 0.0


def test_component_association():
    equipment_box = [180, 240, 480, 390]  # Typical angle grinder body

    # Attached Guard near spindle end [440, 220, 560, 400]
    guard_attached = [440, 220, 560, 400]
    is_assoc, metrics = is_component_associated(equipment_box, guard_attached)
    assert is_assoc is True

    # Detached Guard located far away in background [20, 20, 80, 80]
    guard_distant = [20, 20, 80, 80]
    is_assoc_distant, metrics_distant = is_component_associated(equipment_box, guard_distant)
    assert is_assoc_distant is False
