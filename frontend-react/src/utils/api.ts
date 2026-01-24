/**
 * API utility functions with automatic 401 handling, retry logic, and better error messages
 */

import { config } from "../config";
import { parseApiError } from "./handleApiError";
import { withRetry, RetryOptions } from "./retry";
import { getUserFriendlyError } from "./errorMessages";
import * as Sentry from "@sentry/react";

const TOKEN_KEY = "dbrevel_auth_token";

/**
 * Fetch wrapper with retry logic and better error handling
 */
async function fetchWithRetry(
	url: string,
	options: RequestInit,
	retryOptions?: RetryOptions
): Promise<Response> {
	return withRetry(
		async () => {
			const controller = new AbortController();
			const timeoutId = setTimeout(() => {
				controller.abort();
			}, config.timeout);

			try {
				const response = await fetch(url, {
					...options,
					signal: controller.signal,
				});
				clearTimeout(timeoutId);
				return response;
			} catch (error: any) {
				clearTimeout(timeoutId);
				if (error.name === "AbortError") {
					const timeoutError = new Error(
						`Request timeout: The server did not respond within ${config.timeout / 1000} seconds`
					) as any;
					timeoutError.status = 408;
					throw timeoutError;
				}
				throw error;
			}
		},
		{
			maxRetries: 3,
			initialDelay: 1000,
			maxDelay: 10000,
			retryableStatuses: [408, 429, 500, 502, 503, 504],
			...retryOptions,
		}
	);
}

/**
 * Fetch wrapper that automatically handles 401 errors by logging out
 */
export async function apiFetch(
	url: string,
	options: RequestInit = {},
	onUnauthorized?: () => void,
): Promise<Response> {
	const fullUrl = url.startsWith("http") ? url : `${config.apiUrl}${url}`;

	const headers = new Headers();
	if (options.headers) {
		if (options.headers instanceof Headers) {
			options.headers.forEach((value, key) => {
				headers.set(key, value);
			});
		} else if (Array.isArray(options.headers)) {
			options.headers.forEach(([key, value]) => {
				headers.set(key, value);
			});
		} else {
			Object.entries(options.headers).forEach(([key, value]) => {
				if (value !== null && value !== undefined) {
					headers.set(key, String(value));
				}
			});
		}
	}

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

	let response: Response;
	try {
		response = await fetchWithRetry(fullUrl, optionsWithAuth);
	} catch (error: any) {
		if (import.meta.env.VITE_SENTRY_DSN) {
			Sentry.captureException(error, {
				tags: { component: "apiFetch" },
				extra: { url: fullUrl, method: options.method },
			});
		}
		throw error;
	}

	if (response.status === 401 && onUnauthorized) {
		onUnauthorized();
	}

	if (!response.ok && import.meta.env.VITE_SENTRY_DSN) {
		const errorText = await response.clone().text().catch(() => "");
		Sentry.captureMessage(`API Error: ${response.status}`, {
			level: response.status >= 500 ? "error" : "warning",
			tags: { status: response.status, url: fullUrl },
			extra: { errorText, method: options.method },
		});
	}

	return response;
}

/**
 * Fetch with JSON response parsing, retry logic, and user-friendly error messages
 */
export async function apiFetchJson<T>(
	url: string,
	options: RequestInit = {},
	onUnauthorized?: () => void,
): Promise<T> {
	try {
		const response = await apiFetch(url, options, onUnauthorized);

		if (!response.ok) {
			const errorText = await parseApiError(response);
			const friendlyError = getUserFriendlyError(errorText);
			
			const error = new Error(friendlyError.message) as any;
			error.status = response.status;
			error.category = friendlyError.category;
			error.originalMessage = errorText;
			throw error;
		}

		return response.json();
	} catch (error: any) {
		if (error.category) {
			throw error;
		}

		const friendlyError = getUserFriendlyError(error);
		const formattedError = new Error(friendlyError.message) as any;
		formattedError.status = error.status || 0;
		formattedError.category = friendlyError.category;
		formattedError.originalMessage = error.message;
		throw formattedError;
	}
}
