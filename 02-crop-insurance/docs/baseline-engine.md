# Baseline Engine

## 1. Baseline Definition

For every `(crop, district, season)` triple with **≥ 3 historical years** of cloud-free
`satellite_stats`:

- Acquisitions are aligned to **day-of-season** (day 1 = sowing date from `plots.sowing_date`).
- For each day-of-season, the **p5 / p50 / p95** quantiles of NDVI and NDMI are computed
  across all years and all plots in the district (pooled).
- The result is the **quantile envelope**: p5 = lower band, p50 = expected curve, p95 =
  upper band.

Stored in the `baselines` table, one row per `(crop, district_id, season, day_of_season)`.

## 2. Expected-Performance Curve (ASCII)

```
Crop health (NDVI) vs day-of-season — soybean · kharif · District Dhar
 1.0 ┤
     │                            .─'``'─.
 0.8 ┤                      .─''         ``─.
     │                  .─'                  `─.  ← p95
 0.6 ┤               .─'                        `─.
     │             .'            p50              `.  ← p50 (expected)
 0.4 ┤           .'                                 `.
     │          '                                    `── p5
 0.2 ┤         '   observed ═════╗                      \
     │         ╚═════════════════╝ below p5 for          `── observed
     │                           2 consecutive passes
 0.0 └────┬────┬────┬────┬────┬────┬────┬────┬────┬────
         Jun  Jun  Jul  Jul  Aug  Sep  Sep  Oct  Nov
          1    15   30   45   60   90  105  120  150   ← day of season
                     └──────────── anomaly window ─────────┘
```

## 3. Anomaly Rule

**Trigger:** the observed NDVI curve (3-acquisition mean) falls **below the p5 envelope
for ≥ 2 consecutive cloud-free acquisitions** → damage detection is triggered.

- **Secondary confirmation:** NDMI below p5 on the same acquisitions raises the anomaly
  confidence; a rainfall z-score < −1.5 over the window raises it further.
- The rule is evaluated nightly at 03:00 UTC; a plot's anomaly state persists until the
  observed curve recovers above p50 for 2 consecutive acquisitions.

## 4. Crop Season Windows

| Crop | Season | Cover Window |
|------|--------|--------------|
| Soybean | kharif | Jun 1 – Sep 30 |
| Paddy | kharif | Jun 15 – Oct 31 |
| Cotton | kharif | Jun 1 – Nov 15 |
| Wheat | rabi | Nov 1 – Mar 31 |
| Mustard | rabi | Oct 15 – Mar 15 |
| Maize (rabi) | rabi | Oct 1 – Mar 31 |
| Zaid crops | zaid | Apr 1 – Jun 15 |

Claims outside a crop's cover window are rejected by the rules engine (see
`decision-engine.md`).

## 5. Rebuild Policy

- Baselines rebuild nightly (incremental) and fully on demand via
  `POST /baselines/rebuild` (see `api-contract.md`).
- A district-season baseline requires ≥ 3 years and ≥ 500 plot-seasons of data; below
  that, the fallback heuristic applies (see `ml-pipeline.md` §5).