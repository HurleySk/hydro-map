#!/usr/bin/env python3
"""
Generate PMTiles from processed raster and vector data.

This script uses external tools (gdal2tiles, tippecanoe) to create PMTiles
for client-side rendering with MapLibre GL JS.

Prerequisites:
    - GDAL (gdal2tiles.py, gdal_translate)
    - Tippecanoe (for vector tiles)
    - pmtiles CLI (for PMTiles conversion)

Usage:
    python generate_tiles.py --data-dir data/processed --output-dir data/tiles
"""

import click
from pathlib import Path
import subprocess
import json
from tqdm import tqdm


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
    default=14,
    help='Maximum zoom level'
)
def main(data_dir, output_dir, min_zoom, max_zoom):
    """Generate PMTiles from processed data."""

    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo("Generating tiles...")
    click.echo(f"Data directory: {data_path}")
    click.echo(f"Output directory: {output_path}")
    click.echo(f"Zoom levels: {min_zoom}-{max_zoom}")

    # Raster tiles (hillshade, slope, aspect)
    raster_files = {
        'hillshade': data_path / 'dem' / 'hillshade.tif',
        'slope': data_path / 'dem' / 'slope.tif',
        'aspect': data_path / 'dem' / 'aspect.tif',
    }

    for name, raster_file in raster_files.items():
        if raster_file.exists():
            click.echo(f"\nProcessing {name}...")
            generate_raster_pmtiles(
                raster_file,
                output_path / f"{name}.pmtiles",
                min_zoom,
                max_zoom
            )
        else:
            click.echo(f"Warning: {name} not found at {raster_file}")

    # Vector tiles (streams, geology)
    vector_files = {
        'streams': data_path / 'streams.gpkg',
        'geology': data_path / 'geology.gpkg',
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


def generate_raster_pmtiles(input_file: Path, output_file: Path, min_zoom: int, max_zoom: int):
    """Generate PMTiles from raster data."""

    temp_dir = output_file.parent / 'temp_tiles'
    temp_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Convert to web-friendly format (8-bit, LZW)
        temp_tif = temp_dir / f"{input_file.stem}_web.tif"
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
        click.echo(f"  Generating XYZ tiles (zoom {min_zoom}-{max_zoom})...")

        subprocess.run([
            'gdal2tiles.py',
            '--zoom', f'{min_zoom}-{max_zoom}',
            '--processes', '4',
            '--webviewer', 'none',
            '-r', 'bilinear',
            str(temp_tif),
            str(xyz_dir)
        ], check=True, capture_output=True)

        # Step 3: Convert to PMTiles (requires pmtiles CLI)
        click.echo(f"  Converting to PMTiles...")

        subprocess.run([
            'pmtiles',
            'convert',
            str(xyz_dir),
            str(output_file)
        ], check=True, capture_output=True)

        click.echo(f"  Created {output_file}")

        # Clean up temporary files
        import shutil
        if temp_tif.exists():
            temp_tif.unlink()
        if xyz_dir.exists():
            shutil.rmtree(xyz_dir)

    except subprocess.CalledProcessError as e:
        click.echo(f"  Error: {e}")
    except FileNotFoundError:
        click.echo(f"  Error: Required tool not found (gdal_translate, gdal2tiles.py, or pmtiles)")
        click.echo(f"  Install GDAL: https://gdal.org/")
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
        if input_file.suffix == '.gpkg':
            temp_geojson = output_file.parent / f"{input_file.stem}.geojson"
            subprocess.run([
                'ogr2ogr',
                '-f', 'GeoJSON',
                str(temp_geojson),
                str(input_file)
            ], check=True, capture_output=True)
            input_for_tippecanoe = temp_geojson
        else:
            input_for_tippecanoe = input_file

        # Run Tippecanoe
        subprocess.run([
            'tippecanoe',
            '-o', str(temp_mbtiles),
            '-l', layer_name,
            '-z', str(max_zoom),
            '-Z', str(min_zoom),
            '--drop-densest-as-needed',
            '--extend-zooms-if-still-dropping',
            str(input_for_tippecanoe)
        ], check=True, capture_output=True)

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
