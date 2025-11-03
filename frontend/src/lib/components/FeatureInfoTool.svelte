<script lang="ts">
	import { activeTool } from '$lib/stores';
	import { writable } from 'svelte/store';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	$: currentTool = $activeTool;
	$: isActive = currentTool === 'info';

	let bufferRadius = 10; // Default 10m

	function toggleTool() {
		activeTool.set(isActive ? 'none' : 'info');
	}

	// Dispatch buffer changes to parent
	function updateBuffer() {
		dispatch('bufferChange', bufferRadius);
	}

	export { bufferRadius };
</script>

<div class="panel">
	<h3>Feature Info</h3>

	<button
		class="tool-button"
		class:active={isActive}
		on:click={toggleTool}
	>
		{isActive ? 'Cancel' : 'Inspect Features'}
	</button>

	{#if isActive}
		<div class="settings">
			<label for="buffer-slider" class="slider-label">
				Search Buffer: {bufferRadius}m
			</label>
			<input
				id="buffer-slider"
				type="range"
				min="10"
				max="200"
				step="10"
				bind:value={bufferRadius}
				on:input={updateBuffer}
			/>
			<div class="slider-marks">
				<span>10m</span>
				<span>200m</span>
			</div>
		</div>

		<p class="instructions">
			Click the map to list nearby streams and geology attributes.
		</p>
	{/if}
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

	.tool-button {
		width: 100%;
		padding: 0.75rem;
		background: #0ea5e9;
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.2s;
	}

	.tool-button:hover {
		background: #0284c7;
	}

	.tool-button.active {
		background: #dc2626;
	}

	.tool-button.active:hover {
		background: #b91c1c;
	}

	.settings {
		margin: 1rem 0;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 6px;
	}

	.slider-label {
		display: block;
		font-size: 0.813rem;
		font-weight: 500;
		color: #475569;
		margin-bottom: 0.5rem;
	}

	input[type="range"] {
		width: 100%;
		height: 6px;
		background: #cbd5e1;
		border-radius: 3px;
		outline: none;
		-webkit-appearance: none;
	}

	input[type="range"]::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 16px;
		height: 16px;
		background: #0ea5e9;
		cursor: pointer;
		border-radius: 50%;
	}

	input[type="range"]::-moz-range-thumb {
		width: 16px;
		height: 16px;
		background: #0ea5e9;
		cursor: pointer;
		border-radius: 50%;
		border: none;
	}

	.slider-marks {
		display: flex;
		justify-content: space-between;
		margin-top: 0.25rem;
		font-size: 0.688rem;
		color: #94a3b8;
	}

	.instructions {
		margin: 1rem 0 0 0;
		padding: 0.75rem;
		background: #f0f9ff;
		border-left: 3px solid #0ea5e9;
		font-size: 0.875rem;
		color: #0369a1;
		border-radius: 4px;
	}
</style>
