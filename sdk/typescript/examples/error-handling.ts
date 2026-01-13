/**
 * Error Handling Example
 *
 * This example demonstrates how to handle different types of errors
 * that can occur when using the SDK.
 */

import {
	DbRevelAPIError,
	DbRevelClient,
	DbRevelNetworkError,
	DbRevelTimeoutError,
	DbRevelValidationError,
} from "../src";

async function main() {
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
		timeout: 5000, // 5 second timeout
	});

	try {
		await client.query("Get all users");
	} catch (error) {
		if (error instanceof DbRevelTimeoutError) {
			console.error("Request timed out:", error.message);
			console.error("Timeout was:", error.details?.timeout, "ms");
		} else if (error instanceof DbRevelAPIError) {
			console.error("API error:", error.message);
			console.error("Status code:", error.statusCode);
			console.error("Response:", error.response);

			// Handle specific status codes
			if (error.statusCode === 400) {
				console.error("Bad request - check your query");
			} else if (error.statusCode === 401) {
				console.error("Unauthorized - check your API key");
			} else if (error.statusCode === 404) {
				console.error("Not found - check the endpoint");
			} else if (error.statusCode >= 500) {
				console.error("Server error - try again later");
			}
		} else if (error instanceof DbRevelNetworkError) {
			console.error("Network error:", error.message);
			console.error("Original error:", error.details?.originalError);
			console.error("Check your internet connection and API URL");
		} else if (error instanceof DbRevelValidationError) {
			console.error("Validation error:", error.message);
			console.error("Details:", error.details);
		} else {
			console.error("Unknown error:", error);
		}
	}
}

main();
