# System Architecture

## 1. Service Boundaries

```
                    EXTERNAL SOURCES
   Sentinel-2 L2A   Sentinel-1 GRD   IMD rainfall   ERA5 temps   PMFBY registry
        │                │                │             │             │
        └───────┬────────┴────────┬───────┴──────┬──────┴─────────────┘
                ▼                 ▼              ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ INGESTION (nightly 02:00 UTC)                                      │
   │ STAC query · cloud-cover gate ≥ 80% skip · raw lake writes (MinIO) │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ PREPROCESSING                                                      │
   │ s2cloudless + QA60 cloud mask · resample to 10 m UTM               │
   │ S1 radiometric calibration · terrain correction · Lee filter       │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ FIELD ENGINE                                                       │
   │ clip scene to plot polygons (PostGIS) · zonal statistics           │
   │ only on cloud-free pixels · ≥ 30% valid-pixel gate                 │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ TIME-SERIES ENGINE                                                 │
   │ append satellite_stats rows (TimescaleDB hypertable)               │
   │ assemble per-plot NDVI / NDMI / EVI curve statistics               │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ BASELINE ENGINE                                                    │
   │ (crop, district, season) p5 / p50 / p95 envelope, ≥ 3 years        │
   │ anomaly rule: observed < p5 for 2 consecutive cloud-free passes    │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ DAMAGE DETECTOR + LOSS ESTIMATOR (ML)                              │
   │ XGBoost, exactly 12 features                                       │
   │ outputs: damage_probability (0–1), estimated_yield_loss_pct        │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ CLAIM ENGINE (RULES — ML never pays out directly)                  │
   │ REJECT · AUTO_REJECT · FIELD_VERIFICATION · AUTO_APPROVE (rec.)    │
   │ builds 12-field evidence package · SAR confirmation gate           │
   └──────────────────────────────────┬─────────────────────────────────┘
                                      ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ SURFACES                                                           │
   │ Insurer web dashboard (Next.js) · Farmer app (React Native)        │
   │ REST API (FastAPI) · evidence viewer · human sign-off workflow     │
   └────────────────────────────────────────────────────────────────────┘
```

## 2. Component Responsibility Table

| # | Component | Responsibility | Data Out |
|---|-----------|----------------|----------|
| 1 | `ingestion` | Nightly STAC/S1/IMD/ERA5 pulls; scene validation; cloud-cover gate (≥ 80% skip); raw lake writes | `raw/*` in MinIO |
| 2 | `preprocessing` | Cloud mask (s2cloudless + QA60); resample to 10 m UTM; S1 calibration, terrain correction, 5×5 Lee filter | Cloud masks, index GeoTIFFs |
| 3 | `field_engine` | Clip to plot polygons; zonal stats on cloud-free pixels; ≥ 30% valid-pixel gate → `insufficient_data` flag | `zonal-stats/*.parquet` |
| 4 | `timeseries` | Append `satellite_stats` rows; compute curve statistics (slope, min, mean-of-last-3) | `satellite_stats` hypertable |
| 5 | `baseline` | Build (crop, district, season) p5/p50/p95 envelopes from ≥ 3 years; fire anomaly on 2 consecutive below-p5 acquisitions | `baselines` table, anomaly flags |
| 6 | `damage_model` | XGBoost inference on exactly 12 features → `damage_probability`, `estimated_yield_loss_pct` | Inference rows |
| 7 | `claims` | Claim lifecycle; evidence-package assembly; liability estimate ₹ | `claims`, `evidence_packages` |
| 8 | `rules_engine` | Map inference + policy terms + SAR gate → REJECT / AUTO_REJECT / FIELD_VERIFICATION / AUTO_APPROVE (recommendation only) | `claim_decisions` input |
| 9 | `api` | REST surfaces for web/mobile/insurer; JWT auth; validation (400/404/422/500) | HTTP |
| 10 | `web` / `mobile` | Insurer dashboard; farmer app (React Native) | UI |

## 3. Data Flow — Nightly Run (02:00 UTC)

1. **02:00** — Cron fires `ingestion`: STAC query for S2 L2A granules over the AOI with
   `eo:cloud_cover < 80`.
2. **02:05** — New scene staged; cloud mask applied (s2cloudless prob < 0.4 + QA60 clean).
   Per-scene cloud cover ≥ 80% → scene skipped.
3. **02:15** — NDVI/NDMI/EVI computed, all bands resampled to 10 m UTM.
4. **02:30** — `field_engine` clips the scene to 200,000 plot polygons; zonal statistics on
   cloud-free pixels only; plots with < 30% valid pixels → `insufficient_data`, no stats row.
5. **02:45** — Valid stats appended to `satellite_stats` (TimescaleDB hypertable).
6. **03:00** — `timeseries` recomputes curve statistics; `baseline` checks the envelope:
   observed NDVI < p5 for 2 consecutive cloud-free acquisitions → anomaly triggered.
7. **03:10** — `damage_model` inference: 12 features → `damage_probability = 0.83`,
   `estimated_yield_loss_pct = 44`.
8. **03:15** — `rules_engine`: policy ACTIVE ✓, loss 44% > 40% ✓, prob 0.83 > 0.8 ✓ — but
   SAR moisture anomaly NOT confirmed → recommendation `FIELD_VERIFICATION` (priority HIGH).
9. **03:20** — 12-field evidence package written to `evidence_packages`; insurer dashboard
   updated; farmer app push notification sent.
10. **08:00** — Insurer reviews the queue, opens the evidence package, signs off; payout
    proceeds through the banking core.

## 4. Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| ML never pays | The rules engine maps model outputs to recommendations; only a human authority sign-off triggers payout — hard requirement. |
| TimescaleDB hypertable for `satellite_stats` | Time-series joins with PostGIS plot polygons; 7-day chunks; 14.6 M rows/year at 10k km². |
| MinIO object store + Parquet zonal stats | Cheap imagery retention (~78 GB/year); columnar stats for fast model feature assembly. |
| Celery workers, idempotent by `(scene_id, acquisition_date)` | Nightly pipeline retries safely; dead-letter queue for poison messages. |
| SAR only as confirmation | Sentinel-1 suffers decorrelation in wet conditions; it confirms — never triggers — damage. |