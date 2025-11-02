<script lang="ts">
	import { onMount } from 'svelte';
	import { generatePatternDataURL, type GeologyType } from '$lib/utils/patterns';

	export let opacity: number = 1;

	// Rock types present in the actual Virginia geology data
	interface RockType {
		type: GeologyType;
		color: string;
		label: string;
		pattern?: string;
	}

	const rockTypes: RockType[] = [
		{ type: 'unconsolidated-undifferentiated', color: '#d4d4d8', label: 'Unconsolidated' },
		{ type: 'metamorphic-schist', color: '#9333ea', label: 'Metamorphic: Schist' },
		{ type: 'metamorphic-sedimentary-clastic', color: '#a855f7', label: 'Metamorphic: Sed. Clastic' },
		{ type: 'metamorphic-undifferentiated', color: '#8b5cf6', label: 'Metamorphic: Undiff.' },
		{ type: 'metamorphic-volcanic', color: '#c084fc', label: 'Metamorphic: Volcanic' },
		{ type: 'melange', color: '#7c3aed', label: 'Melange' },
		{ type: 'igneous-intrusive', color: '#f59e0b', label: 'Igneous: Intrusive' },
		{ type: 'water', color: '#3b82f6', label: 'Water' }
	];

	// Generate patterns on mount
	onMount(() => {
		rockTypes.forEach(type => {
			type.pattern = generatePatternDataURL(type.type, type.color);
		});
	});
</script>

<div class="legend" aria-label="Geology legend">
	<h4>Geology</h4>
	<div class="legend-items" style="opacity: {opacity}">
		{#each rockTypes as type}
			<div class="legend-item">
				<span
					class="color-swatch"
					style="background-image: {type.pattern ? `url(${type.pattern})` : 'none'}; background-color: {type.color}; background-size: contain;"
					aria-hidden="true"
					title="{type.label} - Pattern for colorblind accessibility"
				></span>
				<span class="label">{type.label}</span>
			</div>
		{/each}
	</div>
	{#if opacity < 1}
		<div class="opacity-note">
			Opacity: {Math.round(opacity * 100)}%
		</div>
	{/if}
</div>

<style>
	.legend {
		position: absolute;
		bottom: 1rem;
		right: 1rem;
		background: white;
		border-radius: 8px;
		padding: 1rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
		z-index: 5;
		min-width: 140px;
		max-width: 200px;
	}

	h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.legend-items {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
		transition: opacity 0.2s ease;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.color-swatch {
		width: 16px;
		height: 16px;
		border-radius: 3px;
		border: 1px solid #e2e8f0;
		flex-shrink: 0;
	}

	.label {
		font-size: 0.75rem;
		color: #64748b;
		line-height: 1;
	}

	.opacity-note {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid #e2e8f0;
		font-size: 0.75rem;
		color: #94a3b8;
		text-align: center;
	}
</style>