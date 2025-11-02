#!/usr/bin/env python3
"""Compute percentile bounds for flow accumulation normalization."""

import numpy as np
import rasterio as rio

def compute_percentiles(path):
    """Compute robust percentile bounds for normalization."""
    with rio.open(path) as src:
        # Read the first band with masking for nodata
        arr = src.read(1, masked=True)

        # Get valid values (not masked)
        vals = arr.compressed()

        # Remove any NaN or inf values that might have been created
        vals = vals[np.isfinite(vals)]

        # Also remove zeros which should be nodata
        vals = vals[vals > 0]

        # Compute percentiles
        percentiles = [2, 5, 10, 25, 50, 75, 90, 95, 98]
        results = np.percentile(vals, percentiles)

        print(f"Flow Accumulation Log-Scale Statistics:")
        print(f"Total pixels: {len(vals):,}")
        print(f"Min value: {vals.min():.3f}")
        print(f"Max value: {vals.max():.3f}")
        print(f"Mean value: {vals.mean():.3f}")
        print(f"Std deviation: {vals.std():.3f}")
        print(f"\nPercentiles:")
        for p, v in zip(percentiles, results):
            print(f"  {p:3d}%: {v:.3f}")

        # Key values for normalization
        p2, p98 = np.percentile(vals, [2, 98])
        print(f"\n✨ Recommended normalization bounds:")
        print(f"  p2  (min for scaling): {p2:.6f}")
        print(f"  p98 (max for scaling): {p98:.6f}")

        return p2, p98

if __name__ == "__main__":
    path = "data/processed/dem/flow_accum_log.tif"
    p2, p98 = compute_percentiles(path)