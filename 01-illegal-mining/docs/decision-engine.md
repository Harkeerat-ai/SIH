# Decision Engine

## 1. Risk Score — Exact Math

```
Risk = Σ (i = 1..7)  w_i · f_i        with  f_i ∈ [0, 100],  Σ w_i = 1.00
```

The raw sum is rounded to the nearest integer. All seven `f_i` are persisted per detection in `risk_factors` (database-schema.md) so officers can audit the exact breakdown.

| i | Factor `f_i` | Weight `w_i` | Score function |
|---|---|---|---|
| 1 | `new_excavation_area` | **0.20** | `min(100, area_ha × 25)` |
| 2 | `vegetation_loss` | **0.15** | `min(100, loss_ha × 50)` |
| 3 | `river_proximity` | **0.15** | 100 if < 100 m · 60 if 100–500 m · 20 if 500 m–2 km · 0 beyond |
| 4 | `protected_area_overlap` | **0.15** | 100 if polygon overlaps a protected area / ESZ · 0 otherwise |
| 5 | `equipment_detected` | **0.10** | 100 if excavator or truck detected · 60 if access road only · 0 if none |
| 6 | `permit_status` | **0.15** | 100 if unpermitted · 0 if permitted |
| 7 | `expansion_rate` | **0.10** | `min(100, area_growth_%_per_30d × 5)` |

## 2. Tiers

| Tier | Score range | Colour | Behaviour (alerting.md) |
|---|---|---|---|
| LOW | 0–39 | green | dashboard feed only |
| MEDIUM | 40–69 | orange | daily digest (18:00 IST) |
| HIGH | 70–100 | red | immediate SMS + email, ≤ 1 minute |

## 3. Permit Suppression Rule

- If the **entire** detection polygon lies inside a valid permit polygon (`valid_from ≤ today ≤ valid_to`), `f_6 = 0` **and no alert is created at all** — the detection is recorded with `suppressed = true`, and neither SMS, email nor digest includes it. Fully permitted extraction is legal activity.
- Partial overlap: `f_6 = 0` (permitted fraction) but the alert proceeds — the unpermitted portion is still actionable.
- Permit registry is synced daily (data-acquisition.md); the check runs at decision time, not ingest time, so revocations take effect immediately.

## 4. Worked Example — Risk 87 (HIGH)

Scenario: new 2.0 ha excavation near Ghugus village, Chandrapur district. T1 = 05 Jul 2026, T2 = 12 Jul 2026. Detection polygon P.

| Factor | Weight | Evidence for P | `f_i` | Contribution `w_i · f_i` |
|---|---|---|---|---|
| `new_excavation_area` | 0.20 | area = 2.0 ha | `min(100, 2.0 × 25) = 50` | 10.0 |
| `vegetation_loss` | 0.15 | 1.6 ha lost | `min(100, 1.6 × 50) = 80` | 12.0 |
| `river_proximity` | 0.15 | 85 m from Wainganga centreline | 100 (< 100 m) | 15.0 |
| `protected_area_overlap` | 0.15 | overlaps Tadoba-Andhari ESZ | 100 | 15.0 |
| `equipment_detected` | 0.10 | 1 excavator + 2 trucks (YOLO) | 100 | 10.0 |
| `permit_status` | 0.15 | no permit intersects P | 100 | 15.0 |
| `expansion_rate` | 0.10 | +23% growth / 30 days | `min(100, 23 × 5) = 100` | 10.0 |
| **Total** | **1.00** | | | **87.0** |

```
10.0 + 12.0 + 15.0 + 15.0 + 10.0 + 15.0 + 10.0 = 87.0  →  HIGH (70–100)  →  red
```

Action: alert_groups row `status = open`, `risk_score = 87`; SMS to the Chandrapur District Mining Officer + email to the Deputy Director within 1 minute (alerting.md §2).

## 5. Second Example — Risk 60 (MEDIUM)

Permitted-adjacent plot, no overlap with protected areas: area 1.6 ha (f₁ = 40), veg loss 1.0 ha (f₂ = 50), river 250 m (f₃ = 60), overlap 0, excavator present (f₅ = 100), unpermitted (f₆ = 100), +20% growth (f₇ = 100):

```
0.20·40 + 0.15·50 + 0.15·60 + 0.15·0 + 0.10·100 + 0.15·100 + 0.10·100
= 8.0 + 7.5 + 9.0 + 0 + 10.0 + 15.0 + 10.0 = 59.5  →  60  →  MEDIUM (40–69)  →  daily digest
```

## 6. Determinism and Audit

Identical inputs always produce identical scores — no randomness anywhere in the decision path. Every factor's weight and score are stored (risk_factors table) and rendered in the dashboard factor panel, so a HIGH alert can always be explained to a court or a collector in one screen.