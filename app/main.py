"""
SafetyVision AI — Industrial Visual Safety Inspection Dashboard
Built with Streamlit. Professional, auditable, high-contrast industrial interface.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

from app.config import get_config
from app.database import DatabaseManager
from app.detector import DetectionEngine
from app.evidence import EvidenceGenerator
from app.inspection import InspectionEngine
from app.logger import get_logger
from app.report import ReportGenerator
from app.rules import SafetyRuleEngine

# Initialize core services
logger = get_logger()
cfg = get_config(ROOT_DIR)


# Page Configuration
st.set_page_config(
    page_title="SafetyVision AI | Industrial Safety Inspection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Industrial CSS Styling
st.markdown("""
<style>
    /* Industrial dark slate header and typography */
    .main-header {
        background: linear-gradient(90deg, #0D233A 0%, #1E3A8A 100%);
        padding: 18px 24px;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: white !important;
    }
    .main-header p {
        margin: 4px 0 0 0;
        font-size: 13px;
        color: #94A3B8;
    }

    /* Statutory safety disclaimer callout */
    .disclaimer-box {
        background-color: #F8FAFC;
        border-left: 4px solid #475569;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        font-size: 12px;
        color: #334155;
        margin-bottom: 20px;
    }

    /* Status banner blocks */
    .status-pass {
        background: #2E7D32;
        color: white;
        padding: 14px 20px;
        border-radius: 6px;
        font-size: 20px;
        font-weight: 700;
        text-align: center;
        margin: 12px 0;
    }
    .status-fail {
        background: #C62828;
        color: white;
        padding: 14px 20px;
        border-radius: 6px;
        font-size: 20px;
        font-weight: 700;
        text-align: center;
        margin: 12px 0;
    }
    .status-review {
        background: #EF6C00;
        color: white;
        padding: 14px 20px;
        border-radius: 6px;
        font-size: 20px;
        font-weight: 700;
        text-align: center;
        margin: 12px 0;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0D233A;
    }
    .metric-label {
        font-size: 12px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_inspection_pipeline():
    """Initializes and caches the detection and inspection engine."""
    detector = DetectionEngine()
    rule_engine = SafetyRuleEngine()
    db = DatabaseManager()
    evidence_gen = EvidenceGenerator()
    report_gen = ReportGenerator()
    engine = InspectionEngine(
        detector=detector,
        rule_engine=rule_engine,
        db_manager=db,
        evidence_generator=evidence_gen,
        report_generator=report_gen,
    )
    return engine, detector, db


engine, detector, db = get_inspection_pipeline()

# Sidebar Navigation
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 15px;">
    <h2 style="color: #0D233A; margin: 0;">🛡️ SAFETYVISION AI</h2>
    <p style="color: #64748B; font-size: 12px; margin: 0;">Industrial Visual Inspection</p>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigation",
    [
        "Single Inspection",
        "Live Camera",
        "Inspection History",
        "Reports & Analytics",
        "Safety Rules & Config",
        "Model Information",
    ],
)

# Active Model Status Indicator in Sidebar
st.sidebar.markdown("---")
if detector.is_custom_model:
    st.sidebar.success(f"**MODE:** CUSTOM SAFETY MODEL\n\n**MODEL:** {detector.model_name}\n\n**VER:** {detector.model_version}")
else:
    st.sidebar.warning(f"**MODE:** DEMO MODE\n\n**NOTICE:** NOT TRAINED FOR INDUSTRIAL SAFETY INSPECTION\n\n**BASE:** {detector.model_name}")

st.sidebar.markdown("""
<div style="font-size: 11px; color: #94A3B8; margin-top: 20px;">
    SafetyVision AI v0.1.0<br/>
    ISO 27001 / OSHA 1910 Grounded<br/>
    Industrial Proof-of-Concept
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: SINGLE INSPECTION
# ==============================================================================
if menu == "Single Inspection":
    st.markdown("""
    <div class="main-header">
        <h1>Industrial Visual Safety Inspection</h1>
        <p>Automated visual component verification and deterministic safety rule audit</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer-box">
        <b>STATUTORY SAFETY NOTICE:</b> Automated visual inspection verifies configured visual conditions only.
        It does not certify physical or operational safety and does NOT replace competent-person inspection,
        manufacturer guidelines, statutory risk assessments, or formal lockout/tagout procedures.
    </div>
    """, unsafe_allow_html=True)

    col_input, col_meta = st.columns([2, 1])

    with col_meta:
        st.subheader("Inspection Parameters")
        target_equipment = st.selectbox("Target Equipment", ["Angle Grinder"], index=0)
        operator_name = st.text_input("Operator / Inspector ID", value="Tech-104")
        inspection_notes = st.text_input("Audit Notes / Station", value="Workstation Bench #3")
        conf_override = st.slider("Confidence Cutoff", min_value=0.10, max_value=0.95, value=0.25, step=0.05)

    with col_input:
        st.subheader("Source Image")
        source_mode = st.radio("Input Source", ["Upload Image", "Sample Industrial Test Cases"], horizontal=True)
        image_to_inspect = None

        if source_mode == "Upload Image":
            uploaded_file = st.file_uploader(
                "Choose equipment photograph (JPEG, PNG, WebP)",
                type=["jpg", "jpeg", "png", "webp", "bmp"],
            )
            if uploaded_file is not None:
                try:
                    image_to_inspect = Image.open(uploaded_file)
                except Exception as e:
                    st.error(f"Error loading uploaded image: {e}")

        else:
            # Sample synthetic test case selector
            sample_dir = cfg.root_dir / "dataset" / "images" / "test"
            sample_files = list(sample_dir.glob("*.jpg")) + list(sample_dir.glob("*.png"))

            if sample_files:
                sample_choice = st.selectbox(
                    "Select standard acceptance test case",
                    sample_files,
                    format_func=lambda p: p.name,
                )
                if sample_choice:
                    image_to_inspect = Image.open(sample_choice)
            else:
                st.info("No sample test images currently found in dataset/images/test. Please upload an image.")

    if image_to_inspect is not None:
        st.markdown("---")
        preview_col, btn_col = st.columns([3, 1])
        with preview_col:
            st.image(image_to_inspect, caption="Input Frame Preview", use_container_width=True)
        with btn_col:
            st.markdown("### Execute Audit")
            st.write("Click below to execute detection, spatial reasoning, and rule evaluation.")
            run_btn = st.button("RUN INSPECTION", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner("Analyzing physical observations & evaluating safety rules..."):
                try:
                    result = engine.inspect(
                        image_input=image_to_inspect,
                        operator=operator_name,
                        comments=inspection_notes,
                        conf_threshold=conf_override,
                    )
                    st.session_state["last_result"] = result
                except Exception as e:
                    st.error(f"Inspection failed: {e}")
                    logger.error(f"Inspection exception: {e}", exc_info=True)

    # Render Inspection Results if available
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        st.markdown("---")
        st.subheader(f"Inspection Report — ID: {res['inspection_id']}")

        # Overall Status Banner
        status = res["overall_status"]
        if status == "PASS":
            st.markdown(f'<div class="status-pass">OVERALL RESULT: PASS (ALL VISUAL REQUIREMENTS SATISFIED)</div>', unsafe_allow_html=True)
        elif status == "FAIL":
            st.markdown(f'<div class="status-fail">OVERALL RESULT: FAIL ({res["highest_severity"]} SEVERITY VIOLATION)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-review">OVERALL RESULT: REVIEW (INSUFFICIENT VISUAL EVIDENCE)</div>', unsafe_allow_html=True)

        # Performance & Timing Bar
        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        t_col1.metric("AI Confidence", f"{res['confidence'] * 100:.1f}%")
        t_col2.metric("Inference Latency", f"{res['timing']['inference_ms']} ms")
        t_col3.metric("Rule Evaluation", f"{res['timing']['rules_evaluation_ms']} ms")
        t_col4.metric("Total Cycle Time", f"{res['timing']['total_time_ms']} ms ({res['timing']['fps']} FPS)")

        # Evidence Display & Findings
        ev_col, findings_col = st.columns([1, 1])
        with ev_col:
            st.markdown("#### Annotated Evidence Image")
            ev_path = Path(res["evidence_path"])
            if ev_path.exists():
                st.image(str(ev_path), caption=f"Evidence: {ev_path.name}", use_container_width=True)

        with findings_col:
            st.markdown("#### Audit Decision Breakdown")
            st.write(f"**Root Reason:** {res['reason']}")
            st.write(f"**Recommended Action:** {res['recommended_action']}")

            if res["missing_components"]:
                st.error(f"Missing Mandatory Components: {', '.join(res['missing_components'])}")
            if res["damage_violations"]:
                st.error(f"Structural Damage Violations: {', '.join(res['damage_violations'])}")
            if res["warnings"]:
                for w in res["warnings"]:
                    st.warning(w)

            # PDF Download
            rep_path = Path(res.get("report_path", ""))
            if rep_path.exists():
                with open(rep_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="DOWNLOAD OFFICIAL PDF AUDIT REPORT",
                    data=pdf_bytes,
                    file_name=rep_path.name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        # Component Verification Table
        st.markdown("#### Component Verification Details")
        checks_data = []
        for cname, cinfo in res["checks"].items():
            checks_data.append({
                "Component": cinfo.get("display_name", cname),
                "Mandatory": "Yes" if cinfo.get("is_mandatory") else "No",
                "Status": cinfo.get("status"),
                "Confidence": f"{cinfo.get('confidence', 0.0) * 100:.1f}%",
                "Severity": cinfo.get("severity"),
                "Spatial Associated": "Yes" if cinfo.get("is_associated") else "No",
                "Audit Message": cinfo.get("message"),
            })
        if checks_data:
            df_checks = pd.DataFrame(checks_data)
            st.dataframe(df_checks, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE 2: LIVE CAMERA
# ==============================================================================
elif menu == "Live Camera":
    st.markdown("""
    <div class="main-header">
        <h1>Live Camera Inspection Station</h1>
        <p>Webcam capture, optical framing, and snapshot safety evaluation</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer-box">
        <b>CAMERA GUIDELINE:</b> Frame equipment centered under uniform industrial lighting.
        Avoid severe backlight, reflections, and partial occlusion before triggering inspection snapshot.
    </div>
    """, unsafe_allow_html=True)

    cam_col, ctrl_col = st.columns([2, 1])

    with ctrl_col:
        st.subheader("Station Controls")
        operator_cam = st.text_input("Operator ID", value="Line-Operator-02")
        comments_cam = st.text_input("Station Location", value="Assembly Jig A")
        st.info("Point camera at equipment and capture a frame when stationary.")

    with cam_col:
        st.subheader("Camera Feed")
        cam_image = st.camera_input("Capture Inspection Frame")

        if cam_image is not None:
            pil_cam = Image.open(cam_image)
            st.write("Snapshot captured! Click below to execute safety audit.")
            if st.button("AUDIT CAPTURED FRAME", type="primary"):
                with st.spinner("Processing image through SafetyVision AI pipeline..."):
                    res = engine.inspect(
                        image_input=pil_cam,
                        operator=operator_cam,
                        comments=comments_cam,
                    )
                    st.session_state["last_result"] = res
                    st.success(f"Audit completed: {res['overall_status']} (ID: {res['inspection_id']})")


# ==============================================================================
# PAGE 3: INSPECTION HISTORY
# ==============================================================================
elif menu == "Inspection History":
    st.markdown("""
    <div class="main-header">
        <h1>Historical Inspection Records</h1>
        <p>Immutable audit trail stored in SQLite database</p>
    </div>
    """, unsafe_allow_html=True)

    filter_c1, filter_c2, filter_c3 = st.columns(3)
    with filter_c1:
        f_status = st.selectbox("Filter Status", ["ALL", "PASS", "FAIL", "REVIEW"], index=0)
    with filter_c2:
        f_eq = st.selectbox("Equipment Type", ["ALL", "grinder", "angle_grinder"], index=0)
    with filter_c3:
        f_search = st.text_input("Search Inspection ID", "")

    records = db.get_history(limit=100, filter_status=f_status, filter_equipment=f_eq, search_id=f_search)

    if not records:
        st.info("No inspection records match the current filters.")
    else:
        df_hist = pd.DataFrame(records)
        display_cols = ["inspection_id", "timestamp", "equipment_type", "overall_status", "highest_severity", "confidence", "operator", "inference_time_ms", "total_time_ms"]
        available_cols = [c for c in display_cols if c in df_hist.columns]
        st.dataframe(df_hist[available_cols], use_container_width=True, hide_index=True)

        st.markdown("### Record Detail & Evidence Viewer")
        selected_id = st.selectbox("Select Inspection to View", [r["inspection_id"] for r in records])
        if selected_id:
            full_rec = db.get_inspection(selected_id)
            if full_rec:
                det_c1, det_c2 = st.columns([1, 1])
                with det_c1:
                    ev_file = Path(full_rec.get("evidence_path", ""))
                    if ev_file.exists():
                        st.image(str(ev_file), caption=f"Evidence: {selected_id}", use_container_width=True)
                with det_c2:
                    st.write(f"**Overall Status:** {full_rec['overall_status']}")
                    st.write(f"**Highest Severity:** {full_rec['highest_severity']}")
                    st.write(f"**Confidence:** {full_rec['confidence']*100:.1f}%")
                    st.write(f"**Timestamp:** {full_rec['timestamp']}")
                    st.write(f"**Reason:** {full_rec.get('reason', '')}")
                    st.write(f"**Action:** {full_rec.get('recommended_action', '')}")

                    rep_file = Path(full_rec.get("report_path", ""))
                    if rep_file.exists():
                        with open(rep_file, "rb") as f:
                            st.download_button("Download Report PDF", f.read(), file_name=rep_file.name, mime="application/pdf")


# ==============================================================================
# PAGE 4: REPORTS & ANALYTICS
# ==============================================================================
elif menu == "Reports & Analytics":
    st.markdown("""
    <div class="main-header">
        <h1>Quality & Safety Analytics Dashboard</h1>
        <p>Operational safety metrics, compliance ratios, and cycle times</p>
    </div>
    """, unsafe_allow_html=True)

    stats = db.get_statistics()

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.markdown(f'<div class="metric-card"><div class="metric-value">{stats["total_inspections"]}</div><div class="metric-label">Total Inspected</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #2E7D32;">{stats["pass_count"]}</div><div class="metric-label">Pass Count</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #C62828;">{stats["fail_count"]}</div><div class="metric-label">Fail Count</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #EF6C00;">{stats["review_count"]}</div><div class="metric-label">Review Count</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="metric-card"><div class="metric-value">{stats["failure_rate_pct"]}%</div><div class="metric-label">Failure Rate</div></div>', unsafe_allow_html=True)
    m6.markdown(f'<div class="metric-card"><div class="metric-value">{stats["avg_inference_ms"]} ms</div><div class="metric-label">Avg Inference</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Compliance Distribution")
        if stats["total_inspections"] > 0:
            df_dist = pd.DataFrame({
                "Status": ["PASS", "FAIL", "REVIEW"],
                "Count": [stats["pass_count"], stats["fail_count"], stats["review_count"]],
            })
            st.bar_chart(df_dist.set_index("Status"))
        else:
            st.info("No data yet recorded.")

    with c2:
        st.subheader("Performance & Quality Rates")
        st.write(f"- **Pass Rate:** {stats['pass_rate_pct']}%")
        st.write(f"- **Failure Rate:** {stats['failure_rate_pct']}%")
        st.write(f"- **Ambiguity/Review Rate:** {stats['review_rate_pct']}%")
        st.write(f"- **Average Preprocess + Inference:** {stats['avg_inference_ms']} ms")
        st.write(f"- **Average Total Pipeline Cycle:** {stats['avg_total_ms']} ms")


# ==============================================================================
# PAGE 5: SAFETY RULES & CONFIG
# ==============================================================================
elif menu == "Safety Rules & Config":
    st.markdown("""
    <div class="main-header">
        <h1>Safety Rules & Parameters Configuration</h1>
        <p>Deterministic industrial safety rule definitions and spatial thresholds</p>
    </div>
    """, unsafe_allow_html=True)

    eq_rules = cfg.get_equipment_rules("angle_grinder")

    st.subheader("Angle Grinder Safety Rules")
    st.markdown(f"**Applicable Standards:** {eq_rules.get('standard_reference', 'OSHA 1910.243 / ANSI B7.1')}")

    st.markdown("#### Configured Safety Rules")
    st.write("1. **Chassis Verification:** Angle grinder body must be detected as target equipment.")
    st.write("2. **Guard Protection (CRITICAL):** Abrasive wheel guard must be detected and spatially attached.")
    st.write("3. **Two-Hand Control (HIGH):** Auxiliary side handle must be detected and attached.")
    st.write("4. **Electrical Cord (HIGH):** Power cable and strain relief must be detected without damage.")
    st.write("5. **Control Switch (MEDIUM):** Operating dead-man trigger/switch must be detected.")
    st.write("6. **Damage Prevention (CRITICAL):** Any detected damage to guard or cable triggers immediate FAIL.")

    st.markdown("#### Detection Classes & Roles")
    cls_data = []
    for cid, cinfo in cfg.classes.items():
        cls_data.append({
            "Class ID": cid,
            "Class Name": cinfo["name"],
            "Display Name": cinfo["display_name"],
            "Category": cinfo["category"],
            "Description": cinfo["description"],
        })
    st.dataframe(pd.DataFrame(cls_data), use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE 6: MODEL INFORMATION
# ==============================================================================
elif menu == "Model Information":
    st.markdown("""
    <div class="main-header">
        <h1>Model Registry & Governance</h1>
        <p>Active model parameters, export pipelines, and Ultralytics licensing terms</p>
    </div>
    """, unsafe_allow_html=True)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.subheader("Active Model Details")
        st.write(f"**Model Name:** {detector.model_name}")
        st.write(f"**Model Version:** {detector.model_version}")
        st.write(f"**Framework:** Ultralytics YOLO")
        st.write(f"**Device Mode:** {cfg.device_setting}")
        st.write(f"**Custom Weights Loaded:** {'YES' if detector.is_custom_model else 'NO (Running in DEMO MODE)'}")

        if not detector.is_custom_model:
            st.warning("⚠️ **DEMO MODE ACTIVE**: Pretrained weights loaded for pipeline demonstration. Train custom model using `python scripts/train.py`.")

    with m_col2:
        st.subheader("Edge Deployment & ONNX Export")
        st.write("Export active PyTorch weights to open ONNX format for TensorRT / Edge deployment.")
        if st.button("EXPORT TO ONNX"):
            with st.spinner("Exporting model to ONNX..."):
                try:
                    onnx_path = detector.export_onnx()
                    st.success(f"ONNX model successfully exported: {onnx_path}")
                except Exception as e:
                    st.error(f"ONNX export failed: {e}")

    st.markdown("---")
    st.subheader("Commercial Licensing & Compliance Notice")
    st.markdown("""
    SafetyVision AI integrates the Ultralytics YOLO framework.
    - **Open Source / Evaluation:** Ultralytics is distributed under the GNU Affero General Public License v3.0 (AGPL-3.0).
    - **Commercial Distribution:** Companies embedding Ultralytics in closed-source products, commercial appliances, or SaaS without releasing their own source code must acquire an **Ultralytics Commercial License**.
    - For full details, review: `docs/LICENSE_AND_COMMERCIAL_USE.md`.
    """)
