# SIH Restructure — 3 Self-Contained Architecture Folders — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Tasks 2/3/4 are independent — dispatch in parallel (one subagent per project folder), review after each.

**Goal:** Add three sibling folders (`01-illegal-mining/`, `02-crop-insurance/`, `03-urban-heat/`) containing fully self-contained, refined architecture document sets — **no code, no deletions, no `sihvision` references**.

**Architecture:** Each folder follows a shared 12-file template (README + 11 docs) plus 1-2 project-specific docs. Refinement over the user's draft comes from locking concrete decisions: exact scoring formulas, PostGIS table sketches, API endpoint contracts, ML fallback heuristics for missing training data, and alert/claim/verification workflows.

**Tech stack:** Markdown only. Verification via glob/grep/git.

---

### Task 0: Prepare repo + skeleton

- [x] Confirm layout: `sihvision/`, `tests/`, `demo_data/` etc. present; `.gitignore` untouched.
- [x] Create directories: `01-illegal-mining/docs/`, `02-crop-insurance/docs/`, `03-urban-heat/docs/`
- [x] Save this plan to `docs/superpowers/plans/2026-08-14-sih-restructure.md`
- [ ] Commit: `chore: scaffold three architecture doc folders`
- [ ] Verify: `git status` shows only new untracked dirs, nothing modified

### Task 1: Shared per-project doc template (locked here, used by Tasks 2–4)

Each folder gets **exactly** these files, all in Markdown, with the content outlines below. All numbers (weights, thresholds, schemas, endpoints) must be concrete — no "TBD/TODO/approx".

| File | Required content |
|---|---|
| `README.md` | Problem statement, demo story (screenshot-ready narrative), doc map table, page-length = ~50 lines |
| `docs/architecture.md` | Refined ASCII diagram (service boundaries), component responsibility table, data-flow sequence (ingest → predict → decision → action) |
| `docs/data-acquisition.md` | Sources + products + revisit cadence, STAC item schema (JSON), data-lake layout (`raw/{..}/processed/{..}/predictions/{..}`), estimated storage per 10k km² |
| `docs/preprocessing.md` | Exact algorithms: SAR speckle filter (Refined Lee / median 5×5), cloud masking (s2cloudless or QA band), resampling method + target CRS (UTM per zone), radiometric calibration steps |
| `docs/feature-engineering.md` | Index formulas as math (NDVI, NDWI, NDMI, EVI, NDBI, LST as applicable), change-raster computation, distance-to-boundary features |
| `docs/ml-pipeline.md` | Per model: architecture + rationale, training data requirements (classes, min samples/class, chip size), loss, eval metrics + acceptance thresholds, and an **explicit index-threshold fallback heuristic** that works with zero training data |
| `docs/decision-engine.md` | Exact score formula, weight table (with values), per-feature normalization (0–100), tier thresholds (e.g. Low 0–39 / Medium 40–69 / High 70–100), worked example with arithmetic |
| `docs/database-schema.md` | PostGIS-style table sketch: table name, key columns + types, PK/FK, one relationship per line, SQL-adjacent syntax (no full DDL required) |
| `docs/api-contract.md` | ≥8 endpoints, each: method, path, request JSON, response JSON, error codes (400/404/422/500) |
| `docs/dashboard-spec.md` | Map layer list, cluster/alert detail panel spec (fields), officer workflow states, ASCII mockup |
| `docs/folder-structure.md` | Proposed future code layout (`backend/src/{services}/`, `ml/models/`, `web/`, `infra/`) with per-dir responsibility |
| `docs/deployment.md` | docker-compose service list (name, image, purpose, ports), env var table, failure mode notes (Celery retries, dead-letter queue) |

**Project-specific extras:** `01-illegal-mining/docs/alerting.md` (email/SMS/mobile channels, escalation, verification → retraining loop) • `02-crop-insurance/docs/baseline-engine.md` + `evidence-package.md` • `03-urban-heat/docs/lst-engine.md` + `intervention-optimizer.md`

**Refinement directives locked per project:**

- **01-illegal-mining**: risk score = weighted normalized sum of 7 factors (excavation area, vegetation loss, river proximity, protected-area overlap, equipment detected, permit status, expansion rate); **permit check suppresses alerts in permitted zones**; detection entities carry geometry + area_ha + confidence; alert lifecycle `OPEN → ASSIGNED → FIELD_VERIFIED → CONFIRMED/DISMISSED`; YOLO fallback = permissive threshold on change rasters.
- **02-crop-insurance**: TimescaleDB hypertable for per-plot satellite_stats; baseline = per (crop, district, season) quantile envelope (p5–p95 of historical NDVI/NDMI curves); anomaly = observed curve crossing below envelope for ≥2 consecutive acquisitions; XGBoost feature list = 12 features (curve trend slope, min, mean-last-3, delta-vs-baseline, weather z-scores); recommendation tiers `AUTO_APPROVE / FIELD_VERIFICATION / REJECT` — **human approval always gates payout**; evidence package = 12 fields as in draft report.
- **03-urban-heat**: LST via TOA → brightness temperature → single-channel emissivity (NDVI-threshold method) for Landsat, split-window for Sentinel-3/MODIS; vulnerability = weighted composite (temperature 40 / vegetation deficit 20 / pop density 15 / building density 10 / elderly 5 / road 5 / water 5); intervention optimizer = per-intervention cost + modeled ΔLST benefit (literature coefficients: tree ≈ 1.5–3.5°C shade, cool roof Δalbedo 0.3–0.65, reflective pavement) with budget constraint; simulator outputs labeled "model estimate, not guaranteed".

### Task 2: Write `01-illegal-mining/` doc set (13 files)

- [ ] Write all 13 files per Task-1 template with mining-specific content (entities: `districts`, `alert_groups`, `detections`, `risk_factors`, `permits`, `boundaries`, `officers`, `verifications`)
- [ ] Verify: `git ls-files` — all 13 present
- [ ] Commit: `docs: refined architecture for illegal-mining early warning system`

### Task 3: Write `02-crop-insurance/` doc set (14 files)

- [ ] Write all 14 files per template (entities: `farmers`, `plots`, `policies`, `claims`, `satellite_stats`, `baselines`, `weather`, `evidence_packages`, `claim_decisions`)
- [ ] Verify + commit: `docs: refined architecture for crop health micro-insurance engine`

### Task 4: Write `03-urban-heat/` doc set (14 files)

- [ ] Write all 14 files per template (entities: `zones`, `lst_readings`, `indices`, `vulnerability`, `interventions`, `budgets`)
- [ ] Verify + commit: `docs: refined architecture for urban heat island mitigation planner`

### Task 5: Final verification (no code — checklist only)

- [ ] `glob` `{01-illegal-mining,02-crop-insurance,03-urban-heat}/**/*.md` → exactly 41 files
- [ ] `grep -ri "sihvision"` in the 3 folders → **0 matches**
- [ ] `grep -riE "TBD|TODO|FIXME|placeholder|later"` in the 3 folders → 0 matches
- [ ] `git status` → `sihvision/` shows **no modifications**; only new files added
- [ ] Spot-read 3 files (one per folder, the decision-engine docs) to confirm concrete numbers present
- [ ] Commit: `docs: verification pass — no placeholders, no sihvision references`