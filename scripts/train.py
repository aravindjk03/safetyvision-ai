"""
SafetyVision AI — YOLO Training Pipeline
Configurable training script with automatic CUDA detection, CPU fallback,
and model registry synchronization.
"""

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys
import yaml

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import torch
from ultralytics import YOLO

from app.config import get_config
from app.logger import get_logger


def parse_args():
    parser = argparse.ArgumentParser(description="SafetyVision AI — Model Training")
    parser.add_argument("--data", type=str, default="dataset/data.yaml", help="Dataset YAML (relative to project root or absolute)")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Base model weights or architecture (yolo11n.pt, yolo26n)")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size for training")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", type=str, default="auto", help="Execution device: auto, cpu, cuda, or cuda:0")
    parser.add_argument("--workers", type=int, default=2, help="DataLoader workers")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--project", type=str, default="models/training_runs", help="Output project directory")
    parser.add_argument("--name", type=str, default="safetyvision_yolo26n", help="Experiment name")
    parser.add_argument("--save-best", type=str, default="models/safetyvision_yolo26n.pt", help="Path to save best weights")
    return parser.parse_args()


def resolve_device(requested_device: str) -> str:
    """Detects available hardware and prints explicit device notification."""
    if requested_device == "auto":
        if torch.cuda.is_available():
            dev = "cuda:0"
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[DEVICE SELECTION] CUDA GPU DETECTED: {gpu_name}. Training will run on GPU.")
        else:
            dev = "cpu"
            print("[DEVICE SELECTION] CUDA NOT DETECTED. Gracefully falling back to CPU for training.")
    else:
        dev = requested_device
        print(f"[DEVICE SELECTION] Explicitly requested device: {dev}")
    return dev


def run_training():
    args = parse_args()
    logger = get_logger()
    cfg = get_config(ROOT_DIR)

    dataset_yaml = ROOT_DIR / args.data
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"Dataset configuration not found at {dataset_yaml}. Run scripts/generate_sample_data.py first.")

    device = resolve_device(args.device)

    print("==================================================")
    print("SAFETYVISION AI — MODEL TRAINING PIPELINE")
    print(f"Base Architecture: {args.model}")
    print(f"Dataset:           {dataset_yaml}")
    print(f"Epochs:            {args.epochs}")
    print(f"Image Size:        {args.imgsz}")
    print(f"Batch Size:        {args.batch}")
    print(f"Target Device:     {device}")
    print(f"Project Run Dir:   {args.project}/{args.name}")
    print("==================================================")

    logger.info(f"Initiating YOLO training with base: {args.model} on {device}...")

    # Initialize model
    model = YOLO(args.model)

    # Execute training
    results = model.train(
        data=str(dataset_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        workers=args.workers,
        patience=args.patience,
        project=str(ROOT_DIR / args.project),
        name=args.name,
        exist_ok=True,
        verbose=True,
    )

    # Locate best weights from training run
    run_dir = ROOT_DIR / args.project / args.name
    best_weights = run_dir / "weights" / "best.pt"
    save_dest = ROOT_DIR / args.save_best

    if best_weights.exists():
        save_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_weights, save_dest)
        print(f"\n[MODEL READY] Best model saved to: {save_dest}")
        logger.info(f"Copied best model weights to {save_dest}")
    else:
        print(f"\n[WARNING] best.pt not found at {best_weights}. Checking last.pt...")
        last_weights = run_dir / "weights" / "last.pt"
        if last_weights.exists():
            shutil.copy2(last_weights, save_dest)
            print(f"[MODEL READY] Copied last.pt weights to: {save_dest}")

    print("\nTraining completed successfully!")
    print("Run `python scripts/evaluate.py` to calculate precision, recall, and mAP metrics.")
    print("==================================================")


if __name__ == "__main__":
    run_training()
