<script lang="ts">
	import { slide } from 'svelte/transition';
	import { onMount } from 'svelte';

	export let title: string;
	export let icon: string = '';
	export let expanded: boolean = true;
	export let collapsible: boolean = true;
	export let storageKey: string = '';

	// Load saved state from localStorage
	onMount(() => {
		if (storageKey && typeof window !== 'undefined') {
			const saved = localStorage.getItem(`panel-state-${storageKey}`);
			if (saved !== null) {
				expanded = saved === 'true';
			}
		}
	});

	function toggleExpanded() {
		if (!collapsible) return;
		expanded = !expanded;

		// Save state to localStorage
		if (storageKey && typeof window !== 'undefined') {
			localStorage.setItem(`panel-state-${storageKey}`, expanded.toString());
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (!collapsible) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			toggleExpanded();
		}
	}
</script>

<div class="collapsible-panel">
	<button
		class="panel-header"
		class:collapsible
		class:expanded
		on:click={toggleExpanded}
		on:keydown={handleKeydown}
		disabled={!collapsible}
		type="button"
		aria-expanded={expanded}
		aria-controls="panel-content-{title.toLowerCase().replace(/\s+/g, '-')}"
	>
		{#if collapsible}
			<svg
				class="chevron"
				class:rotated={expanded}
				width="16"
				height="16"
				viewBox="0 0 16 16"
				fill="none"
				aria-hidden="true"
			>
				<path
					d="M6 4L10 8L6 12"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			</svg>
		{/if}

		{#if icon}
			<span class="icon" aria-hidden="true">{icon}</span>
		{/if}

		<span class="title">{title}</span>
	</button>

	{#if expanded}
		<div
			class="panel-content"
			id="panel-content-{title.toLowerCase().replace(/\s+/g, '-')}"
			transition:slide={{ duration: 300 }}
			role="region"
			aria-labelledby="panel-header-{title.toLowerCase().replace(/\s+/g, '-')}"
		>
			<slot />
		</div>
	{/if}
</div>

<style>
	.collapsible-panel {
		background: white;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
		margin-bottom: 1rem;
		flex-shrink: 0;
	}

	.panel-header {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		border: none;
		background: transparent;
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		text-align: left;
		transition: background-color 0.2s ease;
		cursor: default;
	}

	.panel-header.collapsible {
		cursor: pointer;
	}

	.panel-header.collapsible:hover {
		background-color: #f8fafc;
	}

	.panel-header:disabled {
		cursor: default;
	}

	.chevron {
		flex-shrink: 0;
		color: #64748b;
		transition: transform 0.3s ease;
	}

	.chevron.rotated {
		transform: rotate(90deg);
	}

	.icon {
		flex-shrink: 0;
		font-size: 1rem;
	}

	.title {
		flex: 1;
	}

	.panel-content {
		border-top: 1px solid #e2e8f0;
		overflow: visible;
		border-radius: 0 0 8px 8px;
	}

	/* Remove default button styles */
	.panel-header:focus {
		outline: none;
	}

	.panel-header:focus-visible {
		outline: 2px solid #3b82f6;
		outline-offset: -2px;
		border-radius: 6px;
	}
</style>