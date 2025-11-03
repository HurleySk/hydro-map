#!/usr/bin/env python3
"""
Compute Topographic Wetness Index (TWI) from DEM derivatives.

TWI = ln(upslope_area / tan(slope))

Where:
- upslope_area = flow_accumulation × cell_area
- slope is in radians
- Higher TWI = wetter/more saturated areas

Usage:
    python compute_twi.py --output data/processed/dem/twi.tif
"""

import argparse
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import rasterio
    from rasterio.transform import Affine
except ImportError:
    print("Required packages not installed. Please install:")
    print("pip install rasterio numpy")
    exit(1)


def compute_twi(
    flow_accum_path: Path,
    slope_deg_path: Path,
    output_path: Path,
    cell_size_m: float = 1.0,
    min_slope_deg: float = 0.01
):
    """
    Compute Topographic Wetness Index.

    Args:
        flow_accum_path: Path to flow accumulation raster (number of cells)
        slope_deg_path: Path to slope raster (degrees)
        output_path: Path to output TWI raster
        cell_size_m: Cell size in meters (default 1m)
        min_slope_deg: Minimum slope to avoid division by zero (default 0.01 degrees)
    """
    print(f"Reading flow accumulation from {flow_accum_path}...")
    with rasterio.open(flow_accum_path) as src:
        flow_accum = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata_accum = src.nodata

    print(f"Reading slope from {slope_deg_path}...")
    with rasterio.open(slope_deg_path) as src:
        slope_deg = src.read(1).astype(np.float64)
        nodata_slope = src.nodata

    # Create mask for valid data
    valid_mask = (
        (flow_accum != nodata_accum if nodata_accum is not None else np.ones_like(flow_accum, dtype=bool)) &
        (slope_deg != nodata_slope if nodata_slope is not None else np.ones_like(slope_deg, dtype=bool)) &
        np.isfinite(flow_accum) &
        np.isfinite(slope_deg) &
        (flow_accum > 0)  # Need positive flow accumulation
    )

    print(f"Valid pixels: {np.sum(valid_mask):,} / {valid_mask.size:,}")

    # Compute upslope contributing area (in square meters)
    # flow_accum is in number of cells, multiply by cell area
    cell_area_m2 = cell_size_m * cell_size_m
    upslope_area_m2 = flow_accum * cell_area_m2

    # Convert slope from degrees to radians
    slope_rad = np.deg2rad(slope_deg)

    # Apply minimum slope to avoid division by zero
    slope_rad_safe = np.where(slope_rad < np.deg2rad(min_slope_deg), np.deg2rad(min_slope_deg), slope_rad)

    # Compute TWI = ln(upslope_area / tan(slope))
    # Only compute for valid pixels
    twi = np.full_like(flow_accum, -9999.0, dtype=np.float32)

    with np.errstate(divide='ignore', invalid='ignore'):
        tan_slope = np.tan(slope_rad_safe)
        ratio = upslope_area_m2 / tan_slope
        # Only compute log where ratio is positive and finite
        ratio_valid = valid_mask & (ratio > 0) & np.isfinite(ratio)
        twi[ratio_valid] = np.log(ratio[ratio_valid])

    # Report statistics
    twi_valid = twi[ratio_valid]
    print(f"\nTWI Statistics:")
    print(f"  Min: {np.min(twi_valid):.3f}")
    print(f"  Max: {np.max(twi_valid):.3f}")
    print(f"  Mean: {np.mean(twi_valid):.3f}")
    print(f"  Median: {np.median(twi_valid):.3f}")
    print(f"  Std Dev: {np.std(twi_valid):.3f}")

    # Report percentiles for normalization
    p2, p25, p75, p98 = np.percentile(twi_valid, [2, 25, 75, 98])
    print(f"  P2: {p2:.3f}")
    print(f"  P25: {p25:.3f}")
    print(f"  P75: {p75:.3f}")
    print(f"  P98: {p98:.3f}")

    # Save output
    print(f"\nSaving TWI raster to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile.update({
        'dtype': 'float32',
        'nodata': -9999.0,
        'compress': 'lzw',
        'predictor': 3  # Floating point predictor
    })

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(twi, 1)

    print(f"TWI computation complete!")
    print(f"Output: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Compute Topographic Wetness Index')
    parser.add_argument('--flow-accum', type=Path,
                        default=Path('data/processed/dem/flow_accumulation.tif'),
                        help='Flow accumulation raster path')
    parser.add_argument('--slope-deg', type=Path,
                        default=Path('data/processed/dem/slope_deg.tif'),
                        help='Slope (degrees) raster path')
    parser.add_argument('--output', type=Path,
                        default=Path('data/processed/dem/twi.tif'),
                        help='Output TWI raster path')
    parser.add_argument('--cell-size', type=float, default=1.0,
                        help='Cell size in meters (default: 1.0)')
    parser.add_argument('--min-slope', type=float, default=0.01,
                        help='Minimum slope in degrees to avoid division by zero (default: 0.01)')

    args = parser.parse_args()

    if not args.flow_accum.exists():
        print(f"Error: Flow accumulation file not found: {args.flow_accum}")
        return 1

    if not args.slope_deg.exists():
        print(f"Error: Slope file not found: {args.slope_deg}")
        return 1

    compute_twi(
        flow_accum_path=args.flow_accum,
        slope_deg_path=args.slope_deg,
        output_path=args.output,
        cell_size_m=args.cell_size,
        min_slope_deg=args.min_slope
    )

    return 0


if __name__ == '__main__':
    exit(main())
