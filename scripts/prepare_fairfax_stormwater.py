#!/usr/bin/env python3
"""
Process Fairfax County stormwater and flood risk data for Hydro-Map integration.

Normalizes attributes, calculates geometry metrics, and prepares datasets
for tile generation.

Usage:
    python prepare_fairfax_stormwater.py
"""

import geopandas as gpd
from pathlib import Path
import sys

# Paths
RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "fairfax"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Dataset configurations
DATASETS = {
    "floodplain_easements": {
        "input": RAW_DIR / "floodplain_easements.gpkg",
        "output": PROCESSED_DIR / "floodplain_easements.gpkg",
        "fields_map": {
            "OBJ_ID_ALIAS": "id"
        },
        "geometry_type": "Polygon"
    },
    "inadequate_outfalls": {
        "input": RAW_DIR / "inadequate_outfalls.gpkg",
        "output": PROCESSED_DIR / "inadequate_outfalls.gpkg",
        "fields_map": {
            "INADEQUATE_OUTFALL_ID": "outfall_id",
            "DRAINAGE_AREA": "drainage_area",
            "DETERMINATION": "determination",
            "WATERSHED": "watershed"
        },
        "geometry_type": "Polygon"
    },
    "inadequate_outfall_points": {
        "input": RAW_DIR / "inadequate_outfall_points.gpkg",
        "output": PROCESSED_DIR / "inadequate_outfall_points.gpkg",
        "fields_map": {
            "INADEQUATE_OUTFALL_ID": "outfall_id",
            "DRAINAGE_AREA": "drainage_area",
            "DETERMINATION": "determination",
            "WATERSHED": "watershed"
        },
        "geometry_type": "Point"
    }
}


def process_layer(name: str, config: dict):
    """
    Process a single layer: normalize fields and calculate metrics.

    Args:
        name: Dataset name
        config: Processing configuration

    Returns:
        bool: Success status
    """
    print(f"\n{'='*70}")
    print(f"Processing: {name}")
    print(f"{'='*70}")

    input_file = config["input"]
    output_file = config["output"]

    if not input_file.exists():
        print(f"✗ Input file not found: {input_file}")
        return False

    try:
        # Read raw data
        print(f"Reading: {input_file}")
        gdf = gpd.read_file(input_file)

        print(f"  Features: {len(gdf):,}")
        print(f"  CRS: {gdf.crs}")
        print(f"  Geometry type: {gdf.geometry.type.iloc[0] if len(gdf) > 0 else 'N/A'}")

        # Validate CRS
        if gdf.crs != "EPSG:4326":
            print(f"  Reprojecting to EPSG:4326...")
            gdf = gdf.to_crs("EPSG:4326")

        # Normalize field names (case-insensitive mapping)
        fields_map = config["fields_map"]
        gdf_processed = gdf.copy()

        # Map fields (try both exact and uppercase matches)
        for orig, target in fields_map.items():
            if orig in gdf_processed.columns:
                gdf_processed.rename(columns={orig: target}, inplace=True)
            elif orig.upper() in gdf_processed.columns:
                gdf_processed.rename(columns={orig.upper(): target}, inplace=True)
            elif orig.lower() in gdf_processed.columns:
                gdf_processed.rename(columns={orig.lower(): target}, inplace=True)
            else:
                print(f"  Warning: Field '{orig}' not found, setting to None")
                gdf_processed[target] = None

        # Add data source attribution
        gdf_processed["data_source"] = "Fairfax County GIS"

        # Calculate geometry metrics
        if config["geometry_type"] == "Polygon":
            # Calculate area in sq km
            gdf_utm = gdf_processed.to_crs("EPSG:32618")  # UTM Zone 18N
            gdf_processed["area_sqkm"] = gdf_utm.geometry.area / 1_000_000
            print(f"  Area range: {gdf_processed['area_sqkm'].min():.6f} - {gdf_processed['area_sqkm'].max():.2f} sq km")

        # Keep only standardized fields + geometry
        keep_fields = list(fields_map.values()) + ["data_source"]
        if config["geometry_type"] == "Polygon":
            keep_fields.append("area_sqkm")
        keep_fields.append("geometry")

        # Filter to only fields that exist
        existing_fields = [f for f in keep_fields if f in gdf_processed.columns]
        gdf_final = gdf_processed[existing_fields].copy()

        # Save processed data
        print(f"  Saving to: {output_file}")
        gdf_final.to_file(output_file, driver="GPKG", layer=name)

        # Verify
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✓ Processing complete: {output_file.name} ({size_mb:.1f} MB, {len(gdf_final):,} features)")

        # Show field summary
        print(f"\n  Fields retained:")
        for field in existing_fields:
            if field != "geometry":
                non_null = gdf_final[field].notna().sum()
                print(f"    - {field}: {non_null:,}/{len(gdf_final):,} non-null")

        return True

    except Exception as e:
        print(f"✗ Error processing {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_outputs():
    """Verify all processed files exist."""
    print(f"\n{'='*70}")
    print("VERIFICATION")
    print(f"{'='*70}")

    all_success = True
    for name, config in DATASETS.items():
        output_file = config["output"]
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"✓ {output_file.name} ({size_mb:.1f} MB)")
        else:
            print(f"✗ {output_file.name} (missing)")
            all_success = False

    return all_success


def main():
    """Process all Fairfax County stormwater/flood datasets."""
    print(f"\n{'='*70}")
    print("FAIRFAX COUNTY STORMWATER/FLOOD PROCESSING")
    print(f"{'='*70}")
    print(f"Raw data: {RAW_DIR}")
    print(f"Output: {PROCESSED_DIR}")
    print(f"Datasets: {len(DATASETS)}")
    print(f"{'='*70}")

    # Process each dataset
    success_count = 0
    for name, config in DATASETS.items():
        if process_layer(name, config):
            success_count += 1

    # Verify
    print(f"\n{'='*70}")
    print(f"PROCESSING SUMMARY: {success_count}/{len(DATASETS)} successful")
    print(f"{'='*70}")

    if verify_outputs():
        print("\n✓ All datasets processed successfully")
        print("\nNext step:")
        print("  1. Update scripts/generate_tiles.py to add these 3 datasets")
        print("  2. Run: python scripts/generate_tiles.py")
        return 0
    else:
        print("\n✗ Some datasets failed - check errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
