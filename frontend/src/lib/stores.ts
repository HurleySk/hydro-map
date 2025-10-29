import { writable } from 'svelte/store';
import { getItem, setItem } from '$lib/utils/localStorage';

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

// Layer visibility and opacity
export const layers = writable<LayersState>({
	hillshade: { visible: true, opacity: 0.6 },
	slope: { visible: false, opacity: 0.7 },
	aspect: { visible: false, opacity: 0.7 },
	streams: { visible: true, opacity: 1.0 },
	geology: { visible: false, opacity: 0.7 },
	contours: { visible: false, opacity: 0.8 },
});

// Active tool
export const activeTool = writable<Tool>('none');

// Watershed results cache
export const watersheds = writable<any[]>([]);

// Cross-section data
export const crossSection = writable<any>(null);

// Map view state with localStorage persistence
export const mapView = createPersistedStore<MapViewState>('view', DEFAULT_MAP_VIEW);

// Search history with localStorage persistence
export const searchHistory = createPersistedStore<SearchHistoryItem[]>('search-history', []);
