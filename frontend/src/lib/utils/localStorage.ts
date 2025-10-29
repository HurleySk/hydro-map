/**
 * LocalStorage utility functions for Hydro-Map
 * Provides type-safe localStorage access with fallbacks
 */

const STORAGE_PREFIX = 'hydro-map:';

/**
 * Get an item from localStorage with type safety
 */
export function getItem<T>(key: string, defaultValue: T): T {
	if (typeof window === 'undefined') {
		return defaultValue;
	}

	try {
		const item = window.localStorage.getItem(STORAGE_PREFIX + key);
		return item ? JSON.parse(item) : defaultValue;
	} catch (error) {
		console.warn(`Failed to read from localStorage: ${key}`, error);
		return defaultValue;
	}
}

/**
 * Set an item in localStorage with type safety
 */
export function setItem<T>(key: string, value: T): void {
	if (typeof window === 'undefined') {
		return;
	}

	try {
		window.localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
	} catch (error) {
		console.warn(`Failed to write to localStorage: ${key}`, error);
	}
}

/**
 * Remove an item from localStorage
 */
export function removeItem(key: string): void {
	if (typeof window === 'undefined') {
		return;
	}

	try {
		window.localStorage.removeItem(STORAGE_PREFIX + key);
	} catch (error) {
		console.warn(`Failed to remove from localStorage: ${key}`, error);
	}
}

/**
 * Clear all Hydro-Map items from localStorage
 */
export function clearAll(): void {
	if (typeof window === 'undefined') {
		return;
	}

	try {
		const keys = Object.keys(window.localStorage);
		keys.forEach(key => {
			if (key.startsWith(STORAGE_PREFIX)) {
				window.localStorage.removeItem(key);
			}
		});
	} catch (error) {
		console.warn('Failed to clear localStorage', error);
	}
}

/**
 * Check if localStorage is available
 */
export function isAvailable(): boolean {
	if (typeof window === 'undefined') {
		return false;
	}

	try {
		const testKey = STORAGE_PREFIX + '__test__';
		window.localStorage.setItem(testKey, 'test');
		window.localStorage.removeItem(testKey);
		return true;
	} catch {
		return false;
	}
}
