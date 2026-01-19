/**
 * Interceptor types for request/response middleware
 * @packageDocumentation
 */

/**
 * Configuration object passed to request interceptors
 *
 * @example
 * ```typescript
 * client.useRequestInterceptor((config: RequestConfig) => {
 *   console.log(`${config.method} ${config.url}`);
 *   return {
 *     ...config,
 *     headers: { ...config.headers, "X-Custom": "value" }
 *   };
 * });
 * ```
 */
export interface RequestConfig {
	/** Full URL of the request */
	url: string;
	/** HTTP method (GET, POST, etc.) */
	method: string;
	/** Request headers */
	headers: HeadersInit;
	/** Request body (for POST/PATCH requests) */
	body?: BodyInit;
	/** AbortSignal for request cancellation */
	signal?: AbortSignal;
	/** Request timeout in milliseconds */
	timeout?: number;
}

/**
 * Function that intercepts and optionally modifies outgoing requests
 *
 * Request interceptors are called before each API request, allowing you to:
 * - Add custom headers (authentication, tracing)
 * - Log request details
 * - Modify the request URL or body
 *
 * @param config - The request configuration to intercept
 * @returns Modified config (sync or async)
 *
 * @example
 * ```typescript
 * // Add request timing
 * const timingInterceptor: RequestInterceptor = (config) => {
 *   console.log(`Request started: ${config.url}`);
 *   return config;
 * };
 *
 * client.useRequestInterceptor(timingInterceptor);
 * ```
 */
export type RequestInterceptor = (
	config: RequestConfig,
) => RequestConfig | Promise<RequestConfig>;

/**
 * Function that intercepts and optionally modifies incoming responses
 *
 * Response interceptors are called after each successful API response, allowing you to:
 * - Log response details
 * - Transform response data
 * - Add custom response handling
 *
 * @param response - The Response object to intercept
 * @returns Modified response (sync or async)
 *
 * @example
 * ```typescript
 * // Log response timing
 * const responseLogger: ResponseInterceptor = (response) => {
 *   console.log(`Response: ${response.status} ${response.statusText}`);
 *   return response;
 * };
 *
 * client.useResponseInterceptor(responseLogger);
 * ```
 */
export type ResponseInterceptor = (
	response: Response,
) => Response | Promise<Response>;

/**
 * Function that intercepts and optionally modifies errors
 *
 * Error interceptors are called when a request fails, allowing you to:
 * - Log errors to external services
 * - Transform error messages
 * - Add context to errors
 *
 * @param error - The error to intercept
 * @returns Modified error (sync or async)
 *
 * @example
 * ```typescript
 * // Log errors to monitoring service
 * const errorLogger: ErrorInterceptor = (error) => {
 *   Sentry.captureException(error);
 *   return error;
 * };
 *
 * client.useErrorInterceptor(errorLogger);
 * ```
 */
export type ErrorInterceptor = (error: Error) => Error | Promise<Error>;
