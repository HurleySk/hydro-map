#!/usr/bin/env python3
"""
Extract and prepare stream network from flow accumulation.

This script:
1. Extracts stream network from flow accumulation threshold
2. Computes stream order (Strahler)
3. Calculates stream attributes
4. Exports to GeoPackage

Usage:
    python prepare_streams.py --flow-acc data/processed/dem/flow_accumulation.tif \\
                               --flow-dir data/processed/dem/flow_direction.tif \\
                               --output data/processed/streams.gpkg \\
                               --threshold 1000
"""

import click
from pathlib import Path
import whitebox
from tqdm import tqdm


@click.command()
@click.option(
    '--flow-acc', '-a',
    type=click.Path(exists=True),
    required=True,
    help='Flow accumulation raster'
)
@click.option(
    '--flow-dir', '-d',
    type=click.Path(exists=True),
    required=True,
    help='Flow direction raster (D8)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output GeoPackage file'
)
@click.option(
    '--threshold', '-t',
    type=int,
    default=1000,
    help='Flow accumulation threshold for stream initiation (cells)'
)
@click.option(
    '--dem',
    type=click.Path(exists=True),
    help='Optional DEM for stream attributes'
)
def main(flow_acc, flow_dir, output, threshold, dem):
    """Extract stream network from flow accumulation."""

    wbt = whitebox.WhiteboxTools()
    wbt.set_verbose_mode(False)

    flow_acc_path = Path(flow_acc)
    flow_dir_path = Path(flow_dir)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Temporary files
    temp_dir = output_path.parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    streams_raster = temp_dir / "streams.tif"
    streams_vector = temp_dir / "streams_raw.shp"

    click.echo(f"Extracting streams with threshold: {threshold} cells")

    with tqdm(total=3, desc="Stream extraction") as pbar:
        # Step 1: Extract streams from flow accumulation
        pbar.set_description("Extracting stream network")
        wbt.extract_streams(
            flow_accum=str(flow_acc_path),
            output=str(streams_raster),
            threshold=threshold
        )
        pbar.update(1)

        # Step 2: Compute stream order
        pbar.set_description("Computing stream order")
        stream_order = temp_dir / "stream_order.tif"
        wbt.strahler_stream_order(
            d8_pntr=str(flow_dir_path),
            streams=str(streams_raster),
            output=str(stream_order)
        )
        pbar.update(1)

        # Step 3: Vectorize streams
        pbar.set_description("Vectorizing streams")
        wbt.raster_streams_to_vector(
            streams=str(streams_raster),
            d8_pntr=str(flow_dir_path),
            output=str(streams_vector)
        )
        pbar.update(1)

    # Convert to GeoPackage with geopandas
    click.echo("Converting to GeoPackage...")
    try:
        import geopandas as gpd

        streams_gdf = gpd.read_file(streams_vector)

        # Add stream order by sampling the raster
        # (This is a simplified version - you might want more sophisticated attribution)
        streams_gdf['order'] = 1  # Placeholder

        # Calculate length
        streams_gdf_proj = streams_gdf.to_crs("EPSG:6933")  # Equal Earth
        streams_gdf['length_m'] = streams_gdf_proj.geometry.length
        streams_gdf['length_km'] = streams_gdf['length_m'] / 1000

        # Save to GeoPackage
        streams_gdf.to_file(output_path, driver='GPKG', layer='streams')

        click.echo(f"\nStream extraction complete!")
        click.echo(f"  Output: {output_path}")
        click.echo(f"  Number of stream segments: {len(streams_gdf)}")
        click.echo(f"  Total length: {streams_gdf['length_km'].sum():.2f} km")

    except ImportError:
        click.echo("Warning: geopandas not available, saving as shapefile only")
        click.echo(f"  Output: {streams_vector}")

    # Clean up temp files (optional)
    # import shutil
    # shutil.rmtree(temp_dir)


if __name__ == '__main__':
    main()
