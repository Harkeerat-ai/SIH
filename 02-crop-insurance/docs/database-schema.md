# Database Schema

PostGIS (geometry) + TimescaleDB (hypertables). All timestamps are `TIMESTAMPTZ`.

## 1. Core Tables

### farmers

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK**, default `gen_random_uuid()` |
| `name` | TEXT | NOT NULL |
| `phone` | TEXT | NOT NULL, UNIQUE |
| `aadhaar_hash` | TEXT | NOT NULL (SHA-256, salted — never raw) |
| `bank_ifsc` | TEXT | NOT NULL |
| `bank_account` | TEXT | NOT NULL |

### plots

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK**, default `gen_random_uuid()` |
| `farmer_id` | UUID | NOT NULL, **FK → farmers(id)** |
| `district_id` | INT | NOT NULL, **FK → districts(id)** |
| `crop` | TEXT | NOT NULL (soybean / paddy / cotton / wheat / mustard / maize) |
| `sowing_date` | DATE | NOT NULL |
| `area_ha` | NUMERIC(6,2) | NOT NULL, CHECK (`area_ha > 0`) |
| `polygon` | GEOMETRY(Polygon, 4326) | NOT NULL, GIST index |
| `historical_yield_kg_ha` | NUMERIC(8,1) | NOT NULL |

### policies

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK** |
| `plot_id` | UUID | NOT NULL, **FK → plots(id)** |
| `scheme` | TEXT | NOT NULL, DEFAULT `'PMFBY'` |
| `premium` | NUMERIC(10,2) | NOT NULL |
| `sum_assured` | NUMERIC(12,2) | NOT NULL |
| `season` | TEXT | NOT NULL CHECK IN (`kharif`, `rabi`, `zaid`) |
| `status` | TEXT | NOT NULL CHECK IN (`ACTIVE`, `INACTIVE`, `EXPIRED`) |
| `cover_start` | DATE | NOT NULL |
| `cover_end` | DATE | NOT NULL, CHECK (`cover_end > cover_start`) |

### satellite_stats — TimescaleDB hypertable (7-day chunks, partitioned on `acquisition_date`)

| Column | Type | Constraints |
|--------|------|-------------|
| `plot_id` | UUID | **PK part**, **FK → plots(id)** |
| `acquisition_date` | DATE | **PK part** |
| `source` | TEXT | **PK part**, CHECK IN (`S2`, `S1`) |
| `ndvi_mean` | NUMERIC(6,4) | NOT NULL, CHECK ∈ [−1, 1] |
| `ndvi_std` | NUMERIC(6,4) | NOT NULL |
| `ndmi_mean` | NUMERIC(6,4) | NOT NULL, CHECK ∈ [−1, 1] |
| `evi_mean` | NUMERIC(6,4) | NOT NULL |
| `valid_pixel_pct` | NUMERIC(5,2) | NOT NULL, CHECK (`≥ 30`) |

### baselines

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | BIGSERIAL | **PK** |
| `crop` | TEXT | NOT NULL |
| `district_id` | INT | NOT NULL, **FK → districts(id)** |
| `season` | TEXT | NOT NULL CHECK IN (`kharif`, `rabi`, `zaid`) |
| `day_of_season` | INT | NOT NULL, CHECK (1–240) |
| `ndvi_p5` / `ndvi_p50` / `ndvi_p95` | NUMERIC(6,4) | NOT NULL |
| `ndmi_p5` / `ndmi_p50` / `ndmi_p95` | NUMERIC(6,4) | NOT NULL |

UNIQUE (`crop`, `district_id`, `season`, `day_of_season`).

### weather

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | BIGSERIAL | **PK** |
| `station_id` | TEXT | NOT NULL (IMD/ERA5 grid-cell id) |
| `date` | DATE | NOT NULL |
| `rainfall_mm` | NUMERIC(6,1) | NOT NULL |
| `tmax_c` | NUMERIC(4,1) | NOT NULL |
| `tmin_c` | NUMERIC(4,1) | NOT NULL |

UNIQUE (`station_id`, `date`).

## 2. Claim Tables

### claims

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK** |
| `plot_id` | UUID | NOT NULL, **FK → plots(id)** |
| `policy_id` | UUID | NOT NULL, **FK → policies(id)** |
| `filed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT `now()` |
| `status` | TEXT | NOT NULL CHECK IN (`FILED`, `IN_VERIFICATION`, `APPROVED`, `REJECTED`, `PAID`) |

### evidence_packages

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK** |
| `claim_id` | UUID | NOT NULL, **FK → claims(id)**, UNIQUE (1:1) |
| `expected_health_pct` | NUMERIC(5,2) | NOT NULL |
| `observed_health_pct` | NUMERIC(5,2) | NOT NULL |
| `estimated_loss_pct` | NUMERIC(5,2) | NOT NULL |
| `indicators` | JSONB | NOT NULL (4 indicator booleans + notes) |
| `image_count` | INT | NOT NULL, CHECK (`≥ 0`) |
| `ai_confidence` | NUMERIC(4,3) | NOT NULL, CHECK (0–1) |
| `recommendation` | TEXT | NOT NULL CHECK IN (`REJECT`, `AUTO_REJECT`, `FIELD_VERIFICATION`, `AUTO_APPROVE`) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT `now()` |

### claim_decisions

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK** |
| `claim_id` | UUID | NOT NULL, **FK → claims(id)** |
| `authority_id` | UUID | NOT NULL, **FK → authorities(id)** |
| `decision` | TEXT | NOT NULL CHECK IN (`APPROVE`, `REJECT`, `REQUEST_MORE_EVIDENCE`) |
| `notes` | TEXT | NOT NULL |
| `decided_at` | TIMESTAMPTZ | NOT NULL, DEFAULT `now()` |

## 3. Reference Tables

### districts

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INT | **PK** |
| `name` | TEXT | NOT NULL |
| `state` | TEXT | NOT NULL |

### authorities

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | **PK** |
| `name` | TEXT | NOT NULL |
| `role` | TEXT | NOT NULL CHECK IN (`insurer`, `government`, `field_auditor`) |

## 4. Integrity Notes

- No row is ever hard-deleted from `claims` / `evidence_packages` (audit trail).
- A payout requires: `claims.status = APPROVED` **and** a `claim_decisions` row with
  `decision = APPROVE` — enforced by the application layer and the deployment checklist.