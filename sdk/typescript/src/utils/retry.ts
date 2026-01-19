/**
 * Retry logic with exponential backoff
 */
import {
	DbRevelAPIError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
} from "../errors";
import type { RetryConfig } from "../types/retry";

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate delay for retry attempt with exponential backoff
 */
function calculateRetryDelay(
	attempt: number,
	config: Required<RetryConfig>,
): number {
	const delay =
		config.retryDelay * Math.pow(config.backoffMultiplier, attempt - 1);
	return Math.min(delay, config.maxRetryDelay);
}

/**
 * Check if error should trigger a retry
 */
function shouldRetry(
	error: Error,
	attempt: number,
	config: Required<RetryConfig>,
): boolean {
	// Check if max retries exceeded
	if (attempt > config.maxRetries) {
		return false;
	}

	// Check custom shouldRetry function - if provided and returns true, allow retry
	if (config.shouldRetry) {
		const customResult = config.shouldRetry(error, attempt);
		if (!customResult) {
			return false;
		}
		// If custom function returns true for a non-standard error, allow retry
		if (
			!(error instanceof DbRevelNetworkError) &&
			!(error instanceof DbRevelTimeoutError) &&
			!(error instanceof DbRevelAPIError)
		) {
			return true;
		}
	}

	// Check error codes
	if (error instanceof DbRevelNetworkError) {
		return config.retryableErrorCodes.includes("NETWORK_ERROR");
	}

	if (error instanceof DbRevelTimeoutError) {
		return config.retryableErrorCodes.includes("TIMEOUT");
	}

	// Check API error status codes
	if (error instanceof DbRevelAPIError && error.statusCode) {
		return config.retryableStatusCodes.includes(error.statusCode);
	}

	return false;
}

/**
 * Execute a function with retry logic
 */
export async function withRetry<T>(
	fn: () => Promise<T>,
	config: RetryConfig = {},
): Promise<T> {
	const retryConfig: Required<RetryConfig> = {
		maxRetries: config.maxRetries ?? 3,
		retryDelay: config.retryDelay ?? 1000,
		maxRetryDelay: config.maxRetryDelay ?? 10000,
		backoffMultiplier: config.backoffMultiplier ?? 2,
		retryableStatusCodes: config.retryableStatusCodes ?? [500, 502, 503, 504],
		retryableErrorCodes: config.retryableErrorCodes ?? [
			"NETWORK_ERROR",
			"TIMEOUT",
		],
		shouldRetry: config.shouldRetry ?? (() => true),
	};

	let lastError: Error;
	let attempt = 0;

	while (attempt <= retryConfig.maxRetries) {
		try {
			return await fn();
		} catch (error) {
			lastError = error instanceof Error ? error : new Error(String(error));
			attempt++;

			if (!shouldRetry(lastError, attempt, retryConfig)) {
				throw lastError;
			}

			// Wait before retrying (skip delay on first attempt)
			if (attempt <= retryConfig.maxRetries) {
				const delay = calculateRetryDelay(attempt, retryConfig);
				await sleep(delay);
			}
		}
	}

	throw lastError!;
}
