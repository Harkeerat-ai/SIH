# Feature Engineering

All indices are computed per pixel, per scene, on cloud-free pixels only (mask applied
first). Per-plot statistics are computed on the valid pixels within the plot polygon.

## 1. Spectral Indices

| Index | Formula | Bands | Purpose |
|-------|---------|-------|---------|
| NDVI | `NDVI = (NIR − R) / (NIR + R)` | B8, B4 | Green biomass / canopy vigour |
| NDMI | `NDMI = (NIR − SWIR1) / (NIR + SWIR1)` | B8, B11 | Canopy moisture content |
| EVI | `EVI = 2.5 × (NIR − R) / (NIR + 6R − 7.5B + 1)` | B8, B4, B2 | Biomass with soil-background correction |
| NDWI | `NDWI = (G − NIR) / (G + NIR)` | B3, B8 | Surface water / hydration |

All indices range over [−1, 1]. EVI removes soil background via the blue band and is
saturated later than NDVI; NDMI tracks moisture stress earlier than NDVI in many crops;
NDWI detects standing water (ponding, waterlogging).

## 2. Per-Plot, Per-Acquisition Aggregation

For each plot *p* and acquisition date *d* (valid pixels only, `valid_pixel_pct ≥ 30%`):

```
ndvi_mean(p,d) = mean over valid pixels of NDVI
ndvi_std(p,d)  = std  over valid pixels of NDVI
ndmi_mean(p,d) = mean over valid pixels of NDMI
evi_mean(p,d)  = mean over valid pixels of EVI
```

Stored as one `satellite_stats` row per `(plot_id, acquisition_date, source)`.

## 3. Weather Features

**Rainfall z-score (30-day):**

```
R30     = Σ rainfall over the last 30 days        (IMD grid cell of plot centroid)
z_rain  = (R30 − μ_R30) / σ_R30
```

where μ_R30, σ_R30 come from the **10-year district climatology** for the same calendar
window (e.g. Jun 10–Jul 9 for a Jun 10 sowing).

**Temperature z-score (30-day):**

```
T30    = mean of (tmax + tmin)/2 over the last 30 days   (ERA5 cell)
z_temp = (T30 − μ_T30) / σ_T30
```

with the same 10-year climatology convention.

## 4. Curve Summary Statistics (Season to Date)

For each per-plot index series x over day-of-season t (t = 1 on sowing date):

| Statistic | Formula |
|-----------|---------|
| OLS trend slope | `slope = Σ(t − t̄)(x − x̄) / Σ(t − t̄)²` (reported per 10 days) |
| Minimum | `min(x)` over acquisitions so far |
| Mean of last 3 acquisitions | `(x_{d} + x_{d−1} + x_{d−2}) / 3` |
| Series mean / std | `x̄`, `σ_x` |
| Baseline delta | `x̄_last3 − baseline_p50(day_of_season)` |

These curve statistics feed the damage model's 12 features (see
`ml-pipeline.md`); the per-(crop, district, season) quantile envelope is defined in
`baseline-engine.md`.