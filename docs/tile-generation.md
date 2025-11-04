# Tile Generation Quick Reference

**Version**: 1.7.0

Quick reference for common tile generation commands and workflows.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Standard Generation Commands](#standard-generation-commands)
- [Resolution Guide](#resolution-guide)
- [Output Files](#output-files)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Options](#advanced-options)

## Prerequisites

### Required Tools

All commands assume you have installed:

- **GDAL** (`gdal2tiles.py`, `gdal_translate`, `gdal_contour`)
- **Tippecanoe** (vector tile generation)
- **mb-util** (Python package, installed in backend venv)
- **PMTiles CLI** (MBTiles → PMTiles conversion)

See [DATA_PREPARATION.md - Installing Required Tools](DATA_PREPARATION.md#installing-required-tools) for installation instructions.

### Activate Backend Environment

The Python script requires backend dependencies:

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Important**: Run all `generate_tiles.py` commands from the project root (not from backend/).

## Standard Generation Commands

All commands below assume you're in the project root directory with backend venv activated.

### Maximum Detail (z=17) - Recommended

Best for ~200m viewing scales with crisp terrain detail:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 17 \
  --contour-interval 10
```

**Output**:
- Resolution at z=17: ~0.9 m/px (at latitude 38.8°)
- File sizes: ~30MB total (all layers)
  - hillshade.pmtiles: ~15-20MB
  - slope.pmtiles: ~8-12MB
  - aspect.pmtiles: ~8-12MB
  - contours.pmtiles: ~5-10MB
  - fairfax_water_lines.pmtiles: ~2-4MB
  - fairfax_water_polys.pmtiles: ~2-4MB
  - perennial_streams.pmtiles: ~2-3MB
  - huc12.pmtiles: ~1-3MB (if processed)
- Generation time: 20-40 minutes (depends on area size)

### Balanced Resolution (z=16)

Good balance between detail and file size:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 16 \
  --contour-interval 10
```

**Output**:
- Resolution at z=16: ~1.9 m/px
- File sizes: ~15MB total (approximately 50% of z=17)
- Generation time: 10-20 minutes

### Fast Generation (z=14)

For quick testing or overview maps:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --max-zoom 14 \
  --contour-interval 20
```

**Output**:
- Resolution at z=14: ~7.5 m/px
- File sizes: ~5MB total
- Generation time: 5-10 minutes

### Regional Overview (z=12)

Large-scale regional visualization:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --min-zoom 8 \
  --max-zoom 12 \
  --contour-interval 50
```

**Output**:
- Resolution at z=12: ~30 m/px
- Very small file sizes (~2MB total)
- Generation time: 2-5 minutes

### Custom Resampling

Specify resampling method for raster tiles:

```bash
# Lanczos (default) - Sharp, high-quality
python scripts/generate_tiles.py \
  --raster-resampling lanczos \
  --max-zoom 17

# Bilinear - Smooth, good if lanczos creates artifacts
python scripts/generate_tiles.py \
  --raster-resampling bilinear \
  --max-zoom 17

# Nearest - For categorical rasters (automatically used for aspect)
python scripts/generate_tiles.py \
  --raster-resampling nearest \
  --max-zoom 17
```

**Note**: The script automatically overrides to `nearest` for aspect layer regardless of `--raster-resampling` flag.

### Custom Contour Intervals

Adjust contour density based on terrain and viewing scale:

```bash
# 5-meter contours for flat terrain, high detail
python scripts/generate_tiles.py --contour-interval 5

# 10-meter contours (recommended general use)
python scripts/generate_tiles.py --contour-interval 10

# 20-meter contours for mountainous terrain
python scripts/generate_tiles.py --contour-interval 20

# 50-meter contours for overview maps
python scripts/generate_tiles.py --contour-interval 50
```

**File size impact**: 20m interval is ~50% smaller than 10m interval.

## Resolution Guide

### Resolution Formula

Calculate pixel resolution for any zoom level and latitude:

```
resolution(z, lat) ≈ 156543.03392 × cos(lat) / 2^z meters/pixel
```

### Resolution Table

Example resolutions at latitude 38.8° (San Francisco area):

| Zoom | m/px | Feature Size @ 200px | Use Case |
|------|------|---------------------|----------|
| 10 | ~76 m | ~15 km | County scale |
| 12 | ~19 m | ~3.8 km | Watershed overview |
| 14 | ~4.8 m | ~960 m | Stream network detail |
| 15 | ~2.4 m | ~480 m | Terrain features |
| 16 | ~1.2 m | ~240 m | High detail |
| 17 | ~0.6 m | ~120 m | **Max recommended for 10m DEM** |
| 18 | ~0.3 m | ~60 m | Only for 3m or better DEM |

### DEM Resolution vs Max Zoom

Match max zoom to your DEM resolution:

| DEM Resolution | Recommended Max Zoom | Reasoning |
|----------------|---------------------|-----------|
| 3m (lidar) | z18 | 1:5 ratio DEM:tile |
| 10m (USGS 3DEP) | z17 | 1:15 ratio DEM:tile |
| 30m (Copernicus/SRTM) | z16 | 1:50 ratio DEM:tile |
| 90m (SRTM v3) | z14 | 1:150 ratio DEM:tile |

Higher zooms than recommended will show pixelated DEM data.

## Output Files

### Expected PMTiles Output

After running `generate_tiles.py`, expect the following files in `data/tiles/`:

**Raster Tiles** (always generated if DEM processed):
- `hillshade.pmtiles` - Shaded relief visualization
- `slope.pmtiles` - Slope angle in degrees (0-90°)
- `aspect.pmtiles` - Compass direction in degrees (0-360°)

**Vector Tiles** (generated if source data exists):
- `contours.pmtiles` - Elevation contour lines (auto-generated if missing)
- `fairfax_water_lines.pmtiles` - Fairfax County water features (linework)
- `fairfax_water_polys.pmtiles` - Fairfax County water bodies (polygons)
- `perennial_streams.pmtiles` - Fairfax perennial stream network
- `huc12.pmtiles` - HUC12 watershed boundaries (if `huc12.gpkg` exists)

### Vector Layer ID Reference

**Important**: Vector layer names inside PMTiles must match `vectorLayerId` in frontend config:

| PMTiles File | Internal Layer Name | Config `vectorLayerId` |
|--------------|---------------------|-----------------------|
| `fairfax_water_lines.pmtiles` | `fairfax_water_lines` | `fairfax_water_lines` |
| `fairfax_water_polys.pmtiles` | `fairfax_water_polys` | `fairfax_water_polys` |
| `perennial_streams.pmtiles` | `perennial_streams` | `perennial_streams` |
| `huc12.pmtiles` | `huc12` | `huc12` |
| `contours.pmtiles` | `contours` | `contours` |

Mismatch will cause layers not to render.

### File Size Estimates

For 100 sq mi area @ 10m DEM:

**z=17** (max detail):
```
hillshade.pmtiles:         15-20 MB
slope.pmtiles:             8-12 MB
aspect.pmtiles:            8-12 MB
contours.pmtiles:          5-10 MB (10m interval)
fairfax_water_lines.pmtiles: 2-4 MB
fairfax_water_polys.pmtiles: 2-4 MB
perennial_streams.pmtiles:   2-3 MB
huc12.pmtiles:              1-3 MB
─────────────────────────────
Total:                     ~42-65 MB
```

**z=16** (balanced):
```
Total: ~20-35 MB (~50% of z=17)
```

**z=14** (fast):
```
Total: ~5-10 MB (~15% of z=17)
```

**Contour interval impact**:
- 10m interval: ~8MB contours.pmtiles
- 20m interval: ~4MB contours.pmtiles (50% smaller)
- 50m interval: ~1.5MB contours.pmtiles (80% smaller)

## Verification

### Check File Existence

```bash
# List all PMTiles with sizes
ls -lh data/tiles/*.pmtiles

# Expected output (example):
# -rw-r--r--  hillshade.pmtiles             18M
# -rw-r--r--  slope.pmtiles                 10M
# -rw-r--r--  aspect.pmtiles                10M
# -rw-r--r--  contours.pmtiles               8M
# -rw-r--r--  fairfax_water_lines.pmtiles    3M
# -rw-r--r--  fairfax_water_polys.pmtiles    3M
# -rw-r--r--  perennial_streams.pmtiles      2M
# -rw-r--r--  huc12.pmtiles                  2M
```

### Verify PMTiles Metadata

**Check raster tiles**:

```bash
pmtiles show data/tiles/hillshade.pmtiles
```

**Must show**:
```
tile type: png
tile compression: png (or unknown)
max zoom: 17
tile count: >1000
```

If `tile type` is empty, tiles won't render. Regenerate with metadata fix.

**Check vector tiles**:

```bash
pmtiles show data/tiles/fairfax_water_lines.pmtiles
```

**Must show**:
```
tile type: mvt
layer name: fairfax_water_lines
max zoom: 17
```

**Check bounds**:

```bash
pmtiles show data/tiles/hillshade.pmtiles | grep bounds
```

Bounds should match your DEM extent.

### Extract Sample Tile

Test a specific tile at zoom 14:

```bash
# Extract single zoom level
pmtiles extract data/tiles/hillshade.pmtiles \
  --region="-122.5,37.7,-122.3,37.9" \
  test.pmtiles

# Check extracted tile
pmtiles show test.pmtiles
```

### Verify in Application

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Check **System Status** → **Tile Status** panel
5. All layers should show "Available" for current map view
6. Toggle each layer to verify rendering
7. Open browser DevTools → Network tab
8. Verify `/tiles/*.pmtiles` requests return `206 Partial Content` with `Accept-Ranges: bytes`

## Troubleshooting

### "Command not found" Errors

**`gdal2tiles.py: command not found`**:
```bash
# Install GDAL
brew install gdal  # macOS
sudo apt-get install gdal-bin  # Ubuntu
```

**`tippecanoe: command not found`**:
```bash
# Install Tippecanoe
brew install tippecanoe  # macOS
sudo apt-get install tippecanoe  # Ubuntu
```

**`pmtiles: command not found`**:
```bash
# Download from GitHub releases
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.11.0/pmtiles_1.11.0_Linux_x86_64.tar.gz
tar xzf pmtiles_*.tar.gz
sudo mv pmtiles /usr/local/bin/
```

**`mb-util: command not found`**:
```bash
# Install in backend venv (NOT via Homebrew)
cd backend
source venv/bin/activate
pip install mbutil
```

### PMTiles Are Empty or Too Small

**Symptoms**: File sizes < 1MB, tile count < 100

**Causes**:
- Source data doesn't exist or is empty
- Zoom range doesn't cover data extent
- Data is outside default bounds

**Solutions**:
```bash
# Check source data
ls -lh data/processed/dem/*.tif
ls -lh data/processed/*.gpkg

# Verify data has content
gdalinfo data/processed/dem/hillshade.tif
ogrinfo data/processed/fairfax_water_lines.gpkg -al -so

# Check if source data is in correct location
# Script looks for:
# - data/processed/dem/*.tif (rasters)
# - data/processed/*.gpkg (vectors)
```

### Raster Tiles Don't Render

**Most common causes**:

1. **Missing metadata** (tile type empty):
   ```bash
   pmtiles show data/tiles/hillshade.pmtiles | grep "tile type"
   # If empty or missing, regenerate
   ```

2. **TMS tiles instead of XYZ**:
   - Script must use `--xyz` flag with gdal2tiles
   - Verify script line uses: `gdal2tiles.py --xyz ...`
   - TMS tiles have Y=0 at bottom, won't render in MapLibre

3. **Wrong resampling for categorical data**:
   - Aspect must use `nearest` resampling
   - Script automatically handles this

**Solution**: Re-run `generate_tiles.py` which automatically:
- Uses `--xyz` flag
- Inserts metadata via sqlite3
- Uses `nearest` for aspect

### Vector Tiles Don't Appear

**Layer name mismatch**:

```bash
# Check internal layer name
pmtiles show data/tiles/fairfax_water_lines.pmtiles | grep "layer"

# Compare with frontend config
# frontend/src/lib/config/layers.ts
# Look for vectorLayerId in LAYER_SOURCES
```

**Solution**: Layer name in PMTiles must match `vectorLayerId` in config.

### Tiles Only Cover Part of Area

**Causes**:
- DEM was clipped too tightly
- Tiles generated for subset of DEM
- Viewing area outside tile bounds

**Solutions**:
```bash
# Check tile bounds
pmtiles show data/tiles/hillshade.pmtiles | grep bounds

# Compare with DEM extent
gdalinfo data/processed/dem/filled_dem.tif | grep "Corner Coordinates"

# If DEM is larger than tiles, regenerate
# If viewing area is outside DEM, pan map to DEM area
```

### Large File Sizes

**Reduce file sizes**:

```bash
# Lower max zoom (most effective)
python scripts/generate_tiles.py --max-zoom 14  # ~4x smaller than z17

# Increase contour interval
python scripts/generate_tiles.py --contour-interval 20  # ~2x smaller

# Simplify vectors before tiling
ogr2ogr -simplify 10 simplified.gpkg input.gpkg

# Use lower DEM resolution
gdalwarp -tr 30 30 -r bilinear input.tif downsampled.tif
```

**File size scaling**:
- z17 → z16: ~50% size (2x fewer tiles)
- z17 → z14: ~10-15% size (8-16x fewer tiles)
- Contour interval 20m vs 10m: ~50% size
- DEM 30m vs 10m: ~10% size (9x fewer cells)

### Slow Generation

**Speed improvements**:

1. **Lower max zoom**: Biggest impact
   ```bash
   --max-zoom 14  # ~4x faster than z17
   ```

2. **Increase contour interval**:
   ```bash
   --contour-interval 20  # ~2x faster
   ```

3. **Process smaller area**:
   ```bash
   # Clip DEM before processing
   gdalwarp -cutline boundary.geojson -crop_to_cutline input.tif clipped.tif
   ```

4. **Use SSD storage**: Tile generation is I/O intensive

5. **Close other applications**: Free up CPU and memory

**Typical generation times** (100 sq mi @ 10m DEM):
- z14: 5-10 minutes
- z16: 10-20 minutes
- z17: 20-40 minutes

### Memory Issues

**"Out of memory" errors**:

- Process smaller area (clip DEM)
- Lower DEM resolution (30m instead of 10m)
- Lower max zoom (z14 instead of z17)
- Close other applications
- Increase system swap space

**Scripts use windowed processing** to limit memory usage, but very large DEMs may still need reduced resolution.

## Topographic Wetness Index (TWI) Raster

The TWI layer replaces the legacy water-accumulation heatmap. It highlights areas likely to retain water by combining flow accumulation and slope.

### Workflow Overview

1. **Compute TWI** from flow accumulation and slope rasters:
   ```bash
   python scripts/compute_twi.py --output data/processed/dem/twi.tif
   ```
2. **Normalize and color TWI** for map rendering:
   ```bash
   python scripts/process_twi_for_tiles.py
   ```
   This creates:
   - `data/processed/dem/twi_8bit.tif` (0-255 normalized raster)
   - `data/processed/dem/twi_color.tif` (RGBA raster with wetness color ramp)
3. **Generate PMTiles** from the colorized raster (until `generate_tiles.py` adds native TWI support, use the manual pipeline below).

### Manual PMTiles Generation

```bash
# 1. Generate XYZ tiles from the colorized raster
gdal2tiles.py --xyz --zoom 8-17 -r bilinear \
  data/processed/dem/twi_color.tif \
  data/tiles/temp_tiles/twi_xyz

# 2. Convert XYZ to MBTiles
mb-util data/tiles/temp_tiles/twi_xyz data/tiles/twi.mbtiles

# 3. Fix MBTiles metadata for overlays
sqlite3 data/tiles/twi.mbtiles \
  "INSERT OR REPLACE INTO metadata (name, value) VALUES ('format', 'png'); \
   INSERT OR REPLACE INTO metadata (name, value) VALUES ('type', 'overlay');"

# 4. Convert MBTiles to PMTiles
pmtiles convert data/tiles/twi.mbtiles data/tiles/twi.pmtiles
```

**Color ramp**: `scripts/color_ramps/twi.txt` controls the dry -> wet gradient. Adjust percentile parameters in `process_twi_for_tiles.py` if your area has very flat or very steep terrain.

**Cleanup**: Remove `data/tiles/temp_tiles/twi_xyz` and the intermediate `twi.mbtiles` once `twi.pmtiles` is verified to save disk space.

## Advanced Options

### Generate Only Specific Layers

Edit `scripts/generate_tiles.py` to comment out layers you don't need:

```python
# Comment out layers to skip
# RASTER_LAYERS = ['hillshade', 'slope', 'aspect']  # Skip rasters
RASTER_LAYERS = ['hillshade']  # Only hillshade

# VECTOR_LAYERS = ['fairfax_water_lines', 'fairfax_water_polys', 'perennial_streams', 'huc12', 'contours']
VECTOR_LAYERS = ['fairfax_water_lines']  # Generate just the Fairfax linework
```

### Custom Zoom Ranges Per Layer

For different detail levels:

```bash
# Generate terrain at z17
python scripts/generate_tiles.py --max-zoom 17

# Then generate HUC12 at lower zoom
# (Edit script to only process huc12)
python scripts/generate_tiles.py --max-zoom 14
```

### Parallel Processing

The script automatically uses multiple processes for raster tiling. To adjust:

```python
# In generate_tiles.py
# gdal2tiles.py inherently uses multiple processes
# tippecanoe can be parallelized with --threads option
```

### Custom Tile Formats

**JPEG for hillshade** (lossy, smaller files):

Edit gdal_translate command in script:
```bash
gdal_translate -of JPEG -co QUALITY=85 input.tif output.jpg
```

**WebP for modern browsers** (better compression):
```bash
gdal_translate -of WEBP -co QUALITY=90 input.tif output.webp
```

**Requires**: Updating metadata and frontend to handle JPEG/WebP tiles.

### Tile Caching Strategy

**Development**: Generate z17 for your test area
**Staging**: Generate z16 for broader testing
**Production**: Generate z14-z16 for large deployments, z17 for specific high-interest areas

Serve tiles from CDN (S3 + CloudFront) for best performance.

## Critical Technical Notes

### XYZ vs TMS Addressing

**CRITICAL**: Must use XYZ tiles, not TMS.

- **XYZ**: Y=0 at top/north (standard web mercator, OSM slippy map)
- **TMS**: Y=0 at bottom/south (not compatible with MapLibre GL JS)

`generate_tiles.py` uses `--xyz` flag with gdal2tiles to ensure XYZ format.

**Verification**: Open PMTiles in MapLibre - if tiles are vertically flipped, they're TMS.

### Raster Metadata Requirements

**CRITICAL**: Raster PMTiles must have metadata for rendering.

After mb-util conversion, script inserts:
```sql
INSERT OR REPLACE INTO metadata (name, value) VALUES ('format', 'png');
INSERT OR REPLACE INTO metadata (name, value) VALUES ('type', 'overlay');
```

Without this, `pmtiles show` reports empty tile type and tiles won't render.

### Categorical Raster Resampling

**CRITICAL**: Aspect (categorical raster) must use `nearest` resampling.

Using `lanczos` or `bilinear` for aspect causes:
- Color bleeding across tile boundaries
- Invalid compass values (e.g., 45.7° where only 0/45/90/etc. should exist)
- Visual artifacts at zoom transitions

`generate_tiles.py` automatically overrides to `nearest` for aspect layer regardless of `--raster-resampling` flag.

### Vector Layer Consistency

**CRITICAL**: Internal layer name in PMTiles must match frontend config.

Example: `fairfax_water_lines.pmtiles` has internal layer `fairfax_water_lines`, which must match:
```typescript
// frontend/src/lib/config/layers.ts
{
  id: 'fairfax-water-lines',
  vectorLayerId: 'fairfax_water_lines',  // Must match PMTiles layer name
  // ...
}
```

Mismatch causes "layer not found" errors.

## References

- [DATA_PREPARATION.md](DATA_PREPARATION.md) - Complete data preparation workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) - Tile generation pipeline details
- [GDAL Documentation](https://gdal.org/)
- [Tippecanoe Documentation](https://github.com/felt/tippecanoe)
- [PMTiles Specification](https://github.com/protomaps/PMTiles)
