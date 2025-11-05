# Data Preparation Guide

**Version**: 1.9.0

This guide walks through the end-to-end workflow for preparing data that Hydro-Map expects at runtime. Use it alongside the [Quick Start](QUICK_START.md), which covers environment setup and application launch.

## Prerequisites

- Python 3.12+, Node 20+, GDAL, Tippecanoe, PMTiles CLI (`pmtiles`), and mb-util (installed in the backend virtualenv)
- Backend virtualenv activated when running the scripts (`cd backend && source venv/bin/activate`)
- Input DEM stored at `data/raw/dem/elevation.tif` (customize paths if desired)

> Run `python scripts/generate_tiles.py --check-tools` to confirm required command-line tools are available before starting.

## Workflow Overview

1. Acquire a DEM covering your project area
2. Run `prepare_dem.py` to generate hydrologic derivatives
3. Download and normalize Fairfax County hydrography
4. Download and normalize Fairfax stormwater and flood-risk overlays
5. (Optional) Add supplementary datasets such as TWI, geology, or custom streams
6. Generate PMTiles with `generate_tiles.py`
7. Verify outputs before launching the app

Each step is described below.

---

## Step 1 – Acquire DEM Data

Hydro-Map works with any single-band elevation raster. Recommended sources:

- **USGS 3DEP 1/3″ (10 m)** – Best for continental US. Download from the [USGS National Map Downloader](https://apps.nationalmap.gov/downloader/).
- **Copernicus GLO-30 (30 m)** – Global coverage via [OpenTopography](https://portal.opentopography.org/).
- **SRTM 1 arc-second (30 m)** – Global between 60° N and 56° S via [USGS EarthExplorer](https://earthexplorer.usgs.gov/).

Tips:

- Clip or mosaic tiles so a single GeoTIFF lives at `data/raw/dem/elevation.tif`.
- Buffer the download by ~1–2 km beyond your area of interest to avoid edge effects.

---

## Step 2 – Process the DEM

```bash
python scripts/prepare_dem.py \
  --input data/raw/dem/elevation.tif \
  --output data/processed/dem/ \
  --breach  # switch to --fill if you prefer depression filling
```

Key outputs inside `data/processed/dem/`:

| File | Purpose |
| --- | --- |
| `filled_dem.tif` | Depression-corrected DEM used by the delineation service |
| `flow_direction.tif` / `flow_accumulation.tif` | D8 routing grids needed for snapping & watershed tracing |
| `hillshade.tif`, `slope.tif`, `aspect.tif` | 8-bit rasters ready for tiling |
| `slope_deg.tif`, `aspect_deg.tif` | Float rasters sampled by the Feature Info endpoint |

The script also creates a 1 m UTM reprojection to improve slope/aspect quality. Rerun the command any time you update the source DEM.

---

## Step 3 – Fairfax Hydrography

Download the Fairfax County open-data hydrography bundle (streams, water bodies, perennial network, and local watersheds):

```bash
python scripts/download_fairfax_hydro.py
python scripts/prepare_fairfax_hydro.py
```

Outputs in `data/processed/`:

- `fairfax_water_lines.gpkg`
- `fairfax_water_polys.gpkg`
- `perennial_streams.gpkg`
- `fairfax_watersheds.gpkg`

Each dataset is normalized to consistent field names, area/length metrics, and EPSG:4326 coordinates. Adjust the AOI or data URLs inside the scripts if you are targeting another county.

---

## Step 4 – Fairfax Stormwater & Flood Risk Layers

The v1.9 release adds optional municipal overlays used by the default UI.

```bash
python scripts/download_fairfax_stormwater.py
python scripts/prepare_fairfax_stormwater.py
```

Outputs in `data/processed/`:

- `floodplain_easements.gpkg`
- `inadequate_outfalls.gpkg`
- `inadequate_outfall_points.gpkg`

These layers feed the Hydrology panel toggles `Floodplain Easements`, `Inadequate Outfalls`, and `Inadequate Outfall Points`. If you skip this step, remove or hide the corresponding layers in `frontend/src/lib/config/layers.ts`.

---

## Step 5 – Optional Enhancements

- **Topographic Wetness Index (TWI)**  
  ```bash
  python scripts/compute_twi.py --output data/processed/dem/twi.tif
  python scripts/process_twi_for_tiles.py
  ```
  Outputs `data/processed/dem/twi_8bit.tif` consumed by `generate_tiles.py`.

- **Geology**  
  If you have geology polygons, place them at `data/raw/geology.*` and run `python scripts/prepare_geology.py`. The script emits `data/processed/geology.gpkg`.

- **Custom or Legacy Streams**  
  See [docs/data/STREAMS.md](data/STREAMS.md) for the DEM-derived/NHD workflow retained for compatibility.

- **HUC12 or other reference boundaries**  
  If you still need USGS HUC12s, run `python scripts/process_huc.py` before tile generation.

---

## Step 6 – Generate PMTiles

`generate_tiles.py` inspects `data/processed/` and produces PMTiles under `data/tiles/`.

```bash
python scripts/generate_tiles.py \
  --data-dir data/processed \
  --output-dir data/tiles \
  --min-zoom 8 \
  --max-zoom 17 \
  --contour-interval 10
```

What it creates (when inputs exist):

- Raster PMTiles: `hillshade.pmtiles`, `slope.pmtiles`, `aspect.pmtiles`, and optional `twi.pmtiles`
- Vector PMTiles: `contours.pmtiles`, `fairfax_water_lines.pmtiles`, `fairfax_water_polys.pmtiles`, `perennial_streams.pmtiles`, `fairfax_watersheds.pmtiles`, `floodplain_easements.pmtiles`, `inadequate_outfalls.pmtiles`, `inadequate_outfall_points.pmtiles`, plus any optional geology/streams layers

Additional presets:

| Use case | Command adjustments |
| --- | --- |
| Faster previews | `--max-zoom 14 --contour-interval 20` |
| Large-region overview | `--min-zoom 6 --max-zoom 12` |
| High-res lidar (≤3 m) | Increase `--max-zoom` to 18 |

Tip: rerun the script whenever you update processed data. Existing PMTiles are overwritten.

---

## Step 7 – Verify Outputs

```bash
ls data/processed/dem/
ls data/processed/fairfax_*.gpkg data/processed/perennial_streams.gpkg
ls data/processed/floodplain_*.gpkg data/processed/inadequate_outfall*.gpkg
ls data/tiles/*.pmtiles
pmtiles show data/tiles/hillshade.pmtiles | head  # confirms metadata
```

If a dataset is missing, revisit the relevant step. The backend `/api/delineate/status` endpoint and frontend Tile Status panel are useful sanity checks once the app is running.

---

## Next Steps

After the data pipeline finishes:

1. Copy `.env.example` → `.env` and point the backend to your processed data paths if they differ from defaults.
2. Start the backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev -- --host`).
3. Use the Tile Status panel to confirm PMTiles coverage, then explore the hydrology and stormwater layers in the UI.
