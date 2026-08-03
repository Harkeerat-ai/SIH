# sihvision

Config-driven satellite image recognition pipeline for Smart India Hackathon.

One package, one config, many tasks:

- **Classification** — folder layout, ResNet/EfficientNet/MobileNet/VGG backbones
- **Object detection** — YOLO-format labels (ultralytics trainer, stub in v0.1)
- **Segmentation** — mask-PNG datasets, FCN head on conv backbones
- **Change detection** — bi-temporal t1/t2 + change mask (abs-diff head)
- **Regression** — images + `labels.csv` → scalar target (e.g. cyclone intensity)

Plus built-in **explainability**: Grad-CAM / vanilla saliency heatmaps and a
self-contained HTML explainability dashboard, and a **FastAPI + IoT** inference
service with a standard JSON prediction envelope.

## Install

```bash
uv sync                          # or: pip install -e .
uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cu121 torch torchvision
```

Requires Python 3.11+. A single 3-channel RGB / 4-channel MSI input is
supported by every backbone (first conv is adapted automatically).

## Quick start

```bash
# inspect a dataset from a config
check-data configs/demo.yaml

# end-to-end demo: synthetic data -> train -> saliency -> dashboard.html
python -m sihvision.demo
```

## Predictions + API

```bash
uvicorn sihvision.api.app:app    # /health  /predict  /iot/predict  /dashboard
```

POST an image:

```json
POST /predict?explain=true   (multipart "file")
{
  "task": "classification",
  "predictions": [{"class": "urban", "score": 0.91}, ...],
  "saliency": {"method": "gradcam", "heatmap_b64": "..."},
  "meta": {"classes": [...], "device": "cuda"}
}
```

`/iot/predict` accepts raw PNG bytes for edge devices/cameras.

## Config

```yaml
task: classification
data:
  root: /path/to/data
  format: folder_classification   # folder_classification|yolo|mask_segmentation|change_detection|regression
  channels: 3                     # 1 | 3 | 4
  img_size: 256
  split_ratio: [0.7, 0.15, 0.15]
model:
  backbone: resnet18              # resnet18/34/50, efficientnet_b0/b1, mobilenet_v3_small, vgg11
train:
  lr: 0.001
  epochs: 30
  device: auto                    # auto | cpu | cuda | mps
```

Dataset formats:

- classification: `root/{split}/{class}/*.png`
- detection: `root/{split}/images/*.png` + `root/{split}/labels/*.txt` (YOLO)
- segmentation / change_detection: `root/{split}/images|masks` (+`t1`/`t2`)
- regression: `root/{split}/images/*.png` + `root/{split}/labels.csv`

## Tests

```bash
python -m pytest -q     # 129 tests
```

## Roadmap

- Detection trainer via ultralytics YOLO (v0.2)
- Tune for real ISRO problem statements (SS586/588/591)
- CI + GitHub remote for team