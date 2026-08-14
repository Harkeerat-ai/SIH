# Feature engineering

All features are derived on the common 30 m UTM grid (docs/preprocessing.md) from Landsat bands (GREEN = B3, RED = B4, NIR = B5, SWIR1 = B6) or Sentinel-2 equivalents (B3, B4, B8, B11). Indices are computed pixel-wise on clear-sky pixels only.

## Spectral indices

**NDVI** (normalized difference vegetation index)

```
NDVI = (NIR − RED) / (NIR + RED)
```

Range −1..+1; high positive values indicate dense vegetation.

**NDBI** (normalized difference built-up index, Zha et al. 2003)

```
NDBI = (SWIR1 − NIR) / (SWIR1 + NIR)
```

Positive values indicate built-up / bare surfaces (SWIR reflectance exceeds NIR).

**NDWI** (normalized difference water index, McFeeters 1996)

```
NDWI = (GREEN − NIR) / (GREEN + NIR)
```

Positive values indicate open water.

## Derived zone features

**Impervious surface estimate**

```
impervious_share = fraction of zone pixels with (NDBI > 0) AND (NDVI < 0.15)
```

Used as a sanity feature; the primary built-up metric is builtup_pct (below).

**Vegetation fraction and deficit**

```
vegetation_fraction_pct = 100 × (zone pixels with NDVI ≥ 0.30) / (all zone pixels)
vegetation_deficit      = 100 − vegetation_fraction_pct
```

A zone with 7 % vegetation cover has a deficit of 93 points.

**Built-up fraction**

```
builtup_pct = 100 × (zone pixels classified built-up) / (all zone pixels)
```

Classification source: U-Net classes {building, road} when segmentation is deployed (docs/ml-pipeline.md); otherwise the threshold fallback (NDBI > 0.1 AND NDVI < 0.15 → built-up).

**Water share**

```
water_share = 100 × (zone pixels with NDWI > 0) / (all zone pixels)
```

**Population density** (census joined by polygon containment)

```
pop_density = zone population / zone area (km²)
```

**Road density** (OSM lines clipped to the zone)

```
road_density = road length inside zone (km) / zone area (km²)
```

## LST composite features

**Monthly mean LST**

```
monthly_mean_LST(z, m) = (1 / N) × Σ_{i=1..N} LST_clear(z, m, i)
```

where N is the number of clear-sky scenes covering zone z in month m.

**Summer peak LST (drives the temperature factor of the vulnerability score)**

```
summer_peak_LST(z) = p95 of all zone LST pixels in May–June composites of the
                     rolling 3-year window (2023–2025)
```

**LST anomaly (zone vs. district baseline)**

```
lst_anomaly(z) = summer_peak_LST(z) − district_summer_mean
```

where `district_summer_mean` is the area-weighted mean of summer_peak_LST across all zones in the district. Used only for ranking/display; the vulnerability score uses summer_peak_LST directly.

## Threshold constants (single source of truth)

| Constant | Value | Used for |
|---|---|---|
| Vegetation NDVI threshold | 0.30 | vegetation_fraction_pct |
| Water NDWI threshold | 0.00 | water_share |
| Impervious NDBI/NDVI thresholds | NDBI > 0, NDVI < 0.15 | impervious_share |
| Built-up fallback thresholds | NDBI > 0.1, NDVI < 0.15 | builtup_pct (fallback) |
| Cloud cover scene cutoff | 70 % | acquisition skip |
