/**
 * API utility functions with automatic 401 handling
 */

import { config } from "../config";
import { parseApiError } from "./handleApiError";

const TOKEN_KEY = "dbrevel_auth_token";

/**
 * Fetch wrapper that automatically handles 401 errors by logging out
 * @param url - API endpoint URL (relative to config.apiUrl)
 * @param options - Fetch options
 * @param onUnauthorized - Callback when 401 is received (typically logout function)
 * @returns Promise<Response>
 */
export async function apiFetch(
	url: string,
	options: RequestInit = {},
	onUnauthorized?: () => void,
): Promise<Response> {
	// Ensure URL is absolute
	const fullUrl = url.startsWith("http") ? url : `${config.apiUrl}${url}`;

	// Automatically add Authorization header if token exists and not already provided
	const headers = new Headers();

	// Copy existing headers if provided
	if (options.headers) {
		if (options.headers instanceof Headers) {
			// If it's already a Headers object, copy all entries
			options.headers.forEach((value, key) => {
				headers.set(key, value);
			});
		} else if (Array.isArray(options.headers)) {
			// If it's an array of tuples
			options.headers.forEach(([key, value]) => {
				headers.set(key, value);
			});
		} else {
			// If it's a plain object
			Object.entries(options.headers).forEach(([key, value]) => {
				if (value !== null && value !== undefined) {
					headers.set(key, String(value));
				}
			});
		}
	}

	// Add Authorization header if not already present
	if (!headers.has("Authorization")) {
		const token = localStorage.getItem(TOKEN_KEY);
		if (token) {
			headers.set("Authorization", `Bearer ${token}`);
		}
	}

	const optionsWithAuth = {
		...options,
		headers: headers,
	};

	const response = await fetch(fullUrl, optionsWithAuth);

	// Handle 401 Unauthorized - token expired or invalid
	if (response.status === 401 && onUnauthorized) {
		console.warn(
			`401 Unauthorized on ${url}. Token may be expired or invalid.`,
		);
		onUnauthorized();
		// Redirect to login will be handled by ProtectedRoute
	}

	// Handle 403 Forbidden - email not verified or insufficient permissions
	// Log for debugging but don't auto-logout (user might need to verify email)
	if (response.status === 403) {
		const errorText = await response
			.clone()
			.text()
			.catch(() => "");
		console.warn(
			`403 Forbidden on ${url}. This may indicate email verification is required or insufficient permissions.`,
			errorText ? `Error: ${errorText}` : "",
		);
	}

	// Handle 404 Not Found - might indicate tenant not found or resource deleted
	if (response.status === 404) {
		const errorText = await response
			.clone()
			.text()
			.catch(() => "");
		console.warn(
			`404 Not Found on ${url}.`,
			errorText ? `Error: ${errorText}` : "",
		);
	}

	return response;
}

/**
 * Fetch with JSON response parsing and 401 handling
 * @param url - API endpoint URL
 * @param options - Fetch options
 * @param onUnauthorized - Callback when 401 is received
 * @returns Promise<T>
 */
export async function apiFetchJson<T>(
	url: string,
	options: RequestInit = {},
	onUnauthorized?: () => void,
): Promise<T> {
	const response = await apiFetch(url, options, onUnauthorized);

	if (!response.ok) {
		const msg = await parseApiError(response);
		throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
	}

	return response.json();
}
