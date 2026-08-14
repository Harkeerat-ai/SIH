# LST engine

Primary path: single-channel Landsat TIRS band 10 with NDVI-threshold emissivity. Alternate path: split-window retrieval on Sentinel-3 SLSTR S8/S9 and MODIS bands 31/32, used only as fallback when Landsat coverage is unavailable.

## Constants

| Constant | Value | Source |
|---|---|---|
| M_L (band 10 radiance mult) | 3.3420e−4 W/(m²·sr·µm·DN) | Landsat C2 L1 MTL (LANDSAT 8 & 9) |
| A_L (band 10 radiance add) | 0.10000 W/(m²·sr·µm) | Landsat C2 L1 MTL |
| K1 (band 10) | 774.8853 W/(m²·sr·µm) | Landsat C2 L1 MTL |
| K2 (band 10) | 1321.0789 K | Landsat C2 L1 MTL |
| λ (effective wavelength, band 10) | 10.9 µm = 10.9e−6 m | TIRS spectral response |
| ρ (second radiation constant, c2) | 1.438e−2 m·K | Planck law constant |

## Step 1 — DN to TOA radiance

```
L = M_L · Qcal + A_L
```

Qcal is the raw 16-bit DN of TIRS band 10.

## Step 2 — Brightness temperature

```
Tb = K2 / ln(K1 / L + 1)
```

## Step 3 — Emissivity via NDVI threshold

| Condition | Emissivity ε |
|---|---|
| NDVI < 0.2 (bare soil / roof) | ε = 0.979 − 0.046 · ρ_RED |
| 0.2 ≤ NDVI < 0.5 (mixed) | linear interpolation between the two branches |
| NDVI ≥ 0.5 (full vegetation) | ε = 0.99 |

ρ_RED is the pixel's RED-band surface reflectance (0–1).

## Step 4 — Emissivity-corrected LST

```
LST = Tb / (1 + (λ · Tb / ρ) · ln ε)
```

## Worked example — bare rooftop pixel reaching 43.8 °C

Pixel from the July 2026 scene over Zone #104: DN = 35,000, RED reflectance = 0.22 (bright bare rooftop).

| Step | Computation | Value |
|---|---|---|
| 1 | L = 3.3420e−4 × 35,000 + 0.1 | 11.797 W/(m²·sr·µm) |
| 2 | K1/L = 774.8853 / 11.797 | 65.685 |
| 3 | Tb = 1321.0789 / ln(65.685 + 1) = 1321.0789 / 4.2000 | 314.54 K (41.4 °C) |
| 4 | ε = 0.979 − 0.046 × 0.22 | 0.96888 |
| 5 | ln ε | −0.031614 |
| 6 | λ·Tb/ρ = (10.9e−6 × 314.54) / 1.438e−2 | 0.238422 |
| 7 | (λ·Tb/ρ)·ln ε = 0.238422 × (−0.031614) | −0.0075375 |
| 8 | LST = 314.54 / (1 − 0.0075375) = 314.54 / 0.9924625 | 316.93 K |
| 9 | LST − 273.15 | **43.8 °C** |

This 43.8 °C pixel value is the exact input used by the vulnerability model's worked example for Zone #104 (docs/decision-engine.md).

## Alternate path — split-window retrieval (Sentinel-3 / MODIS)

Used when the zone has no usable Landsat scene in the trailing 60 days.

```
LST = T1 + a·(T1 − T2) + b·(T1 − T2)² + c·(1 − ε̄) + d·Δε
```

| Sensor | T1 | T2 | a | b | c | d |
|---|---|---|---|---|---|---|
| MODIS MOD11A1 | band 31 (11.03 µm) | band 32 (12.02 µm) | 1.02 | 0.26 | 52.4 | −0.56 |
| Sentinel-3 SLSTR | S8 (10.85 µm) | S9 (12.0 µm) | 1.15 | 0.31 | 48.0 | −0.50 |

ε̄ = (ε1 + ε2)/2 and Δε = ε1 − ε2, both from the NDVI-threshold emissivity of Step 3 (Δε = 0.005 default). The MODIS coefficient set is the Wan & Dozier (1996) generalized split-window table for view zenith ≤ 20° and water vapor ≤ 2.0 g/cm²; the SLSTR set is the ESA Level-2 LST fixed coefficient set.

Worked mini-example (MODIS): T31 = 310.0 K, T32 = 308.0 K, ε̄ = 0.980, Δε = 0.005.

```
LST = 310.0 + 1.02×2.0 + 0.26×4.0 + 52.4×0.020 − 0.56×0.005
    = 310.0 + 2.04 + 1.04 + 1.048 − 0.0028 = 314.13 K = 41.0 °C
```

## Validation and quality gates

- Validation campaign (July 2026): Landsat-derived LST compared against 5 AWS ground stations → MAE 1.1 °C, bias +0.4 °C. No bias correction applied below 1.0 °C.
- On days when both Landsat and MODIS cover the zone, the MODIS path is validated against the Landsat path; if mean |Δ| > 2.0 °C the MODIS scene is rejected for that zone and the zone is marked `insufficient_data`.
- Every LST product carries its source tag: `landsat` or `modis_fallback`, surfaced in the dashboard and API.
