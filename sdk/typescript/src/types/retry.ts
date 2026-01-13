/**
 * Retry configuration types
 */

export interface RetryConfig {
	/**
	 * Maximum number of retry attempts (default: 3)
	 */
	maxRetries?: number;

	/**
	 * Initial delay in milliseconds before first retry (default: 1000)
	 */
	retryDelay?: number;

	/**
	 * Maximum delay in milliseconds between retries (default: 10000)
	 */
	maxRetryDelay?: number;

	/**
	 * Exponential backoff multiplier (default: 2)
	 */
	backoffMultiplier?: number;

	/**
	 * HTTP status codes that should trigger a retry (default: [500, 502, 503, 504])
	 */
	retryableStatusCodes?: number[];

	/**
	 * Error codes that should trigger a retry (default: ['NETWORK_ERROR', 'TIMEOUT'])
	 */
	retryableErrorCodes?: string[];

	/**
	 * Custom function to determine if a request should be retried
	 */
	shouldRetry?: (error: Error, attempt: number) => boolean;
}

export const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
	maxRetries: 3,
	retryDelay: 1000,
	maxRetryDelay: 10000,
	backoffMultiplier: 2,
	retryableStatusCodes: [500, 502, 503, 504],
	retryableErrorCodes: ["NETWORK_ERROR", "TIMEOUT"],
	shouldRetry: () => true,
};
