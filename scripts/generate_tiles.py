#!/usr/bin/env python3
"""
Generate PMTiles from processed raster and vector data.

This script uses external tools (gdal2tiles, tippecanoe, mb-util) to create PMTiles
for client-side rendering with MapLibre GL JS.

Prerequisites:
    - GDAL (gdal2tiles.py, gdal_translate)
    - Tippecanoe (for vector tiles)
    - mb-util (for converting XYZ to MBTiles)
    - pmtiles CLI (for PMTiles conversion)

Usage:
    python generate_tiles.py --data-dir data/processed --output-dir data/tiles
"""

import click
from pathlib import Path
import subprocess
import json
import sys
from tqdm import tqdm

# Add path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from lib.tools import ensure_tools_available, RASTER_TOOLS, VECTOR_TOOLS, PMTILES_TOOLS


@click.command()
@click.option(
    '--data-dir', '-d',
    type=click.Path(exists=True),
    required=True,
    help='Directory with processed data'
)
@click.option(
    '--output-dir', '-o',
    type=click.Path(),
    required=True,
    help='Output directory for tiles'
)
@click.option(
    '--min-zoom',
    type=int,
    default=8,
    help='Minimum zoom level'
)
@click.option(
    '--max-zoom',
    type=int,
    default=19,
    help='Maximum zoom level (default: 19 for 1m DEM)'
)
@click.option(
    '--tile-size',
    type=int,
    default=512,
    help='Tile size in pixels (default: 512)'
)
@click.option(
    '--contour-interval',
    type=int,
    default=1,
    help='Contour interval in meters (default: 1)'
)
@click.option(
    '--raster-resampling',
    type=click.Choice(['nearest', 'bilinear', 'cubic', 'lanczos'], case_sensitive=False),
    default='cubic',
    help='Resampling kernel for raster tiles (default: cubic)'
)
@click.option(
    '--check-tools',
    is_flag=True,
    help='Check required tools and exit'
)
def main(data_dir, output_dir, min_zoom, max_zoom, tile_size, contour_interval, raster_resampling, check_tools):
    """Generate PMTiles from processed data."""

    # Define all required tools
    required_tools = [
        'gdal2tiles.py',
        'gdal_translate',
        'gdal_contour',
        'gdaldem',
        'tippecanoe',
        'mb-util',
        'pmtiles',
        'ogr2ogr'
    ]

    # Check tools if requested or validate before running
    if check_tools:
        click.echo("Checking required tools...")
        success = ensure_tools_available(required_tools, exit_on_missing=False, verbose=True)
        sys.exit(0 if success else 1)
    else:
        # Validate tools are available before starting
        click.echo("Validating required tools...")
        ensure_tools_available(required_tools, exit_on_missing=True, verbose=False)

    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo("\nGenerating tiles...")
    click.echo(f"Data directory: {data_path}")
    click.echo(f"Output directory: {output_path}")
    click.echo(f"Zoom levels: {min_zoom}-{max_zoom}")
    click.echo(f"Tile size: {tile_size}px")
    click.echo(f"Raster resampling: {raster_resampling}")

    # Raster tiles (hillshade, slope, aspect)
    raster_files = {
        'hillshade': data_path / 'dem' / 'hillshade.tif',
        'slope': data_path / 'dem' / 'slope.tif',
        'aspect': data_path / 'dem' / 'aspect.tif',
    }

    for name, raster_file in raster_files.items():
        if raster_file.exists():
            click.echo(f"\nProcessing {name}...")
            # Use nearest for aspect (color-relief) to avoid blending colors
            effective_resampling = raster_resampling
            if name == 'aspect' and raster_resampling.lower() in ['lanczos', 'cubic', 'bilinear']:
                click.echo("  Aspect is color-relief categorical; overriding resampling to 'nearest' for clean color boundaries")
                effective_resampling = 'nearest'

            generate_raster_pmtiles(
                raster_file,
                output_path / f"{name}.pmtiles",
                min_zoom,
                max_zoom,
                tile_size,
                effective_resampling
            )
        else:
            click.echo(f"Warning: {name} not found at {raster_file}")

    # Generate contours from filled DEM
    filled_dem = data_path / 'dem' / 'filled_dem.tif'
    contours_gpkg = data_path / 'contours.gpkg'

    if filled_dem.exists():
        click.echo(f"\nGenerating contours (interval: {contour_interval}m)...")
        try:
            subprocess.run([
                'gdal_contour',
                '-a', 'elevation',
                '-i', str(contour_interval),
                str(filled_dem),
                str(contours_gpkg)
            ], check=True, capture_output=True)
            click.echo(f"  Created {contours_gpkg}")
        except subprocess.CalledProcessError as e:
            click.echo(f"  Error generating contours: {e}")
        except FileNotFoundError:
            click.echo(f"  Error: gdal_contour not found. Install GDAL.")
    else:
        click.echo(f"\nWarning: Filled DEM not found at {filled_dem}, skipping contours")

    # Vector tiles (streams, geology, contours, fairfax hydrology, fairfax watersheds, fairfax stormwater)
    vector_files = {
        'streams': data_path / 'streams.gpkg',
        'geology': data_path / 'geology.gpkg',
        'contours': contours_gpkg,
        'fairfax_water_lines': data_path / 'fairfax_water_lines.gpkg',
        'fairfax_water_polys': data_path / 'fairfax_water_polys.gpkg',
        'perennial_streams': data_path / 'perennial_streams.gpkg',
        'fairfax_watersheds': data_path / 'fairfax_watersheds.gpkg',
        'floodplain_easements': data_path / 'floodplain_easements.gpkg',
        'inadequate_outfalls': data_path / 'inadequate_outfalls.gpkg',
        'inadequate_outfall_points': data_path / 'inadequate_outfall_points.gpkg',
    }

    for name, vector_file in vector_files.items():
        if vector_file.exists():
            click.echo(f"\nProcessing {name}...")
            generate_vector_pmtiles(
                vector_file,
                output_path / f"{name}.pmtiles",
                min_zoom,
                max_zoom,
                layer_name=name
            )
        else:
            click.echo(f"Warning: {name} not found at {vector_file}")

    click.echo("\nTile generation complete!")


def generate_raster_pmtiles(input_file: Path, output_file: Path, min_zoom: int, max_zoom: int, tile_size: int, raster_resampling: str):
    """Generate PMTiles from raster data."""

    temp_dir = output_file.parent / 'temp_tiles'
    temp_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Convert to web-friendly format if needed
        # Hillshade, slope, and aspect are already prepared by prepare_dem.py
        # Hillshade: Byte, 0-255 (multi-directional)
        # Slope: Byte, 0-255 (scaled 0-45 degrees)
        # Aspect: RGB color-relief (no conversion needed)

        temp_tif = temp_dir / f"{input_file.stem}_web.tif"

        # Check if aspect is color-relief (RGB) - skip conversion
        if 'aspect' in input_file.stem:
            # Aspect is color-relief RGB from prepare_dem.py, use directly
            click.echo(f"  Using color-relief aspect (RGB) directly...")
            temp_tif = input_file  # Use original file
        elif 'hillshade' in input_file.stem or 'slope' in input_file.stem:
            # Hillshade and slope are already Byte from prepare_dem.py
            # Just ensure proper tiling and compression
            click.echo(f"  Optimizing for tiling...")
            subprocess.run([
                'gdal_translate',
                '-of', 'GTiff',
                '-co', 'TILED=YES',
                '-co', 'COMPRESS=LZW',
                '-ot', 'Byte',
                str(input_file),
                str(temp_tif)
            ], check=True, capture_output=True)
        else:
            # Fallback for other rasters (legacy support)
            click.echo(f"  Converting to web format...")
            subprocess.run([
                'gdal_translate',
                '-of', 'GTiff',
                '-co', 'TILED=YES',
                '-co', 'COMPRESS=LZW',
                '-scale',
                '-ot', 'Byte',
                str(input_file),
                str(temp_tif)
            ], check=True, capture_output=True)

        # Step 2: Generate XYZ tiles
        xyz_dir = temp_dir / f"{input_file.stem}_xyz"
        click.echo(f"  Generating XYZ tiles (zoom {min_zoom}-{max_zoom}, {tile_size}px)...")

        # Map 'nearest' to 'near' for gdal2tiles.py compatibility
        gdal2tiles_resampling = 'near' if raster_resampling == 'nearest' else raster_resampling

        subprocess.run([
            'gdal2tiles.py',
            '--xyz',  # Use XYZ tile numbering (OSM Slippy Map) instead of TMS
            '--zoom', f'{min_zoom}-{max_zoom}',
            '--tilesize', str(tile_size),
            '--processes', '4',
            '--webviewer', 'none',
            '-r', gdal2tiles_resampling,
            str(temp_tif),
            str(xyz_dir)
        ], check=True, capture_output=True)

        # Step 3: Convert XYZ to MBTiles (requires mb-util)
        click.echo(f"  Converting to MBTiles...")
        temp_mbtiles = temp_dir / f"{input_file.stem}.mbtiles"

        subprocess.run([
            'mb-util',
            str(xyz_dir),
            str(temp_mbtiles)
        ], check=True, capture_output=True)

        # Step 3.5: Fix MBTiles metadata (mb-util doesn't set format/tile_type)
        click.echo(f"  Fixing MBTiles metadata...")
        import sqlite3
        conn = sqlite3.connect(str(temp_mbtiles))
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES ('format', 'png')")
        cursor.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES ('type', 'overlay')")
        conn.commit()
        conn.close()

        # Step 4: Convert MBTiles to PMTiles (requires pmtiles CLI)
        click.echo(f"  Converting to PMTiles...")

        subprocess.run([
            'pmtiles',
            'convert',
            str(temp_mbtiles),
            str(output_file)
        ], check=True, capture_output=True)

        click.echo(f"  Created {output_file}")

        # Clean up temporary files
        import shutil
        if temp_tif.exists() and temp_tif != input_file:
            temp_tif.unlink()
        if temp_mbtiles.exists():
            temp_mbtiles.unlink()
        if xyz_dir.exists():
            shutil.rmtree(xyz_dir)

    except subprocess.CalledProcessError as e:
        click.echo(f"  Error: {e}")
    except FileNotFoundError:
        click.echo(f"  Error: Required tool not found (gdal_translate, gdal2tiles.py, mb-util, or pmtiles)")
        click.echo(f"  Install GDAL: https://gdal.org/")
        click.echo(f"  Install mb-util: https://github.com/mapbox/mbutil")
        click.echo(f"  Install pmtiles: https://github.com/protomaps/go-pmtiles")


def generate_vector_pmtiles(
    input_file: Path,
    output_file: Path,
    min_zoom: int,
    max_zoom: int,
    layer_name: str
):
    """Generate PMTiles from vector data using Tippecanoe."""

    temp_mbtiles = output_file.with_suffix('.mbtiles')

    try:
        click.echo(f"  Generating vector tiles with Tippecanoe...")

        # Convert to GeoJSON if needed
        source_layer = layer_name
        if input_file.suffix == '.gpkg':
            # For streams, try to find the best available layer
            if layer_name == 'streams':
                # Priority order for pure DEM workflow:
                # 1. streams_t100_filtered (finest threshold, filtered)
                # 2. streams_t250_filtered (medium threshold, filtered)
                # 3. streams_merged (if from NHD fusion workflow)
                # 4. streams (fallback)
                candidates = ['streams_t100_filtered', 'streams_t250_filtered', 'streams_merged', 'streams']
                for candidate in candidates:
                    try:
                        subprocess.run(
                            ['ogrinfo', str(input_file), candidate],
                            check=True,
                            capture_output=True
                        )
                        source_layer = candidate
                        click.echo(f"  Using layer: {source_layer}")
                        break
                    except subprocess.CalledProcessError:
                        continue

            temp_geojson = output_file.parent / f"{input_file.stem}.geojson"
            subprocess.run([
                'ogr2ogr',
                '-f', 'GeoJSON',
                str(temp_geojson),
                str(input_file),
                source_layer  # Specify which layer to export from GPKG
            ], check=True, capture_output=True)
            input_for_tippecanoe = temp_geojson
        else:
            input_for_tippecanoe = input_file

        # Run Tippecanoe with better detail preservation for streams
        tippecanoe_cmd = [
            'tippecanoe',
            '-o', str(temp_mbtiles),
            '-l', layer_name,
            '-z', str(max_zoom),
            '-Z', str(min_zoom),
            '--no-tile-size-limit'
        ]

        # Add special parameters for stream layers to preserve detail
        if layer_name == 'streams':
            tippecanoe_cmd.extend([
                '--no-feature-limit',     # Keep all features
                '--simplification', '2',   # Minimal simplification (lower = more detail)
                '--minimum-detail', '12',  # Preserve detail at lower zooms
                '--no-line-simplification', # Disable line simplification
                '--no-tiny-polygon-reduction' # Keep small features
            ])
        else:
            # For other layers, use standard simplification
            tippecanoe_cmd.extend([
                '--no-feature-limit'
            ])

        tippecanoe_cmd.append(str(input_for_tippecanoe))

        subprocess.run(tippecanoe_cmd, check=True, capture_output=True)

        # Convert to PMTiles (requires pmtiles CLI)
        click.echo(f"  Converting to PMTiles...")
        subprocess.run([
            'pmtiles',
            'convert',
            str(temp_mbtiles),
            str(output_file)
        ], check=True, capture_output=True)

        click.echo(f"  Created {output_file}")

        # Clean up
        if temp_mbtiles.exists():
            temp_mbtiles.unlink()
        if input_for_tippecanoe != input_file:
            input_for_tippecanoe.unlink()

    except subprocess.CalledProcessError as e:
        click.echo(f"  Error: {e}")
    except FileNotFoundError as e:
        click.echo(f"  Error: Required tool not found (tippecanoe or pmtiles)")
        click.echo(f"  Install Tippecanoe: https://github.com/felt/tippecanoe")
        click.echo(f"  Install pmtiles: https://github.com/protomaps/go-pmtiles")


if __name__ == '__main__':
    main()
