# Folder Structure

```
02-crop-insurance/
├── backend/
│   └── src/services/
│       ├── ingestion/      # nightly STAC/S1/IMD/ERA5 pulls; raw-lake writes; cloud-cover gate
│       ├── preprocessing/  # s2cloudless+QA60 masks; 10 m resampling; S1 calibration/terrain
│       ├── field_engine/   # clip to plot polygons; zonal stats; ≥ 30% valid-pixel gate
│       ├── timeseries/     # satellite_stats appends; curve statistics assembly
│       ├── baseline/       # (crop, district, season) envelopes; anomaly detection
│       ├── damage_model/   # XGBoost inference (12 features); fallback heuristic
│       ├── claims/         # claim lifecycle; evidence packages; liability estimate
│       ├── rules_engine/   # REJECT/AUTO_REJECT/FIELD_VERIFICATION/AUTO_APPROVE logic
│       └── api/            # FastAPI REST layer (contract in docs/api-contract.md)
├── ml/                     # training, evaluation, SHAP, model registry (xgb-damage-v3.json)
├── web/                    # insurer dashboard (Next.js; docs/dashboard-spec.md §1)
├── mobile/                 # farmer app (React Native; docs/dashboard-spec.md §2)
└── infra/                  # docker-compose, env templates, deploy checklist, DB migrations
```

## One-Line Responsibilities

| Path | Responsibility |
|------|----------------|
| `backend/src/services/ingestion` | Pull sources nightly; validate; enforce cloud-cover gate; write raw lake |
| `backend/src/services/preprocessing` | Cloud-mask, resample to 10 m UTM, calibrate/terrain-correct SAR |
| `backend/src/services/field_engine` | Clip scenes to plot polygons; compute cloud-free zonal statistics; apply the 30% valid-pixel rule |
| `backend/src/services/timeseries` | Append `satellite_stats`; assemble NDVI/NDMI/EVI curves and curve statistics |
| `backend/src/services/baseline` | Build and refresh p5/p50/p95 envelopes; fire the ≥ 2-below-p5 anomaly |
| `backend/src/services/damage_model` | Score 12 features → `damage_probability`, `estimated_yield_loss_pct`; fallback when untrained |
| `backend/src/services/claims` | Own the claim lifecycle; generate evidence packages and liability estimates |
| `backend/src/services/rules_engine` | Apply R1–R5 rules; produce the recommendation; enforce the SAR and human gates |
| `backend/src/services/api` | Expose the REST contract; JWT auth and role checks; 400/404/422/500 mapping |
| `ml` | Offline training/eval against CCE labels; acceptance thresholds; SHAP artifacts |
| `web` | Insurer dashboard: KPIs, map, claim queue, evidence viewer |
| `mobile` | Farmer app: My Farm, weather risk, Report Damage |
| `infra` | docker-compose services, env templates, failure-mode config, launch checklist |