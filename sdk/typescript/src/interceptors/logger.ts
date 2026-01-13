/**
 * Logging interceptor examples
 */
import type {
	ErrorInterceptor,
	RequestInterceptor,
	ResponseInterceptor,
} from "../types/interceptors";

export interface Logger {
	debug?(message: string, ...args: any[]): void;
	info?(message: string, ...args: any[]): void;
	warn?(message: string, ...args: any[]): void;
	error?(message: string, ...args: any[]): void;
}

/**
 * Create a request logging interceptor
 */
export function createRequestLogger(logger?: Logger): RequestInterceptor {
	const log = logger || console;
	return (config) => {
		if (log.debug) {
			log.debug(`[DbRevel] Request: ${config.method} ${config.url}`, {
				headers: config.headers,
				body: config.body,
			});
		}
		return config;
	};
}

/**
 * Create a response logging interceptor
 */
export function createResponseLogger(logger?: Logger): ResponseInterceptor {
	const log = logger || console;
	return async (response) => {
		if (log.debug) {
			const clonedResponse = response.clone();
			let body: any;
			try {
				body = await clonedResponse.json();
			} catch {
				body = await clonedResponse.text();
			}
			const headers: Record<string, string> = {};
			response.headers.forEach((value, key) => {
				headers[key] = value;
			});
			log.debug(
				`[DbRevel] Response: ${response.status} ${response.statusText}`,
				{
					headers,
					body,
				},
			);
		}
		return response;
	};
}

/**
 * Create an error logging interceptor
 */
export function createErrorLogger(logger?: Logger): ErrorInterceptor {
	const log = logger || console;
	return (error) => {
		if (log.error) {
			log.error(`[DbRevel] Error:`, error);
		}
		return error;
	};
}
