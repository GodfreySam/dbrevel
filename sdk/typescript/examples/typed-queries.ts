/**
 * Typed Queries Example
 *
 * This example demonstrates how to use TypeScript generics
 * for type-safe query results.
 */

import { DbRevelClient } from "../src";

// Define your data types
interface User {
	id: number;
	name: string;
	email: string;
	created_at: string;
}

interface Order {
	id: number;
	user_id: number;
	total: number;
	status: string;
	created_at: string;
}

async function main() {
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
	});

	try {
		// Type-safe query - result.data will be User[]
		const usersResult = await client.query<User>("Get all users");
		console.log("Users:", usersResult.data);

		// TypeScript will provide autocomplete for User properties
		usersResult.data.forEach((user) => {
			console.log(`User: ${user.name} (${user.email})`);
			// TypeScript knows user has: id, name, email, created_at
		});

		// Another typed query
		const ordersResult = await client.query<Order>(
			"Get all orders from last month",
		);
		console.log("Orders:", ordersResult.data);

		ordersResult.data.forEach((order) => {
			console.log(`Order #${order.id}: $${order.total} (${order.status})`);
			// TypeScript knows order has: id, user_id, total, status, created_at
		});

		// Query with context
		const userOrdersResult = await client.query<Order>("Get orders for user", {
			context: { userId: 123 },
		});

		// Access metadata with full type safety
		console.log(`Execution time: ${usersResult.metadata.execution_time_ms}ms`);
		console.log(`Trace ID: ${usersResult.metadata.trace_id}`);
	} catch (error) {
		console.error("Query failed:", error);
	}
}

main();
