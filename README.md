# Hydro-Map

An interactive web application for exploring hydrological and geological features, with on-demand watershed delineation, cross-section analysis, and multi-layer visualization.

## Features

### Core Capabilities

- **On-Demand Watershed Delineation**: Click any point on the map to instantly compute the upstream catchment area with detailed statistics.
- **Stream Network Visualization**: Interactive stream lines with Strahler order, flow direction, and length attributes.
- **Terrain Analysis**: Toggle hillshade, slope, aspect, and contour visualizations derived from the DEM.
- **Geological Mapping**: Overlay bedrock/surficial geology (when provided) with formation metadata.
- **Cross-Section Tool**: Draw a line to generate elevation and geology profiles, complete with a sparkline preview.
- **Feature Queries**: Inspect streams and geology at a clicked location using the Feature Info panel.
- **Tile Health Monitoring**: A built-in tile status panel reports coverage and reachability for every PMTiles source.

### Technical Highlights

- Client-side PMTiles rendering for fast, scalable map performance
- WhiteboxTools-powered hydrological analysis
- RESTful API with caching for delineation results
- Responsive Svelte frontend with MapLibre GL JS

## Architecture

```
hydro-map/
├── frontend/          # SvelteKit + MapLibre GL JS
│   ├── src/
│   │   ├── routes/   # Application pages
│   │   └── lib/      # Components and stores
│   └── package.json
├── backend/           # FastAPI + Python
│   ├── app/
│   │   ├── routes/   # API endpoints
│   │   └── services/ # Business logic
│   └── requirements.txt
├── scripts/           # Data preprocessing
│   ├── prepare_dem.py
│   ├── prepare_streams.py
│   └── generate_tiles.py
└── data/
    ├── raw/          # Original DEM, NHD, geology data
    ├── processed/    # Flow grids, prepared vectors
    └── tiles/        # PMTiles for web serving
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **GDAL** (for data processing)
- **Tippecanoe** (for vector tiles)
- **PMTiles CLI** (for tile conversion)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/HurleySk/hydro-map.git
   cd hydro-map
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env to configure paths and settings
   ```
   - Optional: create `frontend/.env` with `VITE_TILE_BASE=http://localhost:8000` so the dev frontend fetches PMTiles directly from the backend (avoids proxy issues with range requests).

3. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd ../frontend
   npm install
   ```

### Data Preparation

Before running the application, you need to prepare your data:

1. **Obtain DEM data**
   - US: Download 10m 3DEP from [USGS National Map](https://apps.nationalmap.gov/downloader/)
   - Global: Download Copernicus GLO-30 from [Copernicus](https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3)

2. **Place raw data**
   ```bash
   # Put your DEM in data/raw/dem/
   data/raw/dem/elevation.tif
   ```

3. **Run preprocessing scripts**
   ```bash
   # Process DEM (fills sinks, computes flow direction/accumulation, terrain products)
   python scripts/prepare_dem.py \
     --input data/raw/dem/elevation.tif \
     --output data/processed/dem/

   # Extract stream network
   python scripts/prepare_streams.py \
     --flow-acc data/processed/dem/flow_accumulation.tif \
     --flow-dir data/processed/dem/flow_direction.tif \
     --output data/processed/streams.gpkg \
     --threshold 1000

   # Generate PMTiles for web serving
   python scripts/generate_tiles.py \
     --data-dir data/processed \
     --output-dir data/tiles \
     --min-zoom 8 \
     --max-zoom 17 \
     --contour-interval 2
   ```
   - By default the script emits 1 m contour isolines; the example above passes `--contour-interval 2`, which pairs well with the 200 m/100 m target scale. Adjust `--max-zoom` or `--contour-interval` to suit your DEM resolution and styling goals.
   - Use the new `--raster-resampling` flag (default: `lanczos`) to fine-tune raster sharpness—switch to `nearest` for categorical rasters such as aspect or landcover.

4. **(Optional) Add geology data**
   - Download geology layers from [USGS](https://mrdata.usgs.gov/geology/state/)
   - Convert to GeoPackage: `ogr2ogr -f GPKG data/processed/geology.gpkg geology.shp`

> **Tip:** after generating tiles, verify that the backend can see them:
> ```bash
> curl -I http://localhost:8000/tiles/hillshade.pmtiles
> curl -I http://localhost:8000/tiles/streams.pmtiles
> ```
> A `200 OK` response (with `Accept-Ranges: bytes`) confirms the files are in place and will render when toggled in the map.

### Running the Application

#### Option 1: Development Mode (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --reload
# Backend runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5173
```

Open http://localhost:5173 in your browser. The map boots focused on Mason District Park (Annandale, VA); adjust `mapView` in local storage or `DEFAULT_CENTER` in `Map.svelte` if your study area differs.

#### Option 2: Docker Compose

```bash
docker-compose up
```

Access at http://localhost:5173

## Usage

### Watershed Delineation

1. Click the **"Delineate Watershed"** button in the left panel
2. Optionally enable **"Snap to nearest stream"** to snap pour points to high flow accumulation
3. Click anywhere on the map
4. The upstream watershed polygon appears with statistics:
  - Area (km², mi²)
  - Perimeter
  - Elevation statistics (min/max/mean/std)

Results are cached by snapped location for fast repeated queries.

### Cross-Section Profiles

1. Click **"Draw Cross-Section"**
2. Click 2+ points on the map to define a profile line
3. Click **"Generate Profile"**
4. View elevation profile with:
   - DEM-based terrain elevation
   - Surface geology contacts where line crosses formations
   - Formation names and rock types

### Layer Controls

Use the **Layers** panel to:
- Toggle visibility of terrain, streams, contours, and more.
- Adjust opacity per layer to blend terrain with vector overlays.
- Combine multiple layers for richer analysis sessions.

### Feature Information

Click **Feature Info** mode and click the map to see attributes of:
- Nearby streams (name, order, length)
- Geology at the point (formation, rock type, age)

### Basemap & Visibility Tools

- Switch between the default color basemap, a light-gray background, or hide the basemap entirely via the **Basemap** panel for better overlay control.
- The layer checklist reflects live MapLibre state—if toggling a layer has no visual effect, confirm the PMTiles exist for the current extent (see troubleshooting below).
- The **Tile Status** panel automatically checks reachability and coverage for each PMTiles source whenever you pan or zoom.

### Layer Visibility Checklist

Use the **Tile Status** panel in the left controls to confirm whether each PMTiles source covers the current map view; it now reports each archive’s native max zoom and flags when you are overzooming beyond it. Additionally, the following manual checks can help:

1. **Tiles reachable?**  
   Check DevTools → Network for `/tiles/*.pmtiles` requests. A `404` or `502` means the backend isn’t serving the files.
2. **Coverage matches AOI?**  
   Pan to the default start location (Mason District Park, Annandale, VA). If tiles were generated elsewhere, rebuild them for this extent.
3. **Vector layer names**  
   Run `pmtiles info data/tiles/streams.pmtiles` and ensure the layer name is `streams` (matching the map source-layer).

Re-run the preprocessing scripts or regenerate PMTiles as needed; restarting the backend will reload new files automatically.

## API Endpoints

### Watershed Delineation
```
POST /api/delineate
{
  "lat": 37.7749,
  "lon": -122.4194,
  "snap_to_stream": true,
  "snap_radius": 100
}
```

### Cross-Section
```
POST /api/cross-section
{
  "line": [[-122.4, 37.77], [-122.3, 37.78]],
  "sample_distance": 10
}
```

### Feature Info
```
POST /api/feature-info
{
  "lat": 37.7749,
  "lon": -122.4194,
  "layers": ["streams", "geology"],
  "buffer": 50
}
```

## Configuration

Edit `.env` to customize:

- **Data paths**: DEM, flow grids, streams, geology
- **Delineation settings**: Snap radius, cache options
- **Cross-section**: Sample distance, max points
- **Server**: Host, port, CORS origins

## Data Sources

### Recommended Data

- **DEM (US)**: [USGS 3DEP 10m](https://www.usgs.gov/3d-elevation-program)
- **DEM (Global)**: [Copernicus GLO-30](https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model)
- **Streams (US)**: [NHD/NHDPlus](https://www.usgs.gov/national-hydrography/national-hydrography-dataset)
- **Geology (US)**: [USGS State Geologic Maps](https://mrdata.usgs.gov/geology/state/)

### Processing Tools

- **WhiteboxTools**: DEM preprocessing, flow analysis
- **GDAL**: Raster/vector processing
- **Tippecanoe**: Vector tile generation
- **PMTiles**: Cloud-optimized tile archives

## Development

### Project Structure

```
frontend/src/
├── routes/+page.svelte          # Main application shell
├── lib/
│   ├── components/
│   │   ├── Map.svelte           # MapLibre integration & PMTiles protocol
│   │   ├── LayerPanel.svelte    # Layer toggles & opacity sliders
│   │   ├── WatershedTool.svelte # Delineation controls & summary
│   │   ├── CrossSectionTool.svelte
│   │   ├── FeatureInfoTool.svelte
│   │   ├── FeatureInfo.svelte
│   │   ├── TileStatusPanel.svelte
│   │   └── BaseMapToggle.svelte
│   ├── stores.ts                # Central Svelte stores (layers, tools, state)
│   └── utils/                   # Local storage helpers & geocoding client

backend/app/
├── main.py                      # FastAPI ASGI application
├── config.py                    # Environment-backed settings via Pydantic
├── routes/
│   ├── delineate.py             # Watershed delineation API
│   ├── cross_section.py         # Elevation & geology profile API
│   ├── features.py              # Stream/geology feature info API
│   └── tiles.py                 # PMTiles range request handler
└── services/
    ├── watershed.py             # Hydrology utilities (snapping, tracing, stats)
    └── cache.py                 # File/Redis cache abstraction for delineations
```

### Adding New Layers

1. Add layer configuration to `frontend/src/lib/stores.ts`
2. Add source and layer to MapLibre style in `Map.svelte`
3. Add layer controls to `LayerPanel.svelte`
4. Generate tiles with `scripts/generate_tiles.py`

## Troubleshooting

### "Delineation failed" Error
- Ensure preprocessing scripts have been run
- Check that `data/processed/dem/` contains flow_direction.tif and flow_accumulation.tif
- Verify paths in `.env` match your data structure

### "Required data files not found"
- Check `/api/delineate/status` endpoint to see which files are missing
- Re-run `prepare_dem.py` script

### Slow Performance
- Reduce DEM resolution for faster processing
- Increase stream extraction threshold in `prepare_streams.py`
- Enable caching in `.env` (CACHE_ENABLED=true)

### No Tiles Appearing
- Ensure tiles are generated in `data/tiles/`
- Check browser console for tile loading errors
- Verify PMTiles paths in MapLibre style

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **WhiteboxTools**: Open-source geospatial analysis (Dr. John Lindsay)
- **MapLibre GL JS**: Open-source mapping library
- **PMTiles**: Protomaps single-file tile archive format
- **USGS**: DEM, stream, and geology data

## Contributing

Contributions welcome! Please open issues or pull requests on GitHub.

## Contact

For questions or support, open an issue at https://github.com/HurleySk/hydro-map/issues
