# Architecture

## Service boundaries

```
                     ┌──────────────────────────────────────────────────────────┐
                     │                  PLANNING DASHBOARD                      │
                     │   GIS heat map · KPI bar · zone drawer · simulate · plans│
                     └───────────────▲──────────────────────────┬──────────────┘
                                     │  REST /api/* (FastAPI)   │ simulated / plan
                     ┌───────────────┴──────────────────────────▼──────────────┐
                     │        INTERVENTION AI / COST-BENEFIT OPTIMIZER          │
                     │   knapsack: max Σ(ΔLST_zone × exposed_population) ≤ B   │
                     └───────────────▲──────────────────────────┬──────────────┘
                                     │ zone heat profile        │ intervention list
                     ┌───────────────┴────────┐   ┌─────────────▼───────────────┐
                     │     VULNERABILITY      │   │          SIMULATOR          │
                     │     MODEL (composite)  │   │  slider re-run of optimizer │
                     └───────────────▲────────┘   └─────────────▲───────────────┘
                                     │ zone statistics          │ simulated ΔLST
                     ┌───────────────┴──────────────────────────┴───────────────┐
                     │            URBAN ANALYTICS (zone statistics)             │
                     └───────────────▲──────────────────────────────────────────┘
                                     │ LST rasters + indices + land cover
                     ┌───────────────┴──────────────────────────────────────────┐
                     │ LAND FEATURES (NDVI/NDBI/NDWI, land cover, impervious)   │
                     └───────────────▲──────────────────────────────────────────┘
                                     │ cloud-masked, calibrated composites
                     ┌───────────────┴──────────────────────────────────────────┐
                     │  GEO PIPELINE (ingestion, preprocessing, LST engine)     │
                     └──────────────────────────────────────────────────────────┘
                                     ▲
                    Landsat 8/9 · Sentinel-2/3 · MODIS · census · OSM · health data
```

Rules of the boundary: every service publishes results only through the API layer and the object store (MinIO) / PostGIS; no service calls another service directly; every derived number carries a `confidence` tag.

## Component responsibility table

| Service | Responsibility | Key outputs |
|---|---|---|
| Geo pipeline | STAC discovery, download, cloud masking, radiometric calibration, compositing | Cloud-free monthly LST rasters; raw COGs in MinIO |
| Land features | Band algebra (NDVI/NDBI/NDWI), optional land-cover segmentation, impervious surface | Index rasters, 6-class land-cover map, impervious fraction |
| Urban analytics | Zonal statistics against admin polygons; joins census, OSM, health data | Per-zone LST mean/p95, vegetation_pct, builtup_pct, water_share, road density, population density, elderly share |
| Vulnerability model | Transparent weighted composite (no deep learning) | V score 0–100, tier (LOW/MEDIUM/HIGH), factor_breakdown JSONB |
| Intervention AI / optimizer | Knapsack cost-benefit allocation under budget; greedy by benefit/cost ratio | Intervention list {type, qty, cost, ΔLST}, cross-zone priority ranking |
| Simulator | Re-runs optimizer formulas on slider inputs | Simulated ΔLST, new vulnerability, confidence: "estimate" |
| Planning dashboard | GIS visualization, KPIs, zone drawer, plan generation and export | Tier heat map, KPI bar, mitigation plans |

## End-to-end data flow (monthly cycle)

1. Monthly Landsat 8/9 pass acquired via STAC; TIRS band 10 radiometrically calibrated; LST computed by the LST engine (docs/lst-engine.md).
2. LST raster produced on the common 30 m UTM grid, cloud-masked with C2 QA_PIXEL.
3. NDVI / NDBI / NDWI computed on the same grid; land cover produced (U-Net, or threshold fallback).
4. Zone statistics per admin polygon: LST mean/p95, vegetation_pct, builtup_pct, water_share, plus census population density, elderly share, OSM road density.
5. Vulnerability model scores every zone → **Zone #104 = 87 (HIGH)** with a stored factor breakdown.
6. Optimizer under ₹5 Cr budget picks for Zone #104: **cool roofs 18,000 m² + 1,200 trees + 4,500 m² pavement** (cost ₹97.7L, ΔLST −1.5 °C).
7. Simulator (demo run with slider-tuned quantities) shows **ΔLST −2.1 °C** and vulnerability 87 → 69.
8. Priority map rendered in the dashboard; hotspot clusters (128 city-wide) and priority zones (27) surfaced for the government spend decision.

## Cross-service contracts

- Raster I/O: MinIO COGs only. Zone metrics: PostgreSQL/PostGIS only. Service calls: FastAPI layer only.
- Confidence tags: `satellite` (Landsat clear-sky), `satellite_fallback` (MODIS), `threshold_fallback` (no segmentation), `estimate` (simulated).
- Idempotency: ingestion jobs keyed by (source, scene_id, date); re-runs overwrite rather than duplicate.
