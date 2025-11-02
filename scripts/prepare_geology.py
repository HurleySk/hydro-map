#!/usr/bin/env python3
"""
Prepare geology data for tile generation.

This script:
1. Reads geology source data (shapefile, GeoJSON, etc.)
2. Normalizes attribute names to standard fields
3. Generates color codes based on rock types if missing
4. Outputs a GeoPackage suitable for tile generation

Usage:
    python prepare_geology.py --input data/raw/geology/source.shp --output data/processed/geology.gpkg
    python prepare_geology.py --create-sample --output data/processed/geology.gpkg  # Create sample data
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import geopandas as gpd
    from shapely.geometry import box, Polygon, MultiPolygon
    import pandas as pd
except ImportError:
    print("Required packages not installed. Please install:")
    print("pip install geopandas shapely pandas")
    exit(1)

# Standard rock type color palette
ROCK_TYPE_COLORS = {
    'igneous': '#f59e0b',
    'sedimentary': '#22c55e',
    'metamorphic': '#8b5cf6',
    'volcanic': '#ef4444',
    'plutonic': '#f97316',
    'carbonate': '#06b6d4',
    'sandstone': '#fbbf24',
    'shale': '#84cc16',
    'limestone': '#10b981',
    'granite': '#f87171',
    'basalt': '#991b1b',
    'gneiss': '#a78bfa',
    'schist': '#c084fc',
    'quartzite': '#e0e7ff',
    'unconsolidated': '#d4d4d8',
    'alluvium': '#fef3c7',
    'water': '#3b82f6',
    'unknown': '#9ca3af'
}

# Common attribute name mappings
ATTRIBUTE_MAPPINGS = {
    'unit': ['UNIT', 'UNIT_NAME', 'MAP_UNIT', 'MAPUNIT', 'Formation', 'FORMATION', 'ORIG_LABEL', 'SGMC_LABEL', 'UNIT_LINK'],
    'rock_type': ['ROCKTYPE', 'ROCKTYPE1', 'ROCK_TYPE', 'LITH1', 'LITHOLOGY', 'MAJOR_ROCK', 'GENERALIZE'],
    'age': ['AGE', 'MIN_AGE', 'GEO_AGE', 'GEOLOGIC_AGE', 'TIME_PERIOD'],
    'description': ['DESCRIPTION', 'UNIT_DESCR', 'UNIT_DESC', 'DESC', 'COMMENTS', 'GENERALIZE'],
    'color': ['COLOR', 'RGB', 'HEX', 'HEXCOLOR', 'FILL_COLOR']
}


def normalize_attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize attribute names to standard fields."""
    # Create new standardized columns
    normalized = gdf.copy()

    # Get existing column names (case-insensitive mapping)
    columns_lower = {col.lower(): col for col in gdf.columns}

    # Map attributes
    for target_attr, possible_names in ATTRIBUTE_MAPPINGS.items():
        if target_attr not in normalized.columns:
            for possible_name in possible_names:
                # Try exact match first
                if possible_name in gdf.columns:
                    normalized[target_attr] = gdf[possible_name]
                    print(f"Mapped {possible_name} -> {target_attr}")
                    break
                # Try case-insensitive match
                elif possible_name.lower() in columns_lower:
                    original_col = columns_lower[possible_name.lower()]
                    normalized[target_attr] = gdf[original_col]
                    print(f"Mapped {original_col} -> {target_attr}")
                    break

    # Ensure required fields exist
    if 'unit' not in normalized.columns:
        normalized['unit'] = 'Unknown Formation'
        print("Warning: No unit/formation field found, using 'Unknown Formation'")

    if 'rock_type' not in normalized.columns:
        normalized['rock_type'] = 'unknown'
        print("Warning: No rock_type field found, using 'unknown'")

    if 'age' not in normalized.columns:
        normalized['age'] = ''

    if 'description' not in normalized.columns:
        normalized['description'] = ''

    return normalized


def generate_color_from_string(s: str) -> str:
    """Generate a deterministic color from a string using hash."""
    # Create hash of the string
    hash_obj = hashlib.md5(s.encode())
    hash_hex = hash_obj.hexdigest()

    # Use first 6 characters for hex color
    return f"#{hash_hex[:6]}"


def assign_colors(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Assign colors based on rock_type or unit name."""
    result = gdf.copy()

    if 'color' not in result.columns:
        result['color'] = ''

    for idx, row in result.iterrows():
        # Skip if color already exists
        if pd.notna(row.get('color', '')) and row['color'].strip():
            continue

        # Try to match rock_type to predefined colors
        rock_type = str(row.get('rock_type', '')).lower()
        color = None

        # Handle Virginia geology format (e.g., "Igneous, intrusive")
        if ',' in rock_type:
            # Take the first part before comma
            rock_type = rock_type.split(',')[0].strip()

        # Check for exact match
        if rock_type in ROCK_TYPE_COLORS:
            color = ROCK_TYPE_COLORS[rock_type]
        else:
            # Check for partial match
            for rock_key, rock_color in ROCK_TYPE_COLORS.items():
                if rock_key in rock_type:
                    color = rock_color
                    break

        # If no match, generate color from unit name
        if not color:
            unit_name = str(row.get('unit', f'unit_{idx}'))
            color = generate_color_from_string(unit_name)

        result.at[idx, 'color'] = color

    return result


def create_sample_geology(bounds: tuple = (-122.5, 37.7, -122.3, 37.9)) -> gpd.GeoDataFrame:
    """Create sample geology data for testing."""
    print("Creating sample geology data...")

    # Define sample geology polygons (San Francisco area)
    minx, miny, maxx, maxy = bounds
    width = (maxx - minx) / 3
    height = (maxy - miny) / 3

    polygons = []
    units = []
    rock_types = []
    ages = []
    descriptions = []

    # Create a 3x3 grid of different geology units
    formations = [
        ('Franciscan Complex', 'metamorphic', 'Jurassic-Cretaceous', 'Graywacke, shale, and greenstone'),
        ('Colma Formation', 'sedimentary', 'Pleistocene', 'Sand and gravel deposits'),
        ('Merced Formation', 'sedimentary', 'Pliocene-Pleistocene', 'Sandstone and mudstone'),
        ('Great Valley Sequence', 'sedimentary', 'Cretaceous', 'Sandstone and shale'),
        ('Serpentinite', 'igneous', 'Jurassic', 'Ultramafic rock, serpentinized'),
        ('Quaternary Alluvium', 'unconsolidated', 'Holocene', 'Stream deposits'),
        ('Dune Sand', 'unconsolidated', 'Holocene', 'Wind-blown sand deposits'),
        ('Artificial Fill', 'unconsolidated', 'Recent', 'Human-made fill material'),
        ('Alcatraz Terrane', 'sandstone', 'Cretaceous', 'Turbidite sandstone')
    ]

    for i in range(3):
        for j in range(3):
            idx = i * 3 + j
            # Create polygon with some irregularity
            x0 = minx + j * width
            y0 = miny + i * height
            x1 = x0 + width
            y1 = y0 + height

            # Add some variation to make it look more natural
            import random
            random.seed(idx)
            coords = [
                (x0 + random.uniform(-width*0.05, width*0.05), y0),
                (x1 + random.uniform(-width*0.05, width*0.05), y0 + random.uniform(-height*0.05, height*0.05)),
                (x1, y1 + random.uniform(-height*0.05, height*0.05)),
                (x0 + random.uniform(-width*0.05, width*0.05), y1),
                (x0, y0 + random.uniform(-height*0.05, height*0.05))
            ]

            poly = Polygon(coords)
            polygons.append(poly)

            formation = formations[idx % len(formations)]
            units.append(formation[0])
            rock_types.append(formation[1])
            ages.append(formation[2])
            descriptions.append(formation[3])

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame({
        'unit': units,
        'rock_type': rock_types,
        'age': ages,
        'description': descriptions,
        'geometry': polygons
    }, crs='EPSG:4326')

    return gdf


def prepare_geology(input_path: Optional[Path], output_path: Path, create_sample: bool = False):
    """Main function to prepare geology data."""

    if create_sample:
        # Create sample data
        gdf = create_sample_geology()
        print(f"Created {len(gdf)} sample geology polygons")
    else:
        if not input_path or not input_path.exists():
            print(f"Error: Input file {input_path} does not exist")
            return False

        # Read input geology data
        print(f"Reading geology data from {input_path}...")
        gdf = gpd.read_file(input_path)
        print(f"Loaded {len(gdf)} features")

        # Reproject to WGS84 if needed
        if gdf.crs and gdf.crs != 'EPSG:4326':
            print(f"Reprojecting from {gdf.crs} to EPSG:4326...")
            gdf = gdf.to_crs('EPSG:4326')

    # Normalize attributes
    print("Normalizing attributes...")
    gdf = normalize_attributes(gdf)

    # Assign colors
    print("Assigning colors based on rock types...")
    gdf = assign_colors(gdf)

    # Keep only necessary columns
    columns_to_keep = ['unit', 'rock_type', 'age', 'description', 'color', 'geometry']
    columns_to_keep = [col for col in columns_to_keep if col in gdf.columns]
    gdf = gdf[columns_to_keep]

    # Save to GeoPackage
    print(f"Saving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver='GPKG', layer='geology')

    # Print summary
    print("\nSummary:")
    print(f"  Features: {len(gdf)}")
    print(f"  Unique units: {gdf['unit'].nunique()}")
    print(f"  Rock types: {gdf['rock_type'].value_counts().to_dict()}")
    print(f"  Output: {output_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description='Prepare geology data for tile generation')
    parser.add_argument('--input', type=Path, help='Input geology file (shapefile, GeoJSON, etc.)')
    parser.add_argument('--output', type=Path, default=Path('data/processed/geology.gpkg'),
                        help='Output GeoPackage path')
    parser.add_argument('--create-sample', action='store_true',
                        help='Create sample geology data for testing')
    parser.add_argument('--bounds', nargs=4, type=float,
                        default=[-122.5, 37.7, -122.3, 37.9],
                        help='Bounds for sample data (minx miny maxx maxy)')

    args = parser.parse_args()

    if not args.create_sample and not args.input:
        print("Error: Either --input or --create-sample must be specified")
        parser.print_help()
        return 1

    success = prepare_geology(
        input_path=args.input,
        output_path=args.output,
        create_sample=args.create_sample
    )

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())