/**
 * Geocoding service using Nominatim (OpenStreetMap)
 * Free geocoding with no API key required
 */

export interface GeocodingResult {
	display_name: string;
	lat: string;
	lon: string;
	boundingbox: [string, string, string, string]; // [south, north, west, east]
	type: string;
	importance: number;
}

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';
const USER_AGENT = 'Hydro-Map/0.1.0';

/**
 * Search for a location using Nominatim geocoding
 *
 * @param query Search query (address, city, place name, or coordinates)
 * @param limit Maximum number of results (default: 5)
 * @returns Array of geocoding results
 */
export async function searchLocation(query: string, limit: number = 5): Promise<GeocodingResult[]> {
	if (!query || query.trim().length === 0) {
		return [];
	}

	// Check if query looks like coordinates (e.g., "37.7749, -122.4194")
	const coordMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/);
	if (coordMatch) {
		const lat = parseFloat(coordMatch[1]);
		const lon = parseFloat(coordMatch[2]);

		if (isValidCoordinate(lat, lon)) {
			return [{
				display_name: `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
				lat: lat.toString(),
				lon: lon.toString(),
				boundingbox: [
					(lat - 0.01).toString(),
					(lat + 0.01).toString(),
					(lon - 0.01).toString(),
					(lon + 0.01).toString()
				],
				type: 'coordinates',
				importance: 1.0
			}];
		}
	}

	try {
		const params = new URLSearchParams({
			q: query,
			format: 'json',
			limit: limit.toString(),
			addressdetails: '1',
			'accept-language': 'en'
		});

		const response = await fetch(`${NOMINATIM_URL}?${params}`, {
			headers: {
				'User-Agent': USER_AGENT
			}
		});

		if (!response.ok) {
			throw new Error(`Geocoding failed: ${response.statusText}`);
		}

		const results: GeocodingResult[] = await response.json();
		return results;
	} catch (error) {
		console.error('Geocoding error:', error);
		return [];
	}
}

/**
 * Validate if coordinates are within valid ranges
 */
function isValidCoordinate(lat: number, lon: number): boolean {
	return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

/**
 * Reverse geocode - get place name from coordinates
 *
 * @param lat Latitude
 * @param lon Longitude
 * @returns Place name or null
 */
export async function reverseGeocode(lat: number, lon: number): Promise<string | null> {
	if (!isValidCoordinate(lat, lon)) {
		return null;
	}

	try {
		const params = new URLSearchParams({
			lat: lat.toString(),
			lon: lon.toString(),
			format: 'json',
			'accept-language': 'en'
		});

		const response = await fetch(`https://nominatim.openstreetmap.org/reverse?${params}`, {
			headers: {
				'User-Agent': USER_AGENT
			}
		});

		if (!response.ok) {
			return null;
		}

		const result = await response.json();
		return result.display_name || null;
	} catch (error) {
		console.error('Reverse geocoding error:', error);
		return null;
	}
}

/**
 * Format a geocoding result for display
 */
export function formatResult(result: GeocodingResult): string {
	return result.display_name;
}

/**
 * Get the center coordinates from a geocoding result
 */
export function getCenter(result: GeocodingResult): [number, number] {
	return [parseFloat(result.lon), parseFloat(result.lat)];
}

/**
 * Calculate an appropriate zoom level based on bounding box
 */
export function calculateZoom(result: GeocodingResult): number {
	const bbox = result.boundingbox;
	const south = parseFloat(bbox[0]);
	const north = parseFloat(bbox[1]);
	const west = parseFloat(bbox[2]);
	const east = parseFloat(bbox[3]);

	const latDiff = north - south;
	const lonDiff = east - west;
	const maxDiff = Math.max(latDiff, lonDiff);

	// Rough zoom level calculation
	if (maxDiff > 10) return 6;
	if (maxDiff > 5) return 8;
	if (maxDiff > 1) return 10;
	if (maxDiff > 0.5) return 11;
	if (maxDiff > 0.1) return 13;
	if (maxDiff > 0.01) return 15;
	return 16;
}
