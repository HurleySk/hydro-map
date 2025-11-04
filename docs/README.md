# Hydro-Map Documentation

**Version**: 1.7.0
**Last Updated**: 2025-12-15

## Welcome

This is the complete documentation for Hydro-Map, a web-based hydrological analysis tool for watershed delineation, terrain analysis, and regional hydrography visualization.

## Documentation Structure

Documentation is organized into guides for different audiences and use cases:

### Getting Started

**New to Hydro-Map?** Start here:

- **[Quick Start Guide](QUICK_START.md)** - Hands-on tutorial to get up and running in 30 minutes
  - Installation
  - Processing your first DEM
  - Running the application
  - Basic workflows

### User Guides

**Using the application:**

- **[UI Guide](UI_GUIDE.md)** - Complete interface reference
  - Map navigation
  - Layer controls
  - Tool usage (watershed delineation, cross-sections, feature info)
  - Keyboard shortcuts
  - Tips and best practices

### Developer Guides

**Building and customizing Hydro-Map:**

- **[Architecture](ARCHITECTURE.md)** - System design and technical overview
  - Component architecture
  - State management
  - Data flow
  - Technology stack
  - API specifications

- **[Data Preparation](DATA_PREPARATION.md)** - Complete data processing guide
  - DEM preparation
  - Fairfax County hydrography download & normalization
  - Optional DEM/NHD stream extraction (legacy)
  - HUC12 watershed boundaries
  - Tile generation

- **[Tile Generation](tile-generation.md)** - PMTiles creation reference
  - Raster tiles (hillshade, slope, aspect, TWI)
  - Vector tiles (Fairfax hydro, contours, HUC12, geology)
  - Critical technical notes
  - Verification and troubleshooting

- **[API Reference](API.md)** - Complete API documentation
  - Watershed delineation endpoint
  - Cross-section endpoint
  - Feature info endpoint
  - Tile serving endpoint
  - Request/response schemas
  - Code examples

### Configuration and Deployment

**Setting up Hydro-Map for production:**

- **[Configuration Guide](CONFIGURATION.md)** - Environment and settings
  - Environment variables
  - Backend configuration
  - Frontend configuration
  - Layer configuration
  - Performance tuning

- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
  - Docker deployment
  - Traditional server deployment
  - Reverse proxy configuration
  - SSL/TLS setup
  - Process management
  - Monitoring and logging

### Troubleshooting

**Having issues?**

- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
  - Quick diagnostics
  - Installation issues
  - Data processing issues
  - Tile generation issues
  - Backend API issues
  - Frontend issues
  - Performance issues
  - Deployment issues

### Reference Documentation

**Deep dives into specific topics:**

- **[Hydrology Data](data/STREAMS.md)** - Fairfax open-data workflow and legacy DEM-derived stream methodology
  - Fairfax County water feature pipeline
  - Optional DEM/NHD extraction process
  - Quality assurance considerations

## Quick Reference

### Common Tasks

| Task | Documentation | Quick Command |
|------|---------------|---------------|
| Install dependencies | [Quick Start](QUICK_START.md#prerequisites) | `pip install -r requirements.txt` |
| Process DEM | [Data Preparation](DATA_PREPARATION.md#step-1-dem-preparation) | `python scripts/prepare_dem.py` |
| Download Fairfax hydro data | [Data Preparation](DATA_PREPARATION.md#step-3-download-fairfax-hydrography) | `python scripts/download_fairfax_hydro.py` |
| Process Fairfax hydro data | [Data Preparation](DATA_PREPARATION.md#step-4-process-fairfax-hydrography) | `python scripts/prepare_fairfax_hydro.py` |
| (Optional) Extract DEM streams | [Hydrology Data](data/STREAMS.md) | `python scripts/prepare_streams.py` |
| Generate tiles | [Tile Generation](tile-generation.md) | `python scripts/generate_tiles.py` |
| Start backend | [Quick Start](QUICK_START.md#running-the-application) | `uvicorn app.main:app --reload` |
| Start frontend | [Quick Start](QUICK_START.md#running-the-application) | `npm run dev` |
| Add new layer | [Configuration](CONFIGURATION.md#layer-configuration) | Edit `layers.ts`, add PMTiles |
| Deploy with Docker | [Deployment](DEPLOYMENT.md#docker-deployment) | `docker-compose up -d` |

### File Locations

| Component | Location | Description |
|-----------|----------|-------------|
| Backend code | `backend/app/` | FastAPI application |
| Frontend code | `frontend/src/` | SvelteKit application |
| Data processing scripts | `backend/scripts/` | Python scripts for DEM/stream processing |
| Configuration | `.env` | Environment variables |
| Layer config | `frontend/src/lib/config/layers.ts` | Layer definitions |
| Raw data | `data/raw/` | Original source data |
| Processed data | `data/processed/` | Backend-ready data files |
| Tiles | `data/tiles/` | PMTiles for frontend |
| Cache | `backend/data/cache/` | Delineation result cache |

### Key Concepts

**DEM Processing**:
- Fill/breach depressions → Flow direction → Flow accumulation → Stream extraction
- See [Data Preparation](DATA_PREPARATION.md#step-1-dem-preparation)

**Fairfax Hydrography (current default)**:
- Fairfax County line and polygon water features prepared via new download/prepare scripts
- Optional perennial stream overlay derived from Fairfax open data
- See [Hydrology Data](data/STREAMS.md)

**Topographic Wetness Index** (v1.4.0+):
- Generated via `scripts/compute_twi.py` + `scripts/process_twi_for_tiles.py`
- Blue gradient raster highlights likely saturated areas
- Visible in the Hydrology group alongside stream layers

**Layer Architecture** (v1.2.0+):
- Single source of truth: `frontend/src/lib/config/layers.ts`
- Automatic registration in Map.svelte and LayerPanel.svelte
- See [Configuration](CONFIGURATION.md#layer-configuration)

**PMTiles**:
- Client-side tile rendering with HTTP range requests
- Efficient alternative to tile servers
- See [Tile Generation](tile-generation.md)

## Version Information

### Current Version: 1.7.0

**Release Date**: 2025-12-15

**Key Features**:
- Fairfax County hydrography layers (lines, polygons, perennial streams) downloadable via new scripts
- Feature Info responses simplified to geology, watershed, and DEM context with adjustable buffers
- Documentation refreshed to reflect Fairfax-first hydrology workflow and revised layer groups
- Geology layer fully enabled with colorblind-safe textures and automatic legend display
- Cross-section results enhanced with distance metrics, sample counts, and geology contact totals
- Tile status monitoring via the System Status panel

**See**: [CHANGELOG.md](../CHANGELOG.md) for complete version history and Fairfax dataset milestones

### Recent Changes

- **v1.7.0** (2025-12-15): Fairfax hydrography workflow, streamlined Feature Info responses, docs refresh
- **v1.4.0** (2025-11-02): Documentation refresh and TWI layer release
- **v1.3.0** (2025-11-02): Stadia Maps vector basemaps with feature-rich POI display, water accumulation heatmap
- **v1.2.1** (2025-11-02): Documentation overhaul
- **v1.2.0** (2025-11-01): LAYER_SOURCES centralization refactor
- **v1.1.1** (2025-10-31): Dual stream network support
- **v1.1.0** (2025-10-28): All core layers working, HUC12 boundaries
- **v1.0.0** (2025-10-15): Initial public release

## System Requirements

### Minimum

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB
- **OS**: Ubuntu 20.04+, macOS 12+, or Windows 10+ with WSL2

### Recommended

- **CPU**: 4-8 cores
- **RAM**: 8-16 GB
- **Storage**: 50-100 GB SSD
- **OS**: Ubuntu 22.04 LTS or macOS 14+

### Software

- **Python**: 3.11+
- **Node.js**: 20+
- **GDAL**: 3.4+
- **WhiteboxTools**: Latest
- **Docker**: 24+ (optional)

## Technology Stack

### Backend

- **Framework**: FastAPI (Python)
- **Geospatial**: GDAL, Rasterio, GeoPandas, Shapely
- **Hydrological**: WhiteboxTools (Rust)
- **Server**: Uvicorn / Gunicorn

### Frontend

- **Framework**: SvelteKit (TypeScript)
- **Map**: MapLibre GL JS
- **Tiles**: PMTiles protocol
- **Charts**: Chart.js (cross-sections)
- **Geocoding**: Nominatim (OpenStreetMap)

### Data Formats

- **Raster**: GeoTIFF (DEM, derivatives)
- **Vector**: GeoPackage (streams, watersheds)
- **Tiles**: PMTiles (raster and vector)
- **Cache**: JSON

## Support and Community

### Getting Help

1. **Documentation**: You're in the right place! Use the search or browse topics above.
2. **Troubleshooting**: Check [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues.
3. **GitHub Issues**: Report bugs or request features at https://github.com/HurleySk/hydro-map/issues

### Reporting Issues

When reporting issues, include:
- Environment (OS, Python version, GDAL version)
- Steps to reproduce
- Error messages and logs
- Screenshots (if UI issue)

See [Troubleshooting Guide](TROUBLESHOOTING.md#getting-help) for full template.

### Contributing

Contributions are welcome! Before contributing:
1. Read the [Architecture](ARCHITECTURE.md) to understand the system
2. Review the [Configuration](CONFIGURATION.md) for layer/feature additions
3. Test changes locally following [Quick Start](QUICK_START.md)
4. Submit pull requests with clear descriptions

## License

Hydro-Map is open source software. See LICENSE file in the project root for details.

## Acknowledgments

**Geospatial Tools**:
- [GDAL/OGR](https://gdal.org/) - Geospatial data processing
- [WhiteboxTools](https://www.whiteboxgeo.com/) - Hydrological analysis
- [Tippecanoe](https://github.com/felt/tippecanoe) - Vector tile generation
- [PMTiles](https://github.com/protomaps/PMTiles) - Cloud-native tile format

**Data Sources**:
- [USGS NHD](https://www.usgs.gov/national-hydrography) - National Hydrography Dataset
- [USGS WBD](https://www.usgs.gov/national-hydrography/watershed-boundary-dataset) - Watershed Boundary Dataset
- [OpenTopography](https://opentopography.org/) - High-resolution DEMs
- [OpenStreetMap](https://www.openstreetmap.org/) - Basemap and geocoding

**Frameworks**:
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [SvelteKit](https://kit.svelte.dev/) - Frontend framework
- [MapLibre GL JS](https://maplibre.org/) - Map rendering

## Further Reading

### External Resources

**Hydrological Methods**:
- Jenson & Domingue (1988) - DEM depression filling
- O'Callaghan & Mark (1984) - D8 flow routing
- Strahler (1957) - Stream ordering

**GIS and Web Mapping**:
- [MapLibre Documentation](https://maplibre.org/maplibre-gl-js-docs/)
- [PMTiles Specification](https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md)
- [GDAL Documentation](https://gdal.org/documentation.html)

**Tutorials and Guides**:
- [WhiteboxTools User Manual](https://www.whiteboxgeo.com/manual/wbt_book/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Svelte Tutorial](https://svelte.dev/tutorial)

---

## Documentation Index

### Core Documentation

1. [README.md](../README.md) - Project overview and quick links
2. [CHANGELOG.md](../CHANGELOG.md) - Version history and release notes
3. [QUICK_START.md](QUICK_START.md) - Getting started tutorial
4. [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical overview
5. [UI_GUIDE.md](UI_GUIDE.md) - User interface reference
6. [API.md](API.md) - API endpoint documentation

### Development Documentation

7. [DATA_PREPARATION.md](DATA_PREPARATION.md) - Data processing workflows
8. [tile-generation.md](tile-generation.md) - Tile creation reference
9. [CONFIGURATION.md](CONFIGURATION.md) - Configuration guide
10. [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment

### Support Documentation

11. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
12. [data/STREAMS.md](data/STREAMS.md) - Stream network methodology

### Internal Documentation

13. [.claude/CLAUDE.md](../.claude/CLAUDE.md) - Technical decision log (for developers)

---

**Questions or feedback?** Open an issue at https://github.com/HurleySk/hydro-map/issues

**Last updated**: 2025-12-15 | **Version**: 1.7.0
