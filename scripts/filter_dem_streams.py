#!/usr/bin/env python3
"""
Filter DEM-derived streams to remove noise and compute confidence scores.

This script:
1. Removes artifacts (segments < minimum length)
2. Filters by minimum drainage area
3. Computes confidence scores based on multiple factors
4. Prepares streams for fusion with NHD network

Usage:
    python filter_dem_streams.py --input data/processed/streams.gpkg \
                                  --output data/processed/streams_filtered.gpkg \
                                  --min-length 25 \
                                  --min-drainage-area 0.1
"""

import click
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
from tqdm import tqdm


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True),
    required=True,
    help='Input GeoPackage with DEM-derived streams'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output GeoPackage file'
)
@click.option(
    '--layer',
    type=str,
    default='streams_t100',
    help='Input layer name (default: streams_t100 for finest threshold)'
)
@click.option(
    '--min-length',
    type=float,
    default=25.0,
    help='Minimum segment length in meters (default: 25)'
)
@click.option(
    '--min-drainage-area',
    type=float,
    default=0.1,
    help='Minimum drainage area in km² (default: 0.1). Set to 0 to disable.'
)
@click.option(
    '--flow-acc',
    type=click.Path(exists=True),
    help='Flow accumulation raster for drainage area calculation (optional)'
)
def main(input, output, layer, min_length, min_drainage_area, flow_acc):
    """Filter DEM-derived streams and compute confidence scores."""

    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Filtering DEM streams from {input_path}")
    click.echo(f"  Input layer: {layer}")
    click.echo(f"  Min length: {min_length} m")
    click.echo(f"  Min drainage area: {min_drainage_area} km²")

    # Read input streams
    try:
        streams_gdf = gpd.read_file(input_path, layer=layer)
    except Exception as e:
        click.echo(f"Error reading layer '{layer}': {e}")
        click.echo(f"Available layers:")
        import fiona
        with fiona.open(input_path) as src:
            for layer_name in fiona.listlayers(input_path):
                click.echo(f"  - {layer_name}")
        return 1

    click.echo(f"  Input features: {len(streams_gdf)}")

    original_count = len(streams_gdf)

    # Step 1: Filter by minimum length
    click.echo("\nStep 1: Filtering by minimum length...")
    streams_gdf = streams_gdf[streams_gdf['length_m'] >= min_length].copy()
    removed = original_count - len(streams_gdf)
    click.echo(f"  Removed {removed} segments < {min_length}m ({removed/original_count*100:.1f}%)")

    if len(streams_gdf) == 0:
        click.echo("Error: No streams remaining after length filter!")
        return 1

    # Step 2: Calculate/sample drainage area if flow_acc is provided
    if flow_acc and min_drainage_area > 0:
        click.echo("\nStep 2: Calculating drainage areas from flow accumulation...")
        streams_gdf = calculate_drainage_areas(streams_gdf, flow_acc)

        # Filter by minimum drainage area if column exists
        if 'drainage_area_sqkm' in streams_gdf.columns:
            before_filter = len(streams_gdf)
            streams_gdf = streams_gdf[streams_gdf['drainage_area_sqkm'] >= min_drainage_area].copy()
            removed = before_filter - len(streams_gdf)
            click.echo(f"  Removed {removed} segments < {min_drainage_area} km² drainage area ({removed/before_filter*100:.1f}%)")
    elif min_drainage_area > 0:
        click.echo("\nStep 2: Skipping drainage area filter (no flow_acc raster provided)")

    if len(streams_gdf) == 0:
        click.echo("Error: No streams remaining after drainage area filter!")
        return 1

    # Step 3: Calculate geometric metrics for artifact detection
    click.echo("\nStep 3: Calculating stream geometry metrics...")
    streams_gdf = calculate_geometric_metrics(streams_gdf)

    # Step 4: Filter likely artifacts based on geometry
    click.echo("\nStep 4: Filtering geometric artifacts...")
    before_geom_filter = len(streams_gdf)
    streams_gdf = filter_geometric_artifacts(streams_gdf)
    removed_geom = before_geom_filter - len(streams_gdf)
    click.echo(f"  Removed {removed_geom} geometric artifacts ({removed_geom/before_geom_filter*100:.1f}%)")

    if len(streams_gdf) == 0:
        click.echo("Error: No streams remaining after geometric filter!")
        return 1

    # Step 5: Compute confidence scores
    click.echo("\nStep 5: Computing confidence scores...")
    streams_gdf = compute_confidence_scores(streams_gdf)

    # Step 6: Classify flow persistence
    click.echo("\nStep 6: Classifying flow persistence...")
    streams_gdf = classify_flow_persistence(streams_gdf)

    # Step 7: Add source type
    streams_gdf['source_type'] = 'dem'

    # Save filtered streams
    click.echo(f"\nSaving filtered streams to {output_path}...")
    output_layer = layer + '_filtered'
    streams_gdf.to_file(output_path, driver='GPKG', layer=output_layer)

    # Print summary statistics
    click.echo("\n" + "="*60)
    click.echo("FILTERING SUMMARY")
    click.echo("="*60)
    click.echo(f"Input features: {original_count}")
    click.echo(f"Output features: {len(streams_gdf)}")
    click.echo(f"Retention rate: {len(streams_gdf)/original_count*100:.1f}%")
    click.echo(f"\nOutput file: {output_path}")
    click.echo(f"Output layer: {output_layer}")

    if 'confidence_score' in streams_gdf.columns:
        click.echo(f"\nConfidence score distribution:")
        click.echo(f"  Mean: {streams_gdf['confidence_score'].mean():.3f}")
        click.echo(f"  Median: {streams_gdf['confidence_score'].median():.3f}")
        click.echo(f"  Min: {streams_gdf['confidence_score'].min():.3f}")
        click.echo(f"  Max: {streams_gdf['confidence_score'].max():.3f}")

        # Show count by confidence bins
        bins = [0, 0.3, 0.5, 0.7, 1.0]
        labels = ['Low (0-0.3)', 'Medium (0.3-0.5)', 'High (0.5-0.7)', 'Very High (0.7-1.0)']
        streams_gdf['conf_bin'] = pd.cut(streams_gdf['confidence_score'], bins=bins, labels=labels, include_lowest=True)
        click.echo(f"\n  Confidence bins:")
        for label in labels:
            count = (streams_gdf['conf_bin'] == label).sum()
            pct = (count / len(streams_gdf)) * 100
            click.echo(f"    {label}: {count} ({pct:.1f}%)")

    if 'drainage_area_sqkm' in streams_gdf.columns:
        valid_da = streams_gdf[streams_gdf['drainage_area_sqkm'].notna()]
        if len(valid_da) > 0:
            click.echo(f"\nDrainage area statistics (km²):")
            click.echo(f"  Mean: {valid_da['drainage_area_sqkm'].mean():.3f}")
            click.echo(f"  Median: {valid_da['drainage_area_sqkm'].median():.3f}")
            click.echo(f"  Min: {valid_da['drainage_area_sqkm'].min():.3f}")
            click.echo(f"  Max: {valid_da['drainage_area_sqkm'].max():.3f}")

    click.echo("\n" + "="*60)


def calculate_geometric_metrics(streams_gdf):
    """
    Calculate geometric metrics for artifact detection.

    Computes:
    - Sinuosity: ratio of stream length to straight-line distance
    - Straightness: inverse of sinuosity (1 = perfectly straight)

    DEM artifacts tend to be very straight (sinuosity ~1.0),
    while real streams meander (sinuosity typically 1.2-3.0).
    """
    from shapely.geometry import Point

    sinuosities = []

    for idx, row in streams_gdf.iterrows():
        geom = row.geometry

        if geom.geom_type == 'LineString':
            # Calculate straight-line distance
            start_point = Point(geom.coords[0])
            end_point = Point(geom.coords[-1])
            straight_distance = start_point.distance(end_point)

            # Sinuosity = actual length / straight distance
            if straight_distance > 0:
                # Use projected length for accuracy
                sinuosity = geom.length / straight_distance
            else:
                # Zero-length or loop - mark as suspicious
                sinuosity = 1.0
        elif geom.geom_type == 'MultiLineString':
            # For MultiLineString, calculate for the longest segment
            longest_line = max(geom.geoms, key=lambda l: l.length)
            start_point = Point(longest_line.coords[0])
            end_point = Point(longest_line.coords[-1])
            straight_distance = start_point.distance(end_point)

            if straight_distance > 0:
                sinuosity = longest_line.length / straight_distance
            else:
                sinuosity = 1.0
        else:
            sinuosity = 1.0

        sinuosities.append(sinuosity)

    streams_gdf['sinuosity'] = sinuosities

    return streams_gdf


def filter_geometric_artifacts(streams_gdf):
    """
    Filter likely DEM artifacts based on geometric properties.

    Removes streams that are:
    - Too straight (sinuosity < 1.05) AND short (< 100m)
      Real short streams can be straight, but DEM artifacts often are

    Conservative filtering to avoid removing real streams.
    """
    # Identify suspicious streams
    suspicious_mask = (
        (streams_gdf['sinuosity'] < 1.05) &  # Very straight
        (streams_gdf['length_m'] < 100)       # Short
    )

    removed_count = suspicious_mask.sum()

    if removed_count > 0:
        click.echo(f"    Flagged {removed_count} suspicious straight segments")
        # Remove suspicious streams
        streams_gdf = streams_gdf[~suspicious_mask].copy()

    return streams_gdf


def calculate_drainage_areas(streams_gdf, flow_acc_path):
    """
    Calculate drainage area for each stream segment from flow accumulation raster.

    Samples the flow accumulation at the downstream end of each segment
    and converts to drainage area in km².
    """
    import rasterio
    from rasterio.transform import rowcol

    with rasterio.open(flow_acc_path) as src:
        # Get pixel area in km²
        # For geographic CRS, approximate using latitude
        if src.crs.is_geographic:
            # Rough approximation: 1 degree ≈ 111 km at equator
            # Pixel size in degrees
            pixel_width_deg = abs(src.transform[0])
            pixel_height_deg = abs(src.transform[4])

            # Approximate center latitude
            center_lat = (src.bounds.top + src.bounds.bottom) / 2
            # Convert to km
            pixel_width_km = pixel_width_deg * 111.32 * np.cos(np.radians(center_lat))
            pixel_height_km = pixel_height_deg * 111.32
            pixel_area_km2 = pixel_width_km * pixel_height_km
        else:
            # For projected CRS, use transform units (assumed meters)
            pixel_width_m = abs(src.transform[0])
            pixel_height_m = abs(src.transform[4])
            pixel_area_km2 = (pixel_width_m * pixel_height_m) / 1e6

        drainage_areas = []

        for idx, row in tqdm(streams_gdf.iterrows(), total=len(streams_gdf), desc="  Sampling drainage areas"):
            # Get downstream point (last coordinate)
            geom = row.geometry
            if geom.geom_type == 'LineString':
                downstream_point = geom.coords[-1]
            elif geom.geom_type == 'MultiLineString':
                # Get last coordinate of last linestring
                downstream_point = list(geom.geoms[-1].coords)[-1]
            else:
                drainage_areas.append(np.nan)
                continue

            # Transform to raster CRS if needed
            if streams_gdf.crs != src.crs:
                from shapely.geometry import Point
                point_gdf = gpd.GeoDataFrame([1], geometry=[Point(downstream_point)], crs=streams_gdf.crs)
                point_proj = point_gdf.to_crs(src.crs).geometry.values[0]
                x, y = point_proj.x, point_proj.y
            else:
                x, y = downstream_point

            # Sample raster
            r, c = rowcol(src.transform, x, y)

            if 0 <= r < src.height and 0 <= c < src.width:
                flow_accum_value = src.read(1, window=((r, r+1), (c, c+1)))[0, 0]

                # Handle nodata
                if src.nodata is not None and flow_accum_value == src.nodata:
                    drainage_area_km2 = np.nan
                else:
                    # Convert flow accumulation (number of cells) to drainage area
                    drainage_area_km2 = flow_accum_value * pixel_area_km2
            else:
                drainage_area_km2 = np.nan

            drainage_areas.append(drainage_area_km2)

        streams_gdf['drainage_area_sqkm'] = drainage_areas

    return streams_gdf


def classify_flow_persistence(streams_gdf):
    """
    Classify streams as Perennial, Intermittent, or Ephemeral based on drainage area.

    Thresholds (approximate, tuned for 10m DEM):
    - Perennial: drainage_area >= 5 km² (large contributing area, likely year-round flow)
    - Intermittent: 0.5 km² <= drainage_area < 5 km² (seasonal flow)
    - Ephemeral: drainage_area < 0.5 km² (flow only during/after storms)

    If drainage_area is not available, defaults to Ephemeral.
    """
    stream_types = []

    for idx, row in streams_gdf.iterrows():
        if 'drainage_area_sqkm' in streams_gdf.columns and pd.notna(row.get('drainage_area_sqkm')):
            da = row['drainage_area_sqkm']

            if da >= 5.0:
                stream_type = 'Perennial'
            elif da >= 0.5:
                stream_type = 'Intermittent'
            else:
                stream_type = 'Ephemeral'
        else:
            # Default to Ephemeral if no drainage area data
            stream_type = 'Ephemeral'

        stream_types.append(stream_type)

    streams_gdf['stream_type'] = stream_types

    # Report distribution
    type_counts = streams_gdf['stream_type'].value_counts()
    click.echo(f"  Flow persistence distribution:")
    for stype in ['Perennial', 'Intermittent', 'Ephemeral']:
        count = type_counts.get(stype, 0)
        pct = (count / len(streams_gdf)) * 100 if len(streams_gdf) > 0 else 0
        click.echo(f"    {stype}: {count} ({pct:.1f}%)")

    return streams_gdf


def compute_confidence_scores(streams_gdf):
    """
    Compute confidence scores for DEM-derived streams.

    Confidence is based on:
    - Length (longer = more confident)
    - Stream order (higher = more confident)
    - Drainage area (larger = more confident, if available)
    - Sinuosity (meandering = more confident than straight)

    Score ranges from 0 to 1.
    """
    scores = []

    for idx, row in streams_gdf.iterrows():
        # Component 1: Length score (0-1)
        # Normalize length: 25m = 0, 500m = 1
        length_score = min(1.0, max(0.0, (row['length_m'] - 25) / (500 - 25)))

        # Component 2: Order score (0-1)
        # Order 1 = 0.3, Order 2 = 0.6, Order 3+ = 1.0
        order = row.get('order', 1)
        if order == 1:
            order_score = 0.3
        elif order == 2:
            order_score = 0.6
        else:
            order_score = 1.0

        # Component 3: Drainage area score (0-1) if available
        if 'drainage_area_sqkm' in streams_gdf.columns and pd.notna(row.get('drainage_area_sqkm')):
            da = row['drainage_area_sqkm']
            # Normalize: 0.1 km² = 0, 5 km² = 1
            da_score = min(1.0, max(0.0, (da - 0.1) / (5.0 - 0.1)))
        else:
            da_score = 0.5  # Neutral if not available

        # Component 4: Sinuosity score (0-1) if available
        # Real streams typically have sinuosity 1.2-2.0
        # Artifacts tend to be very straight (sinuosity ~1.0)
        if 'sinuosity' in streams_gdf.columns and pd.notna(row.get('sinuosity')):
            sinuosity = row['sinuosity']
            if sinuosity < 1.1:
                sinuosity_score = 0.2  # Very straight, suspicious
            elif sinuosity < 1.3:
                sinuosity_score = 0.6  # Moderately straight
            elif sinuosity < 2.0:
                sinuosity_score = 1.0  # Good meandering
            else:
                sinuosity_score = 0.8  # Very sinuous, could be artifact
        else:
            sinuosity_score = 0.5  # Neutral if not available

        # Combined score (weighted average)
        confidence_score = (
            0.2 * length_score +
            0.2 * order_score +
            0.4 * da_score +
            0.2 * sinuosity_score
        )

        scores.append(confidence_score)

    streams_gdf['confidence_score'] = scores

    return streams_gdf


if __name__ == '__main__':
    main()
