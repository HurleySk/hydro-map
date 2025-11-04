#!/usr/bin/env python3
"""
Download Fairfax County hydrography datasets via ArcGIS REST API.

Downloads Water Features (lines and polygons) and Perennial Streams from
Fairfax County Open Data. Reprojects from State Plane feet to WGS84 and
clips to AOI bounding box.

Usage:
    python download_fairfax_hydro.py
"""

import subprocess
from pathlib import Path
import sys

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "fairfax"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# AOI bounding box (WGS84): Northern Virginia focus area
# Approximate extent covering Fairfax County
AOI_BBOX = (-77.5, 38.6, -76.9, 39.0)  # minx, miny, maxx, maxy

# Fairfax County ArcGIS REST endpoints
DATASETS = {
    "water_features_lines": {
        "url": "https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/Water_Features_lines/FeatureServer/0",
        "source_crs": "EPSG:3857",  # Web Mercator (from metadata)
        "fields": ["NAME", "TYPE", "STREAMORDER", "CENTERLINE", "SOURCE", "VISIBLE"]
    },
    "water_features_polys": {
        "url": "https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/Water_Features_polys/FeatureServer/0",
        "source_crs": "EPSG:3857",  # Web Mercator
        "fields": ["NAME", "TYPE", "SOURCE", "VISIBLE"]
    },
    "perennial_streams": {
        "url": "https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/OpenData_S14/FeatureServer/0",
        "source_crs": "EPSG:2283",  # State Plane VA feet (NAD83)
        "fields": ["NAME", "FTYPE", "FCODE", "VISIBLE", "SOURCE"]
    }
}


def download_layer(name: str, config: dict):
    """
    Download a single layer using ogr2ogr.

    Args:
        name: Dataset name (used for output filename)
        config: Dataset configuration with url, source_crs, fields
    """
    output_file = DATA_DIR / f"{name}.gpkg"

    print(f"\n{'='*70}")
    print(f"Downloading: {name}")
    print(f"{'='*70}")
    print(f"Source: {config['url']}")
    print(f"Output: {output_file}")

    # Build ogr2ogr command
    cmd = [
        "ogr2ogr",
        "-f", "GPKG",
        str(output_file),
        config["url"],
        "-t_srs", "EPSG:4326",  # Target: WGS84
        "-spat", str(AOI_BBOX[0]), str(AOI_BBOX[1]), str(AOI_BBOX[2]), str(AOI_BBOX[3]),
        "-spat_srs", "EPSG:4326",  # Spatial filter in WGS84
        "-progress",
        "-overwrite"
    ]

    # Add field selection if specified
    if config.get("fields"):
        # Note: ArcGIS REST doesn't support -select, will use all fields
        # Field filtering will happen in processing script
        pass

    # Execute download
    try:
        print(f"\nExecuting: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Show progress
        if result.stdout:
            print(result.stdout)

        # Verify output
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"\n✓ Download successful: {output_file.name} ({size_mb:.1f} MB)")
        else:
            print(f"\n✗ Download failed: {output_file.name} not created")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error downloading {name}:")
        print(e.stderr)
        return False

    return True


def verify_downloads():
    """Verify all downloads completed successfully."""
    print(f"\n{'='*70}")
    print("VERIFICATION")
    print(f"{'='*70}")

    all_success = True
    for name in DATASETS.keys():
        output_file = DATA_DIR / f"{name}.gpkg"
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"✓ {name}.gpkg ({size_mb:.1f} MB)")
        else:
            print(f"✗ {name}.gpkg (missing)")
            all_success = False

    return all_success


def main():
    """Download all Fairfax County hydrography datasets."""
    print(f"\n{'='*70}")
    print("FAIRFAX COUNTY HYDROGRAPHY DOWNLOAD")
    print(f"{'='*70}")
    print(f"Output directory: {DATA_DIR}")
    print(f"AOI bounding box: {AOI_BBOX}")
    print(f"Datasets: {len(DATASETS)}")
    print(f"{'='*70}")

    # Download each dataset
    success_count = 0
    for name, config in DATASETS.items():
        if download_layer(name, config):
            success_count += 1

    # Verify
    print(f"\n{'='*70}")
    print(f"DOWNLOAD SUMMARY: {success_count}/{len(DATASETS)} successful")
    print(f"{'='*70}")

    if verify_downloads():
        print("\n✓ All downloads completed successfully")
        print("\nNext step:")
        print("  python scripts/prepare_fairfax_hydro.py")
        return 0
    else:
        print("\n✗ Some downloads failed - check errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
