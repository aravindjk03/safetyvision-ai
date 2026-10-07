# SafetyVision AI — Industrial Visual Safety Inspection Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: AGPL-3.0 / Commercial](https://img.shields.io/badge/license-AGPL--3.0%20%2F%20Commercial-green.svg)](docs/LICENSE_AND_COMMERCIAL_USE.md)
[![Architecture: Decoupled](https://img.shields.io/badge/architecture-physically--observable-orange.svg)](docs/ARCHITECTURE.md)
[![Safety: OSHA / ANSI Grounded](https://img.shields.io/badge/safety-OSHA%201910.243-red.svg)](docs/LIMITATIONS.md)

**SafetyVision AI** is an auditable, deterministic, AI-assisted computer vision platform designed for industrial visual safety inspection. The initial prototype is configured for **Industrial Angle Grinder** safety compliance, with an architecture designed to easily scale across power tools, machinery, and inline conveyor belts.

---

> [!IMPORTANT]
> ### Crucial Industrial Safety Principle
> SafetyVision AI evaluates **configured, physically observable visual requirements only**.
> - **It does NOT** claim that equipment is universally or physically "safe".
> - **It does NOT** certify electrical insulation resistance, mechanical bolt torque, or subsurface material fatigue.
> - **It NEVER replaces** formal statutory, OSHA, manufacturer, or certified Competent-Person inspections.
> - Automated decisions strictly adhere to a **Three-State Model**:
>   - **PASS**: All configured visual requirements detected with high confidence and valid spatial attachment.
>   - **FAIL**: One or more mandatory safety components are missing, or structural damage is observed.
>   - **REVIEW**: AI confidence is ambiguous ($< 0.85$), visual evidence is occluded/degraded, or scene is indeterminate.

---

## 1. System Architecture

Unlike fragile black-box classifiers that predict `SAFE` vs `UNSAFE` directly, SafetyVision AI enforces an **explainable, auditable 8-stage pipeline**:

```
CAMERA / IMAGE CAPTURE
         ↓
YOLO OBJECT DETECTION (Ultralytics YOLO26 / YOLO11)
         ↓
PHYSICAL DETECTIONS (grinder, guard, handle, cable, switch, damaged_*, person)
         ↓
SPATIAL RELATIONSHIP ANALYSIS (IoU, Containment, Normalized Center Distance)
         ↓
DETERMINISTIC SAFETY RULE ENGINE (config/safety_rules.yaml)
         ↓
CONFIDENCE & AMBIGUITY EVALUATION (High >= 0.85, Medium 0.60..0.85, Low < 0.60)
         ↓
THREE-STATE DECISION: PASS / FAIL / REVIEW
         ↓
TAMPER-EVIDENT EVIDENCE IMAGE + SQLITE AUDIT RECORD + REPORTLAB PDF REPORT
```

---

## 2. Technology Stack

- **Deep Learning**: Ultralytics YOLO26 / YOLO11 (Hot-swappable Nano, Small, Medium backbones).
- **Computer Vision**: OpenCV (headless/full).
- **Dashboard Frontend**: Streamlit (Multi-page industrial workstation UI).
- **Backend Services**: FastAPI & Pydantic (Headless REST microservice).
- **Database**: SQLite with Write-Ahead Logging (`WAL`).
- **Audit Reports**: ReportLab (Vector PDF generator) & HTML.
- **Data Engineering**: NumPy & Pandas.
- **Configuration**: PyYAML.
- **Edge Deployment**: ONNX export integrated; TensorRT compatible.

---

## 3. Quick Start & Installation

### Windows (PowerShell)
```powershell
# 1. Clone and enter the repository
git clone https://github.com/aravindjk03/safetyvision-ai.git
cd safetyvision-ai

# 2. Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Run automated test suite
pytest -v

# 5. Launch Streamlit Industrial Dashboard (or double-click run.bat)
streamlit run app/main.py
```

The repository already ships the sample dataset and trained weights. Re-generate the synthetic dataset only if you want fresh samples: `python scripts/generate_sample_data.py`.

### Linux (Ubuntu / Debian)
```bash
# 1. Install system multimedia libraries
sudo apt update && sudo apt install -y python3-pip python3-venv libgl1 libglib2.0-0

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies (CPU-only PyTorch first keeps the install small)
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. Run tests & start dashboard / API
pytest -v
./run.sh            # dashboard → http://localhost:8501
./run.sh api        # REST API  → http://localhost:8080/docs
./run.sh all        # both
```

---

## 4. Operational Modes: Demo vs. Custom Model

1. **Demo Mode (Out-of-the-Box)**:
   - When custom trained weights (`models/safetyvision_yolo26n.pt`) are not present, the system loads a standard pretrained nano model to demonstrate the camera feed and UI pipeline.
   - Prominently watermarked: **`"DEMO MODEL — NOT TRAINED FOR INDUSTRIAL SAFETY INSPECTION"`**.
2. **Custom Model Mode**:
   - Once trained weights exist at `models/safetyvision_yolo26n.pt`, the system automatically transitions:
   - Displays: **`MODEL: SafetyVision-YOLO26 | VERSION: 2.1.0 | MODE: CUSTOM SAFETY MODEL`**.

---

## 5. Model Training & Evaluation

```bash
# 1. Validate dataset integrity (checks missing labels, bounding box coordinates, distributions)
python scripts/validate_dataset.py

# 2. Train custom YOLO model (auto-detects CUDA GPU or gracefully falls back to CPU)
python scripts/train.py --epochs 30 --batch 16 --imgsz 320

# 3. Run model evaluation audit (generates reports/model_evaluation.json & .html)
python scripts/evaluate.py --split test --imgsz 320

# 4. Run model latency and throughput benchmark
python scripts/benchmark_models.py
```

**Current model (v2.1.0, see `models/model_registry.yaml`):** held-out test split mAP50 0.995, mAP50-95 0.994, precision 0.997, recall 1.000, about 23 ms per image on CPU at 320 px.
These numbers are saturated because the dataset is synthetic (rendered by `scripts/generate_sample_data.py`), and train and test come from the same generator. They do **not** predict performance on real photographs. Real deployment requires a labelled dataset of real equipment images (see `docs/DATA_COLLECTION_GUIDE.md`).

---

## 6. Project Directory Tree

```
safetyvision-ai/
├── config/
│   ├── config.yaml               # Master application configuration
│   ├── classes.yaml              # Detection class definitions & colors
│   └── safety_rules.yaml         # Equipment safety rules and severities
├── dataset/
│   ├── data.yaml                 # YOLO dataset configuration
│   ├── images/                   # Train / Val / Test partitions
│   └── labels/                   # YOLO normalized bounding box text files
├── models/
│   ├── model_registry.yaml       # Model lineage, versioning, and metrics
│   └── (safetyvision_yolo26n.pt) # Active trained weights
├── data/
│   └── safetyvision.db           # SQLite persistent inspection records
├── evidence/                     # Annotated inspection photos (evidence/YYYY/MM/DD/)
├── reports/                      # Generated PDF & HTML audit reports
├── logs/                         # Rotating application logs
├── app/
│   ├── config.py                 # Configuration manager
│   ├── logger.py                 # Structured rotating logger
│   ├── detector.py               # YOLO model wrapper & detection normalizer
│   ├── spatial.py                # Bounding-box spatial relationship engine
│   ├── rules.py                  # Deterministic safety rule engine
│   ├── inspection.py             # End-to-end inspection orchestrator
│   ├── evidence.py               # OpenCV visual evidence annotator
│   ├── database.py               # SQLite database manager
│   ├── report.py                 # ReportLab PDF report generator
│   ├── roi.py                    # Conveyor inspection ROI logic
│   ├── integrations/plc.py       # Industrial PLC / Fieldbus interface stub
│   ├── api.py                    # FastAPI REST interface
│   └── main.py                   # Streamlit industrial dashboard
├── scripts/
│   ├── generate_sample_data.py   # Synthetic industrial test image generator
│   ├── validate_dataset.py       # Dataset audit & distribution validator
│   ├── train.py                  # Configurable YOLO training pipeline
│   ├── evaluate.py               # Precision, Recall, mAP evaluation
│   └── benchmark_models.py       # Latency, FPS, parameter benchmark
├── tests/
│   ├── test_config.py            # Configuration tests
│   ├── test_spatial.py           # Spatial geometry tests
│   ├── test_rules.py             # Rule engine tests (PASS, FAIL, REVIEW)
│   ├── test_inspection.py        # End-to-end integration tests
│   └── test_report.py            # PDF report generator tests
├── docs/
│   ├── ARCHITECTURE.md           # Mathematical and architectural specs
│   ├── INSTALLATION.md           # Step-by-step setup on Windows & Linux
│   ├── DATASET_GUIDE.md          # Dataset annotations and schemas
│   ├── DATA_COLLECTION_GUIDE.md  # Real-world industrial data collection
│   ├── TRAINING.md               # Training procedure and hyperparameters
│   ├── TESTING.md                # Testing matrix and acceptance criteria
│   ├── PRODUCTION_ROADMAP.md     # Jetson/IPC edge deployment & PLC integration
│   ├── LICENSE_AND_COMMERCIAL_USE.md # Ultralytics AGPL vs commercial analysis
│   ├── CYBERSECURITY.md          # ISO 27001 / IEC 62443 cyber controls
│   └── LIMITATIONS.md            # Boundary conditions & liability disclaimers
├── requirements.txt              # Pinned Python dependencies
├── .env.example                  # Environment variables template
└── README.md                     # Master documentation
```

---

## 7. Headless REST API Integration

Start the headless FastAPI microservice:
```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8080
```
- Interactive Swagger UI: `http://localhost:8080/docs`
- Health check: `GET /health`
- Run image inspection: `POST /inspect/image`
- Query inspection record: `GET /inspection/{id}`
- Query fleet statistics: `GET /inspections`
- Model governance: `GET /model`
- Configured rules: `GET /rules`

---

Example request:
```bash
curl -F "file=@dataset/images/test/acceptance_01_pass_full.jpg;type=image/jpeg" \
     "http://localhost:8080/inspect/image?operator=Line-3"
```

---

## 8. Running Live (Deployment)

### Docker (dashboard + API)
```bash
docker compose up --build
# Dashboard: http://localhost:8501   API: http://localhost:8080/docs
```
Both services share named volumes for the SQLite audit database, evidence images and PDF reports. The image uses CPU-only PyTorch.

### Single container on a hosting platform (Render, Railway, Cloud Run, Hugging Face Docker Spaces)
Point the platform at the `Dockerfile`. The container serves the dashboard on `$PORT` (default `8501`). To run the API instead, override the start command with
`python -m uvicorn app.api:app --host 0.0.0.0 --port $PORT`.

### Streamlit Community Cloud (free, recommended for a public demo)
1. Open the one-click deploy link: <https://share.streamlit.io/deploy?repository=aravindjk03/safetyvision-ai&branch=main&mainModule=app/main.py>
2. Sign in with GitHub and authorize Streamlit.
3. Under **Advanced settings**, choose Python **3.11**, then click **Deploy**.

The first build takes about 5 to 10 minutes. `requirements.txt` pulls CPU-only PyTorch, `packages.txt` installs the OpenCV system libraries, and `.streamlit/config.toml` provides the theme. You get a public `https://<name>.streamlit.app` URL.

> [!NOTE]
> Free hosting tiers have no persistent disk: the inspection history, evidence and reports reset on every restart. Mount a volume (Docker/Render) for a durable audit trail. The **Live Camera** page uses the browser's camera, so it requires the dashboard to be served over HTTPS (or `localhost`).

---

## 9. Licensing

SafetyVision AI prototype integrates Ultralytics YOLO.
- **Open Source Evaluation**: Licensed under GNU AGPL-3.0.
- **Commercial Deployment**: Consult `docs/LICENSE_AND_COMMERCIAL_USE.md` for guidance on acquiring an Ultralytics Commercial License or utilizing the decoupled ONNX Runtime inference architecture.
