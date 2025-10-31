from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

from app.config import settings


router = APIRouter()


class FeatureInfoRequest(BaseModel):
    """Request model for feature information."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    layers: Optional[List[str]] = Field(
        default=None,
        description="Specific layers to query (e.g., ['streams', 'geology'])"
    )
    buffer: Optional[float] = Field(
        default=10,
        ge=0,
        le=1000,
        description="Search buffer in meters"
    )


@router.post("/feature-info")
async def get_feature_info(request: FeatureInfoRequest):
    """
    Get information about features at a clicked location.

    Queries available data layers (streams, geology, etc.) within a buffer
    of the clicked point and returns feature attributes.
    """
    point = Point(request.lon, request.lat)
    layers_to_query = request.layers or ["streams", "geology"]

    features = {}

    # Query streams
    if "streams" in layers_to_query:
        streams_features = await query_streams(point, request.buffer)
        if streams_features:
            features["streams"] = streams_features

    # Query geology
    if "geology" in layers_to_query:
        geology_features = await query_geology(point, request.buffer)
        if geology_features:
            features["geology"] = geology_features

    return {
        "location": {"lat": request.lat, "lon": request.lon},
        "features": features,
        "num_features": sum(len(v) for v in features.values())
    }


async def query_streams(point: Point, buffer_m: float) -> Optional[List[Dict]]:
    """
    Query stream features near a point.

    Args:
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters

    Returns:
        List of stream feature dictionaries or None
    """
    streams_path = Path(settings.STREAMS_PATH)
    if not streams_path.exists():
        return None

    try:
        # Read streams
        streams_gdf = gpd.read_file(streams_path, layer='streams')

        # Create buffer around point
        point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs="EPSG:4326")
        point_gdf_proj = point_gdf.to_crs("EPSG:6933")  # Equal Earth
        buffer_geom = point_gdf_proj.geometry.buffer(buffer_m).values[0]

        # Back to WGS84
        buffer_gdf = gpd.GeoDataFrame([1], geometry=[buffer_geom], crs="EPSG:6933")
        buffer_wgs84 = buffer_gdf.to_crs("EPSG:4326").geometry.values[0]

        # Find intersecting streams
        intersecting = streams_gdf[streams_gdf.intersects(buffer_wgs84)]

        if len(intersecting) == 0:
            return None

        # Extract attributes
        features = []
        for idx, row in intersecting.iterrows():
            feature = {
                "type": "stream",
                "name": row.get('name', row.get('GNIS_NAME', 'Unnamed')),
                "length_km": float(row.get('length_km', row.get('LengthKM', 0))),
                # NHD Plus VAA attributes
                "drainage_area_sqkm": float(row['drainage_area_sqkm']) if 'drainage_area_sqkm' in row and row['drainage_area_sqkm'] is not None else None,
                "stream_order": int(row['stream_order']) if 'stream_order' in row and row['stream_order'] is not None else None,
                "upstream_length_km": float(row['upstream_length_km']) if 'upstream_length_km' in row and row['upstream_length_km'] is not None else None,
                "slope": float(row['slope']) if 'slope' in row and row['slope'] is not None else None,
                "max_elev_m": float(row['max_elev_m']) if 'max_elev_m' in row and row['max_elev_m'] is not None else None,
                "min_elev_m": float(row['min_elev_m']) if 'min_elev_m' in row and row['min_elev_m'] is not None else None,
                "stream_type": str(row['stream_type']) if 'stream_type' in row and row['stream_type'] is not None else None,
                # Keep legacy 'order' field for compatibility
                "order": int(row.get('stream_order', row.get('StreamOrde', row.get('order', 0)))),
            }
            features.append(feature)

        return features if features else None

    except Exception as e:
        print(f"Warning: Failed to query streams: {e}")
        return None


async def query_geology(point: Point, buffer_m: float) -> Optional[List[Dict]]:
    """
    Query geology features at a point.

    Args:
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters

    Returns:
        List of geology feature dictionaries or None
    """
    geology_path = Path(settings.GEOLOGY_PATH)
    if not geology_path.exists():
        return None

    try:
        # Read geology
        geology_gdf = gpd.read_file(geology_path)

        # Ensure same CRS
        if geology_gdf.crs != "EPSG:4326":
            geology_gdf = geology_gdf.to_crs("EPSG:4326")

        # Find containing polygon
        containing = geology_gdf[geology_gdf.contains(point)]

        features = []
        for idx, row in containing.iterrows():
            feature = {
                "type": "geology",
                "formation": str(row.get('UNIT_NAME', row.get('name', 'Unknown'))),
                "rock_type": str(row.get('ROCKTYPE1', row.get('type', 'Unknown'))),
                "age": str(row.get('MIN_AGE', row.get('age', 'Unknown'))),
                "description": str(row.get('UNIT_DESCR', row.get('description', ''))),
            }
            features.append(feature)

        return features if features else None

    except Exception as e:
        print(f"Warning: Failed to query geology: {e}")
        return None
