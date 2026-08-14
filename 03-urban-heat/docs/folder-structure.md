# Folder structure

```
03-urban-heat/
├── README.md
├── docs/                          # this documentation set (14 files)
├── backend/
│   └── src/services/
│       ├── ingestion/             # STAC discovery, download, cloud masking, raw COG writes to MinIO
│       ├── lst/                   # LST engine: DN → radiance → brightness temperature → emissivity → LST; split-window fallback
│       ├── features/              # NDVI/NDBI/NDWI band algebra, impervious surface, zone statistics
│       ├── vulnerability/         # transparent weighted composite scoring, tiering, factor_breakdown JSONB
│       ├── optimizer/             # knapsack/greedy cost-benefit allocation: max Σ(ΔLST × population) ≤ budget
│       ├── simulator/             # slider re-runs of optimizer formulas; "estimate"-flagged outputs
│       └── api/                   # FastAPI routers: ingest, zones, heat-profile, vulnerability, hotspots, simulate, optimize, dashboard, plans
├── ml/
│   ├── training/                  # U-Net land-cover training on S2 4-band tiles; IoU ≥ 0.70 promotion gate
│   └── inference/                 # ONNX land-cover inference service; threshold-fallback classifier
├── web/
│   └── dashboard/                 # React + MapLibre GL planning dashboard: GIS heat map, KPI bar, zone drawer, simulator panel
└── infra/
    ├── docker/                    # docker-compose: postgis, minio, redis, celery, fastapi, frontend
    ├── sql/                       # schema.sql (docs/database-schema.md) and migrations
    └── terraform/                 # deployment-time infrastructure: buckets, networking, monitoring
```

## Per-directory responsibility

| Path | Responsibility |
|---|---|
| `backend/src/services/ingestion/` | STAC queries, scene download, cloud masking, writing raw COGs to the data lake |
| `backend/src/services/lst/` | Radiometric calibration and LST derivation (docs/lst-engine.md), including MODIS/SLSTR split-window fallback |
| `backend/src/services/features/` | Index computation (docs/feature-engineering.md), land-cover application, per-zone statistics |
| `backend/src/services/vulnerability/` | Weighted-composite scoring (docs/decision-engine.md) — transparent, no deep learning |
| `backend/src/services/optimizer/` | Cost-benefit knapsack/greedy allocation (docs/intervention-optimizer.md) under budget and capacity caps |
| `backend/src/services/simulator/` | "What-if" re-runs of optimizer formulas with slider inputs (docs/simulator.md) |
| `backend/src/services/api/` | HTTP layer implementing docs/api-contract.md; validation, auth, error envelopes |
| `ml/training/` | U-Net training pipeline, dataset management, IoU evaluation against the 0.70 gate |
| `ml/inference/` | Land-cover inference serving (ONNX) plus the zero-training threshold fallback |
| `web/dashboard/` | GIS heat map, KPI bar, zone drawer, simulator panel, plan generation (docs/dashboard-spec.md) |
| `infra/docker/` | Container orchestration, health checks, volume layout (docs/deployment.md) |
| `infra/sql/` | Schema definition and versioned migrations |
| `infra/terraform/` | Provisioning of object storage, networking, and monitoring for deployment |

## Dependency direction

`api → (ingestion, lst, features, vulnerability, optimizer, simulator) → (postgis, minio)`. `web → api` only. `ml/inference → (minio, postgis)`. No circular imports; services communicate exclusively through the API layer and the data lake (docs/architecture.md).