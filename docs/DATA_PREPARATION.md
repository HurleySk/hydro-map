# Data Preparation Guide

**Version**: 1.7.0

This guide walks you through preparing data for the Hydro-Map application, including DEM processing, stream extraction (both DEM-derived and NHD-based), HUC12 watershed boundaries, and tile generation.

## Table of Contents

- [Overview](#overview)
- [Step 1: Download DEM Data](#step-1-download-dem-data)
- [Step 2: Process DEM](#step-2-process-dem)
- [Step 3: Download Fairfax Hydrography](#step-3-download-fairfax-hydrography)
- [Step 4: Process Fairfax Hydrography](#step-4-process-fairfax-hydrography)
- [Optional: Legacy Stream Workflows](#optional-legacy-stream-workflows)
- [Step 5: Process HUC12 Watersheds (Optional)](#step-5-process-huc12-watersheds-optional)
- [Step 6: Generate Contours (Optional)](#step-6-generate-contours-optional)
- [Step 7: Generate Web Tiles](#step-7-generate-web-tiles)
- [Step 8: Add Geology Data (Optional)](#step-8-add-geology-data-optional)
- [Installing Required Tools](#installing-required-tools)
- [Validation](#validation)
- [Troubleshooting](#troubleshooting)
- [Complete Workflow Examples](#complete-workflow-examples)

## Overview

The application requires preprocessed hydrological data in three main categories:

### Core Data (Required)
1. **DEM Processing** → Filled DEM, flow direction, flow accumulation, terrain products
2. **Hydrography** → Fairfax water features + perennial streams (default) or a custom stream network
3. **Web Tiles** → PMTiles for all raster and vector layers

### Optional Enhancements
4. **HUC12 Boundaries** → USGS watershed reference layer
5. **Contours** → Elevation contour lines
6. **Geology** → Geologic formations and rock types

### Fairfax Hydrography (Default)

Hydro-Map now ships with Fairfax County open-data hydrography:

- **Fairfax Water Features (Lines)** (`fairfax_water_lines.pmtiles`): streams, channels, ditches, and canals
- **Fairfax Water Features (Polygons)** (`fairfax_water_polys.pmtiles`): ponds, lakes, reservoirs, and flooded areas
- **Fairfax Perennial Streams** (`perennial_streams.pmtiles`): simplified perennial-only network

These layers are produced by `download_fairfax_hydro.py` and `prepare_fairfax_hydro.py` (Steps 3 and 4).

### Legacy Stream Workflows

If you need the previous DEM-derived or NHD-based stream pipelines, keep following this guide but refer to [Hydrology Data](data/STREAMS.md) for the detailed extraction steps. Those pipelines remain supported but are no longer part of the default build.

## Step 1: Download DEM Data

### Option A: US - USGS 3DEP (Recommended for US)

**Resolution**: 10m (excellent for local watersheds 10-100 sq mi)

1. Visit [USGS National Map Downloader](https://apps.nationalmap.gov/downloader/)
2. Click "Define Area" and draw your area of interest
3. Under "Data" tab, select "Elevation Products (3DEP)"
4. Choose "1/3 arc-second DEM" (10m)
5. Download and extract to `data/raw/dem/elevation.tif`

**Coverage**: Continental US, Alaska, Hawaii, Puerto Rico, US territories

### Option B: Global - Copernicus GLO-30

**Resolution**: 30m (good for global coverage)

1. Visit [OpenTopography](https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3)
2. Select your area of interest
3. Choose "Copernicus GLO-30"
4. Download and save to `data/raw/dem/elevation.tif`

**Coverage**: Global (60°N to 56°S)

### Option C: Global - SRTM

**Resolution**: 30m (1 arc-second)

1. Visit [USGS Earth Explorer](https://earthexplorer.usgs.gov/)
2. Search for your area
3. Select "Digital Elevation" → "SRTM 1 Arc-Second Global"
4. Download and mosaic tiles if needed

**Coverage**: Global (60°N to 56°S)

### Pro Tips

**Buffer your area**: Download an area 1-2 km larger than your study region to avoid edge effects in watershed delineation.

**Check resolution**: Match DEM resolution to your analysis scale:
- 10m: Local watersheds (1-100 sq mi)
- 30m: Regional watersheds (100-1000 sq mi)
- 90m: Large basins (> 1000 sq mi)

**Mosaic tiles**: If your area spans multiple DEM tiles:
```bash
gdalbuildvrt mosaic.vrt tile1.tif tile2.tif tile3.tif
gdal_translate mosaic.vrt data/raw/dem/elevation.tif
```

**Clip to AOI**: Reduce file size by clipping to area of interest:
```bash
gdalwarp -cutline boundary.geojson -crop_to_cutline \
  -co COMPRESS=LZW \
  input.tif data/raw/dem/elevation.tif
```

## Step 2: Process DEM

Run the DEM preprocessing script to generate flow grids and terrain products:

```bash
cd backend
source venv/bin/activate

python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/ \
  --breach
```

### What This Does

1. **Remove depressions**: Fills sinks or carves channels (breach algorithm)
2. **Compute flow direction**: D8 flow pointers (8-direction)
3. **Compute flow accumulation**: Counts upstream contributing cells
4. **Generate terrain products**: Hillshade, slope, aspect for visualization

### Options

- `--breach`: Carve channels through barriers (default, recommended)
- `--fill`: Fill sinks completely (alternative approach)
- `--workers N`: Number of parallel workers (default: CPU count)

### Outputs

All files saved to `data/processed/dem/`:

| File | Description | Use |
|------|-------------|-----|
| `filled_dem.tif` | Depression-filled DEM | Delineation, elevation stats |
| `flow_direction.tif` | D8 flow pointers (1-128) | Watershed tracing |
| `flow_accumulation.tif` | Upstream cell count | Stream extraction, snapping |
| `hillshade.tif` | Shaded relief visualization | Web map layer |
| `slope.tif` | Slope angle in degrees | Terrain analysis |
| `aspect.tif` | Compass direction (0-360°) | Terrain analysis |

### Processing Time

- 100 sq mi @ 10m: ~2-5 minutes
- 500 sq mi @ 30m: ~5-10 minutes
- 1000 sq mi @ 30m: ~10-20 minutes

### WhiteboxTools Operations

The script uses WhiteboxTools for all hydrological processing:

1. `BreachDepressionsLeastCost` or `FillDepressionsWangAndLiu`
2. `D8Pointer` for flow direction
3. `D8FlowAccumulation` for accumulation
4. `Hillshade`, `Slope`, `Aspect` for terrain

## Step 3: Download Fairfax Hydrography

Fairfax County publishes high-quality hydrography datasets (lines, polygons, and perennial streams) via ArcGIS REST services. Use the helper script to download, clip, and reproject them into WGS84.

```bash
python scripts/download_fairfax_hydro.py
```

**Creates**:
- `data/raw/fairfax/water_features_lines.gpkg`
- `data/raw/fairfax/water_features_polys.gpkg`
- `data/raw/fairfax/perennial_streams.gpkg`

**Script behavior**:
- Clips data to the AOI bounding box defined in the script (default: Fairfax County, VA)
- Reprojects source CRS to EPSG:4326
- Overwrites existing files so you can rerun the command safely

**Customization**:
- Update `AOI_BBOX` for a different project extent
- Swap dataset URLs in `DATASETS` to target different ArcGIS layers

## Step 4: Process Fairfax Hydrography

Normalize fields, calculate metrics, and write processed GeoPackages consumed by the backend and frontend.

```bash
python scripts/prepare_fairfax_hydro.py
```

**Creates**:
- `data/processed/fairfax_water_lines.gpkg`
- `data/processed/fairfax_water_polys.gpkg`
- `data/processed/perennial_streams.gpkg`

**What the script does**:
1. Reads raw Fairfax data from `data/raw/fairfax/`
2. Reprojects to EPSG:4326 if necessary
3. Renames fields (e.g., `NAME` → `name`, `TYPE` → `type`)
4. Adds `data_source` attribution (`"Fairfax County GIS"`)
5. Computes geometry metrics
   - Lines: length in kilometers (`length_km`)
   - Polygons: area in square kilometres (`area_sqkm`)
6. Writes cleaned layers with standardized schemas (layer names match frontend `vectorLayerId` values)

**Verification**:
- `ogrinfo data/processed/fairfax_water_lines.gpkg -al -so`
- Ensure geometry types (LineString/Polygon) and CRS (EPSG:4326) are correct

## Optional: Legacy Stream Workflows

The previous DEM/NHD stream extraction pipeline is still supported but no longer part of the default workflow. Refer to [docs/data/STREAMS.md](data/STREAMS.md) for detailed instructions if you need to:
- Generate DEM-derived drainage networks for regions outside Fairfax County
- Integrate NHD flowlines or other national datasets
- Produce merged DEM/NHD comparison layers

## Optional: Process NHD Streams

For US watersheds, you can still process official USGS National Hydrography Dataset streams and merge them with DEM-derived or Fairfax datasets if needed.

### Download NHD Data

**Option 1: National Map Downloader**
1. Visit [USGS National Map](https://apps.nationalmap.gov/downloader/)
2. Draw your area of interest
3. Select "Hydrography" → "National Hydrography Dataset (NHD)"
4. Download NHD High Resolution or Medium Resolution
5. Extract to `data/raw/nhd/`

**Option 2: NHD Plus**
1. Visit [EPA NHDPlus](https://www.epa.gov/waterdata/nhdplus-national-hydrography-dataset-plus)
2. Download regional dataset
3. Extract flowlines to `data/raw/nhd/`

**What you need**: NHDFlowline shapefile or geodatabase layer

### Process NHD Streams

```bash
python scripts/process_nhd.py \
  --input data/raw/nhd/NHDFlowline.shp \
  --output data/processed/streams_nhd.gpkg \
  --bounds data/processed/dem/filled_dem.tif \
  --min-order 1
```

### Script Parameters

- `--input`: Path to NHD flowline shapefile or geodatabase
- `--output`: Output GeoPackage path
- `--bounds`: DEM to use for clipping (optional but recommended)
- `--min-order`: Minimum Strahler order to include (default: 1)
- `--include-artificial`: Include artificial paths (canals, aqueducts)
- `--include-intermittent`: Include intermittent streams

### What The Script Does

1. **Read NHD flowlines**: Loads shapefile/geodatabase
2. **Clip to bounds**: Clips to DEM extent (if --bounds specified)
3. **Filter by flow type**: Removes artificial paths unless --include-artificial
4. **Standardize attributes**: Creates consistent attribute schema
5. **Calculate lengths**: Computes segment length in meters
6. **Reproject**: Ensures CRS matches DEM (typically EPSG:4326 or UTM)
7. **Export**: Saves to GeoPackage with spatial index

### Output Attributes

**File**: `data/processed/streams_nhd.gpkg`

Standard attributes:
- `name`: Stream name (GNIS name if available)
- `gnis_id`: Geographic Names Information System ID
- `strahler_order`: Stream order (from NHD or computed)
- `length_m`: Segment length in meters
- `fcode`: Feature code (flow type)
- `flow_type`: Perennial/Intermittent/Ephemeral
- `reachcode`: NHD reach identifier

### Merge NHD with DEM Streams (Optional)

Compare or merge both stream networks:

```bash
python scripts/merge_streams.py \
  --nhd data/processed/streams_nhd.gpkg \
  --dem data/processed/streams_dem.gpkg \
  --output data/processed/streams_merged.gpkg \
  --buffer 10
```

This creates a merged network showing:
- Streams present in both (high confidence)
- NHD-only streams (official but may be dry in DEM)
- DEM-only streams (potential ephemeral channels)

Useful for validation and completeness assessment.

## Step 5: Process HUC12 Watersheds (Optional)

Add USGS Hydrologic Unit Code (HUC12) watershed boundaries as a reference layer.

### Download WBD Data

**Option 1: National Map Downloader**
1. Visit [USGS National Map](https://apps.nationalmap.gov/downloader/)
2. Draw your area of interest
3. Select "Watershed Boundary Dataset (WBD)"
4. Download HUC12 level
5. Extract to `data/raw/wbd/`

**Option 2: Direct Download**
1. Visit [USGS WBD](https://www.usgs.gov/national-hydrography/access-national-hydrography-products)
2. Download state or regional WBD geodatabase
3. Extract HUC12 layer to `data/raw/wbd/`

**What you need**: WBDHU12 shapefile or geodatabase layer

### Process HUC12 Boundaries

```bash
python scripts/process_huc.py \
  --input data/raw/wbd/WBDHU12.shp \
  --output data/processed/huc12.gpkg \
  --bounds data/processed/dem/filled_dem.tif \
  --simplify 5
```

### Script Parameters

- `--input`: Path to HUC12 shapefile or geodatabase
- `--output`: Output GeoPackage path
- `--bounds`: DEM to use for clipping (clips to DEM extent + buffer)
- `--simplify`: Simplification tolerance in meters (default: 5, use 0 to disable)

### What The Script Does

1. **Read HUC12 polygons**: Loads shapefile/geodatabase
2. **Clip to bounds**: Clips to DEM extent with 5km buffer
3. **Simplify geometry**: Reduces vertex count for web display (optional)
4. **Calculate area**: Computes watershed area in km²
5. **Standardize attributes**: Creates consistent schema
6. **Export**: Saves to GeoPackage with spatial index

### Output Attributes

**File**: `data/processed/huc12.gpkg`

Attributes:
- `huc12`: 12-digit HUC code (e.g., "180201050204")
- `name`: Watershed name
- `area_sqkm`: Watershed area in km²
- `area_sqmi`: Watershed area in square miles
- `states`: State(s) the watershed covers

### HUC Hierarchy

HUC12 is the finest level in the WBD hierarchy:

- **HUC2**: Region (e.g., "18" = Lower Colorado)
- **HUC4**: Subregion
- **HUC6**: Basin
- **HUC8**: Subbasin
- **HUC10**: Watershed
- **HUC12**: Subwatershed (10-40 sq mi typical)

HUC12 boundaries are useful for:
- Reference layer showing official watershed delineations
- Comparison with on-demand delineations
- Labeling watersheds by name/code
- Regional watershed selection

## Step 6: Generate Contours (Optional)

Generate elevation contour lines from the filled DEM:

```bash
gdal_contour -a elevation -i 10 \
  data/processed/dem/filled_dem.tif \
  data/processed/contours.gpkg
```

### Parameters

- `-a elevation`: Attribute name for elevation values
- `-i 10`: Contour interval in meters (vertical spacing)
- `-b 1`: Band to process (default: 1)
- `-f GPKG`: Output format (GeoPackage)

### Interval Selection

Choose contour interval based on terrain and map scale:

| Terrain Type | Interval | Use Case |
|--------------|----------|----------|
| Flat coastal | 1-5m | High detail, coastal areas |
| Rolling hills | 5-10m | Suburban, agricultural |
| Moderate mountains | 10-20m | **Recommended general use** |
| Steep mountains | 20-50m | Regional scale, steep slopes |
| High mountains | 50-100m | Very large extent, overview |

**Rule of thumb**: Interval should be ~0.5% of elevation range
- Range 1000m → 5-10m interval
- Range 2000m → 10-20m interval

### Index Contours

Generate bold index contours (every 5th contour):

```bash
# Generate major contours at 50m interval
gdal_contour -a elevation -i 50 \
  data/processed/dem/filled_dem.tif \
  data/processed/contours_major.gpkg
```

Style differently in the map (bolder line, labels).

### Output

**File**: `data/processed/contours.gpkg`

**Attributes**:
- `elevation`: Elevation value in meters (or feet if DEM is in feet)
- `id`: Sequential contour ID

**Processing time**: ~30 seconds - 2 minutes depending on DEM size and interval

## Step 7: Generate Web Tiles

Convert all rasters and vectors to PMTiles for web serving:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --min-zoom 8 \
  --max-zoom 17 \
  --contour-interval 10 \
  --raster-resampling lanczos
```

### Parameters

- `--data-dir`: Directory containing processed data (default: `data/processed`)
- `--output-dir`: Directory to save PMTiles (default: `data/tiles`)
- `--min-zoom`: Minimum zoom level (default: 8)
- `--max-zoom`: Maximum zoom level (default: 17)
- `--contour-interval`: Contour interval in meters (default: 10, generates if not existing)
- `--raster-resampling`: Resampling method: `lanczos`, `bilinear`, `nearest` (default: `lanczos`)

### What The Script Does

The script automatically processes all available datasets:

**Raster Tiles**:
1. Finds: `hillshade.tif`, `slope.tif`, `aspect.tif` in data-dir/dem/
2. For each raster:
   - Converts to 8-bit with `gdal_translate`
   - Generates XYZ tiles with `gdal2tiles.py --xyz` (CRITICAL: must use --xyz)
   - Converts XYZ to MBTiles with `mb-util`
   - Inserts metadata (format=png, type=overlay) using sqlite3
   - Converts MBTiles to PMTiles with `pmtiles convert`
3. **Aspect override**: Automatically uses `nearest` resampling for aspect (categorical)

**Vector Tiles**:
1. Finds: `streams_dem.gpkg`, `streams_nhd.gpkg`, `huc12.gpkg`, `contours.gpkg`
2. For each vector:
   - Converts to GeoJSON with `ogr2ogr`
   - Generates MBTiles with `tippecanoe` (no feature reduction, full detail to z17)
   - Converts MBTiles to PMTiles

**Contour Generation**:
- If `contours.gpkg` doesn't exist, generates it automatically with `gdal_contour`

### Zoom Level Guide

| Zoom | Resolution @ 38°N | Use Case |
|------|-------------------|----------|
| 8 | ~305 m/px | Regional view, county scale |
| 10 | ~76 m/px | Watershed overview |
| 12 | ~19 m/px | Stream network detail |
| 14 | ~4.8 m/px | Hillshade becomes useful |
| 16 | ~1.2 m/px | High detail, terrain features |
| 17 | ~0.6 m/px | **Maximum recommended** for 10m DEM |
| 18 | ~0.3 m/px | Only if DEM is 3m or better |

**Recommendation**: Use z17 for 10m DEM, z16 for 30m DEM

### Resampling Methods

- **lanczos**: Sharp, high-quality, good for continuous rasters (hillshade, slope)
- **bilinear**: Smooth, good for hillshade if lanczos creates artifacts
- **nearest**: Preserves exact values, required for categorical (aspect, landcover)

The script automatically overrides to `nearest` for aspect layer.

### TMS vs XYZ Addressing

**CRITICAL**: The script uses `--xyz` flag with gdal2tiles, which creates XYZ tiles (standard web mercator, Y=0 at top).

Without `--xyz`, gdal2tiles creates TMS tiles (Y=0 at bottom), which **will not render** in MapLibre GL JS.

### Metadata Fixing

After mb-util conversion, the script inserts required metadata for raster tiles:

```sql
INSERT OR REPLACE INTO metadata (name, value) VALUES ('format', 'png');
INSERT OR REPLACE INTO metadata (name, value) VALUES ('type', 'overlay');
```

Without this, raster PMTiles have empty tile type and won't render.

### Expected Outputs

In `data/tiles/`:

| File | Type | Size (approx) | Zoom |
|------|------|---------------|------|
| `hillshade.pmtiles` | Raster | 15-30 MB | 8-17 |
| `slope.pmtiles` | Raster | 10-20 MB | 8-17 |
| `aspect.pmtiles` | Raster | 10-20 MB | 8-17 |
| `contours.pmtiles` | Vector | 5-15 MB | 8-17 |
| `fairfax_water_lines.pmtiles` | Vector | 2-4 MB | 8-17 |
| `fairfax_water_polys.pmtiles` | Vector | 2-4 MB | 8-17 |
| `perennial_streams.pmtiles` | Vector | 2-3 MB | 8-17 |
| `huc12.pmtiles` | Vector | 1-5 MB | 8-14 |

Sizes vary based on area extent, terrain complexity, and zoom range.

### Processing Time

- Raster tiles (z8-z17): ~5-15 minutes per layer
- Vector tiles: ~1-3 minutes per layer
- Total for all layers: ~20-50 minutes

Reduce `--max-zoom` to speed up significantly:
- z14: ~4x faster than z17
- z16: ~2x faster than z17

### Verification

Check tile metadata:

```bash
# Verify raster tile type
pmtiles show data/tiles/hillshade.pmtiles
# Should show: tile type: png, tile compression: png, max zoom: 17

# Verify vector layer names
pmtiles show data/tiles/fairfax_water_lines.pmtiles
# Should show: tile type: mvt, layer name: fairfax_water_lines

pmtiles show data/tiles/fairfax_water_polys.pmtiles
# Should show: layer name: fairfax_water_polys

pmtiles show data/tiles/perennial_streams.pmtiles
# Should show: layer name: perennial_streams

pmtiles show data/tiles/huc12.pmtiles
# Should show: layer name: huc12
```

### Vector Layer ID Consistency

**IMPORTANT**: The vector layer name inside PMTiles must match the `vectorLayerId` configured in `frontend/src/lib/config/layers.ts`.

For example:
- `fairfax_water_lines.pmtiles` has internal layer name `fairfax_water_lines`
- `fairfax_water_polys.pmtiles` has internal layer name `fairfax_water_polys`
- Config must specify matching `vectorLayerId` values in `layers.ts`

## Step 8: Add Geology Data (Optional)

**Note**: The geology layer is fully supported in the UI as of v1.7.0. Providing geology data enables map overlays, Feature Info results, and cross-section geology contact counts.

### Download Geology

**US State Geology**:
1. Visit [USGS State Geologic Maps](https://mrdata.usgs.gov/geology/state/)
2. Select your state
3. Download shapefile or geodatabase

**Other sources**:
- [OneGeology](https://onegeology.org/) - International
- [USGS National Geologic Map Database](https://ngmdb.usgs.gov/) - US

### Prepare Geology

```bash
# Convert to GeoPackage
ogr2ogr -f GPKG \
  -t_srs EPSG:4326 \
  data/processed/geology.gpkg \
  data/raw/geology/state_geology.shp

# Simplify geometry for web (optional, recommended)
ogr2ogr -f GPKG \
  -simplify 10 \
  data/processed/geology_simplified.gpkg \
  data/processed/geology.gpkg
```

### Add Color Attributes

Edit the geology GeoPackage to add color fields based on rock type or age for map styling:

```python
import geopandas as gpd

gdf = gpd.read_file('data/processed/geology.gpkg')

# Simple color mapping by rock type
color_map = {
    'sandstone': '#E6C896',
    'shale': '#96826E',
    'limestone': '#A0B4C8',
    'granite': '#E69696',
    'basalt': '#646464',
    'gneiss': '#C8B4A0',
    'schist': '#A0A096',
}

gdf['color'] = gdf['ROCKTYPE1'].map(color_map).fillna('#CCCCCC')
gdf.to_file('data/processed/geology.gpkg', driver='GPKG')
```

### Generate Geology Tiles

```bash
# Add geology to tile generation
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 14  # Geology doesn't need z17
```

Produces `geology.pmtiles` if `geology.gpkg` exists.

## Installing Required Tools

### Python Packages

Install in backend virtual environment:

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**requirements.txt includes**:
- `whitebox`: WhiteboxTools for hydrological processing
- `rasterio`: Raster I/O
- `geopandas`: Vector data operations
- `mbutil`: MBTiles manipulation (NOT available via Homebrew, must use pip)

### GDAL

Required for raster processing and tile generation.

**macOS (Homebrew)**:
```bash
brew install gdal
```

**Ubuntu/Debian**:
```bash
sudo apt-get install gdal-bin libgdal-dev python3-gdal
```

**Windows**:
Download from [GIS Internals](https://www.gisinternals.com/) or [OSGeo4W](https://trac.osgeo.org/osgeo4w/)

**Verify installation**:
```bash
gdal-config --version
gdalinfo --version
gdal_translate --version
gdal2tiles.py --version
```

### Tippecanoe

Required for vector tile generation.

**macOS (Homebrew)**:
```bash
brew install tippecanoe
```

**Ubuntu/Debian**:
```bash
sudo apt-get install tippecanoe
```

**From source** (if not in package manager):
```bash
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe
make -j
sudo make install
```

**Verify installation**:
```bash
tippecanoe --version
```

### PMTiles CLI

Required for MBTiles → PMTiles conversion.

**Download binary**:
1. Visit [PMTiles Releases](https://github.com/protomaps/go-pmtiles/releases)
2. Download for your platform (Linux, macOS, Windows)

**macOS/Linux**:
```bash
# Example for Linux x86_64
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.11.0/pmtiles_1.11.0_Linux_x86_64.tar.gz
tar xzf pmtiles_*.tar.gz
sudo mv pmtiles /usr/local/bin/
chmod +x /usr/local/bin/pmtiles
```

**Via cargo** (Rust package manager):
```bash
cargo install pmtiles
```

**Verify installation**:
```bash
pmtiles --version
```

### mb-util

**IMPORTANT**: mb-util must be installed via pip in the backend venv, NOT via Homebrew.

```bash
cd backend
source venv/bin/activate
pip install mbutil
```

**Verify installation**:
```bash
mb-util --help
```

## Validation

### Check Data Files

```bash
# Check DEM processing outputs
ls -lh data/processed/dem/
# Should see: filled_dem.tif, flow_direction.tif, flow_accumulation.tif,
#             hillshade.tif, slope.tif, aspect.tif

# Check Fairfax hydro outputs
ls -lh data/processed/fairfax*.gpkg data/processed/perennial_streams.gpkg
# Should see: fairfax_water_lines.gpkg, fairfax_water_polys.gpkg, perennial_streams.gpkg (plus huc12.gpkg if processed)

# Check PMTiles
ls -lh data/tiles/*.pmtiles
# Should see: hillshade.pmtiles, slope.pmtiles, aspect.pmtiles,
#             contours.pmtiles, fairfax_water_lines.pmtiles,
#             fairfax_water_polys.pmtiles, perennial_streams.pmtiles
# Optionally: huc12.pmtiles
```

### Check File Sizes

Typical sizes for 100 sq mi @ 10m DEM, z8-17:

```
filled_dem.tif: 50-200 MB
flow_direction.tif: 50-200 MB
flow_accumulation.tif: 100-400 MB
hillshade.tif: 50-150 MB

hillshade.pmtiles: 15-30 MB
slope.pmtiles: 10-20 MB
aspect.pmtiles: 10-20 MB
contours.pmtiles: 5-15 MB
fairfax_water_lines.pmtiles: 2-4 MB
fairfax_water_polys.pmtiles: 2-4 MB
perennial_streams.pmtiles: 2-3 MB
huc12.pmtiles: 1-5 MB
```

Much larger or smaller suggests issues.

### Verify PMTiles

```bash
# Check raster metadata
pmtiles show data/tiles/hillshade.pmtiles
# Must show: tile type: png, format: png, max zoom: 17

# Check vector layer names
pmtiles show data/tiles/fairfax_water_lines.pmtiles | grep "layer"
# Must show correct layer name (e.g., fairfax_water_lines, fairfax_water_polys)

# Verify bounds
pmtiles show data/tiles/hillshade.pmtiles | grep "bounds"
# Should match your DEM extent
```

### Check Backend API

Start the backend and verify data availability:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# In another terminal:
curl http://localhost:8000/api/delineate/status
```

**Expected response**:
```json
{
  "available": true,
  "missing_files": [],
  "flow_direction": "../data/processed/dem/flow_direction.tif",
  "flow_accumulation": "../data/processed/dem/flow_accumulation.tif",
  "dem": "../data/processed/dem/filled_dem.tif"
}
```

If `available: false`, check the `missing_files` array.

### Test Delineation

```bash
curl -X POST http://localhost:8000/api/delineate \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "snap_to_stream": true, "snap_radius": 100}'
```

Should return watershed GeoJSON with statistics.

### Verify Tiles in Browser

1. Start frontend: `cd frontend && npm run dev`
2. Open http://localhost:5173
3. Open Browser DevTools (F12) → Network tab
4. Toggle each layer (hillshade, slope, etc.)
5. Verify `/tiles/*.pmtiles` requests return 200 OK with `Accept-Ranges: bytes`
6. Check Tile Status panel shows all layers as "Available"

## Troubleshooting

### "No module named 'whitebox'"
```bash
cd backend
source venv/bin/activate
pip install whitebox
```

### "gdal_translate: command not found"
Install GDAL (see [Installing Required Tools](#installing-required-tools))

```bash
# macOS
brew install gdal

# Ubuntu
sudo apt-get install gdal-bin
```

### "tippecanoe: command not found"
Install Tippecanoe:

```bash
# macOS
brew install tippecanoe

# Linux - build from source
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe && make -j && sudo make install
```

### "pmtiles: command not found"
Download PMTiles binary from GitHub releases or install via cargo.

### "mb-util: command not found"
Install mb-util via pip (NOT Homebrew):

```bash
cd backend
source venv/bin/activate
pip install mbutil
```

### PMTiles are empty or very small (< 1MB)
- Check source data exists and is not empty
- Verify zoom range covers data extent
- Check `pmtiles show <file>` for tile count (should be > 100)

### Raster tiles don't render
**Most common issue**: Missing metadata or TMS tiles instead of XYZ

```bash
# Check metadata
pmtiles show data/tiles/hillshade.pmtiles

# Should show:
# tile type: png
# tile compression: png or unknown

# If tile type is empty, regenerate with metadata fix
```

**Solution**: Re-run generate_tiles.py, which automatically:
1. Uses `--xyz` flag with gdal2tiles
2. Inserts metadata with sqlite3

### Vector tiles don't appear
**Layer name mismatch**:

```bash
# Check layer name in PMTiles
pmtiles show data/tiles/streams_dem.pmtiles | grep layer

# Compare with frontend/src/lib/config/layers.ts vectorLayerId
```

Layer name in PMTiles must match `vectorLayerId` in config.

### Tiles only cover part of area
- DEM was clipped too tightly → add buffer when downloading
- Tiles weren't generated for full DEM extent → regenerate
- Map is viewing area outside tile bounds → pan to DEM area

### Large file sizes
**Reduce file sizes**:

```bash
# Lower max zoom
python scripts/generate_tiles.py --max-zoom 14  # Instead of 17

# Simplify vectors
ogr2ogr -simplify 10 simplified.gpkg input.gpkg

# Use lower DEM resolution
gdalwarp -tr 30 30 -r bilinear input.tif downsampled.tif

# Increase contour interval
--contour-interval 20  # Instead of 10
```

**File size scaling**:
- z17 → z16: ~4x smaller
- z17 → z14: ~16x smaller
- Contour interval 20m vs 10m: ~2x smaller

### Processing very slow
**Speed improvements**:

1. **Reduce DEM resolution**:
   ```bash
   gdalwarp -tr 30 30 -r bilinear input.tif downsampled.tif
   ```

2. **Use breaching instead of filling**:
   ```bash
   python scripts/prepare_dem.py --breach  # Faster than --fill
   ```

3. **Process smaller area**:
   ```bash
   gdalwarp -cutline boundary.geojson -crop_to_cutline input.tif clipped.tif
   ```

4. **Lower max zoom**:
   ```bash
   python scripts/generate_tiles.py --max-zoom 14
   ```

5. **Increase contour interval**:
   ```bash
   --contour-interval 20  # Fewer contour lines = faster
   ```

### Out of memory errors
- Process smaller area or lower resolution
- Increase system swap space
- Use windowed processing (scripts already do this for large files)
- Close other applications

## Complete Workflow Examples

### Minimal Workflow (DEM-Derived Streams Only)

```bash
# 1. Download DEM to data/raw/dem/elevation.tif

# 2. Process DEM
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# 3. Extract streams at balanced threshold
python scripts/prepare_streams.py \
  --flow-acc data/processed/dem/flow_accumulation.tif \
  --flow-dir data/processed/dem/flow_direction.tif \
  --output data/processed/streams_dem.gpkg \
  --threshold 250

# 4. Generate tiles
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17

# 5. Start application
cd backend && uvicorn app.main:app --reload &
cd frontend && npm run dev
```

### Complete Workflow (DEM + NHD + HUC12)

```bash
# 1. Download data
# - DEM to data/raw/dem/elevation.tif
# - NHD to data/raw/nhd/NHDFlowline.shp
# - WBD to data/raw/wbd/WBDHU12.shp

# 2. Process DEM
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/

# 3. Extract DEM-derived streams (multi-threshold)
for threshold in 100 250 500 1000; do
  python scripts/prepare_streams.py \
    --flow-acc data/processed/dem/flow_accumulation.tif \
    --flow-dir data/processed/dem/flow_direction.tif \
    --output data/processed/streams_t${threshold}.gpkg \
    --threshold $threshold
done

# 4. Filter DEM streams
python scripts/filter_dem_streams.py \
  --input data/processed/streams_t250.gpkg \
  --output data/processed/streams_dem.gpkg \
  --min-length 25 \
  --min-drainage-area 0.01 \
  --flow-acc data/processed/dem/flow_accumulation.tif

# 5. Process NHD streams
python scripts/process_nhd.py \
  --input data/raw/nhd/NHDFlowline.shp \
  --output data/processed/streams_nhd.gpkg \
  --bounds data/processed/dem/filled_dem.tif

# 6. Process HUC12 watersheds
python scripts/process_huc.py \
  --input data/raw/wbd/WBDHU12.shp \
  --output data/processed/huc12.gpkg \
  --bounds data/processed/dem/filled_dem.tif

# 7. Generate tiles for all layers
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 10

# 8. Verify tiles
for file in data/tiles/*.pmtiles; do
  echo "=== $(basename $file) ==="
  pmtiles show "$file" | head -20
done

# 9. Start application
cd backend && source venv/bin/activate && uvicorn app.main:app --reload &
cd frontend && npm run dev

# 10. Open http://localhost:5173
```

### Production Workflow (Optimized)

```bash
# Use lower max zoom and higher contour interval for faster processing
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 14 \
  --contour-interval 20 \
  --raster-resampling lanczos

# Simplify vectors before tiling
ogr2ogr -simplify 5 data/processed/streams_simplified.gpkg data/processed/streams_dem.gpkg
ogr2ogr -simplify 10 data/processed/huc12_simplified.gpkg data/processed/huc12.gpkg

# Use simplified versions for tile generation
```

## Data Credits

When using this application, please credit data sources appropriately:

- **USGS 3DEP**: "Elevation data from USGS 3D Elevation Program"
- **Copernicus DEM**: "Copernicus DEM ©2021 European Space Agency"
- **USGS NHD**: "Stream data from USGS National Hydrography Dataset"
- **USGS WBD**: "Watershed boundaries from USGS Watershed Boundary Dataset"
- **USGS Geology**: "Geologic data from USGS State Geologic Maps"
- **DEM-Derived Streams**: "Stream network derived from DEM using WhiteboxTools"

## Next Steps

- **Customize layer styles**: Edit `frontend/src/lib/config/layers.ts` (LAYER_SOURCES)
- **Add custom boundaries**: Process and tile additional vector datasets
- **Optimize performance**: See [ARCHITECTURE.md](ARCHITECTURE.md) for caching strategies
- **Deploy to production**: See [DEPLOYMENT.md](DEPLOYMENT.md) for cloud deployment guides

## References

- [WhiteboxTools Manual](https://www.whiteboxgeo.com/manual/wbt_book/)
- [GDAL Documentation](https://gdal.org/)
- [Tippecanoe Documentation](https://github.com/felt/tippecanoe)
- [PMTiles Specification](https://github.com/protomaps/PMTiles)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [USGS NHD](https://www.usgs.gov/national-hydrography)
- [USGS WBD](https://www.usgs.gov/national-hydrography/watershed-boundary-dataset)
