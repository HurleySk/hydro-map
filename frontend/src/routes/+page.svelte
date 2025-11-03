<script lang="ts">
	import Map from '$lib/components/Map.svelte';
	import LayerPanel from '$lib/components/LayerPanel.svelte';
	import LocationSearch from '$lib/components/LocationSearch.svelte';
	import BaseMapToggle from '$lib/components/BaseMapToggle.svelte';
import WatershedTool from '$lib/components/WatershedTool.svelte';
import CrossSectionTool from '$lib/components/CrossSectionTool.svelte';
import FeatureInfo from '$lib/components/FeatureInfo.svelte';
import FeatureInfoTool from '$lib/components/FeatureInfoTool.svelte';
import TileStatusPanel from '$lib/components/TileStatusPanel.svelte';
import CollapsiblePanel from '$lib/components/CollapsiblePanel.svelte';
import GeologyLegend from '$lib/components/GeologyLegend.svelte';
import TWILegend from '$lib/components/TWILegend.svelte';
	import { activeTool, panelStates, layers } from '$lib/stores';

	let mapComponent: any;
	let selectedFeature: any = null;
	let featureInfoBuffer = 10; // Default buffer for feature info queries

	function handleMapClick(event: CustomEvent) {
		const { lngLat, point } = event.detail;

		if ($activeTool === 'delineate') {
			// Handle watershed delineation
			mapComponent.delineateWatershed(lngLat);
		} else if ($activeTool === 'info') {
			// Handle feature info query
			selectedFeature = { lngLat };
		}
	}

	function handleLocationSelect(event: CustomEvent) {
		const { center, zoom, name } = event.detail;
		if (mapComponent) {
			mapComponent.flyToLocation(center, zoom, name);
		}
	}
</script>

<svelte:head>
	<title>Hydro-Map - Hydrological & Geological Exploration</title>
</svelte:head>

<div class="app">
	<header>
		<h1>Hydro-Map</h1>
		<p>Explore hydrological and geological features</p>
	</header>

	<main>
		<Map
			bind:this={mapComponent}
			on:click={handleMapClick}
		/>

		<aside class="controls">
			<LocationSearch on:select={handleLocationSelect} />

			<BaseMapToggle />

			<CollapsiblePanel
				title="Map Layers"
				icon="📚"
				expanded={$panelStates.mapLayers}
				storageKey="map-layers"
			>
				<LayerPanel />
			</CollapsiblePanel>

			<CollapsiblePanel
				title="Analysis Tools"
				icon="🔧"
				expanded={$panelStates.analysisTools}
				storageKey="analysis-tools"
			>
				<div class="tools-group">
					<FeatureInfoTool bind:bufferRadius={featureInfoBuffer} />
					<WatershedTool />
					<CrossSectionTool />
				</div>
			</CollapsiblePanel>

			<CollapsiblePanel
				title="System Status"
				icon="ℹ️"
				expanded={$panelStates.systemStatus}
				storageKey="system-status"
			>
				<TileStatusPanel />
			</CollapsiblePanel>
		</aside>

		{#if selectedFeature}
			<FeatureInfo
				location={selectedFeature.lngLat}
				buffer={featureInfoBuffer}
				on:close={() => {
					selectedFeature = null;
					activeTool.set('none');
				}}
			/>
		{/if}

		{#if $layers['twi']?.visible}
			<TWILegend opacity={$layers['twi'].opacity} />
		{/if}

		{#if $layers['geology']?.visible}
			<GeologyLegend opacity={$layers['geology'].opacity} />
		{/if}
	</main>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
		overflow: hidden;
	}

	.app {
		display: flex;
		flex-direction: column;
		height: 100vh;
		width: 100vw;
	}

	header {
		background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
		color: white;
		padding: 1rem 1.5rem;
		box-shadow: 0 2px 4px rgba(0,0,0,0.1);
		z-index: 10;
	}

	header h1 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
	}

	header p {
		margin: 0.25rem 0 0 0;
		font-size: 0.875rem;
		opacity: 0.9;
	}

	main {
		flex: 1;
		position: relative;
		overflow: hidden;
	}

	.controls {
		position: absolute;
		top: 1rem;
		left: 1rem;
		bottom: 1rem;
		z-index: 5;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-height: calc(100vh - 6rem);
		overflow-y: auto;
		overflow-x: hidden;
		padding-right: 0.5rem;
		min-width: 250px;
		max-width: 350px;
	}

	.controls::-webkit-scrollbar {
		width: 6px;
	}

	.controls::-webkit-scrollbar-track {
		background: transparent;
	}

	.controls::-webkit-scrollbar-thumb {
		background: #cbd5e1;
		border-radius: 3px;
	}

	.tools-group {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
</style>
