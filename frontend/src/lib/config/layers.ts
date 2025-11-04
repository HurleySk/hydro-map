/**
 * Unified layer configuration for the Hydro-Map application.
 * Single source of truth for all layer metadata and properties.
 */

export interface LayerPaintProperties {
  'line-color'?: string | any[];
  'line-width'?: number | any[];
  'line-opacity'?: number;
  'raster-opacity'?: number;
  [key: string]: any;
}

export interface LayerSource {
  /** Unique identifier for the layer */
  id: string;

  /** Display label for the layer in the UI */
  label: string;

  /** PMTiles filename (without path) */
  filename: string;

  /** Layer type */
  type: 'raster' | 'vector';

  /** For vector sources: the actual layer name inside the PMTiles file */
  vectorLayerId?: string;

  /** Minimum zoom level for this layer */
  minZoom?: number;

  /** Maximum zoom level for this layer */
  maxZoom?: number;

  /** Tile size for raster sources (default: 256) */
  tileSize?: number;

  /** Whether this layer is visible by default */
  defaultVisible: boolean;

  /** Default opacity (0-1) */
  defaultOpacity: number;

  /** Category for grouping in the UI */
  category: 'terrain' | 'hydrology' | 'reference';

  /** MapLibre paint properties for vector layers */
  paintProperties?: LayerPaintProperties;

  /** Description for tooltips or documentation */
  description?: string;
}

/**
 * Master configuration for all map layers.
 * Order determines rendering order (first = bottom, last = top).
 */
export const LAYER_SOURCES: LayerSource[] = [
  // Terrain layers (raster) - 1m resolution, 512px tiles
  {
    id: 'hillshade',
    label: 'Hillshade',
    filename: 'hillshade.pmtiles',
    type: 'raster',
    defaultVisible: false,
    defaultOpacity: 0.6,
    minZoom: 8,
    maxZoom: 17,
    tileSize: 512,
    category: 'terrain',
    description: 'Multi-directional shaded relief from 1m DEM'
  },
  {
    id: 'slope',
    label: 'Slope',
    filename: 'slope.pmtiles',
    type: 'raster',
    defaultVisible: false,
    defaultOpacity: 0.7,
    minZoom: 8,
    maxZoom: 17,
    tileSize: 512,
    category: 'terrain',
    description: 'Slope angle from 1m DEM (0-45 degrees)'
  },
  {
    id: 'aspect',
    label: 'Aspect',
    filename: 'aspect.pmtiles',
    type: 'raster',
    defaultVisible: false,
    defaultOpacity: 0.7,
    minZoom: 8,
    maxZoom: 17,
    tileSize: 512,
    category: 'terrain',
    description: 'Color-coded slope direction (N=red, E=yellow, S=cyan, W=blue)'
  },

  // Hydrology layers (vector)
  {
    id: 'twi',
    label: 'Topographic Wetness Index',
    filename: 'twi.pmtiles',
    type: 'raster',
    defaultVisible: false,
    defaultOpacity: 0.65,
    category: 'hydrology',
    description: 'Shows areas prone to water saturation based on upslope area and local slope',
    minZoom: 8,
    maxZoom: 17,
    tileSize: 512
  },
  {
    id: 'contours',
    label: 'Contours',
    filename: 'contours.pmtiles',
    type: 'vector',
    vectorLayerId: 'contours',
    defaultVisible: false,
    defaultOpacity: 0.8,
    category: 'terrain',
    description: 'Elevation contour lines',
    paintProperties: {
      'line-color': '#8b7355',
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10, 0.5,
        14, 1.0,
        17, 1.5
      ],
      'line-opacity': 0.8
    }
  },

  // Reference layers
  {
    id: 'fairfax-watersheds',
    label: 'Watersheds (Fairfax County)',
    filename: 'fairfax_watersheds.pmtiles',
    type: 'vector',
    vectorLayerId: 'fairfax_watersheds',
    defaultVisible: false,
    defaultOpacity: 0.3,
    category: 'reference',
    description: 'Fairfax County local watersheds (30 watershed units). Source: Fairfax County GIS',
    paintProperties: {
      // For fill layer
      'fill-color': '#6b7280',
      'fill-opacity': 0.3,
      // For outline layer (separate)
      'line-color': '#374151',
      'line-width': 2,
      'line-opacity': 0.9
    }
  },
  {
    id: 'geology',
    label: 'Geology',
    filename: 'geology.pmtiles',
    type: 'vector',
    vectorLayerId: 'geology',
    defaultVisible: false,  // Set to false by default
    defaultOpacity: 0.6,
    category: 'reference',
    description: 'Geological formations and rock types',
    paintProperties: {
      // For fill layer
      'fill-color': [
        'coalesce',
        ['get', 'color'],
        ['match',
          ['downcase', ['coalesce', ['get', 'rock_type'], ['get', 'unit'], '']],
          'igneous', '#f59e0b',
          'sedimentary', '#22c55e',
          'metamorphic', '#8b5cf6',
          'volcanic', '#ef4444',
          'plutonic', '#f97316',
          'carbonate', '#06b6d4',
          'sandstone', '#fbbf24',
          'shale', '#84cc16',
          'limestone', '#10b981',
          'granite', '#f87171',
          'basalt', '#991b1b',
          'gneiss', '#a78bfa',
          'schist', '#c084fc',
          'quartzite', '#e0e7ff',
          'unconsolidated', '#d4d4d8',
          'alluvium', '#fef3c7',
          '#9ca3af'  // fallback gray
        ]
      ],
      'fill-opacity': 0.6,
      // For outline layer (separate)
      'line-color': '#4b5563',
      'line-width': 0.5,
      'line-opacity': 0.8
    }
  },

  // Fairfax County hydrology layers
  {
    id: 'fairfax-water-lines',
    label: 'Fairfax Water Features (Lines)',
    filename: 'fairfax_water_lines.pmtiles',
    type: 'vector',
    vectorLayerId: 'fairfax_water_lines',
    defaultVisible: false,
    defaultOpacity: 0.8,
    category: 'hydrology',
    description: 'Fairfax County water features (streams, channels, ditches)',
    paintProperties: {
      'line-color': [
        'match',
        ['coalesce', ['get', 'type'], ''],
        'Stream', '#3b82f6',
        'Channel', '#06b6d4',
        'Ditch', '#6366f1',
        'Canal', '#8b5cf6',
        '#0ea5e9'  // fallback blue
      ],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10, 1.0,
        14, 2.0,
        17, 3.5
      ],
      'line-opacity': 0.8
    }
  },
  {
    id: 'fairfax-water-polys',
    label: 'Fairfax Water Features (Polygons)',
    filename: 'fairfax_water_polys.pmtiles',
    type: 'vector',
    vectorLayerId: 'fairfax_water_polys',
    defaultVisible: false,
    defaultOpacity: 0.6,
    category: 'hydrology',
    description: 'Fairfax County water bodies (ponds, lakes, reservoirs)',
    paintProperties: {
      'fill-color': [
        'match',
        ['coalesce', ['get', 'type'], ''],
        'Lake', '#0284c7',
        'Pond', '#0ea5e9',
        'Reservoir', '#0369a1',
        'Water', '#06b6d4',
        '#0891b2'  // fallback blue
      ],
      'fill-opacity': 0.6,
      'fill-outline-color': '#075985'
    }
  },
  {
    id: 'perennial-streams',
    label: 'Fairfax Perennial Streams',
    filename: 'perennial_streams.pmtiles',
    type: 'vector',
    vectorLayerId: 'perennial_streams',
    defaultVisible: false,
    defaultOpacity: 0.8,
    category: 'hydrology',
    description: 'Fairfax County perennial stream network',
    paintProperties: {
      'line-color': '#1d4ed8',  // Deep blue for perennial streams
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10, 1.5,
        14, 2.5,
        17, 4.0
      ],
      'line-opacity': 0.8
    }
  },

  // Fairfax County Stormwater and Flood Risk layers
  {
    id: 'floodplain-easements',
    label: 'Floodplain Easements',
    filename: 'floodplain_easements.pmtiles',
    type: 'vector',
    vectorLayerId: 'floodplain_easements',
    defaultVisible: false,
    defaultOpacity: 0.5,
    category: 'hydrology',
    description: 'Recorded floodplain easements in Fairfax County (non-regulatory reference). Source: Fairfax County GIS',
    paintProperties: {
      'fill-color': '#60a5fa',  // Light blue for floodplain
      'fill-opacity': 0.4,
      'fill-outline-color': '#2563eb'
    }
  },
  {
    id: 'inadequate-outfalls',
    label: 'Inadequate Outfalls',
    filename: 'inadequate_outfalls.pmtiles',
    type: 'vector',
    vectorLayerId: 'inadequate_outfalls',
    defaultVisible: false,
    defaultOpacity: 0.6,
    category: 'hydrology',
    description: 'Drainage areas with inadequate stormwater outfalls. Uses colorblind-safe Okabe-Ito palette with distinct patterns. Source: Fairfax County GIS',
    paintProperties: {
      'fill-pattern': [
        'match',
        ['get', 'determination'],
        'Erosion', 'pattern-outfall-erosion',
        'Vertical Erosion', 'pattern-outfall-vertical-erosion',
        'Left Bank Unstable', 'pattern-outfall-left-bank-unstable',
        'Right Bank Unstable', 'pattern-outfall-right-bank-unstable',
        'Left and Right Bank Unstable', 'pattern-outfall-both-banks-unstable',
        'Habitat Score', 'pattern-outfall-habitat-score',
        'pattern-outfall-erosion'  // Fallback
      ],
      'fill-opacity': 0.6,
      // Outline layer to mask pattern edge artifacts
      'line-color': [
        'match',
        ['get', 'determination'],
        'Erosion', '#C67A00',           // Darker orange
        'Vertical Erosion', '#A64800',  // Darker vermillion
        'Left Bank Unstable', '#3A8AB5', // Darker sky blue
        'Right Bank Unstable', '#005280', // Darker blue
        'Left and Right Bank Unstable', '#007D59', // Darker bluish green
        'Habitat Score', '#C0B635',     // Darker yellow
        '#6b7280'  // Gray fallback
      ],
      'line-width': 0.75,
      'line-opacity': 0.8
    }
  },
  {
    id: 'inadequate-outfall-points',
    label: 'Inadequate Outfall Points',
    filename: 'inadequate_outfall_points.pmtiles',
    type: 'vector',
    vectorLayerId: 'inadequate_outfall_points',
    defaultVisible: false,
    defaultOpacity: 0.9,
    category: 'hydrology',
    description: 'Pour points for inadequate stormwater outfalls. Source: Fairfax County GIS',
    paintProperties: {
      'circle-color': '#dc2626',  // Red for problem points
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10, 3,
        14, 5,
        17, 7
      ],
      'circle-opacity': 0.9,
      'circle-stroke-color': '#7f1d1d',
      'circle-stroke-width': 1
    }
  }
];

/**
 * Get a layer configuration by ID
 */
export function getLayerById(id: string): LayerSource | undefined {
  return LAYER_SOURCES.find(layer => layer.id === id);
}

/**
 * Get all layers in a specific category
 */
export function getLayersByCategory(category: LayerSource['category']): LayerSource[] {
  return LAYER_SOURCES.filter(layer => layer.category === category);
}

/**
 * Get initial layer visibility state for stores
 */
export function getInitialLayerState(): Record<string, { visible: boolean; opacity: number }> {
  const state: Record<string, { visible: boolean; opacity: number }> = {};
  for (const layer of LAYER_SOURCES) {
    state[layer.id] = {
      visible: layer.defaultVisible,
      opacity: layer.defaultOpacity
    };
  }
  return state;
}

/**
 * Build the PMTiles URL for a layer
 */
export function getLayerPMTilesUrl(layer: LayerSource, basePrefix: string): string {
  return `${basePrefix}${layer.filename}`;
}