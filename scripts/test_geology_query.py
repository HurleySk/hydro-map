#!/usr/bin/env python3
"""
Test the improved geology query logic directly.
"""

import sys
sys.path.insert(0, '/Users/skh/source/hydro-map/backend')

import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
from pathlib import Path

def test_geology_query(lat, lon):
    """Test the geology query at a specific point."""
    point = Point(lon, lat)
    buffer_m = 10

    geology_path = Path("/Users/skh/source/hydro-map/data/processed/geology.gpkg")
    geology_gdf = gpd.read_file(geology_path)

    print(f"\nQuerying point: ({lat}, {lon})")
    print("=" * 60)

    # FIRST: Find all polygons that CONTAIN the click point
    containing = geology_gdf[geology_gdf.contains(point)]

    if len(containing) > 0:
        print(f"Found {len(containing)} polygon(s) containing the point:")

        # Calculate areas
        containing_proj = containing.to_crs("EPSG:6933")
        containing_areas = containing_proj.area

        # Create list with areas
        results = []
        for idx, row in containing.iterrows():
            area_sqm = containing_areas.loc[idx]
            area_sqkm = area_sqm / 1_000_000
            results.append({
                'unit': row.get('unit', 'Unknown'),
                'rock_type': row.get('rock_type', 'Unknown'),
                'area_sqkm': area_sqkm
            })

        # Sort by area (smallest first)
        results.sort(key=lambda x: x['area_sqkm'])

        for i, r in enumerate(results):
            marker = "✓ SELECTED" if i == 0 else "  "
            print(f"  {marker} {r['unit']}: {r['rock_type']} (Area: {r['area_sqkm']:.2f} km²)")

        print(f"\n→ Would return: {results[0]['unit']} ({results[0]['rock_type']})")

    else:
        print("No polygons contain the point. Looking for nearby polygons within 10m...")

        # Create buffer
        import math
        lat_deg_per_m = 1 / 111000
        lon_deg_per_m = 1 / (111000 * math.cos(math.radians(point.y)))
        buffer_deg = max(buffer_m * lat_deg_per_m, buffer_m * lon_deg_per_m)
        buffered_point = point.buffer(buffer_deg)

        intersecting = geology_gdf[geology_gdf.intersects(buffered_point)]

        if len(intersecting) > 0:
            print(f"Found {len(intersecting)} nearby polygon(s):")

            results = []
            for idx, row in intersecting.iterrows():
                polygon_geom = row.geometry
                nearest_pt, _ = nearest_points(polygon_geom.boundary, point)

                # Simple distance calculation
                dx = (nearest_pt.x - point.x) * 111000 * math.cos(math.radians(point.y))
                dy = (nearest_pt.y - point.y) * 111000
                distance = math.sqrt(dx*dx + dy*dy)

                results.append({
                    'unit': row.get('unit', 'Unknown'),
                    'rock_type': row.get('rock_type', 'Unknown'),
                    'distance': distance
                })

            # Sort by distance
            results.sort(key=lambda x: x['distance'])

            for i, r in enumerate(results[:3]):
                marker = "✓ SELECTED" if i == 0 else "  "
                print(f"  {marker} {r['unit']}: {r['rock_type']} (Distance: {r['distance']:.1f}m)")

            if results:
                print(f"\n→ Would return: {results[0]['unit']} ({results[0]['rock_type']})")
        else:
            print("No polygons found within buffer.")


# Test the problematic coordinates
print("\n" + "="*80)
print("TESTING IMPROVED GEOLOGY QUERY LOGIC")
print("="*80)

test_points = [
    (38.82938, -77.17720),  # First user click
    (38.82963, -77.17652),  # Second user click
    (38.82800, -77.17500),  # Additional test point
    (38.83200, -77.17000),  # Another test point
]

for lat, lon in test_points:
    test_geology_query(lat, lon)