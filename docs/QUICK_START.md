# Quick Start Guide

**Version**: 1.9.0  
Goal: get Hydro-Map running locally with the Fairfax demo dataset in under an hour.

---

## 1. Prerequisites

Install the following first:

- Python 3.12+ with `pip`
- Node.js 20+
- GDAL (includes `gdalwarp`, `gdaldem`, `gdal2tiles.py`)
- Tippecanoe
- PMTiles CLI (`pmtiles`)

Quick verification:

```bash
python3 --version
node --version
gdal-config --version
tippecanoe --version
pmtiles --version
```

- macOS: `brew install python@3.12 node gdal tippecanoe` and `cargo install pmtiles` (or download a binary).  
- Ubuntu/Debian: `sudo apt install python3.12 python3-venv python3-pip nodejs npm gdal-bin libgdal-dev` and install Tippecanoe/PMTiles from their GitHub releases.

---

## 2. Project Setup

```bash
git clone https://github.com/HurleySk/hydro-map.git
cd hydro-map

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

# Environment
cp .env.example .env
```

Add a Stadia Maps API key (`VITE_STADIA_API_KEY=...`) if you want the detailed/vector basemap. Without a key, the “Data Only” basemap still works.

---

## 3. Acquire Sample Data

Place a DEM at `data/raw/dem/elevation.tif`. For quick tests:

- Download USGS 3DEP 1/3″ (10 m) DEM covering your area.  
- Or grab Copernicus GLO-30 (30 m) via OpenTopography for global coverage.

Ensure the file is unzipped and clipped/mosaicked if needed.

---

## 4. Process Data

Activate the backend virtualenv before running scripts:

```bash
cd backend
source venv/bin/activate
cd ..
```

Run the core workflow:

```bash
# 4.1 DEM derivatives
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# 4.2 Fairfax hydrography (lines, polygons, perennial streams, watersheds)
python scripts/download_fairfax_hydro.py
python scripts/prepare_fairfax_hydro.py

# 4.3 Fairfax stormwater overlays (floodplain + inadequate outfalls)
python scripts/download_fairfax_stormwater.py
python scripts/prepare_fairfax_stormwater.py

# 4.4 (Optional) Topographic Wetness Index tiles
python scripts/compute_twi.py --output data/processed/dem/twi.tif
python scripts/process_twi_for_tiles.py
```

Outputs land in `data/processed/` and are ready for tiling.

---

## 5. Generate PMTiles

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --min-zoom 8 \
  --max-zoom 17 \
  --contour-interval 10
```

Expected PMTiles include `hillshade`, `slope`, `aspect`, `twi` (if generated), `fairfax_water_lines`, `fairfax_water_polys`, `perennial_streams`, `fairfax_watersheds`, `floodplain_easements`, `inadequate_outfalls`, and `inadequate_outfall_points`.

---

## 6. Run Hydro-Map

**Backend**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**
```bash
cd frontend
npm run dev -- --host
# Dev server -> http://localhost:5173
```

Open <http://localhost:5173>. The default map view is centered on San Francisco. Adjust the startup extent by editing `DEFAULT_MAP_VIEW` in `frontend/src/lib/stores.ts`.

---

## 7. First Look Checklist

1. **Layers panel**  
   - Toggle terrain rasters (Hillshade/Slope/Aspect).  
   - Expand Hydrology and enable Fairfax lines, polygons, perennial streams, floodplain easements, and outfall layers.  
   - Expand Reference and toggle Fairfax Watersheds and Geology (if data exists).

2. **Analysis tools**  
   - Run “Delineate Watershed” on a stream; results show the watershed polygon, area stats, and snapped pour point.  
   - Use “Draw Cross-Section” to digitize a line and inspect the elevation chart and geology contacts.  
   - Switch to “Feature Info” to query geology, Fairfax watershed name, and DEM samples.

3. **System status**  
   - Open the Tile Status panel to verify each PMTiles source is reachable in your current viewport.

---

## 8. Sanity Checks

```bash
# Backend health
curl http://localhost:8000/health

# Required raster availability
curl http://localhost:8000/api/delineate/status

# Sample delineation (San Francisco)
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true}'

# Tile reachability
curl -I http://localhost:8000/tiles/hillshade.pmtiles
```

If anything fails, jump to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 9. Next Steps

- Review [DATA_PREPARATION.md](DATA_PREPARATION.md) for detailed workflows, optional data, and verification tips.
- Skim [ARCHITECTURE.md](ARCHITECTURE.md) to understand how frontend, backend, and preprocessing connect.
- Check [CONFIGURATION.md](CONFIGURATION.md) before deploying or changing data paths.
