# Configuration Guide

**Version**: 1.2.1

## Overview

Hydro-Map is configured through environment variables, configuration files, and layer definitions. This guide covers all configuration options for both backend and frontend components.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Backend Configuration](#backend-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Layer Configuration](#layer-configuration)
- [Data Paths](#data-paths)
- [Performance Tuning](#performance-tuning)
- [Development vs Production](#development-vs-production)

---

## Environment Variables

### Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` to customize your configuration.

### Backend Settings

#### Server Configuration

```bash
# Host address (0.0.0.0 = all interfaces, 127.0.0.1 = localhost only)
BACKEND_HOST=0.0.0.0

# Port for API server
BACKEND_PORT=8000

# Enable auto-reload on code changes (development only)
BACKEND_RELOAD=true
```

**Production recommendations**:
- Set `BACKEND_HOST=0.0.0.0` to accept external connections
- Set `BACKEND_RELOAD=false` for production (reload adds overhead)
- Use a process manager (systemd, supervisord) instead of reload

#### Data Paths

All paths are relative to the `backend/` directory unless absolute paths are provided.

```bash
# DEM and hydrological derivatives
DEM_PATH=../data/processed/dem/filled_dem.tif
FLOW_DIR_PATH=../data/processed/dem/flow_direction.tif
FLOW_ACC_PATH=../data/processed/dem/flow_accumulation.tif

# Vector data
STREAMS_PATH=../data/processed/streams.gpkg
GEOLOGY_PATH=../data/processed/geology.gpkg
```

**Path resolution**:
- Relative paths: Resolved relative to `backend/` directory
- Absolute paths: Used as-is
- Docker: Mount data volume at `/app/data` and use `./data/processed/...`

#### Watershed Delineation

```bash
# Automatically snap pour points to nearest stream
SNAP_TO_STREAM=true

# Default snap radius in meters (used if not specified in API request)
DEFAULT_SNAP_RADIUS=100

# Enable caching of delineation results
CACHE_ENABLED=true

# Cache directory path (relative to backend/)
CACHE_DIR=./data/cache
```

**Cache behavior**:
- Cache key format: `{lat:.6f},{lon:.6f}|snap:{flag}|radius:{radius}`
- Cache files stored as JSON in `CACHE_DIR/watersheds/`
- Cache hit dramatically improves response time (2-3s → <50ms)

**Tuning**:
- `SNAP_TO_STREAM=false`: Exact coordinates, no stream adjustment
- `DEFAULT_SNAP_RADIUS=50`: Smaller radius for dense stream networks
- `DEFAULT_SNAP_RADIUS=200`: Larger radius for sparse networks
- `CACHE_ENABLED=false`: Disable if disk space is limited (all requests recomputed)

#### Cross-Section Configuration

```bash
# Sample interval in meters for elevation profiles
CROSS_SECTION_SAMPLE_DISTANCE=10

# Maximum number of sample points per profile
CROSS_SECTION_MAX_POINTS=1000
```

**Tradeoffs**:
- Smaller `SAMPLE_DISTANCE`: More detail, larger response, slower processing
- Larger `SAMPLE_DISTANCE`: Less detail, smaller response, faster processing
- `MAX_POINTS` prevents excessive memory/bandwidth for long lines

**Recommendations**:
- **High-resolution terrain (10m DEM)**: `SAMPLE_DISTANCE=10`
- **Medium-resolution (30m DEM)**: `SAMPLE_DISTANCE=25`
- **Low-resolution (90m DEM)**: `SAMPLE_DISTANCE=50`

#### CORS Configuration

```bash
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Production**:
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Security note**: Do not use `*` for CORS_ORIGINS in production. Explicitly list allowed domains.

#### Optional: Redis Configuration

```bash
# Redis host (if using Redis for caching instead of disk)
REDIS_HOST=localhost

# Redis port
REDIS_PORT=6379

# Redis database number
REDIS_DB=0
```

**When to use Redis**:
- High-traffic deployments requiring fast caching
- Multiple backend instances sharing cache
- Need for cache expiration policies

**Default**: Disk-based caching (simpler, no extra dependencies)

---

## Backend Configuration

### File: `backend/app/config.py`

Backend configuration is loaded using Pydantic settings from environment variables.

#### Key Configuration Class

```python
class Settings(BaseSettings):
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = True

    # Data paths
    DEM_PATH: str = "../data/processed/dem/filled_dem.tif"
    FLOW_DIR_PATH: str = "../data/processed/dem/flow_direction.tif"
    FLOW_ACC_PATH: str = "../data/processed/dem/flow_accumulation.tif"
    STREAMS_PATH: str = "../data/processed/streams.gpkg"
    GEOLOGY_PATH: str = "../data/processed/geology.gpkg"

    # Watershed settings
    SNAP_TO_STREAM: bool = True
    DEFAULT_SNAP_RADIUS: int = 100
    CACHE_ENABLED: bool = True
    CACHE_DIR: str = "./data/cache"

    # Cross-section
    CROSS_SECTION_SAMPLE_DISTANCE: int = 10
    CROSS_SECTION_MAX_POINTS: int = 1000

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
```

### Modifying Configuration

**Option 1 - Environment variables** (recommended):
```bash
export BACKEND_PORT=8080
export DEFAULT_SNAP_RADIUS=150
```

**Option 2 - .env file** (recommended for persistent config):
```bash
BACKEND_PORT=8080
DEFAULT_SNAP_RADIUS=150
```

**Option 3 - Modify config.py** (not recommended, harder to deploy):
```python
# backend/app/config.py
DEFAULT_SNAP_RADIUS: int = 150  # Changed from 100
```

---

## Frontend Configuration

### SvelteKit Configuration

#### File: `frontend/svelte.config.js`

Standard SvelteKit configuration. No customization typically needed.

#### File: `frontend/vite.config.ts`

Vite build configuration. Default settings work for most cases.

### Environment Variables

Frontend environment variables use Vite's `VITE_` prefix.

#### File: `frontend/.env` (create if needed)

```bash
# API backend URL
VITE_API_URL=http://localhost:8000

# PMTiles tile server URL (usually same as backend)
VITE_TILES_URL=http://localhost:8000/tiles
```

**Production**:
```bash
VITE_API_URL=https://api.yourdomain.com
VITE_TILES_URL=https://api.yourdomain.com/tiles
```

### Build-Time vs Runtime Configuration

**Build-time** (baked into build):
- `VITE_*` environment variables
- Cannot be changed without rebuilding

**Runtime** (dynamic):
- None currently implemented
- Consider using a config endpoint if runtime config is needed

---

## Layer Configuration

### File: `frontend/src/lib/config/layers.ts`

**Single source of truth** for all map layers (v1.2.0+).

#### Layer Source Interface

```typescript
interface LayerSource {
  id: string                    // Unique layer ID
  label: string                 // Display name in UI
  filename: string              // PMTiles filename
  type: 'raster' | 'vector'     // Layer type
  vectorLayerId?: string        // Internal layer name in PMTiles (vector only)
  minZoom?: number              // Minimum zoom level
  maxZoom?: number              // Maximum zoom level
  defaultVisible: boolean       // Visible on startup
  defaultOpacity: number        // Initial opacity (0-1)
  category: 'terrain' | 'hydrology' | 'reference'
  paintProperties?: object      // MapLibre paint properties
  description?: string          // Tooltip description
}
```

#### Example Layer Configuration

```typescript
{
  id: 'hillshade',
  label: 'Hillshade',
  filename: 'hillshade.pmtiles',
  type: 'raster',
  defaultVisible: false,
  defaultOpacity: 0.6,
  category: 'terrain',
  description: 'Shaded relief visualization of terrain'
}
```

### Adding a New Layer

1. **Generate PMTiles file**:
   ```bash
   # See docs/tile-generation.md for tile creation
   ```

2. **Add to LAYER_SOURCES array** in `layers.ts`:
   ```typescript
   {
     id: 'my-new-layer',
     label: 'My New Layer',
     filename: 'my_layer.pmtiles',
     type: 'raster',
     defaultVisible: false,
     defaultOpacity: 0.8,
     category: 'terrain',
     description: 'Custom layer description'
   }
   ```

3. **Place PMTiles file**:
   ```bash
   cp my_layer.pmtiles data/tiles/
   ```

4. **Restart application** - Layer automatically appears in UI

**No manual editing of Map.svelte or LayerPanel.svelte required!** (as of v1.2.0)

### Layer Rendering Order

Layers are rendered in **array order** (first = bottom, last = top):
1. Basemap (underneath everything)
2. Terrain raster layers (hillshade, slope, aspect)
3. Hydrology raster (flow accumulation)
4. HUC12 fill
5. Contours
6. Streams (nhd, dem)
7. HUC12 outline
8. HUC12 labels
9. User-drawn features (top)

**To change order**: Reorder entries in `LAYER_SOURCES` array.

### Vector Layer ID Consistency

**Critical**: `vectorLayerId` must match the actual layer name inside the PMTiles file.

**Check internal layer name**:
```bash
pmtiles show data/tiles/streams_nhd.pmtiles | grep "layer ID"
```

**Common mistakes**:
- `vectorLayerId: 'streams'` but PMTiles contains `streams_t250_filtered` → layer won't render
- Forgetting to set `vectorLayerId` for vector sources → layer won't render

**Fix**: Regenerate tiles with correct internal layer name, or update `vectorLayerId` in config.

---

## Data Paths

### Directory Structure

Expected data layout:

```
hydro-map/
├── data/
│   ├── raw/                    # Original source data
│   │   ├── dem/
│   │   ├── nhd/
│   │   └── wbd/
│   ├── processed/              # Prepared data for backend
│   │   ├── dem/
│   │   │   ├── filled_dem.tif
│   │   │   ├── flow_direction.tif
│   │   │   └── flow_accumulation.tif
│   │   ├── streams_nhd.gpkg
│   │   ├── streams_dem.gpkg
│   │   ├── huc12.gpkg
│   │   └── geology.gpkg
│   ├── tiles/                  # PMTiles for frontend
│   │   ├── hillshade.pmtiles
│   │   ├── slope.pmtiles
│   │   ├── aspect.pmtiles
│   │   ├── streams_nhd.pmtiles
│   │   ├── streams_dem.pmtiles
│   │   ├── flow_accum.pmtiles
│   │   ├── contours.pmtiles
│   │   └── huc12.pmtiles
│   └── cache/                  # Delineation cache
│       └── watersheds/
└── backend/
    └── app/
```

### Configuring Alternate Data Locations

**Scenario**: Data stored on external drive at `/mnt/hydrodata/`

**Option 1 - Absolute paths in .env**:
```bash
DEM_PATH=/mnt/hydrodata/processed/dem/filled_dem.tif
FLOW_DIR_PATH=/mnt/hydrodata/processed/dem/flow_direction.tif
# ... etc
```

**Option 2 - Symlink**:
```bash
ln -s /mnt/hydrodata/ data
# Then use default relative paths
```

**Docker**: Mount external volume:
```yaml
volumes:
  - /mnt/hydrodata:/app/data
```

---

## Performance Tuning

### Backend Performance

#### Caching

**Enable caching** for production:
```bash
CACHE_ENABLED=true
CACHE_DIR=./data/cache
```

**Monitor cache size**:
```bash
du -sh backend/data/cache/
```

**Clear cache** if it grows too large:
```bash
rm -rf backend/data/cache/watersheds/*
```

#### Processing Optimization

**WhiteboxTools**: Already optimized (compiled Rust/C++)

**Rasterio**: Uses GDAL windowed reading (efficient for large DEMs)

**Geopandas**: Spatial indexing enabled automatically

#### API Response Time

Typical response times (10m DEM, 10 km² watershed):
- **First request**: 2-3 seconds (compute + cache write)
- **Cached request**: <50ms (cache read only)
- **Cross-section**: 500-1000ms (depends on line length)
- **Feature info**: 100-300ms (spatial query)

**Slow requests troubleshooting**:
- Check DEM file size (>1 GB may be slow to open)
- Verify DEM has internal tiling and overviews
- Enable caching if disabled
- Use SSD storage for data files

### Frontend Performance

#### Tile Loading

**PMTiles advantages**:
- Client-side HTTP range requests (efficient)
- Only loads visible tiles
- Automatic caching in browser

**Optimize tile sizes**:
- Raster tiles: z8-z17 (balance detail vs file size)
- Vector tiles: z8-z17 for streams, z8-z14 for large polygons

**Check tile file sizes**:
```bash
ls -lh data/tiles/
```

Typical sizes:
- Hillshade (z8-z17): 20-30 MB
- Slope (z8-z17): 5-10 MB
- Aspect (z8-z17): 5-10 MB
- Streams (z8-z17): 2-5 MB
- HUC12 (z8-z14): 1-3 MB

**If tiles are too large**:
- Reduce max zoom level
- Use higher compression (PNG for rasters)
- Simplify vector geometries

#### Browser Performance

**Layer visibility**:
- Hidden layers still consume memory (just not rendered)
- Consider removing unused layers from config entirely

**Opacity**:
- Changing opacity does not reduce rendering cost
- Transparent layers still fully rendered

**Multiple watersheds**:
- Each watershed adds GeoJSON feature to map
- 100+ watersheds may slow map interaction
- Clear old watersheds periodically

---

## Development vs Production

### Development Configuration

```bash
# .env
BACKEND_HOST=127.0.0.1        # Localhost only
BACKEND_PORT=8000
BACKEND_RELOAD=true           # Auto-reload on code changes
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Frontend**:
```bash
npm run dev                   # Vite dev server with HMR
```

**Backend**:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload # Hot reload enabled
```

### Production Configuration

```bash
# .env
BACKEND_HOST=0.0.0.0          # All interfaces
BACKEND_PORT=8000
BACKEND_RELOAD=false          # No reload in production
CORS_ORIGINS=https://yourdomain.com
CACHE_ENABLED=true
```

**Frontend**:
```bash
npm run build                 # Build static files
npm run preview               # Test production build
# Deploy dist/ to static host or use adapter
```

**Backend**:
```bash
# Use gunicorn or uvicorn with workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Security Hardening (Production)

1. **Disable debug mode**:
   - Set `BACKEND_RELOAD=false`

2. **Restrict CORS**:
   - Never use `*` for CORS_ORIGINS
   - List explicit domains only

3. **Serve over HTTPS**:
   - Use reverse proxy (nginx, Caddy) with TLS
   - Redirect HTTP → HTTPS

4. **Rate limiting**:
   - Implement at reverse proxy level
   - Or use FastAPI middleware (slowapi)

5. **Authentication** (if needed):
   - Add API key middleware
   - Use OAuth2 for user authentication

6. **File permissions**:
   - Data files: 644 (read-only for backend process)
   - Cache directory: 755 (writable by backend)
   - Prevent directory traversal attacks

See [Deployment Guide](DEPLOYMENT.md) for complete production setup.

---

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Architecture](ARCHITECTURE.md) - System design overview
- [Data Preparation](DATA_PREPARATION.md) - Generating required data files
- [Troubleshooting](TROUBLESHOOTING.md) - Common configuration issues

---

## Configuration Checklist

Before running the application:

- [ ] `.env` file created and configured
- [ ] Data files generated and placed in correct directories
- [ ] PMTiles files available in `data/tiles/`
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] CORS origins match frontend URL
- [ ] Data paths point to existing files
- [ ] Cache directory exists and is writable

For production additionally:

- [ ] `BACKEND_RELOAD=false`
- [ ] CORS restricted to production domains
- [ ] HTTPS enabled via reverse proxy
- [ ] Rate limiting configured
- [ ] Process manager configured (systemd, supervisord)
- [ ] Log rotation enabled
- [ ] Monitoring/alerting configured
