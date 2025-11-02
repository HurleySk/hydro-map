<script lang="ts">
	import { layers, layerGroupStates } from '$lib/stores';
	import { slide } from 'svelte/transition';

	const layerGroups: Record<string, string[]> = {
		'Terrain': ['hillshade', 'slope', 'aspect', 'contours'],
		'Hydrology': ['streams-nhd', 'streams-dem', 'flow-accum'],
		'Reference': ['huc12-outline', 'geology']
	};

	const layerNames: Record<string, string> = {
		hillshade: 'Hillshade',
		slope: 'Slope',
		aspect: 'Aspect',
		'streams-nhd': 'Real Streams',
		'streams-dem': 'Drainage Network',
		'flow-accum': 'Water Accumulation',
		geology: 'Geology',
		contours: 'Contours',
		'huc12-outline': 'HUC12 Watersheds'
	};

	function toggleLayer(layerId: string) {
		layers.update(l => ({
			...l,
			[layerId]: {
				...l[layerId],
				visible: !l[layerId]?.visible
			}
		}));
	}

	function updateOpacity(layerId: string, opacity: number) {
		layers.update(l => ({
			...l,
			[layerId]: {
				...l[layerId],
				opacity
			}
		}));
	}

	function toggleGroup(groupName: string) {
		const key = groupName.toLowerCase() as 'terrain' | 'hydrology' | 'reference';
		layerGroupStates.update(states => ({
			...states,
			[key]: !states[key]
		}));
	}
</script>

<div class="panel">
	<h3>Layers</h3>

	{#each Object.entries(layerGroups) as [groupName, groupLayers]}
		{@const groupKey = groupName.toLowerCase()}
		{@const isExpanded = $layerGroupStates[groupKey]}
		<div class="layer-group">
			<button
				class="group-header"
				on:click={() => toggleGroup(groupName)}
				type="button"
				aria-expanded={isExpanded}
			>
				<svg
					class="chevron"
					class:rotated={isExpanded}
					width="12"
					height="12"
					viewBox="0 0 12 12"
					fill="none"
					aria-hidden="true"
				>
					<path
						d="M4.5 3L7.5 6L4.5 9"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				</svg>
				<h4>{groupName}</h4>
			</button>

			{#if isExpanded}
			<div class="group-content" transition:slide={{ duration: 200 }}>
			{#each groupLayers as layerId}
				{#if $layers[layerId]}
					<div class="layer-item">
						<label class="checkbox-label">
							<input
								type="checkbox"
								checked={$layers[layerId].visible}
								on:change={() => toggleLayer(layerId)}
							/>
							<span>{layerNames[layerId]}</span>
						</label>

						{#if $layers[layerId].visible}
							<div class="opacity-control">
								<label class="opacity-label">
									<span class="opacity-value">
										{Math.round($layers[layerId].opacity * 100)}%
									</span>
									<input
										type="range"
										min="0"
										max="1"
										step="0.1"
										value={$layers[layerId].opacity}
										on:input={(e) => updateOpacity(layerId, parseFloat(e.currentTarget.value))}
									/>
								</label>
							</div>
						{/if}
					</div>
				{/if}
			{/each}
			</div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.panel {
		background: white;
		border-radius: 8px;
		padding: 1rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
		min-width: 250px;
		max-width: 300px;
	}

	h3 {
		margin: 0 0 1rem 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		border-bottom: 2px solid #e2e8f0;
		padding-bottom: 0.5rem;
	}

	.layer-group {
		margin-bottom: 1rem;
	}

	.layer-group:last-child {
		margin-bottom: 0;
	}

	.group-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.25rem 0;
		margin-bottom: 0.5rem;
		background: none;
		border: none;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.group-header:hover {
		opacity: 0.8;
	}

	.group-header h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-align: left;
	}

	.chevron {
		flex-shrink: 0;
		color: #94a3b8;
		transition: transform 0.2s ease;
	}

	.chevron.rotated {
		transform: rotate(90deg);
	}

	.group-content {
		margin-left: 1.25rem;
	}

	.layer-item {
		margin-bottom: 0.75rem;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		cursor: pointer;
		user-select: none;
	}

	.checkbox-label input[type="checkbox"] {
		margin-right: 0.5rem;
		cursor: pointer;
	}

	.checkbox-label span {
		font-size: 0.875rem;
		color: #334155;
	}

	.opacity-control {
		margin-top: 0.5rem;
		margin-left: 1.5rem;
	}

	.opacity-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: #64748b;
	}

	.opacity-value {
		min-width: 35px;
		text-align: right;
	}

	input[type="range"] {
		flex: 1;
		height: 4px;
		border-radius: 2px;
		background: #e2e8f0;
		outline: none;
		appearance: none;
		-webkit-appearance: none;
	}

	input[type="range"]::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
	}

	input[type="range"]::-moz-range-thumb {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: none;
	}
</style>
