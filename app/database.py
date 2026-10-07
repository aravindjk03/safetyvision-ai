"""
SafetyVision AI — SQLite Database Module
Manages persistent inspection records, component checks, detection logs, and audit statistics.
"""

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_config
from app.logger import get_logger


class DatabaseManager:
    """Manages SQLite storage and historical query analytics."""

    def __init__(self, db_path: Optional[Path] = None):
        self.logger = get_logger()
        self.config = get_config()
        self.db_path = db_path or self.config.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with WAL mode enabled and Row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Creates database schema if not already initialized."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Main Inspections Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    equipment_type TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    highest_severity TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    image_path TEXT,
                    evidence_path TEXT,
                    report_path TEXT,
                    operator TEXT,
                    comments TEXT,
                    reason TEXT,
                    recommended_action TEXT,
                    inference_time_ms REAL,
                    total_time_ms REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Detailed Component Checks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inspection_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    severity TEXT NOT NULL,
                    is_mandatory INTEGER NOT NULL,
                    is_associated INTEGER NOT NULL,
                    message TEXT,
                    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE CASCADE
                );
            """)

            # 3. Raw Bounding Box Detections Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id TEXT NOT NULL,
                    class_id INTEGER NOT NULL,
                    class_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    x1 REAL, y1 REAL, x2 REAL, y2 REAL,
                    center_x REAL, center_y REAL,
                    area REAL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE CASCADE
                );
            """)

            # 4. Equipment Types Configuration Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment_types (
                    key TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    category TEXT,
                    active INTEGER DEFAULT 1
                );
            """)

            # 5. Safety Rules Snapshot Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS safety_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_key TEXT NOT NULL,
                    rule_description TEXT NOT NULL,
                    severity TEXT NOT NULL
                );
            """)

            # 6. Model Versions Audit Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    architecture TEXT,
                    weights_path TEXT,
                    is_custom INTEGER DEFAULT 0,
                    registered_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Populate initial equipment types if empty
            cursor.execute("SELECT COUNT(*) FROM equipment_types;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO equipment_types (key, display_name, category, active)
                    VALUES ('angle_grinder', 'Industrial Angle Grinder', 'power_tools', 1);
                """)

            conn.commit()
            self.logger.info(f"Database schema verified at {self.db_path}")

    def save_inspection(
        self,
        inspection_data: Dict[str, Any],
        checks: Dict[str, Dict[str, Any]],
        detections: List[Any],
    ) -> None:
        """Atomically saves inspection summary, component checks, and detections."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Insert master inspection record
            cursor.execute("""
                INSERT INTO inspections (
                    inspection_id, timestamp, equipment_type, overall_status,
                    confidence, highest_severity, model_version, image_path,
                    evidence_path, report_path, operator, comments,
                    reason, recommended_action, inference_time_ms, total_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                inspection_data.get("inspection_id"),
                inspection_data.get("timestamp"),
                inspection_data.get("equipment_type"),
                inspection_data.get("overall_status"),
                float(inspection_data.get("confidence", 0.0)),
                inspection_data.get("highest_severity", "NONE"),
                inspection_data.get("model_version", "0.1.0"),
                str(inspection_data.get("image_path", "")),
                str(inspection_data.get("evidence_path", "")),
                str(inspection_data.get("report_path", "")),
                inspection_data.get("operator", "System Operator"),
                inspection_data.get("comments", ""),
                inspection_data.get("reason", ""),
                inspection_data.get("recommended_action", ""),
                float(inspection_data.get("inference_time_ms", 0.0)),
                float(inspection_data.get("total_time_ms", 0.0)),
            ))

            insp_id = inspection_data.get("inspection_id")

            # Insert component checks
            for comp_name, chk in checks.items():
                cursor.execute("""
                    INSERT INTO inspection_results (
                        inspection_id, component_name, status, confidence,
                        severity, is_mandatory, is_associated, message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    insp_id,
                    comp_name,
                    chk.get("status", "FAIL"),
                    float(chk.get("confidence", 0.0)),
                    chk.get("severity", "MEDIUM"),
                    1 if chk.get("is_mandatory", True) else 0,
                    1 if chk.get("is_associated", False) else 0,
                    chk.get("message", ""),
                ))

            # Insert raw detections
            for d in detections:
                d_dict = d.to_dict() if hasattr(d, "to_dict") else d
                bbox = d_dict.get("bbox", [0, 0, 0, 0])
                center = d_dict.get("center", [0, 0])
                cursor.execute("""
                    INSERT INTO detections (
                        inspection_id, class_id, class_name, confidence,
                        x1, y1, x2, y2, center_x, center_y, area
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    insp_id,
                    int(d_dict.get("class_id", 0)),
                    d_dict.get("class_name", ""),
                    float(d_dict.get("confidence", 0.0)),
                    float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]),
                    float(center[0]), float(center[1]),
                    float(d_dict.get("area", 0.0)),
                ))

            conn.commit()
            self.logger.info(f"Inspection {insp_id} persisted in database.")

    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single inspection record along with its component checks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inspections WHERE inspection_id = ?;", (inspection_id,))
            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)

            # Fetch component checks
            cursor.execute("SELECT * FROM inspection_results WHERE inspection_id = ?;", (inspection_id,))
            result["checks"] = [dict(r) for r in cursor.fetchall()]

            # Fetch detections
            cursor.execute("SELECT * FROM detections WHERE inspection_id = ?;", (inspection_id,))
            result["detections"] = [dict(r) for r in cursor.fetchall()]

            return result

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        filter_status: Optional[str] = None,
        filter_equipment: Optional[str] = None,
        search_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetches filtered inspection history ordered by newest first."""
        query = "SELECT * FROM inspections WHERE 1=1"
        params: List[Any] = []

        if filter_status and filter_status != "ALL":
            query += " AND overall_status = ?"
            params.append(filter_status)

        if filter_equipment and filter_equipment != "ALL":
            query += " AND equipment_type = ?"
            params.append(filter_equipment)

        if search_id:
            query += " AND inspection_id LIKE ?"
            params.append(f"%{search_id}%")

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates total counts, pass/fail/review rates, and operational metrics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_status = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN overall_status = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                    SUM(CASE WHEN overall_status = 'REVIEW' THEN 1 ELSE 0 END) as review_count,
                    AVG(inference_time_ms) as avg_inference_ms,
                    AVG(total_time_ms) as avg_total_ms
                FROM inspections;
            """)
            row = cursor.fetchone()
            total = row["total"] or 0
            passes = row["pass_count"] or 0
            fails = row["fail_count"] or 0
            reviews = row["review_count"] or 0

            fail_rate = (fails / total * 100.0) if total > 0 else 0.0
            review_rate = (reviews / total * 100.0) if total > 0 else 0.0
            pass_rate = (passes / total * 100.0) if total > 0 else 0.0

            return {
                "total_inspections": total,
                "pass_count": passes,
                "fail_count": fails,
                "review_count": reviews,
                "pass_rate_pct": round(pass_rate, 1),
                "failure_rate_pct": round(fail_rate, 1),
                "review_rate_pct": round(review_rate, 1),
                "avg_inference_ms": round(row["avg_inference_ms"] or 0.0, 1),
                "avg_total_ms": round(row["avg_total_ms"] or 0.0, 1),
            }
