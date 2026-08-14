# Hyper-Local Crop Health & Automated Micro-Insurance Engine

**Smart India Hackathon 2026 · Geospatial AI · Plot-level digital insurance verification**

## Problem Statement

Pradhan Mantri Fasal Bima Yojana (PMFBY) and similar crop-insurance schemes rely on
**crop-cutting experiments (CCEs)** — a slow, expensive, and statistically thin sampling
method — to verify yield loss. CCEs cover a small fraction of insured plots, are prone to
local bias, and typically take 30–60 days to settle a claim. The result: delayed payouts,
disputed assessments, and low farmer trust.

We replace the "wait for a CCE" bottleneck with **plot-level satellite verification**:

1. Every insured plot is registered as a polygon (PostGIS).
2. Sentinel-2 (10 m, 5-day) and Sentinel-1 (SAR, 12-day) imagery is ingested nightly.
3. A per-(crop, district, season) baseline envelope built from ≥ 3 historical years defines
   "normal" crop health.
4. When a plot's observed NDVI curve falls below the p5 envelope for 2 consecutive
   cloud-free acquisitions, the damage detector fires.
5. An XGBoost model (exactly 12 features) estimates `damage_probability` and
   `estimated_yield_loss_pct`.
6. A **rules engine** — never the ML model alone — converts the estimate into a claim
   recommendation: `REJECT`, `AUTO_REJECT`, `FIELD_VERIFICATION`, or `AUTO_APPROVE`
   (recommendation only).
7. A 12-field **evidence package** — satellite imagery, indicators, AI confidence,
   liability estimate — accompanies every claim so an insurer or government authority can
   audit and sign off in minutes, not months.

**Human approval always gates payout.** The engine accelerates and de-risks the process;
it never authorizes money by itself.

## Demo Story

1. **Satellite** — A fresh Sentinel-2 L2A scene (10 m) over District Dhar (MP) is ingested
   at 02:00 UTC and cloud-masked (scene cloud cover 12.4%).
2. **Plot NDVI** — Soybean plot `PLT-2026-0117` (0.50 ha) is clipped; zonal statistics are
   computed on cloud-free pixels only (valid pixel share 87%).
3. **Baseline deviation** — The observed NDVI curve drops below the p5 envelope of the
   district soybean baseline for 2 consecutive cloud-free acquisitions.
4. **Damage 44%** — The 12-feature XGBoost model scores `damage_probability = 0.83`,
   `estimated_yield_loss_pct = 44%` (expected health 82% → observed 46%).
5. **Evidence package** — 12-field package assembled: 6 satellite images, 3 of 4
   indicators confirmed (SAR moisture anomaly unconfirmed due to decorrelation), AI
   confidence 91%, liability estimate ₹24,640.
6. **Insurer dashboard** — The claim lands in the insurer queue as
   `FIELD_VERIFICATION · HIGH` with one-click evidence review; the SAR gate prevents
   auto-approval, and human sign-off remains mandatory.

## Documentation Map

| Doc | Contents |
| --- | --- |
| `docs/architecture.md` | Service boundaries, component responsibilities, nightly data-flow |
| `docs/data-acquisition.md` | Sources table, STAC example, data-lake layout, storage math |
| `docs/preprocessing.md` | Cloud masking, resampling, per-plot aggregation protocol |
| `docs/feature-engineering.md` | Index formulas, per-plot stats, weather z-scores |
| `docs/ml-pipeline.md` | XGBoost damage model: 12 features, evaluation, fallback |
| `docs/baseline-engine.md` | Quantile envelopes, anomaly rule, crop windows |
| `docs/decision-engine.md` | Claim rules, decision tree, worked example |
| `docs/database-schema.md` | PostGIS + TimescaleDB schema with PK/FK |
| `docs/evidence-package.md` | 12-field report schema, JSON, verification packet |
| `docs/api-contract.md` | REST contract: requests, responses, error codes |
| `docs/dashboard-spec.md` | Insurer web + farmer mobile mockups |
| `docs/folder-structure.md` | Repository layout |
| `docs/deployment.md` | docker-compose, env vars, failure modes, launch checklist |

## Scope & Scale Assumptions

- Analysis unit: one 100 km × 100 km tile ≈ 10,000 km² ≈ 100,000 ha.
- Average insured plot: 0.5 ha → ≈ 200,000 plots per 10,000 km².
- Storage: ≈ 78 GB/year per 10,000 km² (≈ 85% Sentinel-2). See `docs/data-acquisition.md`.