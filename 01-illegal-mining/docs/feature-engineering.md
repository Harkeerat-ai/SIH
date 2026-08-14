# Feature Engineering

Notation: `f_t(x)` is the value of product `f` at pixel `x` on acquisition date `t`. T1 = earliest cloud-free scene, T2 = latest scene; pixels cloudy in either date are masked out of all deltas. All rasters are on the shared 10 m UTM grid (EPSG:32643–32645 by zone).

## 1. Spectral Indices

```
NDVI(x) = (NIR − R) / (NIR + R)        Sentinel-2 B8 (NIR, 842 nm), B4 (red, 665 nm)      → [−1, +1]
NDWI(x) = (G − NIR) / (G + NIR)        Sentinel-2 B3 (green, 560 nm), B8 (NIR, 842 nm)    → [−1, +1]
```

- NDVI is the primary vegetation-health channel; NDWI is the open-water / wetness channel. Both are computed on surface reflectance from the preprocessed stack.

## 2. SAR Backscatter Change

```
Δσ⁰(x) = σ⁰_dB,t2(x) − σ⁰_dB,t1(x)    [dB], computed separately for VV and VH
```

- A positive jump of several dB (bare soil / excavation reflectors vs. vegetated ground) is the SAR signature of new digging. Δσ⁰ is available even under full cloud cover, which makes it the fallback channel when optical scenes are rejected.

## 3. General Temporal Differencing

```
D(x) = f_t2(x) − f_t1(x)
```

- Applied to every single-band product: NDVI, NDWI, σ⁰_VV, σ⁰_VH, and the 5×5 local variance of σ⁰_VH (texture). All deltas share one mask: pixels with cloud in either date are excluded.

## 4. Vegetation Loss Mask

```
V(x) = 1   if  NDVI_t2(x) − NDVI_t1(x) < −0.15      (NDVI drop > 0.15)
       0   otherwise
```

- `V` is the direct evidence of land-cover destruction (forest / scrub clearing ahead of excavation). Connected components of `V` smaller than 1,000 m² are discarded as noise.

## 5. Geodesic Distances

```
dist_river(x)    = min over river centreline vertices of geodesic distance(x, v)   [m]
dist_boundary(x) = min over protected-area / lease boundary vertices of geodesic distance(x, v)  [m]
```

- Computed with the **Vincenty (WGS84 ellipsoid)** formula against `geography` columns in PostGIS, rasterized once per boundary-vector version and cached as `dist_river.tif` / `dist_boundary.tif`. Refresh policy: quarterly with the boundary sync (see data-acquisition.md).

## 6. Excavation Indicator

```
E(x) = 1  if  [ NDWI_t2(x) − NDWI_t1(x) < −0.10 ]        (water/wetness removed)
        AND [ slope(x) > 8° ]                              (terrain allows digging, excludes flood plains)
        AND [ ΔVar_VH(x) > 2 dB² ]                         (SAR texture change in 5×5 window)
       0  otherwise
```

- `E` fuses the three independent sensors of evidence (optical wetness loss, terrain, SAR texture). It is a *feature*, not a decision — the AI engine and risk engine consume it alongside model outputs.

## 7. Outputs (per monitored tile, per cycle)

| Raster | Type | Source |
|---|---|---|
| `ndvi_t1.tif`, `ndvi_t2.tif` | Float32 | Sentinel-2 B8/B4 |
| `ndwi_t1.tif`, `ndwi_t2.tif` | Float32 | Sentinel-2 B3/B8 |
| `delta_ndvi.tif`, `delta_ndwi.tif` | Float32 | D(x) |
| `delta_sar_vv_db.tif`, `delta_sar_vh_db.tif` | Float32 | Δσ⁰ (S1) |
| `veg_loss_mask.tif` | UInt8 | V(x) |
| `excavation_indicator.tif` | UInt8 | E(x) |
| `dist_river.tif`, `dist_boundary.tif` | Float32 | geodesic, cached |
| `slope.tif`, `aspect.tif` | Float32 | DEM |

All outputs land in `processed/indices/` (data-acquisition.md §3) and feed the AI engine's model inputs and the fallback heuristic (ml-pipeline.md §4).