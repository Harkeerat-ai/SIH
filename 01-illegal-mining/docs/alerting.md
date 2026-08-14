# Alerting

## 1. Channels

| # | Channel | Provider | Latency target | Content | Used for |
|---|---|---|---|---|---|
| 1 | Dashboard feed | In-app (React + API) | instant | Full alert card, factor breakdown, map pin | All tiers |
| 2 | Email | SMTP (state govt domain) | < 2 min | HTML summary: alert no, risk, area, coordinates, imagery links | HIGH + MEDIUM digest |
| 3 | SMS | Twilio / national gateway | < 1 min | `ALERT MH-2026-00431 HIGH 87/100 area 2.0ha @20.02N 79.21E — verify on portal` | HIGH only |
| 4 | Mobile push (phase 2) | FCM / Web Push | < 1 min | Short alert + deep link to panel | HIGH (optional) |

Every delivery attempt is written to the feed (`GET /alerts/feed`) with channel, recipient and timestamp, so alerting is fully auditable.

## 2. Escalation Tiers

| Tier | Score | Immediate action | Cadence |
|---|---|---|---|
| HIGH | 70–100 | **SMS to the district officer** (`officers` where district matches) **+ email to the Deputy Director** | Immediate — target: risk computed 06:05 UTC → delivered ≤ 06:06 UTC |
| MEDIUM | 40–69 | **Daily digest email (18:00 IST)** listing all MEDIUM alerts with links | Daily |
| LOW | 0–39 | Dashboard feed entry only | On creation |

SLA: end-to-end from acquisition to HIGH SMS ≤ 1 minute after risk computation (pipeline runs at 06:00 UTC; SMS at 06:06 UTC in the reference scenario).

## 3. Alert Lifecycle State Machine

```
              assign officer              field check
   ┌──────────┐ ─────────────────► ┌─────────────┐ ────────────────► ┌────────────────┐
   │  OPEN    │                    │  ASSIGNED   │                   │ FIELD_VERIFIED  │
   └──────────┘                    └─────────────┘                   └────────┬───────┘
        │                                                                     │
        │  14-day quiet window (dedup, §5)                                    │
        ▼                                                                     ▼
   merged, no new alert                                      ┌────────────────┼───────────────┐
                                                             ▼                ▼               ▼
                                                       CONFIRMED      REOPENED (new      DISMISSED
                                                       → retraining   evidence: back     → hard
                                                         positive       to OPEN)         negative
                                                         label
```

Transitions and owners:

| Transition | Trigger | Owner |
|---|---|---|
| `open` | Risk engine creates alert_groups row (risk ≥ 1, not suppressed) | system |
| `open → assigned` | `POST /alert-groups/{id}/assign` | officer |
| `assigned → field_verified` | `POST /alert-groups/{id}/verify` with field evidence | officer |
| `field_verified → confirmed` | officer confirms site activity | officer |
| `field_verified → dismissed` | officer dismisses (reason required) | officer |
| `field_verified → reopened → open` | new detection evidence intersects the group after dismissal-rejection | system |
| any non-terminal → merged | new polygon intersects group > 60% within 14 days (§5) | system |

## 4. Verification → Retraining Feedback Loop

- **CONFIRMED** detections are exported weekly (database-schema.md §3) and appended as **positive training labels** for the change-detection U-Net and the 5-class segmentation model; their imagery chips join the training pool.
- **DISMISSED** alerts are appended as **hard negatives** for change detection and background samples for the segmentation / YOLO models.
- Retraining job runs when **≥ 500 new confirmed + ≥ 200 new dismissed** samples have accumulated since the last run; the promoted model must pass the acceptance gates (ml-pipeline.md §5) before deployment; the old weights stay live in degraded mode if the gate fails.
- Every cycle's confirmed polygons also feed the expansion-rate factor (decision-engine.md §1, factor 7) by giving the growth baseline ground truth.

## 5. Suppression Rules

| Rule | Condition | Effect |
|---|---|---|
| Permit suppression | Detection polygon fully inside a valid permit (decision-engine.md §3) | No alert created; detection stored `suppressed = true` |
| Dedup / quiet window | New polygon intersects an existing non-dismissed group by **> 60% of its area** and `last_seen` within **14 days** | Merge: update group geometry (union), `last_seen`, area, risk_score — **no new alert**, no SMS/email |
| Cloud-cover skip | Optical pass cloud > 30% (deployment.md §3) | No optical detections emitted that pass; SAR-only coverage continues |
| Manual dismissal | Officer dismisses with reason | Group excluded from feed, digest and dedup targets; used as hard negative |

SLA note: the quiet window prevents alert fatigue in fast-growing sites while still refreshing area/risk every cycle — a dormant site that re-activates after 14 days produces a fresh alert, and the expansion-rate factor (×5 per % growth/30d) ensures genuinely expanding sites climb toward HIGH within 2–3 cycles.