# API Contract

Base URL: `https://api.imw.local/api/v1` · Auth: bearer token issued per district · Content-Type: `application/json`

Standard error body (all endpoints):

```json
{ "error": { "code": 404, "message": "detection 1821 not found" } }
```

Error codes used across the API: **400** malformed request body, **404** unknown resource, **422** semantically invalid values (duplicate granule, invalid status, out-of-range risk), **500** internal failure (storage/solver), **503** dependency unavailable (PostGIS/MinIO down), **409** state conflict (e.g., verify on a terminal alert).

---

## 1. POST /ingest/products

Register an incoming satellite scene and queue preprocessing.

**Request:**
```json
{
  "product_id": "S2A_T44QND_20260712T052111_L2A",
  "platform": "sentinel-2",
  "granule_id": "L2A_T44QND_A043215_20260712T052111",
  "tile": "44QND",
  "acquisition_time": "2026-07-12T05:21:11Z",
  "cloud_cover": 8.4,
  "crs": 32644,
  "bucket_key": "raw/sentinel2/S2A_MSIL2A_20260712T052111_N0600_R065_T44QND_20260712T070913.SAFE"
}
```

**Response 201:**
```json
{ "ingest_id": "ing_20260712_001", "status": "queued", "pipeline": ["preprocessing", "feature_engine", "ml_engine", "risk_engine"] }
```

**Errors:** 400 malformed JSON / missing field · 422 `granule_id` already ingested (duplicate) · 422 `cloud_cover` > 30 (rejected by cloud gate — use `force: true` to override) · 500 S3 upload failure.

---

## 2. GET /detections?district=chandrapur&status=open&risk_min=70&limit=25&offset=0

List detections with filters.

**Response 200:**
```json
{
  "count": 1,
  "items": [{
    "detection_id": 1821,
    "alert_group_id": 94,
    "alert_no": "MH-2026-00431",
    "detection_type": "new_excavation",
    "area_ha": 2.0,
    "confidence": 0.87,
    "risk_score": 87,
    "tier": "HIGH",
    "status": "open",
    "source_model": "unet_change",
    "t1_date": "2026-07-05",
    "t2_date": "2026-07-12",
    "geometry": { "type": "Polygon", "coordinates": [[[79.21, 20.02], [79.22, 20.02], [79.22, 20.03], [79.21, 20.03], [79.21, 20.02]]] }
  }]
}
```

**Errors:** 400 invalid filter key · 404 unknown `district` · 422 `risk_min` outside 0–100 · 422 `limit` > 500.

---

## 3. GET /detections/{id}

Full detail for one detection, including its alert group and factor breakdown.

**Response 200:**
```json
{
  "detection_id": 1821,
  "alert_group_id": 94,
  "alert_no": "MH-2026-00431",
  "detection_type": "new_excavation",
  "area_ha": 2.0,
  "confidence": 0.87,
  "source_product": "sentinel-2-l2a",
  "source_model": "unet_change",
  "t1_date": "2026-07-05",
  "t2_date": "2026-07-12",
  "risk_score": 87,
  "tier": "HIGH",
  "geometry": { "type": "Polygon", "coordinates": [[[79.21, 20.02], [79.22, 20.02], [79.22, 20.03], [79.21, 20.03], [79.21, 20.02]]] },
  "factors": [
    { "factor": "new_excavation_area", "weight": 0.20, "score": 50.0, "contribution": 10.0 },
    { "factor": "vegetation_loss",     "weight": 0.15, "score": 80.0, "contribution": 12.0 },
    { "factor": "river_proximity",     "weight": 0.15, "score": 100.0, "contribution": 15.0 },
    { "factor": "protected_area_overlap", "weight": 0.15, "score": 100.0, "contribution": 15.0 },
    { "factor": "equipment_detected",  "weight": 0.10, "score": 100.0, "contribution": 10.0 },
    { "factor": "permit_status",       "weight": 0.15, "score": 100.0, "contribution": 15.0 },
    { "factor": "expansion_rate",      "weight": 0.10, "score": 100.0, "contribution": 10.0 }
  ]
}
```

**Errors:** 404 detection not found.

---

## 4. GET /alert-groups?status=open&district=chandrapur&since=2026-07-01T00:00:00Z

List alert groups.

**Response 200:**
```json
{
  "count": 3,
  "items": [{
    "alert_group_id": 94,
    "alert_no": "MH-2026-00431",
    "status": "open",
    "risk_score": 87,
    "tier": "HIGH",
    "first_seen": "2026-07-12T06:05:11Z",
    "last_seen": "2026-07-12T06:05:11Z",
    "area_ha": 2.0,
    "assigned_officer_id": null,
    "geometry": { "type": "Polygon", "coordinates": [[[79.21, 20.02], [79.22, 20.02], [79.22, 20.03], [79.21, 20.03], [79.21, 20.02]]] }
  }]
}
```

**Errors:** 400 invalid filter · 404 unknown district.

---

## 5. POST /alert-groups/{id}/assign

Assign an officer to an open alert group.

**Request:**
```json
{ "officer_id": 7 }
```

**Response 200:**
```json
{ "alert_group_id": 94, "status": "assigned", "officer_id": 7, "assigned_at": "2026-07-12T09:14:02Z" }
```

**Errors:** 404 alert group not found · 404 officer not found · 409 already assigned to another officer · 409 alert already terminal · 422 `officer_id` not in the alert's district.

---

## 6. POST /alert-groups/{id}/verify

Record the field-verification outcome. Transitions `field_verified` → `confirmed | dismissed`.

**Request:**
```json
{
  "status": "confirmed",
  "notes": "Pit active; 2 excavators; no permit displayed",
  "field_photos": ["s3://imw-lake/field/mh-2026-00431-1.jpg", "s3://imw-lake/field/mh-2026-00431-2.jpg"]
}
```

**Response 200:**
```json
{ "alert_group_id": 94, "status": "confirmed", "verified_at": "2026-07-14T11:40:00Z", "queued_for_retraining": true }
```

**Errors:** 400 missing `status` · 404 alert group not found · 409 alert not in `field_verified` state · 422 `status` not in {confirmed, dismissed}.

---

## 7. GET /risk-factors/{detection_id}

Factor-level breakdown of the risk score (same payload as `detections/{id}.factors`).

**Response 200:**
```json
{
  "detection_id": 1821,
  "total_score": 87.0,
  "tier": "HIGH",
  "factors": [
    { "factor": "new_excavation_area", "weight": 0.20, "score": 50.0, "contribution": 10.0 }
  ]
}
```

**Errors:** 404 detection not found.

---

## 8. GET /dashboard/summary?district=chandrapur

Aggregates for the dashboard header.

**Response 200:**
```json
{
  "district": "chandrapur",
  "totals": { "open": 3, "assigned": 1, "field_verified": 2, "confirmed": 14, "dismissed": 5 },
  "by_tier": { "low": 6, "medium": 4, "high": 3 },
  "area_ha_total": 11.4,
  "top_alerts": ["MH-2026-00431", "MH-2026-00429", "MH-2026-00425"]
}
```

**Errors:** 404 unknown district.

---

## 9. GET /alerts/feed?since=2026-07-12T06:00:00Z

Event feed (alert creation, delivery receipts, state transitions).

**Response 200:**
```json
{
  "events": [
    { "type": "alert_created", "alert_no": "MH-2026-00431", "risk_score": 87, "tier": "HIGH", "at": "2026-07-12T06:05:11Z" },
    { "type": "channel_delivered", "alert_no": "MH-2026-00431", "channel": "sms", "to": "+91-98230-XXXXX", "at": "2026-07-12T06:05:43Z" },
    { "type": "state_change", "alert_no": "MH-2026-00431", "from": "open", "to": "assigned", "at": "2026-07-12T09:14:02Z" }
  ]
}
```

**Errors:** 400 invalid `since` timestamp.

---

## 10. GET /health

Service and capability status — used by the demo to show degraded-mode transparency.

**Response 200:**
```json
{
  "status": "ok",
  "services": { "postgis": "up", "minio": "up", "redis": "up", "celery": "up" },
  "models": { "change_detection": "heuristic", "segmentation": "heuristic", "detection": "yolo_v8" },
  "last_ingest": "2026-07-12T06:00:02Z",
  "uptime_seconds": 86400
}
```

**Errors:** 503 when PostGIS or MinIO is unreachable (with per-service detail in the body).