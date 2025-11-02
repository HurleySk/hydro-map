# Changelog

All notable changes to Hydro-Map are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-11-02

### Added
- **Water Accumulation Heatmap**: New raster layer visualizing upslope water accumulation patterns
  - Blue gradient from transparent (no flow) to deep blue (high accumulation)
  - Based on log-transformed flow accumulation data (1-51,208 cell range)
  - 147MB PMTiles with zoom levels 8-17
- **Dynamic Legend Component**: Color gradient legend for water accumulation
  - Auto-shows/hides with layer visibility
  - Real-time opacity updates matching layer opacity
  - Positioned bottom-right with clear High/Low labels
- **Feature-Rich Vector Basemaps**: Stadia Maps integration for detailed POI display
  - Detailed mode (OSM Bright): Building footprints, parks, schools, land use features
  - Minimal mode (Alidade Smooth): Clean, minimal style
  - Data Only mode: No basemap for maximum data layer emphasis
  - Requires free Stadia Maps API key (20k views/month free tier)
- **Geology Pattern Textures**: Distinct visual patterns for colorblind accessibility
  - 7 unique patterns (horizontal lines, diagonal, crosshatch, waves, dots, vertical, sparse dots)
  - Patterns overlay geology layer polygons independent of color
  - Visible in both map layer and legend
  - Ensures red/green colorblind users can distinguish Sedimentary from Volcanic types
- Color ramp configuration at `scripts/color_ramps/flow_accumulation.txt`
- Percentile computation utility at `scripts/compute_percentiles.py`

### Changed
- Hydrology layer group now includes Water Accumulation option
- UI improvements with collapsible sidebar sections (Map Layers, Analysis Tools, System Status)
- Basemap Toggle now offers Detailed/Minimal/Data Only options
- Darker stream colors for better visibility (#1e3a8a for NHD, gradient for DEM streams)
- BaseMapToggle labels updated for clarity (Vector → Detailed, Light → Minimal, None → Data Only)

### Technical
- Processing pipeline: Log transform → Percentile normalization (p2=0.693, p98=5.878) → 8-bit → Color relief → PMTiles
- Legend component (`Legend.svelte`) with dynamic opacity binding to layer state
- Fixed sidebar scrolling issue when expanded content exceeds viewport
- Geology layer patterns generated via canvas-based pattern utility (`patterns.ts`)
- MapLibre GL `fill-pattern` property enables texture overlay on vector polygons

## [1.2.1] - 2025-11-02

### Changed
- Documentation overhaul - comprehensive updates to all markdown files
- Improved documentation cross-referencing and consistency
- Enhanced troubleshooting guides

## [1.2.0] - 2025-11-01

### Added
- Centralized layer configuration system (`LAYER_SOURCES` in `layers.ts`)
- Single source of truth for all layer metadata
- Automatic layer registration in Map.svelte

### Changed
- Refactored layer management architecture
- Simplified adding new layers (edit single file instead of multiple)
- Layer configuration now drives both UI and map sources automatically

### Technical
- Map.svelte reads from LAYER_SOURCES to create map sources and layers
- LayerPanel.svelte auto-generates UI from LAYER_SOURCES
- Type-safe layer configuration with TypeScript interfaces

## [1.1.1] - 2025-10-31

### Added
- Dual stream network support: NHD-based AND DEM-derived streams
- Independent toggle for "Real Streams" (NHD) vs "DEM-Derived Streams"
- `streams_nhd.pmtiles` for official USGS stream network
- `streams_dem.pmtiles` for calculated drainage network
- Both streams can be displayed simultaneously for comparison

### Changed
- Stream layer architecture split into two independent layers
- Different styling for each stream type (solid blue vs drainage area gradient)
- NHD streams visible by default, DEM streams hidden by default

### Technical
- Separate PMTiles files with distinct vector layer IDs
- Frontend config supports multiple stream sources
- Stream source selection in LAYER_SOURCES

## [1.1.0] - 2025-10-28

### Added
- All core layers working and rendering correctly
- HUC12 watershed boundaries reference layer
- Multi-layer pattern for HUC12 (fill, outline, labels)
- Contour lines with automatic generation
- Layer grouping (terrain, hydrology, reference)

### Fixed
- Layer visibility and opacity controls
- PMTiles protocol initialization race condition
- Raster tile rendering issues
- Vector tile layer naming consistency

### Technical
- PMTiles Protocol registered before map creation
- Raster metadata properly inserted for all tiles
- XYZ tile addressing (not TMS) for MapLibre compatibility

## [1.0.4] - 2025-10-25

### Added
- Location search with Nominatim geocoding
- Search history with localStorage persistence
- BaseMap toggle (color/light/none options)
- UI panel expansion states with localStorage persistence
- Layer group expansion states (terrain/hydrology)

### Changed
- Improved UI organization with collapsible panels
- Map view state persists across sessions
- Enhanced user experience with state persistence

### Fixed
- Panel state persistence bugs
- Search history ordering

## [1.0.3] - 2025-10-22

### Added
- Tile status monitoring panel
- Coverage detection for current map view
- Max zoom reporting for each PMTiles source
- Real-time tile availability checks

### Changed
- System Status panel now shows tile health
- Improved error messaging for missing tiles

### Technical
- PMTiles metadata caching for performance
- Tile bounds checking against map viewport
- Max zoom detection from PMTiles headers

## [1.0.2] - 2025-10-20

### Added
- HUC12 watershed boundaries layer (USGS WBD)
- Reference layer support in UI
- HUC12 processing script (`process_huc.py`)

### Changed
- Layer organization includes "reference" category
- Updated layer panel to support reference layers

## [1.0.1] - 2025-10-18

### Fixed
- Categorical raster resampling (aspect layer)
- Nearest-neighbor resampling for aspect to prevent color bleeding
- Tile boundary artifacts in aspect layer
- Visual quality improvements

### Technical
- Automatic resampling method override for aspect in generate_tiles.py
- Proper handling of categorical vs continuous rasters

## [1.0.0] - 2025-10-15

### Added
- Initial public release
- DEM-based watershed delineation
- Cross-section elevation profiles
- Feature info tool for stream queries
- Hillshade, slope, aspect terrain layers
- DEM-derived stream network
- Contour lines
- Caching for delineation results
- FastAPI backend with REST API
- SvelteKit frontend with MapLibre GL JS
- PMTiles for efficient tile serving
- Docker deployment support

### Technical
- WhiteboxTools for hydrological processing
- D8 flow analysis and tracing
- Multi-threshold stream extraction
- Stream confidence scoring
- Raster tile pipeline (DEM → XYZ → MBTiles → PMTiles)
- Vector tile pipeline (GeoPackage → GeoJSON → MBTiles → PMTiles)

## [0.9.0] - 2025-10-01

### Added
- Beta release for testing
- Core watershed delineation functionality
- Basic UI with map and controls

## [0.5.0] - 2025-09-15

### Added
- Alpha release
- Proof of concept for DEM processing
- Initial backend API structure

---

## Version Numbering

- **Major (X.0.0)**: Breaking changes, major feature additions
- **Minor (1.X.0)**: New features, non-breaking changes
- **Patch (1.0.X)**: Bug fixes, documentation updates

## Upgrade Notes

### Upgrading to 1.2.0+

The v1.2.0 refactor introduces LAYER_SOURCES centralization. If you've customized layer configuration:

1. Migrate layer definitions from `stores.ts` to `layers.ts` (LAYER_SOURCES)
2. Remove manual layer additions from `Map.svelte`
3. Update `LayerPanel.svelte` to read from LAYER_SOURCES

The new system automatically handles layer registration.

### Upgrading to 1.1.1+

If you have both NHD and DEM streams processed:

1. Regenerate tiles with `generate_tiles.py` to create both `streams_nhd.pmtiles` and `streams_dem.pmtiles`
2. Update frontend config if you've customized stream layer settings
3. Both stream layers will be available in the Hydrology group

### Upgrading from 0.x to 1.0+

Major architecture changes:

1. Regenerate all PMTiles with proper metadata
2. Use `--xyz` flag with gdal2tiles (not TMS)
3. Update layer configuration to use new structure
4. Run database migrations if using custom backend changes

## Links

- [GitHub Repository](https://github.com/HurleySk/hydro-map)
- [Documentation](docs/README.md)
- [Issue Tracker](https://github.com/HurleySk/hydro-map/issues)
