/**
 * Configuration types for DbRevel client
 * @packageDocumentation
 */
import type { RetryConfig } from "./retry";

/**
 * Configuration options for initializing the DbRevel client
 *
 * @example
 * ```typescript
 * const client = new DbRevelClient({
 *   baseUrl: "https://api.dbrevel.com",
 *   apiKey: "your-project-api-key",
 *   timeout: 30000,
 *   retry: {
 *     maxRetries: 3,
 *     retryDelay: 1000
 *   }
 * });
 * ```
 */
export interface DbRevelConfig {
	/**
	 * Base URL of the DbRevel API
	 * @example "https://api.dbrevel.com" or "http://localhost:8000"
	 */
	baseUrl: string;

	/**
	 * Project API key for authentication
	 * Sent as `X-Project-Key` header with each request
	 */
	apiKey: string;

	/**
	 * Request timeout in milliseconds
	 * @default 30000 (30 seconds)
	 */
	timeout?: number;

	/**
	 * Retry configuration for automatic retries on transient failures
	 * @see RetryConfig
	 */
	retry?: RetryConfig;
}

/**
 * Options for query execution
 *
 * @example
 * ```typescript
 * // Dry run to see query plan without execution
 * const plan = await client.query("Get users", { dryRun: true });
 *
 * // With context for row-level security
 * const result = await client.query("Get my orders", {
 *   context: { userId: 123 }
 * });
 *
 * // With cancellation support
 * const controller = new AbortController();
 * const result = await client.query("Get all users", {
 *   signal: controller.signal
 * });
 * // Later: controller.abort();
 * ```
 */
export interface QueryOptions {
	/**
	 * When true, returns the query plan without executing the query
	 * Useful for previewing what the AI will do before running it
	 * @default false
	 */
	dryRun?: boolean;

	/**
	 * Context object for row-level security and query customization
	 * Passed to the AI for filtering results based on user permissions
	 */
	context?: Record<string, any>;

	/**
	 * AbortSignal for request cancellation
	 * Use with AbortController to cancel long-running queries
	 */
	signal?: AbortSignal;
}
