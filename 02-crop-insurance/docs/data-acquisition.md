# Data Acquisition

## 1. Source Register

| Source | Product | Resolution / Frequency | Bands / Fields Used | License / Access | Update |
|---|---|---|---|---|---|
| Sentinel-2 | L2A (BOA reflectance) | 10 m (B2, B3, B4, B8) · 20 m (B5, B6, B7, B8A, B11, B12) · 60 m (B1, B9, QA60) · 5-day revisit | B2, B3, B4, B8, B11, QA60 | ESA Copernicus, open | Every 5 days |
| Sentinel-1 | GRD IW, VV + VH | 10 m · 12-day revisit | VV, VH (VH/VV moisture proxy) | ESA Copernicus, open | Every 12 days |
| IMD | Gridded rainfall, 0.25° (≈ 27.8 km) | Daily | `rainfall_mm` | IMD / MoES, MOU | Daily, T+1 |
| ERA5 | Temperature reanalysis | 0.25° · daily tmax/tmin | `tmax_c`, `tmin_c` | ECMWF CDS | Daily, T+1 |
| State agriculture dept. | Plot/crop/season registrations | Plot polygons + sowing date | `polygon`, `crop`, `sowing_date` | Government MOU | On registration |
| PMFBY policy registry | Policy master | Policy terms | `premium`, `sum_assured`, cover window | AIC / insurer | On enrolment |

**Coverage assumption:** one 100 km × 100 km tile ≈ 10,000 km² ≈ 100,000 ha is the analysis
unit. AOI is defined by district polygons in PostGIS.

## 2. STAC Item Example (Sentinel-2 L2A)

The STAC catalog (e.g. Earth Search) is queried nightly for granules overlapping the AOI:

```json
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "S2A_MSIL2A_20260710T052905_N0510_R103_T43PGQ_20260710T085630",
  "collection": "sentinel-2-l2a",
  "datetime": "2026-07-10T05:29:05Z",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[75.00, 22.50], [75.60, 22.50], [75.60, 23.10], [75.00, 23.10], [75.00, 22.50]]]
  },
  "properties": {
    "eo:cloud_cover": 12.4,
    "s2:processing_level": "L2A",
    "s2:product_type": "S2MSI2A",
    "platform": "sentinel-2a"
  },
  "assets": {
    "B04": { "href": "s3://crop-insurance/raw/s2-l2a/2026/07/S2A_MSIL2A_20260710T052905_R103_T43PGQ/GRANULE/L2A_T43PGQ_A052905/B04.jp2", "type": "image/jp2", "gsd": 10 },
    "B08": { "href": "s3://crop-insurance/raw/s2-l2a/2026/07/S2A_MSIL2A_20260710T052905_R103_T43PGQ/GRANULE/L2A_T43PGQ_A052905/B08.jp2", "type": "image/jp2", "gsd": 10 },
    "B11": { "href": "s3://crop-insurance/raw/s2-l2a/2026/07/S2A_MSIL2A_20260710T052905_R103_T43PGQ/GRANULE/L2A_T43PGQ_A052905/B11.jp2", "type": "image/jp2", "gsd": 20 },
    "QA60": { "href": "s3://crop-insurance/raw/s2-l2a/2026/07/S2A_MSIL2A_20260710T052905_R103_T43PGQ/GRANULE/L2A_T43PGQ_A052905/QA60.jp2", "type": "image/jp2", "gsd": 60 }
  }
}
```

## 3. Data-Lake Layout (MinIO, S3-compatible)

```
s3://crop-insurance/
├── raw/
│   ├── s2-l2a/{year}/{month}/{scene_id}/      # original JP2 granules
│   ├── s1-grd/{year}/{month}/{scene_id}/      # VV + VH GeoTIFFs
│   ├── imd-rain/{year}/{month}/daily.csv      # district grid-cell values
│   └── era5-temp/{year}/{month}/daily.csv     # tmax/tmin per cell
├── processed/
│   ├── cloud-masks/{scene_id}/                # s2cloudless + QA60 union
│   ├── indices-10m/{scene_id}/                # NDVI / NDMI / EVI GeoTIFFs
│   └── zonal-stats/{acquisition_date}.parquet # field-engine output
├── models/
│   └── xgb-damage-v3.json                     # trained artifact
└── evidence/
    └── {claim_id}/                            # PNG strips + 12-field JSON report
```

## 4. Storage Estimate — 10,000 km² (100,000 ha)

**Sentinel-2 L2A (dominant cost).** One 10k km² tile per acquisition:

- 10 m bands (B2, B3, B4, B8): 4 × (10,000 × 10,000 px) × 2 B/px = 4 × 200 MB = **800 MB**
- 20 m bands (B5, B6, B7, B8A, B11, B12): 6 × (5,000 × 5,000 px) × 2 B/px = 6 × 50 MB = **300 MB**
- 60 m bands (B1, B9, QA60): 3 × (1,667 × 1,667 px) × 2 B/px ≈ 3 × 5.6 MB ≈ **17 MB**
- Scene total ≈ 1.12 GB → **≈ 0.9 GB** as JP2.

73 acquisitions/year (5-day revisit): 73 × 0.9 GB = **≈ 66 GB/year**.

**Sentinel-1 GRD IW (VV + VH).** Full frame (250 km × 170 km ≈ 42,500 km²) ≈ 1.2 GB; a
10k km² AOI is ≈ 24% of a frame → ≈ 0.3 GB/pass. 30 passes/year (12-day): 30 × 0.3 GB =
**≈ 9 GB/year**.

**Weather.** IMD + ERA5 daily extracts for ~16 grid cells: **< 5 MB/year** (negligible).

**Derived data.** 200,000 plots × 73 rows/year ≈ 14.6 M `satellite_stats` rows × ~150 B ≈
2.2 GB + ~50% index overhead ≈ **3.3 GB/year** in TimescaleDB.

**Total ≈ 66 + 9 + 3.3 + < 0.1 ≈ 78 GB/year per 10,000 km²** (≈ 85% is Sentinel-2).
A 50,000 km² state rollout ≈ **390 GB/year** — fits a 2 TB NVMe pool with 5-year retention
(≈ 2 TB).

## 5. Ingestion Cadence

| Job | Trigger | Gate |
|-----|---------|------|
| Sentinel-2 STAC pull | Nightly 02:00 UTC | `eo:cloud_cover < 80`; ≥ 80% cloud → skip scene |
| Sentinel-1 pull | Nightly 02:05 UTC | Any new GRD scene over AOI |
| IMD / ERA5 | Daily 03:00 UTC | T+1 availability |
| Plot / policy registration | Webhook on registration | Polygon validity, policy terms complete |