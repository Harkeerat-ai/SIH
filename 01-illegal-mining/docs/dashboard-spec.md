# Dashboard Specification

Single-page web app (React + MapLibre GL) for the District Mining Officer and the Deputy Director. Shows the district live, the alert feed, and the full verification workflow.

## 1. Map Layers

| # | Layer | Source | Style | Toggle |
|---|---|---|---|---|
| 1 | Basemap | OSM raster tiles | default streets | always on |
| 2 | District boundary | `districts` table | dashed grey outline | on |
| 3 | Permit polygons | `permits` table | hatched green fill (valid), grey (expired) | on |
| 4 | Protected areas / ESZ | `boundaries` kind='protected' | hatched amber fill + red outline | on |
| 5 | Rivers | `boundaries` kind='river' | blue polyline | on |
| 6 | Forest cover | `boundaries` kind='forest' | green fill | on |
| 7 | Detection polygons | `detections` table | fill + outline coloured by tier: green 0–39, orange 40–69, red 70–100 | on |
| 8 | Alert clusters | `alert_groups` open/assigned only | numbered cluster circles, size ∝ risk | on |
| 9 | Cloud mask (debug) | `processed/optical/*_s2cloudless.tif` | translucent white hatch | off |
| 10 | SAR Δσ⁰ (debug) | `indices/delta_sar_*_db.tif` | blue-red ramp | off |

Interaction: click a detection polygon or cluster → alert detail panel (below).

## 2. Alert Detail Panel — Alert #MH-2026-00431

| Field | Value |
|---|---|
| Alert ID | **MH-2026-00431** (state-code + year + sequence) |
| Risk | **87 / 100 — HIGH** (red pill) |
| Location | Ghugus village, Chandrapur district · 20.02°N, 79.21°E |
| Area | **2.0 ha** new excavation |
| Detected factors | ☑ Unpermitted mining · ☑ 1.6 ha vegetation loss · ☑ 85 m from Wainganga river · ☑ Overlaps Tadoba-Andhari ESZ · ☑ Excavator + 2 trucks detected · ☑ +23% growth in 30 days |
| Confidence | 0.87 (`unet_change` + `yolo`; badge shows `source_model`) |
| Imagery | Before: 05 Jul 2026 · After: 12 Jul 2026 · **[Compare Images ▾]** opens a swipe slider (T1 vs T2 true-colour + change mask overlay) |
| Status | OPEN · first seen 12 Jul 2026 06:05 UTC |
| Actions | **[Generate Inspection Report]** (PDF: factors, coordinates, imagery links, permit status, suggested action) · **[Assign Officer ▾]** (officer dropdown from `officers` for this district) · **[Mark Verified]** (opens form: status confirmed/dismissed, notes, field photos) |

## 3. Officer Workflow States

| State | Who | What happens | Exit |
|---|---|---|---|
| `open` | system | Risk computed; HIGH → SMS + email already sent; panel shows red alert | officer assigns self or delegate |
| `assigned` | officer | Officer owns the alert; 48 h SLA counter displayed; field visit scheduled | field check recorded via **[Mark Verified]** |
| `field_verified` | officer | Field evidence (photos, notes) attached; system awaits final decision | officer selects confirmed / dismissed |
| `confirmed` | system | Polygon → retraining positive label; alert archived with audit trail | — (terminal) |
| `dismissed` | officer | Polygon → hard negative for retraining; alert excluded from feed; `dismissed` reason required | — (terminal) |

Header badges per state: OPEN (red), ASSIGNED (blue), FIELD_VERIFIED (purple), CONFIRMED (green), DISMISSED (grey).

## 4. ASCII Mockup (Map + Side Panel)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  ILLEGAL MINING EARLY WARNING SYSTEM — CHANDRAPUR DISTRICT   [live] [12 Jul 2026]│
├────────────────────────────────────────────┬─────────────────────────────────────┤
│                                            │ ┌─ ALERT #MH-2026-00431 ──────────┐ │
│   MAP VIEWPORT (MapLibre GL)               │ │ RISK 87/100        ● HIGH  red  │ │
│                                            │ ├─────────────────────────────────┤ │
│   ═══ Tadoba-Andhari ESZ ═══               │ │ Location  Ghugus, Chandrapur    │ │
│        ╭──────────────────╮                │ │            20.02N 79.21E        │ │
│        │  P (red, HIGH)   │                │ │ Area      2.0 ha new excavation │ │
│        ╰──────────────────╯                │ ├─────────────────────────────────┤ │
│           ~~ Wainganga river ~~            │ │ ☑ Unpermitted mining            │ │
│                                            │ │ ☑ 1.6 ha vegetation loss        │ │
│        ░░░ permit (green hatch) ░░░        │ │ ☑ 85 m from river               │ │
│                                            │ │ ☑ Overlaps ESZ                  │ │
│                                            │ │ ☑ Excavator + 2 trucks          │ │
│                                            │ │ ☑ +23% growth / 30 days         │ │
│                                            │ ├─────────────────────────────────┤ │
│                                            │ │ Confidence 0.87                 │ │
│                                            │ │ Before 05 Jul · After 12 Jul    │ │
│                                            │ │ [ Compare Images ▾ ]            │ │
│                                            │ ├─────────────────────────────────┤ │
│                                            │ │ [Generate Inspection Report]    │ │
│                                            │ │ [Assign Officer ▾] [Mark Verified│ │
│                                            │ └─────────────────────────────────┘ │
│  Layers: ☑ Detections  ☑ Permits  ☑ ESZ   │                                     │
│          ☑ Rivers  ☐ Cloud mask  ☐ Δσ⁰    │  FEED  MH-2026-00431 · HIGH · 87    │
│                                            │        MH-2026-00429 · MED · 61     │
│  Zoom 14 · 20.02N 79.21E                   │        MH-2026-00425 · LOW · 22     │
└────────────────────────────────────────────┴─────────────────────────────────────┘
```

## 5. Non-Functional Requirements

- Loads the district view in < 3 s on a 4G connection (vector tiles, COG pyramids).
- Panel renders every factor with its weight and contribution — auditable at a glance (decision-engine.md §6).
- Field photos upload to `s3://imw-lake/field/`; report PDF generated server-side and linked.
- All state changes visible in the feed (`GET /alerts/feed`, api-contract.md §9).