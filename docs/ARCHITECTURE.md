# Architecture Overview

This document describes the technical architecture of the Hydro-Map application.

## System Overview

Hydro-Map is a full-stack web application with three main components:

1. **Frontend**: SvelteKit + MapLibre GL JS (client-side rendering)
2. **Backend**: FastAPI + Python (API server)
3. **Data Pipeline**: Preprocessing scripts (offline processing)

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   SvelteKit  │  │  MapLibre GL │  │   PMTiles    │      │
│  │   (UI/UX)    │  │  (Rendering) │  │  (Protocol)  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┴──────────────────┘               │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                    REST API (HTTP)
                            │
┌───────────────────────────┼──────────────────────────────────┐
│                         Backend                              │
│         ┌───────────────┴─────────────┐                     │
│         │        FastAPI Server       │                     │
│         └──┬───────────┬──────────┬───┘                     │
│            │           │          │                          │
│    ┌───────▼──┐  ┌────▼────┐  ┌──▼──────┐                  │
│    │Delineate │  │ Cross-  │  │ Feature │                  │
│    │ Route    │  │ Section │  │  Info   │                  │
│    └───┬──────┘  └────┬────┘  └──┬──────┘                  │
│        │              │           │                          │
│    ┌───▼──────────────▼───────────▼───┐                    │
│    │        Services Layer            │                    │
│    │  • Watershed Delineation         │                    │
│    │  • Flow Analysis                 │                    │
│    │  • Profile Generation            │                    │
│    │  • Caching                       │                    │
│    └──────────────┬───────────────────┘                    │
│                   │                                          │
└───────────────────┼──────────────────────────────────────────┘
                    │
            ┌───────▼────────┐
            │  Data Storage  │
            ├────────────────┤
            │ • Flow Grids   │
            │ • DEM          │
            │ • Streams      │
            │ • Geology      │
            │ • PMTiles      │
            └────────────────┘
```

## Frontend Architecture

### Technology Stack

- **Framework**: SvelteKit 2.0
- **Mapping**: MapLibre GL JS 4.7
- **Tiles**: PMTiles 3.2 (client-side protocol)
- **Spatial**: Turf.js (spatial operations)
- **Visualization**: D3.js (cross-section profiles)

### Component Hierarchy

```
+page.svelte (Main App)
├── Map.svelte (MapLibre wrapper)
│   ├── PMTiles sources (hillshade, slope, streams, etc.)
│   └── GeoJSON sources (watersheds, cross-sections)
├── LayerPanel.svelte (Layer controls)
├── WatershedTool.svelte (Delineation UI)
├── CrossSectionTool.svelte (Profile UI)
└── FeatureInfo.svelte (Popup/sidebar)
```

### State Management

Using Svelte stores (`$lib/stores.ts`):

```typescript
// Layer visibility and opacity
layers: LayersState

// Active tool (none | delineate | cross-section | info)
activeTool: Tool

// Delineated watersheds (cached)
watersheds: Watershed[]

// Current cross-section data
crossSection: CrossSection | null
```

### Client-Side Tile Rendering

**PMTiles Protocol**:
- Single-file tile archives served statically (no tile server needed)
- HTTP range requests for efficient tile loading
- Works with CDN/object storage

**MapLibre Style**:
```javascript
sources: {
  hillshade: {
    type: 'raster',
    url: 'pmtiles:///tiles/hillshade.pmtiles'
  },
  streams: {
    type: 'vector',
    url: 'pmtiles:///tiles/streams.pmtiles'
  }
}
```

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI 0.115
- **Geospatial**: WhiteboxTools, rasterio, geopandas
- **Server**: Uvicorn (ASGI)
- **Caching**: File-based or Redis

### API Routes

#### `/api/delineate` (POST)
Delineate watershed from pour point.

**Request**:
```json
{
  "lat": 37.7749,
  "lon": -122.4194,
  "snap_to_stream": true,
  "snap_radius": 100
}
```

**Response**:
```json
{
  "watershed": { /* GeoJSON polygon */ },
  "pour_point": { /* GeoJSON point */ },
  "statistics": {
    "area_km2": 25.4,
    "elevation_mean_m": 450.2,
    ...
  },
  "metadata": {
    "processing_time": 1.2,
    "from_cache": false
  }
}
```

#### `/api/cross-section` (POST)
Generate elevation and geology profile.

**Request**:
```json
{
  "line": [[-122.4, 37.77], [-122.3, 37.78]],
  "sample_distance": 10
}
```

**Response**:
```json
{
  "profile": [
    {"distance": 0, "elevation": 100, "lat": 37.77, "lon": -122.4},
    ...
  ],
  "geology": [
    {"start_distance": 0, "end_distance": 500, "formation": "..."},
    ...
  ],
  "metadata": { ... }
}
```

### Service Layer

#### `watershed.py`
Core delineation logic:

1. **Snap pour point** to high flow accumulation cell
   - Read flow accumulation raster
   - Search within radius for maximum value
   - Return snapped coordinates

2. **Trace watershed** using D8 flow direction
   - Read flow direction raster
   - Breadth-first search upstream
   - Build binary mask of contributing cells

3. **Polygonize watershed**
   - Convert mask to vector polygon
   - Simplify geometry
   - Calculate statistics

4. **Cache result** by snapped location
   - Hash coordinates to cache key
   - Store GeoJSON + stats as JSON

**Algorithm**: D8 Flow Direction Tracing
```python
# D8 directions: 1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE
# For each cell, check all 8 neighbors
# If neighbor flows TO current cell, add to watershed
# Reverse lookup: 1 flows from 16 (W flows from E)
```

#### `cache.py`
Result caching:

```python
# File-based cache (default)
cache_dir/
  watersheds/
    <hash>.json

# Redis cache (optional)
Key: watershed:<lat>,<lon>
Value: JSON(result)
TTL: 24 hours
```

## Data Pipeline

### Preprocessing Workflow

```
Raw DEM (elevation.tif)
    │
    ├─> Fill sinks/breach depressions
    │       └─> filled_dem.tif
    │
    ├─> Compute D8 flow direction
    │       └─> flow_direction.tif
    │
    ├─> Compute flow accumulation
    │       └─> flow_accumulation.tif
    │
    ├─> Generate hillshade
    │       └─> hillshade.tif
    │
    ├─> Compute slope
    │       └─> slope.tif
    │
    └─> Compute aspect
            └─> aspect.tif

Flow accumulation + Flow direction
    │
    └─> Extract streams (threshold)
            └─> streams.gpkg

Terrain rasters + Stream vectors
    │
    └─> Generate PMTiles
            ├─> hillshade.pmtiles
            ├─> slope.pmtiles
            ├─> aspect.pmtiles
            └─> streams.pmtiles
```

### WhiteboxTools Integration

**Depression Removal**:
- `BreachDepressionsLeastCost`: Carves channels through barriers
- `FillDepressionsWangAndLiu`: Fills sinks to create continuous surface

**Flow Analysis**:
- `D8Pointer`: Computes single flow direction per cell
- `D8FlowAccumulation`: Counts upstream cells
- `ExtractStreams`: Creates raster stream network
- `RasterStreamsToVector`: Converts to vector lines

### Tile Generation

**Raster Tiles** (GDAL):
```bash
# Convert to 8-bit, LZW compression
gdal_translate -scale -ot Byte -co COMPRESS=LZW input.tif output.tif

# Generate XYZ tiles
gdal2tiles.py --zoom 8-14 output.tif tiles/
```

**Vector Tiles** (Tippecanoe):
```bash
tippecanoe -o streams.mbtiles -l streams -z 14 -Z 8 streams.geojson
```

**PMTiles Conversion**:
```bash
pmtiles convert streams.mbtiles streams.pmtiles
```

## Data Flow

### Watershed Delineation Flow

```
User clicks map
    │
    ├─> Frontend sends {lat, lon} to /api/delineate
    │
    └─> Backend:
        ├─> Check cache (by lat,lon)
        │   └─> If hit: return cached result
        │
        ├─> Snap pour point to stream
        │   ├─> Read flow_accumulation.tif window
        │   └─> Find max within radius
        │
        ├─> Delineate watershed
        │   ├─> Read flow_direction.tif
        │   ├─> Trace upstream (BFS)
        │   └─> Polygonize mask
        │
        ├─> Calculate statistics
        │   ├─> Area (reproject to equal-area)
        │   ├─> Elevation stats (sample DEM)
        │   └─> Stream metrics (intersect streams)
        │
        ├─> Cache result
        │
        └─> Return GeoJSON + stats
            │
            └─> Frontend:
                ├─> Add to watersheds store
                ├─> Update map source
                └─> Fit bounds to watershed
```

### Cross-Section Flow

```
User draws line
    │
    ├─> Frontend sends {line: [[lon,lat],...]} to /api/cross-section
    │
    └─> Backend:
        ├─> Sample elevation along line
        │   ├─> Project to equal-area CRS
        │   ├─> Interpolate points at sample_distance
        │   ├─> Read DEM at each point
        │   └─> Build profile [{distance, elevation, lat, lon}]
        │
        ├─> Find geology contacts
        │   ├─> Read geology.gpkg
        │   ├─> Intersect line with polygons
        │   ├─> Calculate start/end distances
        │   └─> Extract formation attributes
        │
        └─> Return profile + geology
            │
            └─> Frontend:
                ├─> Store in crossSection
                └─> Render D3 chart with:
                    ├─> Elevation line
                    ├─> Geology color bands
                    └─> Formation labels
```

## Performance Optimizations

### Frontend
- **Client-side tiles**: No server roundtrips for raster/vector data
- **Lazy loading**: Tiles loaded on demand by zoom level
- **Debouncing**: Limit API calls on rapid interactions
- **Svelte reactivity**: Minimal re-renders

### Backend
- **Caching**: Avoid re-computing identical watersheds
- **Windowed reading**: Only read needed raster regions
- **Async I/O**: Non-blocking file operations
- **Connection pooling**: Reuse database connections

### Data
- **Pyramids**: Multi-resolution tiles (zoom 8-14)
- **Compression**: LZW for rasters, gzip for vectors
- **Simplification**: Reduce geometry vertices for web
- **Indexing**: Spatial indexes on vector layers

## Scalability Considerations

### Current Architecture (Local/Small)
- **Users**: 1-10 concurrent
- **Area**: Single watershed/county (100 sq mi)
- **Storage**: ~1-5 GB processed data
- **Compute**: Single server

### Scale-Up Options

**More Users**:
- Deploy backend behind load balancer
- Use Redis for distributed caching
- Serve PMTiles from CDN (S3 + CloudFront)

**Larger Areas**:
- Tile DEM into manageable chunks
- Pre-compute watersheds for known outlets
- Use PostGIS for vector data queries
- Stream large rasters with COG (Cloud Optimized GeoTIFF)

**More Features**:
- Add background job queue (Celery) for long computations
- Real-time updates via WebSockets
- User accounts with saved analyses

## Security

### Current Implementation
- **CORS**: Configured allowed origins
- **Input validation**: Pydantic models
- **File access**: Restricted to data directory
- **No authentication**: Open access (suitable for demo/research)

### Production Additions
- API authentication (JWT tokens)
- Rate limiting (per IP/user)
- Input sanitization for file paths
- HTTPS with SSL certificates

## Monitoring

### Suggested Metrics
- API response times (p50, p95, p99)
- Cache hit rates
- Tile request counts
- Error rates by endpoint
- DEM read latencies

### Tools
- **FastAPI**: Built-in OpenAPI docs at `/docs`
- **Logging**: Python logging to file/stdout
- **APM**: Sentry, Datadog, or New Relic

## Testing

### Unit Tests
- **Backend**: pytest for services (`tests/test_watershed.py`)
- **Frontend**: Vitest for components

### Integration Tests
- **API**: httpx with FastAPI TestClient
- **E2E**: Playwright for browser testing

### Data Validation
- Check DEM for nodata cells
- Verify stream network topology
- Validate geometry integrity

## Deployment

### Development
```bash
# Backend
uvicorn app.main:app --reload

# Frontend
npm run dev
```

### Production

**Option 1: Docker Compose**
```bash
docker-compose up -d
```

**Option 2: Kubernetes**
- Backend: FastAPI pods behind service
- Frontend: Static build served by nginx
- PMTiles: Object storage (S3/GCS)

**Option 3: Serverless**
- Backend: AWS Lambda + API Gateway
- Frontend: Vercel/Netlify
- PMTiles: S3 + CloudFront

## Future Architecture Enhancements

1. **Real-time Collaboration**: WebSocket for shared sessions
2. **Vector Tile Server**: pg_tileserv or martin for PostGIS
3. **3D Visualization**: Cesium or deck.gl for terrain
4. **Time Series**: Historical DEM comparison
5. **Mobile**: React Native or PWA
6. **ML Integration**: Landcover classification, flood prediction

## References

- [MapLibre GL JS Docs](https://maplibre.org/maplibre-gl-js-docs/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [WhiteboxTools Manual](https://www.whiteboxgeo.com/manual/wbt_book/)
- [PMTiles Spec](https://github.com/protomaps/PMTiles)
- [Svelte Tutorial](https://svelte.dev/tutorial)
