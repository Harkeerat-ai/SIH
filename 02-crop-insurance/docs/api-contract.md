# API Contract

Base URL: `https://api.crop-insurance.in/v1` · Auth: `Authorization: Bearer <JWT>`
(roles: `farmer`, `insurer`, `authority`, `field_auditor`).

Error codes: **400** malformed request · **404** not found · **422** validation/domain
rule violation · **500** internal error (with `trace_id`).

## 1. POST /plots — Register Plot Polygon

Request:
```json
{
  "farmer_id": "f5c0a4a9-0000-0000-0000-000000000001",
  "district_id": 1,
  "crop": "soybean",
  "sowing_date": "2026-06-10",
  "area_ha": 0.50,
  "polygon_geojson": { "type": "Polygon", "coordinates": [ [[75.32,22.63],[75.33,22.63],[75.33,22.64],[75.32,22.64],[75.32,22.63]] ] },
  "historical_yield_kg_ha": 1450
}
```
Response `201`:
```json
{ "plot_id": "PLT-2026-0117", "status": "registered" }
```
Errors: `400` missing field · `422` invalid/self-intersecting polygon or out of AOI ·
`500` storage failure.

## 2. GET /plots/{id}/health — Plot Health Snapshot

Response `200`:
```json
{
  "plot_id": "PLT-2026-0117", "crop": "soybean",
  "current_health_pct": 46, "damage_probability": 0.83,
  "estimated_yield_loss_pct": 44, "anomaly": true,
  "last_acquisition_date": "2026-08-10", "valid_pixel_pct": 87.0,
  "data_status": "ok"
}
```
Errors: `404` unknown plot · `422` `data_status = insufficient_data` (too few valid
pixels) · `500` inference failure.

## 3. GET /plots/{id}/timeseries — Plot Time Series

Response `200`:
```json
{
  "plot_id": "PLT-2026-0117",
  "series": [
    { "acquisition_date": "2026-07-20", "source": "S2", "ndvi_mean": 0.71,
      "ndvi_std": 0.05, "ndmi_mean": 0.22, "evi_mean": 0.54,
      "valid_pixel_pct": 94.0, "baseline_p5": 0.62, "baseline_p50": 0.72 },
    { "acquisition_date": "2026-07-30", "source": "S2", "ndvi_mean": 0.58,
      "ndvi_std": 0.06, "ndmi_mean": 0.10, "evi_mean": 0.41,
      "valid_pixel_pct": 87.0, "baseline_p5": 0.61, "baseline_p50": 0.71 }
  ]
}
```
Errors: `404` unknown plot · `500` query failure.

## 4. POST /claims — File a Claim

Request:
```json
{ "plot_id": "PLT-2026-0117", "policy_id": "POL-2026-0117" }
```
Response `201`:
```json
{ "claim_id": "CLM-2026-0442", "status": "FILED", "recommendation": "FIELD_VERIFICATION", "priority": "HIGH" }
```
Errors: `400` missing field · `404` plot/policy unknown · `422` policy inactive or claim
outside cover window (with `reason`) · `500` pipeline failure.

## 5. GET /claims/{id}/report — Evidence Package

Response `200` — the full 12-field report (see `evidence-package.md`), e.g.:
```json
{
  "claim_id": "CLM-2026-0442",
  "policy_id": "POL-2026-0117",
  "plot_centroid": { "lat": 22.6312, "lon": 75.3245 },
  "crop": "soybean", "area_ha": 0.50,
  "expected_health_pct": 82, "observed_health_pct": 46, "estimated_loss_pct": 44,
  "indicators": { "ndvi_decline": true, "ndmi_decline": true, "rainfall_anomaly": true, "sar_moisture_anomaly": false },
  "satellite_image_count": 6, "ai_confidence_pct": 91,
  "recommendation": "FIELD_VERIFICATION", "priority": "HIGH", "liability_inr": 24640.00,
  "evidence_image_urls": ["https://api.crop-insurance.in/v1/evidence/CLM-2026-0442/1.png"]
}
```
Errors: `404` unknown claim · `422` report not yet generated (AUTO_REJECT) · `500` fetch
failure.

## 6. POST /claims/{id}/decision — Authority Sign-Off

Request:
```json
{ "authority_id": "a9e2c1b0-0000-0000-0000-000000000009", "decision": "APPROVE", "notes": "CCE loss 43% within tolerance" }
```
Response `200`:
```json
{ "claim_id": "CLM-2026-0442", "status": "APPROVED", "decided_at": "2026-08-13T09:14:00Z" }
```
Errors: `400` missing field · `404` claim/authority unknown · `422` decision value invalid
or authority lacks role `authority` · `500` ledger failure.

## 7. GET /insurer/district-summary — District Overview

Query: `?district_id=1&season=kharif&year=2026`
Response `200`:
```json
{
  "district_id": 1, "season": "kharif", "year": 2026,
  "total_farms": 48210, "potential_claims": 7831, "high_risk_farms": 1923,
  "estimated_loss_cr": 38.4, "ai_verified": 6742,
  "claims": [
    { "claim_id": "CLM-2026-0442", "plot_id": "PLT-2026-0117", "crop": "soybean",
      "estimated_loss_pct": 44, "recommendation": "FIELD_VERIFICATION", "priority": "HIGH" }
  ]
}
```
Errors: `404` district unknown · `422` invalid season · `500` aggregation failure.

## 8. GET /farmers/{id}/dashboard — Farmer App Data

Response `200`:
```json
{
  "farmer_id": "f5c0a4a9-0000-0000-0000-000000000001", "name": "Ramesh Patidar",
  "plots": [
    { "plot_id": "PLT-2026-0117", "crop": "soybean", "area_ha": 0.50,
      "health_pct": 46, "damage_probability": 0.83, "policy_status": "ACTIVE",
      "claim_status": "IN_VERIFICATION" }
  ],
  "alerts": [ { "type": "drought", "severity": "HIGH", "message": "Rainfall 30-day z-score -2.1" } ]
}
```
Errors: `404` unknown farmer · `500` query failure.

## 9. POST /baselines/rebuild — Rebuild Baselines

Request:
```json
{ "crop": "soybean", "district_id": 1, "season": "kharif", "years": [2022, 2023, 2024, 2025] }
```
Response `202`:
```json
{ "job_id": "job_8f31c2a4", "status": "queued", "eta_minutes": 12 }
```
Errors: `400` missing field · `422` fewer than 3 years supplied · `500` queue failure.