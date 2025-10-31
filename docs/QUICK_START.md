# Quick Start Guide

Get Hydro-Map running in minutes.

## Prerequisites Check

```bash
# Check if you have the required tools
python3 --version  # Should be 3.11+
node --version     # Should be 20+
gdal-config --version  # Required for processing
```

## Setup (One-time)

```bash
# Run the automated setup script
./scripts/setup.sh

# Or manually:
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install
```

## Get Sample Data

For testing, download a small DEM:

```bash
# Example: San Francisco Bay Area (small test area)
# Download from USGS National Map or use your own DEM
# Place it at: data/raw/dem/elevation.tif
```

## Process Data

```bash
# 1. Process DEM (5-10 minutes for ~100 sq mi)
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# 2. Extract streams (2-5 minutes)
python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams.gpkg \
  --threshold 1000

# 3. Generate web tiles (requires GDAL, Tippecanoe, PMTiles CLI)
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 2
```
> Defaults produce 1 m contour spacing; passing `--contour-interval 2` (as above) generally balances legibility at the 200 m–100 m map scale. Tweak `--max-zoom` or `--contour-interval` if your DEM resolution or styling goals call for different values, and use `--raster-resampling nearest` whenever you tile categorical rasters.

## Run the Application

### Terminal 1: Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

### Open Browser
Navigate to: http://localhost:5173

## First Steps in the App

1. **View Terrain**: Toggle hillshade layer in the Layer Panel
2. **See Streams**: Enable stream network layer
3. **Delineate Watershed**:
   - Click "Delineate Watershed"
   - Click anywhere on the map
   - View the upstream catchment polygon with statistics
4. **Draw Cross-Section**:
   - Click "Draw Cross-Section"
   - Click 2+ points to draw a line
   - Click "Generate Profile"
5. **Check Tile Coverage**:
   - Review the **Tile Status** panel; each PMTiles source reports whether it covers the current map center and flags when you overzoom past its native maximum.
   - If a layer reports "Unavailable", regenerate tiles for the current area of interest or adjust the map view.

## Common Issues

### Backend won't start
```bash
# Check if all data files exist
curl http://localhost:8000/api/delineate/status
```

### No tiles appearing
- Ensure tiles were generated in `data/tiles/` (Tile Status panel should report "Available").
- Check browser console for errors (look for `/tiles/*.pmtiles` 404/500 responses).
- Verify paths in frontend Map.svelte match your data and that the backend has read access.

### Delineation fails
- Ensure flow_direction.tif and flow_accumulation.tif exist
- Check that pour point is within DEM extent
- Try with snap_to_stream disabled

## Next Steps

- Add geology data (see DATA_PREPARATION.md)
- Customize layer styles (edit Map.svelte)
- Deploy to production (see README.md deployment section)
- Add more features (see ARCHITECTURE.md)

## Quick Commands Reference

```bash
# Start development (from project root)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload &
cd frontend && npm run dev

# Check API status
curl http://localhost:8000/health
curl http://localhost:8000/api/delineate/status

# Delineate watershed via API
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true}'

# Run tests
cd backend && pytest
cd frontend && npm run check

# Build for production
cd frontend && npm run build
```

## Resources

- Full setup: [README.md](../README.md)
- Data preparation: [DATA_PREPARATION.md](./DATA_PREPARATION.md)
- Architecture details: [ARCHITECTURE.md](./ARCHITECTURE.md)
- API docs: http://localhost:8000/docs (when backend is running)
