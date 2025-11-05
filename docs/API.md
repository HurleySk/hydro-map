# API Reference

**Version**: 1.9.0

Hydro-Map exposes a small FastAPI service used by the frontend and suitable for direct integrations. All endpoints are unauthenticated by default and return JSON.

| Item | Value |
| --- | --- |
| Base URL (dev) | `http://localhost:8000` |
| Docs | `http://localhost:8000/docs` (Swagger UI) |
| CORS | Controlled by `CORS_ORIGINS` in `.env` (defaults to localhost dev ports) |

---

## 1. Watershed Delineation

### `POST /api/delineate`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `lat` | float | ✅ | Latitude in WGS84 |
| `lon` | float | ✅ | Longitude in WGS84 |
| `snap_to_stream` | bool | ❌ | Overrides server default (`SNAP_TO_STREAM`) |
| `snap_radius` | integer | ❌ | Overrides server default (`DEFAULT_SNAP_RADIUS`, meters) |

Example request:

```bash
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true}'
```

Example response:

```json
{
  "watershed": {
    "type": "Feature",
    "geometry": { "type": "Polygon", "coordinates": [...] },
    "properties": {
      "area_km2": 13.4823,
      "area_mi2": 5.2065,
      "area_m2": 13482344.77,
      "perimeter_km": 21.304,
      "perimeter_m": 21304.11,
      "num_cells": 15384,
      "elevation_min_m": 4.7,
      "elevation_max_m": 414.2,
      "elevation_mean_m": 165.9,
      "elevation_std_m": 48.6
    }
  },
  "pour_point": {
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [-122.4162, 37.7778] },
    "properties": {
      "snapped": true,
      "original_lat": 37.7749,
      "original_lon": -122.4194,
      "snap_distance_m": 374.1,
      "flow_accumulation": 18573.0
    }
  },
  "statistics": { "...same fields as watershed.properties..." },
  "metadata": {
    "processing_time": 2.41,
    "snap_radius": 100,
    "from_cache": false
  }
}
```

Common error codes:

| Code | When |
| --- | --- |
| `400` | Pour point outside DEM extent |
| `422` | Validation error (e.g., latitude > 90) |
| `503` | Required rasters missing (run `prepare_dem.py`) |
| `500` | Unexpected processing failure |

### `GET /api/delineate/status`

Returns filesystem readiness for the delineation service.

```json
{
  "ready": true,
  "files": {
    "dem": { "path": "../data/processed/dem/filled_dem.tif", "exists": true },
    "flow_direction": { "path": "../data/processed/dem/flow_direction.tif", "exists": true },
    "flow_accumulation": { "path": "../data/processed/dem/flow_accumulation.tif", "exists": true }
  },
  "cache_enabled": true
}
```

Use this endpoint in health checks after deployments.

---

## 2. Cross-Section Profiles

### `POST /api/cross-section`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `line` | array of `[lon, lat]` pairs | ✅ | Minimum of 2 vertices |
| `sample_distance` | integer | ❌ | Sampling interval (meters). Defaults to `CROSS_SECTION_SAMPLE_DISTANCE` |

Example request:

```json
{
  "line": [
    [-122.4160, 37.7825],
    [-122.4101, 37.7894]
  ],
  "sample_distance": 20
}
```

Example response:

```json
{
  "profile": [
    { "distance": 0.0, "elevation": 19.2, "lat": 37.7825, "lon": -122.416 },
    { "distance": 20.0, "elevation": 21.8, "lat": 37.7827, "lon": -122.4158 }
    // ...
  ],
  "geology": [
    {
      "type": "geology",
      "formation": "Tcg",
      "rock_type": "Conglomerate",
      "age": "Pleistocene",
      "distance_along_m": 140.5
    }
  ],
  "metadata": {
    "sample_distance_m": 20,
    "total_distance_m": 718.4,
    "num_samples": 37,
    "num_geology_contacts": 2
  }
}
```

Errors mirror the delineation endpoint (`422` for invalid inputs, `503` if rasters missing).

---

## 3. Feature Information

### `POST /api/feature-info`

Returns contextual data for a clicked map location.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `lat` | float | ✅ | Latitude in WGS84 |
| `lon` | float | ✅ | Longitude in WGS84 |
| `buffer` | float | ❌ | Search radius in meters (default 10, max 1000) |
| `layers` | array of strings | ❌ | Layers to query. Defaults to `["geology"]`. Supported values: `geology`, `inadequate-outfalls` (polygon overlay). Geology and stormwater datasets can be disabled by omitting them. |

Regardless of the `layers` list, the API always attempts to return:

- `fairfax_watersheds` – name + metadata for the containing watershed (if any)
- `dem_samples` – elevation, slope, aspect at the click point

Example request:

```bash
curl -X POST http://localhost:8000/api/feature-info \
  -H "Content-Type: application/json" \
  -d '{"lat": 38.8456, "lon": -77.3137, "buffer": 25, "layers": ["geology", "inadequate-outfalls"]}'
```

Example response (abridged):

```json
{
  "location": { "lat": 38.8456, "lon": -77.3137 },
  "query": { "buffer_m": 25.0, "layers": ["geology", "inadequate-outfalls"] },
  "features": {
    "geology": [
      {
        "type": "geology",
        "formation": "Pa",
        "rock_type": "Alluvium",
        "age": "Quaternary",
        "description": "Alluvial deposits along valley floors",
        "distance_to_contact_m": 0.0,
        "precision": "exact",
        "is_nearest": false,
        "source": "geology.gpkg"
      }
    ],
    "inadequate_outfalls": [
      {
        "type": "inadequate_outfall",
        "outfall_id": "IO-417",
        "determination": "Erosion",
        "watershed": "Old Courthouse",
        "drainage_area_sqkm": 0.92,
        "distance_meters": 12.4,
        "is_nearest": false
      }
    ],
    "fairfax_watersheds": {
      "name": "Old Courthouse",
      "area_sqkm": 14.52,
      "web_address": "https://www.fairfaxcounty.gov/publicworks/watersheds"
    },
    "dem_samples": {
      "elevation_m": 84.7,
      "slope_deg": 3.1,
      "aspect_deg": 175.2,
      "aspect_cardinal": "S"
    }
  },
  "num_features": 4,
  "warnings": null,
  "metadata": {
    "datasets": ["geology", "fairfax_watersheds", "dem"]
  }
}
```

Warnings are optional; they describe missing data or nearest-feature fallbacks.

---

## 4. Tiles

### `GET /tiles/{filename}.pmtiles`

Streams PMTiles with HTTP range requests. Example:

```bash
curl -I http://localhost:8000/tiles/hillshade.pmtiles
```

Returns `200 OK` with `Accept-Ranges: bytes`. Suitable for direct use by MapLibre or for validating tile availability.

---

## 5. Health Check

- `GET /health` returns `{"status": "healthy"}` and is used by Docker/docker-compose to confirm the backend is alive.

---

## 6. Tips

- Swagger UI (`/docs`) and ReDoc (`/redoc`) are auto-generated if you prefer exploring interactively.
- The backend logs delineation start/end times and resolved data paths—helpful when integrating in headless environments.
- If you expose the API publicly, add authentication (API keys or OAuth) in FastAPI and tighten `CORS_ORIGINS`.
