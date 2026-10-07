"""
SafetyVision AI — Industrial Visual Safety Inspection Dashboard
Built with Streamlit. Professional, auditable, high-contrast industrial interface.
"""

from html import escape
from pathlib import Path
import sys
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
APP_VERSION = cfg.system_info.get("version", "0.1.0")

STATUS_STYLES = {
    "PASS": {"cls": "pass", "icon": "✅", "color": "#15803D"},
    "FAIL": {"cls": "fail", "icon": "⛔", "color": "#B91C1C"},
    "REVIEW": {"cls": "review", "icon": "⚠️", "color": "#C2410C"},
}


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
    .block-container { padding-top: 3.6rem; padding-bottom: 3rem; max-width: 1320px; }

    /* Page header */
    .main-header {
        background: linear-gradient(120deg, #0B1F33 0%, #12355B 60%, #1D4ED8 130%);
        padding: 20px 26px;
        border-radius: 14px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 6px 18px -8px rgba(13, 35, 58, 0.55);
    }
    .main-header .eyebrow {
        font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase;
        color: #7DD3FC; font-weight: 600; margin: 0 0 4px 0;
    }
    .main-header h1 {
        margin: 0; padding: 0; font-size: 26px; font-weight: 700;
        letter-spacing: 0.2px; color: white !important;
    }
    .main-header p.sub { margin: 6px 0 0 0; font-size: 13.5px; color: #CBD5E1; }

    /* Statutory safety disclaimer callout */
    .disclaimer-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #475569;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        font-size: 12.5px;
        color: #334155;
        margin-bottom: 18px;
    }

    /* Status banner */
    .status-banner {
        display: flex; align-items: center; gap: 16px;
        padding: 16px 22px; border-radius: 12px; margin: 6px 0 16px 0;
        border: 1px solid;
    }
    .status-banner .icon { font-size: 30px; line-height: 1; }
    .status-banner .label { font-size: 12px; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 600; opacity: 0.85; }
    .status-banner .value { font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
    .status-banner .detail { font-size: 13.5px; margin-top: 2px; }
    .status-pass { background: #F0FDF4; border-color: #86EFAC; color: #14532D; }
    .status-fail { background: #FEF2F2; border-color: #FCA5A5; color: #7F1D1D; }
    .status-review { background: #FFF7ED; border-color: #FDBA74; color: #7C2D12; }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 14px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .metric-value { font-size: 26px; font-weight: 750; color: #0B1F33; line-height: 1.15; }
    .metric-label { font-size: 11.5px; color: #64748B; text-transform: uppercase; letter-spacing: 0.7px; margin-top: 4px; }

    /* Status pill */
    .pill {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 12px; font-weight: 700; letter-spacing: 0.4px; color: white;
    }

    /* Sidebar */
    .sb-brand { text-align: left; margin: 0 0 12px 0; }
    .sb-brand .name { font-size: 19px; font-weight: 800; color: #0B1F33; letter-spacing: 0.4px; margin: 0; }
    .sb-brand .tag { font-size: 12px; color: #64748B; margin: 2px 0 0 0; }
    .sb-model {
        border-radius: 10px; padding: 12px 14px; font-size: 12.5px; line-height: 1.55;
        border: 1px solid;
    }
    .sb-model.custom { background: #F0FDF4; border-color: #BBF7D0; color: #14532D; }
    .sb-model.demo { background: #FFFBEB; border-color: #FDE68A; color: #78350F; }
    .sb-model .title { font-weight: 800; letter-spacing: 0.6px; font-size: 11.5px; text-transform: uppercase; margin-bottom: 4px; }
    .sb-footer { font-size: 11px; color: #94A3B8; margin-top: 18px; line-height: 1.6; }
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


# ==============================================================================
# UI HELPERS
# ==============================================================================
def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="main-header">
            <div class="eyebrow">{escape(eyebrow)}</div>
            <h1>{escape(title)}</h1>
            <p class="sub">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def notice(title: str, body: str) -> None:
    st.markdown(f'<div class="disclaimer-box"><b>{escape(title)}:</b> {escape(body)}</div>', unsafe_allow_html=True)


def metric_card(value: Any, label: str, color: Optional[str] = None) -> str:
    style = f' style="color: {color};"' if color else ""
    return f'<div class="metric-card"><div class="metric-value"{style}>{escape(str(value))}</div><div class="metric-label">{escape(label)}</div></div>'


def status_pill(status: str) -> str:
    color = STATUS_STYLES.get(status, {}).get("color", "#475569")
    return f'<span class="pill" style="background:{color};">{escape(status)}</span>'


def render_status_banner(res: Dict[str, Any]) -> None:
    status = res["overall_status"]
    style = STATUS_STYLES.get(status, STATUS_STYLES["REVIEW"])
    if status == "PASS":
        detail = "All configured visual requirements satisfied."
    elif status == "FAIL":
        detail = f"{res['highest_severity']} severity violation detected."
    else:
        detail = "Insufficient or ambiguous visual evidence — competent-person verification required."
    st.markdown(
        f"""
        <div class="status-banner status-{style['cls']}">
            <div class="icon">{style['icon']}</div>
            <div>
                <div class="label">Overall Result · {escape(res['inspection_id'])}</div>
                <div class="value">{escape(status)}</div>
                <div class="detail">{escape(detail)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pdf_download_button(report_path: str, label: str, key: str) -> None:
    rep_path = Path(report_path or "")
    if report_path and rep_path.is_file():
        st.download_button(
            label=label,
            data=rep_path.read_bytes(),
            file_name=rep_path.name,
            mime="application/pdf",
            width="stretch",
            key=key,
        )


def render_inspection_result(res: Dict[str, Any], key_prefix: str) -> None:
    """Renders a full inspection result: status, timings, evidence, findings and component checks."""
    render_status_banner(res)

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Equipment Confidence", f"{res['confidence'] * 100:.1f}%")
    t2.metric("Inference Latency", f"{res['timing']['inference_ms']:.0f} ms")
    t3.metric("Rule Evaluation", f"{res['timing']['rules_evaluation_ms']:.1f} ms")
    t4.metric(f"Total Cycle · {res['timing']['fps']} FPS", f"{res['timing']['total_time_ms']:.0f} ms")

    ev_col, findings_col = st.columns([3, 2], gap="large")
    with ev_col:
        ev_path = Path(res["evidence_path"])
        if ev_path.is_file():
            st.image(str(ev_path), caption=f"Annotated evidence · {ev_path.name}", width="stretch")
        else:
            st.info("Evidence image is not available.")

    with findings_col:
        st.markdown("##### Decision Breakdown")
        st.markdown(f"**Reason:** {res['reason']}")
        st.markdown(f"**Recommended action:** {res['recommended_action']}")

        if res["missing_components"]:
            st.error(f"**Missing mandatory components:** {', '.join(res['missing_components'])}")
        if res["damage_violations"]:
            st.error(f"**Structural damage violations:** {', '.join(res['damage_violations'])}")
        for w in res["warnings"]:
            st.warning(w)

        st.caption(
            f"Model: {res.get('model_name', detector.model_name)} v{res.get('model_version', detector.model_version)} · "
            f"Operator: {res.get('operator', '—')} · {res.get('timestamp', '')}"
        )
        pdf_download_button(res.get("report_path", ""), "⬇ Download PDF audit report", key=f"{key_prefix}_pdf_{res['inspection_id']}")

    tab_checks, tab_dets = st.tabs(["Component verification", "Raw detections"])
    with tab_checks:
        checks_data = [
            {
                "Component": cinfo.get("display_name", cname),
                "Mandatory": "Yes" if cinfo.get("is_mandatory") else "No",
                "Status": cinfo.get("status"),
                "Confidence": cinfo.get("confidence", 0.0) or 0.0,
                "Severity": cinfo.get("severity"),
                "Attached": "Yes" if cinfo.get("is_associated") else "No",
                "Audit Message": cinfo.get("message"),
            }
            for cname, cinfo in res["checks"].items()
        ]
        if checks_data:
            st.dataframe(
                pd.DataFrame(checks_data),
                width="stretch",
                hide_index=True,
                column_config={
                    "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="percent"),
                },
            )
        else:
            st.info("No component checks were evaluated (no equipment detected).")
    with tab_dets:
        if res["detections"]:
            df_det = pd.DataFrame(res["detections"])[["class_name", "confidence", "bbox", "area"]]
            st.dataframe(
                df_det,
                width="stretch",
                hide_index=True,
                column_config={
                    "class_name": "Class",
                    "confidence": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="percent"),
                    "bbox": "BBox [x1, y1, x2, y2]",
                    "area": st.column_config.NumberColumn("Area (px²)", format="%.0f"),
                },
            )
        else:
            st.info("The model returned no detections above the confidence cutoff.")


def run_inspection(image: Image.Image, operator: str, comments: str, conf: Optional[float], result_key: str, source_id: str) -> None:
    with st.spinner("Analyzing physical observations & evaluating safety rules..."):
        try:
            result = engine.inspect(
                image_input=image,
                operator=operator,
                comments=comments,
                conf_threshold=conf,
            )
            st.session_state[result_key] = {"source": source_id, "result": result}
        except Exception as e:
            st.error(f"Inspection failed: {e}")
            logger.error(f"Inspection exception: {e}", exc_info=True)


def current_result(result_key: str, source_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Returns the stored result only if it belongs to the image currently selected."""
    stored = st.session_state.get(result_key)
    if stored and source_id is not None and stored["source"] == source_id:
        return stored["result"]
    return None


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown(
        """
        <div class="sb-brand">
            <p class="name">🛡️ SafetyVision AI</p>
            <p class="tag">Industrial Visual Safety Inspection</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    menu = st.radio(
        "Navigation",
        [
            "Single Inspection",
            "Live Camera",
            "Inspection History",
            "Reports & Analytics",
            "Safety Rules & Config",
            "Model Information",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if detector.is_custom_model:
        st.markdown(
            f"""
            <div class="sb-model custom">
                <div class="title">● Custom safety model</div>
                <b>{escape(detector.model_name)}</b><br/>
                Version {escape(detector.model_version)} · device {escape(cfg.device_setting)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="sb-model demo">
                <div class="title">▲ Demo mode</div>
                Not trained for industrial safety inspection.<br/>
                Base weights: <b>{escape(detector.model_name)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="sb-footer">
            SafetyVision AI v{escape(APP_VERSION)}<br/>
            OSHA 1910.243 / ANSI B7.1 grounded<br/>
            Industrial proof-of-concept
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# PAGE 1: SINGLE INSPECTION
# ==============================================================================
if menu == "Single Inspection":
    page_header(
        "Inspection Station",
        "Industrial Visual Safety Inspection",
        "Automated component verification with a deterministic, auditable PASS / FAIL / REVIEW decision.",
    )
    notice(
        "Statutory safety notice",
        "Automated visual inspection verifies configured visual conditions only. It does not certify physical or "
        "operational safety and does NOT replace competent-person inspection, manufacturer guidelines, statutory "
        "risk assessments, or formal lockout/tagout procedures.",
    )

    col_input, col_meta = st.columns([3, 2], gap="large")

    with col_meta:
        with st.container(border=True):
            st.markdown("##### Inspection Parameters")
            st.selectbox("Target Equipment", ["Angle Grinder"], index=0)
            operator_name = st.text_input("Operator / Inspector ID", value="Tech-104")
            inspection_notes = st.text_input("Audit Notes / Station", value="Workstation Bench #3")
            conf_override = st.slider(
                "Detection Confidence Cutoff", min_value=0.10, max_value=0.95, value=cfg.low_cutoff_threshold, step=0.05,
                help="Detections below this confidence are ignored before safety rules are evaluated.",
            )

    image_to_inspect = None
    source_id = None
    with col_input:
        with st.container(border=True):
            st.markdown("##### Source Image")
            source_mode = st.segmented_control(
                "Input Source", ["Upload Image", "Sample Test Cases"], default="Sample Test Cases",
                label_visibility="collapsed",
            ) or "Sample Test Cases"

            if source_mode == "Upload Image":
                uploaded_file = st.file_uploader(
                    "Choose equipment photograph (JPEG, PNG, WebP, BMP)",
                    type=["jpg", "jpeg", "png", "webp", "bmp"],
                )
                if uploaded_file is not None:
                    try:
                        image_to_inspect = Image.open(uploaded_file)
                        source_id = f"upload:{uploaded_file.file_id}"
                    except Exception as e:
                        st.error(f"Error loading uploaded image: {e}")
            else:
                sample_dir = cfg.root_dir / "dataset" / "images" / "test"
                sample_files = sorted(
                    list(sample_dir.glob("*.jpg")) + list(sample_dir.glob("*.png")),
                    key=lambda p: (not p.name.startswith("acceptance_"), p.name),
                )
                if sample_files:
                    sample_choice = st.selectbox(
                        "Select acceptance / test case",
                        sample_files,
                        format_func=lambda p: p.stem.replace("_", " "),
                    )
                    if sample_choice:
                        image_to_inspect = Image.open(sample_choice)
                        source_id = f"sample:{sample_choice.name}"
                else:
                    st.info("No sample test images found in dataset/images/test. Please upload an image.")

            if image_to_inspect is not None:
                st.image(image_to_inspect, caption="Input frame preview", width="stretch")

    with col_meta:
        run_btn = st.button(
            "▶ Run Inspection", type="primary", width="stretch", disabled=image_to_inspect is None,
        )
        st.caption("Runs YOLO detection, spatial association and the safety rule engine, then stores evidence, a PDF report and a database record.")

    if run_btn and image_to_inspect is not None:
        run_inspection(image_to_inspect, operator_name, inspection_notes, conf_override, "single_result", source_id)

    res = current_result("single_result", source_id)
    if res:
        st.divider()
        st.subheader("Inspection Result")
        render_inspection_result(res, key_prefix="single")


# ==============================================================================
# PAGE 2: LIVE CAMERA
# ==============================================================================
elif menu == "Live Camera":
    page_header(
        "Inspection Station",
        "Live Camera Inspection",
        "Capture a frame from the station camera and run a snapshot safety audit.",
    )
    notice(
        "Camera guideline",
        "Frame equipment centered under uniform industrial lighting. Avoid severe backlight, reflections, and partial "
        "occlusion before triggering the inspection snapshot.",
    )

    cam_col, ctrl_col = st.columns([3, 2], gap="large")

    with ctrl_col:
        with st.container(border=True):
            st.markdown("##### Station Controls")
            operator_cam = st.text_input("Operator ID", value="Line-Operator-02")
            comments_cam = st.text_input("Station Location", value="Assembly Jig A")
            conf_cam = st.slider("Detection Confidence Cutoff", 0.10, 0.95, cfg.low_cutoff_threshold, 0.05, key="cam_conf")

    cam_source = None
    with cam_col:
        with st.container(border=True):
            st.markdown("##### Camera Feed")
            cam_image = st.camera_input("Capture inspection frame", label_visibility="collapsed")
            if cam_image is None:
                st.caption("Allow camera access in your browser, point it at the equipment and capture a frame when stationary.")

    with ctrl_col:
        audit_btn = st.button("▶ Audit Captured Frame", type="primary", width="stretch", disabled=cam_image is None)

    if cam_image is not None:
        cam_source = f"camera:{cam_image.file_id}"
        if audit_btn:
            run_inspection(Image.open(cam_image), operator_cam, comments_cam, conf_cam, "camera_result", cam_source)

    res = current_result("camera_result", cam_source)
    if res:
        st.divider()
        st.subheader("Inspection Result")
        render_inspection_result(res, key_prefix="camera")


# ==============================================================================
# PAGE 3: INSPECTION HISTORY
# ==============================================================================
elif menu == "Inspection History":
    page_header("Audit Trail", "Inspection History", "Immutable audit trail of every inspection stored in the SQLite database.")

    filter_c1, filter_c2, filter_c3 = st.columns(3)
    with filter_c1:
        f_status = st.selectbox("Status", ["ALL", "PASS", "FAIL", "REVIEW"], index=0)
    with filter_c2:
        f_eq = st.selectbox("Equipment Type", ["ALL"] + db.get_equipment_types(), index=0)
    with filter_c3:
        f_search = st.text_input("Search Inspection ID", "", placeholder="e.g. INS-2026")

    records = db.get_history(limit=200, filter_status=f_status, filter_equipment=f_eq, search_id=f_search.strip())

    if not records:
        st.info("No inspection records match the current filters.")
    else:
        df_hist = pd.DataFrame(records)
        display_cols = ["inspection_id", "timestamp", "equipment_type", "overall_status", "highest_severity", "confidence", "operator", "inference_time_ms", "total_time_ms"]
        available_cols = [c for c in display_cols if c in df_hist.columns]
        st.caption(f"Showing {len(records)} most recent record(s).")
        st.dataframe(
            df_hist[available_cols],
            width="stretch",
            hide_index=True,
            column_config={
                "inspection_id": "Inspection ID",
                "timestamp": "Timestamp",
                "equipment_type": "Equipment",
                "overall_status": "Status",
                "highest_severity": "Severity",
                "confidence": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="percent"),
                "operator": "Operator",
                "inference_time_ms": st.column_config.NumberColumn("Inference (ms)", format="%.1f"),
                "total_time_ms": st.column_config.NumberColumn("Total (ms)", format="%.1f"),
            },
        )

        st.subheader("Record Detail")
        selected_id = st.selectbox("Select inspection to view", [r["inspection_id"] for r in records])
        full_rec = db.get_inspection(selected_id) if selected_id else None
        if full_rec:
            det_c1, det_c2 = st.columns([3, 2], gap="large")
            with det_c1:
                ev_file = Path(full_rec.get("evidence_path") or "")
                if full_rec.get("evidence_path") and ev_file.is_file():
                    st.image(str(ev_file), caption=f"Evidence · {selected_id}", width="stretch")
                else:
                    st.info("Evidence image file is not available on this host.")
            with det_c2:
                with st.container(border=True):
                    st.markdown(f"Status: {status_pill(full_rec['overall_status'])}", unsafe_allow_html=True)
                    conf_val = full_rec.get("confidence")
                    st.markdown(f"**Highest severity:** {full_rec.get('highest_severity', '—')}")
                    st.markdown(f"**Confidence:** {conf_val * 100:.1f}%" if conf_val is not None else "**Confidence:** —")
                    st.markdown(f"**Timestamp:** {full_rec.get('timestamp', '—')}")
                    st.markdown(f"**Operator:** {full_rec.get('operator', '—')}")
                    st.markdown(f"**Model version:** {full_rec.get('model_version', '—')}")
                    st.markdown(f"**Reason:** {full_rec.get('reason', '')}")
                    st.markdown(f"**Action:** {full_rec.get('recommended_action', '')}")
                pdf_download_button(full_rec.get("report_path", ""), "⬇ Download PDF report", key=f"hist_pdf_{selected_id}")


# ==============================================================================
# PAGE 4: REPORTS & ANALYTICS
# ==============================================================================
elif menu == "Reports & Analytics":
    page_header("Quality & Safety", "Analytics Dashboard", "Operational safety metrics, compliance ratios, and pipeline cycle times.")

    stats = db.get_statistics()

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.markdown(metric_card(stats["total_inspections"], "Total Inspected"), unsafe_allow_html=True)
    m2.markdown(metric_card(stats["pass_count"], "Pass", STATUS_STYLES["PASS"]["color"]), unsafe_allow_html=True)
    m3.markdown(metric_card(stats["fail_count"], "Fail", STATUS_STYLES["FAIL"]["color"]), unsafe_allow_html=True)
    m4.markdown(metric_card(stats["review_count"], "Review", STATUS_STYLES["REVIEW"]["color"]), unsafe_allow_html=True)
    m5.markdown(metric_card(f"{stats['failure_rate_pct']}%", "Failure Rate"), unsafe_allow_html=True)
    m6.markdown(metric_card(f"{stats['avg_inference_ms']} ms", "Avg Inference"), unsafe_allow_html=True)

    st.write("")
    if stats["total_inspections"] == 0:
        st.info("No inspections recorded yet. Run an inspection to populate analytics.")
    else:
        c1, c2 = st.columns([3, 2], gap="large")
        with c1:
            with st.container(border=True):
                st.markdown("##### Inspections per Day by Result")
                history = pd.DataFrame(db.get_history(limit=1000))
                history["date"] = pd.to_datetime(history["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
                daily = (
                    history.dropna(subset=["date"])
                    .pivot_table(index="date", columns="overall_status", values="inspection_id", aggfunc="count", fill_value=0)
                    .reindex(columns=["PASS", "FAIL", "REVIEW"], fill_value=0)
                )
                st.bar_chart(
                    daily,
                    color=[STATUS_STYLES[s]["color"] for s in daily.columns],
                    stack=True,
                    height=300,
                )
        with c2:
            with st.container(border=True):
                st.markdown("##### Quality & Performance Rates")
                st.progress(stats["pass_rate_pct"] / 100.0, text=f"Pass rate · {stats['pass_rate_pct']}%")
                st.progress(stats["failure_rate_pct"] / 100.0, text=f"Failure rate · {stats['failure_rate_pct']}%")
                st.progress(stats["review_rate_pct"] / 100.0, text=f"Review / ambiguity rate · {stats['review_rate_pct']}%")
                st.markdown(f"**Average inference:** {stats['avg_inference_ms']} ms")
                st.markdown(f"**Average total pipeline cycle:** {stats['avg_total_ms']} ms")


# ==============================================================================
# PAGE 5: SAFETY RULES & CONFIG
# ==============================================================================
elif menu == "Safety Rules & Config":
    page_header("Configuration", "Safety Rules & Parameters", "Deterministic industrial safety rule definitions and spatial thresholds.")

    eq_rules = cfg.get_equipment_rules("angle_grinder")

    st.markdown(f"**Equipment:** {eq_rules.get('display_name', 'Angle Grinder')} · **Applicable standards:** {eq_rules.get('standard_reference', 'OSHA 1910.243 / ANSI B7.1')}")

    rules_rows = [
        ("Chassis Verification", "—", "Angle grinder body must be detected as the target equipment."),
        ("Guard Protection", "CRITICAL", "Abrasive wheel guard must be detected and spatially attached."),
        ("Two-Hand Control", "HIGH", "Auxiliary side handle must be detected and attached."),
        ("Electrical Cord", "HIGH", "Power cable and strain relief must be detected without damage."),
        ("Control Switch", "MEDIUM", "Operating dead-man trigger / switch must be detected."),
        ("Damage Prevention", "CRITICAL", "Any detected damage to guard or cable triggers an immediate FAIL."),
    ]
    st.markdown("##### Configured Safety Rules")
    st.dataframe(
        pd.DataFrame(rules_rows, columns=["Rule", "Severity", "Requirement"]),
        width="stretch",
        hide_index=True,
    )

    conf_rules = eq_rules.get("confidence", {})
    spatial_rules = eq_rules.get("spatial", {})
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(metric_card(conf_rules.get("high_threshold", cfg.high_confidence_threshold), "High confidence ≥"), unsafe_allow_html=True)
    k2.markdown(metric_card(conf_rules.get("medium_threshold", cfg.medium_confidence_threshold), "Review band ≥"), unsafe_allow_html=True)
    k3.markdown(metric_card(conf_rules.get("low_cutoff", cfg.low_cutoff_threshold), "Noise cutoff"), unsafe_allow_html=True)
    k4.markdown(metric_card(spatial_rules.get("max_center_distance_factor", "—"), "Max center distance ×"), unsafe_allow_html=True)

    st.write("")
    st.markdown("##### Detection Classes & Roles")
    cls_data = [
        {
            "Class ID": cid,
            "Class Name": cinfo["name"],
            "Display Name": cinfo["display_name"],
            "Category": cinfo["category"],
            "Description": cinfo["description"],
        }
        for cid, cinfo in cfg.classes.items()
    ]
    st.dataframe(pd.DataFrame(cls_data), width="stretch", hide_index=True)


# ==============================================================================
# PAGE 6: MODEL INFORMATION
# ==============================================================================
elif menu == "Model Information":
    page_header("Model Governance", "Model Registry", "Active model parameters, evaluation metrics, export pipeline and licensing terms.")

    registry = cfg._load_yaml(cfg.root_dir / "models" / "model_registry.yaml")
    active_entry = next(
        (
            m for m in registry.get("models", []) or []
            if m.get("model_name") == detector.model_name and str(m.get("model_version")) == detector.model_version
        ),
        None,
    )

    m_col1, m_col2 = st.columns(2, gap="large")
    with m_col1:
        with st.container(border=True):
            st.markdown("##### Active Model")
            st.markdown(f"**Model name:** {detector.model_name}")
            st.markdown(f"**Model version:** {detector.model_version}")
            st.markdown(f"**Framework:** Ultralytics YOLO")
            st.markdown(f"**Device mode:** {cfg.device_setting}")
            st.markdown(f"**Custom weights loaded:** {'Yes' if detector.is_custom_model else 'No — running in DEMO MODE'}")
            if active_entry:
                st.markdown(f"**Trained:** {active_entry.get('training_date', '—')} on `{active_entry.get('dataset_version', '—')}`")
            if not detector.is_custom_model:
                st.warning("**Demo mode active:** pretrained weights loaded for pipeline demonstration. Train a custom model with `python scripts/train.py`.")

    with m_col2:
        with st.container(border=True):
            st.markdown("##### Edge Deployment & ONNX Export")
            st.write("Export the active PyTorch weights to the open ONNX format for ONNX Runtime / TensorRT edge deployment.")
            if st.button("Export to ONNX", width="stretch"):
                with st.spinner("Exporting model to ONNX..."):
                    try:
                        onnx_path = detector.export_onnx()
                        st.success(f"ONNX model exported: {onnx_path}")
                    except Exception as e:
                        st.error(f"ONNX export failed: {e}")

    if active_entry and active_entry.get("metrics"):
        metrics = active_entry["metrics"]
        st.markdown("##### Evaluation Metrics (from model registry)")
        e1, e2, e3, e4 = st.columns(4)
        fmt = lambda v: f"{float(v) * 100:.1f}%" if isinstance(v, (int, float)) else str(v)
        e1.markdown(metric_card(fmt(metrics.get("mAP50", "—")), "mAP50"), unsafe_allow_html=True)
        e2.markdown(metric_card(fmt(metrics.get("mAP50_95", "—")), "mAP50-95"), unsafe_allow_html=True)
        e3.markdown(metric_card(fmt(metrics.get("precision", "—")), "Precision"), unsafe_allow_html=True)
        e4.markdown(metric_card(fmt(metrics.get("mean_recall", "—")), "Recall"), unsafe_allow_html=True)
        if active_entry.get("notes"):
            st.caption(active_entry["notes"])

    st.write("")
    with st.expander("Commercial licensing & compliance notice"):
        st.markdown("""
        SafetyVision AI integrates the Ultralytics YOLO framework.
        - **Open Source / Evaluation:** Ultralytics is distributed under the GNU Affero General Public License v3.0 (AGPL-3.0).
        - **Commercial Distribution:** Companies embedding Ultralytics in closed-source products, commercial appliances, or SaaS without releasing their own source code must acquire an **Ultralytics Commercial License**.
        - For full details, review: `docs/LICENSE_AND_COMMERCIAL_USE.md`.
        """)
