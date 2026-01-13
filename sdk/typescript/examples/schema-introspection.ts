/**
 * Schema Introspection Example
 *
 * This example demonstrates how to explore database schemas using
 * the SDK's schema utilities.
 */

import { DbRevelClient, SchemaHelper } from "../src";

async function main() {
	const client = new DbRevelClient({
		baseUrl: "http://localhost:8000",
		apiKey: "your-project-api-key",
	});

	try {
		// Get all schemas
		const schemas = await client.getSchemas();
		const helper = new SchemaHelper(schemas);

		console.log("Available Databases:");
		const dbNames = helper.getDatabaseNames();
		dbNames.forEach((dbName) => {
			console.log(`- ${dbName}`);
		});

		// Explore PostgreSQL database
		if (dbNames.length > 0) {
			const dbName = dbNames[0];
			const schema = helper.getDatabaseSchema(dbName);

			if (schema?.type === "postgresql") {
				console.log(`\n${dbName} (PostgreSQL):`);
				const tableNames = helper.getTableNames(dbName);
				console.log(`Tables: ${tableNames.join(", ")}`);

				// Explore first table
				if (tableNames.length > 0) {
					const tableName = tableNames[0];
					const table = helper.getTable(dbName, tableName);

					if (table) {
						console.log(`\nTable: ${tableName}`);
						const columnNames = helper.getColumnNames(dbName, tableName);
						console.log(`Columns: ${columnNames.join(", ")}`);

						// Show primary keys
						const primaryKeys = helper.getPrimaryKeyColumns(dbName, tableName);
						if (primaryKeys.length > 0) {
							console.log(
								`Primary Keys: ${primaryKeys.map((col) => col.name).join(", ")}`,
							);
						}

						// Show foreign keys
						const foreignKeys = helper.getForeignKeyColumns(dbName, tableName);
						if (foreignKeys.length > 0) {
							console.log("\nForeign Keys:");
							foreignKeys.forEach((col) => {
								if (col.foreign_key) {
									console.log(
										`  ${col.name} -> ${col.foreign_key.table}.${col.foreign_key.column}`,
									);
								}
							});
						}
					}
				}
			} else if (schema?.type === "mongodb") {
				console.log(`\n${dbName} (MongoDB):`);
				const collectionNames = helper.getCollectionNames(dbName);
				console.log(`Collections: ${collectionNames.join(", ")}`);

				// Explore first collection
				if (collectionNames.length > 0) {
					const collectionName = collectionNames[0];
					const collection = helper.getCollection(dbName, collectionName);

					if (collection) {
						console.log(`\nCollection: ${collectionName}`);
						if (collection.fields) {
							const fieldNames = collection.fields.map((f) => f.name);
							console.log(`Fields: ${fieldNames.join(", ")}`);
						}
					}
				}
			}
		}

		// Find tables by column name
		console.log("\nFinding tables with 'email' column:");
		const tablesWithEmail = helper.findTablesByColumn("email");
		tablesWithEmail.forEach(({ database, table }) => {
			console.log(`  ${database}.${table.name}`);
		});
	} catch (error) {
		console.error("Schema introspection failed:", error);
	}
}

main();
