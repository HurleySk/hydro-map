<script lang="ts">
	export let opacity: number = 1;
</script>

<div class="legend" aria-label="Topographic Wetness Index legend">
	<h4>Topographic Wetness Index</h4>

	<div class="gradient-container">
		<div class="label top">Wet</div>
		<div
			class="gradient-bar"
			style="opacity: {opacity}"
			aria-label="Color gradient from transparent (dry) to deep blue (wet)"
		/>
		<div class="label bottom">Dry</div>
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
		min-width: 160px;
	}

	h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		text-align: center;
	}

	.gradient-container {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.gradient-bar {
		width: 30px;
		height: 180px;
		/* Colors from TWI color ramp, in reverse order (top = high TWI/wet) */
		background: linear-gradient(
			to bottom,
			rgba(12, 44, 132, 1),      /* 255: Maximum wetness */
			rgba(40, 90, 180, 1),      /* 192: Very dark blue */
			rgba(70, 130, 220, 1),     /* 160: Dark blue */
			rgba(100, 180, 255, 1),    /* 128: Deeper blue */
			rgba(150, 210, 255, 1),    /* 96: Medium blue */
			rgba(200, 230, 255, 0.63), /* 64: Light blue */
			rgba(230, 240, 255, 0.55), /* 32: Very light */
			rgba(255, 255, 230, 0.5)   /* 0: Dry areas */
		);
		border: 1px solid #e2e8f0;
		border-radius: 4px;
	}

	.label {
		font-size: 0.75rem;
		color: #64748b;
		font-weight: 500;
		writing-mode: vertical-rl;
		text-orientation: mixed;
	}

	.label.top {
		align-self: flex-start;
	}

	.label.bottom {
		align-self: flex-end;
	}

	.opacity-note {
		font-size: 0.7rem;
		color: #94a3b8;
		text-align: center;
		padding-top: 0.25rem;
		border-top: 1px solid #f1f5f9;
	}
</style>
