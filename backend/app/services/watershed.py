"""
Watershed delineation service using WhiteboxTools and rasterio.

This module provides functions for:
- Snapping pour points to streams or high flow accumulation cells
- Delineating watersheds from pour points
- Computing watershed statistics
"""

from collections import deque
from pathlib import Path
from typing import Dict, Optional, Tuple
import asyncio
import numpy as np
import rasterio
from rasterio.transform import rowcol
from rasterio.features import shapes
from rasterio.crs import CRS
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union
import geopandas as gpd
from pyproj import Transformer
import json

from app.config import settings


def transform_coordinates_to_raster_crs(
    lon: float, lat: float, raster_crs: CRS
) -> Tuple[float, float]:
    """
    Transform WGS84 lon/lat coordinates to raster CRS.

    Args:
        lon: Longitude in WGS84
        lat: Latitude in WGS84
        raster_crs: Target CRS from rasterio

    Returns:
        Tuple of (x, y) in raster CRS
    """
    # If already in WGS84, return as-is
    if raster_crs == CRS.from_epsg(4326):
        return lon, lat

    # Create transformer from WGS84 to raster CRS
    transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y


def calculate_snap_radius_pixels(
    radius_meters: int, raster_crs: CRS, center_lon: float, center_lat: float, pixel_size: Tuple[float, float]
) -> int:
    """
    Calculate snap radius in pixels, accounting for CRS.

    Args:
        radius_meters: Desired radius in meters
        raster_crs: CRS of the raster
        center_lon: Center longitude in WGS84
        center_lat: Center latitude in WGS84
        pixel_size: (x_size, y_size) from raster.res

    Returns:
        Radius in pixels
    """
    # For WGS84, use approximate conversion (meters per degree at latitude)
    if raster_crs == CRS.from_epsg(4326):
        meters_per_degree = 111320 * np.cos(np.radians(center_lat))
        radius_degrees = radius_meters / meters_per_degree
        pixel_radius = int(radius_degrees / min(pixel_size[0], abs(pixel_size[1])))
    else:
        # For projected CRS, pixel size is already in meters (or similar units)
        pixel_radius = int(radius_meters / min(abs(pixel_size[0]), abs(pixel_size[1])))

    return max(1, pixel_radius)


def calculate_distance_meters(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> float:
    """
    Calculate distance between two WGS84 points using Haversine formula.

    Args:
        lon1, lat1: First point
        lon2, lat2: Second point

    Returns:
        Distance in meters
    """
    # Use GeoDataFrame for accurate distance calculation
    p1 = Point(lon1, lat1)
    p2 = Point(lon2, lat2)
    gdf1 = gpd.GeoDataFrame([1], geometry=[p1], crs="EPSG:4326")
    gdf2 = gpd.GeoDataFrame([1], geometry=[p2], crs="EPSG:4326")

    # Project to equal-area CRS
    gdf1_proj = gdf1.to_crs("EPSG:6933")
    gdf2_proj = gdf2.to_crs("EPSG:6933")

    return gdf1_proj.geometry.distance(gdf2_proj.geometry).values[0]


async def snap_pour_point(lat: float, lon: float, radius: int = 100) -> Dict:
    """
    Async wrapper around the synchronous pour-point snapping routine.
    """
    return await asyncio.to_thread(_snap_pour_point_sync, lat, lon, radius)


def _snap_pour_point_sync(lat: float, lon: float, radius: int = 100) -> Dict:
    """
    Snap a pour point to the nearest high-accumulation cell within a given radius.

    Args:
        lat: Latitude of original pour point
        lon: Longitude of original pour point
        radius: Search radius in meters

    Returns:
        GeoJSON Feature with snapped point location and metadata
    """
    # Check if flow accumulation file exists
    flow_acc_path = Path(settings.FLOW_ACC_PATH)
    if not flow_acc_path.exists():
        # Return original point if no flow accumulation available
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "snapped": False,
                "original_lat": lat,
                "original_lon": lon,
                "reason": "Flow accumulation file not found"
            }
        }

    with rasterio.open(flow_acc_path) as src:
        # Transform coordinates from WGS84 to raster CRS
        x, y = transform_coordinates_to_raster_crs(lon, lat, src.crs)

        # Convert to raster row/col
        row, col = rowcol(src.transform, x, y)

        # Calculate pixel radius based on raster resolution and CRS
        pixel_radius = calculate_snap_radius_pixels(
            radius, src.crs, lon, lat, src.res
        )

        # Define search window
        row_min = max(0, row - pixel_radius)
        row_max = min(src.height, row + pixel_radius + 1)
        col_min = max(0, col - pixel_radius)
        col_max = min(src.width, col + pixel_radius + 1)

        # Read flow accumulation window
        window = rasterio.windows.Window(
            col_min, row_min,
            col_max - col_min, row_max - row_min
        )
        flow_acc = src.read(1, window=window)

        # Find maximum accumulation cell in window
        if flow_acc.size == 0 or np.all(flow_acc == src.nodata):
            # No valid data in window, return original point
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "snapped": False,
                    "original_lat": lat,
                    "original_lon": lon,
                    "reason": "No valid flow accumulation data in search radius"
                }
            }

        # Mask nodata values
        if src.nodata is not None:
            flow_acc = np.ma.masked_equal(flow_acc, src.nodata)

        # Find cell with maximum accumulation
        max_idx = np.unravel_index(np.ma.argmax(flow_acc), flow_acc.shape)
        snapped_row = row_min + max_idx[0]
        snapped_col = col_min + max_idx[1]

        # Convert back to raster CRS coordinates
        snapped_x, snapped_y = src.xy(snapped_row, snapped_col)
        max_accumulation = float(flow_acc[max_idx])

        # Transform snapped coordinates back to WGS84
        if src.crs == CRS.from_epsg(4326):
            snapped_lon, snapped_lat = snapped_x, snapped_y
        else:
            transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            snapped_lon, snapped_lat = transformer.transform(snapped_x, snapped_y)

    # Calculate accurate distance in meters
    snap_distance = calculate_distance_meters(lon, lat, snapped_lon, snapped_lat)

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [snapped_lon, snapped_lat]
        },
        "properties": {
            "snapped": True,
            "original_lat": lat,
            "original_lon": lon,
            "snap_distance_m": float(snap_distance),
            "flow_accumulation": max_accumulation
        }
    }


async def delineate_watershed(lat: float, lon: float) -> Dict:
    """
    Delineate watershed from a pour point using D8 flow direction.

    Args:
        lat: Latitude of pour point (should be snapped)
        lon: Longitude of pour point (should be snapped)

    Returns:
        Dictionary with watershed GeoJSON and statistics
    """
    flow_dir_path = Path(settings.FLOW_DIR_PATH)
    if not flow_dir_path.exists():
        raise FileNotFoundError(f"Flow direction file not found: {flow_dir_path}")

    with rasterio.open(flow_dir_path) as flow_dir_src:
        # Transform pour point from WGS84 to raster CRS
        x, y = transform_coordinates_to_raster_crs(lon, lat, flow_dir_src.crs)

        # Convert to raster row/col
        row, col = rowcol(flow_dir_src.transform, x, y)

        if row < 0 or row >= flow_dir_src.height or col < 0 or col >= flow_dir_src.width:
            raise ValueError("Pour point is outside the DEM extent")

        # Read flow direction
        flow_dir = flow_dir_src.read(1)

        # Trace watershed using D8 flow direction
        # D8 flow direction values: 1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE
        watershed_mask = trace_watershed_d8(flow_dir, row, col, flow_dir_src.nodata)

        # Convert mask to polygon
        watershed_polygons = []
        for geom, value in shapes(
            watershed_mask.astype(np.uint8),
            mask=(watershed_mask == 1),
            transform=flow_dir_src.transform
        ):
            if value == 1:
                watershed_polygons.append(shape(geom))

        if not watershed_polygons:
            raise ValueError("Could not delineate watershed - no contributing area found")

        # Merge polygons if multiple
        watershed_geom = unary_union(watershed_polygons)

        # Calculate statistics
        statistics = await calculate_watershed_statistics(
            watershed_geom=watershed_geom,
            watershed_mask=watershed_mask,
            crs=flow_dir_src.crs
        )

    return {
        "watershed": {
            "type": "Feature",
            "geometry": mapping(watershed_geom),
            "properties": statistics
        },
        "statistics": statistics
    }


def trace_watershed_d8(flow_dir: np.ndarray, outlet_row: int, outlet_col: int, nodata: Optional[float] = None) -> np.ndarray:
    """
    Trace watershed upstream from outlet using D8 flow direction.

    Args:
        flow_dir: D8 flow direction array
        outlet_row: Row index of outlet
        outlet_col: Column index of outlet
        nodata: NoData value in flow direction array

    Returns:
        Binary mask where 1 = in watershed, 0 = outside
    """
    rows, cols = flow_dir.shape
    watershed = np.zeros((rows, cols), dtype=bool)

    # D8 flow direction lookup: direction value -> (row_offset, col_offset)
    d8_lookup = {
        1: (0, 1),    # E
        2: (1, 1),    # SE
        4: (1, 0),    # S
        8: (1, -1),   # SW
        16: (0, -1),  # W
        32: (-1, -1), # NW
        64: (-1, 0),  # N
        128: (-1, 1)  # NE
    }

    # Reverse lookup: which cells flow TO a given cell
    reverse_lookup = {
        1: 16,   # E flows from W
        2: 32,   # SE flows from NW
        4: 64,   # S flows from N
        8: 128,  # SW flows from NE
        16: 1,   # W flows from E
        32: 2,   # NW flows from SE
        64: 4,   # N flows from S
        128: 8   # NE flows from SW
    }

    # Breadth-first search to find all cells that flow to the outlet
    queue = deque([(outlet_row, outlet_col)])
    watershed[outlet_row, outlet_col] = True

    while queue:
        r, c = queue.popleft()

        # Check all 8 neighbors
        for direction, (dr, dc) in d8_lookup.items():
            nr, nc = r + dr, c + dc

            # Check bounds
            if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                continue

            # Skip if already processed
            if watershed[nr, nc]:
                continue

            # Skip nodata cells
            if nodata is not None and flow_dir[nr, nc] == nodata:
                continue

            # Check if this neighbor flows to current cell
            neighbor_flow_dir = flow_dir[nr, nc]
            if neighbor_flow_dir == reverse_lookup.get(direction):
                watershed[nr, nc] = True
                queue.append((nr, nc))

    return watershed.astype(np.uint8)


async def calculate_watershed_statistics(
    watershed_geom,
    watershed_mask: np.ndarray,
    crs
) -> Dict:
    """
    Calculate statistics for a delineated watershed.

    Args:
        watershed_geom: Shapely geometry of watershed
        watershed_mask: Binary mask of watershed
        crs: Coordinate reference system

    Returns:
        Dictionary of watershed statistics
    """
    # Calculate area
    # Transform to equal-area projection for accurate area calculation
    gdf = gpd.GeoDataFrame([1], geometry=[watershed_geom], crs=crs)
    gdf_area = gdf.to_crs("EPSG:6933")  # Equal Earth projection
    area_m2 = gdf_area.geometry.area.values[0]
    area_km2 = area_m2 / 1_000_000
    area_mi2 = area_m2 / 2_589_988

    # Calculate perimeter
    perimeter_m = gdf_area.geometry.length.values[0]
    perimeter_km = perimeter_m / 1000

    # Number of cells
    num_cells = int(np.sum(watershed_mask))

    statistics = {
        "area_km2": round(area_km2, 4),
        "area_mi2": round(area_mi2, 4),
        "area_m2": round(area_m2, 2),
        "perimeter_km": round(perimeter_km, 4),
        "perimeter_m": round(perimeter_m, 2),
        "num_cells": num_cells,
    }

    # Add DEM statistics if available
    try:
        dem_path = Path(settings.DEM_PATH)
        if dem_path.exists():
            with rasterio.open(dem_path) as dem_src:
                # Read DEM values within watershed as a masked array to drop nodata efficiently
                dem_data = dem_src.read(1, masked=True)
                watershed_elevations = dem_data[np.asarray(watershed_mask, dtype=bool)]

                if np.ma.is_masked(watershed_elevations):
                    watershed_elevations = watershed_elevations.compressed()

                if len(watershed_elevations) > 0:
                    statistics.update({
                        "elevation_min_m": float(np.min(watershed_elevations)),
                        "elevation_max_m": float(np.max(watershed_elevations)),
                        "elevation_mean_m": float(np.mean(watershed_elevations)),
                        "elevation_std_m": float(np.std(watershed_elevations)),
                    })
    except Exception as e:
        print(f"Warning: Could not calculate DEM statistics: {e}")

    return statistics
