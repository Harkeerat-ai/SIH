"""Live API server: random data -> train -> register model -> uvicorn."""
import sys
import io
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image

sys.path.insert(0, r"C:\Users\Harkeerat Bhasin\OneDrive\Desktop\SIH")

import importlib
from sihvision.api.app import app, register_model
from sihvision.data.build import build_dataset
from sihvision.models.registry import build_model
from sihvision.train import train

BASE = Path(r"C:\Users\HARKEE~1\AppData\Local\Temp\opencode\live_random")
CLASSES = ["water", "urban", "forest", "barren"]

def make_data(root, n_per_class=8, size=48):
    rng = np.random.default_rng()
    for c, cls in enumerate(CLASSES):
        d = root / "train" / cls
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n_per_class):
            base = rng.integers(0, 80, (size, size, 3), dtype=np.uint8)
            base[..., c % 3] = 235
            arr = np.clip(base + rng.integers(0, 50, base.shape, dtype=np.uint8), 0, 255).astype(np.uint8)
            Image.fromarray(arr).save(d / f"img_{i}.png")

def main():
    print("== generating random data ==", flush=True)
    make_data(BASE)

    print("== building dataset ==", flush=True)
    ds = build_dataset("classification", "folder_classification", BASE, split="train", channels=3)
    print("classes:", ds.classes, "num_classes:", ds.num_classes, flush=True)

    cfg = {
        "task": "classification",
        "data": {"root": str(BASE), "format": "folder_classification", "channels": 3},
        "model": {"backbone": "resnet18"},
        "train": {"epochs": 3, "lr": 1e-3, "device": "cuda"},
    }
    cfg_path = BASE / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    print("== training on CUDA ==", flush=True)
    model = build_model(cfg, num_classes=ds.num_classes)
    history = train(cfg, model, ds, device="cuda")
    print("history:", history, flush=True)

    print("== registering model ==", flush=True)
    register_model(cfg_path, ds.classes)
    api_mod = importlib.import_module("sihvision.api.app")
    api_mod._MODEL.load_state_dict(model.state_dict())
    api_mod._MODEL.eval()
    print("model registered, device:", next(api_mod._MODEL.parameters()).device, flush=True)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
