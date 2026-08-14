# Deployment

## 1. docker-compose Services

| Service | Image (suffix) | Role | Replicas |
|---------|----------------|------|----------|
| `postgis` | `postgis/postgis:16-3.4` | Plot/policy/claim relational store + geometry | 1 |
| `timescaledb` | `timescale/timescaledb:2.17-pg16` | `satellite_stats` hypertable + `weather` | 1 |
| `minio` | `minio/minio:RELEASE.2026-06-01` | Object lake: raw/processed/evidence buckets | 1 |
| `redis` | `redis:7.4-alpine` | Celery broker + cache | 1 |
| `celery` | app image `crop-insurance-backend` | Nightly pipeline workers (ingestion → evidence) | 4 |
| `fastapi` | app image `crop-insurance-backend` | REST API (uvicorn) | 2 |
| `nextjs` | `crop-insurance-web` | Insurer dashboard | 1 |
| `mobile-backend` | `crop-insurance-mobile-api` | Farmer-app BFF + push notifications | 1 |

All services share the `crop-insurance-net` bridge network; MinIO and TimescaleDB data
volumes are persistent.

## 2. Environment Variables

| Variable | Service | Example | Secret |
|----------|---------|---------|--------|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | postgis | `crop_insurance` | Yes |
| `TIMESCALE_DB` / `TIMESCALE_USER` / `TIMESCALE_PASSWORD` | timescaledb | `satellite_stats` | Yes |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | minio | `cropadmin` | Yes |
| `MINIO_BUCKET_RAW` / `MINIO_BUCKET_PROCESSED` / `MINIO_BUCKET_EVIDENCE` | celery, fastapi | `crop-insurance-raw`, `crop-insurance-processed`, `crop-insurance-evidence` | No |
| `REDIS_URL` / `CELERY_BROKER_URL` | celery, fastapi | `redis://redis:6379/0`, `redis://redis:6379/1` | No |
| `STAC_API_URL` / `STAC_COLLECTION` | celery | `https://earth-search.aws.element84.com/v1`, `sentinel-2-l2a` | No |
| `IMD_API_KEY` | celery | `imd-****` | Yes |
| `ERA5_CDS_URL` / `ERA5_CDS_KEY` | celery | `https://cds.climate.copernicus.eu/api`, `era5-****` | Yes |
| `MODEL_PATH` | celery | `s3://crop-insurance/models/xgb-damage-v3.json` | No |
| `JWT_SECRET` / `JWT_TTL_HOURS` | fastapi, mobile-backend | rotate at install · `8` | Yes |
| `NEXT_PUBLIC_API_URL` | nextjs | `https://api.crop-insurance.in` | No |
| `PAYOUT_ENDPOINT` | fastapi | banking-core payment hook | No |

## 3. Failure Modes & Resilience

| Failure | Handling |
|---------|----------|
| Scene ingest error (network/STAC) | 3 retries with exponential backoff (60 s, 120 s, 240 s), then dead-letter queue `pipeline_dlq`; alert on-call |
| Cloud cover ≥ 80% on AOI | Acquisition **skipped entirely** (per-scene gate); plots flagged `insufficient_data` for that date |
| Plot valid pixels < 30% (3+ consecutive acquisitions in 15 days) | Excluded from auto-claim generation; surfaced as `PENDING_REVIEW` — a cloud gap can never fabricate a claim |
| Model inference failure / missing feature | Fallback heuristic (`ml-pipeline.md` §5); recommendation forced to `FIELD_VERIFICATION` |
| Celery worker crash | `task_acks_late` + idempotent tasks keyed by `(scene_id, acquisition_date)`; safe re-run |
| Evidence upload failure | Retry 3× (2^n × 60 s); claim stays `FILED`, never auto-advances without the package |
| DB outage at decision time | Decision endpoint rejects with `500`; no partial state (transactional `claims` + `claim_decisions` write) |

## 4. Human-Approval Gate — Hard Requirement in Deployment Checklist

1. Run DB migrations; verify hypertable chunks and PostGIS extension.
2. Load ≥ 3 years of `baselines`; verify ≥ 500 plot-seasons per district-season.
3. Smoke-test the nightly job end-to-end on one tile with a synthetic scene.
4. **Verify no payout path exists without a `claim_decisions` row** — grep/audit the
   payment hook; `PAYOUT_ENDPOINT` is callable only by the `fastapi` service with role
   `authority`, and only when `claims.status = APPROVED`.
5. Role-based access: `authority` role cannot be self-assigned; `insurer` role cannot sign
   off; every sign-off is audit-logged with the evidence-package hash.
6. Confirm `insufficient_data` plots and cloud-skipped acquisitions appear only in
   `PENDING_REVIEW`, never in the auto-claim queue.
7. Load-test at 200,000 plots: zonal stats ≤ 45 min, inference ≤ 10 min, dashboard
   summary ≤ 2 s (p95).
8. Backup policy: nightly MinIO + DB dumps, 30-day retention, tested restore.