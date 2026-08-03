# sihvision — implementation spec

Status: **implemented (Phases 0–6 complete, 129 tests passing)**

Goal: a config-driven satellite image recognition pipeline for SIH covering
classification, detection, segmentation, change detection and regression,
with XAI saliency and a FastAPI/IoT service.

## Target problem statements

- **SS586** — discover objects/features in satellite images using Explainable AI
- **SS588** — identify monuments from satellite imagery using deep learning + XAI
- **SS591** — CNN for tropical cyclone intensity estimation from INSAT-3D IR
- Fallback radar: flood mapping, crop health, deforestation from 8-PS report

## User constraints (locked in earlier sessions)

- Python + PyTorch only, local dev on Windows + RTX 3050 6GB (CUDA 12.1, torch 2.5.1+cu121)
- Runtime must work on CPU too (shared/tiny GPU) -> device auto-detect
- No huge pretrained weights in repo; models instantiated fresh (weights=None),
  download-on-use deferred
- REST API integration; standard JSON prediction envelope
- XAI is a first-class requirement (ISRO statements demand explainability)
- IoT-reachable inference was requested, so raw-bytes endpoint included
- Problem statements may change -> everything config-driven, no hardcoded tasks

## Architecture

```
sihvision/
  config.py        config.yaml validation (tasks, formats, backbones, channels)
  data/
    vision_dataset.py  (images, targets, meta) contract
    images.py          load_image: 1/3/4/>4 channels, float32 [0,1], uint16->/65535
    errors.py          typed dataset errors
    transforms.py      torchvision v2 compose per task (tv_tensors.Mask)
    split.py           ratio split or per-split layout
    build.py           (task, format) -> loader factory
    loaders/           folder_classification, yolo_detection, mask_segmentation,
                       change_detection, regression
    cli/check_data.py  check-data <config.yaml> summary CLI
  models/
    backbones.py       resnet18/34/50, efficientnet_b0/b1, mobilenet_v3_small,
                       vgg11; first conv adapted for 1/3/4-channel input
    heads.py           classification, regression, segmentation (1x1 + upsample),
                       change-detect (abs-diff of features)
  task_models.py       backbone + head per task, dict input for change detection
  registry.py          build_model(cfg, num_classes) keyed by task
  train.py             unified trainer (CE for class/seg/change, MSE for reg)
                       detection -> NotImplementedError (YOLO trainer stub)
  xai.py               saliency_map(model, image, method=gradcam|vanilla)
                       handles tensor + change-detect dict input
  dashboard.py         render_dashboard(): self-contained HTML w/ canvas overlay
  api/app.py           FastAPI: /health, /predict, /iot/predict, /dashboard
  demo.py              end-to-end demo: synthetic -> train -> saliency -> HTML

## Config schema

```yaml
task: classification            # classification|detection|segmentation|
                                # change_detection|regression
data:
  root: <path>
  format: folder_classification # folder_classification|yolo|mask_segmentation|
                                # change_detection|regression
  channels: 3                   # 1|3|4
  img_size: 256
  split_ratio: [0.7, 0.15, 0.15]
model:
  backbone: resnet18
train:
  lr: 0.001
  epochs: 30
  device: auto                  # auto|cpu|cuda|mps
  yolo: {model_size: n}         # detection only
```

## Dataset layout

- classification : root/{split}/{class}/*.png
- detection      : root/{split}/images/*.png + labels/*.txt (YOLO xywh)
- segmentation   : root/{split}/images + root/{split}/masks
- change_detection : root/{split}/t1 + t2 + masks
- regression     : root/{split}/images + labels.csv (image_id,value)

Contract per `__getitem__`:
`(images, target, meta)` where images = tensor [C,H,W] or {"t1","t2"} dict.
Targets: cls -> long scalar; det -> {boxes,xyxy],[labels]}; seg/change -> long
[H,W]; regression -> float scalar. meta has image_id, orig_size, channels.

## Prediction envelope (API)

```json
{
  "task": "classification",
  "predictions": [{"class": "urban", "score": 0.91}],
  "saliency": {"method": "gradcam", "heatmap_b64": "<png>"},
  "meta": {"classes": [...], "device": "cuda"}
}
```

IoT endpoint: POST raw PNG bytes -> same envelope, no saliency by default.

## Standard commands

- Tests: `python -m pytest -q`
- Demo: `python -m sihvision.demo`
- API: `uvicorn sihvision.api.app:app`
- Check data: `check-data <config.yaml>`

## Known gaps (post-v0.1)

- Detection waiting: train via ultralytics YOLO (registry returns proxy; train() raises explicitly)
- Dashboard image upload API does not feed real model yet (route is static)
- No pretrained weights loaded (weights=None); fine for synthetic/tiny data

## Definition of done

- Test suite green (129 tests) at every phase
- Loaders fail loudly and early (constructor-time verification)
- Runs on any device auto-detected
- Final run: `uv pip sync` reproducibility