# Preprocessing

## 1. Sentinel-2 Cloud Masking (s2cloudless + QA60)

- Run **s2cloudless** (lightGBM pixel classifier) at 160 m, upscale to 10 m via nearest
  neighbour.
- Combine with the **QA60** band (opaque-cloud bits 10–11, cirrus bit 1).
- **Mask rule:** a pixel is valid iff `s2cloudless_probability < 0.4` AND
  `QA60 == 0` (no opaque cloud, no cirrus).
- **Per-scene gate:** if ≥ 80% of AOI pixels are masked → the acquisition is dropped; the
  affected plots are flagged `insufficient_data` for that date and **no spectral stats are
  computed**. This prevents cloud gaps from ever producing false claims.

## 2. Atmospheric Correction

- Primary path: **L2A products** (already Sen2Cor-corrected to bottom-of-atmosphere
  reflectance, scaled 0–10,000, uint16).
- Fallback path (L1C only): run **Sen2Cor v2.11** with default rural aerosol settings and
  the 10 m grid target.
- Output contract: BOA reflectance, uint16, scale factor 10,000.

## 3. Resampling to 10 m UTM

- All bands are resampled to the **10 m grid** of the tile's UTM zone.
- Spectral bands (B5, B6, B7, B8A, B11, B12 from 20 m; B1, B9 from 60 m): bilinear.
- QA60: nearest-neighbour (never interpolate a mask).

## 4. Per-Plot Aggregation Protocol (Field Engine)

1. Clip the scene to the plot polygon via `ST_Intersection` (typical plot: 0.5 ha ≈ 50 px
   at 10 m).
2. Compute zonal statistics **only on cloud-free pixels** — the cloud mask is applied
   before any statistic.
3. **Valid-pixel threshold:** `valid_pixel_pct` = cloud-free pixels ÷ total pixels in the
   plot. If `< 30%` → **no stats row**; the plot is flagged `insufficient_data`.
4. A `satellite_stats` row is appended only when `valid_pixel_pct ≥ 30%`.
5. Plots with 3+ consecutive `insufficient_data` acquisitions within 15 days are
   **excluded from auto-claim generation** and surfaced to the insurer as `PENDING_REVIEW`.

**Rationale:** the 30% floor guarantees every statistic is computed on a representative
cloud-free sample, so cloud gaps can never masquerade as crop damage.

## 5. Sentinel-1: SAR Preprocessing

- **Radiometric calibration** to backscatter σ° (dB) using the orbit state vector and
  calibration file (`calibration/calibration-s1-iw-grd-vv-*.xml`).
- **Terrain correction** (SRTM 30 m) to remove layover/shadow effects.
- **Speckle filter:** 5×5 Lee filter on both VV and VH.
- **Moisture proxy:** `ms_proxy = σ°_VH / σ°_VV` ratio and `σ°_VH (dB)`, aggregated per plot
  with the same 30% valid-pixel rule.
- SAR is used **only as a confirmatory signal** in the decision engine — it never triggers
  damage on its own (decorrelation under rain makes it unreliable as a primary source).

## 6. Validation Gates (Pre-Append)

| Gate | Rule | Action |
|------|------|--------|
| Scene cloud cover | ≥ 80% of AOI masked | Skip scene entirely |
| Plot valid pixels | < 30% | Flag `insufficient_data`, no stats row |
| Geometry validity | Polygon not simple, self-intersecting, or outside AOI | Reject at registration (HTTP 422) |
| Value bounds | Index outside [−1, 1] | Mark corrupt, retry scene once, else quarantine |