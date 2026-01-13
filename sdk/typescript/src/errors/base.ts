/**
 * Base error classes for DbRevel SDK
 */

export class DbRevelError extends Error {
	public readonly code: string;
	public readonly statusCode?: number;
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

export class DbRevelTimeoutError extends DbRevelError {
	constructor(timeout: number) {
		super(`Request timeout after ${timeout}ms`, "TIMEOUT", undefined, {
			timeout,
		});
		this.name = "DbRevelTimeoutError";
	}
}

export class DbRevelAPIError extends DbRevelError {
	public readonly response?: any;

	constructor(message: string, statusCode: number, response?: any) {
		super(message, "API_ERROR", statusCode, response);
		this.name = "DbRevelAPIError";
		this.response = response;
	}
}

export class DbRevelValidationError extends DbRevelError {
	constructor(message: string, details?: any) {
		super(message, "VALIDATION_ERROR", undefined, details);
		this.name = "DbRevelValidationError";
	}
}

export class DbRevelNetworkError extends DbRevelError {
	constructor(message: string, originalError?: Error) {
		super(message, "NETWORK_ERROR", undefined, {
			originalError: originalError?.message,
		});
		this.name = "DbRevelNetworkError";
	}
}
