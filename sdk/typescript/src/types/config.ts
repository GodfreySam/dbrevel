/**
 * Configuration types
 */
import type { RetryConfig } from "./retry";

export interface DbRevelConfig {
	/** Base URL of the DbRevel API */
	baseUrl: string;
	/** Project API key for authentication (sent as X-Project-Key header) */
	apiKey: string;
	/** Request timeout in milliseconds (default: 30000) */
	timeout?: number;
	/** Retry configuration for automatic retries */
	retry?: RetryConfig;
}

export interface QueryOptions {
	dryRun?: boolean;
	context?: Record<string, any>;
	signal?: AbortSignal;
}
