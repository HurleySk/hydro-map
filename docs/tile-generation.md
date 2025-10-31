# Tile Generation Guide

## Prerequisites

Ensure you have the backend virtual environment activated with all dependencies:
```bash
cd backend
source venv/bin/activate
```

## Common Tile Generation Commands

### Standard High-Resolution Generation (z=17)
Default command for maximum detail at ~200m viewing scales:
```bash
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --max-zoom 17
```
- Resolution at z=17: ~0.9 m/px (at latitude 38.8°)
- File sizes: ~25MB total (5-6MB per terrain layer)
- Generation time: 15-30 minutes

### Moderate Resolution (z=16)
Good balance between detail and file size:
```bash
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --max-zoom 16
```
- Resolution at z=16: ~1.9 m/px (at latitude 38.8°)
- File sizes: ~12MB total (approximately 50% of z=17)
- Generation time: 10-15 minutes

### Lower Resolution for Storage Efficiency (z=15)
Suitable for overview maps with reasonable detail:
```bash
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --max-zoom 15
```
- Resolution at z=15: ~3.7 m/px (at latitude 38.8°)
- File sizes: ~7MB total
- Generation time: 5-10 minutes

### Regional Overviews (z=12)
For large-scale regional visualization:
```bash
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --min-zoom 6 --max-zoom 12
```
- Resolution at z=12: ~30 m/px (at latitude 38.8°)
- Very small file sizes
- Generation time: 2-5 minutes

### Custom Contour Intervals
Adjust contour density (default is 1m):
```bash
# 5-meter contours for less dense display
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --contour-interval 5

# 10-meter contours for overview maps
python ../scripts/generate_tiles.py --data-dir ../data/processed --output-dir ../data/tiles --contour-interval 10
```

## Resolution Formula

Calculate pixel resolution for any zoom level and latitude:
```
resolution(z, lat) ≈ 156543.03392 × cos(lat) / 2^z meters/pixel
```

Example resolutions at latitude 38.8°:
- z=14: ~7.5 m/px
- z=15: ~3.7 m/px
- z=16: ~1.9 m/px
- z=17: ~0.9 m/px
- z=18: ~0.5 m/px

## File Size Considerations

Each additional zoom level approximately doubles the number of tiles and increases file size by 3-4x:
- z=14: ~1MB per terrain layer
- z=17: ~5-6MB per terrain layer
- z=18: ~15-20MB per terrain layer (estimated)

## Verification Commands

After generation, verify your tiles:
```bash
# Check file sizes
ls -lh ../data/tiles/*.pmtiles

# Verify PMTiles metadata
pmtiles show ../data/tiles/hillshade.pmtiles

# Extract a specific zoom level for testing
pmtiles extract ../data/tiles/hillshade.pmtiles --zoom=17 test.pmtiles
```

## Troubleshooting

### Missing Dependencies
If you get module errors, ensure you're in the backend virtual environment:
```bash
cd backend
source venv/bin/activate
pip install click tqdm
```

### Large File Sizes
Consider using z=16 instead of z=17, or implement lossy compression (JPEG) for terrain layers.

### Slow Generation
- Use `--processes` parameter to adjust parallel processing
- Consider generating only specific regions if full coverage isn't needed
- Run generation during off-hours

## Notes

- The script automatically generates contours from the filled DEM
- XYZ tile format is used (not TMS) for MapLibre GL compatibility
- MBTiles metadata is automatically fixed for proper rendering
- All terrain layers (hillshade, slope, aspect) are generated from the same DEM source