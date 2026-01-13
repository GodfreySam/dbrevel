/**
 * Basic Query Example
 *
 * This example demonstrates how to execute a simple natural language query.
 */

import { DbRevelClient } from "../src";

async function main() {
	// Initialize the client
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
	});

	try {
		// Execute a simple query
		const result = await client.query("Get all users from Lagos");

		console.log("Query Results:");
		console.log(`- Rows returned: ${result.metadata.rows_returned}`);
		console.log(`- Execution time: ${result.metadata.execution_time_ms}ms`);
		console.log(`- Trace ID: ${result.metadata.trace_id}`);
		console.log("\nData:");
		console.log(JSON.stringify(result.data, null, 2));

		// Access the generated query plan
		console.log("\nGenerated Query:");
		console.log(result.metadata.query_plan.queries[0].query);
	} catch (error) {
		console.error("Query failed:", error);
	}
}

main();
