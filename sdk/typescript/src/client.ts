/**
 * DbRevel Client - Main SDK class
 */
import { DbRevelAPIError } from "./errors";
import {
	chainErrorInterceptors,
	chainRequestInterceptors,
	chainResponseInterceptors,
} from "./interceptors";
import type {
	DbRevelConfig,
	ErrorInterceptor,
	HealthResponse,
	QueryOptions,
	QueryResult,
	RequestConfig,
	RequestInterceptor,
	ResponseInterceptor,
	RetryConfig,
	SchemasResponse,
} from "./types";
import {
	dbRevelFetch,
	parseErrorResponse,
	validateHealthResponse,
	validateQueryResult,
	validateSchemasResponse,
} from "./utils";
import { withRetry } from "./utils/retry";

export class DbRevelClient {
	private baseUrl: string;
	private apiKey: string;
	private timeout: number;
	private retryConfig?: RetryConfig;
	private requestInterceptors: RequestInterceptor[] = [];
	private responseInterceptors: ResponseInterceptor[] = [];
	private errorInterceptors: ErrorInterceptor[] = [];

	constructor(config: DbRevelConfig) {
		this.baseUrl = config.baseUrl.replace(/\/$/, ""); // Remove trailing slash
		this.apiKey = config.apiKey;
		this.timeout = config.timeout || 30000;
		this.retryConfig = config.retry;
	}

	/**
	 * Execute a natural language database query
	 *
	 * @example
	 * ```typescript
	 * const result = await client.query("Get all users from Lagos");
	 * console.log(result.data); // Array of user objects
	 * ```
	 *
	 * @param intent - Natural language query description
	 * @param options - Query options (dry run, context, cancellation)
	 * @returns Promise resolving to query results with metadata
	 * @throws {DbRevelAPIError} When API returns an error
	 * @throws {DbRevelTimeoutError} When request times out
	 * @throws {DbRevelNetworkError} When network request fails
	 */
	async query<T = any>(
		intent: string,
		options?: QueryOptions,
	): Promise<QueryResult<T>> {
		if (!intent || typeof intent !== "string" || intent.trim().length === 0) {
			throw new Error("Intent must be a non-empty string");
		}

		return this.executeRequest<QueryResult<T>>(
			"/api/v1/query",
			{
				method: "POST",
				body: JSON.stringify({
					intent: intent.trim(),
					dry_run: options?.dryRun ?? false,
					context: options?.context,
				}),
				timeout: this.timeout,
				signal: options?.signal,
			},
			validateQueryResult<T>,
		);
	}

	/**
	 * Get database schemas for all connected databases
	 *
	 * @example
	 * ```typescript
	 * const schemas = await client.getSchemas();
	 * console.log(schemas.databases.postgres.tables);
	 * ```
	 *
	 * @returns Promise resolving to all database schemas
	 * @throws {DbRevelAPIError} When API returns an error
	 * @throws {DbRevelTimeoutError} When request times out
	 */
	async getSchemas(): Promise<SchemasResponse> {
		return this.executeRequest<SchemasResponse>(
			"/api/v1/schema",
			{
				method: "GET",
				timeout: this.timeout,
			},
			validateSchemasResponse,
		);
	}

	/**
	 * Get schema for a specific database
	 *
	 * @example
	 * ```typescript
	 * const schema = await client.getSchema("postgres");
	 * console.log(schema.tables);
	 * ```
	 *
	 * @param databaseName - Name of the database
	 * @returns Promise resolving to database schema
	 * @throws {DbRevelAPIError} When API returns an error or database not found
	 * @throws {DbRevelTimeoutError} When request times out
	 */
	async getSchema(
		databaseName: string,
	): Promise<SchemasResponse["databases"][string]> {
		if (!databaseName || typeof databaseName !== "string") {
			throw new Error("Database name must be a non-empty string");
		}

		return this.executeRequest<SchemasResponse["databases"][string]>(
			`/api/v1/schema/${encodeURIComponent(databaseName)}`,
			{
				method: "GET",
				timeout: this.timeout,
			},
		);
	}

	/**
	 * Get a SchemaHelper instance for convenient schema operations
	 *
	 * @example
	 * ```typescript
	 * const schemas = await client.getSchemas();
	 * const helper = client.getSchemaHelper(schemas);
	 * const tableNames = helper.getTableNames("postgres");
	 * const usersTable = helper.getTable("postgres", "users");
	 * ```
	 *
	 * @param schemas - Schemas response (from getSchemas())
	 * @returns SchemaHelper instance
	 */
	getSchemaHelper(
		schemas: SchemasResponse,
	): import("./schema-helper").SchemaHelper {
		const { SchemaHelper } = require("./schema-helper");
		return new SchemaHelper(schemas);
	}

	/**
	 * Health check - verify API and database connectivity
	 *
	 * @example
	 * ```typescript
	 * const health = await client.health();
	 * console.log(health.status); // "healthy"
	 * console.log(health.databases); // { postgres: "connected", mongodb: "connected" }
	 * ```
	 *
	 * @returns Promise resolving to health status
	 * @throws {DbRevelAPIError} When API returns an error
	 * @throws {DbRevelTimeoutError} When request times out
	 */
	async health(): Promise<HealthResponse> {
		return this.executeRequest<HealthResponse>(
			"/health",
			{
				method: "GET",
				timeout: this.timeout,
			},
			validateHealthResponse,
		);
	}

	/**
	 * Add a request interceptor
	 * @param interceptor - Function to intercept and modify requests
	 */
	useRequestInterceptor(interceptor: RequestInterceptor): void {
		this.requestInterceptors.push(interceptor);
	}

	/**
	 * Add a response interceptor
	 * @param interceptor - Function to intercept and modify responses
	 */
	useResponseInterceptor(interceptor: ResponseInterceptor): void {
		this.responseInterceptors.push(interceptor);
	}

	/**
	 * Add an error interceptor
	 * @param interceptor - Function to intercept and modify errors
	 */
	useErrorInterceptor(interceptor: ErrorInterceptor): void {
		this.errorInterceptors.push(interceptor);
	}

	/**
	 * Remove all interceptors
	 */
	clearInterceptors(): void {
		this.requestInterceptors = [];
		this.responseInterceptors = [];
		this.errorInterceptors = [];
	}

	/**
	 * Internal method to execute a request with interceptors and retry
	 */
	private async executeRequest<T>(
		path: string,
		init: RequestInit & { timeout?: number; signal?: AbortSignal },
		validator?: (data: any) => T,
	): Promise<T> {
		const requestConfig: RequestConfig = {
			url: `${this.baseUrl}${path}`,
			method: init.method || "GET",
			headers: this.getHeaders(),
			body: init.body ?? undefined,
			signal: init.signal,
			timeout: init.timeout || this.timeout,
		};

		const execute = async (): Promise<T> => {
			// Apply request interceptors
			const finalConfig = await chainRequestInterceptors(
				this.requestInterceptors,
				requestConfig,
			);

			// Make the request
			let response: Response;
			try {
				response = await dbRevelFetch(finalConfig.url, {
					method: finalConfig.method,
					headers: finalConfig.headers,
					body: finalConfig.body,
					timeout: finalConfig.timeout,
					signal: finalConfig.signal,
				});
			} catch (error) {
				// Apply error interceptors
				const processedError = await chainErrorInterceptors(
					this.errorInterceptors,
					error instanceof Error ? error : new Error(String(error)),
				);
				throw processedError;
			}

			// Apply response interceptors
			response = await chainResponseInterceptors(
				this.responseInterceptors,
				response,
			);

			// Handle error responses
			if (!response.ok) {
				const apiError = await parseErrorResponse(response);
				const processedError = await chainErrorInterceptors(
					this.errorInterceptors,
					apiError,
				);
				throw processedError;
			}

			// Parse and validate response
			const data = await response.json();
			return validator ? validator(data) : (data as T);
		};

		// Apply retry logic if configured
		if (this.retryConfig) {
			return withRetry(execute, this.retryConfig);
		}

		return execute();
	}

	/**
	 * Test database connections
	 *
	 * Tests PostgreSQL and/or MongoDB connections and returns connection status
	 * and schema preview. Does not save the URLs - use updateDatabases() to save.
	 *
	 * @param postgresUrl - PostgreSQL connection URL to test (optional)
	 * @param mongodbUrl - MongoDB connection URL to test (optional)
	 * @returns Connection test results for each database
	 *
	 * @example
	 * ```typescript
	 * const result = await client.testConnection(
	 *   "postgresql://user:pass@host:5432/db",
	 *   "mongodb://host:27017/db"
	 * );
	 * console.log(result.postgres?.success); // true if connection successful
	 * ```
	 */
	async testConnection(
		postgresUrl?: string,
		mongodbUrl?: string,
	): Promise<{
		postgres?: {
			success: boolean;
			error?: string;
			schema_preview?: any;
		};
		mongodb?: {
			success: boolean;
			error?: string;
			schema_preview?: any;
		};
	}> {
		if (!postgresUrl && !mongodbUrl) {
			throw new Error("At least one database URL is required");
		}

		return this.executeRequest("/tenants/me/test-connection", {
			method: "POST",
			body: JSON.stringify({
				postgres_url: postgresUrl || null,
				mongodb_url: mongodbUrl || null,
			}),
		});
	}

	/**
	 * Update database connection URLs
	 *
	 * Updates your tenant's database connection URLs. This will invalidate
	 * existing database adapters and re-initialize them with the new URLs
	 * on the next query.
	 *
	 * @param postgresUrl - New PostgreSQL connection URL (optional)
	 * @param mongodbUrl - New MongoDB connection URL (optional)
	 * @returns Updated tenant information
	 *
	 * @example
	 * ```typescript
	 * const tenant = await client.updateDatabases(
	 *   "postgresql://user:pass@host:5432/newdb",
	 *   "mongodb://host:27017/newdb"
	 * );
	 * console.log(tenant.name); // Your tenant name
	 * ```
	 */
	async updateDatabases(
		postgresUrl?: string,
		mongodbUrl?: string,
	): Promise<{
		id: string;
		name: string;
		api_key: string;
		postgres_url: string;
		mongodb_url: string;
		gemini_mode: string;
		gemini_api_key?: string;
	}> {
		if (!postgresUrl && !mongodbUrl) {
			throw new Error("At least one database URL must be provided");
		}

		return this.executeRequest("/tenants/me/databases", {
			method: "PATCH",
			body: JSON.stringify({
				postgres_url: postgresUrl || null,
				mongodb_url: mongodbUrl || null,
			}),
		});
	}

	/**
	 * Get default headers for API requests
	 */
	private getHeaders(): HeadersInit {
		return {
			"Content-Type": "application/json",
			"X-Project-Key": this.apiKey,
		};
	}
}
