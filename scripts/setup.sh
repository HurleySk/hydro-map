#!/bin/bash

# Hydro-Map Setup Script
# This script helps set up the development environment

set -e

echo "Hydro-Map Setup"
echo "===================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "  $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    print_error "Please run this script from the hydro-map root directory"
    exit 1
fi

echo "Step 1: Checking dependencies..."
echo "--------------------------------"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found (version $PYTHON_VERSION)"
else
    print_error "Python 3 not found. Please install Python 3.11 or later."
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found (version $NODE_VERSION)"
else
    print_error "Node.js not found. Please install Node.js 20 or later."
    exit 1
fi

# Check GDAL
if command -v gdal-config &> /dev/null; then
    GDAL_VERSION=$(gdal-config --version)
    print_success "GDAL found (version $GDAL_VERSION)"
else
    print_warning "GDAL not found. Required for data processing."
    print_info "Install with: brew install gdal (macOS) or apt-get install gdal-bin (Linux)"
fi

# Check Tippecanoe
if command -v tippecanoe &> /dev/null; then
    print_success "Tippecanoe found"
else
    print_warning "Tippecanoe not found. Required for vector tile generation."
    print_info "Install with: brew install tippecanoe (macOS)"
fi

# Check PMTiles
if command -v pmtiles &> /dev/null; then
    print_success "PMTiles CLI found"
else
    print_warning "PMTiles CLI not found. Required for tile conversion."
    print_info "Download from: https://github.com/protomaps/go-pmtiles/releases"
fi

echo ""
echo "Step 2: Creating environment file..."
echo "-------------------------------------"

if [ -f ".env" ]; then
    print_warning ".env file already exists, skipping"
else
    cp .env.example .env
    print_success "Created .env from .env.example"
    print_info "Edit .env to configure paths and settings"
fi

echo ""
echo "Step 3: Setting up Python backend..."
echo "------------------------------------"

cd backend

if [ -d "venv" ]; then
    print_warning "Virtual environment already exists"
else
    python3 -m venv venv
    print_success "Created Python virtual environment"
fi

print_info "Activating virtual environment and installing dependencies..."
source venv/bin/activate

pip install -q --upgrade pip
pip install -q -r requirements.txt

print_success "Backend dependencies installed"

deactivate
cd ..

echo ""
echo "Step 4: Setting up Node.js frontend..."
echo "--------------------------------------"

cd frontend

if [ -d "node_modules" ]; then
    print_warning "node_modules already exists"
else
    npm install
    print_success "Frontend dependencies installed"
fi

cd ..

echo ""
echo "Step 5: Creating data directories..."
echo "------------------------------------"

mkdir -p data/raw/dem
mkdir -p data/raw/hydrology
mkdir -p data/raw/geology
mkdir -p data/processed/dem
mkdir -p data/processed
mkdir -p data/tiles
mkdir -p data/cache

print_success "Data directories created"

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Download DEM data to data/raw/dem/"
echo "   - US: https://apps.nationalmap.gov/downloader/"
echo "   - Global: https://portal.opentopography.org/"
echo ""
echo "2. Process the DEM:"
echo "   python scripts/prepare_dem.py --input data/raw/dem/elevation.tif --output data/processed/dem/"
echo ""
echo "3. Extract stream network:"
echo "   python scripts/prepare_streams.py --flow-acc data/processed/dem/flow_accumulation.tif --flow-dir data/processed/dem/flow_direction.tif --output data/processed/streams.gpkg --threshold 1000"
echo ""
echo "4. Generate tiles:"
echo "   python scripts/generate_tiles.py --data-dir data/processed --output-dir data/tiles"
echo ""
echo "5. Start the application:"
echo "   Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   Terminal 2: cd frontend && npm run dev"
echo ""
echo "6. Open http://localhost:5173 in your browser"
echo ""
echo "For detailed instructions, see:"
echo "  - README.md"
echo "  - docs/DATA_PREPARATION.md"
echo ""
