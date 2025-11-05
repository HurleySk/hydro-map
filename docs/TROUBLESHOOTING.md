# Troubleshooting Guide

**Version**: 1.9.0

Use this guide to diagnose the most common pitfalls when running Hydro-Map.

---

## 1. Quick Diagnostics

```bash
# Verify processed rasters
ls data/processed/dem/

# Verify Fairfax datasets
ls data/processed/fairfax_*.gpkg data/processed/perennial_streams.gpkg
ls data/processed/floodplain_*.gpkg data/processed/inadequate_outfall*.gpkg

# Verify PMTiles
ls data/tiles/*.pmtiles

# Backend health
curl http://localhost:8000/health
curl http://localhost:8000/api/delineate/status

# Frontend build dependencies
cd frontend && npm run check
```

If any command fails, address that step before debugging the UI.

---

## 2. Installation & Dependencies

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError` during script execution | Backend venv inactive | `source backend/venv/bin/activate` then rerun |
| `Failed building wheel for GDAL` | Missing GDAL headers | Install `gdal-bin`/`libgdal-dev` (Linux) or `brew install gdal` (macOS), then reinstall |
| `tippecanoe: command not found` | Tippecanoe not installed | Install using package manager or prebuilt release |
| `pmtiles: command not found` | PMTiles CLI missing | `cargo install pmtiles` or download binary |

---

## 3. Data Processing Errors

| Symptom | Explanation | Resolution |
| --- | --- | --- |
| `FileNotFoundError` for `flow_direction.tif` | DEM pipeline not run or wrong path | Run `prepare_dem.py` and confirm `.env` raster paths |
| Flow accumulation full of zeros | DEM still in geographic CRS | Ensure input DEM uses projected coordinates or let the script reproject |
| Fairfax datasets missing | Scripts not executed | Run `download_fairfax_hydro.py` / `prepare_fairfax_hydro.py` and stormwater equivalents |
| Stormwater layers empty in UI | No raw download | Run `download_fairfax_stormwater.py`; check ArcGIS service availability |

---

## 4. Tile Generation Issues

| Symptom | Explanation | Resolution |
| --- | --- | --- |
| Layer missing from Tile Status panel | PMTiles not generated | Re-run `generate_tiles.py` and confirm file exists |
| Raster colours look wrong | Aspect requires nearest-neighbour sampling | Let the script override to `nearest` or rerun with `--raster-resampling nearest` |
| `pmtiles` conversion errors | Missing `mb-util` or `pmtiles` CLI | Install dependencies (`pip install mbutil` inside backend venv, ensure `pmtiles` on PATH) |
| Large PMTiles for small AOI | High max zoom | Lower `--max-zoom` to 15–16 for 10 m DEMs |

---

## 5. Backend API Issues

| Symptom | Explanation | Resolution |
| --- | --- | --- |
| `/api/delineate` → `503` | Required rasters missing | Check `/api/delineate/status` and rerun `prepare_dem.py` |
| Delineation slow (>5 s) | Cold cache, large DEM | Keep `CACHE_ENABLED=true` and ensure SSD storage |
| Feature Info missing geology | `GEOLOGY_PATH` incorrect or dataset absent | Confirm path in `.env` and rerun geology prep |
| Stormwater results absent | `inadequate-outfalls` not requested | Include it in the `layers` array or verify dataset path in `LAYER_DATASET_MAP` |

Logs appear in the backend console; enable verbose logging or add print statements for deeper inspection.

---

## 6. Frontend Issues

| Symptom | Explanation | Resolution |
| --- | --- | --- |
| Blank page | Dev server not running or Vite port blocked | Run `npm run dev -- --host`, then reload |
| Tiles 404 in console | Wrong backend URL | Ensure backend runs on :8000 and that `VITE_API_URL` points there |
| UI stuck in tool mode | Local state persisted | Press `Esc` or clear localStorage (`localStorage.clear()`) |
| Geocoding fails | Offline or rate-limited Nominatim | Retry later or swap in your own geocoder |

---

## 7. Performance Considerations

- Use the Tile Status panel to verify you’re viewing areas with generated tiles.  
- For large DEMs, lower the frontend default zoom (`DEFAULT_MAP_VIEW`) to reduce initial data load.  
- Cache PMTiles via CDN/object storage if accessing remotely.

---

## 8. Deployment & Ops

| Symptom | Explanation | Resolution |
| --- | --- | --- |
| Tiles return `403` behind proxy | Missing `Accept-Ranges` header passthrough | Ensure your proxy does not strip range requests |
| Docker compose healthcheck loops | Backend needs datasets | Mount `data/` volume and rerun preprocessing before `docker-compose up` |
| HTTPS requests blocked by CORS | Origins not whitelisted | Set `CORS_ORIGINS=https://your-domain` in `.env` |

---

## 9. Still Stuck?

1. Enable FastAPI debug logs (`uvicorn app.main:app --reload --log-level debug`).  
2. Run scripts with `--help` to confirm argument names.  
3. Compare against the latest release in `CHANGELOG.md`.  
4. Open an issue on GitHub with environment details, log snippets, and reproduction steps.
