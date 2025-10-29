<script lang="ts">
	import { activeTool } from '$lib/stores';

	$: currentTool = $activeTool;
	$: isActive = currentTool === 'info';

	function toggleTool() {
		activeTool.set(isActive ? 'none' : 'info');
	}
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
