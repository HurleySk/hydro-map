<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';

	export let location: { lng: number; lat: number };

	const dispatch = createEventDispatcher();

	let features: any = null;
	let loading = true;
	let error = false;
	const controller = new AbortController();

	onMount(async () => {
		try {
			const response = await fetch('/api/feature-info', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					lat: location.lat,
					lon: location.lng,
					buffer: 10  // Precise buffer for accurate click detection
				}),
				signal: controller.signal
			});

			if (!response.ok) {
				throw new Error('Failed to fetch feature info');
			}

			const result = await response.json();
			features = result.features;
			loading = false;
		} catch (err: any) {
			if (err?.name === 'AbortError') {
				return;
			}
			console.error('Feature info error:', err);
			error = true;
			loading = false;
		}
	});

	function close() {
		dispatch('close');
	}

	onDestroy(() => {
		controller.abort();
	});
</script>

<div class="feature-info">
	<div class="header">
		<h3>Feature Information</h3>
		<button class="close-button" on:click={close}>×</button>
	</div>

	<div class="location">
		<strong>Location:</strong><br/>
		{location.lat.toFixed(5)}, {location.lng.toFixed(5)}
	</div>

	{#if loading}
		<div class="loading">Loading...</div>
	{:else if error}
		<div class="error">Failed to load feature information</div>
	{:else if features && Object.keys(features).length > 0}
		{#if features.streams}
			<div class="feature-group">
				<h4>Streams</h4>
				{#each features.streams as stream}
					<div class="feature-item">
						{#if stream.name}
							<div class="feature-name">{stream.name}</div>
						{:else}
							<div class="feature-name">Unnamed Stream</div>
						{/if}

						{#if stream.distance_meters !== undefined}
							<div class="feature-distance">Distance: {stream.distance_meters}m</div>
						{/if}

						{#if stream.stream_order}
							<div class="feature-attr">Stream Order: {stream.stream_order}</div>
						{/if}

						{#if stream.drainage_area_sqkm}
							<div class="feature-attr">Drainage Area: {stream.drainage_area_sqkm.toFixed(2)} km²</div>
						{/if}

						{#if stream.length_km > 0}
							<div class="feature-attr">Segment Length: {stream.length_km.toFixed(2)} km</div>
						{/if}

						{#if stream.upstream_length_km}
							<div class="feature-attr">Upstream Length: {stream.upstream_length_km.toFixed(2)} km</div>
						{/if}

						{#if stream.slope !== undefined && stream.slope !== null}
							<div class="feature-attr">Slope: {(stream.slope * 100).toFixed(3)}%</div>
						{/if}

						{#if stream.max_elev_m && stream.min_elev_m}
							<div class="feature-attr">Elevation Range: {stream.min_elev_m.toFixed(1)}m - {stream.max_elev_m.toFixed(1)}m</div>
						{/if}

						{#if stream.stream_type}
							<div class="feature-attr">Type: {stream.stream_type}</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if features.geology}
			<div class="feature-group">
				<h4>Geology</h4>
				{#each features.geology as geo}
					<div class="feature-item">
						<div class="feature-name">{geo.formation}</div>
						{#if geo.distance_meters !== undefined}
							<div class="feature-distance">
								{#if geo.distance_meters === 0}
									At this location
								{:else}
									Distance: {geo.distance_meters}m
								{/if}
							</div>
						{/if}
						<div class="feature-attr">Type: {geo.rock_type}</div>
						{#if geo.age && geo.age !== 'Unknown'}
							<div class="feature-attr">Age: {geo.age}</div>
						{/if}
						{#if geo.description}
							<div class="feature-description">{geo.description}</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{:else}
		<div class="no-features">No features found at this location</div>
	{/if}
</div>

<style>
	.feature-info {
		position: absolute;
		top: 1rem;
		right: 1rem;
		background: white;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		min-width: 300px;
		max-width: 400px;
		max-height: calc(100vh - 2rem);
		overflow-y: auto;
		z-index: 10;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 2px solid #e2e8f0;
	}

	h3 {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
	}

	.close-button {
		background: none;
		border: none;
		font-size: 1.5rem;
		color: #64748b;
		cursor: pointer;
		padding: 0;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.close-button:hover {
		color: #1e293b;
	}

	.location {
		padding: 1rem;
		background: #f8fafc;
		font-size: 0.813rem;
		color: #475569;
		border-bottom: 1px solid #e2e8f0;
	}

	.loading, .error, .no-features {
		padding: 2rem 1rem;
		text-align: center;
		color: #64748b;
		font-size: 0.875rem;
	}

	.error {
		color: #dc2626;
	}

	.feature-group {
		padding: 1rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.feature-group:last-child {
		border-bottom: none;
	}

	h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #3b82f6;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.feature-item {
		margin-bottom: 1rem;
		padding-bottom: 1rem;
		border-bottom: 1px dashed #e2e8f0;
	}

	.feature-item:last-child {
		margin-bottom: 0;
		padding-bottom: 0;
		border-bottom: none;
	}

	.feature-name {
		font-weight: 600;
		color: #1e293b;
		margin-bottom: 0.25rem;
	}

	.feature-attr {
		font-size: 0.813rem;
		color: #64748b;
		margin-bottom: 0.125rem;
	}

	.feature-description {
		font-size: 0.813rem;
		color: #475569;
		margin-top: 0.5rem;
		font-style: italic;
	}

	.feature-distance {
		font-size: 0.75rem;
		color: #3b82f6;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}
</style>
