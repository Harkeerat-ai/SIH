# Decision engine — heat vulnerability score

The vulnerability score answers the core question: *which zones are most exposed to heat, and who is most affected there?* It is a transparent weighted composite — never a neural network — so every point of the score can be explained to a government planner.

## The formula

```
V = Σ w_i · n_i
```

- `n_i` = normalized factor value, clipped to 0–100.
- `w_i` = fixed factor weight, Σ w_i = 1.00.
- `V` = vulnerability score, 0–100.

| # | Factor (i) | Weight w_i | Raw input | Normalization n_i (clipped 0–100) |
|---|---|---|---|---|
| 1 | Temperature | 0.40 | summer_peak_LST (°C) | n = (LST − 25) / (45 − 25) × 100 |
| 2 | Vegetation deficit | 0.20 | vegetation_pct | n = 100 − vegetation_pct |
| 3 | Population density | 0.15 | pop per km² | n = (pop_km2 / 20000) × 100 |
| 4 | Building density | 0.10 | builtup_pct | n = builtup_pct |
| 5 | Elderly / health risk | 0.05 | elderly share (%) | n = elderly_share_pct × 2 |
| 6 | Road density | 0.05 | km road per km² | n = (km_road_km2 / 20) × 100 |
| 7 | Water availability | 0.05 | water_share (%) | n = 100 − water_share |

## Tiers

| Score | Tier | Map color | Meaning |
|---|---|---|---|
| 0–39 | LOW | green | mitigation optional |
| 40–69 | MEDIUM | orange | intervention warranted |
| 70–100 | HIGH | red | priority for immediate action |

## Worked example — Zone #104 → V = 87 (HIGH)

Zone inputs (July 2026 composite, census, OSM):
LST = 43.8 °C, vegetation 7 %, population 18,000/km², building density 82 %, elderly share 25 %, road density 10 km/km², water cover 18 %.

| Factor | w_i | Raw | n_i | w_i × n_i |
|---|---|---|---|---|
| Temperature | 0.40 | 43.8 °C | (43.8 − 25)/20 × 100 = 94.0 | 37.6 |
| Vegetation deficit | 0.20 | 7 % | 100 − 7 = 93.0 | 18.6 |
| Population density | 0.15 | 18,000/km² | 18000/20000 × 100 = 90.0 | 13.5 |
| Building density | 0.10 | 82 % | 82.0 | 8.2 |
| Elderly / health | 0.05 | 25 % | 25 × 2 = 50.0 | 2.5 |
| Road density | 0.05 | 10 km/km² | 10/20 × 100 = 50.0 | 2.5 |
| Water availability | 0.05 | 18 % | 100 − 18 = 82.0 | 4.1 |
| **V** | **1.00** | | | **87.0 → HIGH** |

## Output contract

Each zone, per date, produces:

```json
{
  "zone_id": 104,
  "date": "2026-07-31",
  "score": 87.0,
  "tier": "HIGH",
  "factor_breakdown": {
    "temperature":        { "w": 0.40, "n": 94.0, "contribution": 37.6 },
    "vegetation_deficit": { "w": 0.20, "n": 93.0, "contribution": 18.6 },
    "population_density": { "w": 0.15, "n": 90.0, "contribution": 13.5 },
    "building_density":   { "w": 0.10, "n": 82.0, "contribution": 8.2 },
    "elderly_health":     { "w": 0.05, "n": 50.0, "contribution": 2.5 },
    "road_density":       { "w": 0.05, "n": 50.0, "contribution": 2.5 },
    "water_availability": { "w": 0.05, "n": 82.0, "contribution": 4.1 }
  },
  "confidence": "satellite"
}
```

## Scoring rules

- Scores are computed on the last day of each month from the month's zone statistics.
- If LST came from MODIS, `confidence = "satellite_fallback"`; if builtup_pct came from thresholds, `confidence = "threshold_fallback"`; simulated re-scores are always `"estimate"`.
- Zones with `insufficient_data` are never scored — they are excluded with a clear flag rather than silently treated as low risk.
