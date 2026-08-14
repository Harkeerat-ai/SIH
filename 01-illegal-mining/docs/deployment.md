# Deployment

## 1. docker-compose Service Stack

| Service | Image | Purpose | Ports |
|---|---|---|---|
| `db` | `postgis/postgis:16-3.4` | PostGIS 16: alert groups, detections, permits, officers, verifications | 5432 |
| `minio` | `minio/minio:latest` | S3-compatible data lake: raw/, processed/, predictions/, models/ | 9000 (API) · 9001 (console) |
| `redis` | `redis:7-alpine` | Celery broker + result backend + dead-letter list | 6379 |
| `celery-worker` | `app:latest` (backend image) | Executes preprocess / features / ml / risk / alert task chains | — |
| `celery-beat` | `app:latest` | Schedules the 06:00 UTC ingest cron and the 18:00 IST daily digest | — |
| `api` | `app:latest` (uvicorn) | REST API — api-contract.md endpoints | 8000 |
| `frontend` | `nginx:1.27` | Serves the dashboard static build + reverse-proxies /api | 8080 → 80 |

One `app:latest` image runs `celery-worker`, `celery-beat` and `api` via different entrypoints; ML weights are mounted from MinIO into `celery-worker` at `/models`.

## 2. Environment Variables

| Variable | Service | Purpose |
|---|---|---|
| `DATABASE_URL` | api, worker | `postgresql://imw:pass@db:5432/imw` |
| `REDIS_URL` | worker, beat | `redis://redis:6379/0` |
| `S3_ENDPOINT` | worker | `http://minio:9000` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | worker | MinIO credentials |
| `S3_BUCKET` | worker | `imw-lake` |
| `SENTINEL_CLIENT_ID` / `SENTINEL_CLIENT_SECRET` | worker | Copernicus Data Space OAuth client |
| `SENTINEL_CLOUD_MAX` | worker | Cloud-cover gate, default `30.0` (%) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | worker | Email delivery (state govt SMTP) |
| `ALERT_FROM_EMAIL` | worker | `no-reply@mining.maharashtra.gov.in` |
| `SMS_PROVIDER_KEY` | worker | Twilio / gateway API key for officer SMS |
| `MODEL_WEIGHTS_PATH` | worker | Path to promoted weights; **empty → degraded (heuristic) mode** |
| `MONITORED_DISTRICTS` | worker | `chandrapur,gadchiroli,wardha` |
| `TZ` | all | `UTC` (cron times are UTC; digest converts to IST) |

## 3. Failure Modes

| Failure | Detection | Mitigation |
|---|---|---|
| Task failure (any service) | Celery task error | **Retry × 3 with exponential backoff: 30 s → 60 s → 120 s**; final failure routes the task to the Redis dead-letter list `alerts_dlq` and emails the operator |
| Optical scene too cloudy | `eo:cloud_cover > 30.0` | **Cloud-cover skip policy:** scene skipped and recorded in STAC; change detection falls back to SAR-only (Δσ⁰ channel) until the next clear pass — all-weather coverage is preserved |
| Model weights missing / corrupt | `MODEL_WEIGHTS_PATH` empty or file hash mismatch | **Degraded mode:** ml_engine runs the deterministic heuristic fallback (ml-pipeline.md §4); risk engine, API and dashboard unchanged; `GET /health` reports `"models": {"change_detection": "heuristic"}` |
| MinIO outage | S3 PUT/GET errors | Worker writes to a local staging dir; Celery retry re-uploads on recovery (same backoff policy) |
| SMS delivery failure | provider non-2xx response | **Fallback chain:** SMS → email → dashboard-only + re-dispatch attempt in the next hourly window; delivery events logged to the feed |
| PostGIS unreachable | connection timeout | API returns 503 with per-service detail; workers pause and retry with backoff; no data loss (all state in PostGIS, idempotent tasks) |
| Sentinel API outage | poll returns 5xx | Skip cycle silently, STAC marks `missing`; next cron run requests the missed window (revisit cadence absorbs one missed pass) |

## 4. Rollout Note

The demo environment runs the full stack above on a single node (Docker Compose); the production design scales `celery-worker` horizontally by queue, and MinIO is backed by NVMe local volumes with nightly off-site sync. No state is kept outside PostGIS, MinIO and Redis, so any worker can die and be replaced without loss.