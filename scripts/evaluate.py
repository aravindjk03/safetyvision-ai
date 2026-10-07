"""
SafetyVision AI — Model Evaluation & Safety Metrics Auditor
Calculates Precision, Recall, mAP50, mAP50-95, and per-class safety-critical breakdowns.
Generates audit reports in JSON and HTML.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ultralytics import YOLO
from app.config import get_config
from app.logger import get_logger


def parse_args():
    parser = argparse.ArgumentParser(description="SafetyVision AI — Model Evaluation")
    parser.add_argument("--weights", type=str, default="models/safetyvision_yolo26n.pt", help="Path to weights file to evaluate")
    parser.add_argument("--data", type=str, default="dataset/data.yaml", help="Path to data.yaml")
    parser.add_argument("--split", type=str, default="test", help="Dataset split to evaluate: val or test")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    return parser.parse_args()


def run_evaluation():
    args = parse_args()
    logger = get_logger()
    cfg = get_config(ROOT_DIR)

    weights_path = ROOT_DIR / args.weights
    data_yaml = ROOT_DIR / args.data

    # If custom weights do not exist, fall back to demo weights for pipeline verification
    if not weights_path.exists():
        print(f"[NOTICE] Custom weights {weights_path} not found. Using demo model {cfg.demo_weights_path}...")
        weights_path = cfg.demo_weights_path

    print("==================================================")
    print("SAFETYVISION AI — MODEL EVALUATION AUDIT")
    print(f"Target Weights: {weights_path}")
    print(f"Dataset YAML:   {data_yaml}")
    print(f"Split:          {args.split}")
    print("==================================================")

    model = YOLO(str(weights_path))

    # Run validation
    metrics = model.val(
        data=str(data_yaml),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        verbose=True,
    )

    box = metrics.box
    class_indices = metrics.box.ap_class_index if hasattr(metrics.box, "ap_class_index") else []

    # Compile structured metrics payload
    eval_results = {
        "timestamp": datetime.now().isoformat(),
        "model_path": str(weights_path),
        "split": args.split,
        "global_metrics": {
            "mAP50": round(float(box.map50), 4),
            "mAP50_95": round(float(box.map), 4),
            "mean_precision": round(float(box.mp), 4),
            "mean_recall": round(float(box.mr), 4),
        },
        "per_class_metrics": {},
        "safety_critical_audit": {},
        "operational_suitability_disclaimer": (
            "IMPORTANT NOTICE ON PRODUCTION READINESS: High mAP metrics alone do NOT certify production readiness. "
            "Suitability for industrial safety inspection requires extensive validation against actual plant conditions, "
            "including lens contamination, severe vibration, motion blur, varied lighting, reflective tooling surfaces, "
            "and out-of-distribution equipment variations."
        ),
    }

    names_dict = model.names if hasattr(model, "names") else {}

    # Per-class metrics
    safety_critical_classes = {"guard", "damaged_guard", "damaged_cable"}

    for idx, c_idx in enumerate(class_indices):
        c_name = names_dict.get(c_idx, f"class_{c_idx}")
        p = float(box.p[idx]) if idx < len(box.p) else 0.0
        r = float(box.r[idx]) if idx < len(box.r) else 0.0
        ap50 = float(box.ap50[idx]) if idx < len(box.ap50) else 0.0
        ap = float(box.ap[idx]) if idx < len(box.ap) else 0.0

        c_metric = {
            "class_id": int(c_idx),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "mAP50": round(ap50, 4),
            "mAP50_95": round(ap, 4),
        }
        eval_results["per_class_metrics"][c_name] = c_metric

        if c_name in safety_critical_classes:
            eval_results["safety_critical_audit"][c_name] = {
                "metric_summary": c_metric,
                "recall_assessment": "SATISFACTORY (>=0.90)" if r >= 0.90 else "UNSATISFACTORY (<0.90) - HIGH FALSE NEGATIVE RISK",
            }

    # Save JSON report
    json_path = cfg.reports_dir / "model_evaluation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    # Save HTML report
    html_path = cfg.reports_dir / "model_evaluation.html"
    generate_html_report(eval_results, html_path)

    print("\n==================================================")
    print("EVALUATION SUMMARY:")
    print(f"Overall mAP50:      {eval_results['global_metrics']['mAP50'] * 100:.1f}%")
    print(f"Overall mAP50-95:   {eval_results['global_metrics']['mAP50_95'] * 100:.1f}%")
    print(f"Mean Precision:    {eval_results['global_metrics']['mean_precision'] * 100:.1f}%")
    print(f"Mean Recall:       {eval_results['global_metrics']['mean_recall'] * 100:.1f}%")
    print("\nSafety-Critical Observations:")
    for sc_name, sc_info in eval_results["safety_critical_audit"].items():
        print(f"  - {sc_name}: Recall = {sc_info['metric_summary']['recall']*100:.1f}% -> {sc_info['recall_assessment']}")
    print(f"\nJSON Report saved: {json_path}")
    print(f"HTML Report saved: {html_path}")
    print("==================================================")


def generate_html_report(res: dict, out_path: Path):
    """Renders HTML evaluation report."""
    rows = ""
    for c_name, c_data in res["per_class_metrics"].items():
        rows += f"""
        <tr>
            <td><b>{c_name}</b></td>
            <td>{c_data['precision']*100:.1f}%</td>
            <td>{c_data['recall']*100:.1f}%</td>
            <td>{c_data['mAP50']*100:.1f}%</td>
            <td>{c_data['mAP50_95']*100:.1f}%</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SafetyVision AI — Model Evaluation Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #F8FAFC; color: #1E293B; }}
        .card {{ background: white; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 900px; margin: auto; }}
        .header {{ border-bottom: 2px solid #0D233A; padding-bottom: 12px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #E2E8F0; padding: 10px 14px; text-align: left; }}
        th {{ background: #0D233A; color: white; }}
        .banner {{ background: #FEF3C7; border-left: 4px solid #D97706; padding: 16px; margin: 20px 0; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1 style="margin: 0; color: #0D233A;">SAFETYVISION AI</h1>
            <p style="margin: 4px 0 0 0; color: #64748B;">COMPUTER VISION MODEL PERFORMANCE AUDIT</p>
        </div>
        <p><b>Model Evaluated:</b> {res['model_path']}</p>
        <p><b>Split:</b> {res['split']} &nbsp;|&nbsp; <b>Timestamp:</b> {res['timestamp']}</p>
        
        <div style="display: flex; gap: 15px; margin: 20px 0;">
            <div style="flex: 1; background: #F1F5F9; padding: 15px; border-radius: 6px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: #0D233A;">{res['global_metrics']['mAP50']*100:.1f}%</div>
                <div style="font-size: 12px; color: #64748B;">mAP@50</div>
            </div>
            <div style="flex: 1; background: #F1F5F9; padding: 15px; border-radius: 6px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: #0D233A;">{res['global_metrics']['mAP50_95']*100:.1f}%</div>
                <div style="font-size: 12px; color: #64748B;">mAP@50-95</div>
            </div>
            <div style="flex: 1; background: #F1F5F9; padding: 15px; border-radius: 6px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: #0D233A;">{res['global_metrics']['mean_precision']*100:.1f}%</div>
                <div style="font-size: 12px; color: #64748B;">Precision</div>
            </div>
            <div style="flex: 1; background: #F1F5F9; padding: 15px; border-radius: 6px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: #0D233A;">{res['global_metrics']['mean_recall']*100:.1f}%</div>
                <div style="font-size: 12px; color: #64748B;">Recall</div>
            </div>
        </div>

        <h3>Per-Class Performance Matrix</h3>
        <table>
            <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>mAP@50</th><th>mAP@50-95</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>

        <div class="banner">
            <b>CRITICAL PRODUCTION NOTICE:</b><br/>
            {res['operational_suitability_disclaimer']}
        </div>
    </div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    run_evaluation()
