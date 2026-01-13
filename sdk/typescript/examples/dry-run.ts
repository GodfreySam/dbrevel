/**
 * Dry Run Example
 *
 * This example demonstrates how to validate a query without executing it.
 */

import { DbRevelClient } from "../src";

async function main() {
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
	});

	try {
		// Validate query without executing
		const result = await client.query("Get users with more than 5 orders", {
			dryRun: true,
		});

		console.log("Query Plan (Dry Run):");
		console.log(
			`- Databases: ${result.metadata.query_plan.databases.join(", ")}`,
		);
		console.log(
			`- Estimated cost: ${result.metadata.query_plan.estimated_cost}`,
		);
		console.log(
			`- Security rules applied: ${result.metadata.query_plan.security_applied.length}`,
		);

		console.log("\nGenerated Queries:");
		result.metadata.query_plan.queries.forEach((query, index) => {
			console.log(`\nQuery ${index + 1} (${query.database}):`);
			console.log(query.query);
		});

		// Note: result.data will be empty for dry runs
		console.log(`\nData rows: ${result.data.length} (empty for dry run)`);
	} catch (error) {
		console.error("Dry run failed:", error);
	}
}

main();
