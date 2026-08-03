"""FastAPI prediction service for sihvision.

Standard JSON envelope for every prediction endpoint::

    {
      "task": "classification",
      "predictions": [{"class": "urban", "score": 0.91}, ...],
      "saliency": {"method": "gradcam", "heatmap_b64": "..."} | null,
      "meta": {"classes": [...], "device": "cpu"}
    }

Endpoints:

- ``GET  /health``          liveness probe
- ``POST /predict``         multipart image upload (``explain=true`` query)
- ``POST /iot/predict``     raw PNG bytes (tiny payloads for edge devices)
- ``GET  /dashboard``       explainability dashboard HTML page
"""

import base64
import io

import numpy as np
import torch
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from sihvision.dashboard import render_dashboard
from sihvision.models.registry import build_model
from sihvision.xai import saliency_map

_TASK = None
_MODEL = None
_CLASSES = None
_DEVICE = None


def register_model(cfg_path, classes):
    """Load config and build the model into module-level inference state."""
    import yaml

    global _TASK, _MODEL, _CLASSES, _DEVICE
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _TASK = cfg["task"]
    _MODEL = build_model(cfg, num_classes=len(classes))
    _MODEL.eval()
    _CLASSES = list(classes)
    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    _MODEL.to(_DEVICE)
    return _MODEL


def _decode_png(raw):
    """Decode PNG bytes to [1, C, H, W] float32 [0,1]."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor


def _top_predictions(probs, k=5):
    idx = probs.argsort(descending=True)[:k]
    return [
        {"class": _CLASSES[i] if i < len(_CLASSES) else str(i), "score": float(probs[i])}
        for i in idx.tolist()
    ]


def _envelope(raw, explain=False):
    img = _decode_png(raw).to(_DEVICE)
    with torch.no_grad():
        logits = _MODEL(img)
    probs = torch.softmax(logits[0], dim=0).cpu()
    body = {
        "task": _TASK,
        "predictions": _top_predictions(probs),
        "saliency": None,
        "meta": {"classes": _CLASSES, "device": _DEVICE},
    }
    if explain:
        try:
            hm = saliency_map(_MODEL, img, method="gradcam")
            png = _heatmap_to_png(hm, img[0].cpu())
            body["saliency"] = {
                "method": "gradcam",
                "heatmap_b64": base64.b64encode(png).decode("ascii"),
            }
        except Exception as exc:  # pragma: no cover
            body["saliency"] = {"method": "gradcam", "error": str(exc)}
    return body


def _heatmap_to_png(heatmap, image):
    """Overlay heatmap onto image and return PNG bytes."""
    heatmap = heatmap.detach().cpu()
    cm = torch.tensor(
        [
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=torch.float32,
    )  # blue->green->red
    idx = (heatmap * 2).clamp(0, 2).long()
    frac = (heatmap * 2) - idx.float()
    c1 = cm[idx]
    c2 = cm[(idx + 1).clamp(max=2)]
    overlay = c1 * (1 - frac[..., None]) + c2 * frac[..., None]  # [H,W,3]
    blended = 0.5 * image.permute(1, 2, 0).cpu() + 0.5 * overlay
    arr = (blended.clamp(0, 1).numpy() * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def create_app():
    app = FastAPI(title="sihvision inference")

    @app.get("/health")
    def health():
        return {"status": "ok", "model_loaded": _MODEL is not None}

    @app.post("/predict")
    async def predict(file: UploadFile = File(...), explain: bool = False):
        if _MODEL is None:
            return JSONResponse({"error": "no model registered"}, status_code=503)
        raw = await file.read()
        return _envelope(raw, explain=explain)

    @app.post("/iot/predict")
    async def iot_predict(request: Request):
        if _MODEL is None:
            return JSONResponse({"error": "no model registered"}, status_code=503)
        raw = await request.body()
        try:
            _decode_png(raw)
        except Exception:
            return JSONResponse(
                {"error": "invalid or unsupported image bytes"}, status_code=400
            )
        return _envelope(raw, explain=False)

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        return render_dashboard(image=b"")

    return app