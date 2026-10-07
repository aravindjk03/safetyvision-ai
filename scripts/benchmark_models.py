"""
SafetyVision AI — Model Benchmarking Suite
Compares latency, memory footprint, throughput (FPS), and parameters across
YOLO nano (n), small (s), and medium (m) architectures.
"""

from datetime import datetime
import json
from pathlib import Path
import sys
import time

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import torch
from ultralytics import YOLO

from app.config import get_config


def benchmark_model(model_name: str, warmup_runs: int = 10, test_runs: int = 30) -> dict:
    """Measures model inference latency, FPS, and parameter count."""
    print(f"\nBenchmarking {model_name}...")
    model = YOLO(model_name)

    # Synthetic 640x640 frame for consistent benchmarking
    dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # Warmup
    for _ in range(warmup_runs):
        _ = model.predict(dummy_frame, verbose=False)

    # Latency Measurement
    latencies = []
    for _ in range(test_runs):
        t0 = time.perf_counter()
        _ = model.predict(dummy_frame, verbose=False)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = float(np.mean(latencies))
    std_ms = float(np.std(latencies))
    p95_ms = float(np.percentile(latencies, 95))
    fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

    # Model size estimation
    weights_path = Path(model.ckpt_path) if hasattr(model, "ckpt_path") and model.ckpt_path else None
    size_mb = (weights_path.stat().st_size / (1024 * 1024)) if weights_path and weights_path.exists() else 0.0

    # Parameter count
    param_count = sum(p.numel() for p in model.model.parameters()) / 1e6 if hasattr(model, "model") else 0.0

    return {
        "model_name": model_name,
        "parameters_m": round(param_count, 2),
        "size_mb": round(size_mb, 2),
        "avg_latency_ms": round(avg_ms, 2),
        "std_latency_ms": round(std_ms, 2),
        "p95_latency_ms": round(p95_ms, 2),
        "throughput_fps": round(fps, 1),
    }


def run_benchmark():
    cfg = get_config(ROOT_DIR)
    models_to_test = ["yolo11n.pt", "yolo11s.pt"]

    print("==================================================")
    print("SAFETYVISION AI — MODEL LATENCY & FPS BENCHMARK")
    print(f"Device: {'CUDA GPU' if torch.cuda.is_available() else 'CPU'}")
    print("==================================================")

    results = []
    for m in models_to_test:
        try:
            res = benchmark_model(m, warmup_runs=5, test_runs=15)
            results.append(res)
        except Exception as e:
            print(f"Skipping {m} due to download or init error: {e}")

    report_payload = {
        "timestamp": datetime.now().isoformat(),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "benchmarks": results,
    }

    out_file = cfg.reports_dir / "model_benchmark_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print("\nBENCHMARK RESULTS TABLE:")
    print(f"{'Model':<16} | {'Params (M)':<10} | {'Latency (ms)':<14} | {'FPS':<8}")
    print("-" * 55)
    for r in results:
        print(f"{r['model_name']:<16} | {r['parameters_m']:<10} | {r['avg_latency_ms']:<14} | {r['throughput_fps']:<8}")

    print(f"\nBenchmark report saved to: {out_file}")
    print("==================================================")


if __name__ == "__main__":
    run_benchmark()
