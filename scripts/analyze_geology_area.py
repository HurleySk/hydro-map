#!/usr/bin/env python3
"""
Analyze geology polygons around Mason District Park to understand feature selection issues.
"""

import geopandas as gpd
from shapely.geometry import Point, box
import pandas as pd
from pathlib import Path

# Mason District Park area
center_lat = 38.82938
center_lon = -77.17720

# Create a bounding box around the park (roughly 1km x 1km)
bbox = box(center_lon - 0.01, center_lat - 0.01, center_lon + 0.01, center_lat + 0.01)

# Load geology data
geology_path = Path("/Users/skh/source/hydro-map/data/processed/geology.gpkg")
geology_gdf = gpd.read_file(geology_path, bbox=bbox)

print(f"Found {len(geology_gdf)} geology features in the Mason District Park area")
print(f"Bounding box: {bbox.bounds}")
print("\n" + "="*80 + "\n")

# Analyze each polygon
for idx, row in geology_gdf.iterrows():
    geom = row.geometry

    # Calculate area in square kilometers
    geom_proj = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs("EPSG:6933")  # Equal Earth projection
    area_sqm = geom_proj.area.values[0]
    area_sqkm = area_sqm / 1_000_000

    # Get bounds
    minx, miny, maxx, maxy = geom.bounds
    width_deg = maxx - minx
    height_deg = maxy - miny

    # Approximate dimensions in km (at this latitude)
    width_km = width_deg * 111 * 0.788  # cos(38.8°) ≈ 0.788
    height_km = height_deg * 111

    print(f"Feature {idx}: {row.get('unit', 'Unknown')}")
    print(f"  Rock Type: {row.get('rock_type', 'Unknown')}")
    print(f"  Area: {area_sqkm:.2f} km²")
    print(f"  Dimensions: {width_km:.2f} km × {height_km:.2f} km")
    print(f"  Bounds: ({minx:.4f}, {miny:.4f}) to ({maxx:.4f}, {maxy:.4f})")

    # Check if specific test points are inside this polygon
    test_points = [
        Point(-77.17720, 38.82938),  # First click
        Point(-77.17652, 38.82963),  # Second click
    ]

    for i, pt in enumerate(test_points, 1):
        if geom.contains(pt):
            print(f"  ✓ Contains test point {i}")

    print()

print("\n" + "="*80 + "\n")
print("ANALYSIS SUMMARY:")
print("-" * 40)

# Find overlapping polygons
overlaps = []
for i in range(len(geology_gdf)):
    for j in range(i+1, len(geology_gdf)):
        geom1 = geology_gdf.iloc[i].geometry
        geom2 = geology_gdf.iloc[j].geometry
        if geom1.overlaps(geom2) or geom1.contains(geom2) or geom2.contains(geom1):
            overlaps.append((
                geology_gdf.iloc[i]['unit'],
                geology_gdf.iloc[j]['unit']
            ))

if overlaps:
    print(f"Found {len(overlaps)} overlapping polygon pairs:")
    for unit1, unit2 in overlaps:
        print(f"  - {unit1} overlaps with {unit2}")
else:
    print("No overlapping polygons found")

print("\n" + "-" * 40)

# Check which polygons contain the test point
test_point = Point(-77.17720, 38.82938)
containing = geology_gdf[geology_gdf.contains(test_point)]
print(f"\nPolygons containing test point ({test_point.x}, {test_point.y}):")
for idx, row in containing.iterrows():
    print(f"  - {row['unit']}: {row['rock_type']}")

# Find the smallest polygon containing the test point
if len(containing) > 0:
    # Calculate areas for containing polygons
    containing_proj = containing.to_crs("EPSG:6933")
    containing['area_sqm'] = containing_proj.area
    smallest = containing.nsmallest(1, 'area_sqm').iloc[0]
    print(f"\nSmallest containing polygon: {smallest['unit']} ({smallest['area_sqm']/1_000_000:.2f} km²)")