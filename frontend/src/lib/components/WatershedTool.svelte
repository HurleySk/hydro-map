<script lang="ts">
	import { activeTool, watersheds } from '$lib/stores';

	let isActive = false;
	let snapToStream = true;

	function toggleTool() {
		isActive = !isActive;
		activeTool.set(isActive ? 'delineate' : 'none');
	}

	function clearWatersheds() {
		watersheds.set([]);
		// This will be handled by the Map component
		window.dispatchEvent(new CustomEvent('clear-watersheds'));
	}

	$: numWatersheds = $watersheds.length;
</script>

<div class="panel">
	<h3>Watershed Delineation</h3>

	<button
		class="tool-button"
		class:active={isActive}
		on:click={toggleTool}
	>
		{isActive ? 'Cancel' : 'Delineate Watershed'}
	</button>

	{#if isActive}
		<p class="instructions">
			Click anywhere on the map to delineate the upstream watershed.
		</p>

		<label class="checkbox-label">
			<input type="checkbox" bind:checked={snapToStream} />
			<span>Snap to nearest stream</span>
		</label>
	{/if}

	{#if numWatersheds > 0}
		<div class="results">
			<p class="result-count">
				{numWatersheds} watershed{numWatersheds > 1 ? 's' : ''} delineated
			</p>

			<button class="clear-button" on:click={clearWatersheds}>
				Clear All
			</button>
		</div>
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
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.2s;
	}

	.tool-button:hover {
		background: #2563eb;
	}

	.tool-button.active {
		background: #dc2626;
	}

	.tool-button.active:hover {
		background: #b91c1c;
	}

	.instructions {
		margin: 1rem 0 0.75rem 0;
		padding: 0.75rem;
		background: #eff6ff;
		border-left: 3px solid #3b82f6;
		font-size: 0.875rem;
		color: #1e40af;
		border-radius: 4px;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		font-size: 0.875rem;
		color: #334155;
		cursor: pointer;
		user-select: none;
	}

	.checkbox-label input {
		margin-right: 0.5rem;
		cursor: pointer;
	}

	.results {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.result-count {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		color: #64748b;
	}

	.clear-button {
		width: 100%;
		padding: 0.5rem;
		background: #f1f5f9;
		color: #475569;
		border: 1px solid #cbd5e1;
		border-radius: 6px;
		font-size: 0.813rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.clear-button:hover {
		background: #e2e8f0;
		border-color: #94a3b8;
	}
</style>
