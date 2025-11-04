<script lang="ts">
	export let opacity: number = 1;

	// Okabe-Ito colorblind-safe palette
	const determinationTypes = [
		{ label: 'Erosion', color: '#E69F00', pattern: 'Crosshatch' },
		{ label: 'Vertical Erosion', color: '#D55E00', pattern: 'Diagonal \\' },
		{ label: 'Left Bank Unstable', color: '#56B4E9', pattern: 'Diagonal /' },
		{ label: 'Right Bank Unstable', color: '#0072B2', pattern: 'Vertical' },
		{ label: 'Left and Right Bank Unstable', color: '#009E73', pattern: 'Horizontal' },
		{ label: 'Habitat Score', color: '#F0E442', pattern: 'Dots' }
	];
</script>

<div class="legend" aria-label="Inadequate Outfalls legend">
	<h4>Inadequate Outfalls</h4>

	<div class="legend-items">
		{#each determinationTypes as item}
			<div class="legend-item">
				<div
					class="color-swatch"
					style="background-color: {item.color}; opacity: {opacity}"
					aria-label="{item.label} indicator"
				/>
				<div class="label-group">
					<span class="label">{item.label}</span>
					<span class="pattern-hint">({item.pattern})</span>
				</div>
			</div>
		{/each}
	</div>

	<div class="opacity-note">
		Opacity: {Math.round(opacity * 100)}%
	</div>
</div>

<style>
	.legend {
		position: absolute;
		bottom: 6rem;
		right: 1rem;
		background: white;
		border-radius: 8px;
		padding: 1rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
		z-index: 5;
		min-width: 200px;
		max-width: 250px;
	}

	h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		text-align: center;
	}

	.legend-items {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.color-swatch {
		width: 20px;
		height: 20px;
		border-radius: 3px;
		border: 1px solid rgba(0, 0, 0, 0.2);
		flex-shrink: 0;
	}

	.label-group {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.label {
		font-size: 0.75rem;
		color: #475569;
		line-height: 1.2;
	}

	.pattern-hint {
		font-size: 0.65rem;
		color: #94a3b8;
		font-style: italic;
	}

	.opacity-note {
		font-size: 0.7rem;
		color: #94a3b8;
		text-align: center;
		padding-top: 0.5rem;
		border-top: 1px solid #f1f5f9;
		margin-top: 0.25rem;
	}
</style>
