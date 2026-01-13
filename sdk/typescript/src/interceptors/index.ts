/**
 * Interceptor utilities
 */
import type {
	ErrorInterceptor,
	RequestConfig,
	RequestInterceptor,
	ResponseInterceptor,
} from "../types/interceptors";

/**
 * Chain multiple request interceptors
 */
export async function chainRequestInterceptors(
	interceptors: RequestInterceptor[],
	config: RequestConfig,
): Promise<RequestConfig> {
	let result = config;
	for (const interceptor of interceptors) {
		result = await interceptor(result);
	}
	return result;
}

/**
 * Chain multiple response interceptors
 */
export async function chainResponseInterceptors(
	interceptors: ResponseInterceptor[],
	response: Response,
): Promise<Response> {
	let result = response;
	for (const interceptor of interceptors) {
		result = await interceptor(result);
	}
	return result;
}

/**
 * Chain multiple error interceptors
 */
export async function chainErrorInterceptors(
	interceptors: ErrorInterceptor[],
	error: Error,
): Promise<Error> {
	let result = error;
	for (const interceptor of interceptors) {
		result = await interceptor(result);
	}
	return result;
}
