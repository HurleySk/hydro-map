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
import numpy as np
import geopandas as gpd


def calculate_drainage_areas_from_flow_acc(streams_gdf, flow_acc_path):
    """
    Calculate drainage area for each stream from flow accumulation raster.

    Samples flow accumulation at downstream endpoint and converts to km².
    """
    import rasterio
    from rasterio.transform import rowcol

    with rasterio.open(flow_acc_path) as src:
        # Get pixel area in km²
        if src.crs.is_geographic:
            # Geographic CRS: approximate using latitude
            pixel_width_deg = abs(src.transform[0])
            pixel_height_deg = abs(src.transform[4])
            center_lat = (src.bounds.top + src.bounds.bottom) / 2
            pixel_width_km = pixel_width_deg * 111.32 * np.cos(np.radians(center_lat))
            pixel_height_km = pixel_height_deg * 111.32
            pixel_area_km2 = pixel_width_km * pixel_height_km
        else:
            # Projected CRS: assume meters
            pixel_width_m = abs(src.transform[0])
            pixel_height_m = abs(src.transform[4])
            pixel_area_km2 = (pixel_width_m * pixel_height_m) / 1e6

        drainage_areas = []

        for idx, row in streams_gdf.iterrows():
            geom = row.geometry
            # Get downstream point (last coordinate)
            if geom.geom_type == 'LineString':
                downstream_point = geom.coords[-1]
            elif geom.geom_type == 'MultiLineString':
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
                if src.nodata is not None and flow_accum_value == src.nodata:
                    drainage_area_km2 = np.nan
                else:
                    drainage_area_km2 = flow_accum_value * pixel_area_km2
            else:
                drainage_area_km2 = np.nan

            drainage_areas.append(drainage_area_km2)

        streams_gdf['drainage_area_sqkm'] = drainage_areas

    return streams_gdf


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
    default=100,
    help='Flow accumulation threshold for stream initiation (cells)'
)
@click.option(
    '--multi-threshold',
    is_flag=True,
    help='Extract streams at multiple thresholds (100, 250, 500, 1000) for fusion workflow'
)
@click.option(
    '--dem',
    type=click.Path(exists=True),
    help='Optional DEM for stream attributes'
)
def main(flow_acc, flow_dir, output, threshold, multi_threshold, dem):
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

    # Determine thresholds to process
    if multi_threshold:
        thresholds = [100, 250, 500, 1000]
        click.echo(f"Multi-threshold mode: extracting streams at {thresholds} cells")
    else:
        thresholds = [threshold]
        click.echo(f"Extracting streams with threshold: {threshold} cells")

    # Process each threshold
    for t in thresholds:
        layer_name = 'streams' if len(thresholds) == 1 else f'streams_t{t}'
        click.echo(f"\n{'='*60}")
        click.echo(f"Processing threshold: {t} cells → layer: {layer_name}")
        click.echo(f"{'='*60}")

        extract_streams_at_threshold(
            wbt=wbt,
            flow_acc_path=flow_acc_path,
            flow_dir_path=flow_dir_path,
            output_path=output_path,
            threshold=t,
            layer_name=layer_name,
            temp_dir=temp_dir
        )


def extract_streams_at_threshold(wbt, flow_acc_path, flow_dir_path, output_path, threshold, layer_name, temp_dir):
    """Extract stream network at a specific threshold."""

    # Ensure temp directory exists
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Set WhiteboxTools working directory to absolute temp dir path
    abs_temp_dir = temp_dir.absolute()
    wbt.set_working_dir(str(abs_temp_dir))

    # Threshold-specific temporary files (use absolute paths for WhiteboxTools)
    streams_raster = abs_temp_dir / f"streams_t{threshold}.tif"
    stream_order = abs_temp_dir / f"stream_order_t{threshold}.tif"
    streams_vector = abs_temp_dir / f"streams_raw_t{threshold}.shp"

    # Use absolute paths for all inputs/outputs
    abs_flow_acc = Path(flow_acc_path).absolute()
    abs_flow_dir = Path(flow_dir_path).absolute()

    with tqdm(total=3, desc=f"Threshold {threshold}") as pbar:
        # Step 1: Extract streams from flow accumulation
        pbar.set_description(f"Extracting streams (t={threshold})")
        wbt.extract_streams(
            flow_accum=str(abs_flow_acc),
            output=str(streams_raster),
            threshold=threshold
        )
        pbar.update(1)

        # Step 2: Compute stream order
        pbar.set_description(f"Computing stream order (t={threshold})")
        wbt.strahler_stream_order(
            d8_pntr=str(abs_flow_dir),
            streams=str(streams_raster),
            output=str(stream_order)
        )
        pbar.update(1)

        # Step 3: Vectorize streams
        pbar.set_description(f"Vectorizing streams (t={threshold})")
        wbt.raster_streams_to_vector(
            streams=str(streams_raster),
            d8_pntr=str(abs_flow_dir),
            output=str(streams_vector)
        )
        pbar.update(1)

    # Convert to GeoPackage with geopandas
    click.echo("Converting to GeoPackage...")
    try:
        import rasterio
        from rasterio.transform import rowcol
        from shapely.geometry import Point

        # Check if file exists
        if not streams_vector.exists():
            click.echo(f"  Error: WhiteboxTools output not found at {streams_vector}")
            click.echo(f"  Checking for files in {temp_dir}...")
            import os
            files = list(temp_dir.glob("*"))
            click.echo(f"  Found {len(files)} files: {[f.name for f in files[:10]]}")
            raise FileNotFoundError(f"Stream vector output not created: {streams_vector}")

        streams_gdf = gpd.read_file(str(streams_vector))

        # WhiteboxTools doesn't create .prj files, so set CRS from flow direction raster
        if streams_gdf.crs is None:
            with rasterio.open(flow_dir_path) as src:
                streams_gdf = streams_gdf.set_crs(src.crs)

        # Add stream order by sampling the raster at stream midpoints
        click.echo("  Sampling stream order...")
        orders = []
        with rasterio.open(stream_order) as src:
            for idx, row in streams_gdf.iterrows():
                # Get midpoint of stream segment
                midpoint = row.geometry.interpolate(0.5, normalized=True)

                # Transform to raster CRS if needed
                if streams_gdf.crs != src.crs:
                    midpoint_gdf = gpd.GeoDataFrame([1], geometry=[midpoint], crs=streams_gdf.crs)
                    midpoint_proj = midpoint_gdf.to_crs(src.crs).geometry.values[0]
                else:
                    midpoint_proj = midpoint

                # Sample raster at midpoint
                r, c = rowcol(src.transform, midpoint_proj.x, midpoint_proj.y)

                # Check bounds and read value
                if 0 <= r < src.height and 0 <= c < src.width:
                    order_value = src.read(1, window=((r, r+1), (c, c+1)))[0, 0]
                    # Handle nodata
                    if src.nodata is not None and order_value == src.nodata:
                        order_value = 1
                else:
                    order_value = 1

                orders.append(int(order_value))

        streams_gdf['order'] = orders

        # Add flow accumulation threshold value for reference
        streams_gdf['flow_accum_threshold'] = threshold

        # Calculate length
        streams_gdf_proj = streams_gdf.to_crs("EPSG:6933")  # Equal Earth
        streams_gdf['length_m'] = streams_gdf_proj.geometry.length
        streams_gdf['length_km'] = streams_gdf['length_m'] / 1000

        # Calculate drainage area from flow accumulation
        click.echo("  Calculating drainage areas from flow accumulation...")
        streams_gdf = calculate_drainage_areas_from_flow_acc(
            streams_gdf, flow_acc_path
        )

        # Save to GeoPackage
        # Check if file exists to determine if we append or create new
        if output_path.exists():
            # Append to existing GeoPackage
            streams_gdf.to_file(output_path, driver='GPKG', layer=layer_name)
        else:
            # Create new GeoPackage
            streams_gdf.to_file(output_path, driver='GPKG', layer=layer_name)

        click.echo(f"\n  Stream extraction complete for threshold {threshold}!")
        click.echo(f"  Output: {output_path} (layer: {layer_name})")
        click.echo(f"  Number of stream segments: {len(streams_gdf)}")
        click.echo(f"  Total length: {streams_gdf['length_km'].sum():.2f} km")
        if len(streams_gdf) > 0:
            click.echo(f"  Order distribution:")
            for order in sorted(streams_gdf['order'].unique()):
                count = (streams_gdf['order'] == order).sum()
                pct = (count / len(streams_gdf)) * 100
                click.echo(f"    Order {int(order)}: {count} ({pct:.1f}%)")

    except ImportError:
        click.echo("Warning: geopandas not available, saving as shapefile only")
        click.echo(f"  Output: {streams_vector}")

    # Clean up temp files (optional)
    # import shutil
    # shutil.rmtree(temp_dir)


if __name__ == '__main__':
    main()
