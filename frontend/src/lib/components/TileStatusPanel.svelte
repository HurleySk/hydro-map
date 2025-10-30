<script lang="ts">
	import { tileStatus } from '$lib/stores';

	$: statuses = $tileStatus;
</script>

{#if statuses.length > 0}
	<div class="panel">
		<h3>Tile Status</h3>
		{#each statuses as status}
			<div class="status" class:ok={status.available} class:warn={!status.available}>
				<div class="label">{status.label}</div>
				<div class="message">{status.message ?? (status.available ? 'Available' : 'Unavailable')}</div>
			</div>
		{/each}
	</div>
{:else}
	<div class="panel">
		<h3>Tile Status</h3>
		<p class="message">Checking tile availability…</p>
	</div>
{/if}

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

	.status {
		border-radius: 6px;
		padding: 0.5rem 0.75rem;
		margin-bottom: 0.5rem;
		background: #f8fafc;
		border: 1px solid #cbd5e1;
	}

	.status:last-child {
		margin-bottom: 0;
	}

	.status.ok {
		background: #ecfdf5;
		border-color: #bbf7d0;
	}

	.status.warn {
		background: #fef2f2;
		border-color: #fecaca;
	}

	.label {
		font-size: 0.875rem;
		font-weight: 600;
		color: #0f172a;
	}

	.message {
		font-size: 0.75rem;
		color: #475569;
		margin-top: 0.25rem;
	}
</style>
