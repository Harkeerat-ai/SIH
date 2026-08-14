# Deployment

Single-node docker-compose deployment (scales to multi-node via the same images).

## Services

| Service | Image | Port | Volume | Purpose |
|---|---|---|---|---|
| postgis | postgis/postgis:16-3.4 | 5432 | postgis_data | zones, scores, plans, budgets (docs/database-schema.md) |
| minio | minio/minio:latest | 9000 (API), 9001 (console) | minio_data | data lake: raw COGs, derived rasters, STAC catalog |
| redis | redis:7-alpine | 6379 | — | Celery broker + result backend |
| celery | backend:1.0 (built from backend/Dockerfile) | — | — | async ingestion, LST, zonal-statistics workers |
| fastapi | backend:1.0 | 8000 | — | REST API (docs/api-contract.md), serves the frontend build |
| frontend | frontend:1.0 (nginx, built from web/dashboard/Dockerfile) | 3000 → 80 | — | static dashboard bundle, proxies /api to fastapi |

Network: single bridge `uh-planner-net`; only fastapi and minio console are published to the host.

## Environment variables

| Variable | Service | Example | Purpose |
|---|---|---|---|
| DATABASE_URL | fastapi, celery | postgresql://planner:uhp2026!@postgis:5432/uh_planner | PostGIS connection string |
| MINIO_ENDPOINT | fastapi, celery | minio:9000 | object store endpoint |
| MINIO_ACCESS_KEY | fastapi, celery | uh-planner | S3 access key |
| MINIO_SECRET_KEY | fastapi, celery | (rotated secret from vault) | S3 secret key |
| MINIO_BUCKET | fastapi, celery | uh-planner-lake | data lake bucket |
| REDIS_URL | celery | redis://redis:6379/0 | Celery broker/backend |
| STAC_URL | celery | https://earth-search.aws.element84.com/v1 | Landsat/Sentinel-2 discovery catalog |
| CELERY_MAX_RETRIES | celery | 3 | per-task retry count |
| CELERY_RETRY_BACKOFF_S | celery | 30 | exponential backoff base (30, 120, 480 s) |
| CELERY_DLQ_QUEUE | celery | lst_ingest_dlq | dead-letter queue for failed tasks |
| API_CORS_ORIGINS | fastapi | http://localhost:3000 | dashboard origin allowlist |
| LOG_LEVEL | all | INFO | logging verbosity |

## Failure modes and mitigations

| Failure | Trigger | Mitigation | Confidence tag |
|---|---|---|---|
| Clouded Landsat pass | district > 70 % cloud cover for the monthly pass | Fall back to MODIS MOD11A1 daily LST (1 km) bilinear-resampled to 30 m | satellite_fallback |
| Persistent LST gaps | < 3 valid scenes in trailing 60 days | Temporal gap-fill: median of ±16-day window; if still < 3 scenes → zone marked insufficient_data, excluded from hotspots | insufficient_data |
| Ingestion task failure | download/parse error | Celery retry ×3 with exponential backoff (30 s, 120 s, 480 s); after 3rd failure → dead-letter queue (lst_ingest_dlq) with scene_id for operator replay | — |
| Sentinel-2 outage | source catalog unreachable | Land-cover falls back to NDBI/NDVI thresholds; builtup_pct tagged threshold_fallback | threshold_fallback |
| Solver failure | optimizer/simulator exception | Return HTTP 500 with error envelope; dashboard keeps last cached simulation, marks it stale | estimate (stale) |
| PostGIS down | database unreachable | /healthz returns 503; fastapi serves cached dashboard summary from MinIO snapshot; full recovery on restart with WAL replay | — |
| Storage full | hot bucket > 90 % | Cold-tier policy: raw Landsat/S2 moved to cold bucket after 90 days; LST/indices composites always retained hot | — |

## Health and operations

- `/healthz` (liveness) and `/readyz` (readiness: postgis, minio, redis reachable) on fastapi.
- Celery queues: `ingest`, `lst`, `stats`, `dlq`; concurrency 4 workers, prefetch 1.
- Monthly cron (inside celery beat): trigger monthly Landsat acquisition → LST → features → stats → vulnerability → optimizer; results upsert into PostGIS and are visible in the dashboard the same day.
- Backup: postgis nightly pg_dump to minio (uh-planner-lake/backups/), retained 30 days.