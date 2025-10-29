<script lang="ts">
interface ProfilePoint {
	distance: number;
	elevation: number | null;
	lat: number;
	lon: number;
}

type ElevationPoint = ProfilePoint & { elevation: number };

export let profile: ProfilePoint[] = [];

	const width = 280;
	const height = 140;
	const padding = 24;

	$: validPoints = profile.filter((point): point is ElevationPoint => point.elevation !== null);
	$: distances = validPoints.map((point) => point.distance);
	$: elevations = validPoints.map((point) => point.elevation);
	$: maxDistance = distances.length ? Math.max(...distances) : 0;
	$: minDistance = distances.length ? Math.min(...distances) : 0;
	$: maxElevation = elevations.length ? Math.max(...elevations) : 0;
	$: minElevation = elevations.length ? Math.min(...elevations) : 0;

	function xScale(distance: number) {
		if (maxDistance === minDistance) return padding;
		return padding + ((distance - minDistance) / (maxDistance - minDistance)) * (width - padding * 2);
	}

	function yScale(elevation: number) {
		if (maxElevation === minElevation) return height - padding;
		const normalized = (elevation - minElevation) / (maxElevation - minElevation);
		return height - padding - normalized * (height - padding * 2);
	}

	$: linePath = validPoints.length
		? validPoints
			.map((point, index) => `${index === 0 ? 'M' : 'L'}${xScale(point.distance)} ${yScale(point.elevation)}`)
			.join(' ')
		: '';
	$: firstPoint = validPoints[0] ?? null;
	$: lastPoint = validPoints.length ? validPoints[validPoints.length - 1] : null;
	$: fillPath = linePath && firstPoint && lastPoint
		? `${linePath} L${xScale(lastPoint.distance)} ${height - padding} L${xScale(firstPoint.distance)} ${height - padding} Z`
		: '';
</script>

{#if validPoints.length < 2}
	<p class="placeholder">Insufficient elevation samples to render a profile.</p>
{:else}
	<svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Cross-section elevation profile">
		<defs>
			<linearGradient id="profile-fill" x1="0" x2="0" y1="0" y2="1">
				<stop offset="0%" stop-color="#38bdf8" stop-opacity="0.35" />
				<stop offset="100%" stop-color="#0ea5e9" stop-opacity="0" />
			</linearGradient>
		</defs>

		<!-- Axes -->
		<line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} class="axis" />
		<line x1={padding} y1={padding} x2={padding} y2={height - padding} class="axis" />

		<!-- Profile fill -->
		{#if fillPath}
			<path d={fillPath} fill="url(#profile-fill)" />
		{/if}

		<!-- Profile line -->
		<path d={linePath} class="profile-line" />
	</svg>
{/if}

<style>
	svg {
		width: 100%;
		height: auto;
	}

	.axis {
		stroke: #cbd5e1;
		stroke-width: 1;
	}

	.profile-line {
		fill: none;
		stroke: #0284c7;
		stroke-width: 2;
	}

	.placeholder {
		margin: 0;
		font-size: 0.813rem;
		color: #64748b;
		text-align: center;
	}
</style>
