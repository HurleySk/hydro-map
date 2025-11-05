from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
from pathlib import Path
import math
import os
from threading import Lock
import rasterio
from datetime import datetime

from app.config import settings
from app.services.dem_sampling import sample_dem_rasters


router = APIRouter()


# Module-level cache for GeoDataFrames with mtime-based invalidation
_dataset_cache: Dict[str, Dict] = {}
_cache_lock = Lock()


def _load_dataset_cached(file_path: str, layer: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """
    Load a GeoDataFrame with caching and mtime-based invalidation.

    Args:
        file_path: Path to GeoPackage file
        layer: Optional layer name for GeoPackage

    Returns:
        GeoDataFrame or None if file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        return None

    cache_key = f"{file_path}:{layer}" if layer else file_path
    current_mtime = os.path.getmtime(path)

    with _cache_lock:
        if cache_key in _dataset_cache:
            cached_mtime = _dataset_cache[cache_key]['mtime']
            if cached_mtime == current_mtime:
                # Cache hit with valid mtime
                return _dataset_cache[cache_key]['gdf']

        # Cache miss or stale - load from disk
        try:
            if layer:
                gdf = gpd.read_file(file_path, layer=layer)
            else:
                gdf = gpd.read_file(file_path)

            # Store in cache
            _dataset_cache[cache_key] = {
                'gdf': gdf,
                'mtime': current_mtime
            }
            return gdf
        except Exception as e:
            print(f"Error loading {file_path} (layer={layer}): {e}")
            return None


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


def query_features_with_fallback(
    gdf: gpd.GeoDataFrame,
    point: Point,
    buffer_m: float,
    max_distance_m: float = 250,
    crs_proj: str = "EPSG:6933"
) -> tuple[gpd.GeoDataFrame, bool]:
    """
    Query features using spatial index with nearest-feature fallback.

    Uses spatial index and bbox prefiltering for performance. If no features
    intersect the buffer, falls back to finding the nearest feature within
    max_distance_m.

    Args:
        gdf: GeoDataFrame to query
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters
        max_distance_m: Maximum distance for nearest-feature fallback
        crs_proj: Projected CRS for accurate distance calculations

    Returns:
        Tuple of (GeoDataFrame with matching features, is_nearest flag)
        is_nearest is True if fallback to nearest-feature was used
    """
    # Create buffer in projected CRS
    point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs="EPSG:4326")
    point_gdf_proj = point_gdf.to_crs(crs_proj)
    buffer_geom_proj = point_gdf_proj.geometry.buffer(buffer_m).values[0]

    # Convert buffer back to WGS84 for querying
    buffer_gdf = gpd.GeoDataFrame([1], geometry=[buffer_geom_proj], crs=crs_proj)
    buffer_wgs84 = buffer_gdf.to_crs("EPSG:4326").geometry.values[0]

    # Use spatial index to prefilter candidates by bbox
    if hasattr(gdf, 'sindex') and gdf.sindex is not None:
        possible_matches_idx = list(gdf.sindex.intersection(buffer_wgs84.bounds))
        possible_matches = gdf.iloc[possible_matches_idx]
    else:
        # Fall back to full dataset if no spatial index
        possible_matches = gdf

    # Filter by actual intersection
    intersecting = possible_matches[possible_matches.intersects(buffer_wgs84)]

    if len(intersecting) > 0:
        return intersecting, False

    # Fallback: Find nearest feature within max_distance
    # Project to accurate CRS for distance calculation
    gdf_proj = gdf.to_crs(crs_proj)
    point_proj = point_gdf_proj.geometry.values[0]

    # Calculate distances to all features
    distances = gdf_proj.geometry.apply(lambda geom: geom.distance(point_proj))

    # Filter by max distance
    within_max = distances <= max_distance_m

    if not within_max.any():
        # No features within max distance
        return gpd.GeoDataFrame(), False

    # Get the nearest feature(s)
    min_distance = distances[within_max].min()
    nearest_mask = (distances == min_distance) & within_max
    nearest_features = gdf[nearest_mask]

    return nearest_features, True


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
    layers_to_query = request.layers or ["geology"]

    features = {}
    all_warnings = []

    # Query geology
    if "geology" in layers_to_query:
        geology_features, warnings = await query_geology(point, request.buffer)
        all_warnings.extend(warnings)
        if geology_features:
            features["geology"] = geology_features

    # Query inadequate outfalls
    if "inadequate-outfalls" in layers_to_query:
        outfalls_features, warnings = await query_inadequate_outfalls(point, request.buffer)
        all_warnings.extend(warnings)
        if outfalls_features:
            features["inadequate_outfalls"] = outfalls_features

    # Query Fairfax watersheds (always query - provides useful context)
    watersheds_data, warnings = await query_fairfax_watersheds(point)
    all_warnings.extend(warnings)
    if watersheds_data:
        features["fairfax_watersheds"] = watersheds_data

    # Sample DEM rasters (always sample - provides useful context)
    dem_data, warnings = sample_dem_rasters(request.lon, request.lat)
    all_warnings.extend(warnings)
    if dem_data:
        features["dem_samples"] = dem_data

    # Build response with canonical structure
    return {
        "location": {"lat": request.lat, "lon": request.lon},
        "query": {
            "buffer_m": request.buffer,
            "layers": layers_to_query
        },
        "features": features,
        "num_features": sum(len(v) if isinstance(v, list) else 1 for v in features.values()),
        "warnings": all_warnings if all_warnings else None,
        "metadata": {
            "datasets": list(set([
                "streams_nhd" if "streams" in features else None,
                "geology" if "geology" in features else None,
                "fairfax_watersheds" if "fairfax_watersheds" in features else None,
                "dem" if "dem_samples" in features else None
            ]) - {None})
        }
    }


async def query_streams(
    point: Point,
    buffer_m: float,
    layer_id: str = "streams-nhd"
) -> tuple[Optional[List[Dict]], List[Dict]]:
    """
    Query stream features near a point.

    Args:
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters
        layer_id: Layer identifier (streams-nhd, streams-dem)

    Returns:
        Tuple of (list of stream feature dictionaries or None, list of warnings)
    """
    warnings = []

    # Get dataset path from config
    if layer_id not in settings.LAYER_DATASET_MAP:
        warning_msg = f"Unknown layer ID '{layer_id}'"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_streams"})
        return None, warnings

    file_path, layer_name = settings.LAYER_DATASET_MAP[layer_id]
    streams_path = Path(file_path)

    if not streams_path.exists():
        warning_msg = f"Stream dataset not found at {streams_path}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_streams"})
        return None, warnings

    # Extract source type from layer_id
    source_type = "nhd" if "nhd" in layer_id else "dem" if "dem" in layer_id else "unknown"

    try:
        # Read streams (with caching)
        streams_gdf = _load_dataset_cached(str(streams_path), layer=layer_name)
        if streams_gdf is None:
            warnings.append({"level": "error", "message": "Failed to load stream dataset", "source": "query_streams"})
            return None, warnings

        # Use spatial index query with nearest-feature fallback
        matching_gdf, is_nearest = query_features_with_fallback(
            streams_gdf, point, buffer_m, max_distance_m=250
        )

        if len(matching_gdf) == 0:
            warnings.append({"level": "info", "message": f"No streams found within 250m (layer: {layer_id})", "source": "query_streams"})
            return None, warnings

        # Add warning if nearest-feature fallback was used
        if is_nearest:
            warnings.append({
                "level": "info",
                "message": f"No streams in buffer ({buffer_m}m), showing nearest within 250m",
                "source": "query_streams"
            })

        # Extract attributes and calculate distances
        features = []
        for idx, row in matching_gdf.iterrows():
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
                # Add distance and source information
                "distance_meters": round(distance, 1),
                "source_type": source_type,
                "is_nearest": is_nearest
            }
            features.append(feature)

        # Sort by distance, closest first
        features.sort(key=lambda x: x['distance_meters'])

        # Limit to top 3 closest features
        if len(features) > 3:
            warnings.append({
                "level": "info",
                "message": f"Found {len(features)} streams, showing closest 3",
                "source": "query_streams"
            })
            features = features[:3]

        return features if features else None, warnings

    except Exception as e:
        warning_msg = f"Failed to query streams from {layer_id}: {e}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_streams"})
        return None, warnings


async def query_fairfax_watersheds(point: Point) -> tuple[Optional[Dict], List[Dict]]:
    """
    Query Fairfax County watershed containing a point.

    Args:
        point: Shapely Point in WGS84

    Returns:
        Tuple of (dictionary with Fairfax watershed info or None, list of warnings)
    """
    warnings = []
    watersheds_path = Path(settings.FAIRFAX_WATERSHEDS_PATH)

    if not watersheds_path.exists():
        warning_msg = f"Fairfax watersheds dataset not found at {watersheds_path}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_fairfax_watersheds"})
        return None, warnings

    try:
        # Read Fairfax watersheds (with caching)
        watersheds_gdf = _load_dataset_cached(str(watersheds_path))
        if watersheds_gdf is None:
            warnings.append({"level": "error", "message": "Failed to load Fairfax watersheds dataset", "source": "query_fairfax_watersheds"})
            return None, warnings

        # Ensure same CRS
        if watersheds_gdf.crs != "EPSG:4326":
            watersheds_gdf = watersheds_gdf.to_crs("EPSG:4326")

        # Use spatial index to prefilter candidates
        if hasattr(watersheds_gdf, 'sindex') and watersheds_gdf.sindex is not None:
            possible_matches_idx = list(watersheds_gdf.sindex.intersection(point.bounds))
            candidates = watersheds_gdf.iloc[possible_matches_idx]
        else:
            candidates = watersheds_gdf

        # Find containing watershed (point can only be in one)
        containing = candidates[candidates.contains(point)]

        if len(containing) > 0:
            # Get first (and only) containing watershed
            row = containing.iloc[0]

            return {
                "name": str(row['name']),
                "area_sqkm": float(row['area_sqkm']) if 'area_sqkm' in row else None,
                "web_address": str(row['web_address']) if 'web_address' in row else None
            }, warnings

        warnings.append({"level": "info", "message": "Point not within any Fairfax County watershed", "source": "query_fairfax_watersheds"})
        return None, warnings

    except Exception as e:
        warning_msg = f"Failed to query Fairfax watersheds: {e}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_fairfax_watersheds"})
        return None, warnings


async def query_geology(point: Point, buffer_m: float) -> tuple[Optional[List[Dict]], List[Dict]]:
    """
    Query geology features at a point.

    Uses two-stage approach:
    1. Check if point is contained in any polygon (use spatial index for prefilter)
    2. If not, find nearest polygons within buffer using spatial index

    Args:
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters

    Returns:
        Tuple of (list of geology feature dictionaries or None, list of warnings)
    """
    warnings = []
    geology_path = Path(settings.GEOLOGY_PATH)

    if not geology_path.exists():
        warning_msg = f"Geology dataset not found at {geology_path}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_geology"})
        return None, warnings

    try:
        # Read geology (with caching)
        geology_gdf = _load_dataset_cached(str(geology_path))
        if geology_gdf is None:
            warnings.append({"level": "error", "message": "Failed to load geology dataset", "source": "query_geology"})
            return None, warnings

        # Ensure same CRS
        if geology_gdf.crs != "EPSG:4326":
            geology_gdf = geology_gdf.to_crs("EPSG:4326")

        features = []

        # FIRST: Find all polygons that CONTAIN the click point (with spatial index)
        # Use spatial index to prefilter by point bounds
        if hasattr(geology_gdf, 'sindex') and geology_gdf.sindex is not None:
            possible_matches_idx = list(geology_gdf.sindex.intersection(point.bounds))
            candidates = geology_gdf.iloc[possible_matches_idx]
        else:
            candidates = geology_gdf

        containing = candidates[candidates.contains(point)]

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

                # Truncate description to 280 chars
                if description and len(description) > 280:
                    description = description[:277] + "..."

                formation = str(row.get('unit', row.get('UNIT_NAME', row.get('ORIG_LABEL', 'Unknown'))))

                feature = {
                    "type": "geology",
                    "formation": formation,
                    "map_unit": formation,  # Use formation as map_unit (no separate field in data)
                    "rock_type": rock_type,
                    "age": str(row.get('age', row.get('MIN_AGE', row.get('AGE', 'Unknown')))),
                    "description": description,
                    "distance_to_contact_m": 0.0,
                    "precision": "exact",
                    "is_nearest": False,
                    "source": "geology.gpkg",
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
            # SECOND: If no polygon contains the point, use spatial query with fallback
            matching_gdf, is_nearest = query_features_with_fallback(
                geology_gdf, point, buffer_m, max_distance_m=250
            )

            if len(matching_gdf) == 0:
                warnings.append({"level": "info", "message": "No geology features found within 250m", "source": "query_geology"})
                return None, warnings

            # Add warning if nearest-feature fallback was used
            if is_nearest:
                warnings.append({
                    "level": "info",
                    "message": f"No geology in buffer ({buffer_m}m), showing nearest within 250m",
                    "source": "query_geology"
                })

            for idx, row in matching_gdf.iterrows():
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

                # Truncate description to 280 chars
                if description and len(description) > 280:
                    description = description[:277] + "..."

                formation = str(row.get('unit', row.get('UNIT_NAME', row.get('ORIG_LABEL', 'Unknown'))))
                distance_rounded = round(distance, 1)

                # Determine precision based on distance
                if distance_rounded == 0:
                    precision = "exact"
                elif distance_rounded < 10:
                    precision = "near_boundary"
                else:
                    precision = "approximate"

                feature = {
                    "type": "geology",
                    "formation": formation,
                    "map_unit": formation,  # Use formation as map_unit (no separate field in data)
                    "rock_type": rock_type,
                    "age": str(row.get('age', row.get('MIN_AGE', row.get('AGE', 'Unknown')))),
                    "description": description,
                    "distance_to_contact_m": distance_rounded,
                    "precision": precision,
                    "is_nearest": is_nearest,
                    "source": "geology.gpkg"
                }
                features.append(feature)

            # Sort by distance, closest first
            features.sort(key=lambda x: x['distance_to_contact_m'])

            # Limit to top 3 closest features
            if len(features) > 3:
                warnings.append({
                    "level": "info",
                    "message": f"Found {len(features)} geology features, showing closest 3",
                    "source": "query_geology"
                })
                features = features[:3]

        return features if features else None, warnings

    except Exception as e:
        warning_msg = f"Failed to query geology: {e}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_geology"})
        return None, warnings


async def query_inadequate_outfalls(point: Point, buffer_m: float) -> tuple[Optional[List[Dict]], List[Dict]]:
    """
    Query inadequate outfalls features at a point.

    Uses two-stage approach:
    1. Check if point is contained in any drainage area polygon
    2. If not, find nearest drainage areas within buffer using spatial index

    Args:
        point: Shapely Point in WGS84
        buffer_m: Buffer distance in meters

    Returns:
        Tuple of (list of inadequate outfall feature dictionaries or None, list of warnings)
    """
    warnings = []

    # Get path from LAYER_DATASET_MAP
    if "inadequate-outfalls" not in settings.LAYER_DATASET_MAP:
        warning_msg = "Inadequate outfalls layer not configured"
        warnings.append({"level": "error", "message": warning_msg, "source": "query_inadequate_outfalls"})
        return None, warnings

    outfalls_path_str, layer_name = settings.LAYER_DATASET_MAP["inadequate-outfalls"]
    outfalls_path = Path(outfalls_path_str)

    if not outfalls_path.exists():
        warning_msg = f"Inadequate outfalls dataset not found at {outfalls_path}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_inadequate_outfalls"})
        return None, warnings

    try:
        # Read inadequate outfalls (with caching)
        outfalls_gdf = _load_dataset_cached(str(outfalls_path), layer_name)
        if outfalls_gdf is None:
            warnings.append({"level": "error", "message": "Failed to load inadequate outfalls dataset", "source": "query_inadequate_outfalls"})
            return None, warnings

        # Ensure same CRS
        if outfalls_gdf.crs != "EPSG:4326":
            outfalls_gdf = outfalls_gdf.to_crs("EPSG:4326")

        features = []

        # FIRST: Find all polygons that CONTAIN the click point (with spatial index)
        if hasattr(outfalls_gdf, 'sindex') and outfalls_gdf.sindex is not None:
            possible_matches_idx = list(outfalls_gdf.sindex.intersection(point.bounds))
            candidates = outfalls_gdf.iloc[possible_matches_idx]
        else:
            candidates = outfalls_gdf

        containing = candidates[candidates.contains(point)]

        if len(containing) > 0:
            # If multiple polygons contain the point, prefer the smallest (most specific drainage area)
            containing_proj = containing.to_crs("EPSG:6933")  # Equal Earth for area calculation
            containing_areas = containing_proj.area

            for idx, row in containing.iterrows():
                area_sqm = containing_areas.loc[idx]

                # Extract fields from the data
                outfall_id = str(row.get('INADEQUATE_OUTFALL_ID', row.get('inadequate_outfall_id', 'Unknown')))
                determination = str(row.get('DETERMINATION', row.get('determination', 'Unknown')))
                drainage_area_sqkm = float(row.get('DRAINAGE_AREA', row.get('drainage_area', 0.0)))
                watershed = str(row.get('WATERSHED', row.get('watershed', 'Unknown')))
                data_source = str(row.get('DATA_SOURCE', row.get('data_source', 'Unknown')))

                feature = {
                    "type": "inadequate_outfall",
                    "outfall_id": outfall_id,
                    "determination": determination,
                    "drainage_area_sqkm": round(drainage_area_sqkm, 2),
                    "watershed": watershed,
                    "data_source": data_source,
                    "distance_meters": 0.0,
                    "precision": "exact",
                    "is_nearest": False,
                    "source": "inadequate_outfalls.gpkg",
                    "_area_sqm": area_sqm  # Internal use for sorting
                }
                features.append(feature)

            # Sort by area (smallest first) - show smaller, more specific drainage areas first
            features.sort(key=lambda x: x['_area_sqm'])

            # Remove internal area field - return ALL containing polygons
            for f in features:
                del f['_area_sqm']
            # Return all features (drainage areas can overlap, unlike geology)

        else:
            # SECOND: If no polygon contains the point, use spatial query with fallback
            matching_gdf, is_nearest = query_features_with_fallback(
                outfalls_gdf, point, buffer_m, max_distance_m=250
            )

            if len(matching_gdf) == 0:
                warnings.append({"level": "info", "message": "No inadequate outfalls found within 250m", "source": "query_inadequate_outfalls"})
                return None, warnings

            # Add warning if nearest-feature fallback was used
            if is_nearest:
                warnings.append({
                    "level": "info",
                    "message": f"No inadequate outfalls in buffer ({buffer_m}m), showing nearest within 250m",
                    "source": "query_inadequate_outfalls"
                })

            for idx, row in matching_gdf.iterrows():
                polygon_geom = row.geometry

                # Calculate distance to boundary
                nearest_pt_on_boundary, _ = nearest_points(polygon_geom.boundary, point)
                distance = calculate_distance_meters(point, nearest_pt_on_boundary)

                # Extract fields from the data
                outfall_id = str(row.get('INADEQUATE_OUTFALL_ID', row.get('inadequate_outfall_id', 'Unknown')))
                determination = str(row.get('DETERMINATION', row.get('determination', 'Unknown')))
                drainage_area_sqkm = float(row.get('DRAINAGE_AREA', row.get('drainage_area', 0.0)))
                watershed = str(row.get('WATERSHED', row.get('watershed', 'Unknown')))
                data_source = str(row.get('DATA_SOURCE', row.get('data_source', 'Unknown')))
                distance_rounded = round(distance, 1)

                # Determine precision based on distance
                if distance_rounded == 0:
                    precision = "exact"
                elif distance_rounded < 10:
                    precision = "near_boundary"
                else:
                    precision = "approximate"

                feature = {
                    "type": "inadequate_outfall",
                    "outfall_id": outfall_id,
                    "determination": determination,
                    "drainage_area_sqkm": round(drainage_area_sqkm, 2),
                    "watershed": watershed,
                    "data_source": data_source,
                    "distance_meters": distance_rounded,
                    "precision": precision,
                    "is_nearest": is_nearest,
                    "source": "inadequate_outfalls.gpkg"
                }
                features.append(feature)

            # Sort by distance, closest first
            features.sort(key=lambda x: x['distance_meters'])

            # Limit to top 3 closest features
            if len(features) > 3:
                warnings.append({
                    "level": "info",
                    "message": f"Found {len(features)} inadequate outfalls, showing closest 3",
                    "source": "query_inadequate_outfalls"
                })
                features = features[:3]

        return features if features else None, warnings

    except Exception as e:
        warning_msg = f"Failed to query inadequate outfalls: {e}"
        print(f"Warning: {warning_msg}")
        warnings.append({"level": "error", "message": warning_msg, "source": "query_inadequate_outfalls"})
        return None, warnings


def check_vector_dataset_health(path: str, layer: Optional[str] = None) -> dict:
    """
    Check health of a vector dataset (GeoPackage).

    Args:
        path: Path to GeoPackage file
        layer: Optional layer name within GeoPackage

    Returns:
        Health status dict with status, message, and metadata
    """
    file_path = Path(path)

    # Check if file exists
    if not file_path.exists():
        return {
            "status": "unhealthy",
            "message": f"File not found: {path}",
            "exists": False,
            "readable": False,
            "feature_count": None,
            "crs": None
        }

    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        return {
            "status": "unhealthy",
            "message": f"File not readable: {path}",
            "exists": True,
            "readable": False,
            "feature_count": None,
            "crs": None
        }

    # Try to load dataset
    try:
        gdf = gpd.read_file(file_path, layer=layer)

        return {
            "status": "healthy",
            "message": "Dataset loaded successfully",
            "exists": True,
            "readable": True,
            "feature_count": len(gdf),
            "crs": str(gdf.crs) if gdf.crs else None,
            "bounds": list(gdf.total_bounds) if len(gdf) > 0 else None,
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Failed to load dataset: {str(e)}",
            "exists": True,
            "readable": True,
            "feature_count": None,
            "crs": None,
            "error": str(e)
        }


def check_raster_health(path: str) -> dict:
    """
    Check health of a raster dataset (GeoTIFF).

    Args:
        path: Path to GeoTIFF file

    Returns:
        Health status dict with status, message, and metadata
    """
    file_path = Path(path)

    # Check if file exists
    if not file_path.exists():
        return {
            "status": "unhealthy",
            "message": f"File not found: {path}",
            "exists": False,
            "readable": False,
            "width": None,
            "height": None,
            "crs": None
        }

    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        return {
            "status": "unhealthy",
            "message": f"File not readable: {path}",
            "exists": True,
            "readable": False,
            "width": None,
            "height": None,
            "crs": None
        }

    # Try to open raster
    try:
        with rasterio.open(file_path) as src:
            return {
                "status": "healthy",
                "message": "Raster opened successfully",
                "exists": True,
                "readable": True,
                "width": src.width,
                "height": src.height,
                "crs": str(src.crs) if src.crs else None,
                "bounds": list(src.bounds),
                "dtype": str(src.dtypes[0]),
                "nodata": src.nodata,
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Failed to open raster: {str(e)}",
            "exists": True,
            "readable": True,
            "width": None,
            "height": None,
            "crs": None,
            "error": str(e)
        }


def check_all_datasets_health() -> dict:
    """
    Check health of all datasets used by feature-info endpoint.

    Returns:
        Dictionary with overall status and individual dataset health
    """
    datasets = {}

    # Check vector datasets
    for layer_id, (file_path, layer_name) in settings.LAYER_DATASET_MAP.items():
        datasets[layer_id] = check_vector_dataset_health(file_path, layer_name)

    # Check raster datasets
    datasets["dem"] = check_raster_health(settings.DEM_PATH)
    datasets["slope"] = check_raster_health("../data/processed/dem/slope_deg.tif")
    datasets["aspect"] = check_raster_health("../data/processed/dem/aspect_deg.tif")

    # Determine overall status
    statuses = [d["status"] for d in datasets.values()]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
        overall_message = "All datasets are healthy"
    elif any(s == "healthy" for s in statuses):
        overall_status = "degraded"
        unhealthy_count = sum(1 for s in statuses if s == "unhealthy")
        overall_message = f"{unhealthy_count} dataset(s) unavailable"
    else:
        overall_status = "unhealthy"
        overall_message = "All datasets are unavailable"

    return {
        "status": overall_status,
        "message": overall_message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "datasets": datasets
    }


@router.get("/feature-info/status")
async def get_feature_info_status(
    layer: Optional[str] = Query(None, description="Check specific layer (e.g., 'streams-nhd', 'geology', 'dem')")
):
    """
    Health check endpoint for feature-info datasets.

    Returns health status of all datasets used by the feature-info endpoint,
    or a specific dataset if layer parameter is provided.

    Query Parameters:
        layer: Optional layer ID to check (e.g., 'streams-nhd', 'geology', 'dem', 'slope', 'aspect')

    Returns:
        Overall health status and individual dataset health information
    """
    # If specific layer requested, check only that dataset
    if layer:
        # Check if it's a vector dataset
        if layer in settings.LAYER_DATASET_MAP:
            file_path, layer_name = settings.LAYER_DATASET_MAP[layer]
            result = check_vector_dataset_health(file_path, layer_name)
            return {
                "layer": layer,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **result
            }

        # Check if it's a raster dataset
        raster_paths = {
            "dem": settings.DEM_PATH,
            "slope": "../data/processed/dem/slope_deg.tif",
            "aspect": "../data/processed/dem/aspect_deg.tif"
        }

        if layer in raster_paths:
            result = check_raster_health(raster_paths[layer])
            return {
                "layer": layer,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **result
            }

        # Unknown layer
        raise HTTPException(
            status_code=404,
            detail=f"Unknown layer: {layer}. Available layers: {list(settings.LAYER_DATASET_MAP.keys()) + list(raster_paths.keys())}"
        )

    # Return health of all datasets
    return check_all_datasets_health()
