"""
SafetyVision AI — REST API Service
FastAPI endpoints for automated industrial inspection integration.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from app.config import get_config
from app.database import DatabaseManager
from app.detector import DetectionEngine
from app.inspection import InspectionEngine
from app.logger import get_logger

logger = get_logger()
cfg = get_config()

app = FastAPI(
    title=cfg.system_config.get("api", {}).get("title", "SafetyVision AI Inspection API"),
    version=cfg.system_config.get("api", {}).get("version", "0.1.0"),
    description="Industrial Visual Safety Inspection Platform REST Interface",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engines
db = DatabaseManager()
detector = DetectionEngine()
inspection_engine = InspectionEngine(detector=detector, db_manager=db)


@app.get("/health", tags=["System"])
async def health_check():
    """Returns service health status, model information, and storage paths."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "app_name": cfg.app_name,
        "version": cfg.system_info.get("version", "0.1.0"),
        "model": {
            "name": detector.model_name,
            "version": detector.model_version,
            "is_custom_model": detector.is_custom_model,
        },
        "database_connected": Path(db.db_path).exists(),
    }


@app.post("/inspect/image", tags=["Inspection"])
async def inspect_uploaded_image(
    file: UploadFile = File(...),
    operator: str = Query("API Operator", description="Operator or inspection line ID"),
    comments: str = Query("", description="Optional inspection notes"),
    conf_threshold: Optional[float] = Query(None, description="Optional custom confidence cutoff"),
):
    """
    Uploads an image, runs YOLO detection, spatial reasoning, safety rule engine,
    and returns full auditable PASS/FAIL/REVIEW payload.
    """
    valid_content_types = ["image/jpeg", "image/png", "image/bmp", "image/webp"]
    if file.content_type not in valid_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type '{file.content_type}'. Must be one of {valid_content_types}.",
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        pil_image = Image.open(BytesIO(contents))
        result = inspection_engine.inspect(
            image_input=pil_image,
            operator=operator,
            comments=comments,
            conf_threshold=conf_threshold,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Inspection error on /inspect/image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inspection failed: {str(e)}")


@app.get("/inspection/{inspection_id}", tags=["Inspection"])
async def get_inspection_by_id(inspection_id: str):
    """Retrieves full inspection record by ID."""
    record = db.get_inspection(inspection_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")
    return record


@app.get("/inspections", tags=["Inspection History"])
async def list_inspections(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by PASS, FAIL, or REVIEW"),
    equipment: Optional[str] = Query(None, description="Filter by equipment key"),
):
    """Retrieves historical inspection records with optional filters."""
    records = db.get_history(limit=limit, offset=offset, filter_status=status, filter_equipment=equipment)
    stats = db.get_statistics()
    return {"statistics": stats, "records": records}


@app.get("/model", tags=["Model Governance"])
async def get_model_info():
    """Returns active model details and registry entries."""
    registry_file = cfg.root_dir / "models" / "model_registry.yaml"
    raw_registry = cfg._load_yaml(registry_file)
    return {
        "active_model": {
            "name": detector.model_name,
            "version": detector.model_version,
            "is_custom": detector.is_custom_model,
        },
        "registry": raw_registry,
    }


@app.get("/rules", tags=["Configuration"])
async def get_safety_rules(equipment_key: str = Query("angle_grinder")):
    """Returns currently loaded safety rules and thresholds for specified equipment."""
    rules = cfg.get_equipment_rules(equipment_key)
    if not rules:
        raise HTTPException(status_code=404, detail=f"No rules defined for '{equipment_key}'.")
    return {
        "equipment": equipment_key,
        "rules": rules,
        "classes": cfg.classes,
    }
