#!/usr/bin/env python3
"""
Prepare DEM for watershed delineation.

This script:
1. Fills sinks/depressions in the DEM
2. Computes D8 flow direction
3. Computes flow accumulation
4. Generates derived terrain products (hillshade, slope, aspect)

Usage:
    python prepare_dem.py --input data/raw/dem/elevation.tif --output data/processed/dem/
"""

import click
from pathlib import Path
import whitebox
from tqdm import tqdm


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
def main(input, output, breach):
    """Prepare DEM for hydrological analysis."""

    wbt = whitebox.WhiteboxTools()
    wbt.set_verbose_mode(True)

    input_path = Path(input)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Processing DEM: {input_path.name}")
    click.echo(f"Output directory: {output_dir}")

    # Output files
    filled_dem = output_dir / "filled_dem.tif"
    flow_dir = output_dir / "flow_direction.tif"
    flow_acc = output_dir / "flow_accumulation.tif"
    hillshade = output_dir / "hillshade.tif"
    slope = output_dir / "slope.tif"
    aspect = output_dir / "aspect.tif"

    with tqdm(total=6, desc="DEM processing") as pbar:
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

        # Step 4: Hillshade
        pbar.set_description("Generating hillshade")
        wbt.hillshade(
            dem=str(filled_dem),
            output=str(hillshade),
            azimuth=315.0,
            altitude=45.0
        )
        pbar.update(1)

        # Step 5: Slope
        pbar.set_description("Computing slope")
        wbt.slope(
            dem=str(filled_dem),
            output=str(slope),
            units="degrees"
        )
        pbar.update(1)

        # Step 6: Aspect
        pbar.set_description("Computing aspect")
        wbt.aspect(
            dem=str(filled_dem),
            output=str(aspect)
        )
        pbar.update(1)

    click.echo("\nDEM processing complete!")
    click.echo(f"\nGenerated files:")
    click.echo(f"  - Filled DEM: {filled_dem}")
    click.echo(f"  - Flow direction: {flow_dir}")
    click.echo(f"  - Flow accumulation: {flow_acc}")
    click.echo(f"  - Hillshade: {hillshade}")
    click.echo(f"  - Slope: {slope}")
    click.echo(f"  - Aspect: {aspect}")


if __name__ == '__main__':
    main()
