<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { searchHistory } from '$lib/stores';
	import type { SearchHistoryItem } from '$lib/stores';
	import { searchLocation, getCenter, calculateZoom } from '$lib/utils/geocoding';
	import type { GeocodingResult } from '$lib/utils/geocoding';

	const dispatch = createEventDispatcher();

	let query = '';
	let results: GeocodingResult[] = [];
	let isSearching = false;
	let showResults = false;
	let showHistory = false;
	let selectedIndex = -1;
	let searchTimeout: number;

	// Handle search input
	function handleInput() {
		clearTimeout(searchTimeout);

		if (query.trim().length === 0) {
			results = [];
			showResults = false;
			showHistory = true;
			return;
		}

		showHistory = false;
		isSearching = true;

		searchTimeout = window.setTimeout(async () => {
			const searchResults = await searchLocation(query, 5);
			results = searchResults;
			showResults = results.length > 0;
			isSearching = false;
			selectedIndex = -1;
		}, 300);
	}

	// Handle result selection
	function selectResult(result: GeocodingResult) {
		const center = getCenter(result);
		const zoom = calculateZoom(result);

		// Add to history
		addToHistory({
			query: result.display_name,
			center,
			zoom,
			timestamp: Date.now()
		});

		// Dispatch event to fly to location
		dispatch('select', { center, zoom, name: result.display_name });

		// Clear search
		query = '';
		results = [];
		showResults = false;
		showHistory = false;
	}

	// Select from history
	function selectHistoryItem(item: SearchHistoryItem) {
		dispatch('select', { center: item.center, zoom: item.zoom, name: item.query });

		query = '';
		showHistory = false;
	}

	// Add to search history
	function addToHistory(item: SearchHistoryItem) {
		searchHistory.update(history => {
			// Remove duplicates
			const filtered = history.filter(h => h.query !== item.query);
			// Add new item at the beginning
			const updated = [item, ...filtered];
			// Keep only last 10 items
			return updated.slice(0, 10);
		});
	}

	// Keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		const items = showHistory ? $searchHistory : results;

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, 0);
		} else if (event.key === 'Enter' && selectedIndex >= 0) {
			event.preventDefault();
			if (showHistory) {
				selectHistoryItem(items[selectedIndex]);
			} else {
				selectResult(items[selectedIndex]);
			}
		} else if (event.key === 'Escape') {
			query = '';
			results = [];
			showResults = false;
			showHistory = false;
		}
	}

	// Handle focus
	function handleFocus() {
		if (query.trim().length === 0 && $searchHistory.length > 0) {
			showHistory = true;
		}
	}

	// Handle blur (with delay to allow clicking results)
	function handleBlur() {
		setTimeout(() => {
			showResults = false;
			showHistory = false;
		}, 200);
	}

	// Clear search
	function clearSearch() {
		query = '';
		results = [];
		showResults = false;
		showHistory = false;
	}
</script>

<div class="search-container">
	<div class="search-input-wrapper">
		<svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
			<path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
		</svg>

		<input
			type="text"
			bind:value={query}
			on:input={handleInput}
			on:focus={handleFocus}
			on:blur={handleBlur}
			on:keydown={handleKeydown}
			placeholder="Search location..."
			class="search-input"
		/>

		{#if query.length > 0}
			<button class="clear-button" on:click={clearSearch} type="button">
				<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
					<path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
				</svg>
			</button>
		{:else if isSearching}
			<div class="spinner"></div>
		{/if}
	</div>

	{#if showResults && results.length > 0}
		<div class="results-dropdown">
			{#each results as result, index}
				<button
					class="result-item"
					class:selected={index === selectedIndex}
					on:click={() => selectResult(result)}
					type="button"
				>
					<svg class="result-icon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
						<path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/>
					</svg>
					<span class="result-text">{result.display_name}</span>
				</button>
			{/each}
		</div>
	{/if}

	{#if showHistory && $searchHistory.length > 0}
		<div class="results-dropdown">
			<div class="history-header">Recent Searches</div>
			{#each $searchHistory as item, index}
				<button
					class="result-item"
					class:selected={index === selectedIndex}
					on:click={() => selectHistoryItem(item)}
					type="button"
				>
					<svg class="result-icon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
						<path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
						<path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
					</svg>
					<span class="result-text">{item.query}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.search-container {
		position: relative;
		width: 100%;
	}

	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		left: 12px;
		color: #64748b;
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem 2.5rem 0.75rem 2.5rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.875rem;
		background: white;
		outline: none;
		transition: all 0.2s;
	}

	.search-input:focus {
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.search-input::placeholder {
		color: #94a3b8;
	}

	.clear-button {
		position: absolute;
		right: 8px;
		padding: 4px;
		background: none;
		border: none;
		color: #64748b;
		cursor: pointer;
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.clear-button:hover {
		background: #f1f5f9;
		color: #334155;
	}

	.spinner {
		position: absolute;
		right: 12px;
		width: 16px;
		height: 16px;
		border: 2px solid #e2e8f0;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.results-dropdown {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		max-height: 300px;
		overflow-y: auto;
		z-index: 100;
	}

	.history-header {
		padding: 0.5rem 1rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid #e2e8f0;
	}

	.result-item {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border: none;
		background: none;
		text-align: left;
		cursor: pointer;
		transition: background 0.2s;
		border-bottom: 1px solid #f1f5f9;
	}

	.result-item:last-child {
		border-bottom: none;
	}

	.result-item:hover,
	.result-item.selected {
		background: #f8fafc;
	}

	.result-icon {
		flex-shrink: 0;
		color: #64748b;
	}

	.result-text {
		flex: 1;
		font-size: 0.875rem;
		color: #334155;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.result-item.selected .result-text {
		color: #1e293b;
		font-weight: 500;
	}
</style>
