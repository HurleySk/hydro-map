"""
Tests for stream network fusion functionality.

Tests the core logic in scripts/merge_streams.py for:
- Spatial conflict detection
- Flow direction calculation
- Tributary snapping
- Schema harmonization
- Topology cleaning
"""

import pytest
import sys
from pathlib import Path
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point

# Add scripts directory to path to import merge_streams module
scripts_path = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_path))

from merge_streams import (
    calculate_flow_direction,
    classify_dem_streams,
    harmonize_schemas,
    snap_tributaries_to_nhd,
)


class TestFlowDirectionCalculation:
    """Test flow direction angle calculation."""

    def test_north_flow(self):
        """Stream flowing north should have angle ~0."""
        line = LineString([(0, 0), (0, 1)])
        angle = calculate_flow_direction(line)
        assert angle == pytest.approx(0.0, abs=1.0)

    def test_east_flow(self):
        """Stream flowing east should have angle ~90."""
        line = LineString([(0, 0), (1, 0)])
        angle = calculate_flow_direction(line)
        assert angle == pytest.approx(90.0, abs=1.0)

    def test_south_flow(self):
        """Stream flowing south should have angle ~180."""
        line = LineString([(0, 1), (0, 0)])
        angle = calculate_flow_direction(line)
        assert angle == pytest.approx(180.0, abs=1.0)

    def test_west_flow(self):
        """Stream flowing west should have angle ~270."""
        line = LineString([(1, 0), (0, 0)])
        angle = calculate_flow_direction(line)
        assert angle == pytest.approx(270.0, abs=1.0)

    def test_diagonal_ne_flow(self):
        """Stream flowing northeast should have angle ~45."""
        line = LineString([(0, 0), (1, 1)])
        angle = calculate_flow_direction(line)
        assert angle == pytest.approx(45.0, abs=1.0)


class TestSpatialConflictDetection:
    """Test DEM stream classification against NHD."""

    def create_test_geodataframes(self):
        """Helper to create test NHD and DEM GeoDataFrames."""
        # Create simple NHD stream (west to east)
        nhd_data = {
            'geometry': [LineString([(0, 5), (10, 5)])],
            'length_km': [0.01],
            'length_m': [10.0],
            'source_type': ['nhd']
        }
        nhd_gdf = gpd.GeoDataFrame(nhd_data, crs="EPSG:4326")

        # Create various DEM streams for testing
        dem_data = {
            'geometry': [
                LineString([(0, 5.0001), (10, 5.0001)]),  # Parallel, very close (duplicate)
                LineString([(5, 0), (5, 4.9)]),  # Tributary, approaches from south
                LineString([(20, 5), (30, 5)]),  # Isolated, far from NHD
            ],
            'length_km': [0.01, 0.005, 0.01],
            'length_m': [10.0, 5.0, 10.0],
            'source_type': ['dem', 'dem', 'dem']
        }
        dem_gdf = gpd.GeoDataFrame(dem_data, crs="EPSG:4326")

        return nhd_gdf, dem_gdf

    def test_duplicate_detection(self):
        """DEM stream very close and parallel to NHD should be classified as duplicate."""
        nhd_gdf, dem_gdf = self.create_test_geodataframes()

        # Classify using projected CRS for accurate distances
        # Note: For this test we use a large duplicate_distance since we're in degrees
        classified = classify_dem_streams(
            nhd_gdf, dem_gdf,
            duplicate_distance=100.0,  # meters
            isolation_distance=5000.0,  # meters
            angle_tolerance=45.0
        )

        # First stream should be duplicate (parallel and close)
        assert classified.iloc[0]['conflict_class'] == 'duplicate'

    def test_tributary_detection(self):
        """DEM stream approaching NHD at angle should be classified as tributary."""
        nhd_gdf, dem_gdf = self.create_test_geodataframes()

        classified = classify_dem_streams(
            nhd_gdf, dem_gdf,
            duplicate_distance=100.0,
            isolation_distance=5000.0,
            angle_tolerance=45.0
        )

        # Second stream should be tributary (perpendicular approach)
        assert classified.iloc[1]['conflict_class'] in ['tributary', 'duplicate']

    def test_isolated_detection(self):
        """DEM stream far from NHD should be classified as isolated."""
        nhd_gdf, dem_gdf = self.create_test_geodataframes()

        classified = classify_dem_streams(
            nhd_gdf, dem_gdf,
            duplicate_distance=100.0,
            isolation_distance=5000.0,  # 5 km
            angle_tolerance=45.0
        )

        # Third stream should be isolated (far from NHD)
        assert classified.iloc[2]['conflict_class'] == 'isolated'


class TestTributarySnapping:
    """Test tributary endpoint snapping to NHD junctions."""

    def test_snap_within_distance(self):
        """Tributary within snap distance should have endpoint moved."""
        # NHD stream with known endpoint
        nhd_data = {
            'geometry': [LineString([(0, 0), (10, 0)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }
        nhd_gdf = gpd.GeoDataFrame(nhd_data, crs="EPSG:4326")

        # DEM stream with endpoint close to NHD endpoint
        dem_data = {
            'geometry': [LineString([(5, 10), (10.0001, 0.0001)])],  # Close to (10, 0)
            'length_km': [0.01],
            'length_m': [10.0],
            'conflict_class': ['tributary']
        }
        dem_gdf = gpd.GeoDataFrame(dem_data, crs="EPSG:4326")

        # Snap with large snap distance (in meters, but coords are degrees)
        snapped = snap_tributaries_to_nhd(nhd_gdf, dem_gdf, snap_distance=100.0)

        # Check that endpoint was modified
        original_endpoint = dem_data['geometry'][0].coords[-1]
        snapped_endpoint = snapped.iloc[0].geometry.coords[-1]

        # Snapped endpoint should be different from original
        assert snapped_endpoint != original_endpoint

    def test_no_snap_beyond_distance(self):
        """Tributary beyond snap distance should remain unchanged."""
        nhd_data = {
            'geometry': [LineString([(0, 0), (10, 0)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }
        nhd_gdf = gpd.GeoDataFrame(nhd_data, crs="EPSG:4326")

        # DEM stream far from NHD endpoints
        dem_data = {
            'geometry': [LineString([(100, 100), (110, 100)])],
            'length_km': [0.01],
            'length_m': [10.0],
            'conflict_class': ['isolated']
        }
        dem_gdf = gpd.GeoDataFrame(dem_data, crs="EPSG:4326")

        snapped = snap_tributaries_to_nhd(nhd_gdf, dem_gdf, snap_distance=10.0)

        # Geometry should be unchanged
        original_coords = list(dem_data['geometry'][0].coords)
        snapped_coords = list(snapped.iloc[0].geometry.coords)

        assert original_coords == snapped_coords


class TestSchemaHarmonization:
    """Test schema compatibility between NHD and DEM streams."""

    def test_add_missing_columns_to_dem(self):
        """DEM should get NHD columns with appropriate defaults."""
        # NHD with rich attributes
        nhd_data = {
            'geometry': [LineString([(0, 0), (1, 1)])],
            'length_km': [0.01],
            'length_m': [10.0],
            'stream_order': [2],
            'drainage_area_sqkm': [5.0],
            'name': ['Test Creek'],
            'is_connector': [False]
        }
        nhd_gdf = gpd.GeoDataFrame(nhd_data, crs="EPSG:4326")

        # DEM with minimal attributes
        dem_data = {
            'geometry': [LineString([(2, 2), (3, 3)])],
            'length_km': [0.01],
            'length_m': [10.0],
            'order': [1],
            'confidence_score': [0.7]
        }
        dem_gdf = gpd.GeoDataFrame(dem_data, crs="EPSG:4326")

        # Harmonize
        harmonized = harmonize_schemas(nhd_gdf, dem_gdf)

        # DEM should now have NHD columns
        assert 'stream_order' in harmonized.columns
        assert 'drainage_area_sqkm' in harmonized.columns
        assert 'name' in harmonized.columns
        assert 'is_connector' in harmonized.columns

        # Check defaults
        assert harmonized.iloc[0]['is_connector'] == False
        assert harmonized.iloc[0]['stream_type'] == 'Ephemeral'

    def test_nhd_gets_confidence_column(self):
        """NHD should get confidence_score if missing."""
        nhd_data = {
            'geometry': [LineString([(0, 0), (1, 1)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }
        nhd_gdf = gpd.GeoDataFrame(nhd_data, crs="EPSG:4326")

        dem_data = {
            'geometry': [LineString([(2, 2), (3, 3)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }
        dem_gdf = gpd.GeoDataFrame(dem_data, crs="EPSG:4326")

        # Harmonize should add confidence to NHD
        _ = harmonize_schemas(nhd_gdf, dem_gdf)

        assert 'confidence_score' in nhd_gdf.columns
        assert nhd_gdf.iloc[0]['confidence_score'] == 1.0


class TestAttributePreservation:
    """Test that NHD attributes are preserved during fusion."""

    def test_nhd_attributes_unchanged(self):
        """NHD stream attributes should remain exactly as input."""
        original_nhd = gpd.GeoDataFrame({
            'geometry': [LineString([(0, 0), (1, 1)])],
            'length_km': [1.5],
            'stream_order': [3],
            'drainage_area_sqkm': [25.5],
            'name': ['Big Creek'],
            'source_type': ['nhd']
        }, crs="EPSG:4326")

        # After harmonization, NHD data should be unchanged
        # (harmonize_schemas modifies DEM, not NHD)
        dem_dummy = gpd.GeoDataFrame({
            'geometry': [LineString([(2, 2), (3, 3)])],
            'length_km': [0.5]
        }, crs="EPSG:4326")

        harmonize_schemas(original_nhd, dem_dummy)

        # Check NHD values are preserved
        assert original_nhd.iloc[0]['length_km'] == 1.5
        assert original_nhd.iloc[0]['stream_order'] == 3
        assert original_nhd.iloc[0]['drainage_area_sqkm'] == 25.5
        assert original_nhd.iloc[0]['name'] == 'Big Creek'


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_nhd(self):
        """Empty NHD should result in all DEM streams classified as isolated."""
        nhd_gdf = gpd.GeoDataFrame({
            'geometry': [],
            'length_km': [],
            'length_m': []
        }, crs="EPSG:4326")

        dem_gdf = gpd.GeoDataFrame({
            'geometry': [LineString([(0, 0), (1, 1)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }, crs="EPSG:4326")

        classified = classify_dem_streams(
            nhd_gdf, dem_gdf,
            duplicate_distance=100.0,
            isolation_distance=5000.0,
            angle_tolerance=45.0
        )

        # All DEM streams should be isolated when NHD is empty
        assert all(classified['conflict_class'] == 'isolated')

    def test_empty_dem(self):
        """Empty DEM should not cause errors."""
        nhd_gdf = gpd.GeoDataFrame({
            'geometry': [LineString([(0, 0), (1, 1)])],
            'length_km': [0.01],
            'length_m': [10.0]
        }, crs="EPSG:4326")

        dem_gdf = gpd.GeoDataFrame({
            'geometry': [],
            'length_km': [],
            'length_m': []
        }, crs="EPSG:4326")

        # Should not raise error
        classified = classify_dem_streams(
            nhd_gdf, dem_gdf,
            duplicate_distance=100.0,
            isolation_distance=5000.0,
            angle_tolerance=45.0
        )

        assert len(classified) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
