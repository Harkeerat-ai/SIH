# ML Pipeline — Damage Model

## 1. Model

**XGBoost** (gradient-boosted trees) with two output heads:

| Output | Objective | Range |
|--------|-----------|-------|
| `damage_probability` | `binary:logistic` | 0–1 |
| `estimated_yield_loss_pct` | `reg:squarederror` | 0–100 |

**Hyperparameters (locked):**

| Parameter | Value |
|-----------|-------|
| `max_depth` | 6 |
| `eta` (learning rate) | 0.05 |
| `min_child_weight` | 5 |
| `subsample` | 0.8 |
| `n_estimators` | 500 (early stop at 50 rounds) |

**Rationale:** trains in minutes on tabular features; robust to collinear vegetation
indices; native SHAP explainability so every claim can show *why* the model scored it.

## 2. Features — Exactly 12

| # | Feature | Source |
|---|---------|--------|
| 1 | NDVI trend slope over season | `satellite_stats` OLS (per 10 days) |
| 2 | NDVI minimum (season to date) | `satellite_stats` |
| 3 | NDVI mean of last 3 acquisitions | `satellite_stats` |
| 4 | NDVI delta vs baseline (observed − p50) | `baselines` |
| 5 | NDMI trend slope | `satellite_stats` OLS (per 10 days) |
| 6 | NDMI delta vs baseline (observed − p50) | `baselines` |
| 7 | EVI mean (season to date) | `satellite_stats` |
| 8 | Rainfall z-score (30-day) | IMD climatology |
| 9 | Temperature z-score (30-day) | ERA5 climatology |
| 10 | Days since sowing | `plots.sowing_date` |
| 11 | Crop-type one-hot index (0–7 integer map) | crop registry |
| 12 | District-normalized historical yield percentile | plot yield ÷ district yield distribution |

The feature vector is assembled by the `timeseries` service from `satellite_stats`,
`baselines`, `weather`, and `plots` — one row per `(plot_id, season)`.

## 3. Training Data

- **Labels:** historical CCE yields mapped to (plot, season); `damage = 1` iff CCE loss > 15%.
- **Volume:** ≥ 40,000 plot-seasons across ≥ 8 districts, 2019–2024.
- **Split:** 70 / 15 / 15 train / validation / test, split **by plot** (no leakage).
- **Artifact:** `s3://crop-insurance/models/xgb-damage-v3.json`.

## 4. Evaluation & Acceptance Thresholds

| Metric | Acceptance Threshold | Model v3 (2026-06-14) |
|--------|----------------------|-----------------------|
| AUC (damage classification) | ≥ 0.80 | 0.86 |
| RMSE (yield loss, pts) | ≤ 12 | 9.4 |
| Brier score | ≤ 0.15 | 0.11 |
| Calibration slope | 0.9–1.1 | 0.97 |

A model version is promoted to production only when all four thresholds pass on the held-out
test split.

## 5. Fallback Heuristic (Zero Training Data)

Until ≥ 3 seasons of CCE labels exist, the engine uses the index envelope alone:

```
damage_pct = clip(100 × (baseline_p50 − observed) / baseline_p50, 0, 100)
```

where `observed` = NDVI mean of the last 3 acquisitions and `baseline_p50` = the p50
envelope value for the current day of season. In fallback mode, every non-`AUTO_REJECT`
recommendation is forced to `FIELD_VERIFICATION` (never auto-approve).

## 6. Guardrails

- Inference runs nightly at 03:10 UTC on rows appended since 02:45.
- Missing feature (e.g. `insufficient_data` on 3+ acquisitions) → no inference; plot goes
  to `PENDING_REVIEW`.
- SHAP values are stored with the evidence package (top-3 contributors per claim).
- The ML model **never** produces a payout decision — see `decision-engine.md`.