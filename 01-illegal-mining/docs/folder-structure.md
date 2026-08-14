# Proposed Folder Structure (Implementation Phase)

This layout is the target for the build phase. Every directory maps one-to-one to a service boundary in architecture.md — nothing crosses service folders.

```
01-illegal-mining/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry point; mounts the api service routes
│   │   ├── config.py            Reads env vars (deployment.md §2) into typed settings
│   │   └── auth.py              District-scoped bearer-token auth for the API
│   └── src/services/
│       ├── ingestion/           Copernicus polling (06:00 UTC cron), cloud gate,
│       │                        STAC registration, upload to MinIO raw/
│       ├── preprocessing/       SAR (orbit→γ⁰→terrain→Lee 5×5→dB) and optical
│       │                        (s2cloudless→sen2cor→10 m UTM grid) workers
│       ├── feature_engine/      NDVI/NDWI/Δσ⁰/D(x)/distances/vegetation-loss and
│       │                        excavation-indicator rasters (feature-engineering.md)
│       ├── ml_engine/           Model serving (ONNX/TorchScript) + heuristic
│       │                        fallback; writes predictions/ (ml-pipeline.md)
│       ├── risk_engine/         Weighted scoring, permit suppression, 14-day dedup,
│       │                        expansion tracking (decision-engine.md)
│       ├── alerting/            Lifecycle state machine, SMS/email/digest dispatch,
│       │                        retraining-label export (alerting.md)
│       └── api/                 REST endpoints — 1:1 with api-contract.md
├── ml/
│   └── models/
│       ├── change_detection/    U-Net ResNet-18, BCE+Dice, IoU ≥ 0.60 gate
│       ├── segmentation/        U-Net / DeepLabV3+ 5-class, IoU ≥ 0.55 gate
│       └── detection/           YOLOv8 equipment/road, mAP@0.5 ≥ 0.50 gate
├── data/
│   ├── raw/                     Mirrors MinIO layout (data-acquisition.md §3):
│   │                            sentinel1/ sentinel2/ dem/ vectors/
│   ├── processed/               sar/ optical/ indices/ (10 m UTM GeoTIFFs)
│   ├── predictions/             segmentation/ objects/ alerts/
│   └── models/                  Promoted weights served by ml_engine
├── web/
│   └── dashboard/               React + MapLibre GL single-page app
│                                (dashboard-spec.md)
└── infra/
    ├── docker-compose.yml       Service stack (deployment.md §1)
    ├── db/
    │   └── init.sql             PostGIS schema (database-schema.md) + seed districts
    └── celery/
        ├── beat-schedule.py     06:00 UTC ingest cron + daily digest job
        └── worker-config.py     Queues: preprocess, features, ml, risk, alert
```

Conventions: one Celery queue per service (`preprocess`, `features`, `ml`, `risk`, `alert`); task chains keyed by `(granule_id, tile)` for idempotency; every service reads config exclusively through `app/config.py`; tests live alongside each service folder and are run per service.