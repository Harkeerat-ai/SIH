# System Architecture

## 1. Overview

Seven services form a strict one-way pipeline: **ingest → preprocessing → feature engine → AI engine → risk engine → alerting → dashboard**. Each service is independently deployable, communicates only through the shared data lake (MinIO S3), the queue (Redis/Celery) and PostGIS, and has a single, explicit responsibility. The pipeline is scheduled by Celery Beat at **06:00 UTC daily**; processing is idempotent per (product, tile, acquisition).

## 2. Architecture Diagram

```
                        EXTERNAL DATA SOURCES
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐
   │ Sentinel-1   │  │ Sentinel-2   │  │ Govt lease   │  │ OSM · CWC ·   │
   │ IW GRD (SAR) │  │ L2A (optical)│  │ permits,     │  │ FSI boundary  │
   │ 12-day       │  │ 5-day        │  │ forest,      │  │ river vectors │
   │              │  │              │  │ river maps   │  │               │
   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘
          │                 │                 │                  │
          ▼                 ▼                 ▼                  ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 1. INGESTION      poll 06:00 UTC cron · cloud-cover gate (≤ 30%) ·   │
   │                   STAC registration · upload raw/ to MinIO           │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 2. PREPROCESSING   S1: orbit → γ⁰ calib → terrain corr → Lee 5×5 →  │
   │                    dB   S2: s2cloudless → (L1C corr) → 10 m UTM grid │
   │                    DEM: slope · aspect                               │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 3. FEATURE ENGINE  NDVI · NDWI · Δσ⁰ · D(x) · veg-loss mask ·        │
   │                    excavation indicator · dist-to-river/boundary     │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 4. AI ENGINE       (a) U-Net change detection  (b) 5-class           │
   │                       excavation segmentation  (c) YOLOv8 equipment/ │
   │                       road detection           + heuristic fallback  │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 5. RISK ENGINE     7 weighted factors → score 0–100 → tier ·         │
   │                    permit suppression · 14-day dedup · expansion     │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 6. ALERTING        state machine OPEN → ASSIGNED → FIELD_VERIFIED →  │
   │                    CONFIRMED|DISMISSED · SMS · email · daily digest  │
   └────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 7. DASHBOARD       map layers · alert panel · comparison viewer ·    │
   │                    verification workflow · inspection report         │
   └──────────────────────────────────────────────────────────────────────┘

                        SHARED INFRASTRUCTURE
   ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────────┐
   │ PostGIS 16    │  │ MinIO (S3)    │  │ Redis 7      │  │ Celery + Beat │
   │ alerts,       │  │ raw/ proc/    │  │ queues,      │  │ cron 06:00 UTC│
   │ permits,      │  │ pred/ models/ │  │ results, DLQ │  │ orchestration │
   │ officers      │  │               │  │              │  │               │
   └───────────────┘  └───────────────┘  └──────────────┘  └───────────────┘
```

## 3. Component Responsibility Table

| Component | Responsibility | Key inputs | Outputs |
|---|---|---|---|
| Ingest | Poll Copernicus APIs on the 06:00 UTC cron, gate on cloud cover, register scenes as STAC items, upload raw objects | Sentinel-1 IW GRD, Sentinel-2 L2A granules; DEM, boundary and permit files | `raw/` objects, STAC items, ingest receipts (`ing_*`) |
| Preprocessing | Deterministic SAR / optical / DEM processing onto the shared 10 m UTM grid | Raw granules + precise orbit files + GLO-30 | `processed/` GeoTIFFs (dB SAR, 10 m surface reflectance, SCL, slope, aspect) |
| Feature engine | Compute index rasters, temporal deltas, geodesic distances, vegetation-loss and excavation indicators | Processed stacks (T1, T2) + boundary vectors | `indices/` rasters, feature tensors for the AI engine |
| AI engine | Change mask, 5-class excavation segmentation, equipment/road boxes; deterministic heuristic fallback when weights absent | Feature tensors, T1/T2 chips, model weights from MinIO | `predictions/` masks, object GeoJSON, per-polygon confidence |
| Risk engine | 7-factor weighted score → tier, permit suppression, 14-day dedup, expansion-rate tracking | Predictions + permits + boundaries | `alert_groups` and `risk_factors` rows in PostGIS |
| Alerting | Lifecycle state machine, channel dispatch, escalation by tier | Risk rows, officer registry, SMTP/SMS credentials | SMS, email, daily digest, dashboard feed events |
| Dashboard | Map rendering, alert detail panel, image comparison, verification workflow, inspection report | PostGIS + REST API | Operator actions: assign, verify, confirm/dismiss, report PDF |

## 4. Data-Flow Sequence: Ingest → Predict → Decide → Act

Worked scenario (identical inputs to the decision-engine worked example → **risk 87**):

| # | Step | Service | Detail |
|---|---|---|---|
| 1 | Trigger | Celery Beat | Cron 06:00 UTC — request all scenes acquired since the last run for monitored districts |
| 2 | Ingest | Ingest | Sentinel-2 L2A tile **44QND**, cloud 8.4% ≤ 30% → accepted; STAC item registered; SAFE uploaded to `raw/sentinel2/` |
| 3 | Preprocess | Preprocessing | s2cloudless mask; bilinear resample to 10 m, EPSG:32644; T1 = 05-Jul, T2 = 12-Jul stacks written to `processed/optical/` |
| 4 | Feature | Feature engine | ΔNDVI = −0.22, ΔNDWI = −0.14, Δσ⁰_VH = +4.1 dB (from 05-Jul S1 scene), slope 12°, river distance 85 m |
| 5 | Predict | AI engine | Change mask (holdout IoU 0.64) → 2.0 ha polygon; segmentation classes pit + exposed_soil; YOLO: 1 excavator, 2 trucks |
| 6 | Decide | Risk engine | 7 factors → **87 → HIGH**; no valid permit → no suppression; no intersecting open group in 14-day window → new alert |
| 7 | Act | Alerting | `alert_groups` row `status=open`, `risk_score=87`; SMS to district officer + email to Deputy Director within 1 minute |
| 8 | Close loop | Dashboard | Officer assigns → verifies → CONFIRMED; polygon appended to retraining set; repeat within 14 days suppressed |

**Degraded sequence:** if `MODEL_WEIGHTS_PATH` is empty (first boot, no GPU), steps 5 runs the index-differencing heuristic (see ml-pipeline.md) — steps 6–8 are unchanged, so the demo works with zero trained weights.