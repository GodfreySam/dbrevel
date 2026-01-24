/**
 * Retry utility with exponential backoff
 */

export interface RetryOptions {
	maxRetries?: number;
	initialDelay?: number;
	maxDelay?: number;
	backoffFactor?: number;
	retryableStatuses?: number[];
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
	maxRetries: 3,
	initialDelay: 1000, // 1 second
	maxDelay: 10000, // 10 seconds
	backoffFactor: 2,
	retryableStatuses: [408, 429, 500, 502, 503, 504], // Timeout, rate limit, server errors
};

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable based on status code
 */
function isRetryable(status: number, retryableStatuses: number[]): boolean {
	return retryableStatuses.includes(status);
}

/**
 * Retry a function with exponential backoff
 */
export async function withRetry<T>(
	fn: () => Promise<T>,
	options: RetryOptions = {},
): Promise<T> {
	const opts = { ...DEFAULT_RETRY_OPTIONS, ...options };
	let lastError: Error | null = null;
	let delay = opts.initialDelay;

	for (let attempt = 0; attempt <= opts.maxRetries; attempt++) {
		try {
			return await fn();
		} catch (error: any) {
			lastError = error;

			// Don't retry on last attempt
			if (attempt === opts.maxRetries) {
				break;
			}

			// Check if error is retryable
			const status = error.status || error.response?.status;
			if (status && !isRetryable(status, opts.retryableStatuses)) {
				// Not a retryable error, throw immediately
				throw error;
			}

			// Wait before retrying
			await sleep(delay);
			delay = Math.min(delay * opts.backoffFactor, opts.maxDelay);
		}
	}

	// All retries exhausted
	if (lastError) {
		throw lastError;
	}

	throw new Error("Retry exhausted without error");
}
