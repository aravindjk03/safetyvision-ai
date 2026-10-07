# SafetyVision AI — Installation & Setup Guide

This guide provides exact deployment commands for Windows and Linux platforms.

---

## Prerequisites
- **Python**: 3.11 or 3.12 (64-bit)
- **Git** (optional, for version control)
- **Webcam / USB Camera** (optional, for live video inspection station)
- **Hardware**:
  - Minimum: 4-Core CPU, 8 GB RAM (runs inference in ~40ms on CPU).
  - Recommended: NVIDIA GPU with CUDA 12+ for real-time >60 FPS inference.

---

## 1. Windows Installation (PowerShell / Command Prompt)

### Step 1: Clone & Navigate to Project
```powershell
git clone https://github.com/aravindjk03/safetyvision-ai.git
cd safetyvision-ai
```

### Step 2: Create Python Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate Virtual Environment
```powershell
# In PowerShell:
.\venv\Scripts\Activate.ps1

# Or in Command Prompt:
.\venv\Scripts\activate.bat
```

### Step 4: Upgrade Pip & Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Verify Environment & Tests
```powershell
pytest -v
```

### Step 6: Launch Industrial Streamlit Dashboard
```powershell
streamlit run app/main.py
```
*The web browser will automatically open at `http://localhost:8501`.*

---

## 2. Linux / Ubuntu Installation (Bash)

### Step 1: Install System Libraries (for OpenCV & GUI headless support)
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv libgl1-mesa-glx libglib2.0-0
```

### Step 2: Navigate to Directory & Create Virtual Environment
```bash
cd /opt/safetyvision-ai
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run Test Suite
```bash
pytest -v
```

### Step 5: Run Application
```bash
streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0
```

---

## 3. Running as Headless REST API (FastAPI)

To run the system as an automated microservice for factory integration:
```bash
# Windows
.\venv\Scripts\uvicorn.exe app.api:app --host 0.0.0.0 --port 8000

# Linux
uvicorn app.api:app --host 0.0.0.0 --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 4. Hardware Acceleration (CUDA GPU Setup)

If an NVIDIA GPU is available:
```bash
# Install PyTorch with CUDA 12.1+ support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```
SafetyVision AI automatically senses CUDA availability and engages the GPU without manual code modifications.
