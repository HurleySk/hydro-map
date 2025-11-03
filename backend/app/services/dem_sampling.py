"""
DEM and terrain raster sampling utilities.

Provides functions for sampling elevation, slope, aspect, and flow accumulation
at point locations for feature information queries.
"""

from typing import Optional, Dict
from pathlib import Path
import rasterio
from rasterio.transform import rowcol
from pyproj import CRS, Transformer

from app.config import settings


def transform_coordinates_to_raster_crs(
    lon: float, lat: float, raster_crs: CRS
) -> tuple[float, float]:
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


def sample_raster_at_point(
    lon: float,
    lat: float,
    raster_path: str
) -> Optional[float]:
    """
    Sample a raster value at a single point location.

    Args:
        lon: Longitude in WGS84
        lat: Latitude in WGS84
        raster_path: Path to raster file

    Returns:
        Raster value at point, or None if outside bounds or nodata
    """
    raster_file = Path(raster_path)
    if not raster_file.exists():
        print(f"Warning: Raster file not found: {raster_path}")
        return None

    try:
        with rasterio.open(raster_file) as src:
            # Transform coordinates to raster CRS
            x, y = transform_coordinates_to_raster_crs(lon, lat, src.crs)

            # Get pixel row/col
            row, col = rowcol(src.transform, x, y)

            # Check bounds
            if 0 <= row < src.height and 0 <= col < src.width:
                # Read single pixel value
                value = float(src.read(1, window=((row, row+1), (col, col+1)))[0, 0])

                # Check for nodata
                if src.nodata is not None and value == src.nodata:
                    return None

                return value
            else:
                return None

    except Exception as e:
        print(f"Warning: Failed to sample raster {raster_path}: {e}")
        return None


def aspect_to_cardinal(degrees: float) -> str:
    """
    Convert aspect in degrees (0-360) to cardinal direction.

    0/360 = North, 90 = East, 180 = South, 270 = West

    Args:
        degrees: Aspect in degrees (0-360)

    Returns:
        Cardinal direction string (N, NE, E, SE, S, SW, W, NW)
    """
    # Normalize to 0-360
    degrees = degrees % 360

    # 8 cardinal directions with 45-degree sectors
    # N: 337.5-22.5, NE: 22.5-67.5, E: 67.5-112.5, etc.
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((degrees + 22.5) / 45) % 8

    return directions[index]


def sample_dem_rasters(lon: float, lat: float) -> tuple[Optional[Dict], list[Dict]]:
    """
    Sample all DEM-derived rasters at a point location.

    Samples elevation, slope, and aspect.

    Args:
        lon: Longitude in WGS84
        lat: Latitude in WGS84

    Returns:
        Tuple of (dictionary with sampled values or None, list of warnings)
    """
    warnings = []

    # Sample each raster
    elevation = sample_raster_at_point(lon, lat, settings.DEM_PATH)
    slope = sample_raster_at_point(lon, lat, "../data/processed/dem/slope_deg.tif")
    aspect = sample_raster_at_point(lon, lat, "../data/processed/dem/aspect_deg.tif")

    # Track which rasters are missing
    missing_rasters = []
    if elevation is None:
        missing_rasters.append("elevation")
    if slope is None:
        missing_rasters.append("slope")
    if aspect is None:
        missing_rasters.append("aspect")

    # If all are None, point is outside DEM coverage
    if all(v is None for v in [elevation, slope, aspect]):
        warnings.append({
            "level": "info",
            "message": "Point outside DEM coverage area",
            "source": "dem_sampling"
        })
        return None, warnings

    # Add warning if some rasters are missing
    if missing_rasters:
        warnings.append({
            "level": "warning",
            "message": f"Some terrain data unavailable: {', '.join(missing_rasters)}",
            "source": "dem_sampling"
        })

    # Build response dict
    result = {
        "elevation_m": elevation,
        "slope_deg": slope,
        "aspect_deg": aspect
    }

    # Add cardinal direction if aspect is available
    if aspect is not None:
        result["aspect_cardinal"] = aspect_to_cardinal(aspect)

    return result, warnings
