# Hydro-Map

**Version 1.5.0**

An interactive web application for exploring hydrological and geological features, with on-demand watershed delineation, cross-section analysis, and multi-layer visualization.

## Features

### Core Capabilities

- **On-Demand Watershed Delineation**: Click any point on the map to instantly compute the upstream catchment area with detailed statistics.
- **Topographic Wetness Index (TWI)**: Visualize areas prone to water saturation with a blue gradient showing dry to wet areas based on upslope area and slope.
- **Dual Stream Networks**: Visualize both NHD-based real streams and DEM-derived calculated streams with Strahler order, flow direction, and length attributes.
- **HUC12 Watershed Boundaries**: Reference layer showing USGS hydrologic unit boundaries with labels.
- **Terrain Analysis**: Toggle hillshade, slope, aspect, and contour visualizations derived from the DEM.
- **Cross-Section Tool**: Draw a line to generate elevation profiles with distance metrics, sample counts, and geology contact totals.
- **Feature Queries**: Inspect stream and geology attributes with an adjustable search buffer and structured warnings for data limitations.
- **Dataset Health Monitoring**: API endpoint (`/api/feature-info/status`) for checking data availability and integrity of all datasets.
- **Dynamic Legends**: Auto-display legends for TWI and geology layers, synced with layer visibility and opacity.
- **Tile Health Monitoring**: Built-in tile status panel reports coverage, reachability, and max zoom for every PMTiles source.
- **Colorblind Accessible**: Geology layer features distinct texture patterns alongside colors for red/green colorblind users.

### Technical Highlights

- Client-side PMTiles rendering for fast, scalable map performance
- WhiteboxTools-powered hydrological analysis
- RESTful API with caching for delineation results
- Responsive Svelte frontend with MapLibre GL JS

## Architecture

**Frontend**: SvelteKit + MapLibre GL JS + PMTiles
**Backend**: FastAPI + Python geospatial stack (WhiteboxTools, GDAL)
**Data Pipeline**: Preprocessing scripts for DEM analysis, stream extraction, and tile generation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed component hierarchy and data flow.

## Quick Start

### Prerequisites

- **Python 3.12+** (with pip)
- **Node.js 20+** (with npm)
- **GDAL, Tippecanoe, PMTiles CLI** (for data processing)

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed installation and setup instructions.

### Installation

```bash
git clone https://github.com/HurleySk/hydro-map.git
cd hydro-map

# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd ../frontend && npm install

# Configure environment
cp .env.example .env  # Add Stadia Maps API key and edit paths as needed
```

### Data Preparation

Prepare your DEM data and generate tiles:

```bash
# 1. Process DEM → flow grids + terrain products
python scripts/prepare_dem.py --input data/raw/dem/elevation.tif --output data/processed/dem/

# 2. Extract DEM-derived streams
python scripts/prepare_streams.py --flow-acc data/processed/dem/flow_accumulation.tif --output data/processed/streams_dem.gpkg

# 3. Generate PMTiles (hillshade, slope, aspect, contours, streams)
python scripts/generate_tiles.py --data-dir data/processed --output-dir data/tiles --max-zoom 17
```

For complete workflows including NHD stream processing and HUC12 boundaries, see [docs/DATA_PREPARATION.md](docs/DATA_PREPARATION.md).

### Running the Application

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

Open http://localhost:5173 in your browser. The map boots focused on San Francisco, CA (default location); adjust `mapView` in local storage or `DEFAULT_CENTER` in `frontend/src/lib/stores.ts` if your study area differs.

**Docker Option:**
```bash
docker-compose up  # Access at http://localhost:5173
```

## Usage

See [docs/UI_GUIDE.md](docs/UI_GUIDE.md) for comprehensive usage instructions. Quick overview:

### Watershed Delineation

1. Click **"Delineate Watershed"** in the Analysis Tools panel
2. Optionally enable **"Snap to nearest stream"**
3. Click anywhere on the map
4. View upstream watershed polygon with area, perimeter, and elevation statistics

Results are cached by location for fast repeated queries.

### Cross-Section Profiles

1. Click **"Draw Cross-Section"**
2. Click 2+ points to define a profile line
3. Click **"Generate Profile"** to view elevation along the transect

### Layer Controls

- **Map Layers panel**: Toggle visibility and adjust opacity for terrain, streams, contours, HUC12 boundaries
- **Terrain group**: Hillshade, slope, aspect, contours
- **Hydrology group**: Real streams (NHD), calculated streams (DEM-derived), Topographic Wetness Index
- **Reference group**: HUC12 boundaries, geology

### Feature Information

Click **Feature Info** mode and click the map to inspect nearby features:
- **Streams**: Name, Strahler order, length, flow direction
- **Geology**: Rock type, formation, age
- **DEM Samples**: Elevation, slope, aspect, TWI at clicked location

### Tile Status

The **System Status panel** shows coverage and max zoom for all PMTiles sources. Use it to verify tile availability for your current map extent.

## API Endpoints

See [docs/API.md](docs/API.md) for complete API documentation with schemas and examples.

**Quick reference:**

- `POST /api/delineate` - Watershed delineation with optional stream snapping
- `GET /api/delineate/status` - Check data file availability
- `POST /api/cross-section` - Generate elevation profiles
- `POST /api/feature-info` - Query stream/geology/spring attributes
- `GET /api/feature-info/status` - Dataset health check with metadata
- `GET /tiles/{filename}` - PMTiles serving with range request support

## Configuration

Edit `.env` to customize data paths, delineation settings, basemap API keys, and server options.

**Required for basemaps**: Get a free Stadia Maps API key at https://client.stadiamaps.com/signup/ and add to `.env`:
```bash
VITE_STADIA_API_KEY=your_api_key_here
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for complete configuration reference.

## Data Sources

### Recommended Data

- **DEM (US)**: [USGS 3DEP 10m](https://www.usgs.gov/3d-elevation-program)
- **DEM (Global)**: [Copernicus GLO-30](https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model)
- **Streams (US)**: [NHD/NHDPlus](https://www.usgs.gov/national-hydrography/national-hydrography-dataset)
- **Watersheds (US)**: [USGS WBD/HUC12](https://www.usgs.gov/national-hydrography/watershed-boundary-dataset)

### Processing Tools

- **WhiteboxTools**: DEM preprocessing, flow analysis
- **GDAL**: Raster/vector processing
- **Tippecanoe**: Vector tile generation
- **PMTiles**: Cloud-optimized tile archives

## Development

### Project Structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed component hierarchy.

```
frontend/src/lib/
├── components/          # UI components
│   ├── Map.svelte      # MapLibre + PMTiles Protocol
│   ├── LayerPanel.svelte
│   ├── WatershedTool.svelte
│   └── ...
├── config/layers.ts    # Centralized layer configuration (LAYER_SOURCES)
└── stores.ts           # Svelte stores for state management

backend/app/
├── main.py             # FastAPI application
├── routers/            # API endpoints
└── services/           # Business logic
```

### Adding New Layers

1. Add layer configuration to `frontend/src/lib/config/layers.ts` (LAYER_SOURCES)
2. Layers are automatically registered in the UI (Map.svelte reads from LAYER_SOURCES)
3. Generate tiles with `scripts/generate_tiles.py`

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow and code style guidelines.

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for comprehensive troubleshooting guide.

**Common issues:**

- **"Delineation failed"**: Ensure `data/processed/dem/` contains flow_direction.tif and flow_accumulation.tif
- **"Required data files not found"**: Check `/api/delineate/status` endpoint, re-run prepare_dem.py
- **No tiles appearing**: Verify tiles exist in `data/tiles/`, check browser console for errors, use Tile Status panel

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Detailed component hierarchy and data flow
- [Quick Start Guide](docs/QUICK_START.md) - Step-by-step installation and setup
- [Data Preparation](docs/DATA_PREPARATION.md) - Complete workflows for DEM, streams, HUC12
- [API Reference](docs/API.md) - Complete API documentation with schemas
- [UI Guide](docs/UI_GUIDE.md) - Frontend features and usage
- [Configuration](docs/CONFIGURATION.md) - Environment variables and settings
- [Deployment](docs/DEPLOYMENT.md) - Production deployment guide
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **WhiteboxTools**: Open-source geospatial analysis (Dr. John Lindsay)
- **MapLibre GL JS**: Open-source mapping library
- **PMTiles**: Protomaps single-file tile archive format
- **USGS**: DEM, stream, and geology data

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Contact

For questions or support, open an issue at https://github.com/HurleySk/hydro-map/issues
