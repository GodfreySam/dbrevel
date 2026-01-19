/**
 * Error classes for DbRevel SDK
 *
 * All SDK errors extend from DbRevelError, allowing you to catch
 * all SDK errors with a single catch block, or catch specific
 * error types for more granular handling.
 *
 * @packageDocumentation
 *
 * @example
 * ```typescript
 * try {
 *   const result = await client.query("Get all users");
 * } catch (error) {
 *   if (error instanceof DbRevelTimeoutError) {
 *     console.log("Request timed out, try again");
 *   } else if (error instanceof DbRevelAPIError) {
 *     console.log(`API error ${error.statusCode}: ${error.message}`);
 *   } else if (error instanceof DbRevelNetworkError) {
 *     console.log("Network error, check your connection");
 *   } else if (error instanceof DbRevelValidationError) {
 *     console.log("Invalid response from server");
 *   } else if (error instanceof DbRevelError) {
 *     console.log(`SDK error: ${error.code}`);
 *   }
 * }
 * ```
 */

/**
 * Base error class for all DbRevel SDK errors
 *
 * All specific error types extend this class, allowing you to:
 * - Catch all SDK errors with `catch (e) { if (e instanceof DbRevelError) }`
 * - Access common properties like `code`, `statusCode`, and `details`
 *
 * @example
 * ```typescript
 * try {
 *   await client.query("...");
 * } catch (error) {
 *   if (error instanceof DbRevelError) {
 *     console.log(`Error code: ${error.code}`);
 *     console.log(`Details: ${JSON.stringify(error.details)}`);
 *   }
 * }
 * ```
 */
export class DbRevelError extends Error {
	/** Error code identifying the type of error (e.g., "TIMEOUT", "API_ERROR") */
	public readonly code: string;
	/** HTTP status code if this was an API error */
	public readonly statusCode?: number;
	/** Additional error details (varies by error type) */
	public readonly details?: any;

	constructor(
		message: string,
		code: string,
		statusCode?: number,
		details?: any,
	) {
		super(message);
		this.name = "DbRevelError";
		this.code = code;
		this.statusCode = statusCode;
		this.details = details;

		// Maintains proper stack trace for where our error was thrown (only available on V8)
		if (Error.captureStackTrace) {
			Error.captureStackTrace(this, this.constructor);
		}
	}
}

/**
 * Error thrown when a request times out
 *
 * This error is retryable by default when using retry configuration.
 *
 * @example
 * ```typescript
 * try {
 *   await client.query("Complex aggregation query");
 * } catch (error) {
 *   if (error instanceof DbRevelTimeoutError) {
 *     console.log(`Request timed out after ${error.details.timeout}ms`);
 *   }
 * }
 * ```
 */
export class DbRevelTimeoutError extends DbRevelError {
	constructor(timeout: number) {
		super(`Request timeout after ${timeout}ms`, "TIMEOUT", undefined, {
			timeout,
		});
		this.name = "DbRevelTimeoutError";
	}
}

/**
 * Error thrown when the API returns an error response (4xx or 5xx)
 *
 * Common status codes:
 * - 400: Bad request (invalid query or parameters)
 * - 401: Unauthorized (invalid or missing API key)
 * - 403: Forbidden (insufficient permissions)
 * - 404: Not found (database or resource not found)
 * - 429: Rate limited (too many requests)
 * - 500+: Server errors (retryable)
 *
 * @example
 * ```typescript
 * try {
 *   await client.query("...");
 * } catch (error) {
 *   if (error instanceof DbRevelAPIError) {
 *     if (error.statusCode === 429) {
 *       console.log("Rate limited, please slow down");
 *     } else if (error.statusCode >= 500) {
 *       console.log("Server error, try again later");
 *     }
 *     console.log("Response:", error.response);
 *   }
 * }
 * ```
 */
export class DbRevelAPIError extends DbRevelError {
	/** Raw response body from the API */
	public readonly response?: any;

	constructor(message: string, statusCode: number, response?: any) {
		super(message, "API_ERROR", statusCode, response);
		this.name = "DbRevelAPIError";
		this.response = response;
	}
}

/**
 * Error thrown when response validation fails
 *
 * This typically indicates an unexpected response format from the API,
 * which could be due to API version mismatch or server issues.
 *
 * @example
 * ```typescript
 * try {
 *   await client.query("...");
 * } catch (error) {
 *   if (error instanceof DbRevelValidationError) {
 *     console.log("Invalid response:", error.details);
 *   }
 * }
 * ```
 */
export class DbRevelValidationError extends DbRevelError {
	constructor(message: string, details?: any) {
		super(message, "VALIDATION_ERROR", undefined, details);
		this.name = "DbRevelValidationError";
	}
}

/**
 * Error thrown when a network request fails
 *
 * This includes DNS resolution failures, connection refused,
 * SSL/TLS errors, and other network-level issues.
 * This error is retryable by default when using retry configuration.
 *
 * @example
 * ```typescript
 * try {
 *   await client.query("...");
 * } catch (error) {
 *   if (error instanceof DbRevelNetworkError) {
 *     console.log("Network error:", error.message);
 *     console.log("Original error:", error.details.originalError);
 *   }
 * }
 * ```
 */
export class DbRevelNetworkError extends DbRevelError {
	constructor(message: string, originalError?: Error) {
		super(message, "NETWORK_ERROR", undefined, {
			originalError: originalError?.message,
		});
		this.name = "DbRevelNetworkError";
	}
}
