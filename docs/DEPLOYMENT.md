# Deployment Guide

**Version**: 1.9.0

Deploying Hydro-Map involves serving a FastAPI backend, a SvelteKit-built frontend, and the generated PMTiles. This guide covers recommended setups and production considerations.

---

## 1. Checklist Before Deploying

1. Run the full data pipeline and confirm `data/processed/` and `data/tiles/` are populated.  
2. Set environment variables in `.env` for the target environment (disable reload, tighten CORS).  
3. Decide whether to host tiles from the backend (`/tiles/*`) or a CDN/object storage bucket.  
4. Generate a production frontend build (`npm run build`).

---

## 2. Docker Compose (Recommended)

### 2.1 Local production-style run

```bash
docker-compose build
docker-compose up -d
```

Default services:

- `backend`: uvicorn with reload (adjust to gunicorn for production)
- `frontend`: Vite dev server (`npm run dev -- --host`)
- `redis`: Optional cache placeholder (unused by default)

For production, create `docker-compose.prod.yml` with:

- `backend` command: `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`
- `frontend` replaced with a static file server (e.g., nginx or Caddy) serving `frontend/build`
- Volume mounts pointing to `data/` (read-only) and `backend/data/cache` (read-write)

Run:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

Use the built-in healthcheck (`/api/delineate/status`) to ensure datasets are mounted correctly.

---

## 3. Traditional VM Deployment

1. **Backend**
   - Install Python 3.12+, GDAL, and project dependencies.
   - Create a systemd service or supervisor job running `gunicorn app.main:app --workers 4 --bind 0.0.0.0:8000`.
   - Expose `.env` via environment file (`EnvironmentFile=/path/to/.env`).

2. **Frontend**
   - Build once (`npm run build`) and serve `frontend/build/` using nginx, Apache, or any static file host.
   - Configure the frontend to reach the backend via `VITE_API_URL=https://api.example.com`.

3. **Tiles**
   - Option A: mount `data/tiles/` and let the backend keep serving `/tiles/*.pmtiles`.
   - Option B: upload PMTiles to object storage (S3, GCS, Azure Blob) and use signed or public URLs; update frontend `layers.ts` to point at the new base URL.

4. **Reverse Proxy**
   - Terminate TLS with nginx/Caddy.  
   - Proxy `/api` and `/tiles` to `http://127.0.0.1:8000`.  
   - Serve the static frontend from `/var/www/hydro-map` (or equivalent).

Example nginx snippet:

```nginx
server {
  listen 80;
  server_name hydro.example.com;

  location / {
    root /srv/hydro-map/frontend;
    try_files $uri /index.html;
  }

  location /api {
    proxy_pass http://127.0.0.1:8000/api;
    proxy_set_header Host $host;
  }

  location /tiles {
    proxy_pass http://127.0.0.1:8000/tiles;
    proxy_set_header Host $host;
  }
}
```

---

## 4. Configuration Tips

- `.env` production defaults:
  ```
  BACKEND_HOST=0.0.0.0
  BACKEND_PORT=8000
  BACKEND_RELOAD=false
  CACHE_ENABLED=true
  CORS_ORIGINS=https://hydro.example.com
  ```
- Store PMTiles on SSD storage for fast range requests.
- Ensure the `backend/data/cache` directory is writable by the service user.
- Monitor disk space for `data/tiles/` when supporting multiple AOIs.

---

## 5. Monitoring & Maintenance

- **Health checks**: `/health` for liveness, `/api/delineate/status` for dataset readiness.  
- **Logging**: run gunicorn with `--access-logfile -` and capture logs via syslog/journal.  
- **Metrics**: integrate a reverse proxy (nginx ingress, Traefik) that exports Prometheus metrics if required.  
- **Backups**: version `data/processed/` and `data/tiles/`—these are expensive to regenerate.

---

## 6. Scaling Considerations

- Horizontal scaling requires making PMTiles accessible to every instance (shared object storage or CDN).  
- For heavy API usage, consider moving cache storage to Redis and wiring it into `services/cache.py`.  
- Use CloudFront/Cloudflare to cache PMTiles globally if users are geographically distributed.

---

## 7. Post-Deployment Smoke Test

1. Hit `/health` and `/api/delineate/status` via the public URL.  
2. Load the frontend, toggle each layer group, and check Tile Status.  
3. Run a watershed delineation and Feature Info query to verify API + data connectivity.  
4. Monitor server logs for a few minutes to confirm no 404/500 responses.
