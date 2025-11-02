<script lang="ts">
	export let opacity: number = 1;
</script>

<div class="legend" aria-label="Water accumulation legend">
	<h4>Water Accumulation</h4>

	<div class="gradient-container">
		<div class="label top">High</div>
		<div
			class="gradient-bar"
			style="opacity: {opacity}"
			aria-label="Color gradient from transparent (low accumulation) to deep blue (high accumulation)"
		/>
		<div class="label bottom">Low</div>
	</div>

	<div class="opacity-note">
		Opacity: {Math.round(opacity * 100)}%
	</div>
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
		/* Colors from our color ramp file, in reverse order (top = high values) */
		background: linear-gradient(
			to bottom,
			rgb(12, 44, 132),         /* 255: deepest dark blue */
			rgb(34, 94, 168),         /* 180: blue-purple */
			rgb(66, 146, 255),        /* 120: deep blue */
			rgb(103, 169, 255),       /* 80: stronger blue */
			rgb(158, 197, 255),       /* 40: medium blue */
			rgb(198, 227, 255),       /* 20: light blue */
			rgba(232, 246, 255, 0.24), /* 1: very faint light-cyan (60/255 = 0.24) */
			rgba(255, 255, 255, 0)     /* 0: fully transparent */
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