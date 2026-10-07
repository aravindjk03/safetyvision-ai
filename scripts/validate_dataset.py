"""
SafetyVision AI — Dataset Validation Script
Audits dataset structure, annotation integrity, bounding-box coordinate validity,
class distributions, and train/val/test integrity before training.
"""

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Set, Tuple

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import cv2
from app.config import get_config
from app.logger import get_logger


def compute_file_hash(path: Path) -> str:
    """Calculates MD5 hash of a file to detect duplicates."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_dataset(dataset_dir: Path, valid_class_ids: Set[int]) -> Dict[str, Any]:
    """Runs rigorous industrial validation on YOLO dataset structure."""
    report: Dict[str, Any] = {
        "dataset_root": str(dataset_dir),
        "splits": {},
        "global_issues": [],
        "class_distribution_total": {cid: 0 for cid in valid_class_ids},
        "duplicate_images_found": [],
        "status": "VALID",
    }

    seen_hashes: Dict[str, Path] = {}
    total_images = 0
    total_annotations = 0

    splits = ["train", "val", "test"]

    for split in splits:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        split_report = {
            "image_count": 0,
            "label_count": 0,
            "missing_labels": [],
            "missing_images": [],
            "empty_labels": [],
            "invalid_labels": [],
            "class_distribution": {cid: 0 for cid in valid_class_ids},
            "unreadable_images": [],
        }

        if not img_dir.exists():
            report["global_issues"].append(f"Missing images directory for split '{split}' at {img_dir}")
            report["splits"][split] = split_report
            continue

        images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpeg"))
        labels = list(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []

        split_report["image_count"] = len(images)
        split_report["label_count"] = len(labels)
        total_images += len(images)

        image_basenames = {img.stem: img for img in images}
        label_basenames = {lbl.stem: lbl for lbl in labels}

        # Check for missing label files
        for stem, img_path in image_basenames.items():
            if stem not in label_basenames:
                split_report["missing_labels"].append(str(img_path.name))
            else:
                # Check for duplicate image content
                h = compute_file_hash(img_path)
                if h in seen_hashes:
                    report["duplicate_images_found"].append({
                        "file1": str(img_path),
                        "file2": str(seen_hashes[h]),
                    })
                else:
                    seen_hashes[h] = img_path

                # Validate image reading and dimensions
                im = cv2.imread(str(img_path))
                if im is None or im.size == 0:
                    split_report["unreadable_images"].append(str(img_path.name))

        # Check for orphan labels without images
        for stem, lbl_path in label_basenames.items():
            if stem not in image_basenames:
                split_report["missing_images"].append(str(lbl_path.name))

        # Validate label contents
        for lbl_path in labels:
            try:
                with open(lbl_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]

                if not lines:
                    split_report["empty_labels"].append(str(lbl_path.name))
                    continue

                for line_idx, line in enumerate(lines):
                    parts = line.split()
                    if len(parts) != 5:
                        split_report["invalid_labels"].append({
                            "file": str(lbl_path.name),
                            "line": line_idx + 1,
                            "reason": f"Expected 5 values, got {len(parts)}",
                        })
                        continue

                    try:
                        cid = int(parts[0])
                        cx, cy, w, h = [float(p) for p in parts[1:]]
                    except ValueError:
                        split_report["invalid_labels"].append({
                            "file": str(lbl_path.name),
                            "line": line_idx + 1,
                            "reason": "Failed to parse numeric coordinates",
                        })
                        continue

                    if cid not in valid_class_ids:
                        split_report["invalid_labels"].append({
                            "file": str(lbl_path.name),
                            "line": line_idx + 1,
                            "reason": f"Invalid class ID: {cid}. Valid IDs: {valid_class_ids}",
                        })
                        continue

                    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                        split_report["invalid_labels"].append({
                            "file": str(lbl_path.name),
                            "line": line_idx + 1,
                            "reason": f"Coordinates out of bounds: cx={cx}, cy={cy}, w={w}, h={h}",
                        })
                        continue

                    split_report["class_distribution"][cid] += 1
                    report["class_distribution_total"][cid] += 1
                    total_annotations += 1

            except Exception as e:
                split_report["invalid_labels"].append({
                    "file": str(lbl_path.name),
                    "reason": f"Exception reading label: {str(e)}",
                })

        report["splits"][split] = split_report

    # Evaluate final validation status
    has_errors = False
    for s_rep in report["splits"].values():
        if s_rep["missing_labels"] or s_rep["invalid_labels"] or s_rep["unreadable_images"]:
            has_errors = True
            break

    if report["global_issues"] or has_errors:
        report["status"] = "ERRORS_DETECTED"
    elif report["duplicate_images_found"]:
        report["status"] = "WARNINGS_DETECTED"
    else:
        report["status"] = "PASSED"

    report["total_images"] = total_images
    report["total_annotations"] = total_annotations

    return report


if __name__ == "__main__":
    cfg = get_config()
    valid_ids = set(cfg.classes.keys())
    ds_dir = cfg.root_dir / "dataset"

    print("==================================================")
    print("SAFETYVISION AI — DATASET VALIDATION AUDIT")
    print(f"Target: {ds_dir}")
    print("==================================================")

    res = validate_dataset(ds_dir, valid_ids)

    out_file = cfg.reports_dir / "dataset_validation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    print(f"Validation Status: {res['status']}")
    print(f"Total Images: {res.get('total_images', 0)}")
    print(f"Total Annotations: {res.get('total_annotations', 0)}")
    print(f"Duplicates: {len(res.get('duplicate_images_found', []))}")
    print("\nClass Distribution:")
    for cid, cnt in res.get("class_distribution_total", {}).items():
        cname = cfg.get_class_name(cid)
        print(f"  Class {cid} ({cname}): {cnt}")

    print(f"\nDetailed report saved to: {out_file}")
    print("==================================================")
