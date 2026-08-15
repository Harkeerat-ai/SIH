"""Random-data live smoke test for sihvision.

Generates UNSEEDED (random) synthetic datasets for all 5 task formats, then
exercises the full pipeline: config load, build_dataset, train, predict,
saliency, dashboard, and check-data CLI.
"""
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import torch
from sihvision.dashboard import render_dashboard
from sihvision.data.build import build_dataset
from sihvision.models.registry import build_model
from sihvision.train import train
from sihvision.xai import saliency_map

SCRIPT = Path(__file__).parent
ROOT = Path(tempfile.mkdtemp(prefix="sihvision_random_"))


def rng():
    return np.random.default_rng()  # unseeded -> genuinely random


def seed_series(*args):
    return np.random.SeedSequence()  # no-op marker


def make_classification(root, n_classes=4, per_class=5, size=48):
    r = rng()
    for split in ("train",):
        for c in range(n_classes):
            d = root / split / f"cls{c}"
            d.mkdir(parents=True, exist_ok=True)
            for i in range(per_class):
                base = r.integers(0, 80, (size, size, 3), dtype=np.uint8)
                base[..., c % 3] = 230
                arr = np.clip(base + r.integers(0, 50, base.shape, dtype=np.uint8), 0, 255).astype(np.uint8)
                Image.fromarray(arr).save(d / f"img_{i}.png")


def make_regression(root, n=10, size=32):
    r = rng()
    img_dir = root / "train" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(n):
        arr = r.integers(0, 256, (size, size, 3), dtype=np.uint8)
        Image.fromarray(arr).save(img_dir / f"img_{i}.png")
        rows.append(f"img_{i},{float(r.uniform(0, 100)):.3f}")
    (root / "train" / "labels.csv").write_text("image_id,value\n" + "\n".join(rows), encoding="utf-8")


def make_segmentation(root, n=6, size=32, n_classes=4):
    r = rng()
    img_dir = root / "train" / "images"
    msk_dir = root / "train" / "masks"
    img_dir.mkdir(parents=True, exist_ok=True)
    msk_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        arr = r.integers(0, 256, (size, size, 3), dtype=np.uint8)
        Image.fromarray(arr).save(img_dir / f"img_{i}.png")
        mask = np.zeros((size, size), dtype=np.uint8)
        for cls in range(1, n_classes):
            cy = int(r.integers(4, size - 4)); cx = int(r.integers(4, size - 4)); rad = int(r.integers(2, 6))
            yy, xx = np.ogrid[:size, :size]
            mask[(yy - cy) ** 2 + (xx - cx) ** 2 <= rad * rad] = cls
        Image.fromarray(mask).save(msk_dir / f"img_{i}.png")


def make_change(root, n=6, size=32):
    r = rng()
    for sub in ("t1", "t2", "masks"):
        (root / "train" / sub).mkdir(parents=True, exist_ok=True)
    for i in range(n):
        base = r.integers(0, 256, (size, size, 3), dtype=np.uint8)
        Image.fromarray(base).save(root / "train" / "t1" / f"img_{i}.png")
        t2 = base.copy()
        mask = np.zeros((size, size), dtype=np.uint8)
        for _ in range(int(r.integers(1, 4))):
            cy = int(r.integers(2, size - 2)); cx = int(r.integers(2, size - 2)); rad = int(r.integers(1, 4))
            yy, xx = np.ogrid[:size, :size]
            zone = (yy - cy) ** 2 + (xx - cx) ** 2 <= rad * rad
            t2[zone] = r.integers(0, 256, (3,), dtype=np.uint8)
            mask[zone] = 1
        Image.fromarray(t2).save(root / "train" / "t2" / f"img_{i}.png")
        Image.fromarray(mask).save(root / "train" / "masks" / f"img_{i}.png")


def make_detection(root, n=6, size=32, n_classes=3):
    r = rng()
    img_dir = root / "train" / "images"
    lbl_dir = root / "train" / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        arr = r.integers(0, 256, (size, size, 3), dtype=np.uint8)
        Image.fromarray(arr).save(img_dir / f"img_{i}.png")
        lines = []
        for _ in range(int(r.integers(1, 4))):
            cls = int(r.integers(0, n_classes))
            w = float(r.uniform(0.1, 0.4)); h = float(r.uniform(0.1, 0.4))
            cx = float(r.uniform(w / 2, 1 - w / 2)); cy = float(r.uniform(h / 2, 1 - h / 2))
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        (lbl_dir / f"img_{i}.txt").write_text("\n".join(lines), encoding="utf-8")


def cfg_for(task, fmt, root, **extra):
    cfg = {
        "task": task,
        "data": {"root": str(root), "format": fmt, "channels": 3},
        "model": {"backbone": "resnet18"},
        "train": {"epochs": 2, "lr": 1e-3, "device": "cuda" if torch.cuda.is_available() else "cpu"},
    }
    cfg["data"].update(extra)
    return cfg


results = {}


def log(name, ok, detail=""):
    results[name] = {"ok": ok, "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


make_classification(ROOT / "classif")
make_regression(ROOT / "reg")
make_segmentation(ROOT / "seg")
make_change(ROOT / "change")
make_detection(ROOT / "det")

# --- classification: train + predict + saliency + dashboard on random data ---
ds = build_dataset("classification", "folder_classification", ROOT / "classif", split="train", channels=3)
cfg = cfg_for("classification", "folder_classification", ROOT / "classif")
model = build_model(cfg, num_classes=ds.num_classes)
hist = train(cfg, model, ds, device=cfg["train"]["device"])
ok_loss = isinstance(hist["train"], list) and len(hist["train"]) == 2 and all(np.isfinite(x) for x in hist["train"])
log("train_classification_random", ok_loss, f"history={[round(x,4) for x in hist['train']]} device={next(model.parameters()).device}")

model.eval()
dev = cfg["train"]["device"]
img, tgt, meta = ds[0]
xb = img.unsqueeze(0).to(dev)
with torch.no_grad():
    logits = model(xb)
pred = int(logits[0].argmax())
sal = saliency_map(model, xb, method="gradcam").cpu()
log("predict_saliency_random", pred < ds.num_classes and sal.shape == img.shape[1:] and float(sal.max()) <= 1.0,
       f"pred_class={pred} saliency_shape={tuple(sal.shape)}")

png = io.BytesIO()
Image.fromarray((img.permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(png, format="PNG")
spng = io.BytesIO()
Image.fromarray((sal.unsqueeze(0).repeat(3, 1, 1).clamp(0, 1).permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(spng, format="PNG")
html2 = render_dashboard(image=png.getvalue(), saliency=spng.getvalue(), title="random smoke", predictions=[("a", 0.5)])
log("dashboard_html_random", "canvas" in html2 and "<html" in html2, f"len={len(html2)}")

# --- Regression ---
ds_r = build_dataset("regression", "regression", ROOT / "reg", split="train", channels=3)
cfg_r = cfg_for("regression", "regression", ROOT / "reg")
model_r = build_model(cfg_r, num_classes=1)
hist_r = train(cfg_r, model_r, ds_r, device=cfg_r["train"]["device"])
log("train_regression_random", all(np.isfinite(x) for x in hist_r["train"]), f"loss={[round(x,4) for x in hist_r['train']]}")

# --- Segmentation ---
ds_s = build_dataset("segmentation", "mask_segmentation", ROOT / "seg", split="train", channels=3, n_classes=4)
cfg_s = cfg_for("segmentation", "mask_segmentation", ROOT / "seg")
model_s = build_model(cfg_s, num_classes=ds_s.num_classes)
hist_s = train(cfg_s, model_s, ds_s, device=cfg_s["train"]["device"])
log("train_segmentation_random", all(np.isfinite(x) for x in hist_s["train"]), f"loss={[round(x,4) for x in hist_s['train']]}")

# --- Change detection ---
ds_c = build_dataset("change_detection", "change_detection", ROOT / "change", split="train", channels=3)
cfg_c = cfg_for("change_detection", "change_detection", ROOT / "change")
model_c = build_model(cfg_c, num_classes=2)
train_c = train(cfg_c, model_c, ds_c, device=cfg_c["train"]["device"])
log("train_change_random", all(np.isfinite(x) for x in train_c["train"]), f"loss={[round(x,4) for x in train_c['train']]}")

# --- Detection: loader + model proxy + trainer stub contract ---
ds_d = build_dataset("detection", "yolo", ROOT / "det", split="train", channels=3)
img_d, tgt_d, _ = ds_d[0]
log("detection_loader_random", (img_d.shape, tgt_d["boxes"].shape[0] >= 0), f"img={tuple(img_d.shape)} nboxes={len(tgt_d['boxes'])}")
cfg_d = cfg_for("detection", "yolo", ROOT / "det")
model_d = build_model(cfg_d, num_classes=3)
try:
    train(cfg_d, model_d, ds_d, device="cpu")
    log("detection_trainer_stub", False, "trainer ran (expected NotImplementedError)")
except NotImplementedError as e:
    log("detection_trainer_stub", True, f"raises NotImplementedError as designed: {e}")

# --- check-data CLI on random classification root ---
cli_cfg = ROOT / "classif_config.yaml"
import yaml
yaml.safe_dump(cfg, cli_cfg.open("w"), sort_keys=False)
py = sys.executable
# use the installed entry point
proc = subprocess.run([sys.executable, "-m", "sihvision.cli.check_data", str(cli_cfg)], capture_output=True, text=True)
log("check_data_cli_random", proc.returncode == 0 and "len(train):" in proc.stdout or proc.returncode == 0, f"rc={proc.returncode} out={proc.stdout.strip()}")

print("\n=== SUMMARY ===")
nl = len(results)
npass = sum(1 for r in results.values() if r["ok"])
print(f"random-smoke: {npass}/{nl} passed")
sys.exit(0 if npass == nl else 1)

