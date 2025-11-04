# Quick Start Guide

**Version**: 1.7.0

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
# Edit .env to add Stadia Maps API key and configure paths
```

### Configure Basemap API Key

Get a free Stadia Maps API key for feature-rich basemaps:

1. Sign up at https://client.stadiamaps.com/signup/ (free tier: 20k views/month)
2. Create an API key
3. Add to `.env`:
   ```bash
   VITE_STADIA_API_KEY=your_api_key_here
   ```

**Optional**: The app works without an API key by using "Data Only" basemap mode.

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

### Core Workflow (DEM + Fairfax Hydrography)

```bash
# Activate backend venv for scripts
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd ..

# 1. Process DEM (fills sinks, builds terrain derivatives)
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# Outputs: filled_dem.tif, flow_direction.tif, flow_accumulation.tif,
#          hillshade.tif, slope.tif, aspect.tif

# 2. Download Fairfax County hydrography (lines, polygons, perennial streams)
python scripts/download_fairfax_hydro.py

# Creates raw GeoPackages in data/raw/fairfax/

# 3. Normalize Fairfax hydrography (standardize fields, add metrics)
python scripts/prepare_fairfax_hydro.py

# Outputs processed GeoPackages in data/processed/:
#   fairfax_water_lines.gpkg, fairfax_water_polys.gpkg, perennial_streams.gpkg

# 4. (Optional) Generate Topographic Wetness Index tiles
# First compute TWI from DEM derivatives
python scripts/compute_twi.py --output data/processed/dem/twi.tif
# Then normalize & colorize for map display
python scripts/process_twi_for_tiles.py

# 5. Generate PMTiles (terrain rasters, Fairfax hydro, contours, geology if present)
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 10
```

**Notes**:
- `generate_tiles.py` automatically picks up Fairfax hydro GeoPackages, geology (`data/processed/geology.gpkg`), and HUC12 polygons if available.
- If you skip the TWI step, disable the layer in the UI or add tiles later.
- Adjust `--max-zoom` based on area size (z16 is plenty for county-scale projects).

### Optional Workflows

- **HUC12 Watersheds**: Run `scripts/process_huc.py` before `generate_tiles.py` to add watershed outlines.
- **Legacy DEM/NHD Streams**: See [Hydrology Data](data/STREAMS.md) for the previous multi-threshold extraction pipeline and guidance on integrating other regional networks.

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
- Hydrology group: Topographic Wetness Index (TWI), Fairfax Water Features (lines/polygons), Fairfax Perennial Streams
- Reference group: HUC12 Watersheds, Geology (legend appears automatically when geology is visible)
- Toggle visibility and adjust opacity for each layer

**Left Panel - Analysis Tools**:
- Feature Info (adjustable search buffer)
- Delineate Watershed
- Draw Cross-Section

**Left Panel - System Status**:
- Tile Status panel shows coverage and max zoom for all PMTiles

### 2. View Terrain

1. Expand **Map Layers** panel
2. Expand **Terrain** group
3. Toggle **Hillshade** layer on
4. Adjust opacity slider (try 60% for good overlay visibility)
5. Toggle **Slope** or **Aspect** to see terrain analysis

### 3. Explore Hydrology Layers

1. Expand **Hydrology** group
2. Toggle **Topographic Wetness Index** (TWI) for a raster view of likely wet terrain; adjust opacity to blend with the basemap
3. Enable **Fairfax Water Features (Lines/Polygons)** to view open-data streams, channels, ponds, and reservoirs
4. Toggle **Fairfax Perennial Streams** for a simplified perennial network overlay
5. Expand the **Reference** group to toggle HUC12 watersheds or geology; the geology legend appears automatically when the layer is visible

### 4. Delineate a Watershed

1. Expand **Analysis Tools** panel
2. Click **"Delineate Watershed"** button (turns blue when active)
3. Optional: Enable **"Snap to nearest stream"** if a stream dataset is configured for your project
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
4. Review the summary card (distance, number of samples, geology contacts) and elevation chart
5. Hover over the chart to see elevation at each point; geology bands appear if geology data is available
6. Click **"Clear Line"** to remove and start a new section

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

### 8. Inspect Nearby Features

1. Click **"Feature Info"** in Analysis Tools (button turns blue when active)
2. Adjust the **Search Buffer** slider (10-200 m) to control how far from the click point features are queried
3. Click the map inside your area of interest
4. Review geology, watershed (HUC12), and DEM sample attributes in the Feature Info panel; geology is returned even if the layer is hidden
5. Click **"Cancel"** to exit Feature Info mode

## Verify Installation

### Check Data Files

```bash
# Check DEM processing outputs
ls -lh data/processed/dem/
# Should see: filled_dem.tif, flow_direction.tif, flow_accumulation.tif,
#             hillshade.tif, slope.tif, aspect.tif

# Check Fairfax hydro outputs
ls -lh data/processed/fairfax*.gpkg data/processed/perennial_streams.gpkg
# Should see: fairfax_water_lines.gpkg, fairfax_water_polys.gpkg, perennial_streams.gpkg

# Check PMTiles
ls -lh data/tiles/*.pmtiles
# Should see at minimum: hillshade.pmtiles, slope.pmtiles, aspect.pmtiles,
#                        contours.pmtiles, fairfax_water_lines.pmtiles,
#                        fairfax_water_polys.pmtiles, perennial_streams.pmtiles
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

curl -I http://localhost:8000/tiles/fairfax_water_lines.pmtiles
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
#    Solution: Disable "Snap to nearest stream" unless you've configured a stream dataset in the backend
```

### Tiles render incorrectly

**Raster tiles show wrong colors or artifacts**:
- Check resampling method: aspect should use `nearest`, others use `lanczos`
- Verify tile addressing: must use `--xyz` flag with gdal2tiles (not TMS)
- Check metadata: run `pmtiles show <file>` to verify tile type

**Vector tiles don't appear**:
- Verify vector layer ID in PMTiles matches config
- Check: `pmtiles show data/tiles/fairfax_water_lines.pmtiles | grep layer_name`
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
