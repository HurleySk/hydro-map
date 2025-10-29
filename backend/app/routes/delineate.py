from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import time

from app.services.watershed import delineate_watershed, snap_pour_point
from app.services.cache import get_cached_watershed, cache_watershed
from app.config import settings


router = APIRouter()


class DelineationRequest(BaseModel):
    """Request model for watershed delineation."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude of pour point")
    lon: float = Field(..., ge=-180, le=180, description="Longitude of pour point")
    snap_to_stream: Optional[bool] = Field(
        default=None,
        description="Whether to snap to nearest stream (defaults to server setting)"
    )
    snap_radius: Optional[int] = Field(
        default=None,
        ge=0,
        le=1000,
        description="Snap radius in meters (defaults to server setting)"
    )


class DelineationResponse(BaseModel):
    """Response model for watershed delineation."""
    watershed: dict  # GeoJSON polygon
    pour_point: dict  # GeoJSON point (snapped if applicable)
    statistics: dict
    metadata: dict


@router.post("/delineate", response_model=DelineationResponse)
async def delineate(request: DelineationRequest):
    """
    Delineate watershed from a pour point.

    This endpoint:
    1. Optionally snaps the pour point to the nearest stream
    2. Computes the upstream catchment using precomputed flow direction
    3. Returns the watershed polygon with statistics
    4. Caches results by snapped location for performance
    """
    start_time = time.time()

    # Use server defaults if not specified
    snap_to_stream = request.snap_to_stream if request.snap_to_stream is not None else settings.SNAP_TO_STREAM
    snap_radius = request.snap_radius if request.snap_radius is not None else settings.DEFAULT_SNAP_RADIUS

    try:
        # Step 1: Snap pour point if requested
        if snap_to_stream:
            snapped_point = await snap_pour_point(
                lat=request.lat,
                lon=request.lon,
                radius=snap_radius
            )
        else:
            snapped_point = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [request.lon, request.lat]
                },
                "properties": {
                    "snapped": False,
                    "original_lat": request.lat,
                    "original_lon": request.lon
                }
            }

        # Step 2: Check cache
        cache_key = f"{snapped_point['geometry']['coordinates'][1]:.6f},{snapped_point['geometry']['coordinates'][0]:.6f}"

        if settings.CACHE_ENABLED:
            cached_result = await get_cached_watershed(cache_key)
            if cached_result:
                return _hydrate_cached_response(
                    cached_result,
                    processing_time=time.time() - start_time
                )

        # Step 3: Delineate watershed
        watershed_result = await delineate_watershed(
            lat=snapped_point["geometry"]["coordinates"][1],
            lon=snapped_point["geometry"]["coordinates"][0]
        )

        # Step 4: Build response
        response = _build_delineation_response(
            watershed=watershed_result["watershed"],
            pour_point=snapped_point,
            statistics=watershed_result["statistics"],
            processing_time=time.time() - start_time,
            snap_radius=snap_radius if snap_to_stream else None,
            from_cache=False
        )

        # Step 5: Cache result
        if settings.CACHE_ENABLED:
            await cache_watershed(cache_key, response)

        return response

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Required data files not found: {str(e)}. Please run preprocessing scripts."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delineation failed: {str(e)}")


@router.get("/delineate/status")
async def delineation_status():
    """Check if delineation service is ready (required data files exist)."""
    from pathlib import Path

    required_files = {
        "dem": settings.DEM_PATH,
        "flow_direction": settings.FLOW_DIR_PATH,
        "flow_accumulation": settings.FLOW_ACC_PATH,
    }

    status = {}
    all_ready = True

    for name, path in required_files.items():
        exists = Path(path).exists()
        status[name] = {
            "path": path,
            "exists": exists
        }
        if not exists:
            all_ready = False

    return {
        "ready": all_ready,
        "files": status,
        "cache_enabled": settings.CACHE_ENABLED
    }


def _build_delineation_response(
    watershed: Dict[str, Any],
    pour_point: Dict[str, Any],
    statistics: Dict[str, Any],
    processing_time: float,
    snap_radius: Optional[int],
    from_cache: bool
) -> Dict[str, Any]:
    return {
        "watershed": watershed,
        "pour_point": pour_point,
        "statistics": statistics,
        "metadata": {
            "processing_time": processing_time,
            "snap_radius": snap_radius,
            "from_cache": from_cache
        }
    }


def _hydrate_cached_response(
    cached_response: Dict[str, Any],
    processing_time: float
) -> Dict[str, Any]:
    metadata = dict(cached_response.get("metadata", {}))
    metadata["processing_time"] = processing_time
    metadata["from_cache"] = True
    cached_response["metadata"] = metadata
    return cached_response
