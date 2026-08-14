# ML pipeline

Two models exist in this system. One is optional and one is mandatory:

1. **Land-cover segmentation (U-Net)** — optional, trainable, gated on IoU ≥ 0.70. Provides builtup_pct, vegetation_pct, water_share from semantic classes.
2. **Vulnerability model** — mandatory, deliberately NOT deep learning. It is a transparent weighted composite whose per-factor breakdown is stored and displayed (docs/decision-engine.md).

## (a) Land-cover segmentation — U-Net over Sentinel-2

| Attribute | Value |
|---|---|
| Architecture | U-Net, encoder stages 16→32→64→128→256 channels, decoder 4 stages, skip connections, final 1×1 conv → 6 logits, softmax |
| Input | 256×256×4 tiles — S2 B2, B3, B4, B8 (10 m), normalized to 0–1 |
| Classes | {building, road, tree, grass, bare_soil, water} |
| Loss | 0.5·CrossEntropy + 0.5·Dice |
| Optimizer / schedule | Adam, lr 1e−4, no decay; batch 16; 60 epochs |
| Training data | 500 labelled 256×256 tiles from 10 Indian cities (8,000 labelled buildings, 6,000 road segments), split 80/10/10 train/val/test |
| Augmentation | horizontal/vertical flips, 90° rotations, brightness jitter ±10 % |
| Promotion gate | per-class IoU on held-out test set: building ≥ 0.70, road ≥ 0.60, tree ≥ 0.70, grass ≥ 0.65, bare_soil ≥ 0.60, water ≥ 0.75; overall IoU ≥ 0.70 |
| Inference cadence | quarterly re-run on new S2 stacks; on-demand after ingestion |

Segmentation outputs feed `builtup_pct` (building + road), `vegetation_pct` (tree + grass), and `water_share` (water).

## (b) Vulnerability model — transparent weighted composite

- **No deep learning.** The score is a weighted sum of 7 normalized factors with fixed weights (0.40, 0.20, 0.15, 0.10, 0.05, 0.05, 0.05); the exact formula, tiering, and worked example are in docs/decision-engine.md.
- Every score row persists `factor_breakdown` as JSONB — the contribution of each factor — so the dashboard can show *why* a zone scored 87.
- Runtime: a single SQL/NumPy pass over zone statistics. No GPU, no retraining, no weights in a model registry.

## (c) Fallback with zero training data

When no segmentation model is available (cold start), built-up classification uses pixel thresholds:

```
built-up pixel ⇔ (NDBI > 0.1) AND (NDVI < 0.15)
```

The complete threshold fallback set:

| Class | Rule |
|---|---|
| built_up | NDBI > 0.1 AND NDVI < 0.15 |
| vegetation | NDVI ≥ 0.30 |
| water | NDWI > 0 |
| bare_soil | NDVI < 0.15 AND NDBI ≤ 0.1 |
| road | OSM road buffers (10 m) not already built_up |

Rows derived this way carry `confidence = "threshold_fallback"`; the dashboard shows a banner when a zone's builtup_pct comes from the fallback rather than segmentation.

## Model registry

| Model | Version | Artifact | Gate |
|---|---|---|---|
| landcover-unet | v1.0.0 | ONNX, input 256×256×4, 6 classes | test IoU 0.71 (July 2026) |
| vulnerability composite | v1 (frozen formula) | SQL view + Python weights table | reviewed by domain team; weights locked |
