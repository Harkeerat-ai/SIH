# Data Acquisition

## 1. Sources, Products and Revisit Cadence

| # | Source | Product | Resolution | Revisit | Format | Purpose |
|---|---|---|---|---|---|---|
| 1 | Copernicus Sentinel-1 (C-band SAR) | IW GRD, VV+VH, Level-1 | 10 m | 12 days | SAFE → GeoTIFF | All-weather change detection; excavation visibility under cloud and rain |
| 2 | Copernicus Sentinel-2 | L2A surface reflectance (S2MSI2A) | 10 / 20 / 60 m | 5 days | SAFE → COG | NDVI/NDWI, vegetation-loss measurement |
| 3 | Copernicus DEM | GLO-30 (Copernicus_DSM) | 30 m | static (one-time) | GeoTIFF | Slope/aspect, SAR terrain correction |
| 4 | OpenStreetMap | Roads, rivers, settlements | vector | continuous | GeoJSON | Access-road context for the detection model |
| 5 | State Mining Dept / District Collector | Mining lease + permit polygons | vector | quarterly sync | GeoJSON / Shapefile | `permit_status` factor and suppression |
| 6 | Forest Survey of India | Forest cover + protected-area / ESZ boundaries | vector | annual sync | GeoJSON / Shapefile | `protected_area_overlap` factor |
| 7 | Central Water Commission / NRSC | River centreline + flood-plain geometry | vector | annual sync | GeoJSON | `river_proximity` factor |
| 8 | State permit registry (API/CSV) | Holder, minerals, validity dates | table | daily sync | CSV / API | Permit validation at decision time |

Notes:
- Sentinel-2 revisit is 5 days with the A+B constellation. Sentinel-1 is 12 days per satellite; when both A and B are available the effective SAR cadence is 6 days.
- All vector sources are versioned in the data lake under `raw/vectors/` with a `synced_at` timestamp; the feature engine caches distance rasters per version.

## 2. STAC Item Schema (Example — Sentinel-2 L2A)

Every ingested product is registered as a STAC 1.0.0 Item in the collection `sentinel-2-l2a` (or `sentinel-1-grd`, `copernicus-dem`, `vectors`):

```json
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "S2A_T44QND_20260712T052111_L2A",
  "collection": "sentinel-2-l2a",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[79.03, 19.56], [79.90, 19.56], [79.90, 20.38], [79.03, 20.38], [79.03, 19.56]]]
  },
  "bbox": [79.03, 19.56, 79.90, 20.38],
  "properties": {
    "datetime": "2026-07-12T05:21:11Z",
    "platform": "sentinel-2a",
    "constellation": "sentinel-2",
    "gsd": 10,
    "eo:cloud_cover": 8.4,
    "s2:product_type": "S2MSI2A",
    "s2:mgrs_tile": "44QND",
    "s2:processing_baseline": "06.00",
    "proj:epsg": 32644,
    "view:off_nadir": 4.2
  },
  "assets": {
    "B04": {
      "href": "s3://imw-lake/raw/sentinel2/S2A_MSIL2A_20260712T052111_N0600_R065_T44QND_20260712T070913.SAFE/GRANULE/L2A_T44QND_A043215_20260712T052111/IMG_DATA/R10m/T44QND_20260712T052111_B04_10m.jp2",
      "roles": ["data"],
      "eo:bands": [{"name": "B04", "common_name": "red", "center_wavelength": 0.665, "full_width_half_max": 0.038}]
    },
    "B08": {
      "href": "s3://imw-lake/raw/sentinel2/S2A_MSIL2A_20260712T052111_N0600_R065_T44QND_20260712T070913.SAFE/GRANULE/L2A_T44QND_A043215_20260712T052111/IMG_DATA/R10m/T44QND_20260712T052111_B08_10m.jp2",
      "roles": ["data"],
      "eo:bands": [{"name": "B08", "common_name": "nir", "center_wavelength": 0.842, "full_width_half_max": 0.115}]
    },
    "SCL": {
      "href": "s3://imw-lake/raw/sentinel2/S2A_MSIL2A_20260712T052111_N0600_R065_T44QND_20260712T070913.SAFE/GRANULE/L2A_T44QND_A043215_20260712T052111/IMG_DATA/R20m/T44QND_20260712T052111_SCL_20m.jp2",
      "roles": ["data", "mask"]
    },
    "cloud-mask": {
      "href": "s3://imw-lake/processed/optical/T44QND_20260712_s2cloudless.tif",
      "roles": ["mask"]
    }
  },
  "links": [
    {"rel": "self", "href": "https://api.imw.local/stac/collections/sentinel-2-l2a/items/S2A_T44QND_20260712T052111_L2A"},
    {"rel": "collection", "href": "https://api.imw.local/stac/collections/sentinel-2-l2a"}
  ]
}
```

## 3. Data-Lake Layout

```
data-lake/                          (MinIO bucket: imw-lake)
├── raw/
│   ├── sentinel1/                  S1A_IW_GRDH_1SDV_20260705T...SAFE (VV+VH)
│   ├── sentinel2/                  S2A_MSIL2A_..._T44QND.SAFE
│   ├── dem/                        Copernicus_DSM_COG_10_N20_00_E079_00_DEM.tif
│   └── vectors/                    permits_2026Q3.geojson · forest_2026.geojson
│                                   · rivers_cwc.geojson · osm_roads.geojson
├── processed/
│   ├── sar/                        {tile}_{date}_vv_db.tif · _vh_db.tif
│   ├── optical/                    {tile}_{date}_sr_10m.tif (B2 B3 B4 B8) · _scl.tif
│   └── indices/                    {tile}_{date}_ndvi.tif · _ndwi.tif
│                                   · delta_ndvi_20260705_20260712.tif
│                                   · veg_loss_mask.tif · excavation_indicator.tif
│                                   · dist_river.tif · dist_boundary.tif · slope.tif
├── predictions/
│   ├── segmentation/               {detection_id}_excavation_mask.tif
│   ├── objects/                    {detection_id}_objects.geojson
│   └── alerts/                     alert_groups.geojson · risk_factors.json
└── models/                         change_unet.onnx · seg_deeplab.onnx · yolo_v8.pt
```

## 4. Storage Estimate — 10,000 km² (Chandrapur district complex, Maharashtra)

Arithmetic:
- **Sentinel-2 L2A ≈ 1 GB per 100×100 km tile** (10 m B2/B3/B4/B8 plus 20/60 m bands, Cloud-Optimized GeoTIFF). A 10,000 km² region spans **3 MGRS tiles** (grid-boundary crossings) → **3 GB per acquisition**. 5-day revisit → 6 passes/month; the cloud gate (≤ 30% cover) keeps ~3 acquisitions → **≈ 9 GB/month raw**.
- **Sentinel-1 IW GRD ≈ 2 GB per scene** (VV+VH, SAFE). One scene (250 × 170 km ≈ 42,500 km²) covers the region; 12-day revisit → ~3 scenes/month → **≈ 6 GB/month raw**.
- **Copernicus DEM GLO-30 ≈ 1.2 GB per 1° × 1° tile**; the region needs 2 tiles → **≈ 2.4 GB one-time**.
- **Processed 10 m rasters:** optical 4-band stack + SCL ≈ 0.9 GB per acquisition (≈ 3 GB/month); SAR dB pair ≈ 2 GB/month; indices ≈ 1 GB/month → **≈ 6 GB/month processed**.
- **Predictions** (masks + GeoJSON + alert exports) < 0.5 GB/month.

| Layer | Monthly | One-time | Notes |
|---|---|---|---|
| raw sentinel2 | 9 GB | — | after cloud-cover gate |
| raw sentinel1 | 6 GB | — | VV + VH |
| raw dem | — | 2.4 GB | static |
| processed | 6 GB | — | 10 m grids |
| predictions | 0.5 GB | — | masks, objects, alerts |
| **Total** | **≈ 21.5 GB/month** | **2.4 GB** | ≈ 260 GB/year |

All buckets are versioned and lifecycle-policed (raw SAFE archives retained 90 days; processed rasters retained 12 months; indices retained 24 months for the retraining loop).