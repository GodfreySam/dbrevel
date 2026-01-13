/**
 * Interceptor types
 */

export interface RequestConfig {
	url: string;
	method: string;
	headers: HeadersInit;
	body?: BodyInit;
	signal?: AbortSignal;
	timeout?: number;
}

export type RequestInterceptor = (
	config: RequestConfig,
) => RequestConfig | Promise<RequestConfig>;

export type ResponseInterceptor = (
	response: Response,
) => Response | Promise<Response>;

export type ErrorInterceptor = (error: Error) => Error | Promise<Error>;
