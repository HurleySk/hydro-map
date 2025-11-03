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
    id: 'streams-nhd',
    label: 'Real Streams',
    filename: 'streams_nhd.pmtiles',
    type: 'vector',
    vectorLayerId: 'streams_nhd', // Actual layer name in PMTiles (with underscore)
    defaultVisible: true,
    defaultOpacity: 1.0,
    category: 'hydrology',
    description: 'Real stream network from National Hydrography Dataset',
    paintProperties: {
      'line-color': '#1e3a8a', // Dark blue
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        8, 1.0,
        14, 2.5,
        17, 4.0
      ],
      'line-opacity': 1.0
    }
  },
  {
    id: 'streams-dem',
    label: 'DEM-Derived Streams',
    filename: 'streams_dem.pmtiles',
    type: 'vector',
    vectorLayerId: 'streams', // Actual layer name in PMTiles (fixed from streams_t250_filtered)
    defaultVisible: false,
    defaultOpacity: 0.7,
    category: 'hydrology',
    description: 'Drainage network calculated from DEM',
    paintProperties: {
      'line-color': [
        'interpolate',
        ['linear'],
        ['coalesce', ['get', 'drainage_area_sqkm'], 0],
        0, '#2563eb',      // Very small: medium-dark blue
        1, '#1e40af',      // Small: dark blue
        5, '#1e3a8a',      // Medium: darker blue
        15, '#172554',     // Large: very dark blue
        50, '#0f172a'      // Very large: almost navy
      ],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        8, 0.5,
        14, 1.5,
        17, 3.0
      ],
      'line-opacity': 0.7
    }
  },
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
    id: 'huc12',
    label: 'Watersheds (HUC12)',
    filename: 'huc12.pmtiles',
    type: 'vector',
    vectorLayerId: 'huc12',
    defaultVisible: false,
    defaultOpacity: 0.3,
    category: 'reference',
    description: '12-digit Hydrologic Unit Code watersheds',
    paintProperties: {
      // For fill layer
      'fill-color': '#6b7280',
      'fill-opacity': 0.3,
      // For outline layer (separate)
      'line-color': '#374151',
      'line-width': 1,
      'line-opacity': 0.8
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