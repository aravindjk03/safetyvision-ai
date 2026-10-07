# SafetyVision AI — Model Training & Transfer Learning Guide

## 1. Overview

SafetyVision AI uses Ultralytics YOLO models optimized for low-latency edge inference and high detection recall on small safety-critical components (such as thin cables and mounting screws).

### Supported Architecture Backbones
The application is designed to dynamically accept any YOLO scale without requiring codebase refactoring:
- `yolo26n` / `yolo11n` (Nano): ~2.6M params, optimized for CPU and edge embedded devices (Jetson Nano / Orin Nano).
- `yolo26s` / `yolo11s` (Small): ~9.4M params, balanced edge performance.
- `yolo26m` / `yolo11m` (Medium): ~20.1M params, higher mAP for complex multi-tool scenes.
- `yolo26l` / `yolo26x` (Large/Extra): High accuracy for offline server batch inspections.

---

## 2. Training Execution

The training pipeline is invoked via `scripts/train.py`:

```bash
# Basic Training Run (Auto-detects CUDA / CPU)
python scripts/train.py --model yolo11n.pt --epochs 30 --batch 16 --imgsz 640

# Custom Hyperparameter Overrides
python scripts/train.py \
    --model yolo11n.pt \
    --epochs 50 \
    --batch 32 \
    --imgsz 640 \
    --device auto \
    --patience 15 \
    --name angle_grinder_safety_v1
```

---

## 3. Hardware Auto-Detection & Fallback

`scripts/train.py` automatically interrogates the PyTorch runtime:
1. **CUDA Available**: Directs training to GPU `cuda:0` with mixed-precision FP16 enabled.
2. **CUDA Unavailable**: Gracefully defaults to multi-core CPU with FP32 precision, outputting an informative console notification.

---

## 4. Hyperparameter Recommendations for Safety Inspection

Industrial safety components present unique visual challenges:
- **Small Component Bounding Boxes**: Cable fraying and switch toggles occupy < 5% of the image area.
- **Data Augmentation**:
  - `mosaic=1.0`: Crucial for detecting components in cluttered environments.
  - `degrees=15.0`: In-plane rotations simulating variable tool resting orientations.
  - `flipud=0.0`: Disabled for floor-standing tools, enabled for handheld tools.
  - `scale=0.5`: Multi-scale training to handle varying camera distances.

---

## 5. Model Lineage & Deployment Weights

When training concludes:
1. Best weights are saved to `models/training_runs/{experiment_name}/weights/best.pt`.
2. Automatically copied to `models/safetyvision_yolo26n.pt`.
3. The detection engine (`app/detector.py`) instantly transitions from **DEMO MODE** to **CUSTOM SAFETY MODEL** upon detecting `models/safetyvision_yolo26n.pt`.
