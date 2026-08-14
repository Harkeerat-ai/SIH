# Preprocessing pipeline

Order of operations per monthly cycle, on every raster entering the system.

## 1. Radiometric calibration (thermal)

- Landsat Collection 2 Level-1 TIRS band 10: convert 16-bit DN (Qcal) to top-of-atmosphere radiance:

  **L = M_L·Qcal + A_L**

  with `M_L = 3.3420e−4` (RADIANCE_MULT_BAND_10) and `A_L = 0.10000` (RADIANCE_ADD_BAND_10), read from the scene MTL file. The radiance COG is staged; the brightness-temperature and emissivity steps live in docs/lst-engine.md.

- Sentinel-3 SLSTR and MODIS MOD11A1 arrive as brightness temperature / LST products respectively and skip this step.

## 2. Cloud masking

- **Landsat (C2 QA_PIXEL):** reject pixels with bit 3 (cloud), bit 4 (cloud shadow), or bit 1 (dilated cloud). Whole scenes with `eo:cloud_cover > 70` are dropped at acquisition.
- **Sentinel-2 (SCL band):** keep classes 4 (vegetation), 5 (non-vegetated), 6 (water); reject 3 (cloud shadow), 8 (medium-probability cloud), 9 (high-probability cloud), 10 (thin cirrus), 11 (snow).
- **MODIS MOD11A1 (QC band):** keep only pixels whose bits 0–1 = "00" (good quality). All other pixels → nodata.

## 3. Resampling to the common 30 m UTM grid

- Every raster is reprojected to the UTM zone of the district centroid (e.g., EPSG:32644 for Mumbai) on a single 30 m grid with identical origin and tile layout.
- LST 100 m → 30 m: **bilinear** interpolation.
- Indices: computed at native resolution first, then resampled to the 30 m grid (bilinear).
- Land cover (categorical): **nearest-neighbour** at 10 m, then majority-resampled to 30 m.
- Water mask: pixels with NDWI > 0 are burned into the grid before zonal statistics so water bodies never pollute LST aggregates.

## 4. Zonal statistics

Per admin polygon (zone), computed with rasterio/zonalstats over the 30 m grid, nodata excluded:

| Metric | Definition |
|---|---|
| LST mean (°C) | area-weighted mean of clear-sky LST pixels in the zone |
| LST p95 (°C) | 95th percentile of zone LST pixels |
| LST std (°C) | standard deviation of zone LST pixels |
| NDVI/NDBI/NDWI mean | area-weighted mean of each index |
| vegetation_pct | 100 × (zone pixels with NDVI ≥ 0.3) / (zone pixels) |
| builtup_pct | 100 × (zone pixels classified built-up) / (zone pixels) |
| water_share | 100 × (zone pixels with NDWI > 0) / (zone pixels) |

Census population and elderly share are joined by polygon containment; road length (km) is clipped to the zone polygon for road density.

## 5. Seasonal composites

- **monthly_mean_LST(z, m)** = mean of all clear-sky zone LST pixels across every scene of month m (pixel-wise mean over the month's clear masks).
- **summer_peak_LST(z)** = 95th percentile of zone LST pixels across the May–June composites of the rolling 3-year window (2023–2025 for the 2026 build).
- **monthly index composites** = pixel-wise mean of clear-sky index values per month.

## 6. Gap filling

- A zone with fewer than 3 valid scenes in the trailing 60 days is filled from MODIS MOD11A1 daily LST (1 km), bilinear-resampled to 30 m; its rows are tagged `source = 'modis_fallback'`.
- If MODIS is also unavailable for the zone, the zone is excluded from the hotspot list and marked `insufficient_data` — it is not silently scored.
- If fewer than 3 valid months exist in the 3-year summer window, `summer_peak_LST` is computed from whatever months exist and the zone's confidence tag is downgraded to `satellite_fallback`.
