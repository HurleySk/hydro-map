#!/usr/bin/env python3
"""
Process NHD Plus HR data: clip to AOI, filter to natural streams, add attributes.

Usage:
    python process_nhd.py --input ../data/raw/nhd/NHDPLUS_H_0207_HU4_GDB.gdb \
                          --output ../data/processed/streams.gpkg \
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
    """Process NHD Plus HR flowline data."""

    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse bounds
    minx, miny, maxx, maxy = map(float, bounds.split(','))
    aoi_bbox = box(minx, miny, maxx, maxy)

    click.echo(f"Processing NHD data from {input_path.name}")
    click.echo(f"AOI bounds: {minx:.4f}, {miny:.4f} to {maxx:.4f}, {maxy:.4f}")

    # Read NHDFlowline layer with bbox filter for efficiency
    click.echo("\nReading NHDFlowline layer...")
    streams_gdf = gpd.read_file(
        input_path,
        layer='NHDFlowline',
        bbox=(minx, miny, maxx, maxy)
    )

    click.echo(f"  Features in AOI: {len(streams_gdf)}")

    if len(streams_gdf) == 0:
        click.echo("Error: No features found in the specified AOI")
        return 1

    # Filter to natural streams only (exclude artificial paths, pipelines, etc.)
    # NHD FCodes:
    #   46000 = StreamRiver (general)
    #   46003 = StreamRiver: Intermittent
    #   46006 = StreamRiver: Perennial
    #   46007 = StreamRiver: Ephemeral
    #   55800 = Artificial Path (EXCLUDE)
    #   33600 = CanalDitch (EXCLUDE)
    #   42800 = Pipeline (EXCLUDE)

    click.echo("\nFiltering to natural streams...")
    natural_stream_codes = [46000, 46003, 46006, 46007]

    if 'FCode' in streams_gdf.columns:
        original_count = len(streams_gdf)
        streams_gdf = streams_gdf[streams_gdf['FCode'].isin(natural_stream_codes)]
        click.echo(f"  Filtered {original_count} -> {len(streams_gdf)} features")
        click.echo(f"  Removed {original_count - len(streams_gdf)} artificial paths/connectors")
    else:
        click.echo("  Warning: FCode field not found, keeping all features")

    if len(streams_gdf) == 0:
        click.echo("Error: No natural streams found after filtering")
        return 1

    # Add calculated attributes
    click.echo("\nCalculating stream attributes...")

    # Calculate length in meters using equal-area projection
    streams_proj = streams_gdf.to_crs("EPSG:6933")  # Equal Earth projection
    streams_gdf['length_m'] = streams_proj.geometry.length
    streams_gdf['length_km'] = streams_gdf['length_m'] / 1000

    # Create simplified stream order field
    # NHD has StreamOrder in VAA table, but we'll use a simple classification
    if 'StreamOrde' in streams_gdf.columns:
        streams_gdf['order'] = streams_gdf['StreamOrde']
    elif 'StreamOrder' in streams_gdf.columns:
        streams_gdf['order'] = streams_gdf['StreamOrder']
    else:
        # Default order based on length (rough approximation)
        streams_gdf['order'] = 1
        streams_gdf.loc[streams_gdf['length_m'] > 500, 'order'] = 2
        streams_gdf.loc[streams_gdf['length_m'] > 2000, 'order'] = 3
        streams_gdf.loc[streams_gdf['length_m'] > 5000, 'order'] = 4
        click.echo("  Note: StreamOrder field not found, assigned based on length")

    # Clean up FCode to stream type mapping
    fcode_to_type = {
        46000: 'Stream',
        46003: 'Intermittent',
        46006: 'Perennial',
        46007: 'Ephemeral'
    }

    if 'FCode' in streams_gdf.columns:
        streams_gdf['stream_type'] = streams_gdf['FCode'].map(fcode_to_type)

    # Select and rename key fields for simplicity
    fields_to_keep = ['geometry', 'length_m', 'length_km', 'order', 'stream_type']

    # Keep GNIS_Name if it exists (official stream names)
    if 'GNIS_Name' in streams_gdf.columns:
        streams_gdf['name'] = streams_gdf['GNIS_Name']
        fields_to_keep.append('name')

    # Keep Permanent_Identifier for traceability
    if 'Permanent_Identifier' in streams_gdf.columns:
        streams_gdf['nhd_id'] = streams_gdf['Permanent_Identifier']
        fields_to_keep.append('nhd_id')

    # Select final fields
    available_fields = [f for f in fields_to_keep if f in streams_gdf.columns or f == 'geometry']
    streams_final = streams_gdf[available_fields].copy()

    # Save to GeoPackage
    click.echo(f"\nSaving to {output_path}...")
    streams_final.to_file(output_path, driver='GPKG', layer='streams')

    # Print summary statistics
    click.echo("\n" + "="*60)
    click.echo("SUMMARY")
    click.echo("="*60)
    click.echo(f"Output file: {output_path}")
    click.echo(f"Number of stream segments: {len(streams_final)}")
    click.echo(f"Total stream length: {streams_final['length_km'].sum():.2f} km")
    click.echo(f"Average segment length: {streams_final['length_m'].mean():.1f} m")
    click.echo(f"Median segment length: {streams_final['length_m'].median():.1f} m")

    if 'stream_type' in streams_final.columns:
        click.echo("\nStream types:")
        for stype, count in streams_final['stream_type'].value_counts().items():
            pct = (count / len(streams_final)) * 100
            click.echo(f"  {stype}: {count} ({pct:.1f}%)")

    if 'order' in streams_final.columns:
        click.echo("\nStream orders:")
        for order in sorted(streams_final['order'].unique()):
            count = (streams_final['order'] == order).sum()
            pct = (count / len(streams_final)) * 100
            click.echo(f"  Order {int(order)}: {count} ({pct:.1f}%)")

    if 'name' in streams_final.columns:
        named_streams = streams_final[streams_final['name'].notna()]
        click.echo(f"\nNamed streams: {len(named_streams)} ({len(named_streams)/len(streams_final)*100:.1f}%)")
        if len(named_streams) > 0:
            click.echo("  Examples:")
            for name in named_streams['name'].unique()[:10]:
                click.echo(f"    - {name}")

    click.echo("\n" + "="*60)
    click.echo("Processing complete!")
    click.echo("="*60)


if __name__ == '__main__':
    main()
