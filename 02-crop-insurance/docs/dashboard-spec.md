# Dashboard Specification

## 1. Insurer Web Dashboard (Next.js, `/insurer`)

### 1.1 District Overview — KPI Cards

| KPI | Value |
|-----|-------|
| Total farms | 48,210 |
| Potential claims | 7,831 |
| High-risk farms | 1,923 |
| Estimated loss | ₹38.4 Cr |
| AI verified | 6,742 |

### 1.2 Mockup

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CROP INSURANCE OPS · DISTRICT DHAR (MP) · kharif 2026 · [Export] [Sync]  │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐ │
│ │ Total farms│ │ Potential   │ │ High-risk   │ │ Est. loss ₹38.4 Cr    │ │
│ │  48,210    │ │ claims 7,831│ │ farms 1,923 │ │ AI verified 6,742     │ │
│ └────────────┘ └─────────────┘ └─────────────┘ └───────────────────────┘ │
│ ┌───────────────────────────────┐  ┌────────────────────────────────────┐│
│ │ MAP — plot polygons           │  │ CLAIM QUEUE (7,831)                ││
│ │ ██ healthy   ██ damaged       │  │ ▸ CLM-0442 · 44% · ⚑HIGH · VERIFY  ││
│ │ ██ high-risk ██ insufficient  │  │ ▸ CLM-0441 · 22% · MED · VERIFY    ││
│ │                               │  │ ▸ CLM-0440 ·  8% · LOW · AUTO_REJ  ││
│ │   [Layer: NDVI / NDMI / EVI]  │  │ ▸ CLM-0439 · 47% · ⚑HIGH · APPROVE ││
│ │                               │  │ ▸ CLM-0438 · 19% · MED · VERIFY    ││
│ └───────────────────────────────┘  └────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Claim Queue Behaviour

- Each row shows: claim ID, plot ID, crop, estimated loss %, priority badge
  (`⚑ HIGH` / `MED` / `LOW`), and recommendation badge (`VERIFY`, `AUTO_REJ`, `APPROVE`).
- Clicking a row opens the **evidence-package viewer**: the 12-field report, the 6
  satellite PNG strips, SHAP top-3 contributors, and a single button
  **"Approve / Reject"** that posts to `POST /claims/{id}/decision` and requires the
  authority's JWT role.
- Filters: district, crop, priority, recommendation, date range. Sort: priority then date.
- `insufficient_data` plots appear in a separate `PENDING_REVIEW` tab — never in the
  auto-claim queue.

## 2. Farmer Mobile App (React Native)

### 2.1 My Farm Screen — Mockup

```
┌──────────────────────────────┐
│ My Farm                      │
│ ┌──────────────────────────┐ │
│ │ Soybean · 0.50 ha        │ │
│ │ ██████████████░░░░ Health│ │
│ │                46%       │ │
│ │ Risk: HIGH (drought)     │ │
│ │ Est. damage: 44%         │ │
│ │ Policy: ACTIVE           │ │
│ │ Claim: IN_VERIFICATION   │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Weather risk: HIGH       │ │
│ │ Rain z-score (30d): -2.1 │ │
│ │ Temp z-score (30d): +1.3 │ │
│ └──────────────────────────┘ │
│ [  Report Damage  ]          │
│ [  View Evidence   ]         │
│ ──────────────────────────── │
│  My Farm   Claims   Weather  │
└──────────────────────────────┘
```

### 2.2 Behaviours

- **Crop health bar**: health % = observed vs baseline p50 (100% = at baseline).
- **Report Damage button**: available only when `policy_status = ACTIVE` and inside the
  cover window; posts `POST /claims`; disabled while a claim is open.
- **View Evidence**: read-only 12-field report + images (farmer-facing subset, no
  liability figure shown to farmers — liability is insurer/authority-only).
- Push notification on status changes (FILED → IN_VERIFICATION → APPROVED/REJECTED),
  plus `insufficient_data` notices explaining that no assessment was possible on cloudy
  acquisitions.