# Architecture Overview

**Version**: 1.9.0

Hydro-Map combines a SvelteKit + MapLibre frontend, a FastAPI backend, and an offline data-preparation toolchain. This document outlines how the pieces fit together so you can extend or debug the system confidently.

---

## 1. High-Level System

```
┌─────────────────────────┐
│        Frontend         │
│  SvelteKit (Vite dev)   │
│  MapLibre GL + PMTiles  │
│  Analysis tools & UI    │
└──────────┬──────────────┘
           │ HTTP / JSON
┌──────────▼──────────────┐
│        Backend          │
│   FastAPI (uvicorn)     │
│   Watershed + feature   │
│   info + cross-section  │
└──────────┬──────────────┘
           │ File IO
┌──────────▼──────────────┐
│   Preprocessed Data     │
│   • DEM derivatives     │
│   • Fairfax hydrology   │
│   • Stormwater overlays │
│   • PMTiles             │
└─────────────────────────┘
```

---

## 2. Frontend

- **Framework**: SvelteKit 2.x (Vite dev server)  
- **Mapping**: MapLibre GL JS with the `pmtiles` protocol for client-side tile streaming  
- **State**: Local Svelte stores for map layers, tools, tile status, and UI preferences

### Key modules

| File | Responsibility |
| --- | --- |
| `src/routes/+page.svelte` | App shell; composes map, panels, and tool components |
| `src/lib/config/layers.ts` | Single source of truth for map layer metadata (terrain, Fairfax hydrology, stormwater overlays, geology, reference) |
| `src/lib/stores.ts` | Centralized stores (layer visibility, active tool, cached watersheds, cross sections, tile status, basemap style) |
| `src/lib/components/Map.svelte` | Initialises MapLibre, registers PMTiles sources, draws GeoJSON overlays, orchestrates API calls |
| `src/lib/components/LayerPanel.svelte` | Layer toggles and opacity sliders grouped into Terrain, Hydrology, and Reference categories |
| `src/lib/components/WatershedTool.svelte` | UI for delineation workflow |
| `src/lib/components/CrossSectionTool.svelte` + `CrossSectionChart.svelte` | Line digitising and D3 elevation profiles |
| `src/lib/components/FeatureInfoTool.svelte` / `FeatureInfo.svelte` | Query buffer selection and response formatting |
| `src/lib/components/TileStatusPanel.svelte` | Live PMTiles availability checks |

Basemap selection (`Detailed`, `Minimal`, `Data Only`) is persisted in localStorage via the `basemapStyle` store.

---

## 3. Backend

- **Framework**: FastAPI running under uvicorn (or gunicorn in production)  
- **Modules**: Located in `backend/app/`

### Routes

| Module | Path(s) | Purpose |
| --- | --- | --- |
| `routes/delineate.py` | `POST /api/delineate`, `GET /api/delineate/status` | Pour-point snapping, watershed tracing, caching |
| `routes/cross_section.py` | `POST /api/cross-section` | Elevation/geology sampling along a digitised line |
| `routes/features.py` | `POST /api/feature-info` | Geology, Fairfax datasets, DEM sampling with nearest-feature fallback |
| `routes/tiles.py` | `/tiles/{name}` | Range requests for serving PMTiles files |

### Supporting services

| Module | Highlights |
| --- | --- |
| `services/watershed.py` | D8 watershed tracing, snap-to-stream logic, statistics (area, perimeter, DEM stats) |
| `services/dem_sampling.py` | Single point sampling for elevation, slope, aspect |
| `services/cache.py` | Simple JSON file cache keyed by snapped pour point + parameters |

`Settings` (see `app/config.py`) loads environment variables from `.env`, providing typed defaults for data paths, layer dataset mapping, snap radius, cache directory, and CORS policies.

---

## 4. Data Pipeline

All scripts live under `scripts/` and are meant to be executed from the project root with the backend virtualenv activated.

| Step | Script | Output |
| --- | --- | --- |
| DEM cleanup & derivatives | `prepare_dem.py` | Filled DEM, flow direction/accumulation, hillshade, slope, aspect, slope/aspect degrees |
| Fairfax hydrography | `download_fairfax_hydro.py` → `prepare_fairfax_hydro.py` | Lines, polygons, perennial streams, Fairfax watersheds GeoPackages |
| Fairfax stormwater overlays | `download_fairfax_stormwater.py` → `prepare_fairfax_stormwater.py` | Floodplain easements, inadequate outfalls (polygons & points) |
| Optional TWI | `compute_twi.py` → `process_twi_for_tiles.py` | TWI raster ready for tiling |
| Optional geology | `prepare_geology.py` | Normalised geology GeoPackage |
| Tile creation | `generate_tiles.py` | Raster + vector PMTiles stored in `data/tiles/` |

The backend accesses GeoPackages (`../data/processed/...`) and rasters on demand; the frontend streams PMTiles through `/tiles/*`.

---

## 5. Data Layout

```
hydro-map/
├── data/
│   ├── raw/                # Downloads (unchanged)
│   ├── processed/          # Normalised GeoPackages & rasters
│   └── tiles/              # Published PMTiles served by FastAPI
├── backend/
│   └── app/                # FastAPI application
└── frontend/
    └── src/lib/            # Layer config and UI components
```

Key processed artifacts:

- `data/processed/dem/` – primary rasters consumed by both backend and tile generation
- `data/processed/fairfax_*` – county hydrography and stormwater datasets
- `data/processed/geology.gpkg` – optional geology polygons
- `data/tiles/*.pmtiles` – assets consumed directly by MapLibre

---

## 6. Request Flow Examples

1. **Watershed delineation**
   - UI toggles “Delineate Watershed” → user clicks map  
   - Frontend posts to `POST /api/delineate` with coords + snap settings  
   - Backend snaps the point (if enabled), checks cache, computes watershed using flow direction, and returns GeoJSON + statistics  
   - Frontend renders the polygon and updates the results panel

2. **Feature info lookup**
   - UI sets buffer radius, posts to `/api/feature-info`  
   - Backend consults `LAYER_DATASET_MAP`, runs spatial queries (with a nearest fallback), samples DEM rasters, and merges warnings  
   - Frontend displays structured results; geology legend still appears even when the geology layer is hidden

3. **PMTiles streaming**
   - MapLibre requests `/tiles/{name}.pmtiles` with range headers  
   - FastAPI stream returns bytes from `data/tiles/`; Tile Status panel reports availability

---

## 7. Extending the System

- **Add a new dataset**: generate a GeoPackage/PMTiles, add it to `LAYER_SOURCES`, serve the PMTiles (via `generate_tiles.py` or your own pipeline), and extend `LAYER_DATASET_MAP` if Feature Info should query it.
- **Change the area of interest**: adjust download scripts, rerun preprocessing, and update default map view (`DEFAULT_MAP_VIEW` in `stores.ts`).
- **Deploy to production**: build the SvelteKit app (`npm run build`), serve it behind a reverse proxy, and run the FastAPI app under gunicorn/uvicorn. See [DEPLOYMENT.md](DEPLOYMENT.md) for patterns.

Keep the documentation and layer configuration in sync whenever you add or remove features so both the UI and API remain consistent.
