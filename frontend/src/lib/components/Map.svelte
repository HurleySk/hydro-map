<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { get } from 'svelte/store';
	import maplibregl from 'maplibre-gl';
	import type { StyleSpecification } from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
import { Protocol, PMTiles } from 'pmtiles';
import {
	layers,
	watersheds,
	mapView,
	activeTool,
	crossSectionLine,
	crossSection,
	watershedOutlets,
	latestDelineation,
	delineationSettings,
	tileStatus,
	basemapStyle,
	type BasemapStyle
} from '$lib/stores';
import { LAYER_SOURCES, getLayerPMTilesUrl } from '$lib/config/layers';
import { getApiUrl, apiPost } from '$lib/api/config';
import { mapLogger as logger } from '$lib/utils/logger';
import {
	generatePattern,
	geologyPatterns,
	type GeologyType,
	generateOutfallPattern,
	outfallPatterns,
	type OutfallDeterminationType
} from '$lib/utils/patterns';

	const dispatch = createEventDispatcher();

	// Basemap sources configuration
	const BASEMAP_SOURCES = {
		light: {
			type: 'raster',
			tiles: [
				'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
				'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
				'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
			],
			tileSize: 256,
			attribution: '© OpenStreetMap contributors'
		},
		vector: {
			type: 'vector',
			url: 'https://api.maptiler.com/tiles/v3-openmaptiles/tiles.json?key=YOUR_KEY'
		}
	};

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map;
	let saveTimeout: number;
	let searchMarker: maplibregl.Marker | null = null;
let unsubscribeLayers: () => void = () => {};
let unsubscribeWatersheds: () => void = () => {};
let unsubscribeCrossSection: () => void = () => {};
let unsubscribeOutlets: () => void = () => {};
let unsubscribeBasemap: () => void = () => {};
let mapReady = false; // Track when map is fully initialized
let styleReady = false; // Track when style graph is ready
let updateQueue: Array<{ type: string; data: any }> = []; // Queue for updates before style ready

type TileHeaderBounds = {
	minLon: number;
	minLat: number;
	maxLon: number;
	maxLat: number;
};

type TileMeta = {
	url: string;
	header?: TileHeaderBounds;
	minZoom?: number;
	maxZoom?: number;
	error?: string;
};

// Use centralized layer configuration
const tileSources = LAYER_SOURCES;

const tileMetadata = new Map<string, TileMeta>();

let tileBasePath = '/tiles';
let pmtilesBasePrefix = 'pmtiles:///tiles';
let pmtilesProtocol: Protocol | null = null;
let tileStatusInitialized = false;

// Basemap configuration - Stadia Maps for feature-rich display
const STADIA_API_KEY = import.meta.env.VITE_STADIA_API_KEY || '';

const BASEMAP_STYLE_URLS = {
	detailed: `https://tiles.stadiamaps.com/styles/osm_bright.json?api_key=${STADIA_API_KEY}`,
	light: `https://tiles.stadiamaps.com/styles/alidade_smooth.json?api_key=${STADIA_API_KEY}`
} as const;

function buildTileHttpUrl(filename: string): string {
	const base = tileBasePath.endsWith('/') ? tileBasePath.slice(0, -1) : tileBasePath;
	const path = `${base}/${filename}`;
	if (/^https?:\/\//.test(path)) {
		return path;
	}
	if (typeof window !== 'undefined') {
		return new URL(path, window.location.origin).toString();
	}
	return path;
}

function buildPmtilesUrl(filename: string): string {
	const base = pmtilesBasePrefix.endsWith('/') ? pmtilesBasePrefix.slice(0, -1) : pmtilesBasePrefix;
	return `${base}/${filename}`;
}

function headerToBounds(header: any): TileHeaderBounds {
	const minLon = header.minLonE7 !== undefined ? header.minLonE7 / 1e7 : header.minLon ?? -180;
	const minLat = header.minLatE7 !== undefined ? header.minLatE7 / 1e7 : header.minLat ?? -90;
	const maxLon = header.maxLonE7 !== undefined ? header.maxLonE7 / 1e7 : header.maxLon ?? 180;
	const maxLat = header.maxLatE7 !== undefined ? header.maxLatE7 / 1e7 : header.maxLat ?? 90;
	return { minLon, minLat, maxLon, maxLat };
}

	// Default center (adjusted to Mason District Park, Annandale, VA)
	const DEFAULT_CENTER: [number, number] = [-77.2045, 38.8358];
	const DEFAULT_ZOOM = 17;

	onMount(() => {
		let destroy: (() => void) | undefined;

		// Run async initialization without making the onMount callback async
		(async () => {
			const envBase = (import.meta.env.VITE_TILE_BASE ?? import.meta.env.VITE_API_URL ?? '') as string;
		const devDefault = typeof window !== 'undefined'
			? (window.location.port === '5173' ? 'http://localhost:8000' : window.location.origin)
			: '';
		const backendBaseRaw = envBase || devDefault;
		const backendBase = backendBaseRaw ? backendBaseRaw.replace(/\/$/, '') : '';
		if (backendBase) {
			tileBasePath = `${backendBase}/tiles`;
			pmtilesBasePrefix = `pmtiles://${backendBase}/tiles`;
		} else if (typeof window !== 'undefined') {
			const origin = window.location.origin.replace(/\/$/, '');
			tileBasePath = '/tiles';
			pmtilesBasePrefix = `pmtiles://${origin}/tiles`;
		} else {
			tileBasePath = '/tiles';
			pmtilesBasePrefix = 'pmtiles:///tiles';
		}

			// Register PMTiles protocol
			const protocol = new Protocol({ metadata: true });
			maplibregl.addProtocol('pmtiles', protocol.tile);
			pmtilesProtocol = protocol;

			// Initialize PMTiles instances BEFORE creating map
			// This ensures Protocol has all instances registered when MapLibre tries to resolve pmtiles:// URLs
			await initializeTileStatus();

			// Get saved view or use defaults
			const savedView = $mapView;

			// Validate saved center - reject if too far from data area (>100km from default)
			let initialCenter = DEFAULT_CENTER;
			if (savedView?.center) {
				const dx = savedView.center[0] - DEFAULT_CENTER[0];
				const dy = savedView.center[1] - DEFAULT_CENTER[1];
				const distanceKm = Math.sqrt(dx * dx + dy * dy) * 111; // rough conversion to km
				if (distanceKm < 100) {
					initialCenter = savedView.center;
				}
			}

			const initialZoom = savedView?.zoom || DEFAULT_ZOOM;

			// If current center is outside any tile coverage, recenter to data
			const centerWithinCoverage = () => {
				for (const meta of tileMetadata.values()) {
					if (meta.header) {
						const { minLon, minLat, maxLon, maxLat } = meta.header;
						if (
							initialCenter[0] >= minLon &&
							initialCenter[0] <= maxLon &&
							initialCenter[1] >= minLat &&
							initialCenter[1] <= maxLat
						) {
							return true;
						}
					}
				}
				return false;
			};

			if (!centerWithinCoverage()) {
				// Use any available tile header for coverage
				const preferred = Array.from(tileMetadata.values()).find(m => m.header)?.header;
				if (preferred) {
					initialCenter = [
						(preferred.minLon + preferred.maxLon) / 2,
						(preferred.minLat + preferred.maxLat) / 2
					];
				}
			}

		// Initialize map with basemap style
		const currentBasemap = get(basemapStyle);
		let initialStyle: string | StyleSpecification;

		if (currentBasemap === 'none') {
			// No basemap - use custom minimal style
			initialStyle = createMapStyle();
		} else {
			// Load Stadia Maps style URL
			initialStyle = currentBasemap === 'light' ? BASEMAP_STYLE_URLS.light : BASEMAP_STYLE_URLS.detailed;
		}

		map = new maplibregl.Map({
			container: mapContainer,
			style: initialStyle,
			center: initialCenter,
			zoom: initialZoom,
			bearing: savedView?.bearing || 0,
			pitch: savedView?.pitch || 0,
			maxZoom: 19,
			minZoom: 8
		});

		// Add controls
		map.addControl(new maplibregl.NavigationControl(), 'top-right');
		map.addControl(new maplibregl.ScaleControl(), 'bottom-right');

			// Removed redundant setTimeout - initialization is handled on the 'load' event

		// Handle click events
		map.on('click', (e) => {
			const tool = get(activeTool);
			if (tool === 'cross-section') {
				addCrossSectionPoint([e.lngLat.lng, e.lngLat.lat]);
				return;
			}

			dispatch('click', {
				lngLat: e.lngLat,
				point: e.point
			});
		});

		// Save map view on movement (debounced)
		map.on('moveend', saveMapView);
		map.on('zoomend', saveMapView);

		// Initialize once the style has loaded. Avoid relying on 'idle', which can
		// hang indefinitely if any source never finishes loading.
		// Subscribe immediately without waiting for map ready events
		logger.log('Setting up store subscriptions immediately');
		unsubscribeLayers = layers.subscribe((state) => {
			logger.debug('layers store changed:', state);
			if (styleReady) {
				applyLayerState(state);
			} else {
				logger.log(' Queuing layer update for when style is ready');
				updateQueue.push({ type: 'layers', data: state });
			}
		});

		unsubscribeWatersheds = watersheds.subscribe((state) => {
			if (styleReady) {
				updateWatershedsLayer(state);
			} else {
				updateQueue.push({ type: 'watersheds', data: state });
			}
		});

		unsubscribeCrossSection = crossSectionLine.subscribe((state) => {
			if (styleReady) {
				updateCrossSectionLayer(state);
			} else {
				updateQueue.push({ type: 'crossSection', data: state });
			}
		});

		unsubscribeOutlets = watershedOutlets.subscribe((state) => {
			if (styleReady) {
				updateOutletLayer(state);
			} else {
				updateQueue.push({ type: 'outlets', data: state });
			}
		});

		unsubscribeBasemap = basemapStyle.subscribe((style) => {
			if (styleReady) {
				updateBasemap(style);
			}
		});

		// Add diagnostic event logging
		map.on('style.load', () => {
			logger.log(' style.load event fired - style graph ready');

			// Add custom sources and layers to the loaded Stadia style
			addCustomSourcesAndLayers();

			styleReady = true;
			mapReady = true;
			processUpdateQueue();
			updateTileStatusForCenter();
		});

		map.on('styledata', () => {
			logger.log(' styledata event fired');
		});

		map.on('sourcedata', (e) => {
			logger.log(' sourcedata event fired for:', e.sourceId);
		});

		map.on('load', () => {
			logger.log(' load event fired - all initial sources loaded');
		});

		map.on('idle', () => {
			logger.log(' idle event fired - rendering complete');
		});

		// Process queued updates
		function processUpdateQueue() {
			logger.log(`Processing ${updateQueue.length} queued updates`);
			const queue = [...updateQueue];
			updateQueue = [];

			for (const update of queue) {
				switch (update.type) {
					case 'layers':
						applyLayerState(update.data);
						break;
					case 'watersheds':
						updateWatershedsLayer(update.data);
						break;
					case 'crossSection':
						updateCrossSectionLayer(update.data);
						break;
					case 'outlets':
						updateOutletLayer(update.data);
						break;
				}
			}
		}

			map.on('moveend', updateTileStatusForCenter);

			// Define cleanup now that map is initialized
			destroy = () => {
				map.off('moveend', updateTileStatusForCenter);
				unsubscribeLayers();
				unsubscribeWatersheds();
				unsubscribeCrossSection();
				unsubscribeOutlets();
				unsubscribeBasemap();
				map.remove();
				maplibregl.removeProtocol('pmtiles');
			};
		})();

		return () => {
			if (destroy) destroy();
		};
	});

	// Save current map view to store (debounced)
	function saveMapView() {
		clearTimeout(saveTimeout);
		saveTimeout = window.setTimeout(() => {
			const center = map.getCenter();
			mapView.set({
				center: [center.lng, center.lat],
				zoom: map.getZoom(),
				bearing: map.getBearing(),
				pitch: map.getPitch()
			});
		}, 500);
	}

	function buildLayersFromConfig(): any[] {
		const configuredLayers: any[] = [];

		// Build layers from LAYER_SOURCES configuration
		for (const layer of LAYER_SOURCES) {
			if (layer.id === 'fairfax-watersheds') {
				// Special handling for Fairfax watersheds with its 3 sub-layers
				configuredLayers.push(
					{
						id: 'fairfax-watersheds-fill',
						type: 'fill',
						source: 'fairfax-watersheds',
						'source-layer': 'fairfax_watersheds',
						layout: { visibility: 'none' },
						paint: {
							'fill-color': '#6b7280',
							'fill-opacity': 0.3
						}
					},
					{
						id: 'fairfax-watersheds-outline',
						type: 'line',
						source: 'fairfax-watersheds',
						'source-layer': 'fairfax_watersheds',
						layout: { visibility: 'none' },
						paint: {
							'line-color': '#374151',
							'line-width': 2,
							'line-opacity': 0.9
						}
					},
					{
						id: 'fairfax-watersheds-labels',
						type: 'symbol',
						source: 'fairfax-watersheds',
						'source-layer': 'fairfax_watersheds',
						minzoom: 11,
						layout: {
							visibility: 'none',
							'text-field': ['get', 'name'],
							'text-font': ['Noto Sans Regular'],
							'text-size': [
								'interpolate',
								['linear'],
								['zoom'],
								11, 12,
								14, 15,
								17, 18
							],
							'text-allow-overlap': false
						},
						paint: {
							'text-color': '#1f2937',
							'text-halo-color': '#ffffff',
							'text-halo-width': 2
						}
					}
				);
			} else if (layer.id === 'geology') {
				// Special handling for geology layer (fill type)
				configuredLayers.push(
					{
						id: 'geology-fill',
						type: 'fill',
						source: 'geology',
						'source-layer': 'geology',
						layout: { visibility: layer.defaultVisible ? 'visible' : 'none' },
						paint: {
							'fill-color': layer.paintProperties?.['fill-color'] || '#9ca3af',
							'fill-opacity': layer.paintProperties?.['fill-opacity'] || 0.6
,
							'fill-pattern': [
								'match',
								['get', 'rock_type'],
								'Metamorphic, schist', 'pattern-metamorphic-schist',
								'Metamorphic, sedimentary clastic', 'pattern-metamorphic-sedimentary-clastic',
								'Metamorphic, undifferentiated', 'pattern-metamorphic-undifferentiated',
								'Metamorphic, volcanic', 'pattern-metamorphic-volcanic',
								'Melange', 'pattern-melange',
								'Igneous, intrusive', 'pattern-igneous-intrusive',
								'Unconsolidated, undifferentiated', 'pattern-unconsolidated-undifferentiated',
								'Water', 'pattern-water',
								'pattern-other'  // fallback
							]
						}
					},
					{
						id: 'geology-outline',
						type: 'line',
						source: 'geology',
						'source-layer': 'geology',
						layout: { visibility: layer.defaultVisible ? 'visible' : 'none' },
						paint: {
							'line-color': layer.paintProperties?.['line-color'] || '#4b5563',
							'line-width': layer.paintProperties?.['line-width'] || 0.5,
							'line-opacity': layer.paintProperties?.['line-opacity'] || 0.8
						}
					}
				);
			} else if (layer.id === 'fairfax-water-polys') {
				// Special handling for fairfax-water-polys (polygon layer)
				configuredLayers.push({
					id: 'fairfax-water-polys',
					type: 'fill',
					source: 'fairfax-water-polys',
					'source-layer': 'fairfax_water_polys',
					layout: { visibility: layer.defaultVisible ? 'visible' : 'none' },
					paint: {
						'fill-color': layer.paintProperties?.['fill-color'] || '#0891b2',
						'fill-opacity': layer.paintProperties?.['fill-opacity'] || 0.6,
						'fill-outline-color': layer.paintProperties?.['fill-outline-color'] || '#075985'
					}
				});
			} else if (layer.id === 'inadequate-outfalls') {
				// Special handling for inadequate outfalls layer (fill + outline)
				configuredLayers.push(
					{
						id: 'inadequate-outfalls-fill',
						type: 'fill',
						source: 'inadequate-outfalls',
						'source-layer': 'inadequate_outfalls',
						layout: { visibility: layer.defaultVisible ? 'visible' : 'none' },
						paint: {
							'fill-pattern': layer.paintProperties?.['fill-pattern'],
							'fill-opacity': layer.paintProperties?.['fill-opacity'] || 0.6
						}
					},
					{
						id: 'inadequate-outfalls-outline',
						type: 'line',
						source: 'inadequate-outfalls',
						'source-layer': 'inadequate_outfalls',
						layout: { visibility: layer.defaultVisible ? 'visible' : 'none' },
						paint: {
							'line-color': layer.paintProperties?.['line-color'],
							'line-width': layer.paintProperties?.['line-width'] || 0.75,
							'line-opacity': layer.paintProperties?.['line-opacity'] || 0.8
						}
					}
				);
			} else {
				// Standard layer from configuration
				// Detect layer type from paint properties
				let layerType = 'line'; // default
				if (layer.type === 'raster') {
					layerType = 'raster';
				} else if (layer.type === 'vector' && layer.paintProperties) {
					// Check paint properties to determine vector layer type
					const paintKeys = Object.keys(layer.paintProperties);
					if (paintKeys.some(k => k.startsWith('circle-'))) {
						layerType = 'circle';
					} else if (paintKeys.some(k => k.startsWith('fill-'))) {
						layerType = 'fill';
					}
				}

				const mapLayer: any = {
					id: layer.id,
					type: layerType,
					source: layer.id,
					layout: {
						visibility: layer.defaultVisible ? 'visible' : 'none'
					}
				};

				// Add source-layer for vector layers
				if (layer.type === 'vector' && layer.vectorLayerId) {
					mapLayer['source-layer'] = layer.vectorLayerId;
				}

				// Add paint properties
				if (layer.paintProperties) {
					mapLayer.paint = layer.paintProperties;
				} else if (layer.type === 'raster') {
					mapLayer.paint = { 'raster-opacity': layer.defaultOpacity };
				}

				configuredLayers.push(mapLayer);
			}
		}

		return configuredLayers;
	}

	function addCustomSourcesAndLayers() {
		if (!map) return;

		// Add custom GeoJSON sources for watersheds, cross-sections, etc.
		map.addSource('watersheds', {
			type: 'geojson',
			data: { type: 'FeatureCollection', features: [] }
		});

		map.addSource('cross-section-line', {
			type: 'geojson',
			data: { type: 'FeatureCollection', features: [] }
		});

		map.addSource('watershed-outlets', {
			type: 'geojson',
			data: { type: 'FeatureCollection', features: [] }
		});

		// Add PMTiles sources for data layers
		for (const layer of LAYER_SOURCES) {
			map.addSource(layer.id, {
				type: layer.type,
				url: buildPmtilesUrl(layer.filename),
				...(layer.type === 'raster' ? { tileSize: layer.tileSize || 256 } : {})
			});
		}

		// Load geology patterns for colorblind accessibility
		// Load all 8 specific rock type patterns
		const geologyTypes: GeologyType[] = [
			'unconsolidated-undifferentiated',
			'metamorphic-schist',
			'metamorphic-sedimentary-clastic',
			'metamorphic-undifferentiated',
			'metamorphic-volcanic',
			'melange',
			'igneous-intrusive',
			'water'
		];

		for (const type of geologyTypes) {
			const color = geologyPatterns[type];
			const pattern = generatePattern(type, color);
			map.addImage(`pattern-${type}`, pattern);
		}

		// Load inadequate outfall patterns for colorblind accessibility
		const outfallTypes: OutfallDeterminationType[] = [
			'erosion',
			'vertical-erosion',
			'left-bank-unstable',
			'right-bank-unstable',
			'both-banks-unstable',
			'habitat-score'
		];

		for (const type of outfallTypes) {
			const color = outfallPatterns[type];
			const pattern = generateOutfallPattern(type, color);
			map.addImage(`pattern-outfall-${type}`, pattern);
		}

		// Add custom layers
		const customLayers = buildLayersFromConfig();
		for (const layer of customLayers) {
			map.addLayer(layer);
		}

		// Add watershed visualization layers
		map.addLayer({
			id: 'watersheds-fill',
			type: 'fill',
			source: 'watersheds',
			paint: {
				'fill-color': '#22c55e',
				'fill-opacity': 0.2
			}
		});

		map.addLayer({
			id: 'watersheds-outline',
			type: 'line',
			source: 'watersheds',
			paint: {
				'line-color': '#16a34a',
				'line-width': 2
			}
		});

		map.addLayer({
			id: 'watershed-outlets',
			type: 'circle',
			source: 'watershed-outlets',
			paint: {
				'circle-color': '#22c55e',
				'circle-radius': 6,
				'circle-stroke-width': 2,
				'circle-stroke-color': '#ffffff'
			}
		});

		map.addLayer({
			id: 'cross-section-points',
			type: 'circle',
			source: 'cross-section-line',
			paint: {
				'circle-color': '#ef4444',
				'circle-radius': 6,
				'circle-stroke-width': 2,
				'circle-stroke-color': '#ffffff'
			}
		});

		map.addLayer({
			id: 'cross-section-line',
			type: 'line',
			source: 'cross-section-line',
			paint: {
				'line-color': '#3b82f6',
				'line-width': 3
			}
		});

		logger.log('Custom sources and layers added to Stadia style');
	}

	function createMapStyle(): StyleSpecification {
    // Note: Layer visibility is handled by applyLayerState() reacting to the store.
    // Initialize layer visibilities to match store defaults to avoid flash of content.

		// Build sources from LAYER_SOURCES configuration
		const currentBasemap = get(basemapStyle);
		const sources: any = {
			// Dynamic basemap based on user selection
			'base-map': currentBasemap === 'light' ? BASEMAP_SOURCES.light : BASEMAP_SOURCES.vector,
			// Dynamic overlay sources (unchanged)
			watersheds: {
				type: 'geojson',
				data: {
					type: 'FeatureCollection',
					features: []
				}
			},
			'cross-section-line': {
				type: 'geojson',
				data: {
					type: 'FeatureCollection',
					features: []
				}
			},
			'watershed-outlets': {
				type: 'geojson',
				data: {
					type: 'FeatureCollection',
					features: []
				}
			}
		};

		// Add layer sources from configuration
		for (const layer of LAYER_SOURCES) {
			sources[layer.id] = {
				type: layer.type,
				url: buildPmtilesUrl(layer.filename),
				...(layer.type === 'raster' ? { tileSize: layer.tileSize || 256 } : {})
			};
		}

		return {
			version: 8 as 8,
			glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
			sources,
			layers: [
				// Basemap layer (visibility based on user selection)
				{
					id: 'basemap',
					type: 'raster',
					source: 'base-map',
					layout: { visibility: currentBasemap === 'none' ? 'none' : 'visible' }
				},
				// Data layers from configuration
				...buildLayersFromConfig(),
				// Dynamic overlay layers (unchanged)
				{
					id: 'watersheds-fill',
					type: 'fill',
					source: 'watersheds',
					paint: {
						'fill-color': '#22c55e',
						'fill-opacity': 0.2
					}
				},
				{
					id: 'watersheds-outline',
					type: 'line',
					source: 'watersheds',
					paint: {
						'line-color': '#16a34a',
						'line-width': 2
					}
				},
				{
					id: 'watershed-outlets',
					type: 'circle',
					source: 'watershed-outlets',
					paint: {
						'circle-color': '#22c55e',
						'circle-radius': 6,
						'circle-stroke-width': 2,
						'circle-stroke-color': '#ffffff'
					}
				},
				{
					id: 'cross-section-line',
					type: 'line',
					source: 'cross-section-line',
					paint: {
						'line-color': '#f97316',
						'line-width': 3
					}
				},
				{
					id: 'cross-section-points',
					type: 'circle',
					source: 'cross-section-line',
					filter: ['==', ['geometry-type'], 'Point'],
					paint: {
						'circle-color': '#fb923c',
						'circle-radius': 5,
						'circle-stroke-width': 1,
						'circle-stroke-color': '#ffffff'
					}
				}
			]
		};
	}

	// Safe layer applier with retries
	function applyLayerState(layersState: any, retryCount = 0) {
		logger.log('[applyLayerState] Called with state:', layersState);

		if (!map) {
			logger.warn('[applyLayerState] Map instance not available');
			return;
		}

		const pendingLayers: string[] = [];

		Object.entries(layersState).forEach(([layerId, config]: [string, any]) => {
			// Skip fairfax-watersheds-fill and fairfax-watersheds-labels - they're controlled by fairfax-watersheds-outline
			if (layerId === 'fairfax-watersheds-fill' || layerId === 'fairfax-watersheds-labels') {
				return;
			}
			// Skip geology-fill and geology-outline as they're controlled by 'geology'
			if (layerId === 'geology-fill' || layerId === 'geology-outline') {
				return;
			}
			// Skip inadequate-outfalls-fill and inadequate-outfalls-outline as they're controlled by 'inadequate-outfalls'
			if (layerId === 'inadequate-outfalls-fill' || layerId === 'inadequate-outfalls-outline') {
				return;
			}

			// Special handling for logical layer groups
			if (layerId === 'geology') {
				const newVisibility = config.visible ? 'visible' : 'none';
				logger.log(`[applyLayerState] Setting geology layers visibility to ${newVisibility}`);

				const geologyFill = map.getLayer('geology-fill');
				const geologyOutline = map.getLayer('geology-outline');

				if (geologyFill) {
					map.setLayoutProperty('geology-fill', 'visibility', newVisibility);
					// Apply opacity to fill
					if (config.visible && config.opacity !== undefined) {
						map.setPaintProperty('geology-fill', 'fill-opacity', config.opacity * 0.6);
					}
				} else {
					pendingLayers.push(layerId);
				}
				if (geologyOutline) {
					map.setLayoutProperty('geology-outline', 'visibility', newVisibility);
				}
				return;
			}

			if (layerId === 'inadequate-outfalls') {
				const newVisibility = config.visible ? 'visible' : 'none';
				logger.log(`[applyLayerState] Setting inadequate outfalls layers visibility to ${newVisibility}`);

				const outfallsFill = map.getLayer('inadequate-outfalls-fill');
				const outfallsOutline = map.getLayer('inadequate-outfalls-outline');

				if (outfallsFill) {
					map.setLayoutProperty('inadequate-outfalls-fill', 'visibility', newVisibility);
					// Apply opacity to fill
					if (config.visible && config.opacity !== undefined) {
						map.setPaintProperty('inadequate-outfalls-fill', 'fill-opacity', config.opacity);
					}
				} else {
					pendingLayers.push(layerId);
				}
				if (outfallsOutline) {
					map.setLayoutProperty('inadequate-outfalls-outline', 'visibility', newVisibility);
					// Apply opacity to outline
					if (config.visible && config.opacity !== undefined) {
						map.setPaintProperty('inadequate-outfalls-outline', 'line-opacity', config.opacity * 0.8);
					}
				}
				return;
			}

			if (layerId === 'fairfax-watersheds') {
				const newVisibility = config.visible ? 'visible' : 'none';
				logger.log(`[applyLayerState] Setting Fairfax watersheds layers visibility to ${newVisibility}`);

				const watershedsFill = map.getLayer('fairfax-watersheds-fill');
				const watershedsOutline = map.getLayer('fairfax-watersheds-outline');
				const watershedsLabels = map.getLayer('fairfax-watersheds-labels');

				if (watershedsOutline) {
					map.setLayoutProperty('fairfax-watersheds-outline', 'visibility', newVisibility);
				} else {
					pendingLayers.push(layerId);
				}
				if (watershedsFill) {
					map.setLayoutProperty('fairfax-watersheds-fill', 'visibility', newVisibility);
				}
				if (watershedsLabels) {
					map.setLayoutProperty('fairfax-watersheds-labels', 'visibility', newVisibility);
				}
				return;
			}

			// Standard layer handling
			const layer = map.getLayer(layerId);
			if (layer) {
				const newVisibility = config.visible ? 'visible' : 'none';
				logger.log(`[applyLayerState] Setting ${layerId} visibility to ${newVisibility}`);

				try {
					// Update opacity for raster layers first to ensure immediate visual change
					if (layer.type === 'raster') {
						const targetOpacity = config.visible ? (config.opacity ?? 1.0) : 0;
						logger.log(`[applyLayerState] Setting ${layerId} opacity to ${targetOpacity}`);
						map.setPaintProperty(layerId, 'raster-opacity', targetOpacity);
					}

					// Update opacity for vector layers
					if (layer.type === 'fill') {
						const targetOpacity = config.visible ? (config.opacity ?? 1.0) : 0;
						logger.log(`[applyLayerState] Setting ${layerId} fill-opacity to ${targetOpacity}`);
						map.setPaintProperty(layerId, 'fill-opacity', targetOpacity);
					}

					if (layer.type === 'line') {
						const targetOpacity = config.visible ? (config.opacity ?? 1.0) : 0;
						logger.log(`[applyLayerState] Setting ${layerId} line-opacity to ${targetOpacity}`);
						map.setPaintProperty(layerId, 'line-opacity', targetOpacity);
					}

					if (layer.type === 'circle') {
						const targetOpacity = config.visible ? (config.opacity ?? 1.0) : 0;
						logger.log(`[applyLayerState] Setting ${layerId} circle-opacity to ${targetOpacity}`);
						map.setPaintProperty(layerId, 'circle-opacity', targetOpacity);
					}

					map.setLayoutProperty(layerId, 'visibility', newVisibility);

					// Special handling: sync Fairfax watersheds fill and labels with outline visibility
					if (layerId === 'fairfax-watersheds-outline') {
						const watershedsFill = map.getLayer('fairfax-watersheds-fill');
						const watershedsLabels = map.getLayer('fairfax-watersheds-labels');

						if (watershedsFill) {
							logger.log(`[applyLayerState] Syncing fairfax-watersheds-fill visibility to ${newVisibility}`);
							map.setLayoutProperty('fairfax-watersheds-fill', 'visibility', newVisibility);
						}
						if (watershedsLabels) {
							logger.log(`[applyLayerState] Syncing fairfax-watersheds-labels visibility to ${newVisibility}`);
							map.setLayoutProperty('fairfax-watersheds-labels', 'visibility', newVisibility);
						}
					}

				} catch (error) {
					logger.error(`[applyLayerState] Error updating layer ${layerId}:`, error);
				}
			} else {
				// Layer not yet available, track for retry
				logger.log(`[applyLayerState] Layer ${layerId} not found, will retry`);
				pendingLayers.push(layerId);
			}
		});

		// Retry for layers that don't exist yet (up to 30 attempts = 3 seconds)
		if (pendingLayers.length > 0 && retryCount < 30) {
			logger.log(`[applyLayerState] Retrying ${pendingLayers.length} layers in 100ms (attempt ${retryCount + 1}/30)`);
			setTimeout(() => {
				// Only retry the pending layers
				const pendingState: any = {};
				pendingLayers.forEach(id => {
					pendingState[id] = layersState[id];
				});
				applyLayerState(pendingState, retryCount + 1);
			}, 100);
		} else if (pendingLayers.length > 0) {
			logger.warn(`[applyLayerState] Gave up on layers after 30 attempts:`, pendingLayers);
		}
	}

	// Legacy function for compatibility - redirects to applyLayerState
	function updateLayers(layersState: any) {
		applyLayerState(layersState);
	}

function updateWatershedsLayer(watershedsData: any[]) {
	if (!mapReady || !map) return;

	const source = map.getSource('watersheds') as maplibregl.GeoJSONSource;
	if (!source) return;

		source.setData({
			type: 'FeatureCollection',
			features: watershedsData
		});
}

function updateOutletLayer(outlets: any[]) {
	if (!mapReady || !map) return;

	const source = map.getSource('watershed-outlets') as maplibregl.GeoJSONSource;
	if (!source) return;

	source.setData({
		type: 'FeatureCollection',
		features: outlets
	});
}

function updateBasemap(style: BasemapStyle) {
	if (!mapReady || !map) return;

	logger.log(`Switching basemap to: ${style}`);

	// Preserve current view state
	const center = map.getCenter();
	const zoom = map.getZoom();
	const bearing = map.getBearing();
	const pitch = map.getPitch();

	// Determine new style
	let newStyle: string | StyleSpecification;

	if (style === 'none') {
		// Use custom minimal style
		newStyle = createMapStyle();
	} else {
		// Load Stadia Maps style URL
		newStyle = style === 'light' ? BASEMAP_STYLE_URLS.light : BASEMAP_STYLE_URLS.detailed;
	}

	// Switch style and restore view
	map.setStyle(newStyle);

	// Re-add custom sources and layers after style loads
	map.once('style.load', () => {
		logger.log('Basemap style loaded, re-adding custom layers');
		addCustomSourcesAndLayers();

		// Restore view state
		map.setCenter(center);
		map.setZoom(zoom);
		map.setBearing(bearing);
		map.setPitch(pitch);

		// Reapply current layer states
		applyLayerState($layers);
	});
}

async function initializeTileStatus() {
	if (tileStatusInitialized || typeof window === 'undefined') {
		return;
	}
	tileStatusInitialized = true;
	tileStatus.set(tileSources.map((src) => ({ id: src.id, label: src.label, available: false, message: 'Checking…' })));

	await Promise.all(tileSources.map(async (src) => {
		const absoluteUrl = buildTileHttpUrl(src.filename);

		try {
			const headResponse = await fetch(absoluteUrl, { method: 'HEAD', cache: 'no-store' });
			if (!headResponse.ok) {
				tileMetadata.set(src.id, { url: absoluteUrl, error: `HTTP ${headResponse.status}` });
				return;
			}
		}
		catch (error) {
			tileMetadata.set(src.id, { url: absoluteUrl, error: 'Not reachable (is the backend serving /tiles?)' });
			return;
		}

		try {
			const pmtiles = new PMTiles(absoluteUrl);
			const header = await pmtiles.getHeader();
			const bounds = headerToBounds(header);
			tileMetadata.set(src.id, {
				url: absoluteUrl,
				header: bounds,
				minZoom: typeof header.minZoom === 'number' ? header.minZoom : undefined,
				maxZoom: typeof header.maxZoom === 'number' ? header.maxZoom : undefined
			});
			pmtilesProtocol?.add(pmtiles);

			// Verify vector layer metadata for vector tiles
			if (src.id === 'contours' || src.id === 'fairfax-watersheds') {
				try {
					const metadata: any = await pmtiles.getMetadata();
					if (metadata && metadata.vector_layers) {
						const layerNames = metadata.vector_layers.map((layer: any) => layer.id);
						const expectedLayer = src.id; // Expected source-layer name

						if (!layerNames.includes(expectedLayer)) {
							logger.warn(`[PMTiles] Vector layer mismatch for ${src.id}.pmtiles:
								Expected source-layer: "${expectedLayer}"
								Available layers: ${layerNames.join(', ')}
								Update your style's source-layer references to match.`);
						} else {
							logger.log(`[PMTiles] Vector layer verified for ${src.id}: "${expectedLayer}" found`);
						}
					}
				} catch (metaError) {
					logger.log(`[PMTiles] Could not verify vector layers for ${src.id}:`, metaError);
				}
			}
		} catch (error) {
			tileMetadata.set(src.id, {
				url: absoluteUrl,
				header: undefined,
				error: undefined
			});
		}
	}));

	updateTileStatusForCenter();
}

function updateTileStatusForCenter() {
	if (!map || !tileStatusInitialized) {
		return;
	}

	const center = map.getCenter();
	const currentZoom = map.getZoom();
	const statuses = tileSources.map((src) => {
		const meta = tileMetadata.get(src.id);
		if (!meta) {
			return { id: src.id, label: src.label, available: false, message: 'Checking…' };
		}

		if (meta.error) {
			const fallback = meta.error === 'HTTP 404'
				? 'File not found. Regenerate tiles or copy them into data/tiles/. '
				: meta.error;
			return { id: src.id, label: src.label, available: false, message: fallback };
		}

		if (!meta.header) {
			return {
				id: src.id,
				label: src.label,
				available: true,
				message: 'File reachable (coverage unknown – metadata missing)'
			};
		}

		const within =
			center.lng >= meta.header.minLon &&
			center.lng <= meta.header.maxLon &&
			center.lat >= meta.header.minLat &&
			center.lat <= meta.header.maxLat;

		const nativeMaxZoom = meta.maxZoom;
		const roundedMaxZoom = nativeMaxZoom !== undefined ? Math.round(nativeMaxZoom) : undefined;
		const overzoom = nativeMaxZoom !== undefined && currentZoom > nativeMaxZoom + 0.05;
		const zoomLabel = roundedMaxZoom !== undefined ? `native max z${roundedMaxZoom}` : 'native max unknown';

		if (!within) {
			return {
				id: src.id,
				label: src.label,
				available: false,
				message: `No coverage at ${center.lat.toFixed(3)}, ${center.lng.toFixed(3)} (${zoomLabel})`
			};
		}

		if (overzoom) {
			return {
				id: src.id,
				label: src.label,
				available: false,
				message: `Overzooming past ${zoomLabel}; current z${currentZoom.toFixed(1)}`
			};
		}

		return {
			id: src.id,
			label: src.label,
			available: true,
			message: roundedMaxZoom !== undefined
				? `Available in current view (${zoomLabel})`
				: 'Available in current view'
		};
	});

	tileStatus.set(statuses);
}

function updateCrossSectionLayer(points: [number, number][]) {
	if (!mapReady || !map) return;

		const source = map.getSource('cross-section-line') as maplibregl.GeoJSONSource;
		if (!source) return;

		const features: any[] = [];

		if (points.length >= 2) {
			features.push({
				type: 'Feature',
				geometry: {
					type: 'LineString',
					coordinates: points
				},
				properties: {}
			});
		}

		points.forEach(([lon, lat], index) => {
			features.push({
				type: 'Feature',
				geometry: {
					type: 'Point',
					coordinates: [lon, lat]
				},
				properties: { index }
			});
		});

		source.setData({
			type: 'FeatureCollection',
			features
		});
	}

	function addCrossSectionPoint(coord: [number, number]) {
		crossSectionLine.update((points) => {
			const next = [...points, coord];
			crossSection.set(null);
			return next;
		});
	}

	// Fly to a location with smooth animation
	export function flyToLocation(center: [number, number], zoom?: number, name?: string) {
		if (!map) return;

		map.flyTo({
			center,
			zoom: zoom || 13,
			speed: 1.2,
			curve: 1.4,
			essential: true
		});

		// Remove existing marker
		if (searchMarker) {
			searchMarker.remove();
		}

		// Add marker at searched location
		if (name) {
			const el = document.createElement('div');
			el.className = 'search-marker';
			el.style.backgroundImage = 'url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iI2VmNDQ0NCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIgMkM4LjEzIDIgNSA1LjEzIDUgOWMwIDUuMjUgNyAxMyA3IDEzczctNy43NSA3LTEzYzAtMy44Ny0zLjEzLTctNy03em0wIDkuNWMtMS4zOCAwLTIuNS0xLjEyLTIuNS0yLjVzMS4xMi0yLjUgMi41LTIuNSAyLjUgMS4xMiAyLjUgMi41LTEuMTIgMi41LTIuNSAyLjV6Ii8+PC9zdmc+)';
			el.style.width = '32px';
			el.style.height = '32px';
			el.style.backgroundSize = 'contain';
			el.style.cursor = 'pointer';

			searchMarker = new maplibregl.Marker({ element: el })
				.setLngLat(center)
				.addTo(map);
		}
	}

export async function delineateWatershed(lngLat: { lng: number; lat: number }) {
	try {
		const settings = get(delineationSettings);
		const result = await apiPost('/api/delineate', {
			lat: lngLat.lat,
			lon: lngLat.lng,
			snap_to_stream: settings.snapToStream,
			snap_radius: settings.snapRadius
		});

		// Add watershed to map
		const nextWatersheds = [...get(watersheds), result.watershed];
		watersheds.set(nextWatersheds);
		latestDelineation.set(result);

		const nextOutlets = [...get(watershedOutlets), result.pour_point];
		watershedOutlets.set(nextOutlets);

		// Fit map to watershed bounds
		const bounds = new maplibregl.LngLatBounds();
		const geom = result.watershed.geometry;

			// Handle both Polygon and MultiPolygon
			if (geom.type === 'Polygon') {
				geom.coordinates.forEach((ring: [number, number][]) => {
					ring.forEach((coord: [number, number]) => {
						bounds.extend(coord);
					});
				});
			} else if (geom.type === 'MultiPolygon') {
				geom.coordinates.forEach((polygon: [number, number][][]) => {
					polygon.forEach((ring: [number, number][]) => {
						ring.forEach((coord: [number, number]) => {
							bounds.extend(coord);
						});
					});
				});
			}

			map.fitBounds(bounds, { padding: 50 });

			return result;
		} catch (error) {
			logger.error('Watershed delineation error:', error);
			alert('Failed to delineate watershed. Check backend is running and data is prepared.');
		}
	}

export function clearWatersheds() {
	watersheds.set([]);
	watershedOutlets.set([]);
	latestDelineation.set(null);
}
</script>

<div bind:this={mapContainer} class="map"></div>

<style>
	.map {
		width: 100%;
		height: 100%;
	}

	:global(.maplibregl-popup-content) {
		padding: 12px;
		border-radius: 8px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}
</style>
