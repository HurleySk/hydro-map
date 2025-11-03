# User Interface Guide

**Version**: 1.5.0

## Overview

Hydro-Map provides an intuitive web interface for watershed analysis and hydrological visualization. This guide covers all UI features, tools, and controls available in the application.

**Access**: Open your browser to `http://localhost:3000` (default development configuration)

## Table of Contents

- [Map Navigation](#map-navigation)
- [Layer Panel](#layer-panel)
- [Basemap Toggle](#basemap-toggle)
- [Location Search](#location-search)
- [Watershed Delineation Tool](#watershed-delineation-tool)
- [Cross-Section Tool](#cross-section-tool)
- [Feature Info Tool](#feature-info-tool)
- [Tile Status Panel](#tile-status-panel)
- [UI State Persistence](#ui-state-persistence)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Tips and Best Practices](#tips-and-best-practices)

---

## Map Navigation

### Basic Controls

**Mouse Controls**:
- **Pan**: Click and drag to move the map
- **Zoom**:
  - Scroll wheel up/down
  - Double-click to zoom in
  - Shift + double-click to zoom out
- **Rotate**: Right-click and drag (or Ctrl + drag)
- **Pitch**: Ctrl + drag up/down (tilt map for 3D perspective)

**Touch Controls** (mobile/tablet):
- **Pan**: Single-finger drag
- **Zoom**: Pinch gesture
- **Rotate**: Two-finger rotate gesture
- **Pitch**: Two-finger drag up/down

### Zoom Controls

Located in the top-right corner of the map:
- **[+] button**: Zoom in one level
- **[-] button**: Zoom out one level
- **Compass**: Click to reset north (rotation to 0°)

### Navigation Tips

- **Default location**: San Francisco, CA (37.7749°N, 122.4194°W)
- **Zoom range**: z0 (world) to z17 (building level)
- **Recommended zoom**: z10-z14 for watershed analysis
- **Terrain detail**: Best visible at z12+

---

## Layer Panel

The Layer Panel controls which map layers are visible and their appearance.

### Location

Left sidebar, top section

### Layer Groups

Layers are organized into collapsible groups:

#### **Terrain** (4 layers)
- **Hillshade**: Grayscale shaded relief showing terrain texture
- **Slope**: Gradient color map showing terrain steepness (0-45+ degrees)
- **Aspect**: Directional color map showing slope orientation (N/E/S/W)
- **Contours**: 10 m elevation contour lines derived from the DEM

#### **Hydrology** (3 layers)
- **Real Streams**: NHD-based stream network (US only, curated data)
- **Drainage Network**: DEM-derived calculated streams (global coverage)
- **Topographic Wetness Index (TWI)**: Raster portraying likely wet areas (blue gradient; darker = wetter)

#### **Reference** (2 layers)
- **HUC12 Watersheds**: USGS watershed boundary reference layer with outlines and labels
- **Geology**: Geological formations with distinct patterns (if data available)
  - Colored by rock type (igneous, sedimentary, metamorphic, volcanic, etc.)
  - Texture patterns for colorblind accessibility
  - Legend automatically appears when geology is visible

### Layer Controls

#### Visibility Toggle

Each layer has a checkbox to control visibility:
- **Checked**: Layer is visible on the map
- **Unchecked**: Layer is hidden

**Default visibility** (on startup):
- Real Streams (NHD): ✓ (visible)
- All other layers: ✗ (hidden until toggled on)

#### Opacity Slider

When a layer is visible, an opacity slider appears below it:
- **Range**: 0% (transparent) to 100% (opaque)
- **Default**: Most layers start at 100%
- **Use case**: Lower opacity to see layers beneath

**Example use**: Set hillshade to 50% opacity to see underlying basemap terrain.

### Expanding/Collapsing Groups

Click the group header (e.g., "Terrain") to expand or collapse that section:
- **Chevron (▶)**: Points right when collapsed, rotates down when expanded
- **State persistence**: Group expansion states are saved to localStorage

### Layer Combination Strategies

**Terrain Analysis**:
```
✓ Hillshade (60% opacity)
✓ Slope (80% opacity)
✗ Aspect
```

**Stream Comparison**:
```
✓ Hillshade (40% opacity)
✓ Real Streams (100% opacity)
✓ Drainage Network (70% opacity)
```
*Compare NHD streams with DEM-derived streams to validate accuracy*

**Watershed Context**:
```
✓ Hillshade (50% opacity)
✓ Real Streams (100% opacity)
✓ HUC12 Watersheds (80% opacity)
✓ Contours (60% opacity)
```
*Full hydrological context with reference boundaries*

---

## Basemap Toggle

Control the underlying reference map with feature-rich vector basemaps from Stadia Maps.

### Location

Left sidebar, near top of controls

### Options

- **Detailed**: High-detail vector basemap with rich POI display (parks, schools, buildings, land use, roads)
- **Minimal**: Clean, minimal style with reduced visual clutter (streets and basic labels only)
- **Data Only**: No basemap (only show your hydrological data layers)

### Default

**Detailed** basemap is selected by default.

### Use Cases

- **Detailed**: General navigation, understanding land use context, identifying features (schools, parks, buildings)
- **Minimal**: Balanced view with subtle basemap and emphasis on data layers
- **Data Only**: Maximum emphasis on terrain/hydrology layers only

### Configuration

Basemaps require a Stadia Maps API key configured in `.env`:
```bash
VITE_STADIA_API_KEY=your_api_key_here
```

**Free tier**: 20,000 map views/month. Sign up at https://client.stadiamaps.com/signup/

**Tip**: Use "Data Only" mode if no API key is configured, or when working with hillshade layer to avoid visual conflict.

---

## Location Search

Quickly navigate to any location by name or address.

### Location

Top of left sidebar

### Features

#### **Search Box**

Type any location query:
- City names: "San Francisco", "Portland"
- Full addresses: "1600 Pennsylvania Ave, Washington DC"
- Landmarks: "Golden Gate Bridge", "Yellowstone National Park"
- Coordinates: "37.7749, -122.4194" (lat, lon)

**Behavior**:
- Search begins automatically after 300ms pause
- Results appear as you type
- Maximum 5 results shown

#### **Search Results**

Results display with:
- **Name**: Location display name
- **Type**: City, county, park, etc.
- **Context**: State, country

**Selection**:
- **Click** a result to fly to that location
- **Arrow keys** (↑/↓) to navigate results
- **Enter** to select highlighted result
- **Escape** to close results

#### **Search History**

Click the search box (when empty) to see recent searches:
- Last 10 searches displayed
- Most recent at top
- Click any history item to return to that location

**History management**:
- Automatically saves searches to localStorage
- Duplicates are removed
- Persists across browser sessions

### Keyboard Navigation

- **Arrow Down (↓)**: Highlight next result
- **Arrow Up (↑)**: Highlight previous result
- **Enter**: Select highlighted result and fly to location
- **Escape**: Close search results/history

### Search Behavior

When you select a location:
1. Map flies to location with smooth animation
2. Zoom level adjusts based on result type:
   - City: z12
   - County: z10
   - State: z7
   - Park: z13
3. Location is added to search history

### Data Source

**Provider**: [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap geocoding service)

**Coverage**: Global

**Rate limiting**: Respectful delays between requests (300ms debounce)

---

## Watershed Delineation Tool

Delineate upstream watersheds from any point on the map.

### Location

Left sidebar, middle section

### Workflow

#### 1. Activate Tool

Click **"Delineate Watershed"** button
- Button turns blue (active state)
- Instructions appear: "Click anywhere on the map to delineate the upstream watershed"
- Cursor changes to crosshair on map

#### 2. Configure Settings

**Snap to nearest stream**:
- ☑ Enabled (default): Pour point automatically adjusts to nearest stream
- ☐ Disabled: Pour point stays at exact click location

**Snap radius** (only if snap enabled):
- **Range**: 10m to 500m
- **Default**: 100m
- **Slider**: Drag to adjust maximum snap distance
- **Display**: Shows current value (e.g., "100 m")

**Recommendation**: Keep snap enabled unless you need exact coordinates.

#### 3. Click Map

Click anywhere on the map:
- **Processing**: Brief wait while backend delineates watershed (typically 1-3 seconds)
- **Success**:
  - Watershed polygon appears (blue fill, dark blue outline)
  - Pour point marker appears (red dot or adjusted location)
  - Statistics appear in tool panel
- **Error**: Alert if processing fails (e.g., point outside DEM coverage)

#### 4. Review Results

Tool panel shows:
- **Watershed count**: Total watersheds delineated in session
- **Latest statistics**:
  - Area (km²)
  - Snap radius used
  - Flow accumulation (cells)
  - Processing time (seconds)

#### 5. Multiple Watersheds

Click additional points:
- Each new watershed is added to the map
- All watersheds remain visible
- Latest statistics update with each new delineation

#### 6. Clear Results

Click **"Clear All"** button to remove all watersheds from map.

#### 7. Deactivate Tool

Click **"Cancel"** button (or activate another tool) to exit delineation mode.

### Caching

Results are cached by:
- Coordinates (6 decimal places ≈ 11cm precision)
- Snap to stream setting
- Snap radius

**Benefit**: Clicking the same location again retrieves results instantly without reprocessing.

**Cache location**: `backend/data/cache/watersheds/`

### Limitations

- **DEM coverage**: Point must be within processed DEM extent
- **Performance**: Large watersheds (>100 km²) may take 5-10 seconds
- **Memory**: Very large watersheds may fail due to memory limits

### Tips

- **Use snap**: Snapping to streams ensures pour point is on drainage network
- **Adjust snap radius**: Increase for sparse stream networks, decrease for dense areas
- **Multiple watersheds**: Compare nested watersheds by clicking upstream points
- **Check flow accumulation**: Values >1000 cells indicate significant drainage

---

## Cross-Section Tool

Generate elevation profiles along a user-drawn line.

### Location

Left sidebar, middle section

### Workflow

#### 1. Activate Tool

Click **"Draw Cross-Section"** button
- Button turns blue (active state)
- Instructions appear: "Click two or more points on the map to draw a profile line"
- Cursor changes to crosshair on map

#### 2. Draw Line

Click points on the map:
- **First click**: Start point (red marker)
- **Second click**: End point, line appears connecting points
- **Additional clicks**: Add intermediate points, line segments update
- **Minimum**: 2 points required

**Visual feedback**:
- Red circular markers at each point
- Blue line connecting points in order
- Point count displayed: "Points: 3"

#### 3. Generate Profile

When you have 2+ points:
- Click **"Generate Profile"** button
- Processing begins (typically <1 second)
- Summary card appears showing total distance, sample count, and geology contact count
- Elevation chart appears below the summary

#### 4. View Chart

The cross-section chart displays:
- **X-axis**: Distance along line (meters)
- **Y-axis**: Elevation (meters)
- **Line**: Elevation profile
- **Hover**: Tooltip shows exact distance and elevation values

**Chart interactions**:
- **Hover**: See precise values at any point
- **Zoom**: Scroll wheel to zoom chart
- **Pan**: Click and drag chart

#### 5. Geology (if available)

If geology data is loaded, colored bands show geological formations:
- **Colors**: Different rock types have distinct colors
- **Labels**: Formation names on hover
- **Contacts**: Boundaries between formations; summary card lists total contacts

#### 6. Edit Line

To modify the line:
- Click **"Clear Line"** button
- Draw new line from scratch
- Click **"Generate Profile"** again

#### 7. Deactivate Tool

Click **"Cancel"** button to exit cross-section mode and clear line.

### Parameters

**Sample distance**: Default 10m (configured in backend)
- Smaller values: More detail, slower processing
- Larger values: Less detail, faster processing
- Can be configured in API request (1-100m)

**Max points**: 1000 samples maximum (backend limit)
- Long lines are automatically downsampled to stay within limit

### Use Cases

**Terrain Analysis**:
- Draw across ridges to measure relief
- Identify valley depths
- Measure slope angles

**Stream Profiles**:
- Draw along stream course to see longitudinal profile
- Identify knickpoints (slope breaks)
- Calculate stream gradients

**Watershed Transects**:
- Draw across watershed to see topography
- Identify drainage divides
- Measure watershed depth

### Tips

- **Hillshade overlay**: Enable hillshade layer to see terrain context while drawing
- **Follow streams**: Trace stream courses to analyze channel profiles
- **Perpendicular to contours**: Draw across contours for steepest slopes
- **Zoom in**: Higher zoom levels (z14-z16) provide better point placement accuracy

---

## Feature Info Tool

Query map features by clicking to get detailed attributes.

### Location

Left sidebar, bottom section

### Workflow

#### 1. Activate Tool

Click **"Feature Info"** button
- Button turns blue (active state)
- Instructions appear: "Click on a feature to get information"
- Cursor changes to pointer on map
- Search Buffer slider appears (10-200 m); adjust before clicking the map

#### 2. Click Feature

Click any location on the map:
- **Processing**: Query executes (typically <500ms)
- **Results**: Panel shows feature attributes

#### 3. View Results

**Streams** (if clicked near stream):
- Name (from NHD) or "Unnamed"
- Length (km)
- Drainage area (km²)
- Stream order (Strahler classification)
- Stream type (Perennial/Intermittent/Ephemeral for DEM-derived)
- Upstream length (total network length upstream)
- Slope (average channel gradient)
- Elevation range (min/max)

**Geology** (if available and clicked on polygon):
- Formation name
- Rock type
- Geological age
- Formation description
- Returned even if the geology layer is toggled off (for contextual awareness)

**No features**:
- Message: "No features found at this location"

#### 4. Buffer Distance

Default: 10m search buffer around click point
Adjustable: 10-200 m via the slider in the Feature Info panel

**Rationale**: Allows clicking "near" a stream without perfect precision.

#### 5. Multiple Features

If multiple features are within buffer:
- All features are listed
- Grouped by type (Streams, Geology)

#### 6. Deactivate Tool

Click **"Cancel"** button to exit feature info mode.

### Supported Layers

Currently queries:
- **Streams**: Both NHD and DEM-derived streams
- **Geology**: If geology data is available

**Note**:
- Other layers (hillshade, slope, aspect, contours, HUC12) are not queryable via feature info tool because they lack click-ready attributes.
- If both stream layers are hidden, the tool automatically queries **Real Streams** (NHD) to provide context.
- Geology is queried regardless of layer visibility so rock information is always returned when data is available.

### Use Cases

**Stream Identification**:
- Click stream to get name and properties
- Verify stream order
- Check drainage area

**Comparing Stream Sources**:
- Enable both "Real Streams" and "Drainage Network" layers
- Click same location to see both NHD and DEM-derived attributes
- Compare drainage area calculations

**Geological Context**:
- Identify bedrock formations
- Understand rock types for infiltration analysis
- Check geological age

### Tips

- **Zoom in**: More accurate clicking at higher zoom levels
- **Layer visibility**: Visible stream layers are queried; if none are visible the tool falls back to Real Streams. Geology is queried even when the layer is hidden.
- **Stream selection**: If clicking doesn't find stream, try zooming in or clicking directly on the blue line

---

## Tile Status Panel

Monitor availability and health of PMTiles sources.

### Location

Bottom-right corner of screen (collapsible panel)

### Display

Shows status for each PMTiles file:

**Green (Available)**:
- Tile file found
- Header successfully read
- Coverage confirmed for current map view
- Max zoom reported

**Red (Unavailable)**:
- Tile file not found (404 error)
- File exists but header read failed
- Coverage does not include current map view

### Status Messages

- **"Available (max zoom: 17)"**: File is working and supports up to z17
- **"Unavailable - File not found"**: PMTiles file missing from `/data/tiles/`
- **"Unavailable - No coverage in this area"**: Valid file but current map view is outside tile bounds
- **"Checking..."**: Initial load, status pending

### Monitored Tiles

- Hillshade (hillshade.pmtiles)
- Slope (slope.pmtiles)
- Aspect (aspect.pmtiles)
- Real Streams (streams_nhd.pmtiles)
- Drainage Network (streams_dem.pmtiles)
- Topographic Wetness Index (twi.pmtiles)
- Contours (contours.pmtiles)
- HUC12 Watersheds (huc12.pmtiles)
- Geology (geology.pmtiles)

### Troubleshooting

If tiles show as unavailable:

1. **Check file existence**:
   ```bash
   ls data/tiles/
   ```
   Verify PMTiles files are present.

2. **Regenerate tiles**:
   ```bash
   python backend/scripts/generate_tiles.py
   ```

3. **Check backend logs**:
   Look for 404 errors or file access issues

4. **Verify coverage**:
   Some tiles may only cover specific regions. Move map to covered area.

See [Troubleshooting Guide](TROUBLESHOOTING.md) for more details.

---

## UI State Persistence

Hydro-Map automatically saves your UI preferences and restores them when you return.

### Persisted State

**Map View** (in localStorage as `mapView`):
- Center coordinates (lat/lon)
- Zoom level
- Bearing (rotation)
- Pitch (tilt)

**Layer Visibility** (in localStorage as `layers`):
- Each layer's visibility state (on/off)
- Each layer's opacity value (0-100%)

**Layer Groups** (in localStorage as `layerGroupStates`):
- Terrain group: expanded or collapsed
- Hydrology group: expanded or collapsed

**Search History** (in localStorage as `searchHistory`):
- Last 10 location searches
- Coordinates and zoom levels
- Timestamps

**Panel States** (in localStorage as `panelStates`):
- Each collapsible panel: expanded or collapsed
- Left sidebar scroll position

**Basemap Selection** (in localStorage as `basemapStyle`):
- Current basemap: 'osm', 'light', or 'none'

### Storage Location

**Browser localStorage** (per-domain):
```javascript
localStorage.getItem('mapView')
localStorage.getItem('layers')
localStorage.getItem('layerGroupStates')
localStorage.getItem('searchHistory')
localStorage.getItem('panelStates')
localStorage.getItem('basemapStyle')
```

### Clearing State

To reset to defaults:

**Option 1 - Browser DevTools**:
1. Open DevTools (F12)
2. Go to "Application" tab
3. Select "Local Storage" → `http://localhost:3000`
4. Right-click and "Clear"
5. Refresh page

**Option 2 - Console**:
```javascript
localStorage.clear()
location.reload()
```

### Privacy Note

All state is stored **locally in your browser**. Nothing is sent to a server. Clearing browser data clears this state.

---

## Keyboard Shortcuts

### Map Navigation

- **Arrow keys**: Pan map in direction
- **+ / =**: Zoom in
- **- / _**: Zoom out
- **Shift + Drag**: Draw box to zoom to area

### Search

- **↓ (Down Arrow)**: Highlight next search result
- **↑ (Up Arrow)**: Highlight previous search result
- **Enter**: Select highlighted result and fly to location
- **Escape**: Close search results

### Tool Activation

Currently no keyboard shortcuts for tool activation. Use mouse/touch to click tool buttons.

**Future enhancement**: Consider adding keyboard shortcuts (e.g., `W` for watershed, `X` for cross-section, `I` for info).

---

## Tips and Best Practices

### Performance

**Slow map performance**:
- Disable layers you're not using
- Lower opacity doesn't improve performance (still rendered)
- Use basemap "None" if you don't need it

**Layer rendering priority**:
1. Basemap (bottom)
2. Hillshade
3. Slope/Aspect
4. Flow Accumulation
5. HUC12 fill
6. Contours
7. Streams
8. HUC12 outline
9. HUC12 labels
10. Watersheds/Tools (top)

### Visual Clarity

**Too many overlapping layers**:
- Group layers thematically (terrain OR hydrology, not both)
- Use opacity sliders to reduce visual weight
- Toggle layers on/off as needed

**Best combinations**:
- **Minimal**: Hillshade (50%) + Real Streams (100%) + Basemap None
- **Detailed**: Hillshade (40%) + Slope (60%) + Real Streams (100%) + Contours (50%)
- **Validation**: Hillshade (30%) + Real Streams (100%) + Drainage Network (70%)

### Workflow Optimization

**Delineating multiple watersheds**:
1. Enable "Snap to nearest stream"
2. Set snap radius to 200m for regional work
3. Click multiple points without deactivating tool
4. Review all watersheds together before clearing

**Comparing stream sources**:
1. Enable both "Real Streams" and "Drainage Network"
2. Set "Drainage Network" to 70% opacity
3. Look for disagreements (NHD vs DEM-derived)
4. Use Feature Info tool to compare attributes

**Analyzing terrain**:
1. Start with Hillshade only
2. Add Slope to identify steep areas
3. Add Contours for quantitative elevation
4. Use Cross-Section tool to measure specific transects

### Data Quality Checks

**Verifying stream accuracy**:
- Compare "Real Streams" (NHD) with "Drainage Network" (DEM-derived)
- DEM streams should generally align with NHD, but may show additional ephemeral channels
- Significant disagreement indicates DEM issues or NHD gaps

**Checking watershed boundaries**:
- Watershed should follow topographic divides (ridges)
- Enable Hillshade or Slope to verify boundary placement
- Pour point should be on stream (if snap enabled)

**Validating cross-sections**:
- Profile should show smooth transitions (not jagged)
- Jagged profiles indicate DEM noise or insufficient resolution
- Stream profiles should show consistent downstream gradient

---

## Related Documentation

- [Quick Start Guide](QUICK_START.md) - Getting started tutorial
- [Architecture](ARCHITECTURE.md) - System design and component overview
- [API Reference](API.md) - Backend API endpoints
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

## Feedback and Issues

Found a bug or have a feature request?

**GitHub Issues**: https://github.com/HurleySk/hydro-map/issues

When reporting UI issues, please include:
- Browser and version (Chrome 120, Firefox 121, etc.)
- Operating system (macOS 14, Windows 11, Ubuntu 22.04, etc.)
- Steps to reproduce the issue
- Screenshots if applicable
- Browser console errors (F12 → Console tab)
