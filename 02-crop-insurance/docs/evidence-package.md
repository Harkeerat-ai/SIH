# Evidence Package

Every claim ships with a **12-field automated report** so an insurer or government
authority can audit the recommendation in minutes. The package is immutable once written
(hash stored with the decision).

## 1. The 12-Field Report Schema

| # | Field | Type | Example |
|---|-------|------|---------|
| 1 | Policy ID | TEXT | `POL-2026-0117` |
| 2 | Plot centroid coords | `{lat, lon}` | `{22.6312, 75.3245}` |
| 3 | Crop | TEXT | `soybean` |
| 4 | Area | NUMERIC(6,2) ha | `0.50` |
| 5 | Expected health % | NUMERIC(5,2) | `82` |
| 6 | Observed health % | NUMERIC(5,2) | `46` |
| 7 | Estimated loss % | NUMERIC(5,2) | `44` |
| 8 | Primary indicators (✓ list) | JSON | 3 of 4 confirmed |
| 9 | Satellite evidence image count | INT | `6` |
| 10 | AI confidence % | NUMERIC(5,2) | `91` |
| 11 | Recommendation | TEXT | `FIELD_VERIFICATION` |
| 12 | Liability estimate ₹ | NUMERIC(12,2) | `24640.00` |

Liability formula: `liability = sum_assured × estimated_loss_pct / 100` —
`₹56,000 × 0.44 = ₹24,640`.

## 2. JSON Example

```json
{
  "policy_id": "POL-2026-0117",
  "plot_centroid": { "lat": 22.6312, "lon": 75.3245 },
  "crop": "soybean",
  "area_ha": 0.50,
  "expected_health_pct": 82,
  "observed_health_pct": 46,
  "estimated_loss_pct": 44,
  "indicators": {
    "ndvi_decline": true,
    "ndmi_decline": true,
    "rainfall_anomaly": true,
    "sar_moisture_anomaly": false,
    "notes": "SAR VH/VV decorrelated during wet spell; moisture anomaly unconfirmed"
  },
  "satellite_image_count": 6,
  "ai_confidence_pct": 91,
  "recommendation": "FIELD_VERIFICATION",
  "priority": "HIGH",
  "liability_inr": 24640.00
}
```

The six satellite images are 512 × 512 px PNG strips (true-colour RGB, NDVI false-colour,
NDMI false-colour) covering the plot across the anomaly window, stored at
`s3://crop-insurance/evidence/{claim_id}/`.

## 3. Field-Verification Packet

When the recommendation is `FIELD_VERIFICATION`, a field officer collects:

| Item | Requirement | Source |
|------|-------------|--------|
| GPS photos | ≥ 5 geotagged photos with EXIF timestamps within 72 h of each other | Field app |
| Crop-cutting experiment (CCE) | 3 random samples of 1 m²; fresh + dry weight; moisture % | Field app |
| Farmer acknowledgment | Aadhaar-authenticated confirmation of loss | Field app |
| Officer sign-off | Authority ID + digital signature | Field app |

### Upgrade / Downgrade Rules

| CCE loss vs estimate | Action |
|----------------------|--------|
| Within ± 5 pts of estimate | **CONFIRM** → recommendation upgraded to `AUTO_APPROVE` path (human sign-off still required) |
| ≥ 10 pts below estimate | **DOWNGRADE to REJECT** → flagged for fraud review |
| ≥ 5 pts above estimate | **UPGRADE** → payout recalculated at CCE loss |
| Photos < 5 or missing geotag | Packet invalid → re-verification within 7 days, else claim on hold |

The upgraded/downgraded recommendation is written to `claim_decisions` with the authority
ID, and the evidence-package hash is appended for tamper-evident audit.