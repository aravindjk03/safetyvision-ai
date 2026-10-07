"""
SafetyVision AI — Spatial Relationship Analysis Module
Calculates geometric relationships (IoU, containment, center distances)
to verify that detected components physically belong to the target equipment.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def calculate_iou(box_a: List[float], box_b: List[float]) -> float:
    """
    Computes Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2].
    """
    x_a1, y_a1, x_a2, y_a2 = box_a
    x_b1, y_b1, x_b2, y_b2 = box_b

    # Determine intersection rectangle
    x_i1 = max(x_a1, x_b1)
    y_i1 = max(y_a1, y_b1)
    x_i2 = min(x_a2, x_b2)
    y_i2 = min(y_a2, y_b2)

    inter_w = max(0.0, x_i2 - x_i1)
    inter_h = max(0.0, y_i2 - y_i1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, x_a2 - x_a1) * max(0.0, y_a2 - y_a1)
    area_b = max(0.0, x_b2 - x_b1) * max(0.0, y_b2 - y_b1)
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def calculate_containment(component_box: List[float], equipment_box: List[float]) -> float:
    """
    Computes the proportion of the component box that lies inside the equipment box.
    Returns: intersection_area / component_area (0.0 to 1.0)
    """
    xc1, yc1, xc2, yc2 = component_box
    xe1, ye1, xe2, ye2 = equipment_box

    x_i1 = max(xc1, xe1)
    y_i1 = max(yc1, ye1)
    x_i2 = min(xc2, xe2)
    y_i2 = min(yc2, ye2)

    inter_w = max(0.0, x_i2 - x_i1)
    inter_h = max(0.0, y_i2 - y_i1)
    inter_area = inter_w * inter_h

    comp_area = max(0.0, xc2 - xc1) * max(0.0, yc2 - yc1)
    if comp_area <= 0.0:
        return 0.0
    return inter_area / comp_area


def center_distance(box_a: List[float], box_b: List[float]) -> float:
    """Computes Euclidean distance between the centers of two bounding boxes."""
    cx_a = (box_a[0] + box_a[2]) / 2.0
    cy_a = (box_a[1] + box_a[3]) / 2.0
    cx_b = (box_b[0] + box_b[2]) / 2.0
    cy_b = (box_b[1] + box_b[3]) / 2.0
    return math.hypot(cx_a - cx_b, cy_a - cy_b)


def get_box_diagonal(box: List[float]) -> float:
    """Computes the diagonal length of a bounding box."""
    w = max(0.0, box[2] - box[0])
    h = max(0.0, box[3] - box[1])
    return math.hypot(w, h)


def is_component_associated(
    equipment_box: List[float],
    component_box: List[float],
    spatial_config: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Dict[str, float]]:
    """
    Determines if a component bounding box is spatially associated with an equipment box.

    Uses three geometric criteria:
    1. Direct containment / overlap (component is inside or overlapping equipment).
    2. Normalized center distance (component center is within a fraction of equipment diagonal).
    3. Expanded bounding box collision (component touches the equipment's immediate perimeter).

    Args:
        equipment_box: [x1, y1, x2, y2]
        component_box: [x1, y1, x2, y2]
        spatial_config: Dictionary containing thresholds:
            - max_center_distance_factor (default: 1.25)
            - expansion_box_factor (default: 1.40)
            - min_containment_overlap (default: 0.01)

    Returns:
        Tuple of (is_associated: bool, metrics: Dict[str, float])
    """
    cfg = spatial_config or {}
    max_center_factor = float(cfg.get("max_center_distance_factor", 1.25))
    expansion_factor = float(cfg.get("expansion_box_factor", 1.40))
    min_containment = float(cfg.get("min_containment_overlap", 0.01))

    iou = calculate_iou(equipment_box, component_box)
    containment = calculate_containment(component_box, equipment_box)
    c_dist = center_distance(equipment_box, component_box)
    eq_diagonal = get_box_diagonal(equipment_box)
    norm_dist = c_dist / max(eq_diagonal, 1.0)

    # Expanded box check: expand equipment bbox around center by expansion_factor
    ex1, ey1, ex2, ey2 = equipment_box
    ew = ex2 - ex1
    eh = ey2 - ey1
    cx = ex1 + (ew / 2.0)
    cy = ey1 + (eh / 2.0)

    expanded_box = [
        cx - (ew * expansion_factor / 2.0),
        cy - (eh * expansion_factor / 2.0),
        cx + (ew * expansion_factor / 2.0),
        cy + (eh * expansion_factor / 2.0),
    ]
    expanded_containment = calculate_containment(component_box, expanded_box)

    # Association condition:
    # 1. Significant containment/IoU with equipment
    # OR 2. Normalized center distance within threshold AND overlaps expanded perimeter
    is_associated = (
        (containment >= min_containment) or
        (iou > 0.0) or
        (norm_dist <= max_center_factor and expanded_containment > 0.10)
    )

    metrics = {
        "iou": round(iou, 4),
        "containment": round(containment, 4),
        "center_distance": round(c_dist, 2),
        "normalized_distance": round(norm_dist, 4),
        "expanded_containment": round(expanded_containment, 4),
    }

    return is_associated, metrics
