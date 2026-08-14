# Database Schema (PostgreSQL 16 + PostGIS 3.4)

All geometry is stored as `geography(..., 4326)` for metre-accurate geodesic measurement; spatial joins against rasters reproject to the tile CRS (EPSG:32643–32645) on demand.

## 1. Tables

### `districts`
```sql
CREATE TABLE districts (
  id       BIGSERIAL PRIMARY KEY,
  name     TEXT UNIQUE NOT NULL,               -- e.g. 'Chandrapur'
  geometry geography(Polygon, 4326) NOT NULL
);
```

### `boundaries`
```sql
CREATE TABLE boundaries (
  id       BIGSERIAL PRIMARY KEY,
  kind     TEXT NOT NULL CHECK (kind IN ('forest', 'river', 'protected', 'lease')),
  name     TEXT NOT NULL,                       -- e.g. 'Tadoba-Andhari ESZ', 'Wainganga river'
  geometry geography(Geometry, 4326) NOT NULL
);
CREATE INDEX idx_boundaries_geom ON boundaries USING GIST (geometry);
```

### `permits`
```sql
CREATE TABLE permits (
  id          BIGSERIAL PRIMARY KEY,
  district_id BIGINT NOT NULL REFERENCES districts (id),
  holder      TEXT NOT NULL,
  polygon     geography(Polygon, 4326) NOT NULL,
  valid_from  DATE NOT NULL,
  valid_to    DATE NOT NULL CHECK (valid_to >= valid_from),
  minerals    TEXT[] NOT NULL                   -- e.g. {'sand', 'stone'}
);
CREATE INDEX idx_permits_geom  ON permits USING GIST (polygon);
CREATE INDEX idx_permits_dist  ON permits (district_id);
```

### `alert_groups`
```sql
CREATE TABLE alert_groups (
  id          BIGSERIAL PRIMARY KEY,
  geometry    geography(Polygon, 4326) NOT NULL,
  first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status      TEXT NOT NULL DEFAULT 'open'
              CHECK (status IN ('open', 'assigned', 'field_verified', 'confirmed', 'dismissed')),
  risk_score  INT NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
  suppressed  BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_alert_groups_geom   ON alert_groups USING GIST (geometry);
CREATE INDEX idx_alert_groups_status ON alert_groups (status, risk_score);
```

### `detections`
```sql
CREATE TABLE detections (
  id              BIGSERIAL PRIMARY KEY,
  alert_group_id  BIGINT NOT NULL REFERENCES alert_groups (id),
  detection_type  TEXT NOT NULL
                  CHECK (detection_type IN ('new_excavation', 'vegetation_loss',
                                            'equipment', 'access_road', 'riverbed_encroachment')),
  geometry        geography(Polygon, 4326) NOT NULL,
  area_ha         NUMERIC(10, 2) NOT NULL,
  confidence      NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  source_product  TEXT NOT NULL,                -- 'sentinel-2-l2a' | 'sentinel-1-grd'
  source_model    TEXT NOT NULL
                  CHECK (source_model IN ('unet_change', 'unet_seg', 'yolo', 'heuristic')),
  t1_date         DATE NOT NULL,
  t2_date         DATE NOT NULL
);
CREATE INDEX idx_detections_geom ON detections USING GIST (geometry);
CREATE INDEX idx_detections_ag   ON detections (alert_group_id);
```

### `risk_factors`
```sql
CREATE TABLE risk_factors (
  id           BIGSERIAL PRIMARY KEY,
  detection_id BIGINT NOT NULL REFERENCES detections (id),
  factor       TEXT NOT NULL
               CHECK (factor IN ('new_excavation_area', 'vegetation_loss', 'river_proximity',
                                 'protected_area_overlap', 'equipment_detected',
                                 'permit_status', 'expansion_rate')),
  weight       NUMERIC(4, 3) NOT NULL,
  score        NUMERIC(6, 2) NOT NULL CHECK (score BETWEEN 0 AND 100),
  UNIQUE (detection_id, factor)
);
```

### `officers`
```sql
CREATE TABLE officers (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT UNIQUE NOT NULL,
  phone       TEXT NOT NULL,
  district_id BIGINT NOT NULL REFERENCES districts (id)
);
```

### `verifications`
```sql
CREATE TABLE verifications (
  id             BIGSERIAL PRIMARY KEY,
  alert_group_id BIGINT NOT NULL REFERENCES alert_groups (id),
  officer_id     BIGINT NOT NULL REFERENCES officers (id),
  status         TEXT NOT NULL CHECK (status IN ('confirmed', 'dismissed')),
  notes          TEXT,
  field_photos   TEXT[],                        -- S3 keys: s3://imw-lake/field/{alert}.jpg
  verified_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_verifications_ag ON verifications (alert_group_id);
```

## 2. Relationships (one per line)

- `permits.district_id → districts.id` — a district has many permits.
- `detections.alert_group_id → alert_groups.id` — an alert group aggregates many detections (one per cycle).
- `risk_factors.detection_id → detections.id` — a detection has exactly 7 factor rows.
- `officers.district_id → districts.id` — a district has many officers.
- `verifications.alert_group_id → alert_groups.id` — an alert group has many verification records.
- `verifications.officer_id → officers.id` — an officer performs many verifications.

## 3. Canonical Queries

14-day dedup (decision-engine.md §3, alerting.md §5):

```sql
SELECT count(*) FROM alert_groups
WHERE ST_Intersects(geometry, ST_SetSRID(ST_MakePoint(79.21, 20.02), 4326)::geography)
  AND last_seen > now() - INTERVAL '14 days'
  AND status <> 'dismissed';
```

Permit suppression (decision-engine.md §3):

```sql
SELECT count(*) FROM permits
WHERE ST_Covers(polygon, ST_SetSRID(ST_MakePoint(79.21, 20.02), 4326)::geography)
  AND valid_from <= CURRENT_DATE AND valid_to >= CURRENT_DATE;
```

Retraining set export (alerting.md §4):

```sql
SELECT d.geometry, d.t2_date FROM detections d
JOIN alert_groups a ON a.id = d.alert_group_id
JOIN verifications v ON v.alert_group_id = a.id
WHERE v.status = 'confirmed' AND v.verified_at > now() - INTERVAL '7 days';
```