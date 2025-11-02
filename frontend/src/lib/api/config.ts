/**
 * API configuration utilities for consistent endpoint management.
 * Handles development vs production environments and cross-origin setups.
 */

/**
 * Get the base URL for API requests.
 * In development, this will use the Vite proxy configuration.
 * In production, it uses the same origin as the frontend.
 */
export function getApiBase(): string {
  // Check for environment variable override
  const envBase = import.meta.env.VITE_API_URL as string | undefined;
  if (envBase) {
    return envBase;
  }

  // In SSR or build time, return empty string (will be handled by proxy)
  if (typeof window === 'undefined') {
    return '';
  }

  // In development with Vite (port 5173), use proxy path
  // The Vite proxy will forward /api/* to localhost:8000
  if (window.location.port === '5173') {
    return ''; // Use relative URLs, Vite proxy handles the rest
  }

  // In production or other environments, use the same origin
  return window.location.origin;
}

/**
 * Construct a full API URL from an endpoint path.
 * @param endpoint - The API endpoint path (e.g., '/api/delineate')
 * @returns The full URL for the API request
 */
export function getApiUrl(endpoint: string): string {
  const base = getApiBase();

  // Ensure endpoint starts with /
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // If base is empty (using proxy), return just the endpoint
  if (!base) {
    return normalizedEndpoint;
  }

  // Remove trailing slash from base and combine
  const normalizedBase = base.replace(/\/$/, '');
  return `${normalizedBase}${normalizedEndpoint}`;
}

/**
 * Get the tiles base URL for PMTiles access
 */
export function getTilesBase(): string {
  // Check for environment variable override
  const envTilesBase = import.meta.env.VITE_TILES_URL as string | undefined;
  if (envTilesBase) {
    return envTilesBase;
  }

  // Default to /tiles/ which will use the proxy in development
  return '/tiles/';
}

/**
 * Common fetch options for API requests
 */
export const defaultFetchOptions: RequestInit = {
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'same-origin', // Include cookies for same-origin requests
};

/**
 * Helper function to make API POST requests with consistent configuration
 */
export async function apiPost<T = any>(
  endpoint: string,
  body: any,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(endpoint);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: 'POST',
    body: JSON.stringify(body),
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text().catch(() => response.statusText);
    throw new Error(`API request failed: ${response.status} - ${error}`);
  }

  return response.json();
}

/**
 * Helper function to make API GET requests with consistent configuration
 */
export async function apiGet<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(endpoint);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: 'GET',
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text().catch(() => response.statusText);
    throw new Error(`API request failed: ${response.status} - ${error}`);
  }

  return response.json();
}

/**
 * Check if the API is healthy
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await apiGet('/health');
    return response?.status === 'healthy';
  } catch {
    return false;
  }
}