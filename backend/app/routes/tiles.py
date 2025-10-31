"""
PMTiles serving endpoint with HTTP Range request support.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Response
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tiles", tags=["tiles"])

# Path to tiles directory
TILES_PATH = Path(__file__).parent.parent.parent.parent / "data" / "tiles"


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """
    Parse HTTP Range header and return start and end byte positions.

    Args:
        range_header: Range header value (e.g., "bytes=0-1023")
        file_size: Total size of the file

    Returns:
        Tuple of (start, end) byte positions
    """
    try:
        # Remove "bytes=" prefix
        range_spec = range_header.replace("bytes=", "")

        # Handle different range formats
        if range_spec.startswith("-"):
            # Suffix byte range (e.g., "-500" means last 500 bytes)
            suffix_length = int(range_spec[1:])
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif range_spec.endswith("-"):
            # Range from start to end of file (e.g., "500-")
            start = int(range_spec[:-1])
            end = file_size - 1
        else:
            # Standard range (e.g., "500-999")
            parts = range_spec.split("-")
            start = int(parts[0])
            end = int(parts[1])

        # Validate range
        if start < 0 or start >= file_size:
            start = 0
        if end >= file_size:
            end = file_size - 1
        if start > end:
            start = 0
            end = file_size - 1

        return start, end
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid range header: {range_header}, error: {e}")
        return 0, file_size - 1


@router.get("/{filename}")
async def serve_pmtiles(
    filename: str,
    range: Optional[str] = Header(None)
):
    """
    Serve PMTiles files with support for HTTP Range requests.

    This endpoint supports byte-range requests which are required by the
    PMTiles protocol for efficient tile loading.

    Args:
        filename: Name of the PMTiles file
        range: Optional HTTP Range header

    Returns:
        File response with appropriate headers for range requests
    """
    # Validate filename (prevent directory traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check if file exists
    file_path = TILES_PATH / filename
    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"PMTiles file not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    # Get file size
    file_size = file_path.stat().st_size

    # Handle range request
    if range:
        logger.debug(f"Range request for {filename}: {range}")
        start, end = parse_range_header(range, file_size)

        # Read the requested byte range
        with open(file_path, "rb") as f:
            f.seek(start)
            content_length = end - start + 1
            content = f.read(content_length)

        # Return 206 Partial Content response
        return Response(
            content=content,
            status_code=206,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(content_length),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )

    # Standard full file response
    logger.debug(f"Full file request for {filename}")
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.head("/{filename}")
async def head_pmtiles(filename: str):
    """
    Handle HEAD requests for PMTiles files.

    Returns metadata headers without the file body, used by frontend
    to check if tiles exist before attempting to load them.

    Args:
        filename: Name of the PMTiles file

    Returns:
        Response with headers only (no body)
    """
    # Validate filename (prevent directory traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check if file exists
    file_path = TILES_PATH / filename
    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"PMTiles file not found (HEAD): {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    # Get file size
    file_size = file_path.stat().st_size

    # Return headers only (no body for HEAD request)
    logger.debug(f"HEAD request for {filename}")
    return Response(
        content=None,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/")
async def list_tiles():
    """
    List available PMTiles files.

    Returns:
        List of available tile files with their sizes
    """
    if not TILES_PATH.exists():
        return {"tiles": [], "error": "Tiles directory not found"}

    tiles = []
    for file_path in TILES_PATH.glob("*.pmtiles"):
        tiles.append({
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
        })

    return {
        "tiles": sorted(tiles, key=lambda x: x["name"]),
        "total": len(tiles)
    }