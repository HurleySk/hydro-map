#!/bin/bash
#
# Pure DEM Stream Network Generation Workflow
#
# This script demonstrates the complete pipeline for generating a stream network
# entirely from DEM data, without relying on NHD or other external stream datasets.
#
# Prerequisites:
# - DEM data already processed (prepare_dem.py completed)
# - Python environment activated with all dependencies
#
# Usage:
#   bash scripts/workflow_pure_dem_streams.sh
#

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Pure DEM Stream Network Generation${NC}"
echo -e "${GREEN}================================================${NC}"

# Configuration
DATA_DIR="data/processed"
TILE_DIR="data/tiles"
DEM_DIR="${DATA_DIR}/dem"

# Input files (from prepare_dem.py)
FLOW_ACC="${DEM_DIR}/flow_accumulation.tif"
FLOW_DIR="${DEM_DIR}/flow_direction.tif"

# Output files
STREAMS_MULTI="${DATA_DIR}/streams_multi.gpkg"
STREAMS_FILTERED="${DATA_DIR}/streams_filtered.gpkg"

# Check prerequisites
echo ""
echo -e "${YELLOW}Step 0: Checking prerequisites...${NC}"

if [ ! -f "${FLOW_ACC}" ]; then
    echo -e "${RED}Error: Flow accumulation not found at ${FLOW_ACC}${NC}"
    echo "Run prepare_dem.py first!"
    exit 1
fi

if [ ! -f "${FLOW_DIR}" ]; then
    echo -e "${RED}Error: Flow direction not found at ${FLOW_DIR}${NC}"
    echo "Run prepare_dem.py first!"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"

# Step 1: Extract streams at multiple thresholds
echo ""
echo -e "${YELLOW}Step 1: Extracting streams at multiple thresholds...${NC}"
echo "  This generates streams at 100, 250, 500, and 1000 cell thresholds"
echo "  Output: ${STREAMS_MULTI}"

python scripts/prepare_streams.py \
  --flow-acc "${FLOW_ACC}" \
  --flow-dir "${FLOW_DIR}" \
  --output "${STREAMS_MULTI}" \
  --multi-threshold

echo -e "${GREEN}✓ Multi-threshold extraction complete${NC}"

# Step 2: Filter streams to remove artifacts
echo ""
echo -e "${YELLOW}Step 2: Filtering streams (removing artifacts)...${NC}"
echo "  Using finest threshold (t100) for maximum detail"
echo "  Filtering criteria:"
echo "    - Minimum length: 25m"
echo "    - Minimum drainage area: 0.1 km²"
echo "    - Sinuosity check (removes very straight short segments)"
echo "  Output: ${STREAMS_FILTERED}"

python scripts/filter_dem_streams.py \
  --input "${STREAMS_MULTI}" \
  --layer streams_t100 \
  --output "${STREAMS_FILTERED}" \
  --min-length 25 \
  --min-drainage-area 0.1 \
  --flow-acc "${FLOW_ACC}"

echo -e "${GREEN}✓ Filtering complete${NC}"

# Step 3: Inspect results
echo ""
echo -e "${YELLOW}Step 3: Inspecting results...${NC}"

echo "  Layers in ${STREAMS_FILTERED}:"
ogrinfo "${STREAMS_FILTERED}" | grep "^[0-9]:" || echo "  (none)"

echo ""
echo "  Sample attributes from filtered streams:"
ogrinfo "${STREAMS_FILTERED}" streams_t100_filtered -so 2>/dev/null | grep -E "(Feature Count|Extent|length_|drainage_|stream_type|confidence_score|sinuosity)" || echo "  Unable to read"

# Step 4: Generate PMTiles
echo ""
echo -e "${YELLOW}Step 4: Generating PMTiles for web serving...${NC}"
echo "  Output: ${TILE_DIR}/streams.pmtiles"

python scripts/generate_tiles.py \
  --data-dir "${DATA_DIR}" \
  --output-dir "${TILE_DIR}" \
  --min-zoom 8 \
  --max-zoom 17

echo -e "${GREEN}✓ Tile generation complete${NC}"

# Step 5: Validate tiles
echo ""
echo -e "${YELLOW}Step 5: Validating tiles...${NC}"

if command -v pmtiles &> /dev/null; then
    echo "  Stream PMTiles metadata:"
    pmtiles show "${TILE_DIR}/streams.pmtiles" | head -20
else
    echo "  (pmtiles CLI not available, skipping validation)"
fi

# Summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Workflow Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Output files:"
echo "  1. Multi-threshold streams: ${STREAMS_MULTI}"
echo "     - streams_t100 (finest detail)"
echo "     - streams_t250"
echo "     - streams_t500"
echo "     - streams_t1000 (major streams only)"
echo ""
echo "  2. Filtered streams: ${STREAMS_FILTERED}"
echo "     - streams_t100_filtered (artifacts removed, confidence scored)"
echo ""
echo "  3. Web tiles: ${TILE_DIR}/streams.pmtiles"
echo "     - Ready to serve via FastAPI backend"
echo ""
echo "Next steps:"
echo "  1. Start backend: cd backend && uvicorn app.main:app --reload"
echo "  2. Start frontend: cd frontend && npm run dev"
echo "  3. Open http://localhost:5173 and toggle the Streams layer"
echo "  4. Visually validate against satellite imagery"
echo ""
echo -e "${YELLOW}Tip: Adjust filtering parameters in Step 2 if you see:${NC}"
echo "  - Too many artifacts: Increase --min-length or --min-drainage-area"
echo "  - Missing real streams: Decrease thresholds or use coarser threshold (t250/t500)"
echo ""
