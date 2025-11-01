# Data Preparation Guide

This guide walks you through preparing data for the Hydro-Map application.

## Overview

The application requires preprocessed hydrological data:
1. **DEM** → Filled DEM, flow direction, flow accumulation
2. **Terrain** → Hillshade, slope, aspect
3. **Streams** → Extracted stream network
4. **Tiles** → PMTiles for web serving

## Step-by-Step Instructions

### 1. Download DEM Data

#### Option A: US - USGS 3DEP (Recommended for US)

**Resolution**: 10m (excellent for local watersheds 10-100 sq mi)

1. Visit [USGS National Map Downloader](https://apps.nationalmap.gov/downloader/)
2. Click "Define Area" and draw your area of interest
3. Under "Data" tab, select "Elevation Products (3DEP)"
4. Choose "1/3 arc-second DEM" (10m)
5. Download and extract to `data/raw/dem/elevation.tif`

#### Option B: Global - Copernicus GLO-30

**Resolution**: 30m (good for global coverage)

1. Visit [OpenTopography](https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3)
2. Select your area of interest
3. Choose Copernicus GLO-30
4. Download and save to `data/raw/dem/elevation.tif`

**Pro tip**: Download an area slightly larger than your study area to avoid edge effects.

### 2. Process DEM

Run the DEM preprocessing script:

```bash
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/ \
  --breach
```

**What this does**:
- Removes sinks/depressions using breach algorithm (or `--fill` for filling)
- Computes D8 flow direction (8 flow directions)
- Computes flow accumulation
- Generates hillshade (for visualization)
- Computes slope (in degrees)
- Computes aspect (slope direction)

**Outputs** (in `data/processed/dem/`):
- `filled_dem.tif` - Depression-filled DEM
- `flow_direction.tif` - D8 flow pointers
- `flow_accumulation.tif` - Number of upstream cells
- `hillshade.tif` - Shaded relief
- `slope.tif` - Slope in degrees
- `aspect.tif` - Aspect in degrees

**Processing time**: ~2-5 minutes for 100 sq mi at 10m resolution

### 3. Extract Stream Network (Pure DEM Approach)

The application uses a **pure DEM-derived stream network** that works globally without requiring external datasets like NHD. This approach extracts streams at multiple thresholds, filters artifacts, and computes hydrologic attributes.

#### Step 3a: Multi-Threshold Stream Extraction

Extract streams at multiple flow accumulation thresholds (100, 250, 500, 1000 cells):

```bash
python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_multi.gpkg \
  --multi-threshold
```

**What this does**:
- Extracts streams at 4 thresholds to capture different stream scales
- Computes Strahler stream order for each threshold
- Calculates drainage area from flow accumulation
- Calculates stream segment length
- Creates separate layers: `streams_t100`, `streams_t250`, `streams_t500`, `streams_t1000`

**Typical thresholds** (for 10m DEM):
- **100 cells**: Finest detail, captures small headwater streams (~0.01 km² drainage area)
- **250 cells**: Good balance of detail vs. artifacts (~0.025 km² drainage area)
- **500 cells**: Medium detail, fewer artifacts (~0.05 km² drainage area)
- **1000 cells**: Major streams only (~0.1 km² drainage area)

**Output**: `data/processed/streams_multi.gpkg` with 4 layers

**Processing time**: ~3-10 minutes depending on DEM size

#### Step 3b: Filter DEM Artifacts

Remove spurious streams and compute confidence scores:

```bash
python scripts/filter_dem_streams.py \
  --input data/processed/streams_multi.gpkg \
  --layer streams_t250 \
  --output data/processed/streams_filtered.gpkg \
  --min-length 25 \
  --min-drainage-area 0.01 \
  --flow-acc data/processed/dem/flow_accumulation.tif
```

**Parameters**:
- `--layer`: Which threshold layer to filter (recommended: `streams_t250` or `streams_t500`)
- `--min-length`: Minimum stream segment length in meters (removes tiny fragments)
- `--min-drainage-area`: Minimum drainage area in km² (removes unlikely headwaters)
- `--flow-acc`: Flow accumulation raster for drainage area calculation

**What this does**:
- **Length filtering**: Removes segments shorter than threshold
- **Drainage area filtering**: Removes streams with implausibly small watersheds
- **Geometric filtering**: Detects and removes very straight segments (likely DEM artifacts)
- **Sinuosity calculation**: Measures stream meandering (real streams meander, artifacts are straight)
- **Flow persistence classification**: Labels as Perennial/Intermittent/Ephemeral based on drainage area
- **Confidence scoring**: Combines multiple metrics into a 0-1 confidence score

**Confidence score formula**:
- Normalized drainage area (0-1)
- Normalized length (0-1)
- Sinuosity bonus (meandering streams = more confident)
- Stream order bonus (higher order = more confident)

**Flow persistence thresholds**:
- **Perennial** (year-round flow): Drainage area ≥ 5.0 km²
- **Intermittent** (seasonal flow): Drainage area 0.5-5.0 km²
- **Ephemeral** (storm-driven): Drainage area < 0.5 km²

**Output**: `data/processed/streams_filtered.gpkg` with layer `streams_t<threshold>_filtered`

**Processing time**: ~1-2 minutes

#### Step 3c: Quality Assurance

Generate a QA report to assess stream network quality:

```bash
python scripts/qa_stream_network.py \
  --input data/processed/streams_filtered.gpkg \
  --layer streams_t250_filtered \
  --output reports/stream_qa_report.md
```

The report includes:
- Stream count and length by order
- Drainage area distribution
- Confidence score distribution
- Flow persistence classification
- Sinuosity metrics
- Recommendations for parameter tuning

**Interpreting results**:
- **High low-confidence rate (>20%)**: Consider increasing `--min-length` or `--min-drainage-area`, or using a coarser threshold
- **Many very straight streams (>50%)**: DEM quality issues or need stricter geometric filtering
- **All ephemeral streams**: Fine threshold capturing headwaters; use t500 or t1000 for perennial streams

For production use, copy the filtered streams to the expected location:

```bash
cp data/processed/streams_filtered.gpkg data/processed/streams.gpkg
```

### 4. Generate Contours (Optional)

Generate elevation contour lines from the DEM:

```bash
gdal_contour -a elevation -i 10 \
  data/processed/dem/filled_dem.tif \
  data/processed/contours.gpkg
```

**Parameters**:
- `-a elevation`: Attribute name for elevation values
- `-i 10`: Contour interval in meters (adjust based on terrain)

**Common intervals**:
- Flat terrain: 5-10m
- Moderate terrain: 10-20m
- Mountainous: 20-50m

**Output**: `data/processed/contours.gpkg` - Contour lines with elevation attribute

**Processing time**: ~30 seconds - 2 minutes

### 5. Generate Web Tiles

Convert rasters and vectors to PMTiles for web serving:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --min-zoom 8 \
  --max-zoom 17 \
  --contour-interval 2
```

`--raster-resampling` lets you select the gdal2tiles kernel (`lanczos` is the new default for crisp hillshade; use `nearest` for categorical rasters like aspect). Vector tiles are exported with `tippecanoe --no-feature-reduction` to preserve geometry all the way to z17.

**Zoom levels** (defaults: min 8, max 17):
- `8-10`: Regional view (county scale)
- `11-12`: Local view (watershed scale)
- `13-15`: Detailed view (stream segments)
- `16-17`: High-resolution terrain (≈1–2 m/px near 39° latitude)

Increase `--max-zoom` only if your DEM resolution supports sub-meter detail; the app will overzoom gracefully, but native tiles give crisper visuals. `--contour-interval` defaults to `1` meter—raise it (e.g., `--contour-interval 2` or `--contour-interval 10`) for broader terrain steps or lower-detail products.

**Outputs** (in `data/tiles/`):
- `hillshade.pmtiles`
- `slope.pmtiles`
- `aspect.pmtiles`
- `streams.pmtiles`
- `contours.pmtiles` (if contours were generated)

**Note**: This script requires external tools:
- **GDAL** (`gdal_translate`, `gdal2tiles.py` with `--xyz`, `gdal_contour`)
- **Tippecanoe** (for vector tiles)
- **mb-util** (Python package for MBTiles manipulation)
- **PMTiles CLI** (for final conversion to PMTiles format)

**IMPORTANT**: The tile generation workflow is:
1. Rasters: DEM → XYZ tiles (gdal2tiles) → MBTiles (mb-util) → PMTiles (pmtiles convert)
2. Vectors: GeoPackage → GeoJSON (ogr2ogr) → MBTiles (tippecanoe) → PMTiles (pmtiles convert)

See [Installing Tools](#installing-required-tools) below.

### 5. (Optional) Add Geology Data

#### Download Geology

**US State Geology**:
1. Visit [USGS State Geologic Maps](https://mrdata.usgs.gov/geology/state/)
2. Select your state
3. Download shapefile or geodatabase

**Other sources**:
- [OneGeology](https://onegeology.org/)
- [USGS National Geologic Map Database](https://ngmdb.usgs.gov/)

#### Prepare Geology

```bash
# Convert to GeoPackage
ogr2ogr -f GPKG \
  data/processed/geology.gpkg \
  data/raw/geology/state_geology.shp

# Simplify geometry for web (optional)
ogr2ogr -f GPKG \
  -simplify 10 \
  data/processed/geology_simplified.gpkg \
  data/processed/geology.gpkg
```

#### Add Color Attributes

Edit the geology GeoPackage to add a `color` field based on rock type or age. This will be used for map styling.

Example using Python:

```python
import geopandas as gpd

gdf = gpd.read_file('data/processed/geology.gpkg')

# Simple color mapping
color_map = {
    'sandstone': '#E6C896',
    'shale': '#96826E',
    'limestone': '#A0B4C8',
    'granite': '#E69696',
    'basalt': '#646464',
}

gdf['color'] = gdf['ROCKTYPE1'].map(color_map).fillna('#CCCCCC')
gdf.to_file('data/processed/geology.gpkg', driver='GPKG')
```

## Installing Required Tools

### WhiteboxTools (Python package)

Already included in `backend/requirements.txt`:

```bash
pip install whitebox
```

### mb-util (Python package)

Required for XYZ to MBTiles conversion. Install in backend venv:

```bash
cd backend
source venv/bin/activate
pip install mbutil
```

**Note**: mb-util is NOT available via Homebrew. Must be installed as a Python package.

### GDAL

#### macOS (Homebrew)
```bash
brew install gdal
```

#### Ubuntu/Debian
```bash
sudo apt-get install gdal-bin libgdal-dev
```

#### Windows
Download from [GIS Internals](https://www.gisinternals.com/)

### Tippecanoe

#### macOS
```bash
brew install tippecanoe
```

#### Ubuntu/Debian
```bash
sudo apt-get install tippecanoe
```

#### From source
```bash
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe
make -j
sudo make install
```

### PMTiles CLI

#### Download binary
Visit [PMTiles Releases](https://github.com/protomaps/go-pmtiles/releases)

#### macOS/Linux
```bash
# Download appropriate version
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.11.0/pmtiles_1.11.0_Linux_x86_64.tar.gz
tar xzf pmtiles_*.tar.gz
sudo mv pmtiles /usr/local/bin/
```

## Validation

Check that all required files exist:

```bash
ls -lh data/processed/dem/
# Should see: filled_dem.tif, flow_direction.tif, flow_accumulation.tif, etc.

ls -lh data/processed/
# Should see: streams.gpkg

ls -lh data/tiles/
# Should see: *.pmtiles files
```

Start the backend and check status:

```bash
cd backend
uvicorn app.main:app --reload

# In another terminal:
curl http://localhost:8000/api/delineate/status
```

Should return:
```json
{
  "ready": true,
  "files": {
    "dem": {"path": "...", "exists": true},
    "flow_direction": {"path": "...", "exists": true},
    "flow_accumulation": {"path": "...", "exists": true}
  }
}
```

## Troubleshooting

### "No module named 'whitebox'"
```bash
pip install whitebox
```

### "gdal_translate: command not found"
Install GDAL (see above)

### "tippecanoe: command not found"
Install Tippecanoe (see above)

### Large file sizes
- Reduce DEM extent
- Lower max zoom level in tile generation
- Use GDAL compression: `gdal_translate -co COMPRESS=LZW`

### Processing very slow
- Reduce DEM resolution with `gdalwarp -tr 30 30`
- Use breaching instead of filling (`--breach`)
- Process smaller area

## Example: Complete Workflow

```bash
# 1. Download DEM to data/raw/dem/elevation.tif

# 2. Process DEM
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# 3a. Extract streams at multiple thresholds
python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_multi.gpkg \
  --multi-threshold

# 3b. Filter streams (remove artifacts)
python scripts/filter_dem_streams.py \
  --input data/processed/streams_multi.gpkg \
  --layer streams_t250 \
  --output data/processed/streams_filtered.gpkg \
  --min-length 25 \
  --min-drainage-area 0.01 \
  --flow-acc data/processed/dem/flow_accumulation.tif

# 3c. Copy filtered streams to expected location
cp data/processed/streams_filtered.gpkg data/processed/streams.gpkg

# 3d. Generate QA report (optional)
python scripts/qa_stream_network.py \
  --input data/processed/streams_filtered.gpkg \
  --layer streams_t250_filtered \
  --output reports/stream_qa_report.md

# 4. Generate tiles
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 2

# 5. Start application
cd backend && uvicorn app.main:app --reload &
cd frontend && npm run dev

# 6. Open http://localhost:5173
```

## Data Credits

When using this application, please credit data sources:
- **USGS 3DEP**: "Elevation data from USGS 3D Elevation Program"
- **Copernicus**: "Copernicus DEM ©2021 European Space Agency"
- **USGS Geology**: "Geologic data from USGS"
- **Stream Network**: "Stream network derived from DEM using WhiteboxTools"
