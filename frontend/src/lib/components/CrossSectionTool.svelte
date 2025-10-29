<script lang="ts">
	import { activeTool, crossSection, crossSectionLine } from '$lib/stores';
	import { get } from 'svelte/store';

	let isActive = false;
	let linePoints: [number, number][] = [];

	$: linePoints = $crossSectionLine;

	function toggleTool() {
		isActive = !isActive;
		activeTool.set(isActive ? 'cross-section' : 'none');
		if (!isActive) {
			clearLine();
		} else {
			crossSectionLine.set([]);
			crossSection.set(null);
		}
	}

	function clearLine() {
		crossSectionLine.set([]);
		crossSection.set(null);
	}

	async function generateProfile() {
		const line = get(crossSectionLine);
		if (line.length < 2) return;

		try {
			const response = await fetch('/api/cross-section', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					line
				})
			});

			if (!response.ok) {
				throw new Error('Cross-section generation failed');
			}

			const result = await response.json();
			crossSection.set(result);
		} catch (error) {
			console.error('Cross-section error:', error);
			alert('Failed to generate cross-section. Check backend is running.');
		}
	}
</script>

<div class="panel">
	<h3>Cross-Section Tool</h3>

	<button
		class="tool-button"
		class:active={isActive}
		on:click={toggleTool}
	>
		{isActive ? 'Cancel' : 'Draw Cross-Section'}
	</button>

	{#if isActive}
		<p class="instructions">
			Click two or more points on the map to draw a profile line.
		</p>

		{#if linePoints.length >= 2}
			<div class="actions">
				<button class="action-button primary" on:click={generateProfile}>
					Generate Profile
				</button>
				<button class="action-button secondary" on:click={clearLine}>
					Clear Line
				</button>
			</div>

			<p class="point-count">
				{linePoints.length} points selected
			</p>
		{/if}
	{/if}

	{#if $crossSection}
		<div class="profile-preview">
			<h4>Profile Generated</h4>
			<p>
				Distance: {($crossSection.metadata.total_distance_m / 1000).toFixed(2)} km<br/>
				Samples: {$crossSection.metadata.num_samples}<br/>
				Geology contacts: {$crossSection.metadata.num_geology_contacts}
			</p>
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
		background: #8b5cf6;
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.2s;
	}

	.tool-button:hover {
		background: #7c3aed;
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
		background: #faf5ff;
		border-left: 3px solid #8b5cf6;
		font-size: 0.875rem;
		color: #6b21a8;
		border-radius: 4px;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	.action-button {
		flex: 1;
		padding: 0.5rem;
		border: none;
		border-radius: 6px;
		font-size: 0.813rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.action-button.primary {
		background: #10b981;
		color: white;
	}

	.action-button.primary:hover {
		background: #059669;
	}

	.action-button.secondary {
		background: #f1f5f9;
		color: #475569;
		border: 1px solid #cbd5e1;
	}

	.action-button.secondary:hover {
		background: #e2e8f0;
	}

	.point-count {
		margin: 0.75rem 0 0 0;
		font-size: 0.813rem;
		color: #64748b;
		text-align: center;
	}

	.profile-preview {
		margin-top: 1rem;
		padding: 0.75rem;
		background: #f0fdf4;
		border-radius: 6px;
		border: 1px solid #86efac;
	}

	.profile-preview h4 {
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #166534;
	}

	.profile-preview p {
		margin: 0;
		font-size: 0.813rem;
		color: #166534;
		line-height: 1.5;
	}
</style>
