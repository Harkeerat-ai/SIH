# Decision Engine (Claim Rules)

The rules engine translates model outputs + policy terms into a **recommendation**. It is
the only component that can move a claim to payout — and even then, **a human authority
sign-off always gates the payout**.

## 1. Inputs

| Input | Example | Source |
|-------|---------|--------|
| `damage_probability` | 0.83 | damage model |
| `estimated_yield_loss_pct` | 44 | damage model |
| `policy.status` | ACTIVE | policies table |
| Claim date vs `cover_start` / `cover_end` | 2026-08-12 ∈ [2026-06-01, 2026-09-30] | policies table |
| `sar_moisture_anomaly_confirmed` | false | preprocessing / field engine |
| `valid_pixel_pct` history | ≥ 30% on both anomaly acquisitions | satellite_stats |

## 2. Decision Tree

```
[Damage detected: anomaly rule fired]
                 │
                 ▼
[Policy ACTIVE and claim inside cover window?] ──No──► REJECT (no liability)
                 │Yes
                 ▼
[estimated_yield_loss_pct < 15%?] ──Yes──► AUTO_REJECT (no evidence of loss)
                 │No
                 ▼
[yield_loss > 40% AND damage_probability > 0.8 AND SAR moisture anomaly confirmed?]
        │No                                                    │Yes
        ▼                                                      ▼
FIELD_VERIFICATION (default)                    AUTO_APPROVE (recommendation only)
  · loss 15–40% or prob 0.6–0.8                  · evidence package auto-built
  · priority = HIGH if loss ≥ 30 or              · STILL requires human authority
    prob ≥ 0.75, else MEDIUM                       sign-off before any payout
```

## 3. Rules Table

| # | Condition | Recommendation | Notes |
|---|-----------|----------------|-------|
| R1 | Policy inactive or claim outside cover window | `REJECT` | Closed without evidence package |
| R2 | `yield_loss_pct < 15` | `AUTO_REJECT` | Below materiality; no evidence gathered |
| R3 | `15 ≤ yield_loss_pct ≤ 40` OR `0.6 ≤ damage_probability ≤ 0.8` | `FIELD_VERIFICATION` | Default path; priority HIGH if loss ≥ 30 or prob ≥ 0.75, else MEDIUM |
| R4 | `yield_loss_pct > 40` AND `damage_probability > 0.8` AND SAR anomaly confirmed | `AUTO_APPROVE` (recommendation) | Payout still gated by human sign-off |
| R5 | R4 thresholds met but SAR NOT confirmed | `FIELD_VERIFICATION` (HIGH) | SAR gate protects against false positives |

## 4. Worked Example

**Plot** `PLT-2026-0117` — soybean, District Dhar (MP), kharif 2026.

| Quantity | Value |
|----------|-------|
| Expected health (baseline p50) | 82% |
| Observed health (last-3 NDVI) | 46% |
| Estimated yield loss | 44% |
| Damage probability | 0.83 |
| Policy status | ACTIVE (cover Jun 1 – Sep 30) |
| Claim date | 2026-08-12 |
| SAR moisture anomaly | NOT confirmed (VH/VV decorrelated under wet spell) |

**Trace:** policy ACTIVE ✓ → loss 44% ≥ 15% ✓ → rule R4 thresholds met (44 > 40, 0.83 >
0.8) but **SAR gate fails** → rule R5 → **`FIELD_VERIFICATION`, priority HIGH**.

The evidence package (12 fields, AI confidence 91%, liability ₹24,640) is queued to the
insurer dashboard for field verification, demonstrating that even a strong ML signal
cannot bypass the confirmation and human-approval gates.

## 5. Sign-Off & Audit

- Every payout requires a `claim_decisions` row with `authority_id`, `decision =
  APPROVE`, and `notes`.
- Decisions are logged with the evidence-package hash; there is no code path that pays
  without a decision row (enforced in deployment checklist — see `deployment.md`).