#!/usr/bin/env python3
"""
Process NHD Plus HR HUC12 watershed boundaries.

Usage:
    python process_huc.py --input ../data/raw/nhd/NHDPLUS_H_0207_HU4_GDB.gdb \
                          --output ../data/processed/huc12.gpkg \
                          --bounds -77.2501389,38.7801389,-77.1501389,38.8801389
"""

import click
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True),
    required=True,
    help='Input NHD geodatabase (.gdb)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output GeoPackage file'
)
@click.option(
    '--bounds',
    type=str,
    default='-77.2501389,38.7801389,-77.1501389,38.8801389',
    help='Bounding box as minx,miny,maxx,maxy (WGS84)'
)
def main(input, output, bounds):
    """Process NHD Plus HR HUC12 watershed boundaries."""

    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse bounds
    minx, miny, maxx, maxy = map(float, bounds.split(','))
    aoi_bbox = box(minx, miny, maxx, maxy)

    click.echo(f"Processing HUC12 boundaries from {input_path.name}")
    click.echo(f"AOI bounds: {minx:.4f}, {miny:.4f} to {maxx:.4f}, {maxy:.4f}")

    # Read WBDHU12 layer with bbox filter for efficiency
    click.echo("\nReading WBDHU12 layer...")
    huc12_gdf = gpd.read_file(
        input_path,
        layer='WBDHU12',
        bbox=(minx, miny, maxx, maxy)
    )

    click.echo(f"  Features intersecting AOI: {len(huc12_gdf)}")

    if len(huc12_gdf) == 0:
        click.echo("Error: No HUC12 watersheds found in the specified AOI")
        return 1

    # Calculate area in sq km using equal-area projection
    click.echo("\nCalculating areas...")
    huc12_proj = huc12_gdf.to_crs("EPSG:6933")  # Equal Earth projection
    huc12_gdf['area_sqkm'] = huc12_proj.geometry.area / 1_000_000  # m² to km²

    # Select and rename key fields for simplicity
    fields_to_keep = ['geometry', 'area_sqkm']

    # HUC12 code
    if 'HUC12' in huc12_gdf.columns:
        huc12_gdf['huc12'] = huc12_gdf['HUC12']
        fields_to_keep.append('huc12')

    # Watershed name
    if 'Name' in huc12_gdf.columns:
        huc12_gdf['name'] = huc12_gdf['Name']
        fields_to_keep.append('name')

    # States
    if 'States' in huc12_gdf.columns:
        huc12_gdf['states'] = huc12_gdf['States']
        fields_to_keep.append('states')

    # Original area from dataset (for comparison)
    if 'AreaSqKm' in huc12_gdf.columns:
        huc12_gdf['source_area_sqkm'] = huc12_gdf['AreaSqKm']
        fields_to_keep.append('source_area_sqkm')

    # Select final fields
    available_fields = [f for f in fields_to_keep if f in huc12_gdf.columns or f == 'geometry']
    huc12_final = huc12_gdf[available_fields].copy()

    # Save to GeoPackage
    click.echo(f"\nSaving to {output_path}...")
    huc12_final.to_file(output_path, driver='GPKG', layer='huc12')

    # Print summary statistics
    click.echo("\n" + "="*60)
    click.echo("SUMMARY")
    click.echo("="*60)
    click.echo(f"Output file: {output_path}")
    click.echo(f"Number of HUC12 watersheds: {len(huc12_final)}")

    if 'area_sqkm' in huc12_final.columns:
        click.echo(f"\nWatershed areas:")
        click.echo(f"  Total: {huc12_final['area_sqkm'].sum():.2f} km²")
        click.echo(f"  Mean: {huc12_final['area_sqkm'].mean():.2f} km²")
        click.echo(f"  Min: {huc12_final['area_sqkm'].min():.2f} km²")
        click.echo(f"  Max: {huc12_final['area_sqkm'].max():.2f} km²")

    if 'name' in huc12_final.columns:
        named_hucs = huc12_final[huc12_final['name'].notna()]
        click.echo(f"\nNamed watersheds: {len(named_hucs)}")
        if len(named_hucs) > 0:
            click.echo("  Examples:")
            for name in named_hucs['name'].unique()[:10]:
                # Find the HUC12 code for this name
                huc_code = huc12_final[huc12_final['name'] == name]['huc12'].iloc[0] if 'huc12' in huc12_final.columns else ''
                if huc_code:
                    click.echo(f"    - {name} ({huc_code})")
                else:
                    click.echo(f"    - {name}")

    click.echo("\n" + "="*60)
    click.echo("Processing complete!")
    click.echo("="*60)


if __name__ == '__main__':
    main()
