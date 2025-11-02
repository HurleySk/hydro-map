from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
from pathlib import Path
import math

from app.config import settings


router = APIRouter()


def calculate_distance_meters(point1: Point, point2: Point) -> float:
    """
    Calculate distance between two WGS84 points in meters using Haversine formula.

    Args:
        point1: First point (lon, lat)
        point2: Second point (lon, lat)

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters

    lat1 = math.radians(point1.y)
    lat2 = math.radians(point2.y)
    dlat = math.radians(point2.y - point1.y)
    dlon = math.radians(point2.x - point1.x)

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


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

        # Extract attributes and calculate distances
        features = []
        for idx, row in intersecting.iterrows():
            # Calculate distance to the nearest point on the stream
            stream_geom = row.geometry
            nearest_pt_on_stream, _ = nearest_points(stream_geom, point)
            distance = calculate_distance_meters(point, nearest_pt_on_stream)

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
                # Add distance
                "distance_meters": round(distance, 1)
            }
            features.append(feature)

        # Sort by distance, closest first
        features.sort(key=lambda x: x['distance_meters'])

        # Limit to top 3 closest features
        features = features[:3] if len(features) > 3 else features

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

        features = []

        # FIRST: Find all polygons that CONTAIN the click point
        containing = geology_gdf[geology_gdf.contains(point)]

        if len(containing) > 0:
            # If multiple polygons contain the point, calculate their areas and prefer the smallest
            containing_proj = containing.to_crs("EPSG:6933")  # Equal Earth for area calculation
            containing_areas = containing_proj.area

            for idx, row in containing.iterrows():
                area_sqm = containing_areas.loc[idx]

                # Use our normalized field names from prepare_geology.py
                rock_type = str(row.get('rock_type', row.get('ROCKTYPE1', row.get('GENERALIZE', 'Unknown'))))
                description = str(row.get('description', row.get('UNIT_DESCR', row.get('GENERALIZE', ''))))

                # Don't include description if it's the same as rock_type
                if description == rock_type:
                    description = ''

                feature = {
                    "type": "geology",
                    "formation": str(row.get('unit', row.get('UNIT_NAME', row.get('ORIG_LABEL', 'Unknown')))),
                    "rock_type": rock_type,
                    "age": str(row.get('age', row.get('MIN_AGE', row.get('AGE', 'Unknown')))),
                    "description": description,
                    "distance_meters": 0.0,
                    "_area_sqm": area_sqm  # Internal use for sorting
                }
                features.append(feature)

            # Sort by area (smallest first) - prefer smaller, more specific polygons
            features.sort(key=lambda x: x['_area_sqm'])

            # Remove internal area field and limit to top feature
            for f in features:
                del f['_area_sqm']
            features = features[:1]  # Only return the smallest containing polygon

        else:
            # SECOND: If no polygon contains the point, find nearby polygons within buffer
            # Create buffer in degrees (approximate)
            # 1 degree latitude ≈ 111 km
            # 1 degree longitude ≈ 111 km * cos(latitude)
            import math
            lat_deg_per_m = 1 / 111000
            lon_deg_per_m = 1 / (111000 * math.cos(math.radians(point.y)))
            buffer_deg = max(buffer_m * lat_deg_per_m, buffer_m * lon_deg_per_m)

            # Create buffered point for intersection testing
            buffered_point = point.buffer(buffer_deg)

            # Find intersecting polygons
            intersecting = geology_gdf[geology_gdf.intersects(buffered_point)]

            for idx, row in intersecting.iterrows():
                polygon_geom = row.geometry

                # Calculate distance to boundary
                nearest_pt_on_boundary, _ = nearest_points(polygon_geom.boundary, point)
                distance = calculate_distance_meters(point, nearest_pt_on_boundary)

                # Use our normalized field names from prepare_geology.py
                rock_type = str(row.get('rock_type', row.get('ROCKTYPE1', row.get('GENERALIZE', 'Unknown'))))
                description = str(row.get('description', row.get('UNIT_DESCR', row.get('GENERALIZE', ''))))

                # Don't include description if it's the same as rock_type
                if description == rock_type:
                    description = ''

                feature = {
                    "type": "geology",
                    "formation": str(row.get('unit', row.get('UNIT_NAME', row.get('ORIG_LABEL', 'Unknown')))),
                    "rock_type": rock_type,
                    "age": str(row.get('age', row.get('MIN_AGE', row.get('AGE', 'Unknown')))),
                    "description": description,
                    "distance_meters": round(distance, 1)
                }
                features.append(feature)

            # Sort by distance, closest first
            features.sort(key=lambda x: x['distance_meters'])

            # Limit to top 3 closest features
            features = features[:3] if len(features) > 3 else features

        return features if features else None

    except Exception as e:
        print(f"Warning: Failed to query geology: {e}")
        return None
