#!/usr/bin/env python3
"""
Process TWI raster for tile generation.

This script:
1. Normalizes TWI values to 0-255 using robust percentiles
2. Applies color relief
3. Prepares for PMTiles generation

Usage:
    python process_twi_for_tiles.py
"""

import subprocess
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    import rasterio
except ImportError:
    print("Required packages not installed. Please install:")
    print("pip install rasterio numpy")
    exit(1)


def normalize_twi(
    input_path: Path,
    output_path: Path,
    p_low: float = 2.0,
    p_high: float = 98.0
):
    """
    Normalize TWI to 0-255 range using percentiles.

    Args:
        input_path: Path to raw TWI raster
        output_path: Path to normalized 8-bit output
        p_low: Lower percentile for clipping (default 2)
        p_high: Upper percentile for clipping (default 98)
    """
    print(f"Reading TWI from {input_path}...")
    with rasterio.open(input_path) as src:
        twi = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata = src.nodata

    # Mask valid data
    if nodata is not None:
        valid_mask = (twi != nodata) & np.isfinite(twi)
    else:
        valid_mask = np.isfinite(twi)

    twi_valid = twi[valid_mask]

    # Compute percentiles
    vmin, vmax = np.percentile(twi_valid, [p_low, p_high])
    print(f"TWI range: [{vmin:.3f}, {vmax:.3f}] (P{p_low}-P{p_high})")

    # Normalize to 0-255
    twi_norm = np.zeros_like(twi, dtype=np.uint8)

    # Clip and scale
    twi_clipped = np.clip(twi, vmin, vmax)
    twi_scaled = ((twi_clipped - vmin) / (vmax - vmin) * 255)

    # Only set valid pixels
    twi_norm[valid_mask] = twi_scaled[valid_mask].astype(np.uint8)

    # Save normalized raster
    print(f"Saving normalized TWI to {output_path}...")
    profile.update({
        'dtype': 'uint8',
        'nodata': 0,
        'compress': 'lzw'
    })

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(twi_norm, 1)

    print(f"Normalization complete!")
    return output_path


def apply_color_relief(
    input_path: Path,
    output_path: Path,
    color_ramp_path: Path
):
    """Apply color relief to normalized TWI raster."""
    print(f"Applying color relief...")
    print(f"  Input: {input_path}")
    print(f"  Color ramp: {color_ramp_path}")
    print(f"  Output: {output_path}")

    cmd = [
        'gdaldem', 'color-relief',
        str(input_path),
        str(color_ramp_path),
        str(output_path),
        '-alpha',
        '-co', 'COMPRESS=LZW',
        '-co', 'TILED=YES',
        '-co', 'BLOCKXSIZE=512',
        '-co', 'BLOCKYSIZE=512'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error applying color relief: {result.stderr}")
        return None

    print(f"Color relief applied successfully!")
    return output_path


def main():
    # Paths
    raw_twi = Path('data/processed/dem/twi.tif')
    twi_8bit = Path('data/processed/dem/twi_8bit.tif')
    twi_color = Path('data/processed/dem/twi_color.tif')
    color_ramp = Path('scripts/color_ramps/twi.txt')

    # Check inputs
    if not raw_twi.exists():
        print(f"Error: {raw_twi} not found. Run compute_twi.py first.")
        return 1

    if not color_ramp.exists():
        print(f"Error: Color ramp {color_ramp} not found.")
        return 1

    # Step 1: Normalize TWI
    normalize_twi(raw_twi, twi_8bit, p_low=2.0, p_high=98.0)

    # Step 2: Apply color relief
    apply_color_relief(twi_8bit, twi_color, color_ramp)

    print("\nTWI processing complete!")
    print(f"  8-bit normalized: {twi_8bit}")
    print(f"  Color relief: {twi_color}")
    print("\nNext steps:")
    print("  1. Generate tiles:")
    print("     python scripts/generate_tiles.py --raster twi --input data/processed/dem/twi_color.tif")
    print("  2. Or use the full pipeline with --twi flag (if implemented)")

    return 0


if __name__ == '__main__':
    exit(main())
