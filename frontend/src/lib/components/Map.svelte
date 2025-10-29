<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { Protocol } from 'pmtiles';
	import { layers, watersheds } from '$lib/stores';

	const dispatch = createEventDispatcher();

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map;

	// Default center (adjust to your area of interest)
	const DEFAULT_CENTER: [number, number] = [-122.4194, 37.7749]; // San Francisco
	const DEFAULT_ZOOM = 11;

	onMount(() => {
		// Register PMTiles protocol
		const protocol = new Protocol();
		maplibregl.addProtocol('pmtiles', protocol.tile);

		// Initialize map
		map = new maplibregl.Map({
			container: mapContainer,
			style: createMapStyle(),
			center: DEFAULT_CENTER,
			zoom: DEFAULT_ZOOM,
			maxZoom: 16,
			minZoom: 8
		});

		// Add controls
		map.addControl(new maplibregl.NavigationControl(), 'top-right');
		map.addControl(new maplibregl.ScaleControl(), 'bottom-right');

		// Handle click events
		map.on('click', (e) => {
			dispatch('click', {
				lngLat: e.lngLat,
				point: e.point
			});
		});

		// Update layers when store changes
		layers.subscribe(updateLayers);

		return () => {
			map.remove();
			maplibregl.removeProtocol('pmtiles');
		};
	});

	function createMapStyle() {
		return {
			version: 8,
			sources: {
				'base-map': {
					type: 'raster',
					tiles: [
						'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
					],
					tileSize: 256,
					attribution: '© OpenStreetMap contributors'
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
				}
			},
			layers: [
				{
					id: 'base',
					type: 'raster',
					source: 'base-map',
					layout: { visibility: 'visible' }
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

	export async function delineateWatershed(lngLat: { lng: number; lat: number }) {
		try {
			const response = await fetch('/api/delineate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					lat: lngLat.lat,
					lon: lngLat.lng,
					snap_to_stream: true
				})
			});

			if (!response.ok) {
				throw new Error('Delineation failed');
			}

			const result = await response.json();

			// Add watershed to map
			const source = map.getSource('watersheds') as maplibregl.GeoJSONSource;
			if (source) {
				watersheds.update(w => [...w, result.watershed]);

				source.setData({
					type: 'FeatureCollection',
					features: [...$watersheds]
				});

				// Fit map to watershed bounds
				const bounds = new maplibregl.LngLatBounds();
				result.watershed.geometry.coordinates[0].forEach((coord: [number, number]) => {
					bounds.extend(coord);
				});
				map.fitBounds(bounds, { padding: 50 });
			}

			return result;
		} catch (error) {
			console.error('Watershed delineation error:', error);
			alert('Failed to delineate watershed. Check backend is running and data is prepared.');
		}
	}

	export function clearWatersheds() {
		watersheds.set([]);
		const source = map.getSource('watersheds') as maplibregl.GeoJSONSource;
		if (source) {
			source.setData({
				type: 'FeatureCollection',
				features: []
			});
		}
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
