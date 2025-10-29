"""
Watershed delineation service using WhiteboxTools and rasterio.

This module provides functions for:
- Snapping pour points to streams or high flow accumulation cells
- Delineating watersheds from pour points
- Computing watershed statistics
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import rasterio
from rasterio.transform import rowcol
from rasterio.features import shapes
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union
import geopandas as gpd
from pyproj import Transformer
import json

from app.config import settings


async def snap_pour_point(lat: float, lon: float, radius: int = 100) -> Dict:
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
        # Convert lat/lon to raster coordinates
        row, col = rowcol(src.transform, lon, lat)

        # Calculate pixel radius based on raster resolution
        pixel_size_x, pixel_size_y = src.res
        pixel_radius = int(radius / min(pixel_size_x, abs(pixel_size_y)))

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

        # Convert back to geographic coordinates
        snapped_lon, snapped_lat = src.xy(snapped_row, snapped_col)
        max_accumulation = float(flow_acc[max_idx])

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
            "snap_distance_m": float(((snapped_lat - lat) ** 2 + (snapped_lon - lon) ** 2) ** 0.5 * 111320),
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
        # Convert pour point to raster coordinates
        row, col = rowcol(flow_dir_src.transform, lon, lat)

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
    queue = [(outlet_row, outlet_col)]
    watershed[outlet_row, outlet_col] = True

    while queue:
        r, c = queue.pop(0)

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
                # Read DEM values within watershed
                dem_data = dem_src.read(1)
                watershed_elevations = dem_data[watershed_mask == 1]

                # Mask nodata
                if dem_src.nodata is not None:
                    watershed_elevations = watershed_elevations[watershed_elevations != dem_src.nodata]

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
