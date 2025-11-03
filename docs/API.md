# API Reference

**Version**: 1.5.0

## Overview

Hydro-Map provides a RESTful API for watershed delineation, cross-section generation, feature queries, and tile serving. All endpoints are available at `/api/` except the tiles endpoint which is at `/tiles/`.

**Base URL**: `http://localhost:8000` (development)

**Content Type**: `application/json`

**CORS**: Enabled for all origins (development configuration)

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Watershed Delineation](#watershed-delineation)
  - [Cross-Section Generation](#cross-section-generation)
  - [Feature Information](#feature-information)
  - [Tile Serving](#tile-serving)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Authentication

**Current version**: No authentication required

All endpoints are publicly accessible in the current version. Future versions may implement API key authentication.

## Endpoints

### Watershed Delineation

Delineate watersheds from a pour point using DEM-based flow analysis.

#### `POST /api/delineate`

Generate a watershed boundary and pour point from coordinates.

**Request Body**:

```json
{
  "lat": 37.7749,
  "lon": -122.4194,
  "snap_to_stream": true,
  "snap_radius": 100
}
```

**Request Schema**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `lat` | float | Yes | -90 to 90 | Latitude in WGS84 decimal degrees |
| `lon` | float | Yes | -180 to 180 | Longitude in WGS84 decimal degrees |
| `snap_to_stream` | boolean | No (default: true) | - | Whether to snap pour point to nearest stream |
| `snap_radius` | integer | No (default: 100) | 0 to 1000 | Maximum snap distance in meters |

**Response** (200 OK):

```json
{
  "watershed": {
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[lon, lat], [lon, lat], ...]]
    },
    "properties": {
      "area_sqkm": 12.456,
      "perimeter_km": 15.789,
      "compactness": 0.75
    }
  },
  "pour_point": {
    "type": "Feature",
    "geometry": {
      "type": "Point",
      "coordinates": [lon, lat]
    },
    "properties": {
      "original_lat": 37.7749,
      "original_lon": -122.4194,
      "snapped": true,
      "snap_distance_m": 45.67,
      "elevation_m": 123.45
    }
  },
  "statistics": {
    "area_sqkm": 12.456,
    "perimeter_km": 15.789,
    "compactness": 0.75,
    "mean_elevation_m": 234.56,
    "min_elevation_m": 100.00,
    "max_elevation_m": 456.78,
    "mean_slope_degrees": 8.92
  },
  "metadata": {
    "cache_key": "37.774900,-122.419400|snap:true|radius:100",
    "cached": false,
    "processing_time_seconds": 2.345,
    "dem_resolution_m": 10
  }
}
```

**Response Fields**:

- `watershed`: GeoJSON Feature with Polygon geometry
  - `area_sqkm`: Total watershed area in square kilometers
  - `perimeter_km`: Watershed boundary length in kilometers
  - `compactness`: Compactness ratio (1.0 = perfect circle)
- `pour_point`: GeoJSON Feature with Point geometry
  - `original_lat/lon`: User-provided coordinates
  - `snapped`: Whether coordinates were adjusted to stream
  - `snap_distance_m`: Distance moved during snapping (if snapped)
  - `elevation_m`: DEM elevation at pour point
- `statistics`: Detailed watershed characteristics
  - `mean_elevation_m`: Average elevation across watershed
  - `min/max_elevation_m`: Elevation range
  - `mean_slope_degrees`: Average slope steepness
- `metadata`: Processing information
  - `cache_key`: Key used for result caching
  - `cached`: Whether result was retrieved from cache
  - `processing_time_seconds`: Time to process request
  - `dem_resolution_m`: DEM spatial resolution

**Errors**:

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid coordinates or parameters |
| 422 | Validation error (e.g., lat > 90) |
| 503 | Required data files not found (DEM missing) |
| 500 | Processing failed (e.g., point outside DEM coverage) |

**Example cURL**:

```bash
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 37.7749,
    "lon": -122.4194,
    "snap_to_stream": true,
    "snap_radius": 100
  }'
```

#### `GET /api/delineate/status`

Check the status of watershed delineation processing (future: for async jobs).

**Current implementation**: Returns server health status.

**Response** (200 OK):

```json
{
  "status": "operational",
  "cache_size": 42,
  "available_data": {
    "dem": true,
    "flow_accumulation": true,
    "flow_direction": true
  }
}
```

---

### Cross-Section Generation

Generate elevation profiles along a user-drawn line.

#### `POST /api/cross-section`

Sample elevation and geology along a line.

**Request Body**:

```json
{
  "line": [
    [-122.4194, 37.7749],
    [-122.4100, 37.7800],
    [-122.4000, 37.7850]
  ],
  "sample_distance": 25
}
```

**Request Schema**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `line` | array | Yes | Min 2 points | Array of [lon, lat] coordinate pairs |
| `sample_distance` | integer | No (default: 10) | 1 to 100 | Sample interval in meters |

**Response** (200 OK):

```json
{
  "profile": [
    {
      "distance": 0.0,
      "elevation": 123.45,
      "lat": 37.7749,
      "lon": -122.4194
    },
    {
      "distance": 25.0,
      "elevation": 145.67,
      "lat": 37.7752,
      "lon": -122.4180
    }
  ],
  "geology": [
    {
      "start_distance": 0.0,
      "end_distance": 450.5,
      "formation": "Franciscan Complex",
      "rock_type": "Sandstone",
      "age": "Jurassic-Cretaceous",
      "color": "#E6C896"
    },
    {
      "start_distance": 450.5,
      "end_distance": 1200.0,
      "formation": "Great Valley Sequence",
      "rock_type": "Shale",
      "age": "Cretaceous",
      "color": "#96826E"
    }
  ],
  "metadata": {
    "sample_distance_m": 25,
    "total_distance_m": 1200.0,
    "num_samples": 49,
    "num_geology_contacts": 2
  }
}
```

**Response Fields**:

- `profile`: Array of elevation samples
  - `distance`: Distance from line start in meters
  - `elevation`: DEM elevation in meters (null if outside coverage)
  - `lat/lon`: WGS84 coordinates of sample point
- `geology`: Array of geological formations crossed (empty if no geology data)
  - `start_distance`: Where formation begins along line (meters)
  - `end_distance`: Where formation ends along line (meters)
  - `formation`: Formation name
  - `rock_type`: Primary rock type
  - `age`: Geological age
  - `color`: Hex color for visualization
- `metadata`:
  - `sample_distance_m`: Actual sample interval used
  - `total_distance_m`: Total line length
  - `num_samples`: Number of elevation samples
  - `num_geology_contacts`: Number of geological units crossed

**Errors**:

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid line coordinates (< 2 points) |
| 422 | Validation error (e.g., sample_distance > 100) |
| 503 | Required data files not found (DEM missing) |
| 500 | Processing failed |

**Example cURL**:

```bash
curl -X POST http://localhost:8000/api/cross-section \
  -H "Content-Type: application/json" \
  -d '{
    "line": [[-122.4194, 37.7749], [-122.4100, 37.7800]],
    "sample_distance": 25
  }'
```

**Notes**:

- Maximum sample points limited by `CROSS_SECTION_MAX_POINTS` config (default: 1000)
- Long lines with small sample distances may be capped
- Geology data is optional; returns empty array if unavailable

---

### Feature Information

Query map features at a clicked location.

#### `POST /api/feature-info`

Get attributes of features near a point.

**Request Body**:

```json
{
  "lat": 37.7749,
  "lon": -122.4194,
  "layers": ["streams", "geology"],
  "buffer": 10
}
```

**Request Schema**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `lat` | float | Yes | -90 to 90 | Latitude in WGS84 decimal degrees |
| `lon` | float | Yes | -180 to 180 | Longitude in WGS84 decimal degrees |
| `layers` | array | No (default: ["streams", "geology"]) | - | Which layers to query |
| `buffer` | float | No (default: 10) | 0 to 1000 | Search buffer in meters |

**Response** (200 OK):

```json
{
  "location": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "features": {
    "streams": [
      {
        "type": "stream",
        "name": "Lobos Creek",
        "length_km": 2.345,
        "drainage_area_sqkm": 5.678,
        "stream_order": 3,
        "upstream_length_km": 12.45,
        "slope": 0.025,
        "max_elev_m": 123.4,
        "min_elev_m": 5.6,
        "stream_type": "Perennial",
        "order": 3
      }
    ],
    "geology": [
      {
        "type": "geology",
        "formation": "Franciscan Complex",
        "rock_type": "Sandstone",
        "age": "Jurassic-Cretaceous",
        "description": "Turbidite sequence with intercalated shale..."
      }
    ]
  },
  "num_features": 2
}
```

**Response Fields**:

- `location`: Echoed query coordinates
- `features`: Object with layer names as keys
  - `streams`: Array of stream features
    - `name`: Stream name (from NHD) or "Unnamed"
    - `drainage_area_sqkm`: Upstream drainage area
    - `stream_order`: Strahler stream order
    - `stream_type`: Perennial/Intermittent/Ephemeral (DEM-derived only)
    - `upstream_length_km`: Total upstream stream length
    - `slope`: Average channel slope (rise/run)
    - `max/min_elev_m`: Elevation range
  - `geology`: Array of geological formations (if point intersects polygons)
    - `formation`: Geological formation name
    - `rock_type`: Primary rock type
    - `age`: Geological age/period
    - `description`: Formation description
- `num_features`: Total feature count across all layers

**Errors**:

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid coordinates or parameters |
| 422 | Validation error |
| 500 | Query failed |

**Example cURL**:

```bash
curl -X POST http://localhost:8000/api/feature-info \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 37.7749,
    "lon": -122.4194,
    "buffer": 10
  }'
```

**Notes**:

- Returns empty object if no features found within buffer
- Buffer is measured in projected coordinates (Equal Earth EPSG:6933)
- Stream query searches for intersecting features within buffer
- Geology query searches for polygons containing the point

---

### Tile Serving

Serve PMTiles files with HTTP range request support for efficient client-side rendering.

#### `GET /tiles/{filename}`

Retrieve a PMTiles file or byte range.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | string (path) | Yes | PMTiles filename (e.g., "hillshade.pmtiles") |

**Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `Range` | No | HTTP byte range (e.g., "bytes=0-1023") |

**Response** (200 OK - full file):

Binary PMTiles file with headers:
- `Content-Type: application/octet-stream`
- `Content-Length: {file_size}`
- `Accept-Ranges: bytes`
- `Cache-Control: public, max-age=3600`
- `Access-Control-Allow-Origin: *`

**Response** (206 Partial Content - range request):

Binary byte range with headers:
- `Content-Type: application/octet-stream`
- `Content-Length: {range_size}`
- `Content-Range: bytes {start}-{end}/{total}`
- `Accept-Ranges: bytes`
- `Cache-Control: public, max-age=3600`
- `Access-Control-Allow-Origin: *`

**Range Request Formats**:

- `bytes=0-1023` - Bytes 0 through 1023
- `bytes=1024-` - From byte 1024 to end of file
- `bytes=-500` - Last 500 bytes of file

**Errors**:

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid filename (directory traversal attempt) |
| 404 | File not found |
| 416 | Range not satisfiable |

**Example cURL** (full file):

```bash
curl http://localhost:8000/tiles/hillshade.pmtiles \
  -o hillshade.pmtiles
```

**Example cURL** (range request):

```bash
curl http://localhost:8000/tiles/hillshade.pmtiles \
  -H "Range: bytes=0-16383" \
  -o header.bin
```

#### `HEAD /tiles/{filename}`

Check if a PMTiles file exists and get metadata.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | string (path) | Yes | PMTiles filename |

**Response** (200 OK):

No body, headers only:
- `Content-Type: application/octet-stream`
- `Content-Length: {file_size}`
- `Accept-Ranges: bytes`
- `Cache-Control: public, max-age=3600`

**Errors**:

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid filename |
| 404 | File not found |

**Example cURL**:

```bash
curl -I http://localhost:8000/tiles/hillshade.pmtiles
```

#### `GET /tiles/`

List all available PMTiles files.

**Response** (200 OK):

```json
{
  "tiles": [
    {
      "name": "aspect.pmtiles",
      "size": 1234567,
      "size_mb": 1.18
    },
    {
      "name": "contours.pmtiles",
      "size": 3456789,
      "size_mb": 3.30
    },
    {
      "name": "hillshade.pmtiles",
      "size": 25678901,
      "size_mb": 24.49
    }
  ],
  "total": 8
}
```

**Response Fields**:

- `tiles`: Array of available tiles
  - `name`: Filename
  - `size`: Size in bytes
  - `size_mb`: Size in megabytes (rounded to 2 decimals)
- `total`: Count of available tiles

**Example cURL**:

```bash
curl http://localhost:8000/tiles/
```

**Notes**:

- PMTiles protocol uses range requests for efficiency
- Frontend loads only necessary tile data, not entire file
- Files are cached for 1 hour (3600 seconds)
- CORS enabled for cross-origin frontend access

---

## Error Handling

All errors follow a consistent JSON structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request succeeded |
| 206 | Partial Content | Range request succeeded |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error (Pydantic) |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Required data files missing |

### Error Examples

**Validation Error** (422):

```json
{
  "detail": [
    {
      "loc": ["body", "lat"],
      "msg": "ensure this value is greater than or equal to -90",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

**Data Missing Error** (503):

```json
{
  "detail": "Required data files not found: DEM file not found: /path/to/dem.tif"
}
```

**Processing Error** (500):

```json
{
  "detail": "Watershed delineation failed: Point outside DEM coverage"
}
```

---

## Rate Limiting

**Current version**: No rate limiting

The API currently has no rate limits. Future versions may implement:
- Per-IP request throttling
- API key-based quotas
- Separate limits for expensive operations (delineation vs. feature info)

For production deployments, consider implementing rate limiting at the reverse proxy level (nginx, Caddy).

---

## Examples

### Complete Workflow Example

This example demonstrates a typical workflow: delineate watershed, query stream at pour point, generate cross-section.

#### 1. Delineate Watershed

```bash
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 37.7749,
    "lon": -122.4194,
    "snap_to_stream": true,
    "snap_radius": 100
  }' | jq .
```

**Response excerpt**:
```json
{
  "watershed": { ... },
  "pour_point": {
    "geometry": {
      "coordinates": [-122.419234, 37.774856]
    },
    "properties": {
      "snapped": true,
      "snap_distance_m": 45.2
    }
  },
  "statistics": {
    "area_sqkm": 2.456
  }
}
```

#### 2. Query Stream at Pour Point

```bash
curl -X POST http://localhost:8000/api/feature-info \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 37.774856,
    "lon": -122.419234,
    "layers": ["streams"],
    "buffer": 10
  }' | jq .
```

**Response excerpt**:
```json
{
  "features": {
    "streams": [{
      "name": "Lobos Creek",
      "drainage_area_sqkm": 2.456,
      "stream_order": 3,
      "stream_type": "Perennial"
    }]
  }
}
```

#### 3. Generate Cross-Section Through Watershed

```bash
curl -X POST http://localhost:8000/api/cross-section \
  -H "Content-Type: application/json" \
  -d '{
    "line": [
      [-122.420, 37.770],
      [-122.419, 37.775],
      [-122.418, 37.780]
    ],
    "sample_distance": 25
  }' | jq .
```

**Response excerpt**:
```json
{
  "profile": [
    {"distance": 0, "elevation": 45.6, "lat": 37.770, "lon": -122.420},
    {"distance": 25, "elevation": 56.7, "lat": 37.7705, "lon": -122.4195},
    ...
  ],
  "metadata": {
    "total_distance_m": 1234.5,
    "num_samples": 50
  }
}
```

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Delineate watershed
response = requests.post(
    f"{BASE_URL}/api/delineate",
    json={
        "lat": 37.7749,
        "lon": -122.4194,
        "snap_to_stream": True,
        "snap_radius": 100
    }
)

if response.status_code == 200:
    data = response.json()
    watershed = data["watershed"]
    print(f"Watershed area: {watershed['properties']['area_sqkm']:.2f} km²")
else:
    print(f"Error: {response.json()['detail']}")

# Query features
response = requests.post(
    f"{BASE_URL}/api/feature-info",
    json={
        "lat": 37.7749,
        "lon": -122.4194,
        "buffer": 10
    }
)

if response.status_code == 200:
    features = response.json()["features"]
    if "streams" in features:
        for stream in features["streams"]:
            print(f"Stream: {stream['name']}, Order: {stream['order']}")
```

### JavaScript (fetch) Example

```javascript
// Delineate watershed
const delineateWatershed = async (lat, lon) => {
  const response = await fetch('http://localhost:8000/api/delineate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat,
      lon,
      snap_to_stream: true,
      snap_radius: 100
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return await response.json();
};

// Generate cross-section
const generateCrossSection = async (coordinates) => {
  const response = await fetch('http://localhost:8000/api/cross-section', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      line: coordinates,
      sample_distance: 25
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return await response.json();
};

// Usage
try {
  const watershed = await delineateWatershed(37.7749, -122.4194);
  console.log('Watershed area:', watershed.statistics.area_sqkm, 'km²');

  const crossSection = await generateCrossSection([
    [-122.420, 37.770],
    [-122.418, 37.780]
  ]);
  console.log('Profile samples:', crossSection.profile.length);
} catch (error) {
  console.error('Error:', error.message);
}
```

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design and data flow
- [Data Preparation](DATA_PREPARATION.md) - Generating required data files
- [Deployment](DEPLOYMENT.md) - Production deployment guide
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

## API Versioning

**Current version**: 1.5.0 (no API versioning in URL)

Future versions may implement URL-based versioning (e.g., `/api/v2/delineate`) for breaking changes. The current API is considered stable for the 1.x release series.

## Changelog

- **v1.5.0** (2025-11-04): Cross-section responses include geology contact counts; Feature Info defaults adjusted to query geology automatically
- **v1.2.1** (2025-11-02): Documentation improvements
- **v1.2.0** (2025-11-01): No API changes (frontend refactor only)
- **v1.1.1** (2025-10-31): Dual stream support (NHD + DEM-derived)
- **v1.1.0** (2025-10-28): HUC12 boundaries support
- **v1.0.0** (2025-10-15): Initial stable API release
