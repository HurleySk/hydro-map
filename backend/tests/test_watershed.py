import numpy as np
import pytest
from rasterio.crs import CRS

from app.services.watershed import (
    transform_coordinates_to_raster_crs,
    calculate_snap_radius_pixels,
    calculate_distance_meters,
    trace_watershed_d8,
)


def test_transform_coordinates_identity():
    lon, lat = -122.0, 37.5
    x, y = transform_coordinates_to_raster_crs(lon, lat, CRS.from_epsg(4326))
    assert x == pytest.approx(lon)
    assert y == pytest.approx(lat)


def test_transform_coordinates_projected():
    lon, lat = -122.0, 37.5
    x, y = transform_coordinates_to_raster_crs(lon, lat, CRS.from_epsg(3857))
    # EPSG:3857 x/y units in meters; check reasonable magnitude
    assert x == pytest.approx(-13580977.0, rel=1e-4)
    assert y == pytest.approx(4509031.39, rel=1e-4)


def test_calculate_snap_radius_pixels_wgs84():
    radius = 100  # meters
    lat = 45.0
    pixel_size = (0.0001, 0.0001)
    pixels = calculate_snap_radius_pixels(
        radius_meters=radius,
        raster_crs=CRS.from_epsg(4326),
        center_lon=-120.0,
        center_lat=lat,
        pixel_size=pixel_size,
    )
    # 0.0001 degrees at 45 deg latitude ~ 7.85 m, so expect about 12 pixels
    assert pixels == 12


def test_calculate_distance_meters():
    distance = calculate_distance_meters(-122.0, 37.5, -122.001, 37.5)
    assert distance == pytest.approx(96.49, rel=1e-2)


def test_trace_watershed_d8_simple():
    # Simple 3x3 grid with neighbors flowing into central outlet (1,1)
    flow_dir = np.array([
        [0, 4, 0],
        [1, 0, 16],
        [0, 64, 0],
    ], dtype=np.uint8)
    mask = trace_watershed_d8(flow_dir, outlet_row=1, outlet_col=1, nodata=0)
    expected = np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ], dtype=np.uint8)
    np.testing.assert_array_equal(mask, expected)
