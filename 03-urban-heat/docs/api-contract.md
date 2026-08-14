# API contract

Base URL: `/api/v1`. Content type: `application/json`. Every response carries the envelope:

```json
{
  "data": { },
  "error": null
}
```

Error envelope (HTTP 400, 404, 422, 500):

```json
{
  "data": null,
  "error": { "code": "ZONE_NOT_FOUND", "message": "zone 9999 does not exist", "detail": "query: /zones/9999/heat-profile" }
}
```

Error codes: `400` malformed request body, `404` unknown zone/plan, `422` semantically invalid input (negative quantity, budget ≤ 0), `500` upstream failure (solver, raster read, database).

---

## 1. POST /ingest/lst

Register an LST product for processing (queued to Celery).

Request:

```json
{
  "source": "landsat",
  "date": "2026-07-12",
  "scene_id": "LC09_L1TP_144046_20260712_20260712_02_T1",
  "asset_url": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_ST_B10.TIF"
}
```

Response `202`:

```json
{ "data": { "job_id": "job_1042", "status": "queued" }, "error": null }
```

Errors: `400` missing source/date; `422` unknown source ('landsat'|'sentinel3'|'modis'); `500` object-store read failure.

## 2. GET /zones

List zones, optionally filtered.

Query: `?admin_level=ward&bbox=72.5,18.9,72.9,19.3`

Response `200`:

```json
{
  "data": { "count": 1500, "zones": [ { "id": 104, "name": "Zone 104", "admin_level": "ward", "population": 45000 } ] },
  "error": null
}
```

Errors: `400` malformed bbox; `422` invalid admin_level.

## 3. GET /zones/{id}/heat-profile

Latest composite + trailing 12-month series for one zone.

Response `200`:

```json
{
  "data": {
    "zone_id": 104,
    "latest": { "date": "2026-07-31", "lst_mean_c": 42.1, "lst_p95_c": 43.8, "ndvi_mean": 0.11, "ndbi_mean": 0.22, "ndwi_mean": -0.18, "vegetation_pct": 7.0, "builtup_pct": 82.0, "source": "landsat" },
    "series": [ { "date": "2026-07-31", "lst_mean_c": 42.1, "lst_p95_c": 43.8 }, { "date": "2026-06-30", "lst_mean_c": 41.9, "lst_p95_c": 43.5 } ]
  },
  "error": null
}
```

Errors: `404` unknown zone; `500` raster/database failure.

## 4. GET /zones/{id}/vulnerability

Latest score with full factor breakdown. Query: `?date=2026-07-31`.

Response `200`:

```json
{
  "data": {
    "zone_id": 104, "date": "2026-07-31", "score": 87.0, "tier": "HIGH",
    "factor_breakdown": {
      "temperature": { "w": 0.40, "n": 94.0, "contribution": 37.6 },
      "vegetation_deficit": { "w": 0.20, "n": 93.0, "contribution": 18.6 },
      "population_density": { "w": 0.15, "n": 90.0, "contribution": 13.5 },
      "building_density": { "w": 0.10, "n": 82.0, "contribution": 8.2 },
      "elderly_health": { "w": 0.05, "n": 50.0, "contribution": 2.5 },
      "road_density": { "w": 0.05, "n": 50.0, "contribution": 2.5 },
      "water_availability": { "w": 0.05, "n": 82.0, "contribution": 4.1 }
    },
    "confidence": "satellite"
  },
  "error": null
}
```

Errors: `404` zone not found or no score for date; `422` malformed date.

## 5. GET /hotspots

Zones scored HIGH/MEDIUM for a date. Query: `?date=2026-07-31&tier=HIGH`.

Response `200`:

```json
{
  "data": { "date": "2026-07-31", "tier": "HIGH", "count": 128, "hotspots": [ { "zone_id": 104, "score": 87.0, "lst_p95_c": 43.8, "population": 45000, "rank": 1 } ] },
  "error": null
}
```

Errors: `400` missing date; `422` invalid tier.

## 6. POST /simulate

Re-run the optimizer formulas on slider inputs.

Request:

```json
{ "zone_id": 104, "trees": 1200, "cool_roof_m2": 18000, "pavement_m2": 4500 }
```

Response `200`:

```json
{
  "data": {
    "zone_id": 104,
    "interventions": [
      { "type": "cool_roof",           "qty": 18000, "cost": 6300000, "delta_lst": -0.72 },
      { "type": "tree",                "qty": 1200,  "cost": 1440000, "delta_lst": -0.30 },
      { "type": "reflective_pavement", "qty": 4500,  "cost": 2025000, "delta_lst": -0.52 }
    ],
    "total_delta_lst": -1.54,
    "new_vulnerability": 69,
    "confidence": "estimate"
  },
  "error": null
}
```

Errors: `404` unknown zone; `422` negative quantity or quantity beyond slider bounds; `500` solver failure.

## 7. GET /optimize

Full budget run for one zone. Query: `?zone_id=104&budget=50000000`.

Response `200`:

```json
{
  "data": {
    "zone_id": 104, "budget_inr": 50000000, "total_cost_inr": 9765000, "est_delta_lst_c": -1.54,
    "new_vulnerability": 69,
    "interventions": [
      { "type": "cool_roof",          "qty": 18000, "unit": "m2",    "cost_inr": 6300000, "delta_lst_c": -0.72 },
      { "type": "tree",               "qty": 1200,  "unit": "trees", "cost_inr": 1440000, "delta_lst_c": -0.30 },
      { "type": "reflective_pavement","qty": 4500,  "unit": "m2",    "cost_inr": 2025000, "delta_lst_c": -0.52 }
    ],
    "confidence": "estimate"
  },
  "error": null
}
```

Errors: `404` unknown zone; `422` budget ≤ 0; `500` optimizer failure.

## 8. GET /dashboard/summary

KPI bar data for the dashboard.

Response `200`:

```json
{
  "data": {
    "as_of": "2026-07-31",
    "hotspots": 128,
    "population_at_risk": 1400000,
    "priority_zones": 27,
    "district_avg_lst_c": 38.4,
    "budget_inr": { "total": 500000000, "allocated": 310000000 }
  },
  "error": null
}
```

Errors: `500` dashboard aggregate failure.

## 9. POST /plans

Persist a mitigation plan from simulated/optimized output.

Request:

```json
{
  "zone_id": 104,
  "name": "Zone 104 heat mitigation — Jul 2026",
  "recommendations": {
    "interventions": [
      { "type": "cool_roof",          "qty": 18000, "unit": "m2",    "cost_inr": 6300000, "delta_lst_c": -0.72 },
      { "type": "tree",               "qty": 1200,  "unit": "trees", "cost_inr": 1440000, "delta_lst_c": -0.30 },
      { "type": "reflective_pavement","qty": 4500,  "unit": "m2",    "cost_inr": 2025000, "delta_lst_c": -0.52 }
    ],
    "new_vulnerability": 69,
    "confidence": "estimate"
  }
}
```

Response `201`:

```json
{ "data": { "plan_id": 7, "zone_id": 104, "total_cost": 9765000, "est_delta_lst": -1.54, "created_at": "2026-08-01T10:12:00Z" }, "error": null }
```

Errors: `400` empty recommendations; `404` unknown zone; `422` recommendation cost > referenced budget (scheme, year); `500` database failure.