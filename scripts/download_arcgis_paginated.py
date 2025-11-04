#!/usr/bin/env python3
"""
Download large ArcGIS FeatureServer layers using pagination.

The ArcGIS REST API limits result size, so this script paginates through
all features using resultOffset and resultRecordCount parameters.
"""

import requests
import json
from pathlib import Path
from typing import Dict, List
import time

# Target dataset
DATASET = {
    "name": "inadequate_outfalls",
    "url": "https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/Inadequate_Outfalls/FeatureServer/0",
    "output_dir": Path(__file__).parent.parent / "data" / "raw" / "fairfax"
}

# AOI bounding box (WGS84)
AOI_BBOX = (-77.5, 38.6, -76.9, 39.0)  # minx, miny, maxx, maxy

# Pagination settings
BATCH_SIZE = 50  # Features per request (reduced from 1000 due to large geometries)
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def query_features(url: str, offset: int, count: int, bbox: tuple) -> Dict:
    """
    Query features from ArcGIS REST endpoint with pagination.

    Args:
        url: FeatureServer layer URL
        offset: Result offset (starting position)
        count: Number of features to return
        bbox: Bounding box (minx, miny, maxx, maxy)

    Returns:
        GeoJSON FeatureCollection dict
    """
    params = {
        "where": "1=1",  # Get all features
        "outFields": "*",  # All fields
        "geometry": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",  # Input spatial reference (WGS84)
        "outSR": "4326",  # Output spatial reference (WGS84)
        "resultOffset": offset,
        "resultRecordCount": count,
        "f": "geojson"
    }

    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Requesting offset {offset}, count {count} (attempt {attempt + 1}/{MAX_RETRIES})...", end=" ", flush=True)
            response = requests.get(f"{url}/query", params=params, timeout=120)
            response.raise_for_status()

            data = response.json()
            feature_count = len(data.get("features", []))
            print(f"received {feature_count} features")

            return data

        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"failed: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"  Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise

    return {"type": "FeatureCollection", "features": []}


def download_layer(name: str, url: str, output_dir: Path, bbox: tuple, batch_size: int = BATCH_SIZE):
    """
    Download entire layer using pagination.

    Args:
        name: Dataset name
        url: FeatureServer layer URL
        output_dir: Output directory
        bbox: Bounding box
        batch_size: Features per batch
    """
    output_file = output_dir / f"{name}.geojson"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"Downloading: {name}")
    print(f"{'='*70}")
    print(f"Source: {url}")
    print(f"Output: {output_file}")
    print(f"Batch size: {batch_size}")

    # Initialize combined GeoJSON
    combined = {
        "type": "FeatureCollection",
        "features": []
    }

    # Paginate through all features
    offset = 0
    total_features = 0

    while True:
        batch = query_features(url, offset, batch_size, bbox)
        features = batch.get("features", [])

        if not features:
            print(f"  No more features at offset {offset}")
            break

        combined["features"].extend(features)
        total_features += len(features)
        offset += batch_size

        print(f"  Total features collected: {total_features}")

        # Check if we got fewer features than requested (last page)
        if len(features) < batch_size:
            print(f"  Last page reached ({len(features)} < {batch_size})")
            break

    # Write combined GeoJSON
    print(f"\nWriting {total_features} features to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(combined, f)

    # Verify output
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"Download complete: {output_file.name} ({size_mb:.1f} MB, {total_features} features)")

    return output_file


def main():
    """Download inadequate_outfalls dataset."""
    print(f"\n{'='*70}")
    print("ARCGIS PAGINATED DOWNLOAD")
    print(f"{'='*70}")
    print(f"Dataset: {DATASET['name']}")
    print(f"URL: {DATASET['url']}")
    print(f"AOI: {AOI_BBOX}")
    print(f"Batch size: {BATCH_SIZE}")

    try:
        output_file = download_layer(
            DATASET["name"],
            DATASET["url"],
            DATASET["output_dir"],
            AOI_BBOX,
            BATCH_SIZE
        )

        print(f"\n{'='*70}")
        print("SUCCESS")
        print(f"{'='*70}")
        print(f"Downloaded: {output_file}")
        print("\nNext step:")
        print("  python scripts/prepare_fairfax_stormwater.py")

        return 0

    except Exception as e:
        print(f"\n{'='*70}")
        print("ERROR")
        print(f"{'='*70}")
        print(f"Failed to download: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
