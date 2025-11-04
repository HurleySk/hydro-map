# Architecture Overview

**Version**: 1.7.0

This document describes the technical architecture of the Hydro-Map application, including system components, data flow, and implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [Data Pipeline](#data-pipeline)
- [Data Flow](#data-flow)
- [Layer Configuration System](#layer-configuration-system)
- [Performance Optimizations](#performance-optimizations)
- [Scalability Considerations](#scalability-considerations)
- [Security](#security)
- [Monitoring](#monitoring)
- [Testing](#testing)
- [Deployment](#deployment)
- [Future Enhancements](#future-architecture-enhancements)

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
│    │ Routes   │  │ Section │  │  Info   │                  │
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
            │ • HUC12        │
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
- **Geocoding**: Nominatim API (location search)

### Component Hierarchy

```
frontend/src/routes/+page.svelte (Main App Container)
│
├── Map.svelte
│   ├── Registers PMTiles Protocol & initializes MapLibre
│   ├── Reads LAYER_SOURCES to create map sources and layers
│   ├── Manages GeoJSON overlays (watersheds, cross-sections, outlets)
│   ├── Handles delineation/cross-section requests and map interactions
│   ├── Computes tile availability state for the TileStatus store
│   └── Implements PMTiles Protocol initialization sequence (critical)
│
├── LayerPanel.svelte
│   ├── Reads layer config from LAYER_SOURCES
│   ├── Organizes layers into collapsible groups (terrain, hydrology, reference)
│   ├── Visibility toggles and opacity sliders
│   └── Persists layer group expansion states to localStorage
│
├── WatershedTool.svelte
│   ├── Delineation mode toggle
│   ├── Snap-to-stream controls
│   ├── Latest results summary (area, elevation stats)
│   └── Watershed list management
│
├── CrossSectionTool.svelte
│   ├── Line digitizing workflow
│   ├── Preview elevation chart
│   └── Clear/generate controls
│
├── CrossSectionChart.svelte
│   ├── D3.js elevation profile visualization
│   └── Interactive hover/tooltips
│
├── FeatureInfoTool.svelte
│   └── Feature inspection mode toggle
│
├── FeatureInfo.svelte
│   └── Attribute popup/sidebar for clicked features
│
├── TileStatusPanel.svelte
│   ├── Tile reachability & coverage report
│   ├── Max zoom detection
│   └── Real-time coverage checks on map pan/zoom
│
├── BaseMapToggle.svelte
│   └── Basemap style selector (color/light/none)
│
└── LocationSearch.svelte
    ├── Nominatim geocoding search
    ├── Search history (localStorage-backed)
    └── Quick navigation to search results
```

### State Management

Global UI state lives in `frontend/src/lib/stores.ts` and is composed of Svelte writable stores:

```typescript
// Layer visibility and opacity (initialized from LAYER_SOURCES)
layers: LayersState = {
  hillshade: { visible: boolean, opacity: number },
  slope: { visible: boolean, opacity: number },
  aspect: { visible: boolean, opacity: number },
  'fairfax-water-lines': { visible: boolean, opacity: number },
  'fairfax-water-polys': { visible: boolean, opacity: number },
  'perennial-streams': { visible: boolean, opacity: number },
  contours: { visible: boolean, opacity: number },
  huc12: { visible: boolean, opacity: number },
  'huc12-fill': { visible: boolean, opacity: number },    // Sub-layer
  'huc12-outline': { visible: boolean, opacity: number }, // Sub-layer
  'huc12-labels': { visible: boolean, opacity: number }   // Sub-layer
}

// Active tool (none | delineate | cross-section | info)
activeTool: Tool

// Delineated watersheds (cached in UI)
watersheds: Watershed[]

// Current cross-section data
crossSection: CrossSection | null

// Digitized cross-section vertices
crossSectionLine: [number, number][]

// Persisted delineation settings (snap to stream, radius)
delineationSettings: {
  snapToStream: boolean,
  snapRadius: number
}

// Watershed outlet features (snapped pour points)
watershedOutlets: Feature[]

// Latest delineation response (front-end summary)
latestDelineation: DelineationResponse | null

// Map view persistence (center, zoom, bearing, pitch) - localStorage
mapView: MapViewState

// Tile availability summary for the Tile Status panel
tileStatus: TileStatusItem[]

// Location search history (localStorage-backed)
searchHistory: SearchHistoryItem[]

// UI panel expansion states (localStorage-backed)
panelStates: {
  mapLayers: boolean,      // Map Layers panel
  analysisTools: boolean,  // Analysis Tools panel
  systemStatus: boolean    // System Status panel
}

// Layer group expansion states (localStorage-backed)
layerGroupStates: {
  terrain: boolean,    // Terrain group (hillshade, slope, aspect, contours)
  hydrology: boolean   // Hydrology group (TWI, Fairfax water layers, perennial streams)
}
```

### Client-Side Tile Rendering

**PMTiles Protocol**:
- Single-file tile archives served statically (no tile server needed)
- HTTP range requests for efficient tile loading
- Works with CDN/object storage
- Tile metadata (bounds/header) is cached client-side to drive availability checks
- **CRITICAL**: Protocol must be registered BEFORE map creation to avoid race conditions

**MapLibre Style Sources** (Generated from LAYER_SOURCES):
```javascript
sources: {
  hillshade: {
    type: 'raster',
    url: 'pmtiles:///tiles/hillshade.pmtiles',
    tileSize: 256
  },
  slope: {
    type: 'raster',
    url: 'pmtiles:///tiles/slope.pmtiles',
    tileSize: 256
  },
  aspect: {
    type: 'raster',
    url: 'pmtiles:///tiles/aspect.pmtiles',
    tileSize: 256
  },
  'fairfax-water-lines': {
    type: 'vector',
    url: 'pmtiles:///tiles/fairfax_water_lines.pmtiles'
  },
  'fairfax-water-polys': {
    type: 'vector',
    url: 'pmtiles:///tiles/fairfax_water_polys.pmtiles'
  },
  'perennial-streams': {
    type: 'vector',
    url: 'pmtiles:///tiles/perennial_streams.pmtiles'
  },
  contours: {
    type: 'vector',
    url: 'pmtiles:///tiles/contours.pmtiles'
  },
  huc12: {
    type: 'vector',
    url: 'pmtiles:///tiles/huc12.pmtiles'
  }
}
```

**Layer Rendering Order** (bottom to top):
1. Raster terrain layers (hillshade, slope, aspect)
2. Vector contours
3. Fairfax water polygons → Fairfax water lines → Perennial streams
4. HUC12 watersheds (fill, outline, labels)

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI 0.115.0
- **Server**: Uvicorn 0.32.0 (ASGI)
- **Geospatial Libraries**:
  - **WhiteboxTools**: DEM preprocessing, flow analysis
  - **rasterio**: Raster I/O and windowed reading
  - **geopandas**: Vector data operations
  - **shapely**: Geometry manipulation
  - **pyproj**: Coordinate transformations
- **Caching**: File-based (default) or Redis

### Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application initialization
│   ├── config.py               # Pydantic settings (environment variables)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── delineate.py        # Watershed delineation endpoints
│   │   ├── cross_section.py    # Elevation profile endpoints
│   │   ├── features.py         # Feature info query endpoints
│   │   └── tiles.py            # PMTiles static file serving
│   └── services/
│       ├── watershed.py        # Hydrology utilities (snap, trace, stats)
│       └── cache.py            # Cache abstraction (file/Redis)
├── data/
│   ├── cache/
│   │   └── watersheds/         # Cached delineation results (JSON)
│   ├── processed/
│   │   ├── dem/                # Flow grids, terrain products
│   │   └── *.gpkg              # Vector datasets
│   └── tiles/                  # PMTiles archives
└── requirements.txt
```

### API Routes & Responsibilities

#### `POST /api/delineate`
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
  "watershed": {
    "type": "Feature",
    "geometry": { /* GeoJSON polygon */ },
    "properties": { /* statistics */ }
  },
  "pour_point": {
    "type": "Feature",
    "geometry": { /* GeoJSON point */ },
    "properties": {
      "snapped": true,
      "snap_distance_m": 45.2
    }
  },
  "statistics": {
    "area_km2": 25.4,
    "area_mi2": 9.8,
    "perimeter_km": 32.1,
    "elevation_mean_m": 450.2,
    "elevation_std_m": 120.5,
    "elevation_min_m": 200.0,
    "elevation_max_m": 850.0
  },
  "metadata": {
    "processing_time_s": 1.2,
    "from_cache": false,
    "cache_key": "37.774900,-122.419400|snap:true|radius:100"
  }
}
```

**Process**:
1. Validate input coordinates and parameters
2. Snap pour point to high flow accumulation cell (if enabled)
3. Check cache using snapped coordinates + parameters
4. If cache miss: delineate watershed using D8 flow tracing
5. Calculate area, perimeter, elevation statistics
6. Cache result (if caching enabled)
7. Return GeoJSON + statistics

#### `GET /api/delineate/status`
Check data file availability for watershed delineation.

**Response**:
```json
{
  "available": true,
  "missing_files": [],
  "flow_direction": "/path/to/flow_direction.tif",
  "flow_accumulation": "/path/to/flow_accumulation.tif",
  "dem": "/path/to/filled_dem.tif"
}
```

#### `POST /api/cross-section`
Generate elevation profile along a line.

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
    {
      "distance_m": 0,
      "elevation_m": 100.5,
      "lat": 37.77,
      "lon": -122.4
    },
    ...
  ],
  "metadata": {
    "total_distance_m": 1250.0,
    "num_points": 125,
    "sample_distance_m": 10
  }
}
```

#### `POST /api/feature-info`
Query geology, watershed, and DEM attributes around a clicked location.

**Request**:
```json
{
  "lat": 38.8732,
  "lon": -77.2716,
  "layers": ["geology", "huc12"],
  "buffer_m": 25
}
```

**Response**:
```json
{
  "geology": [
    {
      "formation": "Occoquan Granite",
      "rock_type": "Granite",
      "age": "Late Ordovician"
    }
  ],
  "huc12": {
    "huc12": "020700080204",
    "name": "Difficult Run-Accotink Creek",
    "area_sqkm": 73.1
  },
  "dem_samples": {
    "elevation_m": 92.6,
    "slope_degrees": 4.8,
    "aspect_degrees": 182.0
  }
}
```

#### `GET/HEAD /tiles/{filename}`
Serve PMTiles archives with HTTP range support.

- Supports HTTP range requests for efficient tile loading
- Static file serving via FastAPI StaticFiles
- Returns `Accept-Ranges: bytes` header
- Used by MapLibre GL JS PMTiles Protocol

### Service Layer

#### `services/watershed.py`
Core delineation logic:

**`snap_pour_point(lat, lon, radius)`**:
1. Read flow accumulation raster in windowed mode
2. Search within radius for maximum accumulation value
3. Return snapped coordinates and snap distance

**`delineate_watershed(lat, lon)`**:
1. Read flow direction raster
2. Breadth-first search (BFS) upstream to build contributing cell mask
3. Polygonize mask using `rasterio.features.shapes`
4. Merge polygons with `shapely.unary_union`
5. Calculate area (reproject to equal-area CRS) and perimeter
6. Sample DEM for elevation statistics (min/max/mean/std)
7. Return GeoJSON polygon with statistics

**Cache Key Design**:
```
"{lat:.6f},{lon:.6f}|snap:{flag}|radius:{radius}"
```
- 6 decimal precision (~11cm accuracy)
- Includes all parameters affecting delineation
- Ensures cache hits only for identical requests

#### `services/cache.py`
Cache abstraction for delineation results:

**File-based Cache (Default)**:
- Hashes cache key to `<hash>.json`
- Stores in `data/cache/watersheds/`
- Simple filesystem storage

**Redis Cache (Optional)**:
- Configurable via environment variables
- Supports distributed caching
- Faster than file-based for high traffic

#### `routes/cross_section.py`
Elevation sampling and profile generation:

1. Project line to equal-area CRS
2. Interpolate points at sample_distance
3. Read DEM at each point (windowed reading)
4. Build profile `[{distance, elevation, lat, lon}]`
5. Return profile data

#### `routes/features.py`
Spatial queries for feature info:

1. Load datasets configured in `LAYER_DATASET_MAP` (geology, huc12, Fairfax hydro, etc.)
2. Buffer point by specified radius
3. Intersect with vector geometries
4. Extract and return feature attributes (geology, watershed, DEM samples, custom layers)

## Data Pipeline

### Preprocessing Workflow

```
Raw DEM (elevation.tif)
    │
    ├─> Fill sinks/breach depressions (WhiteboxTools)
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
    ├─> Compute slope (degrees)
    │       └─> slope.tif
    │
    ├─> Compute aspect (compass direction)
    │       └─> aspect.tif
    │
    └─> Generate contours (gdal_contour)
            └─> contours.gpkg

Fairfax GIS Services
    │
    ├─> download_fairfax_hydro.py
    │       ├─> water_features_lines.gpkg
    │       ├─> water_features_polys.gpkg
    │       └─> perennial_streams.gpkg
    │
    └─> prepare_fairfax_hydro.py
            ├─> fairfax_water_lines.gpkg
            ├─> fairfax_water_polys.gpkg
            └─> perennial_streams.gpkg

(Optional) Legacy stream workflows
    │
    ├─> DEM-derived extraction (prepare_streams.py → streams_dem.gpkg)
    └─> NHD processing (process_nhd.py → streams_nhd.gpkg)

HUC12 Data (Watershed Boundary Dataset)
    │
    └─> Process HUC12 boundaries
            └─> huc12.gpkg

Terrain rasters + Fairfax hydro + HUC12 + (optional legacy streams)
    │
    └─> Generate PMTiles
            ├─> hillshade.pmtiles       (raster, z8-17)
            ├─> slope.pmtiles           (raster, z8-17)
            ├─> aspect.pmtiles          (raster, z8-17)
            ├─> contours.pmtiles              (vector, z8-17)
            ├─> fairfax_water_lines.pmtiles  (vector, z8-17)
            ├─> fairfax_water_polys.pmtiles  (vector, z8-17)
            ├─> perennial_streams.pmtiles    (vector, z8-17)
            └─> huc12.pmtiles                (vector, z8-14)
```

### WhiteboxTools Integration

**Depression Removal**:
- `BreachDepressionsLeastCost`: Carves channels through barriers
- `FillDepressionsWangAndLiu`: Fills remaining sinks

**Flow Analysis**:
- `D8Pointer`: Computes single flow direction per cell (8 directions)
- `D8FlowAccumulation`: Counts upstream contributing cells
- *(Legacy)* `ExtractStreams` / `RasterStreamsToVector`: Used only for DEM-derived stream workflow

**Terrain Analysis**:
- `Hillshade`: Shaded relief visualization
- `Slope`: Slope angle in degrees
- `Aspect`: Compass direction of slope (0-360°)

### Tile Generation

**Raster Tiles** (GDAL):
```bash
# CRITICAL: Must use --xyz flag for MapLibre compatibility
gdal2tiles.py --xyz --zoom 8-17 --resampling lanczos hillshade.tif tiles_xyz/

# Convert XYZ tiles to MBTiles
mb-util tiles_xyz/ hillshade.mbtiles

# Fix metadata (CRITICAL for raster rendering)
sqlite3 hillshade.mbtiles <<EOF
INSERT OR REPLACE INTO metadata (name, value) VALUES ('format', 'png');
INSERT OR REPLACE INTO metadata (name, value) VALUES ('type', 'overlay');
EOF

# Convert to PMTiles
pmtiles convert hillshade.mbtiles hillshade.pmtiles
```

**Resampling Strategy**:
- `lanczos`: For continuous rasters (hillshade, slope) - sharp, smooth
- `nearest`: For categorical rasters (aspect) - prevents color bleeding

**Vector Tiles** (Tippecanoe):
```bash
# Convert GeoPackage to GeoJSON
ogr2ogr -f GeoJSON fairfax_water_lines.geojson data/processed/fairfax_water_lines.gpkg fairfax_water_lines

# Generate MBTiles
tippecanoe -o fairfax_water_lines.mbtiles -l fairfax_water_lines -z 17 -Z 8 \
  --no-feature-reduction \
  --no-tile-size-limit \
  fairfax_water_lines.geojson

# Convert to PMTiles
pmtiles convert fairfax_water_lines.mbtiles fairfax_water_lines.pmtiles
```

**PMTiles Verification**:
```bash
# Verify tile type and metadata
pmtiles show hillshade.pmtiles
# Should show: tile type: png, format png, max zoom: 17

pmtiles show fairfax_water_lines.pmtiles
# Should show: tile type: mvt, layer name: fairfax_water_lines
```

## Data Flow

### Watershed Delineation Flow

```
User clicks map
    │
    ├─> Frontend sends POST /api/delineate {lat, lon, snap_to_stream, snap_radius}
    │
    └─> Backend:
        │
        ├─> Validate input (Pydantic models)
        │
        ├─> Snap pour point to stream (if snap_to_stream=true)
        │   ├─> Read flow_accumulation.tif (windowed, radius buffer)
        │   ├─> Find cell with maximum accumulation within radius
        │   └─> Return snapped coordinates + snap distance
        │
        ├─> Build cache key (snapped_lat, snapped_lon, snap_flag, radius)
        │
        ├─> Check cache
        │   └─> If hit: return cached result immediately
        │
        ├─> If miss: Delineate watershed
        │   ├─> Read flow_direction.tif
        │   ├─> BFS upstream from pour point to build mask
        │   ├─> Polygonize mask → GeoJSON
        │   ├─> Reproject to equal-area CRS (for area calculation)
        │   ├─> Calculate area_km2, area_mi2, perimeter_km
        │   ├─> Sample filled_dem.tif for elevation stats
        │   └─> Build response object
        │
        ├─> Cache result (if CACHE_ENABLED=true)
        │
        └─> Return GeoJSON + statistics
            │
            └─> Frontend:
                ├─> Parse response
                ├─> Add watershed to watersheds store
                ├─> Add pour point to watershedOutlets store
                ├─> Update latestDelineation store
                ├─> Update map GeoJSON sources
                ├─> Fit map bounds to watershed extent
                └─> Display statistics in WatershedTool panel
```

### Cross-Section Flow

```
User draws line on map
    │
    ├─> Frontend sends POST /api/cross-section {line: [[lon,lat],...], sample_distance}
    │
    └─> Backend:
        │
        ├─> Validate input
        │
        ├─> Project line to equal-area CRS (for accurate distance)
        │
        ├─> Interpolate points along line at sample_distance
        │   └─> Calculate total number of sample points
        │
        ├─> Sample elevation at each point
        │   ├─> Read filled_dem.tif (windowed reading)
        │   └─> Extract elevation value at each coordinate
        │
        ├─> Build profile array
        │   └─> [{distance_m, elevation_m, lat, lon}, ...]
        │
        └─> Return profile + metadata
            │
            └─> Frontend:
                ├─> Store in crossSection store
                ├─> Update crossSectionLine store (for map visualization)
                ├─> Render D3 elevation chart in CrossSectionChart.svelte
                ├─> Add line overlay to map
                └─> Display interactive profile with hover tooltips
```

### Tile Loading Flow

```
Map pan/zoom
    │
    ├─> MapLibre GL JS determines required tiles for viewport
    │
    ├─> For each tile needed:
    │   │
    │   ├─> Check tile cache (browser)
    │   │
    │   └─> If not cached:
    │       ├─> Parse pmtiles:// URL
    │       ├─> PMTiles Protocol resolves to /tiles/{filename}
    │       ├─> Read PMTiles header (cached per file)
    │       ├─> Calculate byte range for tile (z/x/y)
    │       ├─> HTTP GET /tiles/{filename} with Range header
    │       │   └─> Backend returns tile data (206 Partial Content)
    │       └─> Decode and render tile (PNG for raster, MVT for vector)
    │
    └─> Composite all tiles into final map view
```

## Layer Configuration System

### LAYER_SOURCES Architecture (v1.2.0)

**Central Source of Truth**: `frontend/src/lib/config/layers.ts`

```typescript
export const LAYER_SOURCES: LayerSource[] = [
  {
    id: 'hillshade',
    label: 'Hillshade',
    filename: 'hillshade.pmtiles',
    type: 'raster',
    defaultVisible: false,
    defaultOpacity: 0.6,
    category: 'terrain',
    description: 'Shaded relief visualization of terrain'
  },
  {
    id: 'fairfax-water-lines',
    label: 'Fairfax Water Features (Lines)',
    filename: 'fairfax_water_lines.pmtiles',
    type: 'vector',
    vectorLayerId: 'fairfax_water_lines',
    defaultVisible: false,
    defaultOpacity: 0.8,
    category: 'hydrology',
    paintProperties: { /* MapLibre paint config */ }
  },
  {
    id: 'perennial-streams',
    label: 'Fairfax Perennial Streams',
    filename: 'perennial_streams.pmtiles',
    type: 'vector',
    vectorLayerId: 'perennial_streams',
    defaultVisible: false,
    defaultOpacity: 0.8,
    category: 'hydrology',
    paintProperties: { /* MapLibre paint config */ }
  },
  // ... more layers
];
```

**Benefits**:
1. **Single location** for layer metadata
2. **Automatic registration**: Map.svelte reads LAYER_SOURCES to create sources/layers
3. **Type safety**: TypeScript interfaces ensure consistency
4. **Easy updates**: Add new layers by editing one file
5. **UI synchronization**: LayerPanel automatically stays in sync

**Adding New Layers**:
1. Add PMTiles file to `backend/data/tiles/`
2. Add layer configuration to LAYER_SOURCES in `layers.ts`
3. Map and UI automatically update - no manual Map.svelte edits needed

### Fairfax Hydrography Layers

The default hydrology configuration ships with Fairfax County data:

1. **fairfax-water-lines**
   - PMTiles: `fairfax_water_lines.pmtiles`
   - Attributes: `name`, `type`, `length_km`, `data_source`
   - Styled by `type` to highlight streams, channels, ditches, canals

2. **fairfax-water-polys**
   - PMTiles: `fairfax_water_polys.pmtiles`
  - Attributes: `name`, `type`, `area_sqkm`, `data_source`
   - Filled polygons for ponds, lakes, reservoirs

3. **perennial-streams**
   - PMTiles: `perennial_streams.pmtiles`
   - Attributes: `name`, `feature_type`, `length_km`
   - Deep-blue overlay emphasising perennial-only network

Topographic Wetness Index (TWI) complements these layers for modeled wetness. Legacy DEM/NHD streams can still be added by extending `LAYER_SOURCES`.

### HUC12 Multi-Layer Pattern

**Single PMTiles source** (`huc12.pmtiles`) with **three MapLibre layers**:

1. `huc12-fill`: Polygon fill (low opacity)
2. `huc12-outline`: Polygon outline/stroke
3. `huc12-labels`: Text labels showing HUC12 codes

**Configuration**:
- All three sub-layers share the same PMTiles source
- Controlled by single visibility toggle in UI
- Sub-layer visibility inherits from parent `huc12` layer state

**Pattern Benefits**:
- Rich visualization from single tile source
- Efficient: Only one PMTiles file
- Flexible: Can toggle fill/outline/labels independently if needed

## Performance Optimizations

### Frontend

- **Client-side tiles**: No server roundtrips for raster/vector data
- **Lazy loading**: Tiles loaded on demand by zoom level
- **Debouncing**: Limit API calls on rapid map interactions
- **Svelte reactivity**: Minimal re-renders, efficient DOM updates
- **Tile health checks**: PMTiles metadata cached and reused to avoid redundant HEAD requests
- **localStorage persistence**: Map view, panel states, search history stored locally
- **Windowed tile loading**: MapLibre only requests tiles in viewport

### Backend

- **Caching**: Avoid re-computing identical watersheds via file/Redis cache
- **Windowed raster reading**: Only read small windows around pour point or profile line
- **Async operations**: `asyncio.to_thread` for CPU-bound tasks (snapping)
- **Pydantic validation**: Fast input validation with early rejection
- **Static PMTiles serving**: Zero computation for tile requests
- **Lazy dataset loading**: Vector datasets loaded on demand, not at startup

### Data

- **Tile pyramids**: Multi-resolution tiles (zoom 8-17) for progressive enhancement
- **Compression**: LZW for raster tiles, gzip for vector tiles
- **Geometry simplification**: Reduce vertices for web display
- **Spatial indexes**: GeoPackage spatial indexes for fast queries
- **PMTiles format**: Cloud-optimized with efficient range requests

## Scalability Considerations

### Current Architecture (Small/Local)

- **Users**: 1-10 concurrent users
- **Area**: Single watershed/county (~100-500 sq mi)
- **Storage**: ~1-5 GB processed data
- **Compute**: Single server (desktop or small VM)

### Scale-Up Options

**More Users (10-1000)**:
- Deploy backend behind load balancer (nginx, HAProxy)
- Use Redis for distributed caching
- Serve PMTiles from CDN (S3 + CloudFront, GCS + Cloud CDN)
- Horizontal scaling: Multiple FastAPI instances

**Larger Areas (State/Regional)**:
- Tile DEM into manageable chunks (COG - Cloud Optimized GeoTIFF)
- Pre-compute watersheds for known outlets
- Use PostGIS for vector data queries
- Stream large rasters with GDAL VRT

**More Features**:
- Add background job queue (Celery, RQ) for long computations
- Real-time updates via WebSockets
- User accounts with saved analyses (PostgreSQL)
- Database-backed caching (PostgreSQL, Redis)

## Security

### Current Implementation

- **CORS**: Configured allowed origins in settings
- **Input validation**: Pydantic models validate all API inputs
- **File access**: Restricted to data directory (no path traversal)
- **No authentication**: Open access (suitable for demo/research)

### Production Additions

- **Authentication**: JWT tokens, OAuth2
- **Rate limiting**: Per IP/user (slowapi, Redis)
- **Input sanitization**: Additional validation for file paths
- **HTTPS**: SSL certificates (Let's Encrypt)
- **API keys**: For external access
- **CSP headers**: Content Security Policy

## Monitoring

### Recommended Metrics

- **API response times**: p50, p95, p99 latency
- **Cache hit rates**: Track delineation cache effectiveness
- **Tile request counts**: Monitor tile usage patterns
- **Error rates**: By endpoint and error type
- **DEM read latencies**: Track raster I/O performance
- **Active users**: Concurrent sessions
- **Watershed delineation volume**: Requests per hour

### Tools

- **FastAPI**: Built-in OpenAPI docs at `/docs`
- **Logging**: Python logging to file/stdout (configurable levels)
- **APM**: Application Performance Monitoring (Sentry, Datadog, New Relic)
- **Metrics**: Prometheus + Grafana
- **Uptime**: UptimeRobot, Pingdom

## Testing

### Unit Tests

- **Backend**: pytest for services
  - `tests/test_watershed.py`: Delineation logic
  - `tests/test_cache.py`: Cache operations
- **Frontend**: Vitest for components
  - Layer visibility toggling
  - Store mutations
  - Utility functions

### Integration Tests

- **API**: httpx with FastAPI TestClient
  - Endpoint response validation
  - Error handling
  - Cache behavior
- **E2E**: Playwright for browser testing
  - Map interactions
  - Watershed delineation workflow
  - Cross-section drawing

### Data Validation

- Check DEM for nodata cells
- Verify stream network topology (no dangles)
- Validate geometry integrity (no self-intersections)
- Confirm PMTiles metadata (tile type, format)

## Deployment

### Development

```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

### Production

**Option 1: Docker Compose**
```bash
docker-compose up -d
```

**Option 2: Systemd Services**
```bash
# Backend service
sudo systemctl start hydro-map-backend

# Frontend (static build served by nginx)
npm run build
sudo systemctl start nginx
```

**Option 3: Kubernetes**
- Backend: FastAPI pods behind LoadBalancer service
- Frontend: Static build served by nginx ingress
- PMTiles: Object storage (S3/GCS) with CDN

**Option 4: Serverless**
- Backend: AWS Lambda + API Gateway (or Azure Functions)
- Frontend: Vercel/Netlify static hosting
- PMTiles: S3 + CloudFront with range request support

### Environment Variables

See [docs/CONFIGURATION.md](CONFIGURATION.md) for complete configuration reference.

## Future Architecture Enhancements

1. **Real-time Collaboration**: WebSocket for shared map sessions
2. **Vector Tile Server**: pg_tileserv or martin for PostGIS-backed tiles
3. **3D Visualization**: Cesium or deck.gl for terrain fly-throughs
4. **Time Series Analysis**: Historical DEM comparison, change detection
5. **Mobile Support**: Progressive Web App (PWA) or React Native
6. **ML Integration**: Landcover classification, flood prediction models
7. **Distributed Processing**: Dask or Apache Spark for large-scale analysis
8. **User Accounts**: Save analyses, share watersheds, export reports

## References

- [MapLibre GL JS Documentation](https://maplibre.org/maplibre-gl-js-docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WhiteboxTools Manual](https://www.whiteboxgeo.com/manual/wbt_book/)
- [PMTiles Specification](https://github.com/protomaps/PMTiles)
- [Svelte Tutorial](https://svelte.dev/tutorial)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [GDAL Documentation](https://gdal.org/)
- [Tippecanoe](https://github.com/felt/tippecanoe)
