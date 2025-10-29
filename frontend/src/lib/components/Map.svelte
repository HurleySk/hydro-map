<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { get } from 'svelte/store';
	import maplibregl from 'maplibre-gl';
	import type { StyleSpecification } from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { Protocol } from 'pmtiles';
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
	basemapStyle
} from '$lib/stores';

	const dispatch = createEventDispatcher();

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map;
	let saveTimeout: number;
	let searchMarker: maplibregl.Marker | null = null;
let unsubscribeLayers: () => void = () => {};
let unsubscribeWatersheds: () => void = () => {};
let unsubscribeCrossSection: () => void = () => {};
let unsubscribeOutlets: () => void = () => {};
let unsubscribeBasemap: () => void = () => {};

	// Default center (adjusted to Mason District Park, Annandale, VA)
	const DEFAULT_CENTER: [number, number] = [-77.204, 38.836];
	const DEFAULT_ZOOM = 14;

	onMount(() => {
		// Register PMTiles protocol
		const protocol = new Protocol();
		maplibregl.addProtocol('pmtiles', protocol.tile);

		// Get saved view or use defaults
		const savedView = $mapView;
		const initialCenter = savedView?.center || DEFAULT_CENTER;
		const initialZoom = savedView?.zoom || DEFAULT_ZOOM;

		// Initialize map
		map = new maplibregl.Map({
			container: mapContainer,
			style: createMapStyle(),
			center: initialCenter,
			zoom: initialZoom,
			bearing: savedView?.bearing || 0,
			pitch: savedView?.pitch || 0,
			maxZoom: 16,
			minZoom: 8
		});

		// Add controls
		map.addControl(new maplibregl.NavigationControl(), 'top-right');
		map.addControl(new maplibregl.ScaleControl(), 'bottom-right');

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

		// Update layers when store changes
		unsubscribeLayers = layers.subscribe(updateLayers);

		// Update watersheds layer when store changes
		unsubscribeWatersheds = watersheds.subscribe(updateWatershedsLayer);

		// Update cross-section layer when store changes
		unsubscribeCrossSection = crossSectionLine.subscribe(updateCrossSectionLayer);

		// Update outlets layer when store changes
		unsubscribeOutlets = watershedOutlets.subscribe(updateOutletLayer);

		// Update basemap selection
		unsubscribeBasemap = basemapStyle.subscribe(updateBasemap);

		// Refresh rendered data once style is loaded
		map.on('load', () => {
			updateLayers(get(layers));
			updateWatershedsLayer(get(watersheds));
			updateCrossSectionLayer(get(crossSectionLine));
			updateOutletLayer(get(watershedOutlets));
			updateBasemap(get(basemapStyle));
		});

		return () => {
			unsubscribeLayers();
			unsubscribeWatersheds();
			unsubscribeCrossSection();
			unsubscribeOutlets();
			unsubscribeBasemap();
			map.remove();
			maplibregl.removeProtocol('pmtiles');
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

	function createMapStyle(): StyleSpecification {
		return {
			version: 8 as 8,
			sources: {
				'base-map-osm': {
					type: 'raster',
					tiles: [
						'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
					],
					tileSize: 256,
					attribution: '© OpenStreetMap contributors'
				},
				'base-map-light': {
					type: 'raster',
					tiles: [
						'https://tile.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
					],
					tileSize: 256,
					attribution: '© OpenStreetMap contributors, © CARTO'
				},
				hillshade: {
					type: 'raster',
					url: 'pmtiles:///tiles/hillshade.pmtiles'
				},
				slope: {
					type: 'raster',
					url: 'pmtiles:///tiles/slope.pmtiles'
				},
				aspect: {
					type: 'raster',
					url: 'pmtiles:///tiles/aspect.pmtiles'
				},
				streams: {
					type: 'vector',
					url: 'pmtiles:///tiles/streams.pmtiles'
				},
				geology: {
					type: 'vector',
					url: 'pmtiles:///tiles/geology.pmtiles'
				},
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
				},
				contours: {
					type: 'vector',
					url: 'pmtiles:///tiles/contours.pmtiles'
				}
			},
			layers: [
				{
					id: 'base-osm',
					type: 'raster',
					source: 'base-map-osm',
					layout: { visibility: 'visible' }
				},
				{
					id: 'base-light',
					type: 'raster',
					source: 'base-map-light',
					layout: { visibility: 'none' }
				},
				{
					id: 'hillshade',
					type: 'raster',
					source: 'hillshade',
					layout: { visibility: 'visible' },
					paint: { 'raster-opacity': 0.6 }
				},
				{
					id: 'slope',
					type: 'raster',
					source: 'slope',
					layout: { visibility: 'none' },
					paint: { 'raster-opacity': 0.7 }
				},
				{
					id: 'aspect',
					type: 'raster',
					source: 'aspect',
					layout: { visibility: 'none' },
					paint: { 'raster-opacity': 0.7 }
				},
				{
					id: 'geology',
					type: 'fill',
					source: 'geology',
					'source-layer': 'geology',
					layout: { visibility: 'none' },
					paint: {
						'fill-color': ['get', 'color'],
						'fill-opacity': 0.6
					}
				},
				{
					id: 'geology-outline',
					type: 'line',
					source: 'geology',
					'source-layer': 'geology',
					layout: { visibility: 'none' },
					paint: {
						'line-color': '#333',
						'line-width': 1
					}
				},
				{
					id: 'streams',
					type: 'line',
					source: 'streams',
					'source-layer': 'streams',
					layout: { visibility: 'visible' },
					paint: {
						'line-color': '#3b82f6',
						'line-width': [
							'interpolate',
							['linear'],
							['zoom'],
							8, 1,
							14, 3
						]
					}
				},
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
					id: 'contours',
					type: 'line',
					source: 'contours',
					'source-layer': 'contours',
					layout: { visibility: 'none' },
					paint: {
						'line-color': '#1f2937',
						'line-width': 1,
						'line-opacity': 0.6
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

	function updateLayers(layersState: any) {
		if (!map || !map.isStyleLoaded()) return;

		Object.entries(layersState).forEach(([layerId, config]: [string, any]) => {
			if (map.getLayer(layerId)) {
				map.setLayoutProperty(
					layerId,
					'visibility',
					config.visible ? 'visible' : 'none'
				);

				// Update opacity for raster layers
				if (map.getLayer(layerId)?.type === 'raster') {
					map.setPaintProperty(layerId, 'raster-opacity', config.opacity);
				}
			}
		});
	}

function updateWatershedsLayer(watershedsData: any[]) {
	if (!map || !map.isStyleLoaded()) return;

	const source = map.getSource('watersheds') as maplibregl.GeoJSONSource;
	if (!source) return;

		source.setData({
			type: 'FeatureCollection',
			features: watershedsData
		});
}

function updateOutletLayer(outlets: any[]) {
	if (!map || !map.isStyleLoaded()) return;

	const source = map.getSource('watershed-outlets') as maplibregl.GeoJSONSource;
	if (!source) return;

	source.setData({
		type: 'FeatureCollection',
		features: outlets
	});
}

function updateBasemap(style: 'osm' | 'light') {
	if (!map || !map.isStyleLoaded()) return;

	if (map.getLayer('base-osm')) {
		map.setLayoutProperty('base-osm', 'visibility', style === 'osm' ? 'visible' : 'none');
	}
	if (map.getLayer('base-light')) {
		map.setLayoutProperty('base-light', 'visibility', style === 'light' ? 'visible' : 'none');
	}
}

function updateCrossSectionLayer(points: [number, number][]) {
	if (!map || !map.isStyleLoaded()) return;

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
		const response = await fetch('/api/delineate', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				lat: lngLat.lat,
				lon: lngLat.lng,
				snap_to_stream: settings.snapToStream,
				snap_radius: settings.snapRadius
			})
		});

			if (!response.ok) {
				throw new Error('Delineation failed');
			}

		const result = await response.json();

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
			console.error('Watershed delineation error:', error);
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
