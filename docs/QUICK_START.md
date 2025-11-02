# Quick Start Guide

**Version**: 1.2.1

Get Hydro-Map running in minutes.

## Prerequisites Check

```bash
# Check if you have the required tools
python3 --version  # Should be 3.12+
node --version     # Should be 20+
gdal-config --version  # Required for processing
tippecanoe --version  # Required for vector tiles
pmtiles --version  # Required for PMTiles conversion
```

### Installing Prerequisites

**macOS (Homebrew)**:
```bash
brew install python@3.12 node gdal tippecanoe
cargo install pmtiles  # Or download binary from GitHub
```

**Ubuntu/Debian**:
```bash
sudo apt install python3.12 python3-pip nodejs npm gdal-bin
# Install tippecanoe from source: https://github.com/felt/tippecanoe
# Install pmtiles from: https://github.com/protomaps/go-pmtiles
```

## Setup (One-time)

```bash
# Clone repository
git clone https://github.com/HurleySk/hydro-map.git
cd hydro-map

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend setup
cd frontend
npm install
cd ..

# Create .env file
cp .env.example .env
# Edit .env to configure paths if needed
```

## Get Sample Data

For testing, download a small DEM for your area of interest:

**Option 1: USGS 3DEP (US only)**
```bash
# Download from https://apps.nationalmap.gov/downloader/
# Select "Elevation Products (3DEP)" → "1/3 arc-second DEM"
# Choose your area and download
mkdir -p data/raw/dem
# Move downloaded file to data/raw/dem/elevation.tif
```

**Option 2: Copernicus GLO-30 (Global)**
```bash
# Download from https://portal.opentopography.org/
# Search for "Copernicus GLO-30"
# Download tile for your area
```

**San Francisco Bay Area (Example)**:
- Area: ~100 sq mi test region
- Download 10m 3DEP DEM for SF Bay coordinates
- Place at: `data/raw/dem/elevation.tif`

## Process Data

### Basic Workflow (DEM-Derived Streams Only)

```bash
# Activate backend venv
cd backend
source venv/bin/activate

# 1. Process DEM (5-10 minutes for ~100 sq mi)
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# This creates:
# - filled_dem.tif (depression-filled DEM)
# - flow_direction.tif (D8 flow direction)
# - flow_accumulation.tif (upstream cell count)
# - hillshade.tif (shaded relief)
# - slope.tif (slope angle in degrees)
# - aspect.tif (compass direction 0-360°)

# 2. Extract DEM-derived streams with multi-threshold workflow (2-5 minutes)
# Extract at multiple thresholds
python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_t100.gpkg \
  --threshold 100

python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_t250.gpkg \
  --threshold 250

python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_t500.gpkg \
  --threshold 500

# 3. Filter and merge streams (optional but recommended)
python scripts/filter_dem_streams.py \
  --input data/processed/streams_t250.gpkg \
  --output data/processed/streams_dem.gpkg

# 4. Generate web tiles (5-15 minutes depending on area and max zoom)
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 10 \
  --raster-resampling lanczos

# This creates PMTiles in data/tiles/:
# - hillshade.pmtiles (raster, z8-17)
# - slope.pmtiles (raster, z8-17)
# - aspect.pmtiles (raster, z8-17) - uses nearest-neighbor automatically
# - contours.pmtiles (vector, z8-17)
# - streams_dem.pmtiles (vector, z8-17) if streams_dem.gpkg exists
```

**Tip**: The `--contour-interval` defaults to 1m. For typical use at 100-200m viewing scale, 10m or 20m intervals work well and reduce file size.

### Advanced: Add NHD Streams

```bash
# 1. Download NHD data from https://www.usgs.gov/national-hydrography
# Place NHD Flowlines in data/raw/nhd/

# 2. Process NHD streams
python scripts/process_nhd.py \
  --input data/raw/nhd/NHDFlowline.shp \
  --output data/processed/streams_nhd.gpkg \
  --bounds data/processed/dem/filled_dem.tif

# 3. Optional: Merge with DEM-derived for comparison
python scripts/merge_streams.py \
  --nhd data/processed/streams_nhd.gpkg \
  --dem data/processed/streams_dem.gpkg \
  --output data/processed/streams_merged.gpkg

# 4. Generate tiles (will include streams_nhd.pmtiles)
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17
```

### Advanced: Add HUC12 Watershed Boundaries

```bash
# 1. Download WBD (Watershed Boundary Dataset) from USGS
# https://www.usgs.gov/national-hydrography/watershed-boundary-dataset

# 2. Process HUC12 boundaries
python scripts/process_huc.py \
  --input data/raw/wbd/WBDHU12.shp \
  --output data/processed/huc12.gpkg \
  --bounds data/processed/dem/filled_dem.tif

# 3. Generate tiles (will include huc12.pmtiles)
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 14  # HUC12 typically doesn't need z17
```

## Run the Application

### Terminal 1: Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using watchfiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

**Expected output**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### Open Browser
Navigate to: http://localhost:5173

**Default view**: Map centered on San Francisco, CA (default location set in stores.ts)

**To change default location**: Edit `DEFAULT_MAP_VIEW` in `frontend/src/lib/stores.ts`

## First Steps in the App

### 1. Explore the Interface

**Left Panel - Map Layers**:
- Terrain group: Hillshade, Slope, Aspect, Contours
- Hydrology group: Real Streams (NHD), DEM-Derived Streams, HUC12 Boundaries
- Toggle visibility and adjust opacity for each layer

**Left Panel - Analysis Tools**:
- Delineate Watershed
- Draw Cross-Section
- Feature Info

**Left Panel - System Status**:
- Tile Status panel shows coverage and max zoom for all PMTiles

### 2. View Terrain

1. Expand **Map Layers** panel
2. Expand **Terrain** group
3. Toggle **Hillshade** layer on
4. Adjust opacity slider (try 60% for good overlay visibility)
5. Toggle **Slope** or **Aspect** to see terrain analysis

### 3. View Stream Networks

1. Expand **Hydrology** group
2. **Real Streams** (NHD) is visible by default (if you processed NHD data)
3. Toggle **DEM-Derived Streams** to compare calculated vs. official streams
4. Notice the color gradient on DEM-derived streams (darker = larger drainage area)

### 4. Delineate a Watershed

1. Expand **Analysis Tools** panel
2. Click **"Delineate Watershed"** button (turns blue when active)
3. Optional: Enable **"Snap to nearest stream"** checkbox
4. Click anywhere on the map (preferably on or near a stream)
5. Wait 1-3 seconds for processing
6. View results:
   - Watershed polygon appears on map (semi-transparent blue)
   - Pour point shown as red dot
   - Statistics panel shows:
     - Area (km², mi²)
     - Perimeter
     - Elevation stats (min/max/mean/std)
7. Click elsewhere to delineate another watershed
8. Click **"Delineate Watershed"** again to exit mode

**Tip**: Cached results are instant - clicking the same location returns immediately.

### 5. Draw a Cross-Section

1. Click **"Draw Cross-Section"** in Analysis Tools
2. Click 2 or more points on the map to define a profile line
3. Click **"Generate Profile"** button
4. View elevation chart below the map
5. Hover over the chart to see elevation at each point
6. Click **"Clear"** to remove and start a new section

### 6. Check Tile Coverage

1. Expand **System Status** panel
2. Review **Tile Status** for each PMTiles source:
   - Green check = Available for current map view
   - Red X = Not available (out of bounds or file missing)
   - Max Zoom indicator shows native resolution
3. If a layer shows "Unavailable":
   - Pan map to area where you generated tiles
   - Or regenerate tiles for current area

### 7. Search for Locations

1. Use **Location Search** box at top
2. Type an address or place name
3. Select from search results
4. Map flies to location
5. Recent searches saved in dropdown

## Verify Installation

### Check Data Files

```bash
# Check DEM processing outputs
ls -lh data/processed/dem/
# Should see: filled_dem.tif, flow_direction.tif, flow_accumulation.tif,
#             hillshade.tif, slope.tif, aspect.tif

# Check stream outputs
ls -lh data/processed/*.gpkg
# Should see: streams_dem.gpkg (and streams_nhd.gpkg, huc12.gpkg if processed)

# Check PMTiles
ls -lh data/tiles/*.pmtiles
# Should see at minimum: hillshade.pmtiles, slope.pmtiles, aspect.pmtiles,
#                        contours.pmtiles, streams_dem.pmtiles
```

### Check Backend API

```bash
# Check backend health
curl http://localhost:8000/health

# Check data file availability
curl http://localhost:8000/api/delineate/status

# Test delineation (San Francisco coordinates)
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true, "snap_radius": 100}'
```

### Check Tile Serving

```bash
# Verify PMTiles are accessible
curl -I http://localhost:8000/tiles/hillshade.pmtiles
# Should return: 200 OK, Accept-Ranges: bytes

curl -I http://localhost:8000/tiles/streams_dem.pmtiles
# Should return: 200 OK
```

## Common Issues

### Backend won't start

**Error**: `ModuleNotFoundError: No module named 'xxx'`
```bash
# Solution: Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: '../data/processed/dem/flow_direction.tif'`
```bash
# Solution: Run data processing scripts first
python scripts/prepare_dem.py --input data/raw/dem/elevation.tif --output data/processed/dem/

# Or check status endpoint to see which files are missing
curl http://localhost:8000/api/delineate/status
```

### No tiles appearing

**Check Tile Status Panel**:
- Open System Status panel
- If tiles show "Unavailable":
  - Verify tiles exist: `ls data/tiles/*.pmtiles`
  - Check if map is in correct area (tiles only cover DEM extent)
  - Regenerate tiles if needed

**Check Browser Console**:
- Open DevTools (F12) → Console tab
- Look for errors like `/tiles/*.pmtiles 404` or `Failed to fetch`
- If 404: Tiles weren't generated, run `generate_tiles.py`
- If CORS error: Check backend CORS_ORIGINS in .env

**Check PMTiles Metadata**:
```bash
# Verify raster tile metadata (CRITICAL for rendering)
pmtiles show data/tiles/hillshade.pmtiles
# Should show: tile type: png, tile compression: png

# If metadata is missing, tiles won't render - regenerate with proper workflow
```

### Delineation fails

**Error**: "Delineation failed" in UI
```bash
# Check which files are missing
curl http://localhost:8000/api/delineate/status

# Common causes:
# 1. flow_direction.tif or flow_accumulation.tif missing
#    Solution: Run prepare_dem.py

# 2. Pour point outside DEM extent
#    Solution: Pan map to area covered by your DEM

# 3. Snap to stream fails (no streams in radius)
#    Solution: Disable "Snap to nearest stream" or increase radius
```

### Tiles render incorrectly

**Raster tiles show wrong colors or artifacts**:
- Check resampling method: aspect should use `nearest`, others use `lanczos`
- Verify tile addressing: must use `--xyz` flag with gdal2tiles (not TMS)
- Check metadata: run `pmtiles show <file>` to verify tile type

**Vector tiles don't appear**:
- Verify vector layer ID in PMTiles matches config
- Check: `pmtiles show data/tiles/streams.pmtiles | grep layer_name`
- Should match `vectorLayerId` in `frontend/src/lib/config/layers.ts`

### Map is blank

**All white or all black**:
- Check basemap toggle (might be set to "None")
- Try switching to "Color" or "Light" basemap

**Layers toggle but nothing shows**:
- Check zoom level (some layers have min/max zoom)
- Verify tile coverage (use Tile Status panel)
- Check browser console for errors

## Performance Tips

### Speed Up Processing

**Reduce DEM resolution**:
```bash
# Downsample large DEMs before processing
gdalwarp -tr 30 30 -r bilinear input.tif data/raw/dem/elevation.tif
# 30m resolution is sufficient for most watershed analysis
```

**Lower max zoom**:
```bash
# z14 instead of z17 = 8x fewer tiles, much faster
python scripts/generate_tiles.py --max-zoom 14 ...
```

**Use smaller area**:
```bash
# Clip DEM to area of interest
gdalwarp -te <xmin> <ymin> <xmax> <ymax> \
  -cutline boundary.geojson \
  large_dem.tif data/raw/dem/elevation.tif
```

### Speed Up Tile Loading

**Enable caching**:
- Browser automatically caches tiles
- Backend caches delineation results (set CACHE_ENABLED=true in .env)

**Use lower opacity**:
- Hillshade at 50-60% opacity renders faster than 100%

**Disable unused layers**:
- Only enable layers you're actively viewing

## Next Steps

### Add More Data

- **Geology layers**: See [DATA_PREPARATION.md](DATA_PREPARATION.md) Section 6
- **Additional stream sources**: Process multiple NHD datasets
- **Custom boundaries**: Add county, state, or custom watershed boundaries

### Customize Appearance

- **Layer styles**: Edit `frontend/src/lib/config/layers.ts` (LAYER_SOURCES)
- **Map colors**: Modify paint properties for vector layers
- **Basemap**: Change default basemap in Map.svelte

### Deploy to Production

- **Docker**: Use `docker-compose.yml` for containerized deployment
- **Cloud**: See [DEPLOYMENT.md](DEPLOYMENT.md) for AWS/Azure/GCP guides
- **CDN**: Serve PMTiles from S3 + CloudFront for better performance

### Development

- **Add new layers**: Edit LAYER_SOURCES in layers.ts, generate tiles, done
- **Custom analysis**: Add new endpoints to backend routes
- **UI enhancements**: Svelte components in frontend/src/lib/components/

## Quick Commands Reference

```bash
# Start development (from project root)
# Terminal 1:
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2:
cd frontend && npm run dev

# Check API status
curl http://localhost:8000/health
curl http://localhost:8000/api/delineate/status

# Delineate watershed via API
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true, "snap_radius": 100}'

# Generate cross-section via API
curl -X POST http://localhost:8000/api/cross-section \
  -H "Content-Type: application/json" \
  -d '{"line": [[-122.42, 37.77], [-122.40, 37.78]], "sample_distance": 10}'

# Run tests
cd backend && pytest
cd frontend && npm test

# Build for production
cd frontend && npm run build

# Verify PMTiles
pmtiles show data/tiles/hillshade.pmtiles
pmtiles show data/tiles/streams_dem.pmtiles

# Check tile in browser
# Hillshade tile at z10/x163/y395:
curl "http://localhost:8000/tiles/hillshade.pmtiles" \
  -H "Range: bytes=..." \
  --output tile.png
```

## Resources

- **Full Documentation**: [README.md](../README.md)
- **Data Preparation**: [DATA_PREPARATION.md](DATA_PREPARATION.md) - Complete workflows
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design details
- **API Reference**: [API.md](API.md) - Complete endpoint documentation
- **Configuration**: [CONFIGURATION.md](CONFIGURATION.md) - Environment variables
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- **Interactive API Docs**: http://localhost:8000/docs (when backend running)

## Getting Help

- **GitHub Issues**: https://github.com/HurleySk/hydro-map/issues
- **Check logs**: Backend logs appear in terminal, browser DevTools for frontend
- **Tile Status panel**: First place to check for tile availability issues
- **API status endpoint**: `/api/delineate/status` shows missing data files
