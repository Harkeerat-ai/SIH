# Autonomous Illegal Mining & Encroachment Early Warning System

**Smart India Hackathon 2026 · Environment & Geospatial AI**

Fully autonomous detection of new mining excavation and riverbed/forest encroachment from satellite imagery, with deterministic risk scoring and officer-alert escalation. Zero human intervention between satellite overpass and officer SMS.

## Problem Statement

Illegal sand, stone and coal mining — frequently on riverbeds, forest land and protected-area buffer zones — destroys habitats, alters river morphology and drains state revenue. Ground inspections are remote, reactive and sparse; by the time officials arrive, the damage is done and the machinery is gone. Existing monitoring is manual, ad-hoc and slow.

**Goal:** a pipeline that turns every satellite overpass into a structured, risk-scored, geolocated alert in the hands of the enforcement officer — autonomously, every cycle, with no analyst in the loop.

## Solution at a Glance

Sentinel-2 (5-day revisit) and Sentinel-1 SAR (12-day revisit) images are ingested on a 06:00 UTC cron, preprocessed onto a common 10 m UTM grid, differenced into spectral and SAR change features, passed through three AI models (change detection, excavation segmentation, equipment/road detection) with a deterministic index-differencing fallback, scored on 7 weighted risk factors, and escalated by tier.

## Demo Story (Screenshot-Ready Narrative)

1. **Satellite overpass — 06:00 UTC.** Sentinel-2 L2A tile 44QND arrives over Chandrapur district, Maharashtra. Cloud cover 8.4% — inside the 30% acceptance threshold. *(Screenshot: scene listing / STAC registry.)*
2. **Cloud masking.** s2cloudless builds the residual cloud mask; the scene enters the preprocessing queue. *(Screenshot: cloud mask overlay.)*
3. **AI detects new excavation.** The change-detection U-Net compares 12 July vs 05 July and flags a **2.0 ha new excavation** near Ghugus village. Segmentation confirms classes pit + exposed_soil; YOLO finds **1 excavator and 2 trucks**. *(Screenshot: change mask + object boxes on imagery.)*
4. **Expansion calculation.** The feature engine measures **1.6 ha of vegetation loss** and **+23% area growth over 30 days**. *(Screenshot: delta NDVI / area-over-time chart.)*
5. **Boundary checks.** Geodesic distance to the Wainganga river: **85 m**. The polygon overlaps the **Tadoba-Andhari Eco-Sensitive Zone**. The permit registry contains **no valid lease** for the polygon. *(Screenshot: boundary overlays highlighted.)*
6. **Risk score.** The decision engine computes **87 / 100 — HIGH (red)** from 7 weighted factors. *(Screenshot: factor breakdown panel.)*
7. **Officer alert.** Within 1 minute: **SMS to the Chandrapur District Mining Officer**, email to the **Deputy Director**, and a dashboard entry — **Alert #MH-2026-00431, status OPEN**. *(Screenshot: SMS render + feed entry.)*
8. **Field verification.** Officer assigns, verifies in field, marks **CONFIRMED**. The confirmed polygon becomes a retraining label; repeat alerts within 14 days are suppressed. *(Screenshot: verification form.)*

## Headline Numbers

| Parameter | Value |
|---|---|
| Revisit cadence | 5 days optical · 12 days SAR |
| Ground resolution | 10 m (UTM grid, EPSG:32643–32645 for India) |
| Risk model | 7 weighted factors → score 0–100 |
| Tiers | LOW 0–39 · MEDIUM 40–69 · HIGH 70–100 |
| Alert-to-officer SLA | ≤ 1 minute after risk computation |
| Model acceptance | Change IoU ≥ 0.60 · Segmentation IoU ≥ 0.55 · mAP@0.5 ≥ 0.50 |
| Storage budget | ≈ 21.5 GB/month per 10,000 km² |

## Documentation Map

| Document | What it locks down |
|---|---|
| `docs/architecture.md` | Service boundaries (7 services), component responsibility table, end-to-end data flow |
| `docs/data-acquisition.md` | Data sources, revisit cadence, STAC item schema, data-lake layout, storage arithmetic |
| `docs/preprocessing.md` | Exact SAR / optical / DEM algorithms and parameters |
| `docs/feature-engineering.md` | Index math: NDVI, NDWI, Δσ⁰, differencing, geodesic distances, excavation indicator |
| `docs/ml-pipeline.md` | 3 models + zero-data heuristic fallback, training data, metrics definitions |
| `docs/decision-engine.md` | Exact risk formula, 7 factor weights, tiers, worked example → 87 HIGH |
| `docs/database-schema.md` | PostGIS schema: districts, boundaries, permits, detections, alerts, officers |
| `docs/api-contract.md` | 10 REST endpoints with request/response and error bodies |
| `docs/dashboard-spec.md` | Map layers, alert detail panel, officer workflow, ASCII mockup |
| `docs/folder-structure.md` | Proposed code layout for the implementation phase |
| `docs/deployment.md` | docker-compose services, environment variables, failure modes |
| `docs/alerting.md` | Channels, escalation tiers, lifecycle state machine, retraining loop |

## Scope

This repository is a decision-complete architecture specification. Every number, weight, threshold, schema and endpoint is final for the hackathon build — no placeholder values remain.
