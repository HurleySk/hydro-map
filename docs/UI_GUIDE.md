# User Interface Guide

**Version**: 1.9.0  
Hydro-Map runs at `http://localhost:5173` in development (SvelteKit dev server).

---

## 1. Map Navigation

- **Pan**: drag with left mouse button (one finger on touch)
- **Zoom**: scroll wheel, trackpad pinch, or `+ / –` buttons in the top-right corner
- **Rotate/Pitch**: right-drag (or `Ctrl` + drag); click the compass to reset north-up
- **Search**: use the search bar to geocode places (powered by Nominatim). Recent searches persist in local storage.

---

## 2. Panels & Layout

The left sidebar has three collapsible panels whose open/closed state persists between sessions.

### 2.1 Map Layers

Layers are grouped and defined in `frontend/src/lib/config/layers.ts`. Each entry offers a visibility toggle and an opacity slider when enabled.

- **Terrain**  
  `Hillshade`, `Slope`, `Aspect`, `Contours`

- **Hydrology**  
  `Topographic Wetness Index`, `Fairfax Water Features (Lines)`, `Fairfax Water Features (Polygons)`, `Fairfax Perennial Streams`, `Floodplain Easements`, `Inadequate Outfalls`, `Inadequate Outfall Points`

- **Reference**  
  `Fairfax Watersheds` (outline + labels) and `Geology`

Tips:

- Combine `Hillshade` (40–60 % opacity) with vector layers for context.  
- TWI is rendered as a semitransparent raster; adjust opacity to blend with the basemap.  
- When `Geology` is visible, a legend automatically appears in the lower-right corner.

### 2.2 Analysis Tools

- **Feature Info** – activates a click-to-query mode. Adjust the **Search Buffer** slider (10–200 m). Responses show geology (if available), Fairfax watershed metadata, stormwater outfalls (when enabled), and DEM samples.
- **Delineate Watershed** – click the map to snap (optional) and compute an upstream catchment. Results appear in the map and a summary card.
- **Draw Cross-Section** – digitize a line; hit “Generate Profile” to view the elevation chart and geology contacts. “Clear Line” resets the tool.

### 2.3 System Status

The Tile Status panel lists every PMTiles source referenced by the UI, flagging whether the current viewport intersects available tiles and displaying the max native zoom.

---

## 3. Basemap Toggle

The floating Basemap widget (bottom-right) switches between:

- **Detailed** – Stadia vector basemap (requires API key)
- **Minimal** – Light cartographic style with subdued colours
- **Data Only** – No basemap; ideal when layering hillshade or dense overlays

The selection is stored in localStorage (`basemapStyle`).

---

## 4. Analysis Outputs

- Watershed delineations remain on the map until cleared or replaced; multiple delineations are listed in the Watershed tool.
- Cross-section charts support hover tooltips showing station distance and elevation. Geology contacts render as brightly coloured bands.
- Feature Info results show warnings when data is missing or when the service falls back to the nearest feature (e.g., outside a polygon).

---

## 5. Keyboard & Productivity Tips

- `Esc` exits the currently active tool.  
- When drawing cross-sections, double-click (or press `Enter`) to finish the line quickly.  
- Use browser split panes or a second monitor to keep API logs visible while working in the UI.

---

## 6. Troubleshooting UI Issues

- Blank map? Confirm the frontend dev server is running and that the backend `/tiles/*` endpoints return `200`.  
- Missing layers? Check that corresponding PMTiles exist in `data/tiles/` and reload the page to refresh the Layer Panel configuration.  
- Stuck tool state? Refresh or clear localStorage (`localStorage.clear()`) to reset persisted UI state.

For backend-specific errors, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
