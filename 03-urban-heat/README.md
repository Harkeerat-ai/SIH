# Urban Heat Island & Microclimate Mitigation Planner

A GIS decision-support system for Smart India Hackathon 2026 that answers one question for government planners: **where should the government spend money to reduce heat?**

## Problem statement

Indian cities are getting hotter: daytime land surface temperatures (LST) in dense built-up zones routinely exceed 43 °C in May–June, and heat waves raise mortality, hospital admissions, and energy demand. Governments allocate crores of rupees to heat mitigation — tree planting, cool roofs, reflective pavement — but today the allocation is ad hoc. There is no systematic, evidence-based answer to *"which wards, blocks, or zones get the money first?"*

This system turns satellite imagery, census, and infrastructure data into an operational GIS decision-support tool:

- **Measure** LST and surface features from Landsat 8/9, Sentinel-2/3, and MODIS for every administrative zone.
- **Score** every zone 0–100 on heat vulnerability using a transparent weighted composite (no black box).
- **Rank** hotspots and recommend cost-justified interventions under a fixed budget.
- **Simulate** "what-if" mitigation scenarios before any money is spent.

## Demo story

1. The analyst opens the planning dashboard and sees a tier-colored GIS heat map of the city (LOW green / MEDIUM orange / HIGH red).
2. Zone #104 (dense built-up ward) shows LST 43.8 °C and a vulnerability score of **87 — HIGH**.
3. Hotspot detection flags Zone #104 among **128 hotspots** city-wide.
4. The optimizer, under a ₹5 Cr budget, recommends: **cool roofs 18,000 m² (₹63.0L), 1,200 trees (₹14.4L), 4,500 m² reflective pavement (₹20.25L)** — total ₹97.7L, estimated ΔLST −1.5 °C, vulnerability 87 → 69 (−18 points).
5. The analyst moves the simulator sliders (more trees, more pavement) and the dashboard re-runs the cost-benefit math live — ΔLST **−2.1 °C** in the demo run, still labeled "model estimate".
6. "Generate Mitigation Plan" packages the zone-level recommendations, cost tables, and simulated outcomes into an exportable plan.

## Architecture at a glance

```
Satellite + census + OSM data
        │
        ▼
geo pipeline → land features → urban analytics → vulnerability model → intervention AI / optimizer → simulator
        │                                                                              │
        └──────────────────────────── planning dashboard ◄─────────────────────────────┘
```

## Documentation map

| Document | What it locks down |
|---|---|
| docs/architecture.md | Service boundaries, component responsibilities, end-to-end data flow |
| docs/data-acquisition.md | Satellite/census/OSM sources, STAC ingestion, data lake, storage budget |
| docs/preprocessing.md | Radiometric calibration, cloud masking, resampling, zonal statistics, composites |
| docs/feature-engineering.md | NDVI/NDBI/NDWI, impervious surface, vegetation deficit, LST composite math |
| docs/lst-engine.md | Full LST derivation: DN → radiance → brightness temperature → emissivity → LST; split-window fallback |
| docs/ml-pipeline.md | Optional U-Net land-cover segmentation; threshold fallback; vulnerability is a transparent composite, not deep learning |
| docs/decision-engine.md | Exact vulnerability formula, weights, tiers, worked example (87 HIGH) |
| docs/intervention-optimizer.md | Cost-benefit math and knapsack/greedy allocation; worked Zone #104 example |
| docs/simulator.md | Simulator spec: sliders, re-run semantics, estimate disclaimers, response contract |
| docs/database-schema.md | PostgreSQL/PostGIS tables, keys, JSONB payloads |
| docs/api-contract.md | 9 endpoints with request/response examples and error codes |
| docs/dashboard-spec.md | GIS heat map, KPIs, zone drawer, Generate Mitigation Plan workflow, ASCII mockup |
| docs/folder-structure.md | Repository layout and per-directory responsibility |
| docs/deployment.md | docker-compose services, environment variables, failure modes |

## Principles

- Every output that drives spending is a **model estimate**, labeled as such — never a guaranteed physical outcome.
- The vulnerability score is **transparent**: its factor breakdown is stored and displayed, so planners can explain exactly why a zone scored 87.
- The system **degrades gracefully**: clouded Landsat passes fall back to MODIS, and missing segmentation falls back to thresholds — with a confidence flag on every derived number.
