# Troubleshooting Guide

**Version**: 1.2.1

## Overview

This guide covers common issues, error messages, and solutions for Hydro-Map. Issues are organized by component and symptom.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Data Processing Issues](#data-processing-issues)
- [Tile Generation Issues](#tile-generation-issues)
- [Backend API Issues](#backend-api-issues)
- [Frontend Issues](#frontend-issues)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### System Health Check

Run these commands to verify your setup:

```bash
# 1. Check data files exist
ls data/processed/dem/
ls data/tiles/

# 2. Check backend dependencies
cd backend
source venv/bin/activate
python -c "import rasterio, geopandas, whitebox; print('Dependencies OK')"

# 3. Test backend API
curl http://localhost:8000/api/delineate/status

# 4. Check frontend dependencies
cd ../frontend
npm list

# 5. Test frontend dev server
curl http://localhost:5173/
```

### Common Symptoms Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| "Module not found" errors | Missing Python packages | `pip install -r requirements.txt` |
| Layers not rendering | PMTiles files missing | Run `python scripts/generate_tiles.py` |
| "File not found: DEM" | Incorrect data paths | Check `.env` file paths |
| API 404 errors | Backend not running | Start backend: `uvicorn app.main:app` |
| Blank map | Frontend build issue | Clear cache, rebuild |
| Slow watershed delineation | Large DEM, no cache | Enable caching in `.env` |

---

## Installation Issues

### Python Version Mismatch

**Symptom**:
```
ERROR: Python 3.11 or higher is required
```

**Solution**:
```bash
# Check Python version
python3 --version

# Install Python 3.11+ (Ubuntu)
sudo apt install python3.11 python3.11-venv

# Create venv with correct version
python3.11 -m venv backend/venv
```

### GDAL Installation Failed

**Symptom**:
```
ERROR: Failed building wheel for GDAL
```

**Solution Ubuntu/Debian**:
```bash
# Install GDAL system libraries first
sudo apt install gdal-bin libgdal-dev

# Set environment variables
export GDAL_CONFIG=/usr/bin/gdal-config
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

# Install Python GDAL
pip install GDAL==$(gdal-config --version)
```

**Solution macOS**:
```bash
# Install via Homebrew
brew install gdal

# Find GDAL version
gdal-config --version

# Install matching Python package
pip install GDAL==3.8.4  # Use your version
```

### WhiteboxTools Not Found

**Symptom**:
```
FileNotFoundError: WhiteboxTools executable not found
```

**Solution**:
```bash
# Download WhiteboxTools
wget https://www.whiteboxgeo.com/WBT_Linux/WhiteboxTools_linux_amd64.zip
unzip WhiteboxTools_linux_amd64.zip

# Make executable
chmod +x WBT/whitebox_tools

# Add to PATH or specify in scripts
export PATH=$PATH:$(pwd)/WBT
```

### npm Install Errors

**Symptom**:
```
EACCES: permission denied, mkdir '/usr/local/lib/node_modules'
```

**Solution**:
```bash
# Option 1: Use Node version manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# Option 2: Fix npm permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

---

## Data Processing Issues

### DEM Processing Failed

**Symptom**:
```
ERROR: Cannot open DEM file: data/raw/dem/dem.tif
```

**Solution**:
1. Verify file exists: `ls data/raw/dem/`
2. Check file format: `gdalinfo data/raw/dem/dem.tif`
3. Verify CRS: DEM should be in projected coordinates (not lat/lon) for best results
4. Check file permissions: `chmod 644 data/raw/dem/dem.tif`

### Flow Direction All Same Value

**Symptom**:
Flow direction raster appears uniform or invalid.

**Cause**: DEM not filled or breached properly.

**Solution**:
```bash
# Use breach_depressions instead of fill_depressions
python scripts/prepare_dem.py --breach  # Instead of --fill
```

### Stream Extraction Shows No Streams

**Symptom**:
Streams layer is empty or has very few features.

**Solutions**:

1. **Threshold too high**:
   ```bash
   # Try lower threshold
   python scripts/prepare_streams.py --threshold 100  # Instead of 1000
   ```

2. **Flow accumulation incorrect**:
   ```bash
   # Verify flow accumulation looks correct
   gdalinfo -stats data/processed/dem/flow_accumulation.tif
   # Min should be 1, max should be large (10000+)
   ```

3. **DEM resolution too coarse**:
   - 90m DEM: Only major streams visible
   - 30m DEM: Medium streams
   - 10m DEM: Most streams including headwaters

### Memory Error During Processing

**Symptom**:
```
MemoryError: Unable to allocate array
```

**Solutions**:

1. **Process smaller regions**:
   ```bash
   # Clip DEM to smaller area first
   gdalwarp -te xmin ymin xmax ymax input.tif output_clipped.tif
   ```

2. **Increase system swap**:
   ```bash
   # Add 8GB swap (Linux)
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Use tiled processing**:
   - Enable windowed reading in scripts
   - Process DEM in chunks

---

## Tile Generation Issues

### PMTiles File Not Created

**Symptom**:
```
ERROR: PMTiles file not found: data/tiles/hillshade.pmtiles
```

**Solution**:
```bash
# Check if MBTiles was created
ls data/tiles/*.mbtiles

# If MBTiles exists but not PMTiles, convert manually
pmtiles convert data/tiles/hillshade.mbtiles data/tiles/hillshade.pmtiles

# If MBTiles doesn't exist, check mb-util installation
pip install mb-util
```

### Raster Tiles Not Rendering

**Symptom**:
Raster layers (hillshade, slope, aspect) appear blank in UI.

**Diagnosis**:
```bash
# Check PMTiles metadata
pmtiles show data/tiles/hillshade.pmtiles

# Look for:
# tile type: png (NOT empty or unknown)
# tile compression: png (NOT unknown)
```

**Solution if metadata missing**:
```bash
# Re-run tile generation (fixed in generate_tiles.py)
python backend/scripts/generate_tiles.py --data-dir data/processed --output-dir data/tiles

# Verify metadata inserted
pmtiles show data/tiles/hillshade.pmtiles | grep "tile type"
```

### TMS vs XYZ Tile Addressing

**Symptom**:
Tiles render in wrong locations or flipped vertically.

**Cause**: gdal2tiles created TMS tiles instead of XYZ.

**Solution**:
```bash
# MUST use --xyz flag
gdal2tiles.py --xyz --zoom 8-17 input.tif output/

# Regenerate all raster tiles with correct flag
python backend/scripts/generate_tiles.py  # Already includes --xyz
```

### Vector Layer Not Rendering

**Symptom**:
Vector layers (streams, HUC12) don't appear on map.

**Diagnosis**:
```bash
# Check internal layer name
pmtiles show data/tiles/streams_nhd.pmtiles | grep "layer ID"

# Should match vectorLayerId in frontend/src/lib/config/layers.ts
```

**Solution**:
1. Update `vectorLayerId` in `layers.ts` to match actual layer name
2. OR regenerate tiles with correct layer name using tippecanoe `-l` flag:
   ```bash
   tippecanoe -o output.mbtiles -l streams input.geojson
   ```

### Contours Missing

**Symptom**:
Contour layer unavailable or empty.

**Solution**:
```bash
# Generate contours from filled DEM
gdal_contour -a elevation -i 10 \
  data/processed/dem/filled_dem.tif \
  data/processed/contours.geojson

# Convert to tiles
python backend/scripts/generate_tiles.py --data-dir data/processed --output-dir data/tiles
```

### Categorical Raster Color Bleeding

**Symptom**:
Aspect layer shows blurred colors at tile boundaries.

**Cause**: Using wrong resampling method (lanczos instead of nearest).

**Solution**:
Aspect layer automatically uses nearest-neighbor resampling in `generate_tiles.py` (line 85-89). If still occurring:
```bash
# Manually regenerate with nearest resampling
gdal2tiles.py --xyz --resampling near --zoom 8-17 aspect.tif output/
```

---

## Backend API Issues

### Backend Won't Start

**Symptom**:
```
ERROR: Could not import module "app.main"
```

**Solution**:
```bash
# Verify in backend directory
cd backend

# Check PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Activate venv
source venv/bin/activate

# Run with full path
uvicorn app.main:app --reload
```

### Port Already in Use

**Symptom**:
```
ERROR: [Errno 48] Address already in use
```

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### File Not Found: DEM

**Symptom**:
```
503 Service Unavailable
{"detail": "Required data files not found: DEM file not found"}
```

**Solution**:
1. Check `.env` file paths:
   ```bash
   cat .env | grep DEM_PATH
   ```

2. Verify file exists:
   ```bash
   ls -l $(grep DEM_PATH .env | cut -d= -f2)
   ```

3. Use absolute paths if relative paths fail:
   ```bash
   # In .env
   DEM_PATH=/absolute/path/to/data/processed/dem/filled_dem.tif
   ```

### Watershed Delineation Returns Error

**Symptom**:
```
500 Internal Server Error
{"detail": "Watershed delineation failed: Point outside DEM coverage"}
```

**Solutions**:

1. **Point outside DEM extent**:
   - Click within DEM coverage area
   - Check DEM bounds: `gdalinfo data/processed/dem/filled_dem.tif`

2. **Flow direction invalid**:
   ```bash
   # Regenerate flow direction
   python scripts/prepare_dem.py
   ```

3. **Check backend logs**:
   ```bash
   # See detailed error
   tail -f /var/log/hydro-map/error.log
   # Or journalctl if using systemd
   sudo journalctl -u hydro-map-backend -f
   ```

### CORS Error

**Symptom** (browser console):
```
Access to fetch at 'http://localhost:8000/api/delineate' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**Solution**:
```bash
# Add frontend URL to CORS_ORIGINS in .env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Restart backend
```

### Slow API Response

**Symptom**:
Watershed delineation takes 10+ seconds.

**Solutions**:

1. **Enable caching**:
   ```bash
   # In .env
   CACHE_ENABLED=true
   CACHE_DIR=./data/cache
   ```

2. **Check DEM size**:
   ```bash
   ls -lh data/processed/dem/filled_dem.tif
   # >1 GB may be slow
   ```

3. **Add internal tiling to DEM**:
   ```bash
   gdal_translate -co TILED=YES -co COMPRESS=LZW \
     input.tif output_tiled.tif
   ```

---

## Frontend Issues

### Frontend Shows Blank Page

**Symptom**:
Browser shows blank white page, no errors in console.

**Solutions**:

1. **Check frontend is running**:
   ```bash
   curl http://localhost:5173/
   # Should return HTML
   ```

2. **Clear build cache**:
   ```bash
   cd frontend
   rm -rf .svelte-kit
   rm -rf node_modules
   npm install
   npm run dev
   ```

3. **Check for JavaScript errors**:
   - Open browser DevTools (F12)
   - Check Console tab for errors

### Map Not Loading

**Symptom**:
Map container is visible but map tiles don't load.

**Solutions**:

1. **Check basemap**:
   - Try switching basemap (Color/Light/None)
   - OpenStreetMap may be blocked by corporate firewall

2. **Check MapLibre errors**:
   - Open browser console (F12)
   - Look for MapLibre GL JS errors

3. **Verify PMTiles protocol registered**:
   ```javascript
   // In browser console
   console.log(maplibregl.version)
   ```

### Layers Not Appearing

**Symptom**:
Toggling layers in UI has no effect.

**Diagnosis**:
1. Check Tile Status panel (shows availability)
2. Open browser DevTools Network tab
3. Look for 404 errors on `/tiles/*.pmtiles`

**Solutions**:

1. **PMTiles files missing**:
   ```bash
   ls data/tiles/
   # Should show 8 .pmtiles files
   ```

2. **Incorrect vectorLayerId**:
   - Check `frontend/src/lib/config/layers.ts`
   - Verify `vectorLayerId` matches internal layer name

3. **PMTiles protocol not initialized**:
   - Refresh page (F5)
   - Check browser console for initialization errors

### Search Not Working

**Symptom**:
Location search returns no results.

**Solutions**:

1. **Nominatim API blocked**:
   - Check browser console for CORS errors
   - Corporate firewall may block nominatim.openstreetmap.org

2. **Rate limiting**:
   - Wait 60 seconds between searches
   - Nominatim has usage limits

3. **Network error**:
   ```bash
   # Test Nominatim from command line
   curl "https://nominatim.openstreetmap.org/search?q=San+Francisco&format=json"
   ```

### Watershed Delineation Hangs

**Symptom**:
Clicking map for watershed delineation shows no response.

**Solutions**:

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/api/delineate/status
   ```

2. **Check browser console**:
   - Look for API error messages
   - Check Network tab for failed requests

3. **Verify CORS**:
   - Backend must allow frontend origin
   - Check `CORS_ORIGINS` in `.env`

---

## Performance Issues

### Slow Map Pan/Zoom

**Symptoms**:
- Laggy map interactions
- Dropped frames during pan

**Solutions**:

1. **Too many visible layers**:
   - Disable unused layers
   - Only enable 2-3 layers at once

2. **Browser hardware acceleration**:
   - Enable in browser settings
   - Chrome: `chrome://settings` → Advanced → System → Use hardware acceleration

3. **Large watershed polygons**:
   - Clear old watersheds
   - Limit to <50 watershed features on map

### Slow Tile Loading

**Symptoms**:
- Tiles load slowly when zooming
- Blank tiles for several seconds

**Solutions**:

1. **Network bandwidth**:
   - Check tile file sizes: `ls -lh data/tiles/`
   - Reduce max zoom if files too large

2. **Server response time**:
   ```bash
   # Test tile request speed
   time curl -o /dev/null http://localhost:8000/tiles/hillshade.pmtiles
   ```

3. **Enable caching**:
   - Browser cache: Check DevTools → Application → Cache Storage
   - Server cache headers in reverse proxy

### High Memory Usage

**Symptoms**:
- Backend process using >2 GB RAM
- System OOM (out of memory) errors

**Solutions**:

1. **Reduce worker processes**:
   ```bash
   # In production
   gunicorn app.main:app --workers 2  # Reduce from 4+
   ```

2. **Limit concurrent requests**:
   - Configure reverse proxy to limit connections

3. **Clear cache periodically**:
   ```bash
   # Clear old cache files
   find backend/data/cache/ -mtime +30 -delete
   ```

---

## Deployment Issues

### Docker Containers Won't Start

**Symptom**:
```
ERROR: failed to solve: failed to compute cache key
```

**Solution**:
```bash
# Rebuild without cache
docker-compose build --no-cache

# Check Docker logs
docker-compose logs backend
docker-compose logs frontend
```

### Permission Denied in Docker

**Symptom**:
```
PermissionError: [Errno 13] Permission denied: '/app/data/cache'
```

**Solution**:
```bash
# Fix permissions on host
chmod -R 755 data/
chmod -R 777 backend/data/cache/

# Or use Docker volume with correct uid/gid
```

### Reverse Proxy 502 Bad Gateway

**Symptom**:
nginx returns 502 when accessing application.

**Solutions**:

1. **Backend not running**:
   ```bash
   systemctl status hydro-map-backend
   # Or check Docker: docker-compose ps
   ```

2. **Wrong upstream port**:
   - Check nginx config: `upstream backend { server localhost:8000; }`
   - Verify backend listening on that port: `netstat -tlnp | grep 8000`

3. **Firewall blocking**:
   ```bash
   # Allow port 8000 locally
   sudo ufw allow from 127.0.0.1 to any port 8000
   ```

### SSL Certificate Issues

**Symptom**:
```
SSL certificate problem: unable to get local issuer certificate
```

**Solutions**:

1. **Let's Encrypt renewal failed**:
   ```bash
   sudo certbot renew --dry-run
   # Check for errors
   ```

2. **Certificate paths incorrect**:
   - Verify nginx SSL paths exist
   - `ls -l /etc/letsencrypt/live/yourdomain.com/`

3. **Certificate expired**:
   ```bash
   # Check expiration
   echo | openssl s_client -connect yourdomain.com:443 | openssl x509 -noout -dates
   ```

---

## Getting Help

### Before Asking for Help

1. **Check logs**:
   - Backend: `journalctl -u hydro-map-backend -n 50`
   - Frontend: Browser DevTools console
   - nginx: `/var/log/nginx/error.log`

2. **Verify versions**:
   ```bash
   python3 --version
   node --version
   gdal-config --version
   ```

3. **Test with minimal example**:
   - Fresh clone of repository
   - Default configuration
   - Sample data

### Information to Include

When reporting issues, include:

1. **Environment**:
   - OS and version
   - Python version
   - Node.js version
   - GDAL version

2. **Steps to reproduce**:
   - Exact commands run
   - Configuration used
   - Sample data (if possible)

3. **Error messages**:
   - Full error text
   - Stack traces
   - Browser console errors (if frontend)

4. **Logs**:
   - Backend logs
   - nginx/proxy logs (if applicable)

### Where to Get Help

**GitHub Issues**: https://github.com/HurleySk/hydro-map/issues

**Issue template**:
```markdown
## Environment
- OS: Ubuntu 22.04
- Python: 3.11.5
- Node.js: 20.10.0
- GDAL: 3.6.2

## Problem Description
Brief description of the issue.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Error Messages
```
Paste error messages here
```

## Logs
```
Paste relevant log excerpts
```
```

---

## Related Documentation

- [Quick Start Guide](QUICK_START.md) - Getting started tutorial
- [Data Preparation](DATA_PREPARATION.md) - Data processing workflows
- [Configuration](CONFIGURATION.md) - Environment and settings
- [Deployment](DEPLOYMENT.md) - Production deployment
- [Architecture](ARCHITECTURE.md) - System design

---

## Common Error Messages Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `ModuleNotFoundError: No module named 'rasterio'` | Missing dependency | `pip install rasterio` |
| `GDAL ERROR: Cannot open file` | File doesn't exist | Check file path |
| `MemoryError: Unable to allocate` | Insufficient RAM | Process smaller regions |
| `CORS policy: No 'Access-Control-Allow-Origin'` | CORS not configured | Add origin to `CORS_ORIGINS` |
| `404 Not Found: /tiles/hillshade.pmtiles` | Tile file missing | Run `generate_tiles.py` |
| `503 Service Unavailable: DEM file not found` | Data path incorrect | Fix paths in `.env` |
| `Address already in use` | Port conflict | Kill process or use different port |
| `Failed to load PMTiles header` | Corrupt PMTiles | Regenerate tiles |
| `Layer 'streams' does not exist` | vectorLayerId mismatch | Fix `layers.ts` config |
| `Point outside DEM coverage` | Click outside DEM | Click within DEM extent |
