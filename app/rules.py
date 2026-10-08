"""
SafetyVision AI — Deterministic Safety Rule Engine
Translates physical detections and spatial relationships into auditable compliance results.
Enforces the mandatory three-state decision system: PASS / FAIL / REVIEW.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_config
from app.detector import Detection
from app.logger import get_logger
from app.spatial import is_component_associated


@dataclass
class ComponentCheck:
    """Audit result for a single safety component or condition."""
    component_name: str
    display_name: str
    status: str          # "PASS", "FAIL", "REVIEW"
    severity: str        # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    confidence: float
    is_mandatory: bool
    is_associated: bool
    message: str
    detection_bbox: Optional[List[float]] = None
    spatial_metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RuleEvaluationResult:
    """Comprehensive evaluation payload produced by the safety rule engine."""
    equipment: str
    equipment_display_name: str
    equipment_detected: bool
    equipment_confidence: float
    equipment_bbox: Optional[List[float]]
    overall_status: str         # "PASS", "FAIL", "REVIEW"
    highest_severity: str       # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    missing_components: List[str] = field(default_factory=list)
    detected_components: List[str] = field(default_factory=list)
    damage_violations: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    reason: str = ""
    recommended_action: str = ""
    disclaimer: str = (
        "Automated visual inspection identifies configured visual conditions only. "
        "It does not replace competent-person inspection, manufacturer requirements, "
        "statutory requirements, risk assessment, or preventive maintenance."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SafetyRuleEngine:
    """Evaluates detections against configurable industrial safety rules."""

    AUTO = "auto"
    DEFAULT_EQUIPMENT = "angle_grinder"

    def __init__(self, equipment_key: str = AUTO):
        self.logger = get_logger()
        self.config = get_config()
        self.equipment_key = equipment_key
        self.auto_select = equipment_key == self.AUTO
        self.rules = self.config.get_equipment_rules(self.DEFAULT_EQUIPMENT if self.auto_select else equipment_key)

        if not self.rules:
            self.logger.warning(f"No rules found for equipment '{equipment_key}', using defaults.")

    def _equipment_classes(self) -> Dict[str, str]:
        """Maps each configured equipment detection class to its rules key."""
        mapping = {}
        for key in self.config.get_all_equipment_keys():
            eq_class = self.config.get_equipment_rules(key).get("equipment_class")
            if eq_class:
                mapping[eq_class] = key
        return mapping

    def _select_rules(self, detections: List[Detection]) -> Tuple[Dict[str, Any], List[Detection]]:
        """
        Returns the rule set to apply and the equipment detections it is judged on.
        In auto mode the most confident detected equipment type decides which rules apply, and every
        configured equipment type counts towards the one-item-per-inspection check.
        """
        if not self.auto_select:
            eq_class = self.rules.get("equipment_class", "grinder")
            return self.rules, [d for d in detections if d.class_name == eq_class]

        eq_classes = self._equipment_classes()
        candidates = [d for d in detections if d.class_name in eq_classes]
        if not candidates:
            return self.rules, []
        best = max(candidates, key=lambda d: d.confidence)
        return self.config.get_equipment_rules(eq_classes[best.class_name]), candidates

    def evaluate(self, detections: List[Detection]) -> RuleEvaluationResult:
        """
        Executes deterministic rule evaluation against extracted detections.

        Step 1: Equipment identification & count check.
        Step 2: Damage violation screening.
        Step 3: Component spatial association & confidence assessment.
        Step 4: Final status aggregation & recommendation synthesis.
        """
        rules, equipment_detections = self._select_rules(detections)
        eq_class = rules.get("equipment_class", "grinder")
        eq_display = rules.get("display_name", "Angle Grinder")
        mandatory_components = rules.get("mandatory_components", ["guard", "handle", "cable", "switch"])
        severities = rules.get("component_severities", {})
        spatial_cfg = rules.get("spatial", {})
        damage_specs = rules.get("damage_violations", {})

        high_thresh = self.config.high_confidence_threshold
        med_thresh = self.config.medium_confidence_threshold

        # Step 1: Detect equipment instance(s)

        # Case 1A: No equipment detected
        if len(equipment_detections) == 0:
            return RuleEvaluationResult(
                equipment=eq_class,
                equipment_display_name=eq_display,
                equipment_detected=False,
                equipment_confidence=0.0,
                equipment_bbox=None,
                overall_status="REVIEW",
                highest_severity="MEDIUM",
                findings=[
                    "Target equipment chassis was not detected in the image."
                    if not self.auto_select
                    else "No supported equipment (angle grinder or power drill) was detected in the image."
                ],
                warnings=["Insufficient visual evidence or equipment absent."],
                reason="REVIEW — Target equipment could not be identified with adequate confidence.",
                recommended_action="Re-align camera framing, verify lighting, and ensure equipment is fully in view.",
            )

        # Case 1B: Multiple equipment items in scene
        if len(equipment_detections) > 1:
            best_eq = max(equipment_detections, key=lambda d: d.confidence)
            return RuleEvaluationResult(
                equipment=eq_class,
                equipment_display_name=eq_display,
                equipment_detected=True,
                equipment_confidence=best_eq.confidence,
                equipment_bbox=best_eq.bbox,
                overall_status="REVIEW",
                highest_severity="MEDIUM",
                findings=[f"Multiple ({len(equipment_detections)}) candidate equipment objects detected."],
                warnings=["Multiple equipment items in field of view."],
                reason="REVIEW — Multiple candidate equipment objects detected. Scene requires operator disambiguation.",
                recommended_action="Isolate target equipment in camera frame so only one unit is inspected at a time.",
            )

        # Primary equipment object selected
        primary_eq = equipment_detections[0]
        eq_box = primary_eq.bbox

        checks_dict: Dict[str, Dict[str, Any]] = {}
        detected_components: List[str] = []
        missing_components: List[str] = []
        damage_violations: List[str] = []
        findings: List[str] = []
        warnings: List[str] = []

        overall_status = "PASS"
        highest_severity = "NONE"

        def update_severity(sev: str):
            nonlocal highest_severity
            rank = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            if rank.get(sev, 0) > rank.get(highest_severity, 0):
                highest_severity = sev

        # Step 2: Screen for damage classes
        for d in detections:
            if d.class_name in damage_specs:
                is_assoc, metrics = is_component_associated(eq_box, d.bbox, spatial_cfg)
                if is_assoc and d.confidence >= med_thresh:
                    spec = damage_specs[d.class_name]
                    sev = spec.get("severity", "CRITICAL")
                    damage_violations.append(d.class_name)
                    findings.append(f"VIOLATION: {spec.get('reason')} (Confidence: {d.confidence * 100:.1f}%)")
                    update_severity(sev)
                    overall_status = "FAIL"

                    checks_dict[d.class_name] = ComponentCheck(
                        component_name=d.class_name,
                        display_name=self.config.get_display_name(d.class_name),
                        status="FAIL",
                        severity=sev,
                        confidence=d.confidence,
                        is_mandatory=False,
                        is_associated=True,
                        message=spec.get("reason", "Structural damage observed"),
                        detection_bbox=d.bbox,
                        spatial_metrics=metrics,
                    ).to_dict()

        # Step 3: Evaluate mandatory components
        for comp_name in mandatory_components:
            comp_display = self.config.get_display_name(comp_name)
            sev = severities.get(comp_name, "HIGH")

            # Find candidate detections for this component
            candidates = [d for d in detections if d.class_name == comp_name]

            # Filter candidates that are spatially associated with the grinder
            associated_candidates = []
            for c in candidates:
                is_assoc, metrics = is_component_associated(eq_box, c.bbox, spatial_cfg)
                if is_assoc:
                    associated_candidates.append((c, metrics))

            if not associated_candidates:
                # Component is missing or not attached
                missing_components.append(comp_name)
                comp_desc = rules.get("component_descriptions", {}).get(
                    comp_name, f"Mandatory {comp_name} was not detected."
                )
                findings.append(f"CRITICAL FINDING: {comp_desc}")
                update_severity(sev)
                overall_status = "FAIL"

                checks_dict[comp_name] = ComponentCheck(
                    component_name=comp_name,
                    display_name=comp_display,
                    status="FAIL",
                    severity=sev,
                    confidence=0.0,
                    is_mandatory=True,
                    is_associated=False,
                    message=comp_desc,
                    detection_bbox=None,
                    spatial_metrics=None,
                ).to_dict()
            else:
                # Select the highest-confidence associated candidate
                best_comp, best_metrics = max(associated_candidates, key=lambda item: item[0].confidence)

                if best_comp.confidence >= high_thresh:
                    # Confident detection
                    detected_components.append(comp_name)
                    checks_dict[comp_name] = ComponentCheck(
                        component_name=comp_name,
                        display_name=comp_display,
                        status="PASS",
                        severity="NONE",
                        confidence=best_comp.confidence,
                        is_mandatory=True,
                        is_associated=True,
                        message=f"{comp_display} verified in position.",
                        detection_bbox=best_comp.bbox,
                        spatial_metrics=best_metrics,
                    ).to_dict()
                elif best_comp.confidence >= med_thresh:
                    # Ambiguous detection -> Flag for human review
                    detected_components.append(comp_name)
                    warnings.append(
                        f"{comp_display} detected with marginal confidence ({best_comp.confidence * 100:.1f}%)."
                    )
                    update_severity("MEDIUM")
                    if overall_status != "FAIL":
                        overall_status = "REVIEW"

                    checks_dict[comp_name] = ComponentCheck(
                        component_name=comp_name,
                        display_name=comp_display,
                        status="REVIEW",
                        severity="MEDIUM",
                        confidence=best_comp.confidence,
                        is_mandatory=True,
                        is_associated=True,
                        message=f"{comp_display} detection ambiguous or partially occluded.",
                        detection_bbox=best_comp.bbox,
                        spatial_metrics=best_metrics,
                    ).to_dict()
                else:
                    # Low confidence -> Below cutoff, treat as missing
                    missing_components.append(comp_name)
                    findings.append(
                        f"Insufficient visual evidence for {comp_display} (confidence {best_comp.confidence * 100:.1f}% below threshold)."
                    )
                    update_severity(sev)
                    overall_status = "FAIL"

                    checks_dict[comp_name] = ComponentCheck(
                        component_name=comp_name,
                        display_name=comp_display,
                        status="FAIL",
                        severity=sev,
                        confidence=best_comp.confidence,
                        is_mandatory=True,
                        is_associated=True,
                        message="Component confidence below industrial acceptance threshold.",
                        detection_bbox=best_comp.bbox,
                        spatial_metrics=best_metrics,
                    ).to_dict()

        # Step 4: Synthesize Reason & Recommended Action
        if overall_status == "PASS":
            reason = f"PASS — All mandatory safety components detected and spatially verified on {eq_display}."
            recommended_action = "Equipment satisfies configured visual safety requirements. Proceed with standard operational workflow."
        elif overall_status == "FAIL":
            parts = []
            if missing_components:
                parts.append(f"Missing mandatory components: {', '.join(missing_components)}")
            if damage_violations:
                parts.append(f"Structural damage observed: {', '.join(damage_violations)}")
            reason = f"FAIL — {'; '.join(parts)}."
            recommended_action = (
                "Do NOT operate tool. Lockout/tagout equipment immediately and schedule a certified "
                "competent-person mechanical and electrical safety inspection."
            )
        else:  # REVIEW
            reason = "REVIEW — Insufficient or ambiguous visual evidence. Component confidence or visual conditions require verification."
            recommended_action = (
                "Perform physical manual inspection by a qualified operator or competent person. "
                "Ensure lighting is uniform and retake inspection photograph if necessary."
            )

        return RuleEvaluationResult(
            equipment=eq_class,
            equipment_display_name=eq_display,
            equipment_detected=True,
            equipment_confidence=primary_eq.confidence,
            equipment_bbox=primary_eq.bbox,
            overall_status=overall_status,
            highest_severity=highest_severity,
            checks=checks_dict,
            missing_components=missing_components,
            detected_components=detected_components,
            damage_violations=damage_violations,
            findings=findings,
            warnings=warnings,
            reason=reason,
            recommended_action=recommended_action,
        )
