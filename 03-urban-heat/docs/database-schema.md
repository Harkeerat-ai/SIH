# Database schema (PostgreSQL + PostGIS)

Seven tables. All geometry in EPSG:4326. All monetary values in INR. All scores 0–100.

## Tables

### zones

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| name | TEXT | NOT NULL |
| geometry | GEOMETRY(Polygon, 4326) | NOT NULL |
| admin_level | TEXT | NOT NULL — 'ward' \| 'block' \| 'zone' |
| population | INTEGER | NOT NULL |
| elderly_share | REAL | NOT NULL — % population aged ≥ 60 |

### lst_readings

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| zone_id | INTEGER | NOT NULL, **FOREIGN KEY → zones(id)** ON DELETE CASCADE |
| date | DATE | NOT NULL |
| lst_mean_c | REAL | NOT NULL |
| lst_p95_c | REAL | NOT NULL |
| source | TEXT | NOT NULL — 'landsat' \| 'modis_fallback' |

UNIQUE (zone_id, date, source).

### indices

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| zone_id | INTEGER | NOT NULL, **FOREIGN KEY → zones(id)** ON DELETE CASCADE |
| date | DATE | NOT NULL |
| ndvi_mean | REAL | NOT NULL |
| ndbi_mean | REAL | NOT NULL |
| ndwi_mean | REAL | NOT NULL |
| vegetation_pct | REAL | NOT NULL |
| builtup_pct | REAL | NOT NULL |

UNIQUE (zone_id, date).

### vulnerability

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| zone_id | INTEGER | NOT NULL, **FOREIGN KEY → zones(id)** ON DELETE CASCADE |
| date | DATE | NOT NULL |
| score | REAL | NOT NULL, CHECK (score BETWEEN 0 AND 100) |
| tier | TEXT | NOT NULL, CHECK (tier IN ('LOW','MEDIUM','HIGH')) |
| factor_breakdown | JSONB | NOT NULL |

UNIQUE (zone_id, date). `factor_breakdown` example:

```json
{
  "temperature":        { "w": 0.40, "n": 94.0, "contribution": 37.6 },
  "vegetation_deficit": { "w": 0.20, "n": 93.0, "contribution": 18.6 },
  "population_density": { "w": 0.15, "n": 90.0, "contribution": 13.5 },
  "building_density":   { "w": 0.10, "n": 82.0, "contribution": 8.2 },
  "elderly_health":     { "w": 0.05, "n": 50.0, "contribution": 2.5 },
  "road_density":       { "w": 0.05, "n": 50.0, "contribution": 2.5 },
  "water_availability": { "w": 0.05, "n": 82.0, "contribution": 4.1 }
}
```

### interventions

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| zone_id | INTEGER | NOT NULL, **FOREIGN KEY → zones(id)** ON DELETE CASCADE |
| type | TEXT | NOT NULL, CHECK (type IN ('cool_roof','tree','reflective_pavement')) |
| quantity | REAL | NOT NULL |
| unit | TEXT | NOT NULL — 'm2' \| 'trees' |
| cost_inr | NUMERIC(14,2) | NOT NULL |
| est_delta_lst_c | REAL | NOT NULL |
| status | TEXT | NOT NULL DEFAULT 'proposed', CHECK (status IN ('proposed','approved','rejected','executed')) |

### budgets

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| scheme | TEXT | NOT NULL |
| year | INTEGER | NOT NULL |
| amount_inr | NUMERIC(16,2) | NOT NULL |
| allocated_inr | NUMERIC(16,2) | NOT NULL DEFAULT 0 |

UNIQUE (scheme, year).

### plans

| Column | Type | Constraint |
|---|---|---|
| id | SERIAL | **PRIMARY KEY** |
| zone_id | INTEGER | NOT NULL, **FOREIGN KEY → zones(id)** ON DELETE CASCADE |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| total_cost | NUMERIC(16,2) | NOT NULL |
| est_delta_lst | REAL | NOT NULL |
| recommendations | JSONB | NOT NULL |

`recommendations` example (Zone #104 plan):

```json
{
  "interventions": [
    { "type": "cool_roof",          "qty": 18000, "unit": "m2",    "cost_inr": 6300000,  "delta_lst_c": -0.72 },
    { "type": "tree",               "qty": 1200,  "unit": "trees", "cost_inr": 1440000,  "delta_lst_c": -0.30 },
    { "type": "reflective_pavement","qty": 4500,  "unit": "m2",    "cost_inr": 2025000,  "delta_lst_c": -0.52 }
  ],
  "new_vulnerability": 69,
  "confidence": "estimate"
}
```

## Key relationships

| From | To | Cardinality |
|---|---|---|
| lst_readings.zone_id | zones.id | many → 1 |
| indices.zone_id | zones.id | many → 1 |
| vulnerability.zone_id | zones.id | many → 1 |
| interventions.zone_id | zones.id | many → 1 |
| plans.zone_id | zones.id | many → 1 |
| budgets | (standalone, referenced by scheme+year in plans) | 1 : many |

## Conventions

- Hotspot and priority-zone queries use a spatial index on `zones.geometry` (GIST) and `vulnerability.date` (BTREE) for the `WHERE date = '2026-07-31'` scans.
- `vulnerability`, `lst_readings`, and `indices` are append-only by (zone, date); re-ingestion upserts on the UNIQUE keys.
- Zone statistics (`zones` + derived) are refreshed monthly; geometry is immutable after the first ingest.