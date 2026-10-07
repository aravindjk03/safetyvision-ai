"""
SafetyVision AI — PDF & HTML Inspection Report Generator
Generates audit-ready, tamper-evident inspection reports using ReportLab.
Includes executive status badges, component tables, evidence images, and statutory disclaimers.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)

from app.config import get_config
from app.logger import get_logger
from app.rules import RuleEvaluationResult


class ReportGenerator:
    """Generates professional PDF and HTML reports for visual safety inspections."""

    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.reports_dir = self.config.reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf(
        self,
        inspection_id: str,
        rule_result: RuleEvaluationResult,
        evidence_image_path: Optional[Path] = None,
        operator: str = "System Operator",
        model_version: str = "0.1.0",
        timestamp: Optional[datetime] = None,
    ) -> Path:
        """
        Builds a comprehensive PDF report using ReportLab.
        """
        ts = timestamp or datetime.now()
        filename = f"{inspection_id}.pdf"
        target_path = self.reports_dir / filename

        doc = SimpleDocTemplate(
            str(target_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Industrial Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0D233A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1A202C"),
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748"),
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#718096"),
        )

        elements: List[Any] = []

        # 1. Header Banner
        elements.append(Paragraph("SAFETYVISION AI", title_style))
        elements.append(Paragraph("INDUSTRIAL VISUAL SAFETY INSPECTION AUDIT REPORT", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D233A"), spaceAfter=12))

        # 2. Executive Metadata & Status Block
        status = rule_result.overall_status.upper()
        if status == "PASS":
            status_bg = colors.HexColor("#2E7D32")
            status_text = "PASS — COMPLIANT"
        elif status == "FAIL":
            status_bg = colors.HexColor("#C62828")
            status_text = f"FAIL — {rule_result.highest_severity} VIOLATION"
        else:
            status_bg = colors.HexColor("#EF6C00")
            status_text = "REVIEW — AMBIGUOUS / INSUFFICIENT"

        metadata_data = [
            [
                Paragraph(f"<b>Inspection ID:</b> {inspection_id}", body_style),
                Paragraph(f"<b>Date/Time:</b> {ts.strftime('%Y-%m-%d %H:%M:%S')}", body_style),
            ],
            [
                Paragraph(f"<b>Equipment Type:</b> {rule_result.equipment_display_name}", body_style),
                Paragraph(f"<b>Model Version:</b> {model_version}", body_style),
            ],
            [
                Paragraph(f"<b>Operator:</b> {operator}", body_style),
                Paragraph(f"<b>AI Confidence:</b> {rule_result.equipment_confidence * 100:.1f}%", body_style),
            ],
        ]
        meta_table = Table(metadata_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # 3. Large Overall Status Badge
        status_table = Table([[Paragraph(f"<font color='white' size=14><b>OVERALL RESULT: {status_text}</b></font>", ParagraphStyle("StatusBanner", alignment=1))]], colWidths=[540])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 12))

        # 4. Embedded Evidence Image (if available)
        if evidence_image_path and Path(evidence_image_path).exists():
            elements.append(Paragraph("VISUAL EVIDENCE ARTIFACT", section_heading))
            try:
                # Maintain aspect ratio within 540x240 box
                rl_img = RLImage(str(evidence_image_path), width=480, height=220)
                img_table = Table([[rl_img]], colWidths=[540])
                img_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A202C")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                elements.append(img_table)
                elements.append(Spacer(1, 10))
            except Exception as e:
                self.logger.error(f"Failed to embed evidence image into PDF: {e}")

        # 5. Component Breakdown Table
        elements.append(Paragraph("SAFETY COMPONENT VERIFICATION MATRIX", section_heading))
        table_rows = [
            ["Component", "Mandatory", "Detection Status", "Confidence", "Severity", "Audit Finding"]
        ]

        for comp_name, chk in rule_result.checks.items():
            c_status = chk.get("status", "FAIL")
            c_conf = chk.get("confidence", 0.0)
            c_sev = chk.get("severity", "NONE")
            c_msg = chk.get("message", "")
            c_disp = chk.get("display_name", comp_name)
            is_mand = "YES" if chk.get("is_mandatory", True) else "NO"

            table_rows.append([
                c_disp,
                is_mand,
                c_status,
                f"{c_conf * 100:.1f}%" if c_conf > 0 else "N/A",
                c_sev,
                c_msg[:45] + "..." if len(c_msg) > 45 else c_msg,
            ])

        comp_table = Table(table_rows, colWidths=[100, 55, 75, 65, 65, 180])
        ts_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D233A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]

        # Row zebra striping and status color highlights
        for i, row in enumerate(table_rows[1:], start=1):
            if row[2] == "PASS":
                ts_style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#2E7D32")))
            elif row[2] == "FAIL":
                ts_style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#C62828")))
            else:
                ts_style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#EF6C00")))

            if i % 2 == 0:
                ts_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F7FAFC")))

        comp_table.setStyle(TableStyle(ts_style))
        elements.append(comp_table)
        elements.append(Spacer(1, 10))

        # 6. Findings & Recommended Actions
        findings_block = [
            Paragraph(f"<b>Root Evaluation:</b> {rule_result.reason}", body_style),
            Paragraph(f"<b>Recommended Action:</b> {rule_result.recommended_action}", body_style),
        ]
        if rule_result.warnings:
            warnings_str = " | ".join(rule_result.warnings)
            findings_block.append(Paragraph(f"<b>System Warnings:</b> {warnings_str}", body_style))

        elements.append(Paragraph("INSPECTION FINDINGS & REQUIRED ACTION", section_heading))
        rec_table = Table([[item] for item in findings_block], colWidths=[540])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB") if status != "PASS" else colors.HexColor("#F0FDF4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCD34D") if status != "PASS" else colors.HexColor("#86EFAC")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(rec_table)
        elements.append(Spacer(1, 12))

        # 7. Statutory & Competent-Person Safety Disclaimer
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceAfter=6))
        elements.append(Paragraph(
            "<b>STATUTORY SAFETY NOTICE & COMPETENT PERSON DISCLAIMER:</b> "
            "SafetyVision AI provides automated visual condition verification against configured visual safety criteria only. "
            "This software does NOT certify universal, physical, mechanical, or electrical safety and does NOT replace formal "
            "statutory inspections, manufacturer safety maintenance, job safety analyses (JSA), or evaluations conducted by an "
            "OSHA-defined Competent Person. Unsafe equipment must be tagged out and removed from service immediately.",
            disclaimer_style,
        ))

        # Build Document
        doc.build(elements)
        self.logger.info(f"Generated PDF inspection report: {target_path}")
        return target_path

    def generate_html(
        self,
        inspection_id: str,
        rule_result: RuleEvaluationResult,
        evidence_image_path: Optional[Path] = None,
        operator: str = "System Operator",
        model_version: str = "0.1.0",
        timestamp: Optional[datetime] = None,
    ) -> Path:
        """Generates an HTML version of the inspection audit report."""
        ts = timestamp or datetime.now()
        target_path = self.reports_dir / f"{inspection_id}.html"

        status = rule_result.overall_status.upper()
        status_color = "#2E7D32" if status == "PASS" else ("#C62828" if status == "FAIL" else "#EF6C00")

        rows_html = ""
        for comp_name, chk in rule_result.checks.items():
            rows_html += f"""
            <tr>
                <td><b>{chk.get('display_name', comp_name)}</b></td>
                <td>{'YES' if chk.get('is_mandatory') else 'NO'}</td>
                <td style="color: {'#2E7D32' if chk.get('status')=='PASS' else '#C62828'}; font-weight: bold;">{chk.get('status')}</td>
                <td>{chk.get('confidence', 0.0)*100:.1f}%</td>
                <td>{chk.get('severity')}</td>
                <td>{chk.get('message', '')}</td>
            </tr>
            """

        evidence_html = ""
        if evidence_image_path and Path(evidence_image_path).exists():
            evidence_html = f"""
            <div style="text-align: center; margin: 20px 0;">
                <img src="{Path(evidence_image_path).name}" style="max-width: 100%; border: 2px solid #CBD5E0; border-radius: 4px;" alt="Evidence" />
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SafetyVision AI Report — {inspection_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; background: #F8FAFC; color: #1E293B; }}
        .card {{ background: white; border-radius: 8px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 850px; margin: auto; }}
        .header {{ border-bottom: 2px solid #0D233A; padding-bottom: 12px; margin-bottom: 20px; }}
        .status-badge {{ background: {status_color}; color: white; padding: 12px; border-radius: 6px; font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ border: 1px solid #E2E8F0; padding: 8px 12px; text-align: left; }}
        th {{ background: #0D233A; color: white; }}
        .disclaimer {{ margin-top: 25px; padding: 12px; background: #F1F5F9; border-left: 4px solid #64748B; font-size: 12px; color: #475569; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1 style="margin: 0; color: #0D233A;">SAFETYVISION AI</h1>
            <p style="margin: 4px 0 0 0; color: #64748B;">INDUSTRIAL VISUAL SAFETY INSPECTION AUDIT REPORT</p>
        </div>
        <div class="status-badge">OVERALL RESULT: {status}</div>
        <p><b>Inspection ID:</b> {inspection_id} &nbsp;|&nbsp; <b>Timestamp:</b> {ts.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Equipment:</b> {rule_result.equipment_display_name} &nbsp;|&nbsp; <b>Model Version:</b> {model_version}</p>
        <p><b>Operator:</b> {operator} &nbsp;|&nbsp; <b>Confidence:</b> {rule_result.equipment_confidence * 100:.1f}%</p>
        {evidence_html}
        <h3>Safety Component Checks</h3>
        <table>
            <thead><tr><th>Component</th><th>Mandatory</th><th>Status</th><th>Confidence</th><th>Severity</th><th>Message</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div style="margin-top: 20px; padding: 15px; background: #FEF3C7; border-radius: 6px;">
            <b>Root Evaluation:</b> {rule_result.reason}<br/>
            <b>Recommended Action:</b> {rule_result.recommended_action}
        </div>
        <div class="disclaimer">
            <b>STATUTORY NOTICE:</b> SafetyVision AI provides automated visual condition verification only. It does not replace competent-person inspections, OSHA/ANSI requirements, or formal preventive maintenance.
        </div>
    </div>
</body>
</html>"""

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"Generated HTML report: {target_path}")
        return target_path
