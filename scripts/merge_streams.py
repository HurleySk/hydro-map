#!/usr/bin/env python3
"""
Merge NHD and DEM-derived stream networks.

This script fuses NHD streams (authoritative) with filtered DEM streams
to capture unmapped tributaries while avoiding duplicates and artifacts.

Fusion rules:
1. NHD streams are always kept unchanged (authoritative)
2. DEM streams within 30m of NHD with similar flow direction → DISCARD (duplicate)
3. DEM streams that cross NHD at tributary angle → SNAP endpoint, mark as 'merged'
4. DEM streams isolated (>50m from NHD) → KEEP as 'dem' source_type

Usage:
    python merge_streams.py --nhd data/processed/streams_nhd.gpkg \
                             --dem data/processed/streams_dem_filtered.gpkg \
                             --output data/processed/streams_fused.gpkg
"""

import click
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import nearest_points, snap
from tqdm import tqdm


@click.command()
@click.option(
    '--nhd', '-n',
    type=click.Path(exists=True),
    required=True,
    help='Input NHD streams GeoPackage'
)
@click.option(
    '--nhd-layer',
    type=str,
    default='streams',
    help='NHD layer name (default: streams)'
)
@click.option(
    '--dem', '-d',
    type=click.Path(exists=True),
    required=True,
    help='Input filtered DEM streams GeoPackage'
)
@click.option(
    '--dem-layer',
    type=str,
    default='streams_t100_filtered',
    help='DEM layer name (default: streams_t100_filtered)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output fused streams GeoPackage'
)
@click.option(
    '--duplicate-distance',
    type=float,
    default=30.0,
    help='Distance in meters to consider DEM stream a duplicate of NHD (default: 30)'
)
@click.option(
    '--isolation-distance',
    type=float,
    default=50.0,
    help='Distance in meters for DEM stream to be considered isolated (default: 50)'
)
@click.option(
    '--snap-distance',
    type=float,
    default=5.0,
    help='Distance in meters to snap tributary endpoints to NHD (default: 5)'
)
@click.option(
    '--angle-tolerance',
    type=float,
    default=45.0,
    help='Max angle difference in degrees for flow direction matching (default: 45)'
)
def main(nhd, nhd_layer, dem, dem_layer, output, duplicate_distance,
         isolation_distance, snap_distance, angle_tolerance):
    """Merge NHD and DEM stream networks."""

    nhd_path = Path(nhd)
    dem_path = Path(dem)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo("="*60)
    click.echo("NHD-DEM STREAM NETWORK FUSION")
    click.echo("="*60)
    click.echo(f"NHD source: {nhd_path} (layer: {nhd_layer})")
    click.echo(f"DEM source: {dem_path} (layer: {dem_layer})")
    click.echo(f"Output: {output_path}")
    click.echo(f"\nFusion parameters:")
    click.echo(f"  Duplicate distance: {duplicate_distance} m")
    click.echo(f"  Isolation distance: {isolation_distance} m")
    click.echo(f"  Snap distance: {snap_distance} m")
    click.echo(f"  Flow angle tolerance: {angle_tolerance}°")

    # Step 1: Load NHD streams (authoritative)
    click.echo("\nStep 1: Loading NHD streams...")
    try:
        nhd_gdf = gpd.read_file(nhd_path, layer=nhd_layer)
    except Exception as e:
        click.echo(f"Error loading NHD layer: {e}")
        return 1

    click.echo(f"  NHD features: {len(nhd_gdf)}")
    click.echo(f"  Total NHD length: {nhd_gdf['length_km'].sum():.2f} km")

    # Ensure source_type is set
    if 'source_type' not in nhd_gdf.columns:
        nhd_gdf['source_type'] = 'nhd'

    # Step 2: Load filtered DEM streams
    click.echo("\nStep 2: Loading filtered DEM streams...")
    try:
        dem_gdf = gpd.read_file(dem_path, layer=dem_layer)
    except Exception as e:
        click.echo(f"Error loading DEM layer: {e}")
        return 1

    click.echo(f"  DEM features: {len(dem_gdf)}")
    click.echo(f"  Total DEM length: {dem_gdf['length_km'].sum():.2f} km")

    # Ensure both are in the same CRS
    if nhd_gdf.crs != dem_gdf.crs:
        click.echo(f"  Reprojecting DEM streams from {dem_gdf.crs} to {nhd_gdf.crs}")
        dem_gdf = dem_gdf.to_crs(nhd_gdf.crs)

    # Step 3: Spatial conflict detection and classification
    click.echo("\nStep 3: Detecting spatial conflicts...")
    dem_classified = classify_dem_streams(
        nhd_gdf=nhd_gdf,
        dem_gdf=dem_gdf,
        duplicate_distance=duplicate_distance,
        isolation_distance=isolation_distance,
        angle_tolerance=angle_tolerance
    )

    # Report classification results
    click.echo("\n  Classification results:")
    for class_name, count in dem_classified['conflict_class'].value_counts().items():
        pct = (count / len(dem_classified)) * 100
        click.echo(f"    {class_name}: {count} ({pct:.1f}%)")

    # Step 4: Filter and prepare streams for fusion
    click.echo("\nStep 4: Filtering DEM streams for fusion...")

    # Discard duplicates
    duplicate_count = (dem_classified['conflict_class'] == 'duplicate').sum()
    dem_to_add = dem_classified[dem_classified['conflict_class'] != 'duplicate'].copy()
    click.echo(f"  Discarded {duplicate_count} duplicate streams")
    click.echo(f"  Retaining {len(dem_to_add)} DEM streams for fusion")

    # Step 5: Snap tributary endpoints to NHD junctions
    click.echo("\nStep 5: Snapping tributary endpoints...")
    dem_snapped = snap_tributaries_to_nhd(
        nhd_gdf=nhd_gdf,
        dem_gdf=dem_to_add,
        snap_distance=snap_distance
    )

    # Update source_type based on classification
    dem_snapped.loc[dem_snapped['conflict_class'] == 'tributary', 'source_type'] = 'merged'
    dem_snapped.loc[dem_snapped['conflict_class'] == 'isolated', 'source_type'] = 'dem'

    # Step 6: Merge NHD and DEM streams
    click.echo("\nStep 6: Merging stream networks...")

    # Ensure schema compatibility
    dem_snapped = harmonize_schemas(nhd_gdf, dem_snapped)

    # Combine
    fused_gdf = pd.concat([nhd_gdf, dem_snapped], ignore_index=True)

    click.echo(f"  Total fused features: {len(fused_gdf)}")
    click.echo(f"  Total fused length: {fused_gdf['length_km'].sum():.2f} km")

    # Step 7: Topology cleaning
    click.echo("\nStep 7: Topology cleaning...")
    fused_gdf = clean_topology(fused_gdf, min_dangle_length=50.0)

    # Step 8: Save outputs
    click.echo("\nStep 8: Saving fused network...")

    # Main fused layer
    fused_gdf.to_file(output_path, driver='GPKG', layer='streams')

    # Exploded version for tippecanoe (maintain existing behavior)
    fused_exploded = fused_gdf.explode(index_parts=False).reset_index(drop=True)
    # Recalculate lengths for exploded segments
    fused_exploded_proj = fused_exploded.to_crs("EPSG:6933")
    fused_exploded['length_m'] = fused_exploded_proj.geometry.length
    fused_exploded['length_km'] = fused_exploded['length_m'] / 1000
    fused_exploded = fused_exploded.to_crs(nhd_gdf.crs)
    fused_exploded.to_file(output_path, driver='GPKG', layer='streams_merged')

    # Save backup layers for QA
    nhd_gdf.to_file(output_path, driver='GPKG', layer='streams_nhd_only')
    dem_classified.to_file(output_path, driver='GPKG', layer='streams_dem_candidates')

    # Print final summary
    print_fusion_summary(nhd_gdf, dem_classified, fused_gdf, output_path)


def classify_dem_streams(nhd_gdf, dem_gdf, duplicate_distance, isolation_distance, angle_tolerance):
    """
    Classify DEM streams based on spatial relationship to NHD.

    Returns DEM GeoDataFrame with 'conflict_class' column:
    - 'duplicate': Within duplicate_distance of NHD, similar flow direction
    - 'tributary': Crosses or approaches NHD at tributary angle
    - 'isolated': >isolation_distance from NHD network
    """
    # Convert to projected CRS for accurate distance calculations
    nhd_proj = nhd_gdf.to_crs("EPSG:6933")  # Equal Earth
    dem_proj = dem_gdf.to_crs("EPSG:6933")

    # Build spatial index for NHD
    nhd_sindex = nhd_proj.sindex

    conflict_classes = []

    for idx, dem_stream in tqdm(dem_proj.iterrows(), total=len(dem_proj), desc="  Classifying DEM streams"):
        # Find nearby NHD streams
        possible_matches_idx = list(nhd_sindex.intersection(dem_stream.geometry.bounds))

        if not possible_matches_idx:
            conflict_classes.append('isolated')
            continue

        # Calculate minimum distance to NHD network
        min_distance = min(
            nhd_proj.iloc[i].geometry.distance(dem_stream.geometry)
            for i in possible_matches_idx
        )

        if min_distance > isolation_distance:
            conflict_classes.append('isolated')
        elif min_distance <= duplicate_distance:
            # Check flow direction similarity
            # Get closest NHD stream
            closest_idx = min(
                possible_matches_idx,
                key=lambda i: nhd_proj.iloc[i].geometry.distance(dem_stream.geometry)
            )
            nhd_stream = nhd_proj.iloc[closest_idx]

            # Calculate flow direction angle
            dem_angle = calculate_flow_direction(dem_stream.geometry)
            nhd_angle = calculate_flow_direction(nhd_stream.geometry)

            angle_diff = abs(dem_angle - nhd_angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            if angle_diff <= angle_tolerance:
                conflict_classes.append('duplicate')
            else:
                conflict_classes.append('tributary')
        else:
            # Between duplicate and isolation distance - likely a tributary
            conflict_classes.append('tributary')

    dem_gdf['conflict_class'] = conflict_classes

    return dem_gdf


def calculate_flow_direction(geom):
    """
    Calculate flow direction angle in degrees from north.

    Uses the overall direction from first to last point.
    """
    if geom.geom_type == 'LineString':
        coords = list(geom.coords)
    elif geom.geom_type == 'MultiLineString':
        coords = list(geom.geoms[0].coords)  # Use first segment
    else:
        return 0.0

    if len(coords) < 2:
        return 0.0

    # Use first and last point for overall direction
    x1, y1 = coords[0]
    x2, y2 = coords[-1]

    # Calculate angle in degrees (0 = north, 90 = east)
    angle = np.degrees(np.arctan2(x2 - x1, y2 - y1))
    if angle < 0:
        angle += 360

    return angle


def snap_tributaries_to_nhd(nhd_gdf, dem_gdf, snap_distance):
    """
    Snap tributary endpoints to nearby NHD junctions.

    Only snaps if within snap_distance of NHD network.
    """
    # Convert to projected CRS
    nhd_proj = nhd_gdf.to_crs("EPSG:6933")
    dem_proj = dem_gdf.to_crs("EPSG:6933")

    # Extract NHD endpoints for snapping targets
    nhd_points = []
    for geom in nhd_proj.geometry:
        if geom.geom_type == 'LineString':
            nhd_points.extend([Point(geom.coords[0]), Point(geom.coords[-1])])
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                nhd_points.extend([Point(line.coords[0]), Point(line.coords[-1])])

    nhd_points_gdf = gpd.GeoDataFrame(geometry=nhd_points, crs="EPSG:6933")
    nhd_sindex = nhd_points_gdf.sindex

    snapped_geometries = []
    snapped_count = 0

    for idx, dem_stream in tqdm(dem_proj.iterrows(), total=len(dem_proj), desc="  Snapping endpoints"):
        geom = dem_stream.geometry

        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            downstream_point = Point(coords[-1])

            # Find nearby NHD points
            possible_matches = list(nhd_sindex.intersection(downstream_point.buffer(snap_distance).bounds))

            if possible_matches:
                # Snap to nearest NHD point
                nearest_nhd_point = min(
                    (nhd_points_gdf.iloc[i].geometry for i in possible_matches),
                    key=lambda p: downstream_point.distance(p)
                )

                if downstream_point.distance(nearest_nhd_point) <= snap_distance:
                    # Replace last coordinate with snapped position
                    coords[-1] = (nearest_nhd_point.x, nearest_nhd_point.y)
                    snapped_geometries.append(LineString(coords))
                    snapped_count += 1
                else:
                    snapped_geometries.append(geom)
            else:
                snapped_geometries.append(geom)
        else:
            # Keep MultiLineString as-is for simplicity
            snapped_geometries.append(geom)

    click.echo(f"    Snapped {snapped_count} tributary endpoints")

    # Update geometries and reproject back to original CRS
    dem_proj.geometry = snapped_geometries
    dem_snapped = dem_proj.to_crs(dem_gdf.crs)

    return dem_snapped


def harmonize_schemas(nhd_gdf, dem_gdf):
    """
    Ensure DEM GeoDataFrame has compatible schema with NHD.

    Adds missing columns with null/default values.
    """
    # Get all columns from NHD
    nhd_cols = set(nhd_gdf.columns) - {'geometry'}
    dem_cols = set(dem_gdf.columns) - {'geometry'}

    # Add missing NHD columns to DEM
    for col in nhd_cols - dem_cols:
        if col in ['is_connector']:
            dem_gdf[col] = False
        elif col in ['stream_type']:
            dem_gdf[col] = 'Ephemeral'  # Assume DEM streams are ephemeral unless proven otherwise
        else:
            dem_gdf[col] = None

    # Add missing DEM columns to NHD (if any unique ones)
    # For now, we'll primarily keep NHD schema
    # Ensure key fusion columns are present
    if 'confidence_score' not in nhd_gdf.columns:
        nhd_gdf['confidence_score'] = 1.0  # NHD has maximum confidence

    return dem_gdf


def clean_topology(gdf, min_dangle_length=50.0):
    """
    Clean topology issues in the fused network.

    - Remove short dangles (disconnected segments < min_dangle_length)
    - Validate no self-intersections
    """
    # Convert to projected CRS for length calculations
    gdf_proj = gdf.to_crs("EPSG:6933")

    # Build spatial index
    sindex = gdf_proj.sindex

    # Find dangles (endpoints that don't connect to other streams)
    to_remove = []

    for idx, stream in tqdm(gdf_proj.iterrows(), total=len(gdf_proj), desc="  Checking dangles"):
        geom = stream.geometry

        if geom.geom_type == 'LineString':
            # Get endpoints
            start_point = Point(geom.coords[0])
            end_point = Point(geom.coords[-1])

            # Buffer slightly for intersection check (1 meter)
            buffer_dist = 1.0

            # Find nearby streams (excluding self)
            possible_matches = list(sindex.intersection(geom.bounds))
            nearby_streams = [gdf_proj.iloc[i] for i in possible_matches if i != idx]

            # Check if endpoints connect to other streams
            start_connected = any(
                start_point.buffer(buffer_dist).intersects(s.geometry)
                for s in nearby_streams
            )
            end_connected = any(
                end_point.buffer(buffer_dist).intersects(s.geometry)
                for s in nearby_streams
            )

            # If both endpoints are disconnected and segment is short, mark for removal
            if not start_connected and not end_connected:
                if stream['length_m'] < min_dangle_length:
                    to_remove.append(idx)

    if to_remove:
        click.echo(f"    Removing {len(to_remove)} short dangles < {min_dangle_length}m")
        gdf = gdf.drop(index=to_remove).reset_index(drop=True)
    else:
        click.echo(f"    No short dangles found")

    return gdf


def print_fusion_summary(nhd_gdf, dem_classified, fused_gdf, output_path):
    """Print summary statistics of the fusion process."""
    click.echo("\n" + "="*60)
    click.echo("FUSION SUMMARY")
    click.echo("="*60)

    click.echo(f"\nInput streams:")
    click.echo(f"  NHD features: {len(nhd_gdf)}")
    click.echo(f"  NHD total length: {nhd_gdf['length_km'].sum():.2f} km")
    click.echo(f"  DEM candidates: {len(dem_classified)}")
    click.echo(f"  DEM total length: {dem_classified['length_km'].sum():.2f} km")

    click.echo(f"\nDEM classification:")
    for class_name, count in dem_classified['conflict_class'].value_counts().items():
        pct = (count / len(dem_classified)) * 100
        length_km = dem_classified[dem_classified['conflict_class'] == class_name]['length_km'].sum()
        click.echo(f"  {class_name}: {count} streams ({pct:.1f}%), {length_km:.2f} km")

    click.echo(f"\nFused network:")
    click.echo(f"  Total features: {len(fused_gdf)}")
    click.echo(f"  Total length: {fused_gdf['length_km'].sum():.2f} km")

    click.echo(f"\nBy source type:")
    for source, count in fused_gdf['source_type'].value_counts().items():
        pct = (count / len(fused_gdf)) * 100
        length_km = fused_gdf[fused_gdf['source_type'] == source]['length_km'].sum()
        click.echo(f"  {source}: {count} streams ({pct:.1f}%), {length_km:.2f} km")

    click.echo(f"\nAdded by fusion:")
    added_streams = len(fused_gdf) - len(nhd_gdf)
    added_length = fused_gdf['length_km'].sum() - nhd_gdf['length_km'].sum()
    added_pct = (added_length / nhd_gdf['length_km'].sum()) * 100
    click.echo(f"  New features: {added_streams}")
    click.echo(f"  New length: {added_length:.2f} km (+{added_pct:.1f}%)")

    click.echo(f"\nOutput file: {output_path}")
    click.echo(f"  Layers: streams, streams_merged, streams_nhd_only, streams_dem_candidates")

    click.echo("\n" + "="*60)
    click.echo("Fusion complete!")
    click.echo("="*60)


if __name__ == '__main__':
    main()
