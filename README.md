# sihvision

**Config-driven satellite image recognition pipeline** for the Smart India
Hackathon (SIH). One package, one YAML config, five computer-vision tasks —
plus built-in explainable AI and a FastAPI/IoT inference service.

> Team doc: this README explains what the project is, what every file does,
> and which algorithms/data are used. Quick-start commands are at the bottom.

---

## 1. What is this project?

`sihvision` is a modular PyTorch library that reads satellite imagery, trains a
deep-learning model, serves predictions over HTTP, and explains *why* the model
decided what it decided (saliency heatmaps).

It targets the ISRO problem statements that look like an image-recognition fit:

| Statement | Task |
|---|---|
| **SS586** | Discover objects/features in satellite images using **Explainable AI** |
| **SS588** | Identify monuments from satellite imagery using DL + **XAI** |
| **SS591** | CNN for tropical cyclone intensity estimation from INSAT-3D IR images (regression) |

The problem statement is **not locked yet**, so everything is config-driven:
you change `task:` / `backbone:` / `data.root:` in a YAML file — no code changes.

### Supported tasks & dataset formats

| Task | Format string | Data layout |
|---|---|---|
| Classification | `folder_classification` | `root/{split}/{class}/*.png` |
| Object detection | `yolo` | `root/{split}/images/*.png` + `labels/*.txt` (YOLO xywh) |
| Segmentation | `mask_segmentation` | `root/{split}/images/` + `masks/` |
| Change detection | `change_detection` | `root/{split}/t1/` + `t2/` + `masks/` |
| Regression | `regression` | `root/{split}/images/` + `labels.csv` |

---

## 2. How it flows (what is happening)

```
config.yaml ──► config.py (validate)
                    │
                    ▼
data: build_dataset(task, format, root, split)
  loaders/ ──► (images, target, meta)      [per-sample contract]
  transforms.py ──► resize/normalize/augment
                    │
                    ▼
models/registry.py: build_model(cfg, n_classes)
  backbones.py (ResNet/EfficientNet/...) + heads.py (task head)
                    │
                    ▼
train.py: unified Trainer  ──► history (loss per epoch)
                    │
                    ▼
xai.py: saliency_map(model, image, method=gradcam|vanilla)
  ──► heatmap [H, W] in [0,1]
                    │
                    ▼
dashboard.py / api/app.py ──► HTML page or JSON envelope
```

**The per-sample contract** (every loader returns this):

- `images` — `Tensor[C,H,W]` float32 in [0,1], or `{"t1":…, "t2":…}` for change detection
- `targets` — class index (long), `{boxes, labels}` dict, mask `long[H,W]`, or scalar (regression)
- `meta` — `image_id`, `image_path`, `orig_size`, `channels`

---

## 3. File-by-file map

### Root
| File | Purpose |
|---|---|
| `pyproject.toml` | Packaging, dependencies, `check-data` CLI entry point, pytest config |
| `README.md` | This document |
| `.gitignore` | Excludes `.venv/`, caches, etc. |

### `sihvision/` — the library
| File | Purpose |
|---|---|
| `config.py` | YAML schema validation: tasks, formats, backbones, channels, split ratios, train params |
| `demo.py` | End-to-end demo: synthetic data → train → predict + saliency → `dashboard.html` |
| `train.py` | Unified `Trainer`: one loop for all tasks (CrossEntropy for class/seg/change, MSE for regression); detection raises `NotImplementedError` (YOLO trainer stub) |
| `xai.py` | `saliency_map()`: **Grad-CAM** and **vanilla gradients**; handles class/seg/change models (incl. t1/t2 dict input) |
| `dashboard.py` | `render_dashboard()`: self-contained HTML page with canvas saliency overlay + prediction bars |
| `__init__.py` | Package marker |

### `sihvision/data/`
| File | Purpose |
|---|---|
| `vision_dataset.py` | Abstract base class + the `(images, targets, meta)` contract |
| `images.py` | `load_image()`: reads 1/3/4-channel images (and >4-band TIFF via tifffile), normalizes to float32 [0,1], uint16→/65535 |
| `errors.py` | Typed exceptions (`MissingLabelError`, `LabelsMismatchError`, …) |
| `transforms.py` | torchvision-v2 pipelines per task (resize, normalize, flips/rotations); masks handled via `tv_tensors.Mask` |
| `split.py` | `split_dataset()`: ratio-split into train/val/test, or detects pre-split folders |
| `build.py` | `build_dataset(task, format, root, split)`: factory mapping (task, format) → loader class |
| `loaders/folder_classification.py` | Classes = subfolder names; `__getitem__` returns image + class index |
| `loaders/yolo_detection.py` | YOLO `.txt` labels → pixel-space xyxy boxes; empty labels → empty tensors |
| `loaders/mask_segmentation.py` | Paired `images/` + `masks/`; mask = class-id per pixel |
| `loaders/change_detection.py` | Bi-temporal `t1/` + `t2/` + change-mask triplets |
| `loaders/regression.py` | `labels.csv` (image_id,value) → float32 scalar target |
| `cli/check_data.py` | `check-data <config.yaml>`: build a dataset from config and print a summary |

### `sihvision/models/`
| File | Purpose |
|---|---|
| `backbones.py` | Feature extractors: **ResNet-18/34/50, EfficientNet-b0/b1, MobileNetV3-Small, VGG-11** (torchvision, `weights=None`). First conv is replaced so 1/3/4-channel inputs work |
| `heads.py` | Task heads: classification (pool+linear), regression (pool+linear→1), segmentation (1×1 conv + bilinear upsample), change detection (abs-difference of t1/t2 features) |
| `task_models.py` | Assembles backbone + head per task; change-detection model takes a dict input |
| `registry.py` | `build_model(cfg, num_classes)` — config → model; detection returns a YOLO proxy stub |
| `__init__.py` | Public exports |

### `sihvision/api/`
| File | Purpose |
|---|---|
| `app.py` | FastAPI app: `GET /health`, `POST /predict` (multipart, `?explain=true`), `POST /iot/predict` (raw bytes for edge devices), `GET /dashboard`. Standard JSON envelope: `{task, predictions, saliency, meta}` |

### `tests/`
| Path | Purpose |
|---|---|
| `fixtures/generate_synthetic.py` | Deterministic synthetic dataset generators (seeded RNG) for every format |
| `test_*.py` (20 files) | 129 tests covering config, loaders, transforms, split/build, backbones, heads, registry, trainer, XAI, dashboard, API, demo, CLI |

### `docs/`
| File | Purpose |
|---|---|
| `superpowers/specs/sihvision-implementation.md` | The formal implementation spec (architecture, config schema, contracts, gaps) |

---

## 4. Algorithms used

| Component | Algorithm |
|---|---|
| Backbones | ResNet-18/34/50, EfficientNet-b0/b1, MobileNetV3-Small, VGG-11 (torchvision, no pretrained weights — trained fresh) |
| Classification head | Adaptive-average-pool → Linear → class logits |
| Regression head | Adaptive-average-pool → Linear(1) → scalar (e.g. cyclone intensity) |
| Segmentation head | 1×1 conv over backbone features → bilinear upsample to input size |
| Change detection | Shared backbone encodes t1 and t2; **abs-diff** of features → 2-class change map (order-invariant by design) |
| Losses | CrossEntropy (classification, segmentation, change detection), MSE (regression) |
| Optimizer | Adam (default lr 1e-3, configurable) |
| **XAI saliency** | **Grad-CAM** (gradient-weighted activations of last conv, Selvaraju et al.) + **vanilla input-gradient**; per-task targeting (class logit / full segmentation map / change-magnitude) |
| Detection | Dataset + config support (YOLO format, `model_size`); the trainer is intentionally a stub until ultralytics YOLO is wired in |
| Hardware | CUDA 12.1 on RTX 3050 6GB; CPU fallback via `device: auto` |

---

## 5. Data used

- **Currently: synthetic only.** The demo and test suite generate small seeded
  datasets (32×32 px, few classes) — enough to prove the pipeline end-to-end.
- **Real data comes later:** once the SIH problem statement is locked, point
  `data.root` at the provided satellite imagery (INSAT-3D IR for SS591,
  any given rasters for SS586/588). No code changes needed.
- **Multi-spectral support:** 1 (grayscale), 3 (RGB), 4 (MSI: R,G,B,NIR) bands
  native; **>4-band TIFFs** load via tifffile with uint16 → [0,1] normalization.
- Standard formats (folder-class, YOLO, mask-PNG, change triplets, CSV labels)
  mean most public datasets (e.g. Potsdam/Vaihingen for segmentation, LEVIR-CD
  for change detection) can be dropped in with a tiny shim script.

---

## 6. Quick start (team)

```bash
# install (Python 3.11+)
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -e .

# GPU build (optional, replaces CPU wheels)
uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cu121 torch torchvision

# end-to-end demo: trains on synthetic data, writes dashboard.html
python -m sihvision.demo

# inspect any dataset from a config
check-data path/to/config.yaml

# serve the API
uvicorn sihvision.api.app:app        # /health /predict /iot/predict /dashboard

# run the test suite
python -m pytest -q                  # 129 tests
```

### Example config

```yaml
task: classification
data:
  root: ./data
  format: folder_classification
  channels: 3
  img_size: 256
  split_ratio: [0.7, 0.15, 0.15]
model:
  backbone: resnet18
train:
  lr: 0.001
  epochs: 30
  device: auto
```

### Example API call

```bash
curl -X POST "http://localhost:8000/predict?explain=true" \
     -F "file=@scene.png"
```

```json
{
  "task": "classification",
  "predictions": [{"class": "urban", "score": 0.91}],
  "saliency": {"method": "gradcam", "heatmap_b64": "<png>"},
  "meta": {"classes": ["water", "urban", "forest"], "device": "cuda"}
}
```

---

## 7. Roadmap / known gaps

- **Detection trainer** — dataset/config support exists; ultralytics YOLO training is the v0.2 stub
- **Pretrained weights** — currently `weights=None`; swap in ImageNet-pretrained when data volume demands it
- **Real data** — replace synthetic demo data once the PS is released
- **CI** — GitHub Actions runner for the 129-test suite