# Preprocessing

Input: raw SAFE / GeoTIFF granules. Output: 10 m UTM-grid GeoTIFFs (Float32 for reflectance and dB backscatter, UInt8 for masks), plus DEM derivatives. Every step is deterministic; every output carries `proj:epsg`, `datetime` and `granule_id` in its STAC record.

## 1. Sentinel-1 (SAR) Pipeline — Exact Steps

Executed per IW GRD scene (VV + VH), in order:

| # | Step | Method / Parameters | Output |
|---|---|---|---|
| 1 | Orbit correction | Precise Orbit Ephemerides (POE, ±5 cm) applied to state vectors | corrected metadata |
| 2 | Thermal noise removal | ESA IW GRD thermal noise correction (per-swath polynomial) | noise-corrected σ⁰ |
| 3 | Radiometric calibration | σ⁰ → γ⁰: `γ⁰ = σ⁰ / cos(θ_inc)`, where θ_inc is the local incidence angle | calibrated γ⁰ (linear, Float32) |
| 4 | Terrain correction | Range-Doppler, Copernicus GLO-30 DEM, pixel spacing 10 m, output CRS = UTM zone of scene centroid | terrain-corrected γ⁰ |
| 5 | Speckle filtering | **Refined Lee filter, window 5×5, 1 iteration**, applied to VV and VH independently | filtered γ⁰ |
| 6 | dB conversion | `σ⁰_dB = 10 · log10(γ⁰_lin)`; values clipped to **[−25, +5] dB**; no-data = −9999 | `{tile}_{date}_vv_db.tif`, `_vh_db.tif` (Float32) |
| 7 | Co-registration | Master = earliest available scene in the tile stack; slaves resampled to the master grid (bilinear for intensity) | time-aligned stack |

## 2. Sentinel-2 (Optical) Pipeline — Exact Steps

| # | Step | Method / Parameters | Output |
|---|---|---|---|
| 1 | Cloud masking | **s2cloudless** on L2A reflectance + SCL; probability threshold **0.4**; pixels ≥ 0.4 flagged cloud; scene rejected if `eo:cloud_cover > 30%` (cloud-cover policy, see deployment.md) | `{tile}_{date}_s2cloudless.tif` (UInt8 mask) |
| 2 | Atmospheric correction | Only for L1C inputs: **sen2cor** (ESA) with standard aerosol retrieval (AOT from dark dense vegetation, CAMS fallback). L2A products are used as-is | surface reflectance |
| 3 | Grid alignment | Resample B2 (blue), B3 (green), B4 (red), B8 (NIR) native 10 m, and B11, B12 (SWIR) native 20 m, onto the shared **10 m UTM grid**; SCL resampled by nearest neighbour | `{tile}_{date}_sr_10m.tif` (B2 B3 B4 B8 B11 B12), `_scl.tif` |
| 4 | Scene classification | Keep SCL classes for the feature engine: 3 vegetation, 4 bare soil, 5 water, 6 unclassified, 7/8/9 cloud, 10 cirrus, 11 snow | SCL band |

## 3. Resampling Rules

| Product | Interpolator | Rationale |
|---|---|---|
| Optical reflectance (B2, B3, B4, B8, B11, B12) | **Bilinear** | Preserves radiometry, smooth edges |
| Masks (SCL, cloud mask) | **Nearest neighbour** | Preserves class identity |
| SAR dB intensity (after step 5) | **Bilinear** on calibrated float | Speckle already filtered |
| DEM (to 10 m) | **Bilinear** | Smooth terrain derivatives |

## 4. Target CRS

- Rule: `UTM zone = floor((lon_centroid + 180) / 6) + 1`; EPSG code = `32600 + zone` (WGS 84).
- India coverage: zones 42–46; core supported codes for the pilot are **EPSG:32643, EPSG:32644, EPSG:32645** (UTM 43N–45N).
- Demo region (Chandrapur district, ~79.3°E) → zone 44 → **EPSG:32644**.
- Vector overlays (permits, boundaries) are stored in PostGIS as `geography(...,4326)` and reprojected to the tile CRS at query time (see database-schema.md).

## 5. DEM Derivatives

| Product | Method | Parameters | Use |
|---|---|---|---|
| `slope.tif` | **Horn's method**, degrees | GLO-30, resampled to 10 m (bilinear) | Excavation indicator (slope > 8°); terrain context |
| `aspect.tif` | Degrees from north | GLO-30, 10 m | Context band for segmentation model |

Deterministic processing order: DEM → S1 (uses DEM) → S2 → indices (see feature-engineering.md). Preprocessing runs as a Celery task chain keyed by `(granule_id, tile)` so re-runs are idempotent and never duplicate work.