/**
 * Fetch wrapper with error handling
 */
import {
	DbRevelAPIError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
} from "../errors";

/**
 * Enhanced fetch wrapper that converts errors to DbRevel errors
 */
export async function dbRevelFetch(
	url: string,
	init: RequestInit & { timeout?: number },
): Promise<Response> {
	const timeout = init.timeout || 30000;
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeout);

	// Merge abort signals if provided
	if (init.signal) {
		init.signal.addEventListener("abort", () => controller.abort());
	}

	const signal = controller.signal;

	try {
		const response = await fetch(url, {
			...init,
			signal,
		});

		clearTimeout(timeoutId);
		return response;
	} catch (error) {
		clearTimeout(timeoutId);

		if (error instanceof Error) {
			if (error.name === "AbortError" || signal.aborted) {
				throw new DbRevelTimeoutError(timeout);
			}

			// Network errors (no internet, DNS failure, etc.)
			if (
				error.message.includes("fetch") ||
				error.message.includes("network") ||
				error.message.includes("Failed to fetch")
			) {
				throw new DbRevelNetworkError(`Network error: ${error.message}`, error);
			}
		}

		throw error;
	}
}

/**
 * Parse error response from API
 */
export async function parseErrorResponse(
	response: Response,
): Promise<DbRevelAPIError> {
	let errorBody: any;
	try {
		errorBody = await response.json();
	} catch {
		// If response is not JSON, use status text
		errorBody = { detail: response.statusText };
	}

	const message =
		errorBody?.detail || errorBody?.message || response.statusText;
	return new DbRevelAPIError(message, response.status, errorBody);
}
