/**
 * Retry Logic Example
 *
 * This example demonstrates how to configure automatic retries
 * with exponential backoff for handling transient failures.
 */

import { DbRevelClient } from "../src";

async function main() {
	// Configure client with retry logic
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
		retry: {
			maxRetries: 3, // Retry up to 3 times
			retryDelay: 1000, // Start with 1 second delay
			maxRetryDelay: 10000, // Cap at 10 seconds
			backoffMultiplier: 2, // Double delay each retry (1s, 2s, 4s)
			retryableStatusCodes: [500, 502, 503, 504], // Retry on these HTTP codes
			retryableErrorCodes: ["NETWORK_ERROR", "TIMEOUT"], // Retry on these errors
		},
	});

	try {
		// This request will automatically retry on network errors or 5xx status codes
		const result = await client.query("Get all users");
		console.log("Query successful:", result.metadata.rows_returned, "rows");
	} catch (error) {
		console.error("Query failed after retries:", error);
	}

	// Custom retry logic example
	const clientWithCustomRetry = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
		retry: {
			maxRetries: 5,
			retryDelay: 500,
			backoffMultiplier: 1.5,
			// Custom function to determine if request should be retried
			shouldRetry: (error, attempt) => {
				// Don't retry on 4xx errors (client errors)
				if (error instanceof Error && "statusCode" in error) {
					const statusCode = (error as any).statusCode;
					if (statusCode >= 400 && statusCode < 500) {
						return false;
					}
				}
				// Retry up to 5 times
				return attempt <= 5;
			},
		},
	});

	try {
		const result = await clientWithCustomRetry.query("Get all users");
		console.log("Query with custom retry successful");
	} catch (error) {
		console.error("Query failed:", error);
	}
}

main();
