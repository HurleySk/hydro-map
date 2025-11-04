# Stream Network Data

**Version**: 1.7.0

## Overview

Hydro-Map now ships with **Fairfax County hydrography** as the default hydrology dataset. Three layers are generated from Fairfax GIS open data:

- `fairfax_water_lines`: Streams, channels, ditches, and canals
- `fairfax_water_polys`: Ponds, lakes, and reservoirs
- `perennial_streams`: Simplified perennial-only network

Scripts `download_fairfax_hydro.py` and `prepare_fairfax_hydro.py` (Steps 3 & 4 in [DATA_PREPARATION.md](../DATA_PREPARATION.md)) automate download, clipping, reprojection, field normalization, and metric calculation.

**Need another region?** Swap dataset URLs in the scripts, or use the legacy DEM/NHD extraction workflow described later in this document.

## Legacy DEM-Derived Stream Methodology

### 1. Flow Accumulation Analysis

Stream extraction begins with DEM-derived flow accumulation, which represents the number of upstream cells that drain to each cell. The workflow uses WhiteboxTools to:

1. Fill or breach depressions in the DEM
2. Compute D8 flow direction (8 possible flow directions)
3. Compute flow accumulation from flow direction
4. Apply threshold to identify stream initiation points

**Why flow accumulation?** It directly represents catchment area and correlates with stream discharge - the fundamental determinant of whether a channel exists.

### 2. Multi-Threshold Extraction

Rather than a single threshold, we extract streams at **four thresholds** to capture different stream scales:

| Threshold | Cell Count | Drainage Area* | Stream Type | Use Case |
|-----------|-----------|----------------|-------------|----------|
| t100 | 100 cells | ~0.01 km² | Headwater streams | Maximum detail, high artifact rate |
| t250 | 250 cells | ~0.025 km² | Small streams | Good balance of detail/quality |
| t500 | 500 cells | ~0.05 km² | Medium streams | Fewer artifacts, misses headwaters |
| t1000 | 1000 cells | ~0.1 km² | Major streams | Lowest artifact rate, main channels only |

*For 10m DEM (0.01 ha per cell)

**Rationale**: Different thresholds suit different purposes. Fine thresholds (t100) capture ephemeral headwaters but include more DEM artifacts. Coarse thresholds (t1000) miss small streams but have higher confidence. By extracting all four, users can choose the appropriate level of detail.

### 3. Stream Order Calculation

We use **Strahler stream order** to classify stream hierarchy:

- **Order 1**: Headwater streams (no upstream tributaries)
- **Order 2**: Formed by junction of two order-1 streams
- **Order 3**: Formed by junction of two order-2 streams
- **Order N**: Junction of two order-(N-1) streams

Stream order is computed using WhiteboxTools' `strahler_stream_order` algorithm based on the flow direction raster.

### 4. Drainage Area Calculation

Drainage area is calculated for each stream segment by:

1. Sampling the flow accumulation raster at the **downstream endpoint** of each segment
2. Converting accumulated cells to area using DEM resolution and CRS
3. Accounting for geographic vs. projected coordinate systems

**Formula**:
```
drainage_area_km² = flow_accumulation_cells × pixel_area_km²

For geographic CRS (lat/lon):
  pixel_width_km = pixel_width_deg × 111.32 × cos(center_latitude)
  pixel_height_km = pixel_height_deg × 111.32
  pixel_area_km² = pixel_width_km × pixel_height_km

For projected CRS (meters):
  pixel_area_km² = (pixel_width_m × pixel_height_m) / 1,000,000
```

**Why downstream endpoint?** The downstream point has accumulated all upstream flow, giving the total drainage area for that stream segment.

### 5. Artifact Filtering

DEM-derived streams can include artifacts from:
- Erroneous flow directions caused by noise/errors in the DEM
- Very short segments at confluences
- Perfectly straight channels (unrealistic in nature)

The filtering process applies multiple checks:

#### a. Length Filtering
Removes segments shorter than a minimum length (default: 25m)

**Rationale**: Very short segments are often artifacts from vectorization or DEM noise. Real streams rarely change direction in <25m.

#### b. Drainage Area Filtering
Removes streams with implausibly small drainage areas (default: 0.01 km²)

**Rationale**: For a stream to have continuous flow, it needs sufficient catchment area. Segments with tiny drainage areas are likely artifacts.

#### c. Geometric Filtering (Sinuosity)
Calculates sinuosity and removes unnaturally straight segments:

```
sinuosity = stream_length / straight_line_distance
```

- **Real streams**: Sinuosity typically 1.1-3.0 (meandering)
- **Artifacts**: Sinuosity often 1.0-1.05 (perfectly straight)

Segments with `sinuosity < 1.1` and `length < 100m` are flagged as potential artifacts.

**Rationale**: Natural streams meander due to erosion patterns. Perfectly straight short segments often result from DEM gridding effects.

### 6. Flow Persistence Classification

Streams are classified based on expected flow regime using drainage area as a proxy:

| Class | Drainage Area | Expected Flow Behavior |
|-------|---------------|----------------------|
| **Perennial** | ≥ 5.0 km² | Year-round continuous flow |
| **Intermittent** | 0.5 - 5.0 km² | Seasonal flow, dry in summer/drought |
| **Ephemeral** | < 0.5 km² | Flow only during/after precipitation events |

**Caveats**:
- Thresholds are approximate and vary by climate
- Arid regions: Higher thresholds for perennial flow
- Humid regions: Lower thresholds may sustain perennial flow
- This classification is a first-order estimate, not field-verified

### 7. Confidence Scoring

Each stream segment receives a confidence score (0-1) based on multiple factors:

```python
# Normalized drainage area (0-1, capped at 10 km²)
da_score = min(drainage_area_sqkm / 10.0, 1.0)

# Normalized length (0-1, capped at 1000m)
length_score = min(length_m / 1000.0, 1.0)

# Sinuosity bonus (0-0.3)
sinuosity_bonus = 0.0
if sinuosity >= 1.1:
    sinuosity_bonus = min((sinuosity - 1.0) * 0.15, 0.3)

# Stream order bonus (0-0.2)
order_bonus = min((stream_order - 1) * 0.05, 0.2)

# Combined confidence
confidence = (da_score * 0.4) + (length_score * 0.4) + sinuosity_bonus + order_bonus
```

**Score interpretation**:
- **0.7 - 1.0**: Very high confidence (likely real stream)
- **0.5 - 0.7**: High confidence
- **0.3 - 0.5**: Medium confidence (visual inspection recommended)
- **0.0 - 0.3**: Low confidence (likely artifact)

**Weights rationale**:
- Drainage area (40%): Primary determinant of stream existence
- Length (40%): Longer segments less likely to be artifacts
- Sinuosity (up to 30%): Meandering indicates natural process
- Stream order (up to 20%): Higher-order streams more reliable

### 8. Quality Assurance

The QA workflow generates a comprehensive report including:

1. **Overall statistics**: Total count, length, spatial extent
2. **Stream order distribution**: Count and length by order
3. **Drainage area distribution**: Histogram of drainage areas
4. **Flow persistence**: Breakdown by Perennial/Intermittent/Ephemeral
5. **Confidence distribution**: How many streams at each confidence level
6. **Geometric metrics**: Sinuosity statistics
7. **Data quality checks**: Missing values, null geometries
8. **Recommendations**: Parameter tuning suggestions based on results

**Interpretation guidelines**:

- **High artifact rate (>20% low confidence)**:
  - Increase `--min-length` parameter
  - Increase `--min-drainage-area` parameter
  - Use coarser threshold (t500 or t1000)

- **Many straight streams (>50% sinuosity < 1.1)**:
  - DEM quality issues (check source data)
  - Apply stricter geometric filtering

- **All ephemeral classification**:
  - Fine threshold capturing headwaters (expected for t100/t250)
  - Use t500 or t1000 for perennial streams

## UI Integration and Output

### PMTiles Output

The tile generation pipeline creates **`streams_dem.pmtiles`** from the processed stream GeoPackage:

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles
```

**Input**: `data/processed/streams_dem.gpkg` (filtered stream network)
**Output**: `data/tiles/streams_dem.pmtiles` (vector tiles, z8-17)

### Vector Layer Naming

**IMPORTANT**: The internal layer name in PMTiles must be `streams` (not `streams_t250_filtered` or `streams_dem`).

The tile generation script automatically names the internal layer `streams` for frontend compatibility:

```typescript
// frontend/src/lib/config/layers.ts
{
  id: 'streams-dem',
  label: 'DEM-Derived Streams',
  filename: 'streams_dem.pmtiles',
  vectorLayerId: 'streams',  // Must match internal PMTiles layer name
  // ...
}
```

Mismatch between `vectorLayerId` and internal layer name will cause the layer not to render.

### Map Layer Appearance

In the Hydro-Map UI:

- **Layer name**: "DEM-Derived Streams"
- **Layer group**: Hydrology
- **Default visibility**: Hidden (not visible by default)
- **Style**: Blue gradient by drainage area (darker = larger drainage)
- **Toggle**: Users can enable/disable independently from NHD streams

### Comparing with NHD

The application supports **simultaneous display** of both stream sources:

- **DEM-Derived Streams** (this methodology): Global coverage, shows ephemeral channels
- **Real Streams** (NHD): US-only, curated official network with names

Users can toggle both layers on to:
- Validate DEM extraction quality
- Identify streams present in DEM but missing from NHD (ephemeral channels)
- Identify streams in NHD but missing from DEM (data resolution issues)

This dual-layer approach provides comprehensive stream coverage and quality validation.

### Automation Script

The complete workflow from DEM to filtered streams is automated:

```bash
bash scripts/workflow_pure_dem_streams.sh
```

This script runs:
1. Multi-threshold stream extraction (t100, t250, t500, t1000)
2. Filtering with recommended parameters
3. Quality assurance report generation
4. Final output preparation

See the script for customization options.

## Workflow Scripts

### prepare_streams.py

Extracts stream network from flow accumulation using WhiteboxTools.

**Key functions**:
- `extract_streams_at_threshold()`: Main extraction logic
- `calculate_drainage_areas_from_flow_acc()`: Drainage area calculation

**Algorithm**:
1. Apply threshold to flow accumulation → binary stream raster
2. Compute stream order from flow direction + stream raster
3. Vectorize stream raster to line segments
4. Sample stream order at segment midpoints
5. Calculate drainage area at segment outlets
6. Compute segment lengths in meters

### filter_dem_streams.py

Filters DEM-derived streams to remove artifacts and compute attributes.

**Key functions**:
- `calculate_geometric_metrics()`: Sinuosity calculation
- `filter_geometric_artifacts()`: Straight segment removal
- `classify_flow_persistence()`: Perennial/Intermittent/Ephemeral
- `calculate_confidence_scores()`: Combined confidence metric

**Algorithm**:
1. Load stream layer from GeoPackage
2. Calculate segment lengths (in projected CRS)
3. Filter by minimum length threshold
4. Calculate drainage areas from flow accumulation
5. Filter by minimum drainage area threshold
6. Calculate sinuosity for each segment
7. Remove very straight short segments
8. Classify flow persistence based on drainage area
9. Compute confidence scores
10. Export filtered layer with all attributes

### qa_stream_network.py

Generates quality assurance report for stream networks.

**Outputs**:
- Markdown report with statistics and visualizations
- Console summary of key metrics

**Metrics**:
- Stream count, length, and spatial coverage
- Distribution by stream order
- Drainage area histogram
- Confidence score distribution
- Flow persistence breakdown
- Sinuosity statistics
- Data quality checks

## Data Attributes

Filtered stream layers include these attributes:

| Attribute | Type | Description | Units |
|-----------|------|-------------|-------|
| `order` | integer | Strahler stream order | - |
| `length_m` | float | Segment length | meters |
| `length_km` | float | Segment length | kilometers |
| `drainage_area_sqkm` | float | Upstream drainage area | km² |
| `flow_accum_threshold` | integer | Threshold used for extraction | cells |
| `sinuosity` | float | Stream length / straight-line distance | ratio |
| `stream_type` | string | Perennial / Intermittent / Ephemeral | - |
| `confidence_score` | float | Quality confidence (0-1) | - |
| `geometry` | LineString | Stream segment geometry | - |

## Limitations and Considerations

### DEM Resolution Effects

- **10m DEM**: Good for streams > 0.01 km² drainage area
- **30m DEM**: Reliable for streams > 0.1 km² drainage area
- **90m DEM**: Only major streams (> 1 km² drainage area)

Finer DEMs capture more detail but also more noise. Coarser DEMs miss small streams.

### Climate and Hydrogeology

The flow persistence thresholds (5.0 km² for perennial, 0.5 km² for intermittent) are **general estimates** that vary significantly by:

- **Climate**: Arid vs. humid regions
- **Geology**: Permeable (karst) vs. impermeable bedrock
- **Season**: Thresholds based on average conditions
- **Land use**: Urban areas vs. forested catchments

For accurate classification, thresholds should be calibrated to local conditions using field observations.

### Comparison to NHD

Advantages of DEM-derived streams:
- Global coverage (works anywhere with DEM)
- Consistent methodology
- Drainage area attribute included
- No dependency on external datasets

Disadvantages vs. NHD:
- Higher artifact rate (requires filtering)
- No stream names or classifications
- Headwater locations approximate
- Flow direction may differ from actual channels in flat areas

NHD streams are field-verified and curated, making them more accurate where available. DEM-derived streams are a good alternative for:
- Regions without NHD coverage
- International projects
- Applications requiring drainage area
- Rapid prototyping / initial analysis

### Flat Terrain Challenges

DEM-derived flow routing struggles in flat areas (<1% slope) because:
- Flow direction ambiguous with small elevation changes
- DEM errors comparable to terrain relief
- Channels may not follow topographic lows

**Mitigation strategies**:
- Use higher-resolution DEM if available
- Breach instead of fill depressions
- Apply stricter confidence filtering
- Consider supplementing with external data in flat regions

## Recommended Workflows

### High-Detail Headwater Analysis
```bash
# Use threshold 100, minimal filtering
python scripts/prepare_streams.py --multi-threshold --flow-acc ... --flow-dir ...
python scripts/filter_dem_streams.py --layer streams_t100 --min-length 10 --min-drainage-area 0
```

### Balanced Accuracy and Coverage
```bash
# Use threshold 250, moderate filtering (RECOMMENDED)
python scripts/prepare_streams.py --multi-threshold --flow-acc ... --flow-dir ...
python scripts/filter_dem_streams.py --layer streams_t250 --min-length 25 --min-drainage-area 0.01
```

### Conservative / High-Confidence Only
```bash
# Use threshold 500 or 1000, strict filtering
python scripts/prepare_streams.py --multi-threshold --flow-acc ... --flow-dir ...
python scripts/filter_dem_streams.py --layer streams_t500 --min-length 50 --min-drainage-area 0.05
```

### Production Workflow with QA
```bash
# Complete workflow with quality assurance
bash scripts/workflow_pure_dem_streams.sh
```

See `scripts/workflow_pure_dem_streams.sh` for the full automated pipeline.

## References

### Algorithms and Methods

- **Strahler stream ordering**: Strahler, A. N. (1957). "Quantitative analysis of watershed geomorphology". *Transactions, American Geophysical Union*, 38(6), 913-920.

- **D8 flow routing**: O'Callaghan, J. F., & Mark, D. M. (1984). "The extraction of drainage networks from digital elevation data". *Computer Vision, Graphics, and Image Processing*, 28(3), 323-344.

- **Depression filling**: Jenson, S. K., & Domingue, J. O. (1988). "Extracting topographic structure from digital elevation data for geographic information system analysis". *Photogrammetric Engineering and Remote Sensing*, 54(11), 1593-1600.

### Tools

- **WhiteboxTools**: Lindsay, J. B. (2016). "Whitebox GAT: A case study in geomorphometric analysis". *Computers & Geosciences*, 95, 75-84. https://www.whiteboxgeo.com/

- **GDAL**: GDAL/OGR contributors (2024). *GDAL/OGR Geospatial Data Abstraction software Library*. Open Source Geospatial Foundation. https://gdal.org

- **Tippecanoe**: Mapbox (2024). *Tippecanoe*. https://github.com/felt/tippecanoe

## Updates and Versioning

**Current version**: 1.7.0 (Fairfax hydrography workflow is the default configuration)

**Stream network evolution**:
- **v1.7.0 (2025-12)**: Fairfax County water features and perennial streams integrated as default hydrology layers
- **v1.5.0 (2025-11)**: Feature Info tool falls back to stream datasets when available
- **v1.4.0 (2025-11)**: Documentation alignment with Hydro-Map v1.4.0; no pipeline changes
- **v1.1.1+ (2025-11)**: Dual stream network - DEM-derived AND NHD-based layers available simultaneously
- **v1.0 (2025-11)**: Pure DEM implementation with multi-threshold extraction, artifact filtering, and confidence scoring
- **v0.x (2024-2025)**: NHD-based approach only (US only)

**Note**: NHD streams are NOT discontinued. As of v1.1.1, the application supports both DEM-derived and NHD-based streams as independent toggleable layers. Users can display one, both, or neither depending on their needs.

**Future enhancements**:
- Climate-adjusted flow persistence thresholds
- Machine learning artifact detection
- Integration with global river datasets (e.g., HydroRIVERS) for validation
- Upstream area calculation for pour points
- Automated stream name assignment using proximity to NHD features
## Fairfax Hydrography Layers

### Fairfax Water Features (Lines)

- **Source**: `water_features_lines` ArcGIS REST service
- **Layer ID**: `fairfax_water_lines`
- **Key fields**:
  - `name`: Feature name (if provided)
  - `type`: Stream, channel, canal, ditch, etc.
  - `length_km`: Calculated segment length in kilometres (UTM 18N)
  - `data_source`: Always set to "Fairfax County GIS"
- **Usage**: Styled by `type` with colour ramp in `frontend/src/lib/config/layers.ts`
- **API access**: Add `"fairfax-water-lines"` to `LAYER_DATASET_MAP` (already configured by default) to expose via Feature Info

### Fairfax Water Features (Polygons)

- **Source**: `water_features_polys` ArcGIS REST service
- **Layer ID**: `fairfax_water_polys`
- **Key fields**:
  - `name`: Waterbody name (may be null)
  - `type`: Lake, pond, reservoir, etc.
  - `area_sqkm`: Polygon area in square kilometres (UTM 18N)
  - `data_source`: "Fairfax County GIS"
- **Usage**: Filled with type-based colour palette; outline colour configurable in `layers.ts`

### Fairfax Perennial Streams

- **Source**: `OpenData_S14` ArcGIS layer (perennial streams)
- **Layer ID**: `perennial_streams`
- **Key fields**:
  - `name`: Stream name (if provided)
  - `feature_type` / `feature_code`: Fairfax classification codes
  - `length_km`: Calculated segment length in kilometres
  - `data_source`: "Fairfax County GIS"
- **Usage**: Styled as deep blue linework to complement the more detailed water lines layer

### Quality Checks

- Run the scripts and verify outputs with `ogrinfo data/processed/fairfax_water_lines.gpkg -al -so`
- Inspect attribute distributions in QGIS (length/area histograms)
- Compare against basemap imagery to confirm alignment

> **Tip**: Swap dataset URLs in the download script to bring in a different county or state dataset. Ensure you update the layer IDs in `prepare_fairfax_hydro.py` if the service exposes different names.
