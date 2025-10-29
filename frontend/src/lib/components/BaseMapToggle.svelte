<script lang="ts">
	import { basemapStyle } from '$lib/stores';
	import type { BasemapStyle } from '$lib/stores';

	const options: { value: BasemapStyle; label: string }[] = [
		{ value: 'osm', label: 'Color' },
		{ value: 'light', label: 'Light Gray' }
	];

	$: current = $basemapStyle;

	function select(style: BasemapStyle) {
		basemapStyle.set(style);
	}
</script>

<div class="panel">
	<h3>Basemap</h3>
	<div class="toggle">
		{#each options as option}
			<button
				type="button"
				on:click={() => select(option.value)}
				class:selected={current === option.value}
			>
				{option.label}
			</button>
		{/each}
	</div>
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
		margin: 0 0 0.75rem 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		border-bottom: 2px solid #e2e8f0;
		padding-bottom: 0.5rem;
	}

	.toggle {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.5rem;
	}

	button {
		padding: 0.5rem;
		border-radius: 6px;
		border: 1px solid #cbd5e1;
		background: #f8fafc;
		color: #475569;
		font-size: 0.813rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	button:hover {
		background: #e2e8f0;
		border-color: #94a3b8;
	}

	button.selected {
		background: #3b82f6;
		color: white;
		border-color: #2563eb;
	}
</style>
