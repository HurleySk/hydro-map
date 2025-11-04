import { writable } from 'svelte/store';
import { getItem, setItem } from '$lib/utils/localStorage';
import { getInitialLayerState } from '$lib/config/layers';

export interface LayerConfig {
	visible: boolean;
	opacity: number;
}

export interface LayersState {
	[key: string]: LayerConfig;
}

export type Tool = 'none' | 'delineate' | 'cross-section' | 'info';

export interface MapViewState {
	center: [number, number];
	zoom: number;
	bearing?: number;
	pitch?: number;
}

export interface SearchHistoryItem {
	query: string;
	center: [number, number];
	zoom: number;
	timestamp: number;
}

// Default map view (San Francisco)
const DEFAULT_MAP_VIEW: MapViewState = {
	center: [-122.4194, 37.7749],
	zoom: 11,
	bearing: 0,
	pitch: 0
};

// Create a localStorage-persisted store
function createPersistedStore<T>(key: string, defaultValue: T) {
	const initialValue = getItem(key, defaultValue);
	const store = writable<T>(initialValue);

	store.subscribe(value => {
		setItem(key, value);
	});

	return store;
}

// Layer visibility and opacity - using centralized configuration
const initialLayerState = getInitialLayerState();

// Add the special Fairfax watersheds sub-layers (fill, outline, labels) that are managed separately
// These inherit visibility from the main fairfax-watersheds layer
const layersWithWatershedsSublayers = {
	...initialLayerState,
	'fairfax-watersheds-fill': { visible: initialLayerState['fairfax-watersheds']?.visible ?? false, opacity: 1.0 },
	'fairfax-watersheds-outline': { visible: initialLayerState['fairfax-watersheds']?.visible ?? false, opacity: 1.0 },
	'fairfax-watersheds-labels': { visible: initialLayerState['fairfax-watersheds']?.visible ?? false, opacity: 1.0 },
};

export const layers = writable<LayersState>(layersWithWatershedsSublayers);

// Active tool
export const activeTool = writable<Tool>('none');

// Watershed results cache
export const watersheds = writable<any[]>([]);

// Cross-section data
export const crossSection = writable<any>(null);

// Cross-section line points being digitized
export const crossSectionLine = writable<[number, number][]>([]);

// Latest delineation response (metadata + pour point)
export const latestDelineation = writable<any>(null);

// Watershed outlet features (snapped pour points)
export const watershedOutlets = writable<any[]>([]);

// Delineation settings persisted in UI
export interface DelineationSettings {
	snapToStream: boolean;
	snapRadius: number;
}

export const delineationSettings = writable<DelineationSettings>({
	snapToStream: true,
	snapRadius: 100
});

export interface TileStatusItem {
	id: string;
	label: string;
	available: boolean;
	message?: string;
}

export const tileStatus = writable<TileStatusItem[]>([]);

// Map view state with localStorage persistence
export const mapView = createPersistedStore<MapViewState>('view', DEFAULT_MAP_VIEW);

// Search history with localStorage persistence
export const searchHistory = createPersistedStore<SearchHistoryItem[]>('search-history', []);

// UI panel expansion states
export interface PanelStates {
	mapLayers: boolean;
	analysisTools: boolean;
	systemStatus: boolean;
}

export const panelStates = createPersistedStore<PanelStates>('panel-states', {
	mapLayers: true,      // Expanded by default
	analysisTools: true,  // Expanded by default
	systemStatus: false   // Collapsed by default
});

// Layer group expansion states
export interface LayerGroupStates {
	terrain: boolean;
	hydrology: boolean;
	reference: boolean;
}

export const layerGroupStates = createPersistedStore<LayerGroupStates>('layer-group-states', {
	terrain: false,           // Collapsed by default
	hydrology: true,          // Expanded by default (includes Fairfax layers)
	reference: true           // Expanded to show geology controls
});

// Basemap style selection
export type BasemapStyle = 'vector' | 'light' | 'none';

export const basemapStyle = createPersistedStore<BasemapStyle>('basemap-style', 'vector');
