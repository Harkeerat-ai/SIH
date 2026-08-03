"""End-to-end demo: synthetic data -> train -> predict + saliency -> dashboard.

``run_demo`` returns a summary dict and writes ``out_dir/dashboard.html``.
"""

import io
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from sihvision.dashboard import render_dashboard
from sihvision.models.registry import build_model
from sihvision.train import train
from sihvision.xai import saliency_map

CLASSES = ["water", "urban", "forest"]
N_PER_CLASS = 6
IMG_SIZE = 32


def _make_data(root, n_per_class=N_PER_CLASS, img_size=IMG_SIZE):
    """Write a tiny synthetic classification dataset to ``root``."""
    rng = np.random.default_rng(7)
    for split in ("train",):
        for c, cls in enumerate(CLASSES):
            d = Path(root) / split / cls
            d.mkdir(parents=True, exist_ok=True)
            for i in range(n_per_class):
                base = rng.integers(0, 80, (img_size, img_size, 3), dtype=np.uint8)
                base[..., c] = 220  # class-discriminative channel
                arr = base + rng.integers(0, 40, base.shape, dtype=np.uint8)
                Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
                    d / f"img_{i}.png"
                )
    return Path(root)


def _probs_from_logits(logits, classes):
    probs = torch.softmax(logits[0], dim=0).tolist()
    return [(classes[i], float(p)) for i, p in enumerate(probs)]


def _image_to_png_bytes(tensor):
    """Convert [C,H,W] float tensor to PNG bytes."""
    arr = (tensor.clamp(0, 1).permute(1, 2, 0).numpy() * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def run_demo(root, out_dir, n_per_class=6, img_size=32, epochs=2, lr=1e-3,
             device="cpu"):
    """Run the full pipeline and write ``out_dir/dashboard.html``.

    Returns a dict with keys: history, prediction, saliency (tensor).
    """
    root = Path(root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _make_data(root, n_per_class=n_per_class, img_size=img_size)

    from sihvision.data.build import build_dataset

    ds = build_dataset(
        "classification", "folder_classification", root,
        split="train", channels=3,
    )

    cfg = {
        "task": "classification",
        "model": {"backbone": "resnet18"},
        "data": {"channels": 3},
        "train": {"epochs": epochs, "lr": lr, "device": device},
    }
    model = build_model(cfg, num_classes=len(CLASSES))
    history = train(cfg, model, ds, device=device)

    model.eval()
    img, _, meta = ds[0]
    img_batch = img.unsqueeze(0)
    with torch.no_grad():
        logits = model(img_batch)
    prediction = {
        "class": CLASSES[int(logits[0].argmax())],
        "probs": _probs_from_logits(logits, CLASSES),
        "image_id": meta["image_id"],
    }

    saliency = saliency_map(model, img_batch, method="gradcam")

    img_png = _image_to_png_bytes(img)
    saliency_png = _image_to_png_bytes(saliency.unsqueeze(0).repeat(3, 1, 1))
    html = render_dashboard(
        image=img_png,
        saliency=saliency_png,
        title=f"sihvision demo — {prediction['image_id']}",
        predictions=prediction["probs"],
    )
    (out_dir / "dashboard.html").write_text(html, encoding="utf-8")

    return {
        "history": history,
        "prediction": prediction,
        "saliency": saliency,
    }


if __name__ == "__main__":
    result = run_demo(
        root=Path("demo_data"),
        out_dir=Path("demo_out"),
        epochs=2,
    )
    print("demo finished:", result["prediction"]["class"])