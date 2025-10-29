<script lang="ts">
	import { layers } from '$lib/stores';

	const layerGroups: Record<string, string[]> = {
		'Terrain': ['hillshade', 'slope', 'aspect'],
		'Hydrology': ['streams'],
		'Geology': ['geology', 'contours']
	};

	const layerNames: Record<string, string> = {
		hillshade: 'Hillshade',
		slope: 'Slope',
		aspect: 'Aspect',
		streams: 'Stream Network',
		geology: 'Geology',
		contours: 'Contours'
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
</script>

<div class="panel">
	<h3>Layers</h3>

	{#each Object.entries(layerGroups) as [groupName, groupLayers]}
		<div class="layer-group">
			<h4>{groupName}</h4>

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

	h4 {
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
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
