#!/usr/bin/env python3
"""
Prepare DEM for watershed delineation.

This script:
1. Fills sinks/depressions in the DEM
2. Computes D8 flow direction
3. Computes flow accumulation
4. Reprojects DEM to UTM for accurate terrain derivatives
5. Generates derived terrain products (hillshade, slope, aspect) using GDAL

Usage:
    python prepare_dem.py --input data/raw/dem/elevation.tif --output data/processed/dem/
"""

import click
from pathlib import Path
import whitebox
from tqdm import tqdm
import subprocess
import sys


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True),
    required=True,
    help='Input DEM file (GeoTIFF)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output directory for processed files'
)
@click.option(
    '--breach/--fill',
    default=True,
    help='Use breaching (default) or filling for depression removal'
)
@click.option(
    '--utm-zone',
    type=int,
    default=18,
    help='UTM zone for terrain derivative computation (default: 18 for DC area)'
)
@click.option(
    '--hemisphere',
    type=click.Choice(['N', 'S']),
    default='N',
    help='Hemisphere for UTM zone (N or S, default: N)'
)
def main(input, output, breach, utm_zone, hemisphere):
    """Prepare DEM for hydrological analysis."""

    wbt = whitebox.WhiteboxTools()
    wbt.set_verbose_mode(True)

    input_path = Path(input)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Processing DEM: {input_path.name}")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"UTM Zone: {utm_zone}{hemisphere}")

    # Output files
    filled_dem = output_dir / "filled_dem.tif"
    dem_utm = output_dir / "dem_utm_1m.tif"
    flow_dir = output_dir / "flow_direction.tif"
    flow_acc = output_dir / "flow_accumulation.tif"
    hillshade = output_dir / "hillshade.tif"
    slope_deg = output_dir / "slope_deg.tif"
    slope = output_dir / "slope.tif"
    aspect_deg = output_dir / "aspect_deg.tif"
    aspect = output_dir / "aspect.tif"

    # UTM EPSG code (e.g., 32618 for UTM 18N, 32718 for UTM 18S)
    utm_epsg = 32600 + utm_zone if hemisphere == 'N' else 32700 + utm_zone

    # Color ramp file for aspect
    aspect_colors = Path(__file__).parent / "color_ramps" / "aspect.txt"
    if not aspect_colors.exists():
        click.echo(f"Warning: Aspect color ramp not found at {aspect_colors}", err=True)
        sys.exit(1)

    with tqdm(total=10, desc="DEM processing") as pbar:
        # Step 1: Fill sinks or breach depressions
        pbar.set_description("Removing depressions")
        if breach:
            click.echo("Using breach depressions method...")
            wbt.breach_depressions_least_cost(
                dem=str(input_path),
                output=str(filled_dem),
                dist=5,
                fill=True
            )
        else:
            click.echo("Using fill depressions method...")
            wbt.fill_depressions_wang_and_liu(
                dem=str(input_path),
                output=str(filled_dem)
            )
        pbar.update(1)

        # Step 2: D8 flow direction
        pbar.set_description("Computing flow direction")
        wbt.d8_pointer(
            dem=str(filled_dem),
            output=str(flow_dir)
        )
        pbar.update(1)

        # Step 3: Flow accumulation
        pbar.set_description("Computing flow accumulation")
        wbt.d8_flow_accumulation(
            i=str(flow_dir),
            output=str(flow_acc),
            out_type="cells"
        )
        pbar.update(1)

        # Step 4: Reproject DEM to UTM for accurate terrain derivatives
        pbar.set_description("Reprojecting to UTM")
        click.echo(f"\nReprojecting to EPSG:{utm_epsg}...")
        subprocess.run([
            'gdalwarp',
            '-t_srs', f'EPSG:{utm_epsg}',
            '-tr', '1', '1',
            '-r', 'cubic',
            '-co', 'COMPRESS=LZW',
            '-co', 'TILED=YES',
            '-co', 'BIGTIFF=IF_SAFER',
            str(filled_dem),
            str(dem_utm)
        ], check=True)
        pbar.update(1)

        # Step 5: Multi-directional hillshade (GDAL)
        pbar.set_description("Generating multi-directional hillshade")
        click.echo("\nGenerating multi-directional hillshade...")
        subprocess.run([
            'gdaldem', 'hillshade',
            '-multidirectional',
            '-az', '315',
            '-alt', '45',
            '-co', 'COMPRESS=LZW',
            str(dem_utm),
            str(hillshade)
        ], check=True)
        pbar.update(1)

        # Step 6: Slope in degrees (GDAL)
        pbar.set_description("Computing slope")
        click.echo("\nComputing slope...")
        subprocess.run([
            'gdaldem', 'slope',
            '-s', '1.0',
            '-co', 'COMPRESS=LZW',
            str(dem_utm),
            str(slope_deg)
        ], check=True)
        pbar.update(1)

        # Step 7: Convert slope to 8-bit with percentile scaling
        pbar.set_description("Scaling slope to 8-bit")
        # Use 0-45 degree range (physical limit for most terrain)
        subprocess.run([
            'gdal_translate',
            '-scale', '0', '45', '0', '255',
            '-ot', 'Byte',
            '-co', 'COMPRESS=LZW',
            str(slope_deg),
            str(slope)
        ], check=True)
        pbar.update(1)

        # Step 8: Aspect in degrees (GDAL)
        pbar.set_description("Computing aspect")
        click.echo("\nComputing aspect...")
        subprocess.run([
            'gdaldem', 'aspect',
            '-co', 'COMPRESS=LZW',
            str(dem_utm),
            str(aspect_deg)
        ], check=True)
        pbar.update(1)

        # Step 9: Apply color-relief to aspect
        pbar.set_description("Applying aspect color ramp")
        click.echo("\nApplying aspect color ramp...")
        subprocess.run([
            'gdaldem', 'color-relief',
            '-alpha',
            '-co', 'COMPRESS=LZW',
            str(aspect_deg),
            str(aspect_colors),
            str(aspect)
        ], check=True)
        pbar.update(1)

        # Step 10: Cleanup intermediate files
        pbar.set_description("Cleaning up")
        # Keep slope_deg and aspect_deg for reference, but could delete if needed
        pbar.update(1)

    click.echo("\nDEM processing complete!")
    click.echo(f"\nGenerated files:")
    click.echo(f"\nHydrological products (EPSG:4326):")
    click.echo(f"  - Filled DEM: {filled_dem}")
    click.echo(f"  - Flow direction: {flow_dir}")
    click.echo(f"  - Flow accumulation: {flow_acc}")
    click.echo(f"\nTerrain products (EPSG:{utm_epsg}):")
    click.echo(f"  - UTM DEM: {dem_utm}")
    click.echo(f"  - Multi-directional hillshade: {hillshade}")
    click.echo(f"  - Slope (8-bit, 0-45°): {slope}")
    click.echo(f"  - Aspect (color-coded): {aspect}")
    click.echo(f"\nIntermediate files:")
    click.echo(f"  - Slope (degrees): {slope_deg}")
    click.echo(f"  - Aspect (degrees): {aspect_deg}")


if __name__ == '__main__':
    main()
