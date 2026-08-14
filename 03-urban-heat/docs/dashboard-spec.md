# Planning dashboard specification

The dashboard is the single screen a government planner uses to decide where to spend heat-mitigation money. It is a GIS application (MapLibre GL over PostGIS vector tiles) with a KPI bar, a zone detail drawer, and a plan-generation workflow.

## Layout (ASCII mockup)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ URBAN HEAT PLANNER — Navi Mumbai                [date: Jul 2026 ▾] [tier ▾] [Export]│
├──────────────────────────────────────────────────────────────────────────────────┤
│ █ HOTSPOTS 128    █ POPULATION AT RISK 1.4M    █ PRIORITY ZONES 27    BUDGET 62% │
├───────────────────────────────────────────────┬──────────────────────────────────┤
│                                               │ ┌─ ZONE DETAIL — Zone #104 ─────┐ │
│              GIS HEAT MAP                     │ │ Vulnerability  87 HIGH  (Jul) │ │
│                                               │ │ LST 43.8 °C · vegetation 7%   │ │
│   ═════════════════════════════════════       │ │ building 82% · pop 18,000/km² │ │
│   ═══░░░░░░░░░░░░░░░░░░░░░░░░░░════          │ │ water 18% · road 10 km/km²    │ │
│   ═══░░░░░░░░░░░░▓▓▓▓▓▓▓▓░░░░░░════          │ │ ── Recommended interventions ─│ │
│   ═══░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓░░░░════  ← Z104  │ │ ✓ cool roofs 18,000 m² ₹63.0L │ │
│   ═══░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓░░░░════   hotspot │ │ ✓ trees 1,200       ₹14.4L   │ │
│   ═══░░░░░░░░░░░░░░░░░░░░░░░░░░════          │ │ ✓ pavement 4,500 m² ₹20.3L   │ │
│   ═════════════════════════════════════       │ │ Total ₹97.7L · ΔLST −1.5 °C  │ │
│                                               │ │ new vulnerability 69 (−18)    │ │
│   ███ HIGH    ▓▓ MEDIUM    ░░ LOW             │ │ [Simulate]  [Add to Plan]     │ │
│   (tier-colored zone polygons)                │ └───────────────────────────────┘ │
├───────────────────────────────────────────────┴──────────────────────────────────┤
│ SIMULATOR PANEL — Zone #104        Model estimate, not guaranteed physical outcome│
│ trees [============●] 1,200    cool roofs [======●] 18,000 m²   pavement [●●●●]  │
│ ΔLST −1.5 °C → new vulnerability 69            [Generate Mitigation Plan]        │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## KPI bar

| KPI | Value | Definition |
|---|---|---|
| HOTSPOTS | 128 | zones with tier HIGH on the selected date (query: GET /hotspots) |
| POPULATION AT RISK | 1.4M | sum of population over HIGH zones |
| PRIORITY ZONES | 27 | HIGH zones ranked in the top decile of `score × population` |
| BUDGET | 62 % | allocated_inr / amount_inr across active budget schemes |

## GIS heat map

- Zone polygons colored by tier: LOW green (#2E7D32), MEDIUM orange (#F57C00), HIGH red (#C62828); opacity by score.
- Hotspot clusters: aggregate HIGH zones within 2 km into numbered bubbles (e.g., "12"); clicking a bubble zooms in.
- Basemap: light OSM tiles; overlay: summer_peak_LST raster (30 m) at 40 % opacity, toggleable.
- Clicking any zone opens the zone detail drawer.

## Zone detail drawer

Contents, top to bottom:

1. Header: zone name, tier badge, score, date, confidence tag (`satellite` / `satellite_fallback` / `threshold_fallback`).
2. Metrics grid: LST mean / LST p95 / vegetation % / building % / water % / road density / population density / elderly share.
3. Factor breakdown bar chart (7 factors, each showing w_i, n_i, contribution — e.g., temperature 0.40 × 94.0 = 37.6).
4. Recommended interventions table: type, quantity, unit, cost (INR), ΔLST — from GET /optimize.
5. Cost table summary: total cost, ΔLST, new vulnerability (87 → 69).
6. Buttons: **Simulate** (opens the simulator panel pre-filled) and **Add to Plan**.

## Generate Mitigation Plan workflow

1. Planner clicks **Simulate** on a zone; the simulator panel opens with optimizer defaults.
2. Planner adjusts sliders; the panel re-runs POST /simulate on each change and shows ΔLST + new vulnerability; the banner "Model estimate, not guaranteed physical outcome" is always visible.
3. Planner clicks **Add to Plan** — the simulated interventions accumulate in the plan tray (count badge on the tray).
4. Planner clicks **Generate Mitigation Plan** → POST /plans with the plan payload; the response (plan_id, total_cost, est_delta_lst) is confirmed; a plan card appears in the plan tray.
5. **Export** produces a PDF/XLSX: per-zone intervention table, cost table, simulated ΔLST, new vulnerability, and the confidence/estimate disclaimer on every page.

## Design rules

- Every simulated number carries the disclaimer; the confidence tag is rendered as a small chip next to every satellite-derived number.
- Zones with `insufficient_data` are shown hatched (not green) so absence of data is never read as "safe".
- All KPIs derive from the API endpoints in docs/api-contract.md; the dashboard renders, it never computes.