/**
 * Interceptors Example
 *
 * This example demonstrates how to use request, response, and error interceptors
 * to customize SDK behavior.
 */

import {
	DbRevelClient,
	createErrorLogger,
	createRequestLogger,
	createResponseLogger,
} from "../src";

async function main() {
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
	});

	// Add logging interceptors
	client.useRequestInterceptor(createRequestLogger());
	client.useResponseInterceptor(createResponseLogger());
	client.useErrorInterceptor(createErrorLogger());

	// Custom request interceptor - add custom header
	client.useRequestInterceptor((config) => {
		return {
			...config,
			headers: {
				...config.headers,
				"X-Request-ID": `req-${Date.now()}`,
				"X-Client-Version": "1.0.0",
			},
		};
	});

	// Custom response interceptor - log response time
	client.useResponseInterceptor(async (response) => {
		const startTime = Date.now();
		const cloned = response.clone();
		await cloned.json(); // Consume body to measure time
		const duration = Date.now() - startTime;
		console.log(`Response processed in ${duration}ms`);
		return response;
	});

	// Custom error interceptor - add context
	client.useErrorInterceptor((error) => {
		console.error(`[${new Date().toISOString()}] Error:`, error.message);
		// You could send to error tracking service here
		return error;
	});

	try {
		const result = await client.query("Get all users");
		console.log("Query successful:", result.metadata.rows_returned, "rows");
	} catch (error) {
		console.error("Query failed after interceptors:", error);
	}
}

main();
