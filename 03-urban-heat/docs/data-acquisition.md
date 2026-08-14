# Data acquisition

## Source register

| Source | Sensor / bands | Revisit | Resolution | Bands used | Role |
|---|---|---|---|---|---|
| Landsat 8/9 OLI+TIRS (USGS, Collection 2 L1) | OLI VNIR-SWIR + TIRS thermal | 16 days | 30 m optical / 100 m thermal | B3 GREEN, B4 RED, B5 NIR, B6 SWIR1, B10 TIRS | LST engine (primary); NDVI/NDBI/NDWI |
| Sentinel-2 MSI (ESA L2A) | VNIR-SWIR | 5 days | 10 m (B2/B3/B4/B8) | B2 BLUE, B3 GREEN, B4 RED, B8 NIR | Land-cover segmentation (optional) |
| Sentinel-3 SLSTR | S8/S9 thermal | 2 days | 1 km | S8 10.85 µm, S9 12.0 µm | Split-window LST fallback |
| MODIS MOD11A1 (NASA) | MODIS bands 31/32 | daily | 1 km | LST, QC | Daily LST fallback / gap filling |
| Census (Govt. of India 2011 + 2024 projections) | — | decadal | ward/block | population, age structure | Population density, elderly share |
| Building footprints (OSM) | — | quarterly | polygon | geometry | Building density factor; roof-area capacity for cool roofs |
| Road network (OSM) | — | quarterly | line | geometry | Road density factor; pavement-area capacity |
| Health vulnerability data (district health surveys) | — | annual | district | heat-illness incidence, age 60+ rates | Elderly / health risk factor |

## STAC ingestion

Every scene is discovered and fetched through a STAC catalog. The item below is the unit of ingestion (Landsat 9 Collection 2 Level-1, Mumbai frame, July 2026):

```json
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "LC09_L1TP_144046_20260712_20260712_02_T1",
  "collection": "landsat-c2-l1",
  "datetime": "2026-07-12T04:53:21Z",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[72.5, 18.9], [72.9, 18.9], [72.9, 19.3], [72.5, 19.3], [72.5, 18.9]]]
  },
  "bbox": [72.5, 18.9, 72.9, 19.3],
  "properties": {
    "eo:cloud_cover": 12.4,
    "platform": "LANDSAT_9",
    "landsat:collection_category": "T1",
    "landsat:wrs_path": 144,
    "landsat:wrs_row": 46
  },
  "assets": {
    "green":   { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_SR_B3.TIF", "type": "image/tiff; application=geotiff" },
    "red":     { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_SR_B4.TIF", "type": "image/tiff; application=geotiff" },
    "nir":     { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_SR_B5.TIF", "type": "image/tiff; application=geotiff" },
    "swir1":   { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_SR_B6.TIF", "type": "image/tiff; application=geotiff" },
    "thermal": { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_ST_B10.TIF", "type": "image/tiff; application=geotiff" },
    "qa":      { "href": "s3://uh-planner-lake/raw/landsat/2026/07/LC09_L1TP_144046_20260712_QA_PIXEL.TIF", "type": "image/tiff; application=geotiff" }
  },
  "links": []
}
```

Ingestion rule: scenes with `eo:cloud_cover > 70` are skipped entirely. Derived products (monthly LST, indices) are published back to the same STAC catalog with their own item records.

## Data lake layout

```
s3://uh-planner-lake/
├── raw/
│   ├── landsat/{year}/{month}/LC09_*.TIF       # SR bands + B10 + QA_PIXEL (COG)
│   ├── sentinel2/{year}/{month}/S2A_*.tif      # 4-band 10 m stack (COG)
│   ├── sentinel3/{year}/{month}/SLSTR_*.nc     # S8/S9 brightness temperature
│   └── modis/MOD11A1/{year}/{doy}/MOD11A1.*.tif # LST + QC
├── derived/
│   ├── lst/monthly/{yyyy-mm}/lst_mean_30m.tif   # monthly mean LST (30 m, float32)
│   ├── lst/summer_peak/{year}/lst_p95_30m.tif   # May–June p95 LST
│   ├── indices/{ndvi,ndbi,ndwi}/{yyyy-mm}/      # monthly index composites (30 m)
│   ├── landcover/{yyyymmdd}/lc_6class_10m.tif   # segmentation output (optional)
│   └── zone_stats/{yyyy-mm}/zones.parquet       # per-zone statistics
└── stac/
    ├── catalog.json                             # STAC catalog of derived products
    └── collections/{landsat-lst,indices,landcover}.json
```

## Storage estimate — 10,000 km² coverage

Arithmetic (10,000 km² = 10⁴ km² × 10⁶ m²/km² = 10¹⁰ m²):

- Pixels at 30 m: 10¹⁰ / 900 = 11,111,111 ≈ 11.1 M pixels.
- LST composite (float32, 1 band): 11.1 M × 4 B = **44.4 MB** per scene.
- Landsat 16-day revisit → 23 overpasses/yr; ~50 % cloud-free → 12 usable scenes → 12 × 44.4 MB = **0.53 GB/yr**.
- Indices (3 bands × float32 × 30 m): 3 × 44.4 MB = 133 MB/month → **1.6 GB/yr**.
- Sentinel-2 10 m (pixel 100 m²): 10¹⁰ / 100 = 100 M pixels × 2 B = 200 MB/band → 800 MB per 4-band scene; 73 overpasses/yr, ~30 cloud-free → **24 GB/yr** (cold tier, retained for segmentation retraining).
- MODIS 1 km (pixel 10⁶ m²): 10,000 pixels → 40 KB/scene; 365 daily scenes → **15 MB/yr** (fallback only).
- Zone statistics: 1,500 zones × 12 months × 24 fields × 4 B = **1.7 MB/yr**.

| Tier | Contents | Annual growth |
|---|---|---|
| Hot (PostGIS + MinIO hot) | monthly LST, indices, zone stats | ≈ 2.2 GB/yr |
| Cold (MinIO cold bucket) | raw Landsat, Sentinel-2 stacks, MODIS, SLSTR | ≈ 25 GB/yr |
| Meta (PostgreSQL) | STAC catalog, zone metrics, scores, plans | < 50 MB/yr |
