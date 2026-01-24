/**
 * User-friendly error message mapping
 */

export interface ErrorMapping {
	pattern: RegExp | string;
	message: string;
	category: "network" | "auth" | "validation" | "server" | "unknown";
}

const ERROR_MAPPINGS: ErrorMapping[] = [
	// Network errors
	{
		pattern: /network error|failed to fetch|network request failed/i,
		message:
			"Network error. Please check your internet connection and try again.",
		category: "network",
	},
	{
		pattern: /timeout|timed out/i,
		message:
			"Request timed out. The server is taking too long to respond. Please try again.",
		category: "network",
	},
	{
		pattern: /cors|cross-origin/i,
		message: "CORS error. Please contact support if this persists.",
		category: "network",
	},

	// Authentication errors
	{
		pattern: /401|unauthorized|invalid.*token|token.*expired/i,
		message: "Your session has expired. Please log in again.",
		category: "auth",
	},
	{
		pattern: /403|forbidden|email.*verified/i,
		message:
			"Access denied. Please verify your email address or contact support.",
		category: "auth",
	},
	{
		pattern: /incorrect.*password|invalid.*credentials/i,
		message: "Incorrect email or password. Please try again.",
		category: "auth",
	},

	// Validation errors
	{
		pattern: /422|validation|invalid.*input/i,
		message: "Invalid input. Please check your data and try again.",
		category: "validation",
	},
	{
		pattern: /email.*already.*exists|user.*already.*exists/i,
		message:
			"An account with this email already exists. Please log in instead.",
		category: "validation",
	},

	// Server errors
	{
		pattern: /500|internal.*server.*error/i,
		message:
			"Server error. Our team has been notified. Please try again later.",
		category: "server",
	},
	{
		pattern: /503|service.*unavailable/i,
		message:
			"Service temporarily unavailable. Please try again in a few moments.",
		category: "server",
	},
	{
		pattern: /429|rate.*limit|too.*many.*requests/i,
		message: "Too many requests. Please wait a moment and try again.",
		category: "server",
	},

	// Database errors
	{
		pattern: /database|connection.*failed|db.*error/i,
		message: "Database connection error. Please try again or contact support.",
		category: "server",
	},

	// Query errors
	{
		pattern: /query.*failed|invalid.*query/i,
		message: "Query execution failed. Please check your query and try again.",
		category: "validation",
	},
];

/**
 * Get user-friendly error message from error
 */
export function getUserFriendlyError(error: string | Error): {
	message: string;
	category: ErrorMapping["category"];
} {
	const errorStr =
		typeof error === "string" ? error : error.message || error.toString();

	// Find matching error mapping
	for (const mapping of ERROR_MAPPINGS) {
		const pattern =
			mapping.pattern instanceof RegExp
				? mapping.pattern
				: new RegExp(mapping.pattern, "i");
		if (pattern.test(errorStr)) {
			return {
				message: mapping.message,
				category: mapping.category,
			};
		}
	}

	// Default message
	return {
		message:
			"An unexpected error occurred. Please try again or contact support.",
		category: "unknown",
	};
}
