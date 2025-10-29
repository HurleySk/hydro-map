from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
import rasterio
from rasterio.transform import rowcol
from shapely.geometry import LineString, Point
import geopandas as gpd
import numpy as np
from pathlib import Path

from app.config import settings
from app.services.watershed import transform_coordinates_to_raster_crs


router = APIRouter()


class CrossSectionRequest(BaseModel):
    """Request model for cross-section generation."""
    line: List[List[float]] = Field(
        ...,
        description="Line coordinates as [[lon, lat], [lon, lat], ...]",
        min_length=2
    )
    sample_distance: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Sample distance in meters (defaults to server setting)"
    )


class CrossSectionResponse(BaseModel):
    """Response model for cross-section."""
    profile: List[dict]  # Array of {distance, elevation, lat, lon}
    geology: List[dict]  # Array of geology contacts
    metadata: dict


@router.post("/cross-section", response_model=CrossSectionResponse)
async def generate_cross_section(request: CrossSectionRequest):
    """
    Generate elevation and geology cross-section along a line.

    This endpoint:
    1. Samples elevation along the line at specified intervals
    2. Identifies where the line crosses geological unit boundaries
    3. Returns elevation profile with geology contacts
    """
    sample_distance = request.sample_distance or settings.CROSS_SECTION_SAMPLE_DISTANCE

    try:
        # Create LineString from coordinates
        line_coords = [(lon, lat) for lon, lat in request.line]
        line = LineString(line_coords)

        # Generate elevation profile
        profile = await sample_elevation_profile(line, sample_distance)

        # Get geology contacts
        geology = await get_geology_contacts(line)

        return {
            "profile": profile,
            "geology": geology,
            "metadata": {
                "sample_distance_m": sample_distance,
                "total_distance_m": profile[-1]["distance"] if profile else 0,
                "num_samples": len(profile),
                "num_geology_contacts": len(geology)
            }
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Required data files not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cross-section generation failed: {str(e)}"
        )


async def sample_elevation_profile(
    line: LineString,
    sample_distance: int
) -> List[dict]:
    """
    Sample elevation along a line at regular intervals.

    Args:
        line: Shapely LineString in WGS84 (lon/lat)
        sample_distance: Sample interval in meters

    Returns:
        List of {distance, elevation, lat, lon} dictionaries
    """
    dem_path = Path(settings.DEM_PATH)
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM file not found: {dem_path}")

    # Project line to equal-area CRS for distance calculations
    gdf = gpd.GeoDataFrame([1], geometry=[line], crs="EPSG:4326")
    gdf_proj = gdf.to_crs("EPSG:6933")  # Equal Earth
    line_proj = gdf_proj.geometry.values[0]

    # Calculate number of samples
    total_length = line_proj.length
    num_samples = min(
        int(total_length / sample_distance) + 1,
        settings.CROSS_SECTION_MAX_POINTS
    )

    # Generate sample points along projected line
    distances = np.linspace(0, total_length, num_samples)
    sample_points_proj = [line_proj.interpolate(d) for d in distances]

    # Convert back to WGS84
    gdf_samples = gpd.GeoDataFrame(geometry=sample_points_proj, crs="EPSG:6933")
    gdf_samples_wgs84 = gdf_samples.to_crs("EPSG:4326")

    # Sample elevation from DEM
    profile = []
    with rasterio.open(dem_path) as dem_src:
        for i, point in enumerate(gdf_samples_wgs84.geometry):
            lon, lat = point.x, point.y

            # Transform coordinates to DEM CRS
            x, y = transform_coordinates_to_raster_crs(lon, lat, dem_src.crs)

            # Get elevation value
            row, col = rowcol(dem_src.transform, x, y)

            if 0 <= row < dem_src.height and 0 <= col < dem_src.width:
                elevation = float(dem_src.read(1, window=((row, row+1), (col, col+1)))[0, 0])

                # Check for nodata
                if dem_src.nodata is not None and elevation == dem_src.nodata:
                    elevation = None
            else:
                elevation = None

            profile.append({
                "distance": float(distances[i]),
                "elevation": elevation,
                "lat": lat,
                "lon": lon
            })

    return profile


async def get_geology_contacts(line: LineString) -> List[dict]:
    """
    Find where a line crosses geological unit boundaries.

    Args:
        line: Shapely LineString in WGS84

    Returns:
        List of geology contact dictionaries with formation info
    """
    geology_path = Path(settings.GEOLOGY_PATH)
    if not geology_path.exists():
        # Return empty list if no geology data
        return []

    try:
        # Read geology data
        geology_gdf = gpd.read_file(geology_path)

        # Ensure same CRS
        line_gdf = gpd.GeoDataFrame([1], geometry=[line], crs="EPSG:4326")
        if geology_gdf.crs != line_gdf.crs:
            geology_gdf = geology_gdf.to_crs(line_gdf.crs)

        # Find intersecting geology polygons
        intersecting = geology_gdf[geology_gdf.intersects(line)]

        if len(intersecting) == 0:
            return []

        # Project to equal-area for distance calculation
        line_gdf_proj = line_gdf.to_crs("EPSG:6933")
        line_proj = line_gdf_proj.geometry.values[0]
        intersecting_proj = intersecting.to_crs("EPSG:6933")

        # Find contact points
        contacts = []
        for idx, row in intersecting_proj.iterrows():
            intersection = line_proj.intersection(row.geometry)

            if intersection.is_empty:
                continue

            # Get the distance along the line
            if intersection.geom_type == 'LineString':
                # Line segment - use start and end
                start_dist = line_proj.project(Point(intersection.coords[0]))
                end_dist = line_proj.project(Point(intersection.coords[-1]))
            elif intersection.geom_type == 'MultiLineString':
                # Multiple segments - use first and last
                coords = [coord for geom in intersection.geoms for coord in geom.coords]
                start_dist = line_proj.project(Point(coords[0]))
                end_dist = line_proj.project(Point(coords[-1]))
            elif intersection.geom_type == 'Point':
                start_dist = end_dist = line_proj.project(intersection)
            else:
                continue

            # Extract formation attributes
            formation_name = row.get('UNIT_NAME', row.get('name', 'Unknown'))
            rock_type = row.get('ROCKTYPE1', row.get('type', 'Unknown'))
            age = row.get('MIN_AGE', row.get('age', None))

            contacts.append({
                "start_distance": float(start_dist),
                "end_distance": float(end_dist),
                "formation": str(formation_name),
                "rock_type": str(rock_type),
                "age": str(age) if age else None,
                "color": _get_geology_color(rock_type)
            })

        # Sort by start distance
        contacts.sort(key=lambda x: x["start_distance"])

        return contacts

    except Exception as e:
        print(f"Warning: Failed to process geology data: {e}")
        return []


def _get_geology_color(rock_type: str) -> str:
    """
    Get a color for a rock type.

    This is a simple mapping - you can customize based on your data.
    """
    colors = {
        "sandstone": "#E6C896",
        "shale": "#96826E",
        "limestone": "#A0B4C8",
        "granite": "#E69696",
        "basalt": "#646464",
        "metamorphic": "#C89696",
        "sedimentary": "#C8B496",
        "igneous": "#966464",
    }

    rock_type_lower = str(rock_type).lower()
    for key, color in colors.items():
        if key in rock_type_lower:
            return color

    return "#CCCCCC"  # Default gray
