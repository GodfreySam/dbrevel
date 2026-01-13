/**
 * DbRevel SDK - TypeScript Client
 * AI-Powered Universal Database Queries
 *
 * @packageDocumentation
 */

// Export client
export { DbRevelClient } from "./client";
export type { DbRevelConfig, QueryOptions } from "./types";

// Export types
export type {
	CollectionSchema,
	ColumnSchema,
	DatabaseQuery,
	DatabaseSchema,
	ErrorInterceptor,
	HealthResponse,
	QueryMetadata,
	QueryPlan,
	QueryResult,
	RequestInterceptor,
	ResponseInterceptor,
	RetryConfig,
	SchemasResponse,
	TableSchema,
} from "./types";

// Export errors
export {
	DbRevelAPIError,
	DbRevelError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
	DbRevelValidationError,
} from "./errors";

// Export interceptors
export {
	createErrorLogger,
	createRequestLogger,
	createResponseLogger,
} from "./interceptors/logger";
export type { Logger } from "./interceptors/logger";

// Export schema utilities
export { SchemaHelper } from "./schema-helper";
export * from "./utils/schema";

// Default export
import { DbRevelClient } from "./client";
export default DbRevelClient;
