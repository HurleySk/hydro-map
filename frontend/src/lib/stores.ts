import { writable } from 'svelte/store';

export interface LayerConfig {
	visible: boolean;
	opacity: number;
}

export interface LayersState {
	[key: string]: LayerConfig;
}

export type Tool = 'none' | 'delineate' | 'cross-section' | 'info';

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
