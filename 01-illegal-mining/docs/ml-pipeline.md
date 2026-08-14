# ML Pipeline

Three models + one deterministic fallback. The fallback guarantees a working end-to-end demo **with zero training data** — it is the hackathon-critical path and is always available.

## 1. Model (a) — Change Detection

| Parameter | Value |
|---|---|
| Architecture | U-Net, ResNet-18 encoder (ImageNet init for optical; SAR-only weights trained from scratch), 4 decoder stages |
| Input | 256×256 × 6 channel stack: [NDVI_t1, NDVI_t2, NDWI_t1, NDWI_t2, σ⁰_VH_t1, σ⁰_VH_t2] (z-scored per tile) |
| Output | Binary change mask (sigmoid) |
| Loss | **BCE + Dice (λ = 1.0)** |
| Optimizer / schedule | Adam, lr 1e-4, batch 16, 60 epochs, cosine decay |
| Chips | 256 × 256 |
| Acceptance gate | **IoU ≥ 0.60** on a 10% holdout of the paired-chip dataset |
| Post-processing | Connected components (8-connectivity); keep components ≥ 1,000 m² |

## 2. Model (b) — Excavation Segmentation

| Parameter | Value |
|---|---|
| Architecture | U-Net (ResNet-34) or DeepLabV3+ (ResNet-50) |
| Classes | `background`, `pit`, `exposed_soil`, `tailings`, `water_disturbance` |
| Input | 256×256 × 8 channel stack: [B2, B3, B4, B8, B11, B12, slope, SCL] (both dates) |
| Loss | **CrossEntropy + Dice (λ = 0.5)**, median-frequency class weighting |
| Optimizer / schedule | Adam, lr 1e-4, batch 16, 80 epochs, cosine decay |
| Chips | 256 × 256 |
| Acceptance gate | **mean IoU ≥ 0.55** over the 4 mining classes (background excluded) |

## 3. Model (c) — Equipment / Road Detection

| Parameter | Value |
|---|---|
| Architecture | **YOLOv8** (YOLO11 interchangeable), 1280×1280 input |
| Classes | `truck`, `excavator`, `temporary_structure`, `access_road` |
| Output | Boxes + confidence; NMS IoU 0.45, confidence floor 0.25 |
| Acceptance gate | **mAP@0.5 ≥ 0.50** |
| Augmentation | Mosaic, flips, 90° rotations, HSV jitter; speckle-noise injection when SAR (VH dB) is used |

## 4. Fallback Heuristic — Zero Training Data (Hackathon-Critical)

Runs when `MODEL_WEIGHTS_PATH` is empty (no GPU, first boot, or model download failure). Deterministic, ~2 s per tile, no weights required:

1. Compute deltas from the feature engine: `ΔNDVI`, `ΔNDWI`, `Δσ⁰_VH`.
2. Per-pixel change candidates where **any one** condition holds:
   - `ΔNDVI ≤ −0.15` (vegetation loss)
   - `Δσ⁰_VH ≥ +3 dB` (SAR backscatter jump)
   - `ΔNDWI ≤ −0.10` (water/wetness removal)
3. **Majority vote:** keep pixels satisfying **≥ 2 of 3** conditions.
4. **Morphology:** opening 3×3 (remove single-pixel speckle) → closing 3×3 (fill holes).
5. **Connected components** (8-connectivity); keep components **≥ 1,000 m² (0.1 ha)**.
6. Intersect with `slope > 8°` → excavation mask; intersect with `dist_river < 2,000 m` → riverbed-encroachment flag.
7. Emit detections in the identical schema as the models, with `source_model = "heuristic"` and `confidence` = fraction of conditions met (0.66 or 1.00).

The risk engine, database and API treat heuristic and model outputs identically; the dashboard shows a `source_model` badge for transparency.

## 5. Training-Data Requirements

| Model | Minimum data | Chip size | Augmentation |
|---|---|---|---|
| Change detection | **2,000 labelled T1/T2 pairs** (≥ 1,000 containing change) | 256×256 | Flips, 90° rotations, color jitter (optical); **Gamma speckle-noise injection, k = 4 looks** (SAR) |
| Excavation segmentation | **3,000 chips**, ≥ 300 per class | 256×256 | Flips, rotations, HSV jitter, class-balanced sampling |
| Equipment/road detection | **≥ 300 instances per class** (`truck`, `excavator`, `temporary_structure`, `access_road`) | 1280×1280 | Mosaic, flips, rotations, HSV jitter; speckle injection for SAR inputs |

Labels come from three sources: (1) field-confirmed alerts (alerting.md §4), (2) manually digitized reference chips from the pilot districts, (3) existing open change-detection datasets (OSCD, SEN12-CD) transferred for optical pairs.

## 6. Metrics Definitions

| Metric | Formula |
|---|---|
| IoU | `TP / (TP + FP + FN)` per class; mean over classes |
| Dice | `2·TP / (2·TP + FP + FN)` |
| BCE | `−1/N · Σ [ y·log(ŷ) + (1−y)·log(1−ŷ) ]` |
| CrossEntropy | `−1/N · Σ Σ_c y_c·log(p_c)` over classes |
| mAP@0.5 | mean over classes of average precision at IoU threshold 0.5 (PASCAL protocol) |
| Detection confidence | change/segmentation: mean sigmoid over polygon; YOLO: max box score; heuristic: vote fraction (0.66 / 1.00) |

## 7. Serving

- Training: offline nightly job on a GPU pod; acceptance gates above must pass before weights are promoted to `models/` in MinIO.
- Serving: ONNX / TorchScript exports, batch inference on the Celery worker (ml_engine service).
- Weights missing → fallback heuristic (§4). The API advertises the active source via `GET /health` (api-contract.md).